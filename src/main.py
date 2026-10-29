#!/usr/bin/env python3
"""
Bull Put Spread Screener - Main Entry Point

Daily options screener for Bull Put Spreads using IBKR (ib_insync).
Finds high-probability credit spreads based on Delta, DTE, Volume, and PoP.

Usage:
    python -m src.main                    # Run screening with default watchlist
    python -m src.main --use-scanner      # Use IBKR scanner instead of watchlist
    python -m src.main --watchlist NVDA,TSLA,AAPL  # Custom watchlist
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import CONFIG, ScreenerConfig
from src.screener import run_screening
from src.output import generate_all_reports

# Default watchlist of liquid, optionable stocks
DEFAULT_WATCHLIST = [
    'NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META',
    'NFLX', 'AMD', 'INTC', 'CRM', 'ADBE', 'PYPL', 'UBER',
    'SHOP', 'SQ', 'ROKU', 'ZM', 'DOCU', 'PTON', 'COIN',
    'MSTR', 'MARA', 'RIOT', 'SMCI', 'AVGO', 'QCOM', 'MU',
    'LRCX', 'KLAC', 'AMAT', 'ASML', 'TSM', 'ARM', 'PLTR',
    'SPY', 'QQQ', 'IWM', 'DIA'  # ETFs with liquid options
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description='Bull Put Spread Screener')
    parser.add_argument('--host', default=CONFIG.host, help='TWS/Gateway host')
    parser.add_argument('--port', type=int, default=CONFIG.port, help='TWS/Gateway port')
    parser.add_argument('--client-id', type=int, default=CONFIG.client_id, help='Client ID')
    parser.add_argument('--top-n', type=int, default=CONFIG.top_n, help='Top N results')
    parser.add_argument('--min-dte', type=int, default=CONFIG.min_dte, help='Min DTE')
    parser.add_argument('--max-dte', type=int, default=CONFIG.max_dte, help='Max DTE')
    parser.add_argument('--min-pop', type=float, default=CONFIG.min_pop, help='Min PoP (0-1)')
    parser.add_argument('--min-volume', type=int, default=CONFIG.min_volume, help='Min volume per leg')
    parser.add_argument('--short-delta-min', type=float, default=CONFIG.short_delta_min, help='Short put min delta')
    parser.add_argument('--short-delta-max', type=float, default=CONFIG.short_delta_max, help='Short put max delta')
    parser.add_argument('--long-delta-min', type=float, default=CONFIG.long_delta_min, help='Long put min delta')
    parser.add_argument('--long-delta-max', type=float, default=CONFIG.long_delta_max, help='Long put max delta')
    parser.add_argument('--max-positions', type=int, default=CONFIG.max_positions, help='Max positions')
    parser.add_argument('--stop-mult', type=float, default=CONFIG.stop_multiplier, help='Stop multiplier')
    parser.add_argument('--profit-target', type=float, default=CONFIG.profit_target, help='Profit target (0-1)')
    parser.add_argument('--output-dir', default=CONFIG.output_dir, help='Output directory')
    parser.add_argument('--use-scanner', action='store_true', help='Use IBKR scanner instead of watchlist')
    parser.add_argument('--watchlist', type=str, default=None, help='Comma-separated watchlist symbols')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    return parser.parse_args()


def build_config(args) -> ScreenerConfig:
    """Build config from CLI args."""
    return ScreenerConfig(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        top_n=args.top_n,
        min_dte=args.min_dte,
        max_dte=args.max_dte,
        min_pop=args.min_pop,
        min_volume=args.min_volume,
        short_delta_min=args.short_delta_min,
        short_delta_max=args.short_delta_max,
        long_delta_min=args.long_delta_min,
        long_delta_max=args.long_delta_max,
        max_positions=args.max_positions,
        stop_multiplier=args.stop_mult,
        profit_target=args.profit_target,
        output_dir=args.output_dir
    )


def main():
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = build_config(args)

    # Determine watchlist
    if args.use_scanner:
        watchlist = None  # Use scanner
    elif args.watchlist:
        watchlist = [s.strip().upper() for s in args.watchlist.split(',')]
    else:
        watchlist = DEFAULT_WATCHLIST

    # Ensure output directory exists
    Path(config.output_dir).mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("BULL PUT SPREAD SCREENER")
    logger.info("=" * 60)
    logger.info(f"Connection: {config.host}:{config.port} (clientId={config.client_id})")
    logger.info(f"Filters: DTE {config.min_dte}-{config.max_dte}, "
                f"Short Δ {config.short_delta_min:.2f}-{config.short_delta_max:.2f}, "
                f"Long Δ {config.long_delta_min:.2f}-{config.long_delta_max:.2f}")
    logger.info(f"Min Volume: {config.min_volume}, Min PoP: {config.min_pop:.0%}")
    logger.info(f"Output: Top {config.top_n} -> {config.output_dir}")
    if watchlist:
        logger.info(f"Watchlist: {len(watchlist)} symbols")
    else:
        logger.info("Source: IBKR Scanner")
    logger.info("=" * 60)

    try:
        # Run screening
        result = run_screening(config, watchlist=watchlist)

        # Generate reports
        files = generate_all_reports(result)

        logger.info("=" * 60)
        logger.info("SCREENING COMPLETE")
        logger.info(f"  Symbols scanned: {result.scanned_symbols}")
        logger.info(f"  Spreads found: {len(result.spreads)}")
        logger.info(f"  Reports generated:")
        for fmt, path in files.items():
            logger.info(f"    {fmt.upper()}: {path}")
        if result.errors:
            logger.warning(f"  Errors: {len(result.errors)}")
            for e in result.errors:
                logger.warning(f"    - {e}")
        logger.info("=" * 60)

        # Print top 5 to console
        if result.spreads:
            print("\n🏆 TOP 5 BULL PUT SPREADS:")
            print("-" * 100)
            print(f"{'Symbol':<8} {'Exp':<12} {'DTE':>3} {'Short':>8} {'Long':>8} {'Width':>6} {'Credit':>7} {'PoP':>6} {'R/R':>5}")
            print("-" * 100)
            for s in result.spreads[:5]:
                print(f"{s.symbol:<8} {s.expiry.strftime('%Y-%m-%d'):<12} {s.dte:>3} "
                      f"{s.short_strike:>8.2f} {s.long_strike:>8.2f} {s.width:>6.2f} "
                      f"${s.credit:>6.2f} {s.pop*100:>5.1f}% {s.risk_reward:>5.2f}")
            print("-" * 100)

        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Screening failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())