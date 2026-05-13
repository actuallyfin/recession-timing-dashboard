from __future__ import annotations

from pathlib import Path

import pandas as pd

from dashboard import build_variant_result
from published_strategies import strategy_variant_specs
from strategy import build_strategy


OUTPUT = Path(__file__).resolve().parents[1] / "notes" / "research_template_output.csv"


def experimental_specs() -> list[dict[str, object]]:
    """Define research-only strategy specs here."""
    base = strategy_variant_specs()[0]
    return [
        base,
        {
            "key": "research_unrate_only",
            "label": "Research: UNRATE Only",
            "description": "Research-only test using the unemployment trend signal by itself.",
            "scores": {"unemployment": 1.0},
            "trigger_score": 1.0,
        },
    ]


def main() -> None:
    result = build_strategy(refresh=False)
    rows = []
    for spec in experimental_specs():
        variant = build_variant_result(result, spec, next_update_dates={})
        row = variant["stats"].iloc[0].copy()
        row["strategy_key"] = spec["key"]
        row["strategy_label"] = spec["label"]
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUTPUT, index=False)
    print(OUTPUT)


if __name__ == "__main__":
    main()
