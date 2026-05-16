# Recession Timing Dashboard Project Guide

This repo is the active home for the recession timing dashboard. It is separate from the CAPE country rotation backtesting work and keeps its own data-loading, strategy, dashboard, and deployment code.

## Main Flow

1. `dashboard.py` is the entry point.
2. It reads the live strategy list from `published_strategies.py`.
3. It calls `strategy.py` to build each daily 200-day strategy variant and benchmark.
4. `strategy.py` calls `data_loader.py` for macro data, equity total-return data, and cash returns.
5. `data_loader.py` uses `market_data.py` for shared market-data utilities.
6. `dashboard.py` derives the monthly 10-month moving-average variant payloads from the same daily source data.
7. `dashboard.py` writes the static site files to `output/`.
8. GitHub Actions runs the same build daily and publishes `output/` to GitHub Pages.

## Scripts And Modules

### `dashboard.py`

Builds the web dashboard as static HTML, CSS, and JavaScript. It prepares the current-signal summary, builds the performance table and charts, and writes the final files into `output/`.

Important responsibilities:

- Reads the dashboard strategy menu from `published_strategies.py`.
- Renders current signal tiles, indicator tables, rule summaries, performance tables, and growth charts.
- Builds the page-level trend-rule selector for daily 200-day SMA mode and monthly 10-month moving-average mode.
- Builds the page-level trading-cost selector for the default no-cost mode and the optional 10 bps bid/ask spread mode.
- Creates source links for dated SPY observations through the shared Yahoo Finance helper.
- Accepts `--refresh` to force fresh data downloads before rebuilding.

### `published_strategies.py`

Defines the strategy variants that appear on the live dashboard. This file is the intentional promotion point for strategies that should be visible on the published site.

Important responsibilities:

- Keeps `ActuallyFinance GTT` as the default strategy.
- Defines the Philosophical Economics GTT comparison variants.
- Stores per-strategy score maps and trigger scores used by `dashboard.py`.

### `strategy.py`

Contains the backtesting engine and strategy calculations for the daily 200-day SMA production mode. It combines daily SPY ETF/proxy total-return data, cash returns, economic indicator signals, and the 200-day SMA trend rule.

Important responsibilities:

- Builds daily indicator scores for each strategy variant.
- Applies the timing gate and the 200-day SMA trend-following rule.
- Calculates daily strategy returns, benchmark returns, drawdowns, Sharpe ratio, Sortino ratio, CAGR, and percent invested.
- Produces the structures that `dashboard.py` renders.

The monthly 10-month moving-average mode is assembled in `dashboard.py` from the same daily source output. It resamples completed months, uses month-end prices, compounds cash monthly, shifts the selected month-end trend position forward one month, and calculates monthly performance metrics.

The optional trading-cost mode is also assembled in `dashboard.py`. The 10 bps bid/ask option subtracts a 5 bps one-way cost when a strategy changes between equity and cash. The default mode keeps the published no-cost figures unchanged.

### `data_loader.py`

Loads and assembles project-specific data. This is where FRED macro data, revised point-in-time indicator histories, SPY ETF/proxy total-return history, and cash return history are prepared.

Important responsibilities:

- Downloads FRED series and FRED vintage/revision data when a `FRED_API_KEY` is available.
- Builds the hybrid daily macro dataset used by the strategy.
- Builds the article-style retail sales splice used by production backtests: discontinued `RSALES` history chained into scaled modern `RRSFS`.
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

### `research/`

Research-only scripts and templates. The live dashboard does not import files from this folder. Use it for score sweeps, alternate indicator sets, timing-delay tests, or other experiments that should not change the published site.

### `tests/`

Small dependency-free smoke tests. `tests/test_published_contract.py` checks that the published strategy list and default strategy contract have not changed accidentally.

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
- Add research-only strategy variants to `research/`.
- Add visible strategy variants to `published_strategies.py`.
- Add presentation changes to `dashboard.py`.
- Keep CAPE country rotation helpers in their own project unless a helper is truly generic enough to copy into a shared package later.
