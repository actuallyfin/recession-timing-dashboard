# Research Workspace

Use this folder for one-off backtests, score sweeps, timing delays, alternate indicator sets, and prototype strategy definitions.

Research scripts may import shared project code such as `strategy.py`, `data_loader.py`, `market_data.py`, and `published_strategies.py`, but they should not change the published dashboard unless the goal is explicitly to update the live site.

Recommended pattern:

1. Define experimental strategy specs inside a research script.
2. Reuse `strategy.build_strategy()` to get the common data and benchmark calculations.
3. Save exploratory results into `notes/` when they become decision-useful.
4. Promote an experiment into `published_strategies.py` only after deciding it belongs on the live dashboard.

The live site does not import files from this folder.
