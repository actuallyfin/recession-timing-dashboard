from __future__ import annotations

from dataclasses import dataclass


START_DATE = "1960-01-01"
INITIAL_CAPITAL = 1.0
INITIAL_INVESTMENT = 10_000
TRADING_DAYS_PER_YEAR = 252
SPY_FIRST_TRADING_DATE = "1993-01-29"
SPY_INCEPTION_EXPENSE_RATIO = 0.001845


@dataclass(frozen=True)
class IndicatorRule:
    key: str
    name: str
    fred_series: str
    transform: str
    threshold: float
    direction: str
    signal_score: float
    display: str
    source_url: str


INDICATORS: tuple[IndicatorRule, ...] = (
    IndicatorRule(
        key="unemployment",
        name="Unemployment Rate Trend",
        fred_series="UNRATE",
        transform="above_12m_sma",
        threshold=0.0,
        direction="above",
        signal_score=2.0,
        display="UNRATE above its 12-month average",
        source_url="https://fred.stlouisfed.org/series/UNRATE",
    ),
    IndicatorRule(
        key="retail_sales",
        name="Real Retail Sales Growth",
        fred_series="RRSFS",
        transform="yoy",
        threshold=0.0,
        direction="below",
        signal_score=1.0,
        display="YoY growth below 0%",
        source_url="https://fred.stlouisfed.org/series/RRSFS",
    ),
    IndicatorRule(
        key="industrial_production",
        name="Industrial Production Growth",
        fred_series="INDPRO",
        transform="yoy",
        threshold=0.0,
        direction="below",
        signal_score=1.0,
        display="YoY growth below 0%",
        source_url="https://fred.stlouisfed.org/series/INDPRO",
    ),
    IndicatorRule(
        key="employment",
        name="Employment Growth",
        fred_series="PAYEMS",
        transform="yoy",
        threshold=0.0,
        direction="below",
        signal_score=1.0,
        display="YoY growth below 0%",
        source_url="https://fred.stlouisfed.org/series/PAYEMS",
    ),
    IndicatorRule(
        key="real_income",
        name="Real Personal Income Growth",
        fred_series="RPI",
        transform="yoy",
        threshold=0.03,
        direction="below",
        signal_score=1.0,
        display="YoY growth below 3%",
        source_url="https://fred.stlouisfed.org/series/RPI",
    ),
    IndicatorRule(
        key="housing_starts",
        name="Housing Starts Growth",
        fred_series="HOUST",
        transform="yoy",
        threshold=-0.10,
        direction="below",
        signal_score=1.0,
        display="YoY growth below -10%",
        source_url="https://fred.stlouisfed.org/series/HOUST",
    ),
)


# The economic timing gate is score based.
#
# Default behavior matches "2+ indicators trip": every indicator has a
# signal_score of 1.0 and timing turns on when the score reaches 2.0.
#
# Examples:
# - 1+ trigger: set TIMING_ON_TRIGGER_SCORE = 1.0
# - 3+ triggers: set TIMING_ON_TRIGGER_SCORE = 3.0
# - one indicator counts double: set its signal_score = 2.0
# - one indicator counts half: set its signal_score = 0.5
TIMING_ON_TRIGGER_SCORE = 2.0
