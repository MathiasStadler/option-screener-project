"""Screening engine: finds Bull Put Spread candidates."""

import math
from datetime import date, timedelta
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import calendar

from scipy.stats import norm

from src.config import CONFIG
from src.models import OptionQuote, BullPutSpread, ScreeningResult
from src.ibkr_client import IBKRClient, get_monthly_expiries
from ib_insync import Stock
from ib_insync import Option as OptionContract

logger = logging.getLogger(__name__)


def safe_int(value) -> int:
    """Safely convert value to int, handling None and NaN."""
    if value is None:
        return 0
    if isinstance(value, float) and math.isnan(value):
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


class BlackScholes:
    """Black-Scholes calculator for PoP and Greeks."""

    @staticmethod
    def d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d1."""
        if sigma <= 0 or T <= 0:
            return 0
        return (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))

    @staticmethod
    def d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d2."""
        return BlackScholes.d1(S, K, T, r, sigma) - sigma * math.sqrt(T)

    @staticmethod
    def put_delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Put delta (negative)."""
        d1 = BlackScholes.d1(S, K, T, r, sigma)
        return norm.cdf(d1) - 1

    @staticmethod
    def probability_otm_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Probability that put expires OTM (stock > strike)."""
        if sigma <= 0 or T <= 0:
            return 0.5
        d2 = BlackScholes.d2(S, K, T, r, sigma)
        return norm.cdf(d2)

    @staticmethod
    def probability_profit_spread(S: float, short_K: float, long_K: float,
                                   T: float, r: float, sigma: float) -> float:
        """
        Probability of profit for Bull Put Spread.
        Profit if stock > short_strike - credit at expiry.
        """
        if sigma <= 0 or T <= 0:
            return 0.5
        # Break-even = short_strike - credit_received
        # But we don't know credit yet in pure BS - approximate with delta
        # Better: use the actual break-even
        d2 = BlackScholes.d2(S, short_K, T, r, sigma)
        return norm.cdf(d2)


