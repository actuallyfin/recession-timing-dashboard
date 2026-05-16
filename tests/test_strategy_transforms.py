from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy import _apply_transform


def test_yoy_uses_exact_calendar_year_when_available() -> None:
    series = pd.Series(
        [100.0, 130.0, 120.0],
        index=pd.to_datetime(["2025-09-01", "2025-10-01", "2026-10-01"]),
    )

    yoy = _apply_transform(series, "yoy")

    assert yoy.loc[pd.Timestamp("2026-10-01")] == (120.0 / 130.0) - 1


def test_yoy_interpolates_isolated_missing_year_ago_month() -> None:
    series = pd.Series(
        [100.0, 140.0, 120.0],
        index=pd.to_datetime(["2025-09-01", "2025-11-01", "2026-10-01"]),
    )

    yoy = _apply_transform(series, "yoy")

    assert yoy.loc[pd.Timestamp("2026-10-01")] == (120.0 / 120.0) - 1


def test_yoy_stays_missing_when_interpolation_neighbors_are_missing() -> None:
    series = pd.Series(
        [100.0, 120.0],
        index=pd.to_datetime(["2025-09-01", "2026-10-01"]),
    )

    yoy = _apply_transform(series, "yoy")

    assert pd.isna(yoy.loc[pd.Timestamp("2026-10-01")])


if __name__ == "__main__":
    test_yoy_uses_exact_calendar_year_when_available()
    test_yoy_interpolates_isolated_missing_year_ago_month()
    test_yoy_stays_missing_when_interpolation_neighbors_are_missing()
    print("strategy transform tests ok")
