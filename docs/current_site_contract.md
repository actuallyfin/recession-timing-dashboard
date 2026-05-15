# Current Site Contract

This document marks which files power the live dashboard and which files are safe places for research-only experiments.

## Live Dashboard Files

Changing these files can change the published site or its backtest results:

- `dashboard.py`: renders the static dashboard and writes `output/`.
- `published_strategies.py`: defines the strategies shown in the dropdown and performance table.
- `strategy.py`: calculates signals, returns, benchmarks, and performance metrics.
- `data_loader.py`: builds the project-specific FRED, SPY ETF/proxy, and cash datasets.
- `market_data.py`: shared data download, Yahoo price, caching, and index-linking helpers.
- `config.py`: indicator definitions, FRED series IDs, thresholds, scores, dates, and constants.
- `.github/workflows/deploy-pages.yml`: daily and manual GitHub Pages build/deploy workflow.

## Published Strategy Contract

The first strategy in `published_strategies.strategy_variant_specs()` is the default live dashboard selection:

- Key: `actuallyfinance_gtt`
- Label: `ActuallyFinance GTT`
- Scores: unemployment `2.0`, retail sales `1.0`, industrial production `1.0`, real income `1.0`, housing starts `1.0`
- Employment growth is visible on the page, but excluded from the ActuallyFinance GTT score.
- Trigger score: `2.0`
- Article-matching macro definitions are used for the published comparison variants where applicable: retail sales is discontinued `RSALES` chained into scaled modern `RRSFS`, employment growth is `PAYEMS / CLF16OV` year-over-year, and housing-start growth is `HOUST / CLF16OV` year-over-year. Real personal income remains ordinary `RPI` year-over-year.

The remaining published variants are the Philosophical Economics GTT comparison strategies. They should stay in `published_strategies.py` unless the live site is intentionally being changed.

## Published Trend Rule Contract

The live page has a trend-rule selector that is separate from the strategy selector:

- `200d`: the default mode. It uses daily returns, a 200-day SMA trend rule, and keeps the existing dashboard presentation unchanged on first load.
- `10m`: the monthly mode. It uses completed month-end observations, a 10-month moving average of month-end prices, monthly compounded cash returns, and a position shift so the selected month-end signal applies to the following month.

`dashboard.py` writes separate CSV snapshots for the two modes: `daily_strategy.csv` and `monthly_signal.csv` for the 200-day default, plus `monthly_signal_10m.csv` and `performance_summary_10m.csv` for the monthly mode. `strategy_variants.json` is nested by trend mode and powers the browser-side selector.

## Research-Only Area

Use `research/` for experiments that should not affect the published dashboard. Research scripts can import shared helpers and save results into `notes/`, but the live site does not import files from `research/`.

When a research variation should become part of the site, promote it deliberately by editing `published_strategies.py` and running the smoke test.

## Smoke Test

Run this before and after strategy refactors:

```powershell
python tests/test_published_contract.py
```

The test checks the default published strategy, its scores, and the expected published strategy keys.
