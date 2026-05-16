# Recession Timing Dashboard

Static Python rebuild of the spreadsheet model. This is a separate project folder:

- `data/raw/`: downloaded source data cache for this dashboard only
- `output/`: generated dashboard and CSV snapshots
- `config.py`: indicator rules and timing trigger settings

For a fuller map of how the scripts work together, see `docs/project_guide.md`.
For the live-site boundaries that research work should avoid changing by
accident, see `docs/current_site_contract.md`.

## Strategy

1. Buy and hold by default.
2. Economic timing turns on when tripped indicators sum to the configured trigger score.
3. When timing is on, hold the SPY ETF/proxy total-return series only when it is above the selected trend rule.
4. The published page lets the reader switch between a daily 200-day SMA rule and a monthly 10-month moving-average rule.
5. Compare against the matching moving-average strategy that is always active and against buy-and-hold.

The default ActuallyFinance GTT strategy excludes employment growth from scoring,
keeps Unemployment Rate Trend at `signal_score=2.0`, and counts retail sales,
industrial production, real income, and housing starts at `signal_score=1.0`.
Timing turns on when the selected indicator scores reach
`TIMING_ON_TRIGGER_SCORE=2.0`.
To match the Philosophical Economics article definitions, employment growth is
calculated as `PAYEMS / CLF16OV` year-over-year and housing-start growth is
calculated as `HOUST / CLF16OV` year-over-year. Real personal income remains
ordinary `RPI` year-over-year.
Retail sales uses the article-style real retail sales splice for production
backtests: discontinued FRED `RSALES` through its history, then scaled modern
`RRSFS` thereafter. This makes retail sales available for the full post-1960
dashboard window while preserving the modern RRSFS-based current signal.
To test "1+ trigger," set `TIMING_ON_TRIGGER_SCORE=1.0`; for "3+ triggers,"
set it to `3.0`. To make an indicator count double or half, edit that
indicator's `signal_score` or the published strategy score map in
`published_strategies.py`. For research-only tests, prefer adding a script under
`research/` instead of editing the live dashboard strategy definitions.

## Run

```powershell
& 'C:\Users\bfinl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\dashboard.py --refresh
```

The dashboard is written to `output/index.html`, with supporting CSV snapshots in the same folder. The performance summary follows the same terminology as the country-CAPE backtest page: Start, End, CAGR, Vol, Sharpe, Sortino, Max DD, and Avg % Invested. The growth chart shows the value of an initial $10,000 investment.

Cash/risk-free treatment follows the country-CAPE backtest convention: out-of-market capital earns a cash proxy, and Sharpe is calculated from daily excess returns over that same cash series. BIL adjusted close is used after inception; before BIL exists, a synthetic daily cash level is built from FRED `TB3MS`. Before TB3MS point-in-time vintages are available, final revised TB3MS values are used with an approximate reporting lag.

Macro timing signals are structured to use FRED real-time revision events (`output_type=3`) when available. Before a FRED series has available vintage history, the model uses final revised values with an approximate one-month reporting lag. For labor-force-adjusted ratios, the numerator uses the same hybrid/revision-aware event history as the other indicators, while `CLF16OV` uses initial-release observations as the denominator to avoid a large and slow denominator revision dependency. Indicators do not contribute before their own series has enough history for the configured transform, so `RRSFS` is not used before it has enough history to calculate YoY growth.

The equity series is stitched to extend the backtest to 1960:

- 1960 through 1987: synthetic daily S&P 500 total-return proxy. Daily S&P 500 price returns are adjusted to match published annual S&P 500 total returns, then reduced by an inception-era SPY expense assumption.
- 1988 until SPY starts: Yahoo `^SP500TR` daily S&P 500 total-return index.
- SPY inception onward: adjusted SPY prices as a dividends-reinvested proxy.

The default 200-day mode keeps the existing daily return calculation and writes `output/daily_strategy.csv` plus `output/monthly_signal.csv`. The 10-month mode uses month-end SPY ETF/proxy observations, a 10-month moving average of month-end prices, and a one-month-lagged position change for monthly returns; it writes `output/monthly_signal_10m.csv` and `output/performance_summary_10m.csv`. `output/strategy_variants.json` contains both mode payloads for the strategy dropdown and chart controls.

Each backtest starts only after the equity proxy has enough history for the selected moving average.

For current FRED macro data, set a `FRED_API_KEY` environment variable before running. Without it, the loader attempts FRED's no-key graph CSV endpoint, which may be slower or blocked by the network.

## Publish

This repo is set up for GitHub Pages through GitHub Actions:

1. Create a new GitHub repository.
2. Add a repository secret named `FRED_API_KEY`.
3. In the repo settings, set Pages to deploy from GitHub Actions.
4. Push the `main` branch.

The workflow in `.github/workflows/deploy-pages.yml` rebuilds the dashboard, uploads the generated `output/` directory as the Pages artifact, and deploys it. It runs on pushes to `main`, manual dispatch, and weekday scheduled refreshes at 13:30 UTC.
