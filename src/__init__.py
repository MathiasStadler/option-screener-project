"""Option Screener Package."""

from src.config import CONFIG, ScreenerConfig
from src.models import OptionQuote, BullPutSpread, ScreeningResult
from src.ibkr_client import IBKRClient
from src.screener import run_screening, SpreadFinder, BlackScholes
from src.output import generate_all_reports, save_csv, save_excel, save_html

__version__ = '1.0.0'
__all__ = [
    'CONFIG', 'ScreenerConfig',
    'OptionQuote', 'BullPutSpread', 'ScreeningResult',
    'IBKRClient',
    'run_screening', 'SpreadFinder', 'BlackScholes',
    'generate_all_reports', 'save_csv', 'save_excel', 'save_html'
]