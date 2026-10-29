"""IBKR connection and data fetching using ib_insync."""

import asyncio
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
import logging
import calendar

from ib_insync import IB, Stock, Option, ScannerSubscription, ScanData
from ib_insync.objects import Contract

from src.config import CONFIG
from src.models import OptionQuote, ScreeningResult

logger = logging.getLogger(__name__)


class IBKRClient:
    """Wrapper for ib_insync connection and data fetching."""

    def __init__(self, config=None):
        self.config = config or CONFIG
        self.ib = IB()
        self.connected = False

    def connect(self) -> bool:
        """Connect to TWS/Gateway."""
        try:
            self.ib.connect(
                self.config.host,
                self.config.port,
                clientId=self.config.client_id,
                timeout=30
            )
            # Use delayed market data (type 3) - works without real-time subscription
            self.ib.reqMarketDataType(3)
            self.connected = True
            logger.info(f"Connected to TWS at {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from TWS."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from TWS")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def get_scanner_results(self, scan_codes: List[str] = None,
                            instrument: str = "STK",
                            location: str = "STK.US.MAJOR",
                            max_results: int = 200) -> List[Contract]:
        """Get symbols from IBKR scanner (Top Volume, Most Active, etc.)."""
        if not self.connected:
            raise RuntimeError("Not connected to TWS")

        scan_codes = scan_codes or self.config.scanner_scan_codes
        all_contracts = []

        for scan_code in scan_codes:
            try:
                sub = ScannerSubscription(
                    instrument=instrument,
                    locationCode=location,
                    scanCode=scan_code
                )
                # Request scanner data
                scanner_data = self.ib.reqScannerData(sub, [])
                # Wait a bit for results
                self.ib.sleep(2)

                contracts = [d.contractDetails.contract for d in scanner_data]
                all_contracts.extend(contracts)
                logger.info(f"Scanner '{scan_code}': {len(contracts)} results")

            except Exception as e:
                logger.error(f"Scanner {scan_code} failed: {e}")

        # Deduplicate by symbol
        seen = set()
        unique = []
        for c in all_contracts:
            if c.symbol not in seen:
                seen.add(c.symbol)
                unique.append(c)

        logger.info(f"Total unique symbols from scanner: {len(unique)}")
        return unique[:max_results]

    def get_option_chain(self, symbol: str) -> List[dict]:
        """Get available option chains for a symbol (expiries and strikes)."""
        if not self.connected:
            raise RuntimeError("Not connected to TWS")

        contract = Stock(symbol, 'SMART', 'USD')
        try:
            # Qualify the contract first
            qualified = self.ib.qualifyContracts(contract)[0]
            chains = self.ib.reqSecDefOptParams(
                qualified.symbol, '', qualified.secType, qualified.conId
            )
            return chains
        except Exception as e:
            logger.error(f"Failed to get option chain for {symbol}: {e}")
            return []

    def get_option_market_data(self, symbol: str, expiry: date,
                                strike: float, right: str) -> Optional[OptionQuote]:
        """Get real-time market data for a specific option."""
        if not self.connected:
            raise RuntimeError("Not connected to TWS")

        contract = Option(symbol, expiry.strftime('%Y%m%d'), strike, right, 'SMART')
        underlying_contract = Stock(symbol, 'SMART', 'USD')
        try:
            qualified = self.ib.qualifyContracts(contract)
            if not qualified:
                return None
            contract = qualified[0]

            # Request market data with snapshot (use delayed if no real-time)
            ticker = self.ib.reqMktData(contract, '', True, False)
            self.ib.sleep(0.5)  # Wait for data

            # Also get underlying price
            underlying_ticker = self.ib.reqMktData(underlying_contract, '', True, False)
            self.ib.sleep(0.2)

            if ticker.bid <= 0 and ticker.ask <= 0 and ticker.last <= 0:
                return None

            return OptionQuote(
                symbol=symbol,
                expiry=expiry,
                strike=strike,
                right=right,
                bid=ticker.bid,
                ask=ticker.ask,
                last=ticker.last,
                volume=ticker.volume,
                open_interest=getattr(ticker, 'openInterest', 0) or 0,
                implied_vol=ticker.impliedVol if hasattr(ticker, 'impliedVol') and ticker.impliedVol else 0,
                delta=ticker.modelGreeks.delta if hasattr(ticker, 'modelGreeks') and ticker.modelGreeks else 0,
                gamma=ticker.modelGreeks.gamma if hasattr(ticker, 'modelGreeks') and ticker.modelGreeks else 0,
                theta=ticker.modelGreeks.theta if hasattr(ticker, 'modelGreeks') and ticker.modelGreeks else 0,
                vega=ticker.modelGreeks.vega if hasattr(ticker, 'modelGreeks') and ticker.modelGreeks else 0,
                underlying_price=underlying_ticker.last if underlying_ticker.last > 0 else 0
            )
        except Exception as e:
            logger.error(f"Market data failed for {symbol} {expiry} {strike}{right}: {e}")
            return None
        finally:
            # Cancel market data
            self.ib.cancelMktData(contract)
            self.ib.cancelMktData(underlying_contract)

    def get_historical_volatility(self, symbol: str, duration: str = '1 Y',
                                   bar_size: str = '1 day') -> float:
        """Get historical volatility of underlying (annualized)."""
        if not self.connected:
            raise RuntimeError("Not connected to TWS")

        contract = Stock(symbol, 'SMART', 'USD')
        try:
            bars = self.ib.reqHistoricalData(
                contract, '', duration, bar_size, 'TRADES', 1, 1, False
            )
            if not bars or len(bars) < 2:
                return 0.0

            import numpy as np
            closes = [b.close for b in bars]
            returns = np.diff(np.log(closes))
            hv = np.std(returns) * np.sqrt(252)  # Annualized
            return hv
        except Exception as e:
            logger.error(f"Historical vol failed for {symbol}: {e}")
            return 0.0

    def get_valid_strikes(self, symbol: str, expiry: date,
                          min_strike: float, max_strike: float,
                          strike_step: float = 5.0) -> List[float]:
        """Get valid option strikes for a symbol/expiry by qualifying contracts."""
        if not self.connected:
            raise RuntimeError("Not connected to TWS")

        expiry_str = expiry.strftime('%Y%m%d')
        strikes = []
        s = max_strike
        while s >= min_strike:
            strikes.append(round(s / strike_step) * strike_step)
            s -= strike_step

        # Create option contracts for all strikes
        contracts = [Option(symbol, expiry_str, strike, 'P', 'SMART') for strike in strikes]

        # Qualify in batches (ib_insync handles batching)
        qualified = self.ib.qualifyContracts(*contracts)

        valid_strikes = [c.strike for c in qualified]
        logger.debug(f"{symbol} {expiry}: {len(valid_strikes)}/{len(strikes)} valid strikes")
        return sorted(valid_strikes, reverse=True)


def get_monthly_expiries(min_dte: int, max_dte: int, months_ahead: int = 6) -> List[date]:
    """Get list of monthly expiration dates (3rd Fridays) within DTE range."""
    today = date.today()
    expiries = []
    
    for i in range(months_ahead):
        target_month = today.month + i
        target_year = today.year
        while target_month > 12:
            target_month -= 12
            target_year += 1
        
        # Find 3rd Friday of the month
        cal = calendar.monthcalendar(target_year, target_month)
        fridays = [week[calendar.FRIDAY] for week in cal if week[calendar.FRIDAY] != 0]
        if len(fridays) >= 3:
            third_friday = fridays[2]
            exp_date = date(target_year, target_month, third_friday)
            dte = (exp_date - today).days
            if min_dte <= dte <= max_dte:
                expiries.append(exp_date)
    
    return sorted(expiries)