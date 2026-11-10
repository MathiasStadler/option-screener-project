# Bull Put Spread Screener

Daily options screener for **Bull Put Spreads** using IBKR (ib_insync).
Finds high-probability credit spreads based on Delta, DTE, Volume, and Probability of Profit (PoP).

## Features

- **Strategy**: Bull Put Spreads only (Short Put + Long Put, same expiry)
- **Data Source**: IBKR TWS/Gateway via `ib_insync` (Port 7496)
- **Universe**: Default watchlist of 39 liquid stocks/ETFs or IBKR Scanner
- **Filters**:
  - DTE: 30–55 days (monthly expiries, 3rd Fridays)
  - Short Put Delta: -0.40 to -0.10
  - Long Put Delta: -0.15 to -0.02
  - Min Probability of Profit (PoP): 55%
  - Min Volume per leg: configurable (0 = no filter)
- **Output**: CSV, Excel (formatted), HTML (interactive Chart.js charts)
- **Risk Management** (configurable): max positions, stop-loss multiplier, profit target

---

## Installation

```bash
# 1. Clone / navigate to project
cd /home/hermes/option-screener-project

# 2. Activate virtual environment
source venv/bin/activate

# 3. Verify dependencies (already installed)
# ib_insync, pandas, numpy, scipy, openpyxl, jinja2
```

---

## TWS / IBKR Gateway Configuration

**Required**: TWS or IBKR Gateway must be running and accessible on `localhost:7496`.

### 1. Enable API Access
- TWS: **File → Global Configuration → API → Settings**
- Check: ✅ **Enable ActiveX and Socket Clients**
- Socket port: **7496** (default for live)
- Trusted IP: `127.0.0.1` (or leave empty for localhost)

### 2. Increase API Idle Timeout (Critical!)
Default is 30 seconds — too short for screening.
- **File → Global Configuration → API → Settings**
- **Socket timeout / Idle timeout**: Set to **300** (or higher)
- Apply & restart TWS

### 3. Market Data Subscription
- For real-time Greeks/IV: Requires **"US Options Streaming Market Data"** subscription
- Without subscription: Works with **delayed data** (15 min delay) — sufficient for screening

---

## Usage

### Activate venv first
```bash
cd /home/hermes/option-screener-project
source venv/bin/activate
```

### 1. Default Watchlist (recommended)
```bash
python -m src.main \
  --min-volume 0 \
  --max-dte 55 \
  --min-pop 0.55 \
  --short-delta-min -0.4 \
  --short-delta-max -0.1 \
  --long-delta-min -0.15 \
  --long-delta-max -0.02
```

### 2. Custom Watchlist
```bash
python -m src.main \
  --watchlist NVDA,TSLA,AAPL,MSFT,AMZN,GOOGL,META \
  --min-volume 0 \
  --max-dte 55 \
  --min-pop 0.55 \
  --short-delta-min -0.4 \
  --short-delta-max -0.1 \
  --long-delta-min -0.15 \
  --long-delta-max -0.02
```

### 2.1 Custom Watchlist
```bash
python -m src.main \
  --watchlist NVDA,TSLA,AAPL,MSFT,AMZN,GOOGL,META \
  --min-volume 0 \
  --max-dte 10 \
  --min-pop 0.55 \
  --short-delta-min -0.4 \
  --short-delta-max -0.1 \
  --long-delta-min -0.15 \
  --long-delta-max -0.02
```

### 2.2 Custom Watchlist
```bash
python -m src.main \
  --watchlist CSX,TREX,CROX,FTB,ELF \
  --min-volume 0 \
  --max-dte 55 \
  --min-pop 0.55 \
  --short-delta-min -0.4 \
  --short-delta-max -0.1 \
  --long-delta-min -0.15 \
  --long-delta-max -0.02
```


### 3. Use IBKR Scanner (Top Volume + Most Active)
```bash
python -m src.main \
  --use-scanner \
  --min-volume 100 \
  --max-dte 45 \
  --min-pop 0.65 \
  --short-delta-min -0.3 \
  --short-delta-max -0.15 \
  --long-delta-min -0.1 \
  --long-delta-max -0.05
```

### 4. Conservative Settings (Higher Probability)
```bash
python -m src.main \
  --watchlist NVDA,TSLA,AAPL,MSFT,SPY,QQQ \
  --min-volume 50 \
  --max-dte 45 \
  --min-pop 0.70 \
  --short-delta-min -0.25 \
  --short-delta-max -0.10 \
  --long-delta-min -0.10 \
  --long-delta-max -0.03
```

### 5. Aggressive Settings (Higher Credit)
```bash
python -m src.main \
  --watchlist NVDA,TSLA,AMD,NFLX,PLTR,COIN \
  --min-volume 10 \
  --max-dte 55 \
  --min-pop 0.50 \
  --short-delta-min -0.45 \
  --short-delta-max -0.15 \
  --long-delta-min -0.20 \
  --long-delta-max -0.05
```

