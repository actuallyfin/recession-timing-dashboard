# Recession Timing Dashboard Project Guide

This repo is the active home for the recession timing dashboard. It is separate from the CAPE country rotation backtesting work and keeps its own data-loading, strategy, dashboard, and deployment code.

## Main Flow

1. `dashboard.py` is the entry point.
2. It calls `strategy.py` to build each strategy variant and benchmark.
3. `strategy.py` calls `data_loader.py` for macro data, equity total-return data, and cash returns.
4. `data_loader.py` uses `market_data.py` for shared market-data utilities.
5. `dashboard.py` writes the static site files to `output/`.
6. GitHub Actions runs the same build daily and publishes `output/` to GitHub Pages.

## Scripts And Modules

### `dashboard.py`

Builds the web dashboard as static HTML, CSS, and JavaScript. It defines the visible strategy variants, prepares the current-signal summary, builds the performance table and charts, and writes the final files into `output/`.

Important responsibilities:

- Defines the dashboard strategy menu, including `ActuallyFinance GTT` and the Philosophical Economics GTT variations.
- Renders current signal tiles, indicator tables, rule summaries, performance tables, and growth charts.
- Creates source links for dated SPY observations through the shared Yahoo Finance helper.
- Accepts `--refresh` to force fresh data downloads before rebuilding.

### `strategy.py`

Contains the backtesting engine and strategy calculations. It combines daily SPY ETF/proxy total-return data, cash returns, economic indicator signals, and the 200-day SMA trend rule.

Important responsibilities:

- Builds daily indicator scores for each strategy variant.
- Applies the timing gate and the 200-day SMA trend-following rule.
- Calculates daily strategy returns, benchmark returns, drawdowns, Sharpe ratio, Sortino ratio, CAGR, and percent invested.
- Produces the structures that `dashboard.py` renders.

### `data_loader.py`

Loads and assembles project-specific data. This is where FRED macro data, revised point-in-time indicator histories, SPY ETF/proxy total-return history, and cash return history are prepared.

Important responsibilities:

- Downloads FRED series and FRED vintage/revision data when a `FRED_API_KEY` is available.
- Builds the hybrid daily macro dataset used by the strategy.
- Builds the extended U.S. equity total-return series:
  - SPY adjusted close after SPY inception.
  - Yahoo `^SP500TR` linked to SPY for the official pre-SPY total-return period.
  - Earlier synthetic annual S&P 500 total returns modeled with SPY's inception expense ratio.
- Builds the cash return series using BIL where available and FRED risk-free data before BIL.
- Looks up FRED release calendars for the "next update" dates in the indicator table.

### `market_data.py`

Shared market-data helper module. This is intended to stay generic enough to support future strategy backtests without importing CAPE-specific code.

Important responsibilities:

- Downloads text from remote data sources with retry and local caching support.
- Loads Yahoo Finance adjusted daily price data into a consistent DataFrame.
- Drops an incomplete current-session Yahoo bar before the market close buffer.
- Provides `scale_to_anchor()` for linking one price index to another at a chosen date.
- Builds Yahoo Finance history links for specific observation dates.
- Reads local yfinance-style fallback CSVs if network data is unavailable.

### `config.py`

Holds strategy and data constants. This is the first place to look when changing indicator definitions, FRED series IDs, signal scores, thresholds, or the default trigger score.

Important responsibilities:

- Defines each macro indicator and its rule.
- Stores FRED graph links used on the page.
- Stores the backtest start date and SPY inception date.
- Stores SPY's inception expense ratio used in the early synthetic index period.

### `requirements.txt`

Lists the Python packages needed for the build. The current project intentionally stays lightweight.

### `.github/workflows/deploy-pages.yml`

Builds and deploys the dashboard through GitHub Actions. It installs Python dependencies, sets `FRED_API_KEY` from the repo secret, runs `python dashboard.py --refresh`, and publishes the generated `output/` folder to GitHub Pages.

### `notes/`

Reference notes from one-off research and backtest comparisons. These are not part of the dashboard build, but they preserve useful decisions and exploratory results.

### `data/raw/`

Local cache for downloaded raw data. This folder is ignored by git because the dashboard can refresh it from the source APIs.

### `output/`

Generated static site files. This folder is ignored by git in the source branch because GitHub Actions rebuilds and deploys it.

## Data Refresh Model

The dashboard is designed to be rebuilt from source data. On a local machine, run:

```powershell
$env:FRED_API_KEY = "your_fred_key"
python dashboard.py --refresh
```

Without `--refresh`, cached files in `data/raw/` are reused when present. With `--refresh`, the build attempts to download fresh FRED and Yahoo data and then rebuilds the static dashboard.

On GitHub Pages, the scheduled workflow handles this automatically. The user-facing website remains static, but the static files are regenerated by the daily job.

## Extension Points

For future recession timing or related backtests:

- Add generic market data utilities to `market_data.py`.
- Add project-specific macro, cash, or stitched-index loaders to `data_loader.py`.
- Add strategy logic and metrics to `strategy.py`.
- Add visible strategy variants and presentation changes to `dashboard.py`.
- Keep CAPE country rotation helpers in their own project unless a helper is truly generic enough to copy into a shared package later.

