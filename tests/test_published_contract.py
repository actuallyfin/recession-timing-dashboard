from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from published_strategies import strategy_variant_specs


EXPECTED_KEYS = [
    "actuallyfinance_gtt",
    "pe_gtt_1_retail_sales",
    "pe_gtt_2_industrial_production",
    "pe_gtt_3_retail_or_industrial",
    "pe_gtt_4_employment",
    "pe_gtt_5_income_or_housing",
    "pe_gtt_6_unrate",
]


def test_published_strategy_contract() -> None:
    specs = strategy_variant_specs()
    keys = [spec["key"] for spec in specs]
    assert keys == EXPECTED_KEYS

    default = specs[0]
    assert default["key"] == "actuallyfinance_gtt"
    assert default["label"] == "ActuallyFinance GTT"
    assert default["trigger_score"] == 2.0
    assert default["scores"] == {
        "unemployment": 2.0,
        "retail_sales": 1.0,
        "industrial_production": 1.0,
        "real_income": 1.0,
        "housing_starts": 1.0,
    }
    assert "employment" not in default["scores"]


if __name__ == "__main__":
    test_published_strategy_contract()
    print("published strategy contract ok")