---

## All CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | TWS/Gateway host |
| `--port` | `7496` | TWS/Gateway port (7496=live, 4001=gateway) |
| `--client-id` | `1` | API client ID (unique per connection) |
| `--top-n` | `20` | Number of top spreads to output |
| `--min-dte` | `30` | Minimum days to expiration |
| `--max-dte` | `45` | Maximum days to expiration |
| `--min-pop` | `0.65` | Minimum Probability of Profit (0–1) |
| `--min-volume` | `100` | Minimum volume per leg |
| `--short-delta-min` | `-0.30` | Short put minimum delta |
| `--short-delta-max` | `-0.15` | Short put maximum delta |
| `--long-delta-min` | `-0.10` | Long put minimum delta |
| `--long-delta-max` | `-0.05` | Long put maximum delta |
| `--max-positions` | `5` | Max concurrent positions (report only) |
| `--stop-mult` | `2.0` | Stop loss at N× premium (report only) |
| `--profit-target` | `0.50` | Profit target at N% (report only) |
| `--output-dir` | `./output` | Output directory |
| `--use-scanner` | `false` | Use IBKR scanner instead of watchlist |
| `--watchlist` | *(default list)* | Comma-separated symbols |
| `--verbose` / `-v` | `false` | Debug logging |

---

## Output Files

Generated in `./output/` with timestamp:

| File | Description |
|------|-------------|
| `bull_put_spreads_YYYYMMDD_HHMMSS.csv` | Raw data, sortable |
| `bull_put_spreads_YYYYMMDD_HHMMSS.xlsx` | Formatted Excel with Summary sheet |
| `bull_put_spreads_YYYYMMDD_HHMMSS.html` | Interactive report with charts |

### HTML Report Charts
- **Credit vs PoP** (scatter)
- **DTE Distribution** (bar)
- **Top 10 Risk/Reward** (horizontal bar)
- **Sector Distribution** (doughnut, placeholder)

---

## Example Output (Console)

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

### CSV Columns
```
Symbol, Expiry, DTE, Short Strike, Long Strike, Width, Credit,
Max Profit, Max Loss, PoP, Short Delta, Long Delta,
Short Vol, Long Vol, Underlying, R/R, Credit%Width, Break Even
```

---

## Risk Management (Configurable Variables)

The screener includes risk parameters in output (not enforced during screening):

| Parameter | Purpose |
|-----------|---------|
| `max_positions` | Max concurrent positions (default 5) |
| `stop_multiplier` | Stop loss at N× credit received (default 2.0) |
| `profit_target` | Take profit at N% of max profit (default 50%) |

---

## Troubleshooting

### Connection Timeout (30 seconds)
**Cause**: TWS default API idle timeout = 30s
**Fix**: TWS → Global Configuration → API → Settings → Socket timeout = 300+

### "No security definition" for options
**Cause**: Strike/expiry combo doesn't exist
**Fix**: Script auto-qualifies valid strikes — no action needed

### Zero spreads found
- Relax filters: lower `--min-pop`, widen delta ranges, increase `--max-dte`
- Check market hours (screening works best during RTH)
- Verify TWS shows option chains for symbols

### Volume = 0 / NaN
- Delayed data doesn't always include volume
- Use `--min-volume 0` to ignore volume filter

### ModuleNotFoundError
```bash
source venv/bin/activate
pip install ib_insync pandas numpy scipy openpyxl jinja2
```

---

## Project Structure

```
option-screener-project/
├── venv/                    # Virtual environment
├── src/
│   ├── __init__.py
│   ├── config.py           # ScreenerConfig dataclass
│   ├── models.py           # OptionQuote, BullPutSpread, ScreeningResult
│   ├── ibkr_client.py      # IBKR connection, scanner, market data
│   ├── screener.py         # Core engine: Black-Scholes, spread finder
│   ├── output.py           # CSV/Excel/HTML report generation
│   └── main.py             # CLI entry point
├── output/                 # Generated reports
└── README.md
```

---

## Default Watchlist (39 Symbols)

**Stocks**: NVDA, TSLA, AAPL, MSFT, AMZN, GOOGL, META, NFLX, AMD, INTC, CRM, ADBE, PYPL, UBER, SHOP, SQ, ROKU, ZM, DOCU, PTON, COIN, MSTR, MARA, RIOT, SMCI, AVGO, QCOM, MU, LRCX, KLAC, AMAT, ASML, TSM, ARM, PLTR

**ETFs**: SPY, QQQ, IWM, DIA

---

## License

MIT — Use at your own risk. Not financial advice.

python -m src.main   --watchlist CSX,TREX,CROX,FTB,ELF   --min-volume 0   --max-dte 55   --min-pop 0.55   --short-delta-min -0.4   --short-delta-max -0.1   --long-delta-min -0.15   --long-delta-max -0.02

