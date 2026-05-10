# Recession Timing Dashboard

Static Python rebuild of the spreadsheet model. This is a separate project folder:

- `data/raw/`: downloaded source data cache for this dashboard only
- `output/`: generated dashboard and CSV snapshots
- `config.py`: indicator rules and timing trigger settings

## Strategy

1. Buy and hold by default.
2. Economic timing turns on when tripped indicators sum to the configured trigger score.
3. When timing is on, hold the U.S. equity total-return proxy only when it is above its 200-day simple moving average.
4. Compare against a 200-day SMA strategy that is always active and against buy-and-hold.

The default ActuallyFinance GTT strategy excludes employment growth from scoring,
keeps UNRATE at `signal_score=2.0`, and counts retail sales, industrial
production, real income, and housing starts at `signal_score=1.0`. Timing turns
on when the selected indicator scores reach `TIMING_ON_TRIGGER_SCORE=2.0`.
To test "1+ trigger," set `TIMING_ON_TRIGGER_SCORE=1.0`; for "3+ triggers,"
set it to `3.0`. To make an indicator count double or half, edit that
indicator's `signal_score` or the strategy score map in `dashboard.py`.

## Run

```powershell
& 'C:\Users\bfinl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\dashboard.py --refresh
```

The dashboard is written to `output/index.html`, with supporting CSV snapshots in the same folder. The performance summary follows the same terminology as the country-CAPE backtest page: Start, End, CAGR, Vol, Sharpe, Max DD, and Avg % Invested. The growth chart shows the value of an initial $10,000 investment.

Cash/risk-free treatment follows the country-CAPE backtest convention: out-of-market capital earns a cash proxy, and Sharpe is calculated from daily excess returns over that same cash series. BIL adjusted close is used after inception; before BIL exists, a synthetic daily cash level is built from FRED `TB3MS`. Before TB3MS point-in-time vintages are available, final revised TB3MS values are used with an approximate reporting lag.

Macro timing signals are structured to use FRED real-time revision events (`output_type=3`) when available. Before a FRED series has available vintage history, the model uses final revised values with an approximate one-month reporting lag. Indicators do not contribute before their own series has enough history for the configured transform, so `RRSFS` is not used before it has enough history to calculate YoY growth.

The equity series is stitched to extend the backtest to 1960:

- 1960 through 1987: synthetic daily S&P 500 total-return proxy. Daily S&P 500 price returns are adjusted to match published annual S&P 500 total returns, then reduced by an inception-era SPY expense assumption.
- 1988 until SPY starts: Yahoo `^SP500TR` daily S&P 500 total-return index.
- SPY inception onward: adjusted SPY prices as a dividends-reinvested proxy.

The backtest starts only after the equity proxy has enough history for a valid 200-day SMA.

For current FRED macro data, set a `FRED_API_KEY` environment variable before running. Without it, the loader attempts FRED's no-key graph CSV endpoint, which may be slower or blocked by the network.

## Publish

This repo is set up for GitHub Pages through GitHub Actions:

1. Create a new GitHub repository.
2. Add a repository secret named `FRED_API_KEY`.
3. In the repo settings, set Pages to deploy from GitHub Actions.
4. Push the `main` branch.

The workflow in `.github/workflows/deploy-pages.yml` rebuilds the dashboard, uploads the generated `output/` directory as the Pages artifact, and deploys it. It runs on pushes to `main`, manual dispatch, and weekday scheduled refreshes at 13:30 UTC.
