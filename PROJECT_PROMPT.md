# COMPLETE PROJECT PROMPT — Bull Put Spread Screener
=========================================================

## Original User Request
> Ich möchte look like diesem video mit der lynx api in python einen option screener bauen
> Schau dir dazu dieses video mit den kreterien an => @url:`https://www.youtube.com/watch?v=-PJhcM6dd_8`
> Das Ziel ist das ich jeden Tag einen Output mit den bestens options shortput oder auch Bull put spreads bekomme
> Verwende bitte die python lib/package ib-insync
> Für fragen bin ich hier - grill me :-)

## Video Reference
- **Title**: "Short Put Strategie - Optionen & Aktien screenen I Barchart.com" (Options4Winners)
- **URL**: https://www.youtube.com/watch?v=-PJhcM6dd_8
- **Core Strategy**: Short Put / Bull Put Spread screening using Barchart.com criteria

## Technical Requirements

### Stack
- **Language**: Python 3.13+
- **Primary Library**: `ib_insync` (IBKR TWS/Gateway API wrapper)
- **Dependencies**: pandas, numpy, scipy, openpyxl, jinja2
- **Runtime**: Virtual environment (venv)
- **Connection**: TWS Socket API on `localhost:7496` (Port 7496)

### Architecture
```
option-screener-project/
├── venv/                    # Virtual environment
├── src/
│   ├── config.py           # ScreenerConfig dataclass
│   ├── models.py           # OptionQuote, BullPutSpread, ScreeningResult
│   ├── ibkr_client.py      # IBKR connection, scanner, market data
│   ├── screener.py         # Core engine: Black-Scholes, spread finder
│   ├── output.py           # CSV/Excel/HTML report generation
│   ├── main.py             # CLI entry point
│   └── __init__.py
├── output/                 # Generated reports
└── README.md               # Complete documentation
```

## Screening Criteria (from Video + User Decisions)

