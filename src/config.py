"""Configuration for Option Screener."""

from dataclasses import dataclass
from typing import List


@dataclass
class ScreenerConfig:
    # Connection
    host: str = "127.0.0.1"
    port: int = 7496
    client_id: int = 1

    # Scanner settings
    scanner_instruments: List[str] = None  # None = all, or ["STK"] for stocks only
    scanner_location: str = "STK.US.MAJOR"  # US major stocks
    scanner_scan_codes: List[str] = None  # None = default Top Volume + Most Active

    # Filter criteria
    min_dte: int = 30
    max_dte: int = 45
    short_delta_min: float = -0.30
    short_delta_max: float = -0.15
    long_delta_min: float = -0.10
    long_delta_max: float = -0.05
    min_volume: int = 100
    min_pop: float = 0.65  # Probability of Profit > 65%

    # Output
    top_n: int = 20
    output_dir: str = "/home/hermes/option-screener-project/output"

    # Risk management (variables)
    max_positions: int = 5
    stop_multiplier: float = 2.0  # 2x premium
    profit_target: float = 0.50  # 50% profit target

    def __post_init__(self):
        if self.scanner_instruments is None:
            self.scanner_instruments = ["STK"]
        if self.scanner_scan_codes is None:
            self.scanner_scan_codes = ["TOP_VOLUME_RATE", "MOST_ACTIVE"]


# Default config instance
CONFIG = ScreenerConfig()