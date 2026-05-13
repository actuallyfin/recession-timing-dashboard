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

The remaining published variants are the Philosophical Economics GTT comparison strategies. They should stay in `published_strategies.py` unless the live site is intentionally being changed.

## Research-Only Area

Use `research/` for experiments that should not affect the published dashboard. Research scripts can import shared helpers and save results into `notes/`, but the live site does not import files from `research/`.

When a research variation should become part of the site, promote it deliberately by editing `published_strategies.py` and running the smoke test.

## Smoke Test

Run this before and after strategy refactors:

```powershell
python tests/test_published_contract.py
```

The test checks the default published strategy, its scores, and the expected published strategy keys.