### Strategy
- **Only Bull Put Spreads** (no naked short puts)
- Short Put + Long Put, same expiry
- Short Delta: -0.40 to -0.10 (relaxed from video's -0.30 to -0.15)
- Long Delta: -0.15 to -0.02 (relaxed from video's -0.10 to -0.05)

### Filters
| Parameter | Value | Notes |
|-----------|-------|-------|
| DTE (Days to Expiration) | 30–55 days | Monthly expiries (3rd Fridays) |
| Min Probability of Profit (PoP) | 55% | Black-Scholes calculated |
| Min Volume per leg | 0 (configurable) | Delayed data often lacks volume |
| IV Rank | **Excluded** | No IV history via IBKR; uses HV proxy |

### Universe
- **Default**: 39-symbol watchlist (liquid stocks + ETFs)
  - Stocks: NVDA, TSLA, AAPL, MSFT, AMZN, GOOGL, META, NFLX, AMD, INTC, CRM, ADBE, PYPL, UBER, SHOP, SQ, ROKU, ZM, DOCU, PTON, COIN, MSTR, MARA, RIOT, SMCI, AVGO, QCOM, MU, LRCX, KLAC, AMAT, ASML, TSM, ARM, PLTR
  - ETFs: SPY, QQQ, IWM, DIA
- **Alternative**: IBKR Scanner (TOP_VOLUME_RATE + MOST_ACTIVE)

### Risk Management (Report Variables)
- `max_positions`: 5 (max concurrent positions)
- `stop_multiplier`: 2.0× premium received
- `profit_target`: 50% of max profit

## Implementation Details

### Data Flow
1. **Connect** to TWS/Gateway (delayed market data type 3)
2. **Get underlying price** + 1-year historical volatility (HV)
3. **Generate monthly expiries** (3rd Fridays within DTE range)
4. **Qualify valid strikes** per expiry via `ib.qualifyContracts()`
5. **Fetch market data** (bid/ask/last/volume) for each strike
6. **Calculate Greeks/PoP** via Black-Scholes using HV as IV proxy
7. **Build spreads**: Pair short/long puts meeting delta criteria
8. **Filter** by credit > 0, PoP ≥ threshold, volume ≥ threshold
9. **Sort** by `credit × PoP` (risk-adjusted return)
10. **Output** top N to CSV, Excel, HTML

### Black-Scholes Implementation
- `d1`, `d2` calculation
- Put delta: `N(d1) - 1`
- PoP (probability stock > short_strike at expiry): `N(d2)`
- Risk-free rate: 5% fixed

### Delayed Data Handling
- `ib.reqMarketDataType(3)` — 15-min delayed data
- No real-time Greeks/IV → calculate from HV
- Snapshot=False + 1.5s wait for streaming delayed quotes
- Volume often NaN → `safe_int()` helper

### TWS Configuration Required
1. **Enable API**: File → Global Configuration → API → Settings → ✅ Enable ActiveX and Socket Clients
2. **Port**: 7496 (live), 4001 (gateway)
3. **CRITICAL**: Socket/Idle timeout → **300 seconds** (default 30s too short)

## CLI Interface

```bash
# Default watchlist
python -m src.main \
  --min-volume 0 \
  --max-dte 55 \
  --min-pop 0.55 \
  --short-delta-min -0.4 \
  --short-delta-max -0.1 \
  --long-delta-min -0.15 \
  --long-delta-max -0.02

# Custom watchlist
python -m src.main --watchlist NVDA,TSLA,AAPL,MSFT [filters...]

# IBKR Scanner
python -m src.main --use-scanner [filters...]

# All options
--host, --port, --client-id, --top-n, --min-dte, --max-dte, --min-pop,
--min-volume, --short-delta-min/max, --long-delta-min/max,
--max-positions, --stop-mult, --profit-target, --output-dir,
--use-scanner, --watchlist, --verbose
```

## Output Formats

### 1. CSV (`bull_put_spreads_YYYYMMDD_HHMMSS.csv`)
Raw columns: Symbol, Expiry, DTE, Short Strike, Long Strike, Width, Credit, Max Profit, Max Loss, PoP, Short Delta, Long Delta, Short Vol, Long Vol, Underlying, R/R, Credit%Width, Break Even

### 2. Excel (`bull_put_spreads_YYYYMMDD_HHMMSS.xlsx`)
- **Spreads sheet**: Formatted, auto-width columns
- **Summary sheet**: Run metadata (timestamp, symbols scanned, config)

### 3. HTML (`bull_put_spreads_YYYYMMDD_HHMMSS.html`)
Interactive report with Chart.js:
- Credit vs PoP (scatter)
- DTE Distribution (bar)
- Top 10 Risk/Reward (horizontal bar)
- Sector Distribution (doughnut — placeholder)
- Sortable table with all spreads

## Console Output Example
```
🏆 TOP 5 BULL PUT SPREADS:
----------------------------------------------------------------------------------------------------
Symbol   Exp          DTE    Short     Long  Width  Credit    PoP   R/R
----------------------------------------------------------------------------------------------------
NVDA     2026-12-18    50   200.00   170.00  30.00 $  5.13  67.6%  0.21
NVDA     2026-12-18    50   200.00   180.00  20.00 $  4.17  67.6%  0.26
NVDA     2026-12-18    50   190.00   170.00  20.00 $  2.63  79.7%  0.15
NVDA     2026-12-18    50   190.00   180.00  10.00 $  1.62  79.7%  0.19
----------------------------------------------------------------------------------------------------
```

## Key Code Patterns

### Strike Qualification
```python
def get_valid_strikes(self, symbol, expiry, min_strike, max_strike, step):
    strikes = generate_strikes(min_strike, max_strike, step)
    contracts = [Option(symbol, expiry_str, s, 'P', 'SMART') for s in strikes]
    qualified = self.ib.qualifyContracts(*contracts)
    return sorted([c.strike for c in qualified], reverse=True)
```

### Spread Construction
```python
# Pre-calculate deltas via Black-Scholes (HV as IV proxy)
for strike in valid_strikes:
    delta = BlackScholes.put_delta(underlying, strike, T, r, hv)

# Pair short/long
for short_strike in strikes:
    if short_delta in range:
        for long_strike in strikes:
            if long_strike < short_strike and long_delta in range:
                credit = short_mid - long_mid
                if credit > 0 and pop >= min_pop:
                    create_spread()
```

### Safe Volume Conversion
```python
def safe_int(value) -> int:
    if value is None: return 0
    if isinstance(value, float) and math.isnan(value): return 0
    try: return int(value)
    except: return 0
```

## Known Limitations / Future Work

| Item | Status |
|------|--------|
| TWS idle timeout (30s default) | **Must configure to 300+** |
| Real-time Greeks/IV | Requires paid market data subscription |
| Parallel screening | Sequential only (ThreadPool easy to add) |
| Sector data for HTML | Placeholder (needs fundamental data source) |
| Config file (YAML) | CLI only currently |
| Historical logging | Not implemented |
| Alerting (Telegram/Email) | Not implemented |
| Market hours/holiday check | Not implemented |

## Grilling Decisions (User Confirmed)
1. ✅ Only Bull Put Spreads (margin advantage)
2. ✅ IBKR TWS Socket (7496) via ib_insync
3. ✅ Output: CSV + HTML (with charts)
4. ✅ Manual trigger (user starts TWS first)
5. ✅ Risk vars: max_positions, stop_mult, profit_target
6. ✅ Data source: ib_insync only (no Barchart scrape)
7. ✅ Universe: IBKR Scanner (Top Volume + Most Active)
8. ✅ IV-Rank excluded, HV proxy used
9. ✅ All scanner results screened
10. ✅ PoP > 65% (later relaxed to 55% for testing)
11. ✅ Local execution (not on server)
12. ✅ Top 20 results

## Run Commands Summary

```bash
cd /home/hermes/option-screener-project
source venv/bin/activate

# Quick test (1 symbol)
python -m src.main --watchlist NVDA --min-volume 0 --max-dte 55 --min-pop 0.55 \
  --short-delta-min -0.4 --short-delta-max -0.1 \
  --long-delta-min -0.15 --long-delta-max -0.02

# Production (default watchlist)
python -m src.main --min-volume 0 --max-dte 55 --min-pop 0.55 \
  --short-delta-min -0.4 --short-delta-max -0.1 \
  --long-delta-min -0.15 --long-delta-max -0.02

# Conservative
python -m src.main --watchlist NVDA,TSLA,AAPL,MSFT,SPY,QQQ \
  --min-volume 50 --max-dte 45 --min-pop 0.70 \
  --short-delta-min -0.25 --short-delta-max -0.10 \
  --long-delta-min -0.10 --long-delta-max -0.03
```

## File Locations
- **Project**: `/home/hermes/option-screener-project/`
- **README**: `/home/hermes/option-screener-project/README.md`
- **Source**: `/home/hermes/option-screener-project/src/`
- **Output**: `/home/hermes/option-screener-project/output/`
- **Venv**: `/home/hermes/option-screener-project/venv/`