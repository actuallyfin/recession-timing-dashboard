from __future__ import annotations

from config import INDICATORS, TIMING_ON_TRIGGER_SCORE


def strategy_variant_specs() -> list[dict[str, object]]:
    """Return the strategy variants used by the published dashboard."""
    actuallyfinance_scores = {
        rule.key: rule.signal_score
        for rule in INDICATORS
        if rule.key != "employment"
    }
    return [
        {
            "key": "actuallyfinance_gtt",
            "label": "ActuallyFinance GTT",
            "description": "Score-based economic gate. Unemployment Rate Trend counts as 2; retail sales, industrial production, real income, and housing starts count as 1; timing turns on at score 2.",
            "scores": actuallyfinance_scores,
            "trigger_score": TIMING_ON_TRIGGER_SCORE,
        },
        {
            "key": "pe_gtt_1_retail_sales",
            "label": "Philosophical Economics GTT #1: Retail Sales",
            "description": "Timing turns on when real retail sales YoY growth is below 0%.",
            "scores": {"retail_sales": 1.0},
            "trigger_score": 1.0,
        },
        {
            "key": "pe_gtt_2_industrial_production",
            "label": "Philosophical Economics GTT #2: Industrial Production",
            "description": "Timing turns on when industrial production YoY growth is below 0%.",
            "scores": {"industrial_production": 1.0},
            "trigger_score": 1.0,
        },
        {
            "key": "pe_gtt_3_retail_or_industrial",
            "label": "Philosophical Economics GTT #3: Retail Sales or Industrial Production",
            "description": "Timing turns on when either real retail sales or industrial production YoY growth is below 0%.",
            "scores": {"retail_sales": 1.0, "industrial_production": 1.0},
            "trigger_score": 1.0,
        },
        {
            "key": "pe_gtt_4_employment",
            "label": "Philosophical Economics GTT #4: Employment Growth",
            "description": "Timing turns on when labor-force-adjusted payroll employment YoY growth is below 0%.",
            "scores": {"employment": 1.0},
            "trigger_score": 1.0,
        },
        {
            "key": "pe_gtt_5_income_or_housing",
            "label": "Philosophical Economics GTT #5: Real Income or Housing Starts",
            "description": "Timing turns on when real personal income YoY growth is below 3% or labor-force-adjusted housing starts YoY growth is below -10%.",
            "scores": {"real_income": 1.0, "housing_starts": 1.0},
            "trigger_score": 1.0,
        },
        {
            "key": "pe_gtt_6_unrate",
            "label": "Philosophical Economics GTT #6: Unemployment Rate Trend",
            "description": "Timing turns on when the unemployment rate is above its 12-month average.",
            "scores": {"unemployment": 1.0},
            "trigger_score": 1.0,
        },
    ]
