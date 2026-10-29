"""Core data models for the option screener."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
import math


@dataclass
class OptionQuote:
    """Container for option market data."""
    symbol: str
    expiry: date
    strike: float
    right: str  # 'C' or 'P'
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_vol: float
    delta: float
    gamma: float
    theta: float
    vega: float
    underlying_price: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2 if self.bid > 0 and self.ask > 0 else self.last

    @property
    def dte(self) -> int:
        return (self.expiry - date.today()).days


@dataclass
class BullPutSpread:
    """Represents a Bull Put Spread candidate."""
    symbol: str
    expiry: date
    dte: int
    short_strike: float
    long_strike: float
    width: float
    short_option: OptionQuote
    long_option: OptionQuote
    credit: float
    max_profit: float
    max_loss: float
    pop: float  # Probability of Profit
    short_delta: float
    long_delta: float
    short_volume: int
    long_volume: int
    underlying_price: float
    iv_rank_proxy: float = 0.0  # Placeholder for IV vs HV comparison

    @property
    def risk_reward(self) -> float:
        return self.max_profit / self.max_loss if self.max_loss > 0 else 0

    @property
    def credit_pct_width(self) -> float:
        return (self.credit / self.width) * 100 if self.width > 0 else 0

    @property
    def break_even(self) -> float:
        return self.short_strike - self.credit


@dataclass
class ScreeningResult:
    """Results container for a screening run."""
    timestamp: datetime = field(default_factory=datetime.now)
    spreads: list = field(default_factory=list)
    scanned_symbols: int = 0
    errors: list = field(default_factory=list)

    def to_dataframe(self):
        import pandas as pd
        if not self.spreads:
            return pd.DataFrame()
        data = []
        for s in self.spreads:
            data.append({
                'Symbol': s.symbol,
                'Expiry': s.expiry.strftime('%Y-%m-%d'),
                'DTE': s.dte,
                'Short Strike': s.short_strike,
                'Long Strike': s.long_strike,
                'Width': s.width,
                'Credit': round(s.credit, 2),
                'Max Profit': round(s.max_profit, 2),
                'Max Loss': round(s.max_loss, 2),
                'PoP': round(s.pop * 100, 1),
                'Short Delta': round(s.short_delta, 3),
                'Long Delta': round(s.long_delta, 3),
                'Short Vol': s.short_volume,
                'Long Vol': s.long_volume,
                'Underlying': round(s.underlying_price, 2),
                'R/R': round(s.risk_reward, 2),
                'Credit%Width': round(s.credit_pct_width, 1),
                'Break Even': round(s.break_even, 2),
            })
        return pd.DataFrame(data)