class SpreadFinder:
    """Finds optimal Bull Put Spreads for a given symbol."""

    def __init__(self, client: IBKRClient, config=None):
        self.client = client
        self.config = config or CONFIG
        self.risk_free_rate = 0.05  # 5% approximate

    def find_spreads_for_symbol(self, symbol: str) -> List[BullPutSpread]:
        """Find all valid Bull Put Spreads for a symbol."""
        spreads = []

        # Get option chain to find available expiries
        chains = self.client.get_option_chain(symbol)
        if not chains:
            return spreads

        # Get underlying price and HV
        underlying_price = self._get_underlying_price(symbol)
        if underlying_price <= 0:
            return spreads

        hv = self.client.get_historical_volatility(symbol)

        # Get monthly expiries (3rd Fridays) within DTE range
        target_expiries = get_monthly_expiries(
            self.config.min_dte, self.config.max_dte
        )
        logger.debug(f"{symbol}: target expiries = {target_expiries}")

        for expiry in target_expiries:
            # Determine strike step based on price
            if underlying_price < 50:
                strike_step = 2.5
            elif underlying_price < 200:
                strike_step = 5.0
            else:
                strike_step = 10.0

            # OTM puts: strikes below current price
            min_strike = underlying_price * 0.5
            max_strike = underlying_price * 0.98  # Slightly OTM

            # Get valid strikes by qualifying contracts
            valid_strikes = self.client.get_valid_strikes(
                symbol, expiry, min_strike, max_strike, strike_step
            )

            if not valid_strikes:
                logger.debug(f"{symbol} {expiry}: no valid strikes")
                continue

            # Find valid spreads for this expiry
            expiry_spreads = self._find_spreads_for_expiry(
                symbol, expiry, valid_strikes, underlying_price, hv
            )
            spreads.extend(expiry_spreads)

        return spreads

    def _get_underlying_price(self, symbol: str) -> float:
        """Get current underlying price."""
        contract = Stock(symbol, 'SMART', 'USD')
        try:
            qualified = self.client.ib.qualifyContracts(contract)[0]
            # Use snapshot=False for streaming data, wait longer
            ticker = self.client.ib.reqMktData(qualified, '', False, False)
            self.client.ib.sleep(1.5)  # Wait for delayed data
            price = ticker.last if ticker.last and ticker.last > 0 else ticker.close
            self.client.ib.cancelMktData(qualified)
            return price if price and price > 0 else 0.0
        except Exception:
            return 0.0

    def _find_spreads_for_expiry(self, symbol: str, expiry: date,
                                  strikes: List[float], underlying: float, hv: float) -> List[BullPutSpread]:
        """Find all valid spreads for a specific expiry."""
        spreads = []
        dte = (expiry - date.today()).days
        T = dte / 365.0

        # Use HV as IV estimate for Greeks calculation (delayed data doesn't provide Greeks)
        iv_estimate = hv if hv > 0 else 0.3

        # Pre-calculate deltas for all strikes using Black-Scholes
        strike_deltas = {}
        for strike in strikes:
            if strike < underlying:  # Only OTM puts
                delta = BlackScholes.put_delta(underlying, strike, T, self.risk_free_rate, iv_estimate)
                strike_deltas[strike] = delta

        # Iterate through strikes to find short put candidates
        for short_strike in strikes:
            if short_strike >= underlying:
                continue  # Only OTM puts

            short_delta = strike_deltas.get(short_strike, 0)
            if not (self.config.short_delta_min <= short_delta <= self.config.short_delta_max):
                continue

            # Get short put market data (for bid/ask/volume)
            short_opt = self.client.get_option_market_data(symbol, expiry, short_strike, 'P')
            if not short_opt or short_opt.volume < self.config.min_volume:
                continue
            if short_opt.bid <= 0 and short_opt.ask <= 0 and short_opt.last <= 0:
                continue

            # Find long put (further OTM, lower strike)
            for long_strike in strikes:
                if long_strike >= short_strike:
                    continue

                long_delta = strike_deltas.get(long_strike, 0)
                if not (self.config.long_delta_min <= long_delta <= self.config.long_delta_max):
                    continue

                long_opt = self.client.get_option_market_data(symbol, expiry, long_strike, 'P')
                if not long_opt:
                    continue
                if long_opt.bid <= 0 and long_opt.ask <= 0 and long_opt.last <= 0:
                    continue
                if long_opt.volume < self.config.min_volume:
                    continue

                # Calculate spread metrics
                credit = short_opt.mid - long_opt.mid
                if credit <= 0:
                    continue

                width = short_strike - long_strike
                max_profit = credit * 100
                max_loss = (width - credit) * 100

                # Calculate PoP using Black-Scholes
                pop = BlackScholes.probability_otm_put(underlying, short_strike, T,
                                                        self.risk_free_rate, iv_estimate)

                if pop < self.config.min_pop:
                    continue

                spread = BullPutSpread(
                    symbol=symbol,
                    expiry=expiry,
                    dte=dte,
                    short_strike=short_strike,
                    long_strike=long_strike,
                    width=width,
                    short_option=short_opt,
                    long_option=long_opt,
                    credit=credit,
                    max_profit=max_profit,
                    max_loss=max_loss,
                    pop=pop,
                    short_delta=short_delta,
                    long_delta=long_delta,
                    short_volume=safe_int(short_opt.volume),
                    long_volume=safe_int(long_opt.volume),
                    underlying_price=underlying,
                    iv_rank_proxy=iv_estimate / hv if hv > 0 else 0
                )
                spreads.append(spread)

        return spreads


def run_screening(config=None, watchlist: list = None) -> ScreeningResult:
    """Main screening function - runs full scan and returns results."""
    config = config or CONFIG
    result = ScreeningResult()

    with IBKRClient(config) as client:
        if not client.connected:
            result.errors.append("Failed to connect to TWS")
            return result

        # Get symbols: use watchlist if provided, otherwise scanner
        if watchlist:
            # Convert watchlist symbols to contracts
            from ib_insync import Stock
            symbols = [Stock(sym, 'SMART', 'USD') for sym in watchlist]
            logger.info(f"Using watchlist: {len(symbols)} symbols")
        else:
            # Get symbols from scanner
            symbols = client.get_scanner_results()
            logger.info(f"Using scanner: {len(symbols)} symbols")

        result.scanned_symbols = len(symbols)

        finder = SpreadFinder(client, config)
        all_spreads = []

        # Process symbols (can parallelize later)
        for i, contract in enumerate(symbols):
            symbol = contract.symbol
            try:
                logger.info(f"[{i+1}/{len(symbols)}] Screening {symbol}...")
                spreads = finder.find_spreads_for_symbol(symbol)
                all_spreads.extend(spreads)
                logger.info(f"  Found {len(spreads)} spreads")
            except Exception as e:
                logger.error(f"Error screening {symbol}: {e}")
                result.errors.append(f"{symbol}: {e}")

        # Sort by credit * PoP (risk-adjusted return)
        all_spreads.sort(key=lambda s: s.credit * s.pop, reverse=True)

        # Take top N
        result.spreads = all_spreads[:config.top_n]

    logger.info(f"Screening complete. Top {len(result.spreads)} spreads found.")
    return result