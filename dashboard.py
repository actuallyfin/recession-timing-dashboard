from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

from config import INDICATORS
from data_loader import next_fred_release_date
from market_data import source_history_url
from published_strategies import strategy_variant_specs
from strategy import _performance_stats, build_strategy


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"


COLORS = {
    "ink": "#172026",
    "muted": "#60707c",
    "line": "#d8e0e6",
    "blue": "#2563eb",
    "teal": "#0f766e",
    "amber": "#b7791f",
    "red": "#c2410c",
    "green": "#15803d",
}

def pct(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{value:.{digits}%}"


def num(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{value:,.{digits}f}"


def money(value: float, digits: int = 0) -> str:
    if pd.isna(value):
        return "n/a"
    return f"${value:,.{digits}f}"


def yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def spy_source_url(date_text: object) -> str:
    return source_history_url("SPY", date_text)


def source_date_link(date_text: object) -> str:
    return f'<a href="{html.escape(spy_source_url(date_text))}">{html.escape(str(date_text))}</a>'


def format_indicator_value(value: float) -> str:
    if pd.isna(value):
        return "n/a"
    return pct(value, 1)


def format_reading(row: object) -> str:
    if pd.isna(row.latest_raw_value):
        return "n/a"
    return f"{row.latest_raw_value:.2f}%" if row.key == "unemployment" else pct(row.latest_value, 1)


def format_threshold(row: object) -> str:
    if pd.isna(row.current_threshold):
        return "n/a"
    if row.key == "unemployment":
        return f"{row.current_threshold:.2f}%"
    return pct(row.current_threshold, 1)


def indicator_rule_text(row: object) -> str:
    rule = str(row.rule)
    if row.key == "unemployment" and not pd.isna(row.current_threshold):
        return f"{rule}; current threshold: {row.current_threshold:.2f}%"
    return rule


def format_next_update_date(date: pd.Timestamp | None, is_scheduled: bool) -> str:
    if date is None or pd.isna(date):
        return "n/a"
    prefix = "" if is_scheduled else "Est. "
    return f"{prefix}{pd.Timestamp(date).strftime('%Y-%m-%d')}"


def score_series_for_variant(indicator_trips: pd.DataFrame, scores: dict[str, float]) -> pd.Series:
    score = pd.Series(0.0, index=indicator_trips.index)
    for key, weight in scores.items():
        score = score + indicator_trips[key].astype(float) * float(weight)
    return score


def trip_count_for_variant(indicator_trips: pd.DataFrame, scores: dict[str, float]) -> pd.Series:
    if not scores:
        return pd.Series(0, index=indicator_trips.index)
    return indicator_trips[list(scores)].sum(axis=1).astype(int)


def build_next_update_dates(result: dict[str, object], refresh: bool = False) -> dict[str, str]:
    indicator_values = result["indicator_values"]
    indicator_available_dates = result["indicator_available_dates"]
    latest_indicator_date = indicator_values.dropna(how="all").index[-1]
    latest_available_dates = indicator_available_dates.loc[latest_indicator_date]
    next_updates = {}
    for rule in INDICATORS:
        available_date = latest_available_dates.get(rule.key, pd.NaT)
        date, is_scheduled = next_fred_release_date(rule.fred_series, available_date, refresh=refresh)
        next_updates[rule.key] = format_next_update_date(date, is_scheduled)
    return next_updates


def build_current_rows_for_variant(
    result: dict[str, object],
    spec: dict[str, object],
    next_update_dates: dict[str, str],
) -> pd.DataFrame:
    scores = spec["scores"]
    indicator_values = result["indicator_values"]
    indicator_thresholds = result["indicator_thresholds"]
    indicator_raw_values = result["indicator_raw_values"]
    indicator_observation_dates = result["indicator_observation_dates"]
    indicator_available_dates = result["indicator_available_dates"]
    indicator_trips = result["indicator_trips"]
    latest_indicator_date = indicator_values.dropna(how="all").index[-1]
    latest_values = indicator_values.loc[latest_indicator_date]
    latest_thresholds = indicator_thresholds.loc[latest_indicator_date]
    latest_raw_values = indicator_raw_values.loc[latest_indicator_date]
    latest_observation_dates = indicator_observation_dates.loc[latest_indicator_date]
    latest_available_dates = indicator_available_dates.loc[latest_indicator_date]
    latest_trips = indicator_trips.loc[latest_indicator_date]

    current_rows = []
    for rule in INDICATORS:
        included_score = float(scores.get(rule.key, 0.0))
        tripped = bool(latest_trips.get(rule.key, 0))
        if included_score == 0:
            status_text = "Not used"
            status_class = "neutral"
        elif tripped:
            status_text = "Tripped"
            status_class = "bad"
        else:
            status_text = "Clear"
            status_class = "good"
        observation_date = latest_observation_dates.get(rule.key, pd.NaT)
        available_date = latest_available_dates.get(rule.key, pd.NaT)
        current_rows.append(
            {
                "key": rule.key,
                "name": rule.name,
                "rule": rule.display,
                "signal_score": included_score,
                "latest_raw_value": latest_raw_values.get(rule.key, np.nan),
                "current_threshold": latest_thresholds.get(rule.key, np.nan),
                "data_through": observation_date.strftime("%Y-%m-%d") if pd.notna(observation_date) else "",
                "available_date": available_date.strftime("%Y-%m-%d") if pd.notna(available_date) else "",
                "next_update": next_update_dates.get(rule.key, "n/a"),
                "latest_value": latest_values.get(rule.key, np.nan),
                "tripped": tripped and included_score > 0,
                "score_contribution": included_score if tripped else 0.0,
                "status_text": status_text,
                "status_class": status_class,
                "source_url": rule.source_url,
            }
        )
    return pd.DataFrame(current_rows)


def build_rules_html(spec: dict[str, object]) -> str:
    scores = spec["scores"]
    used_rules = [rule for rule in INDICATORS if rule.key in scores]
    used_list = "\n".join(
        f'<li><a href="{html.escape(rule.source_url)}">{html.escape(rule.name)}</a>; '
        f"score {float(scores[rule.key]):g}.</li>"
        for rule in used_rules
    )
    return f"""
      <p>{html.escape(str(spec["description"]))}</p>
      <ol class="rules">
        <li>Stay invested by default.</li>
        <li>Turn timing on when the selected indicators sum to a score of at least {float(spec["trigger_score"]):g}.</li>
        <li>When timing is on, hold the SPY ETF only when price is above its 200-day simple moving average.</li>
        <li>When timing is off, ignore the SMA rule and remain invested.</li>
      </ol>
      <p class="note">Indicators used by this strategy (links to FRED):</p>
      <ul class="rules">{used_list}</ul>
      <p class="note">Backtest is structured to use FRED real-time revision events when available. Before an indicator's vintage history begins, final revised FRED values are used with an approximate one-month reporting lag; indicators do not contribute before their own series has enough history. The SPY ETF/Proxy uses a synthetic S&P 500 total-return approximation through 1987, the Yahoo ^SP500TR daily total-return index from 1988 until SPY starts, and adjusted SPY prices after inception. The pre-1988 synthetic segment is reduced by an inception-era SPY expense assumption. The historical test begins once the 200-day SMA is available.</p>
    """


def svg_line_chart(
    frame: pd.DataFrame,
    columns: list[str],
    labels: list[str],
    colors: list[str],
    height: int = 320,
    log_y: bool = False,
    y_format: str = "multiple",
) -> str:
    data = frame[columns].dropna(how="all")
    if data.empty:
        return "<svg></svg>"

    width = 980
    pad_left, pad_right, pad_top, pad_bottom = 58, 20, 22, 46
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    x_raw = data.index.map(pd.Timestamp.toordinal).to_numpy(dtype=float)
    x_min, x_max = x_raw.min(), x_raw.max()
    x_span = max(x_max - x_min, 1)

    y_data = data.astype(float)
    if log_y:
        y_data = np.log(y_data.clip(lower=0.0001))
    y_min = float(np.nanmin(y_data.to_numpy()))
    y_max = float(np.nanmax(y_data.to_numpy()))
    y_pad = (y_max - y_min) * 0.08 if y_max > y_min else 1
    y_min -= y_pad
    y_max += y_pad

    def x_pos(date_ord: float) -> float:
        return pad_left + ((date_ord - x_min) / x_span) * plot_w

    def y_pos(value: float) -> float:
        return pad_top + (1 - ((value - y_min) / (y_max - y_min))) * plot_h

    y_ticks = np.linspace(y_min, y_max, 5)
    x_ticks = pd.date_range(data.index.min(), data.index.max(), periods=6)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Line chart">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    for tick in y_ticks:
        y = y_pos(tick)
        display = np.exp(tick) if log_y else tick
        if y_format == "currency":
            label = f"${display / 1000:,.0f}k" if display >= 1000 else f"${display:,.0f}"
        elif y_format == "multiple":
            label = f"{display:.1f}x"
        else:
            label = pct(display, 0)
        parts.append(f'<line x1="{pad_left}" y1="{y:.1f}" x2="{width-pad_right}" y2="{y:.1f}" stroke="{COLORS["line"]}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_left-10}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["muted"]}">{label}</text>')
    for tick in x_ticks:
        x = x_pos(tick.toordinal())
        parts.append(f'<text x="{x:.1f}" y="{height-16}" text-anchor="middle" font-size="11" fill="{COLORS["muted"]}">{tick.year}</text>')

    for col, label, color in zip(columns, labels, colors):
        series = y_data[col].dropna()
        points = " ".join(
            f"{x_pos(idx.toordinal()):.1f},{y_pos(value):.1f}" for idx, value in series.items()
        )
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>')

    legend_x = pad_left
    for label, color in zip(labels, colors):
        safe = html.escape(label)
        parts.append(f'<circle cx="{legend_x}" cy="14" r="4" fill="{color}"/>')
        parts.append(f'<text x="{legend_x+8}" y="18" font-size="12" fill="{COLORS["ink"]}">{safe}</text>')
        legend_x += 165
    parts.append("</svg>")
    return "".join(parts)


def svg_signal_chart(monthly: pd.DataFrame, trigger_score: float, height: int = 260) -> str:
    data = monthly[["signal_score", "timing_on"]].dropna().copy()
    if data.empty:
        return "<svg></svg>"

    width = 980
    pad_left, pad_right, pad_top, pad_bottom = 46, 18, 24, 42
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    x_raw = data.index.map(pd.Timestamp.toordinal).to_numpy(dtype=float)
    x_min, x_max = x_raw.min(), x_raw.max()
    x_span = max(x_max - x_min, 1)
    y_max = max(6.0, float(data["signal_score"].max()), trigger_score)

    def x_pos(date_ord: float) -> float:
        return pad_left + ((date_ord - x_min) / x_span) * plot_w

    def y_pos(value: float) -> float:
        return pad_top + (1 - (value / y_max)) * plot_h

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Timing signal chart">',
        '<rect x="0" y="0" width="980" height="260" fill="#ffffff"/>',
    ]

    on_periods = data[data["timing_on"]]
    for idx in on_periods.index:
        x = x_pos(idx.toordinal())
        parts.append(f'<rect x="{x-2:.1f}" y="{pad_top}" width="4" height="{plot_h}" fill="#fee2e2" opacity="0.75"/>')

    for tick in range(0, int(np.ceil(y_max)) + 1):
        y = y_pos(tick)
        parts.append(f'<line x1="{pad_left}" y1="{y:.1f}" x2="{width-pad_right}" y2="{y:.1f}" stroke="{COLORS["line"]}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_left-10}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["muted"]}">{tick}</text>')

    points = " ".join(
        f"{x_pos(idx.toordinal()):.1f},{y_pos(value):.1f}" for idx, value in data["signal_score"].items()
    )
    threshold_y = y_pos(trigger_score)
    parts.append(f'<line x1="{pad_left}" y1="{threshold_y:.1f}" x2="{width-pad_right}" y2="{threshold_y:.1f}" stroke="{COLORS["red"]}" stroke-width="1.5" stroke-dasharray="5 5"/>')
    parts.append(f'<text x="{width-pad_right-4}" y="{threshold_y-8:.1f}" text-anchor="end" font-size="11" fill="{COLORS["red"]}">timing turns on at score {trigger_score:g}</text>')
    parts.append(f'<polyline points="{points}" fill="none" stroke="{COLORS["amber"]}" stroke-width="2.3" stroke-linejoin="round" stroke-linecap="round"/>')

    x_ticks = pd.date_range(data.index.min(), data.index.max(), periods=6)
    for tick in x_ticks:
        x = x_pos(tick.toordinal())
        parts.append(f'<text x="{x:.1f}" y="{height-14}" text-anchor="middle" font-size="11" fill="{COLORS["muted"]}">{tick.year}</text>')
    parts.append("</svg>")
    return "".join(parts)


def build_variant_result(
    result: dict[str, object],
    spec: dict[str, object],
    next_update_dates: dict[str, str],
) -> dict[str, object]:
    scores = spec["scores"]
    trigger_score = float(spec["trigger_score"])
    daily = result["daily"][
        [
            "Close",
            "cash_return",
            "sma_200",
            "daily_return",
            "trend_above_sma",
            "always_timing_invested",
            "buy_hold_invested",
            "always_timing_return",
            "buy_hold_return",
            "always_timing_equity",
            "buy_hold_equity",
            "always_timing_growth_10k",
            "buy_hold_growth_10k",
        ]
    ].copy()
    indicator_trips = result["indicator_trips"]
    score = score_series_for_variant(indicator_trips, scores)
    trip_count = trip_count_for_variant(indicator_trips, scores)
    timing = pd.DataFrame(
        {
            "trip_count": trip_count,
            "signal_score": score,
            "timing_on": score >= trigger_score,
        }
    )
    timing_daily = timing.reindex(daily.index, method="ffill")
    daily = daily.join(timing_daily)
    daily[["trip_count", "signal_score"]] = daily[["trip_count", "signal_score"]].fillna(0)
    daily["timing_on"] = daily["timing_on"].fillna(False).astype(bool)
    daily["combined_invested"] = (~daily["timing_on"]) | daily["trend_above_sma"]
    combined_position = daily["combined_invested"].shift(1).fillna(True).astype(bool)
    daily["combined_return"] = daily["daily_return"].where(combined_position, daily["cash_return"])
    daily["combined_equity"] = (1 + daily["combined_return"]).cumprod()
    daily["combined_growth_10k"] = 10_000 * daily["combined_equity"]

    monthly = daily.resample("ME").last()
    monthly = monthly[
        [
            "Close",
            "sma_200",
            "trend_above_sma",
            "trip_count",
            "timing_on",
            "combined_invested",
            "always_timing_invested",
            "signal_score",
            "combined_equity",
            "always_timing_equity",
            "buy_hold_equity",
            "combined_growth_10k",
            "always_timing_growth_10k",
            "buy_hold_growth_10k",
        ]
    ].dropna(subset=["Close"])

    latest_date = daily.dropna(subset=["Close"]).index[-1]
    latest = daily.loc[latest_date]
    latest_indicator_date = result["indicator_values"].dropna(how="all").index[-1]
    summary = {
        "key": spec["key"],
        "label": spec["label"],
        "description": spec["description"],
        "latest_price_date": latest_date.strftime("%Y-%m-%d"),
        "latest_indicator_date": latest_indicator_date.strftime("%Y-%m-%d"),
        "latest_macro_release_date": latest_indicator_date.strftime("%Y-%m-%d"),
        "timing_on": bool(latest["timing_on"]),
        "trend_above_sma": bool(latest["trend_above_sma"]),
        "combined_invested": bool(latest["combined_invested"]),
        "trip_count": int(latest["trip_count"]),
        "indicator_count": len(scores),
        "signal_score": float(latest["signal_score"]),
        "trigger_score": trigger_score,
        "max_score": float(sum(float(value) for value in scores.values())),
        "spy_close": float(latest["Close"]),
        "spy_sma_200": float(latest["sma_200"]) if not pd.isna(latest["sma_200"]) else np.nan,
    }
    stats = pd.DataFrame(
        [
            _performance_stats(daily, "combined", str(spec["label"])),
            _performance_stats(daily, "always_timing", "200D SMA always on"),
            _performance_stats(daily, "buy_hold", "Buy and hold"),
        ]
    )
    current = build_current_rows_for_variant(result, spec, next_update_dates)
    return {
        "spec": spec,
        "daily": daily,
        "monthly": monthly,
        "summary": summary,
        "stats": stats,
        "current_indicators": current,
    }


def render_indicator_rows(current: pd.DataFrame) -> str:
    return "\n".join(
        f"""
        <tr>
          <td data-label="Indicator"><a href="{html.escape(row.source_url)}">{html.escape(row.name)}</a></td>
          <td data-label="Rule">{html.escape(indicator_rule_text(row))}</td>
          <td data-label="Data Through" class="num">{html.escape(row.data_through)}</td>
          <td data-label="Available" class="num">{html.escape(row.available_date)}</td>
          <td data-label="Next Update" class="num">{html.escape(row.next_update)}</td>
          <td data-label="Latest" class="num">{format_reading(row)}</td>
          <td data-label="Threshold" class="num">{format_threshold(row)}</td>
          <td data-label="Score" class="num">{num(row.signal_score, 1)}</td>
          <td data-label="Status"><span class="pill {html.escape(row.status_class)}">{html.escape(row.status_text)}</span></td>
        </tr>
        """
        for row in current.itertuples(index=False)
    )


def build_comparison_stats(variants: list[dict[str, object]]) -> pd.DataFrame:
    rows = []
    for variant in variants:
        row = variant["stats"].iloc[0].copy()
        row["strategy_key"] = variant["summary"]["key"]
        row["row_kind"] = "strategy"
        rows.append(row)

    benchmarks = variants[0]["stats"].iloc[1:].copy()
    benchmark_keys = {
        "200D SMA always on": "benchmark_sma",
        "Buy and hold": "benchmark_buy_hold",
    }
    for _, row in benchmarks.iterrows():
        row = row.copy()
        row["strategy_key"] = benchmark_keys.get(str(row["strategy"]), "benchmark")
        row["row_kind"] = "benchmark"
        rows.append(row)
    return pd.DataFrame(rows)


def render_stat_rows(stats: pd.DataFrame, selected_key: str | None = None) -> str:
    return "\n".join(
        render_stat_row(row, selected_key)
        for row in stats.itertuples(index=False)
    )


def render_stat_row(row: object, selected_key: str | None = None) -> str:
    row_key = html.escape(str(getattr(row, "strategy_key", "")))
    row_kind = html.escape(str(getattr(row, "row_kind", "strategy")))
    row_class = ""
    if row_kind == "strategy":
        row_class = "selected" if row_key == selected_key else "muted"
    elif row_kind == "benchmark":
        row_class = "benchmark"
    class_attr = f' class="{row_class}"' if row_class else ""
    return (
        f"""
        <tr{class_attr} data-strategy-key="{row_key}" data-row-kind="{row_kind}">
          <td data-label="Strategy">{html.escape(row.strategy)}</td>
          <td data-label="Start" class="num">{html.escape(row.start)}</td>
          <td data-label="End" class="num">{source_date_link(row.end)}</td>
          <td data-label="Final Equity" class="num">{money(row.final_equity, 0)}</td>
          <td data-label="CAGR" class="num">{pct(row.cagr, 1)}</td>
          <td data-label="Vol" class="num">{pct(row.vol, 1)}</td>
          <td data-label="Sharpe" class="num">{num(row.sharpe, 2)}</td>
          <td data-label="Sortino" class="num">{num(row.sortino, 2)}</td>
          <td data-label="Max DD" class="num">{pct(row.max_drawdown, 1)}</td>
          <td data-label="Avg % Invested" class="num">{pct(row.avg_pct_invested, 1)}</td>
        </tr>
        """
    )


def render_recent_rows(monthly: pd.DataFrame) -> str:
    recent = monthly.tail(18).iloc[::-1]
    return "\n".join(
        f"""
        <tr>
          <td data-label="Month">{idx.strftime('%Y-%m')}</td>
          <td data-label="Signal Score" class="num">{num(row.signal_score, 1)}</td>
          <td data-label="Timing On">{yes_no(bool(row.timing_on))}</td>
          <td data-label="Position">{'Invested' if row.combined_invested else 'Defensive'}</td>
          <td data-label="SPY ETF" class="num">{num(row.Close, 2)}</td>
          <td data-label="200D SMA" class="num">{num(row.sma_200, 2)}</td>
        </tr>
        """
        for idx, row in recent.iterrows()
    )


def render_variant_payload(variant: dict[str, object]) -> dict[str, object]:
    summary = variant["summary"]
    monthly = variant["monthly"]
    action = current_action(summary)
    return {
        "key": summary["key"],
        "label": summary["label"],
        "description": summary["description"],
        "action": action,
        "summary": {
            "timingOn": summary["timing_on"],
            "combinedInvested": summary["combined_invested"],
            "trendAboveSma": summary["trend_above_sma"],
            "tripCount": summary["trip_count"],
            "indicatorCount": summary["indicator_count"],
            "signalScore": num(summary["signal_score"], 1),
            "triggerScore": num(summary["trigger_score"], 1),
            "latestPriceDate": summary["latest_price_date"],
            "priceSourceUrl": spy_source_url(summary["latest_price_date"]),
            "latestMacroReleaseDate": summary["latest_macro_release_date"],
            "spyClose": num(summary["spy_close"], 2),
            "spySma200": num(summary["spy_sma_200"], 2),
        },
        "indicatorRows": render_indicator_rows(variant["current_indicators"]),
        "recentRows": render_recent_rows(monthly),
        "rulesHtml": build_rules_html(variant["spec"]),
        "equityChart": svg_line_chart(
            monthly,
            ["combined_growth_10k", "always_timing_growth_10k", "buy_hold_growth_10k"],
            [str(summary["label"]), "SMA always on", "Buy and hold"],
            [COLORS["teal"], COLORS["blue"], COLORS["muted"]],
            log_y=True,
            y_format="currency",
        ),
        "signalChart": svg_signal_chart(monthly, float(summary["trigger_score"])),
    }


SHORT_CHART_LABELS = {
    "actuallyfinance_gtt": "AF GTT",
    "pe_gtt_1_retail_sales": "Retail",
    "pe_gtt_2_industrial_production": "Ind Prod",
    "pe_gtt_3_retail_or_industrial": "Retail/IP",
    "pe_gtt_4_employment": "Jobs",
    "pe_gtt_5_income_or_housing": "Income/Housing",
    "pe_gtt_6_unrate": "UNRATE",
    "benchmark_sma": "200D SMA",
    "benchmark_buy_hold": "Buy & Hold",
}


CHART_COLORS = {
    "actuallyfinance_gtt": "#0f766e",
    "pe_gtt_1_retail_sales": "#2563eb",
    "pe_gtt_2_industrial_production": "#b7791f",
    "pe_gtt_3_retail_or_industrial": "#7c3aed",
    "pe_gtt_4_employment": "#dc2626",
    "pe_gtt_5_income_or_housing": "#15803d",
    "pe_gtt_6_unrate": "#0891b2",
    "benchmark_sma": "#475569",
    "benchmark_buy_hold": "#111827",
}


def growth_chart_series(variants: list[dict[str, object]]) -> dict[str, pd.Series]:
    series = {
        str(variant["summary"]["key"]): variant["monthly"]["combined_growth_10k"]
        for variant in variants
    }
    default_monthly = variants[0]["monthly"]
    series["benchmark_sma"] = default_monthly["always_timing_growth_10k"]
    series["benchmark_buy_hold"] = default_monthly["buy_hold_growth_10k"]
    return series


def svg_multi_growth_chart(series_map: dict[str, pd.Series], default_checked: set[str]) -> str:
    frame = pd.DataFrame(series_map).dropna(how="all")
    if frame.empty:
        return "<svg></svg>"

    width, height = 980, 320
    pad_left, pad_right, pad_top, pad_bottom = 58, 20, 22, 46
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    x_raw = frame.index.map(pd.Timestamp.toordinal).to_numpy(dtype=float)
    x_min, x_max = x_raw.min(), x_raw.max()
    x_span = max(x_max - x_min, 1)
    y_data = np.log(frame.astype(float).clip(lower=0.0001))
    y_min = float(np.nanmin(y_data.to_numpy()))
    y_max = float(np.nanmax(y_data.to_numpy()))
    y_pad = (y_max - y_min) * 0.08 if y_max > y_min else 1
    y_min -= y_pad
    y_max += y_pad

    def x_pos(date_ord: float) -> float:
        return pad_left + ((date_ord - x_min) / x_span) * plot_w

    def y_pos(value: float) -> float:
        return pad_top + (1 - ((value - y_min) / (y_max - y_min))) * plot_h

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Growth of 10000 chart">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    for tick in np.linspace(y_min, y_max, 5):
        y = y_pos(tick)
        display = np.exp(tick)
        label = f"${display / 1000:,.0f}k" if display >= 1000 else f"${display:,.0f}"
        parts.append(f'<line x1="{pad_left}" y1="{y:.1f}" x2="{width-pad_right}" y2="{y:.1f}" stroke="{COLORS["line"]}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_left-10}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="{COLORS["muted"]}">{label}</text>')
    for tick in pd.date_range(frame.index.min(), frame.index.max(), periods=6):
        x = x_pos(tick.toordinal())
        parts.append(f'<text x="{x:.1f}" y="{height-16}" text-anchor="middle" font-size="11" fill="{COLORS["muted"]}">{tick.year}</text>')

    for key, values in y_data.items():
        points = " ".join(
            f"{x_pos(idx.toordinal()):.1f},{y_pos(value):.1f}"
            for idx, value in values.dropna().items()
        )
        display = "" if key in default_checked else "none"
        parts.append(
            f'<polyline class="growth-line" data-series="{html.escape(key)}" points="{points}" '
            f'fill="none" stroke="{CHART_COLORS[key]}" stroke-width="2.3" '
            f'stroke-linejoin="round" stroke-linecap="round" style="display:{display}"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


def render_growth_controls(series_keys: list[str], default_checked: set[str]) -> str:
    controls = []
    for key in series_keys:
        checked = " checked" if key in default_checked else ""
        controls.append(
            f"""
            <label class="chart-toggle">
              <input type="checkbox" data-series="{html.escape(key)}"{checked}>
              <span class="swatch" style="background:{CHART_COLORS[key]}"></span>
              <span>{html.escape(SHORT_CHART_LABELS[key])}</span>
            </label>
            """
        )
    return "\n".join(controls)


def build_dashboard(refresh: bool = False) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = build_strategy(refresh=refresh)

    variant_specs = strategy_variant_specs()
    next_update_dates = build_next_update_dates(result, refresh=refresh)
    variants = [build_variant_result(result, spec, next_update_dates) for spec in variant_specs]
    default_variant = variants[0]
    comparison_stats = build_comparison_stats(variants)
    default_payload = render_variant_payload(default_variant)
    variant_payloads = {variant["summary"]["key"]: render_variant_payload(variant) for variant in variants}
    default_chart_keys = {"actuallyfinance_gtt"}
    chart_series = growth_chart_series(variants)
    chart_keys = [str(spec["key"]) for spec in variant_specs] + ["benchmark_sma", "benchmark_buy_hold"]
    growth_chart = svg_multi_growth_chart(chart_series, default_chart_keys)
    growth_controls = render_growth_controls(chart_keys, default_chart_keys)

    default_variant["daily"].to_csv(OUTPUT_DIR / "daily_strategy.csv")
    default_variant["monthly"].to_csv(OUTPUT_DIR / "monthly_signal.csv")
    default_variant["current_indicators"].to_csv(OUTPUT_DIR / "current_indicators.csv", index=False)
    comparison_stats.to_csv(OUTPUT_DIR / "performance_summary.csv", index=False)
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(default_variant["summary"], indent=2), encoding="utf-8")
    all_variant_stats = []
    for variant in variants:
        stats = variant["stats"].copy()
        stats.insert(0, "variant_key", variant["summary"]["key"])
        stats.insert(1, "variant_label", variant["summary"]["label"])
        all_variant_stats.append(stats)
    pd.concat(all_variant_stats, ignore_index=True).to_csv(
        OUTPUT_DIR / "strategy_variant_performance.csv", index=False
    )

    json_payload = {
        key: {
            "label": value["label"],
            "description": value["description"],
            "summary": value["summary"],
        }
        for key, value in variant_payloads.items()
    }
    (OUTPUT_DIR / "strategy_variants.json").write_text(
        json.dumps(json_payload, indent=2), encoding="utf-8"
    )

    html_text = render_html(
        variant_specs,
        variant_payloads,
        default_payload,
        growth_chart,
        growth_controls,
        render_stat_rows(comparison_stats, str(default_variant["summary"]["key"])),
    )
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


def current_action(summary: dict[str, object]) -> dict[str, str]:
    if not summary["timing_on"]:
        return {
            "headline": "Timing is OFF",
            "detail": f"Strategy remains invested because the economic signal score is below {float(summary['trigger_score']):g}.",
            "class": "ok",
        }
    if summary["trend_above_sma"]:
        return {
            "headline": "Timing is ON, trend is positive",
            "detail": "Strategy remains invested while the SPY ETF is above its 200-day moving average.",
            "class": "watch",
        }
    return {
        "headline": "Timing is ON, trend is negative",
        "detail": "Strategy is defensive because the SPY ETF is below its 200-day moving average.",
        "class": "risk",
    }


def render_html(
    summary: dict[str, object],
    action: dict[str, str],
    current: pd.DataFrame,
    stats: pd.DataFrame,
    monthly: pd.DataFrame,
    equity_chart: str,
    signal_chart: str,
) -> str:
    indicator_rows = "\n".join(
        f"""
        <tr>
          <td><a href="{html.escape(row.source_url)}">{html.escape(row.name)}</a></td>
          <td>{html.escape(indicator_rule_text(row))}</td>
          <td class="num">{html.escape(row.data_through)}</td>
          <td class="num">{html.escape(row.available_date)}</td>
          <td class="num">{html.escape(row.next_update)}</td>
          <td class="num">{format_reading(row)}</td>
          <td class="num">{format_threshold(row)}</td>
          <td class="num">{num(row.signal_score, 1)}</td>
          <td><span class="pill {'bad' if row.tripped else 'good'}">{'Tripped' if row.tripped else 'Clear'}</span></td>
        </tr>
        """
        for row in current.itertuples(index=False)
    )

    stat_rows = "\n".join(
        f"""
        <tr>
          <td>{html.escape(row.strategy)}</td>
          <td class="num">{html.escape(row.start)}</td>
          <td class="num">{html.escape(row.end)}</td>
          <td class="num">{money(row.final_equity, 0)}</td>
          <td class="num">{pct(row.cagr, 1)}</td>
          <td class="num">{pct(row.vol, 1)}</td>
          <td class="num">{num(row.sharpe, 2)}</td>
          <td class="num">{pct(row.max_drawdown, 1)}</td>
          <td class="num">{pct(row.avg_pct_invested, 1)}</td>
        </tr>
        """
        for row in stats.itertuples(index=False)
    )

    recent = monthly.tail(18).iloc[::-1]
    recent_rows = "\n".join(
        f"""
        <tr>
          <td>{idx.strftime('%Y-%m')}</td>
          <td class="num">{num(row.signal_score, 1)}</td>
          <td>{yes_no(bool(row.timing_on))}</td>
          <td>{'Invested' if row.combined_invested else 'Defensive'}</td>
          <td class="num">{num(row.Close, 2)}</td>
          <td class="num">{num(row.sma_200, 2)}</td>
        </tr>
        """
        for idx, row in recent.iterrows()
    )

    rules = "\n".join(
        f"<li>{html.escape(rule.name)}: {html.escape(rule.display)}; score {rule.signal_score:g}.</li>"
        for rule in INDICATORS
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Recession Timing Dashboard</title>
  <style>
    :root {{
      --ink: {COLORS["ink"]};
      --muted: {COLORS["muted"]};
      --line: {COLORS["line"]};
      --blue: {COLORS["blue"]};
      --teal: {COLORS["teal"]};
      --amber: {COLORS["amber"]};
      --red: {COLORS["red"]};
      --green: {COLORS["green"]};
      --bg: #f6f8fa;
      --panel: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
      letter-spacing: 0;
    }}
    header {{
      background: #ffffff;
      border-bottom: 1px solid var(--line);
    }}
    .wrap {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 30px;
      line-height: 1.1;
      font-weight: 760;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 18px;
      line-height: 1.2;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    .status {{
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) repeat(4, minmax(140px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .metric, section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .metric {{
      padding: 16px;
      min-height: 104px;
    }}
    .metric.primary {{
      border-color: {'#fed7aa' if action["class"] == 'watch' else '#fecaca' if action["class"] == 'risk' else '#bbf7d0'};
      background: {'#fff7ed' if action["class"] == 'watch' else '#fff1f2' if action["class"] == 'risk' else '#f0fdf4'};
    }}
    .label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      font-weight: 700;
    }}
    .value {{
      margin-top: 8px;
      font-size: 24px;
      line-height: 1.15;
      font-weight: 760;
      overflow-wrap: anywhere;
    }}
    .sub {{
      margin-top: 7px;
      color: var(--muted);
      font-size: 13px;
    }}
    main.wrap {{
      display: grid;
      gap: 18px;
    }}
    section {{
      padding: 18px;
      overflow: hidden;
    }}
    .table-scroll {{
      width: 100%;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }}
    .chart {{
      width: 100%;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    .table-scroll table {{
      min-width: 1080px;
    }}
    .current-indicators table {{
      table-layout: auto;
      font-size: 12.5px;
    }}
    .current-indicators th, .current-indicators td {{
      padding: 8px 6px;
    }}
    .current-indicators td:nth-child(2) {{
      min-width: 190px;
      white-space: normal;
    }}
    .current-indicators th:nth-child(3),
    .current-indicators th:nth-child(4),
    .current-indicators th:nth-child(5),
    .current-indicators td:nth-child(3),
    .current-indicators td:nth-child(4),
    .current-indicators td:nth-child(5) {{
      white-space: nowrap;
    }}
    .current-indicators .pill {{
      min-width: 58px;
    }}
    th, td {{
      padding: 10px 9px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: middle;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      font-weight: 720;
    }}
    #stat-rows tr.muted {{
      color: #8a94a6;
    }}
    #stat-rows tr.muted a {{
      color: #8a94a6;
    }}
    #stat-rows tr.selected {{
      color: var(--ink);
      font-weight: 620;
    }}
    #stat-rows tr.benchmark {{
      color: var(--ink);
    }}
    .num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    a {{
      color: var(--blue);
      text-decoration: none;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-width: 68px;
      justify-content: center;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
      font-weight: 720;
    }}
    .pill.good {{ background: #dcfce7; color: #166534; }}
    .pill.bad {{ background: #ffedd5; color: #9a3412; }}
    .rules {{
      margin: 0;
      padding-left: 20px;
      color: var(--ink);
      line-height: 1.55;
    }}
    .note {{
      margin-top: 12px;
      font-size: 13px;
      color: var(--muted);
    }}
    @media (max-width: 900px) {{
      .status {{
        grid-template-columns: 1fr;
      }}
      .wrap {{
        padding: 16px;
      }}
      h1 {{
        font-size: 24px;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <h1>Recession Timing Dashboard</h1>
      <p>This dashboard provides the current inputs to a timing strategy inspired by Philosophical Economics <a href="https://www.philosophicaleconomics.com/2016/01/gtt/">Growth-Trend Timing</a> strategies. Backtested results for the strategy, and variations of the original proposed GTT strategies are also provided below. Economic indicators contribute signal scores based on the latest macro data; when the selected strategy's signal reaches its trigger, the portfolio switches from an S&P 500 buy and hold to a 200-day simple moving average rule.</p>
      <div class="status">
        <div class="metric primary">
          <div class="label">Current Signal</div>
          <div class="value">{html.escape(action["headline"])}</div>
          <div class="sub">{html.escape(action["detail"])}</div>
        </div>
        <div class="metric">
          <div class="label">Tripped Indicators</div>
          <div class="value">{summary["trip_count"]} / {len(INDICATORS)}</div>
          <div class="sub">Score {num(summary["signal_score"], 1)} / trigger {num(summary["trigger_score"], 1)}</div>
        </div>
        <div class="metric">
          <div class="label">Strategy Position</div>
          <div class="value">{'Invested' if summary["combined_invested"] else 'Defensive'}</div>
          <div class="sub">As of {source_date_link(summary["latest_price_date"])}</div>
        </div>
        <div class="metric">
          <div class="label">SPY ETF vs 200D SMA</div>
          <div class="value">{'Above' if summary["trend_above_sma"] else 'Below'}</div>
          <div class="sub">As of {source_date_link(summary["latest_price_date"])}: {num(summary["spy_close"], 2)} vs {num(summary["spy_sma_200"], 2)}</div>
        </div>
        <div class="metric">
          <div class="label">Macro Data Date</div>
          <div class="value">{summary["latest_macro_release_date"]}</div>
          <div class="sub">Latest macro release date in the snapshot</div>
        </div>
      </div>
    </div>
  </header>
  <main class="wrap">
    <section class="current-indicators">
      <h2>Current Economic Indicators</h2>
      <table>
        <thead><tr><th>Indicator</th><th>Rule</th><th class="num">Data Through</th><th class="num">Available</th><th class="num">Next Update</th><th class="num">Latest</th><th class="num">Threshold</th><th class="num">Score</th><th>Status</th></tr></thead>
        <tbody>{indicator_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Performance Summary</h2>
      <div class="table-scroll">
        <table>
          <thead><tr><th>Strategy</th><th class="num">Start</th><th class="num">End</th><th class="num">Final Equity</th><th class="num">CAGR</th><th class="num">Vol</th><th class="num">Sharpe</th><th class="num">Max DD</th><th class="num">Avg % Invested</th></tr></thead>
          <tbody>{stat_rows}</tbody>
        </table>
      </div>
      <p class="note">Stats are computed from daily returns. Idle capital earns the cash proxy return, and Sharpe is calculated on excess returns over that same cash series. Cash uses BIL adjusted close after inception and a synthetic pre-BIL level from FRED TB3MS.</p>
    </section>
    <section>
      <h2>Rules</h2>
      <ol class="rules">
        <li>Stay invested by default.</li>
        <li>Turn timing on when tripped indicators sum to a score of at least {TIMING_ON_TRIGGER_SCORE:g}.</li>
        <li>When timing is on, hold the SPY ETF only when price is above its 200-day simple moving average.</li>
        <li>When timing is off, ignore the SMA rule and remain invested.</li>
      </ol>
      <p class="note">Indicator thresholds used in this first pass:</p>
      <ul class="rules">{rules}</ul>
      <p class="note">Backtest is structured to use FRED real-time revision events when available. Before an indicator's vintage history begins, final revised FRED values are used with an approximate one-month reporting lag; indicators do not contribute before their own series has enough history. The SPY ETF/Proxy uses a synthetic S&P 500 total-return approximation through 1987, the Yahoo ^SP500TR daily total-return index from 1988 until SPY starts, and adjusted SPY prices after inception. The pre-1988 synthetic segment is reduced by an inception-era SPY expense assumption. The historical test begins once the 200-day SMA is available.</p>
    </section>
    <section>
      <h2>Growth of $10,000 (Log Scale)</h2>
      <div class="chart">{equity_chart}</div>
    </section>
    <section>
      <h2>Timing Gate Through Time</h2>
      <div class="chart">{signal_chart}</div>
    </section>
    <section>
      <h2>Recent Monthly Signal</h2>
      <table>
        <thead><tr><th>Month</th><th class="num">Signal Score</th><th>Timing On</th><th>Position</th><th class="num">SPY ETF</th><th class="num">200D SMA</th></tr></thead>
        <tbody>{recent_rows}</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def render_html(
    variant_specs: list[dict[str, object]],
    variant_payloads: dict[str, dict[str, object]],
    default_payload: dict[str, object],
    growth_chart: str,
    growth_controls: str,
    comparison_stat_rows: str,
) -> str:
    options = "\n".join(
        f'<option value="{html.escape(str(spec["key"]))}">{html.escape(str(spec["label"]))}</option>'
        for spec in variant_specs
    )
    payload_json = json.dumps(variant_payloads).replace("</", "<\\/")
    action = default_payload["action"]
    summary = default_payload["summary"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Recession Timing Dashboard</title>
  <style>
    :root {{
      --ink: {COLORS["ink"]};
      --muted: {COLORS["muted"]};
      --line: {COLORS["line"]};
      --blue: {COLORS["blue"]};
      --teal: {COLORS["teal"]};
      --bg: #f6f8fa;
      --panel: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
      letter-spacing: 0;
    }}
    header {{
      background: #ffffff;
      border-bottom: 1px solid var(--line);
    }}
    .wrap {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 30px;
      line-height: 1.1;
      font-weight: 760;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 18px;
      line-height: 1.2;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    .strategy-control {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-top: 18px;
    }}
    .strategy-control label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      font-weight: 740;
    }}
    .chart-controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      margin-bottom: 12px;
    }}
    .chart-toggle {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--ink);
      font-size: 13px;
      white-space: nowrap;
    }}
    .chart-toggle input {{
      margin: 0;
      accent-color: #111827;
    }}
    .swatch {{
      width: 11px;
      height: 11px;
      border-radius: 2px;
      border: 1px solid rgba(0, 0, 0, 0.18);
    }}
    select {{
      appearance: auto;
      min-width: min(560px, 100%);
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 9px 10px;
      font-size: 15px;
    }}
    .status {{
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) repeat(4, minmax(140px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .metric, section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .metric {{
      padding: 16px;
      min-height: 104px;
    }}
    .metric.primary.ok {{ border-color: #bbf7d0; background: #f0fdf4; }}
    .metric.primary.watch {{ border-color: #fed7aa; background: #fff7ed; }}
    .metric.primary.risk {{ border-color: #fecaca; background: #fff1f2; }}
    .label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      font-weight: 700;
    }}
    .value {{
      margin-top: 8px;
      font-size: 24px;
      line-height: 1.15;
      font-weight: 760;
      overflow-wrap: anywhere;
    }}
    .sub {{
      margin-top: 7px;
      color: var(--muted);
      font-size: 13px;
    }}
    main.wrap {{
      display: grid;
      gap: 18px;
    }}
    section {{
      padding: 18px;
      overflow: hidden;
    }}
    .table-scroll, .chart {{
      width: 100%;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }}
    .chart svg {{
      display: block;
      width: 100%;
      min-width: 760px;
      height: auto;
    }}
    #signal-chart svg {{
      min-width: 680px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    .table-scroll table {{
      min-width: 1080px;
    }}
    .current-indicators table {{
      table-layout: auto;
      font-size: 12.5px;
    }}
    .current-indicators th, .current-indicators td {{
      padding: 8px 6px;
    }}
    .current-indicators td:nth-child(2) {{
      min-width: 190px;
      white-space: normal;
    }}
    .current-indicators th:nth-child(3),
    .current-indicators th:nth-child(4),
    .current-indicators th:nth-child(5),
    .current-indicators td:nth-child(3),
    .current-indicators td:nth-child(4),
    .current-indicators td:nth-child(5) {{
      white-space: nowrap;
    }}
    th, td {{
      padding: 10px 9px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: middle;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      font-weight: 720;
    }}
    #stat-rows tr.muted {{
      color: #8a94a6;
    }}
    #stat-rows tr.muted a {{
      color: #8a94a6;
    }}
    #stat-rows tr.selected {{
      color: var(--ink);
      font-weight: 620;
    }}
    #stat-rows tr.benchmark {{
      color: var(--ink);
    }}
    .num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    a {{
      color: var(--blue);
      text-decoration: none;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-width: 68px;
      justify-content: center;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
      font-weight: 720;
      white-space: nowrap;
    }}
    .pill.good {{ background: #dcfce7; color: #166534; }}
    .pill.bad {{ background: #ffedd5; color: #9a3412; }}
    .pill.neutral {{ background: #e5e7eb; color: #4b5563; }}
    .rules {{
      margin: 12px 0 0;
      padding-left: 20px;
      color: var(--ink);
      line-height: 1.55;
    }}
    .note {{
      margin-top: 12px;
      font-size: 13px;
      color: var(--muted);
    }}
    @media (max-width: 900px) {{
      .status {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .metric.primary {{
        grid-column: 1 / -1;
      }}
      .wrap {{
        padding: 18px;
      }}
      h1 {{
        font-size: 24px;
      }}
    }}
    @media (max-width: 640px) {{
      .wrap {{
        padding: 14px;
      }}
      h1 {{
        font-size: 23px;
      }}
      h2 {{
        font-size: 16px;
      }}
      p {{
        font-size: 14px;
      }}
      .strategy-control {{
        display: block;
      }}
      .strategy-control label {{
        display: block;
        margin-bottom: 6px;
      }}
      select {{
        width: 100%;
        min-width: 0;
        min-height: 44px;
        font-size: 14px;
      }}
      .status {{
        grid-template-columns: 1fr;
        gap: 10px;
      }}
      .metric {{
        min-height: 0;
        padding: 14px;
      }}
      .value {{
        font-size: 21px;
      }}
      main.wrap {{
        gap: 14px;
      }}
      section {{
        padding: 14px;
      }}
      .chart-controls {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
      }}
      .chart-toggle {{
        min-height: 38px;
        padding: 8px;
        border: 1px solid var(--line);
        border-radius: 6px;
        white-space: normal;
      }}
      .chart {{
        margin: 0 -2px;
        padding-bottom: 4px;
      }}
      .chart svg {{
        min-width: 700px;
      }}
      #signal-chart svg {{
        min-width: 640px;
      }}
      .table-scroll {{
        overflow-x: visible;
      }}
      .responsive-table,
      .responsive-table thead,
      .responsive-table tbody,
      .responsive-table tr,
      .responsive-table td {{
        display: block;
        width: 100%;
      }}
      .responsive-table thead {{
        display: none;
      }}
      .responsive-table tr {{
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 10px;
        background: #fff;
      }}
      .responsive-table tr:last-child {{
        margin-bottom: 0;
      }}
      .responsive-table td {{
        display: grid;
        grid-template-columns: minmax(104px, 42%) minmax(0, 1fr);
        gap: 10px;
        align-items: start;
        padding: 8px 0;
        border-bottom: 1px solid var(--line);
        text-align: right;
      }}
      .responsive-table td:last-child {{
        border-bottom: 0;
      }}
      .responsive-table td::before {{
        content: attr(data-label);
        color: var(--muted);
        font-size: 11px;
        line-height: 1.25;
        text-transform: uppercase;
        font-weight: 740;
        text-align: left;
      }}
      .responsive-table td[data-label="Indicator"],
      .responsive-table td[data-label="Rule"],
      .responsive-table td[data-label="Strategy"] {{
        grid-template-columns: 1fr;
        gap: 5px;
        text-align: left;
      }}
      .responsive-table .num {{
        text-align: right;
      }}
      .current-indicators table {{
        font-size: 13px;
      }}
      .current-indicators td:nth-child(2) {{
        min-width: 0;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <h1>Recession Timing Dashboard</h1>
      <p>This dashboard provides the current inputs to a timing strategy inspired by Philosophical Economics <a href="https://www.philosophicaleconomics.com/2016/01/gtt/">Growth-Trend Timing</a> strategies. Backtested results for the strategy, and variations of the original proposed GTT strategies are also provided below. Economic indicators contribute signal scores based on the latest macro data; when the selected strategy's signal reaches its trigger, the portfolio switches from an S&P 500 buy and hold to a 200-day simple moving average rule.</p>
      <div class="strategy-control">
        <label for="strategy-select">Strategy</label>
        <select id="strategy-select">{options}</select>
      </div>
      <div class="status">
        <div id="current-signal-card" class="metric primary {html.escape(action["class"])}">
          <div class="label">Current Signal</div>
          <div id="current-headline" class="value">{html.escape(action["headline"])}</div>
          <div id="current-detail" class="sub">{html.escape(action["detail"])}</div>
        </div>
        <div class="metric">
          <div class="label">Tripped Indicators</div>
          <div id="trip-value" class="value">{summary["tripCount"]} / {summary["indicatorCount"]}</div>
          <div id="trip-sub" class="sub">Score {summary["signalScore"]} / trigger {summary["triggerScore"]}</div>
        </div>
        <div class="metric">
          <div class="label">Strategy Position</div>
          <div id="position-value" class="value">{'Invested' if summary["combinedInvested"] else 'Defensive'}</div>
          <div class="sub">As of <a id="position-date" href="{spy_source_url(summary["latestPriceDate"])}">{summary["latestPriceDate"]}</a></div>
        </div>
        <div class="metric">
          <div class="label">SPY ETF vs 200D SMA</div>
          <div id="trend-value" class="value">{'Above' if summary["trendAboveSma"] else 'Below'}</div>
          <div class="sub">As of <a id="trend-date" href="{spy_source_url(summary["latestPriceDate"])}">{summary["latestPriceDate"]}</a>: <span id="trend-sub">{summary["spyClose"]} vs {summary["spySma200"]}</span></div>
        </div>
        <div class="metric">
          <div class="label">Macro Data Date</div>
          <div id="macro-date" class="value">{summary["latestMacroReleaseDate"]}</div>
          <div class="sub">Latest macro release date in the snapshot</div>
        </div>
      </div>
    </div>
  </header>
  <main class="wrap">
    <section class="current-indicators">
      <h2>Current Economic Indicators</h2>
      <table class="responsive-table">
        <thead><tr><th>Indicator</th><th>Rule</th><th class="num">Data Through</th><th class="num">Available</th><th class="num">Next Update</th><th class="num">Latest</th><th class="num">Threshold</th><th class="num">Score</th><th>Status</th></tr></thead>
        <tbody id="indicator-rows">{default_payload["indicatorRows"]}</tbody>
      </table>
    </section>
    <section>
      <h2>Performance Summary</h2>
      <div class="table-scroll">
        <table class="responsive-table">
          <thead><tr><th>Strategy</th><th class="num">Start</th><th class="num">End</th><th class="num">Final Equity</th><th class="num">CAGR</th><th class="num">Vol</th><th class="num">Sharpe</th><th class="num">Sortino</th><th class="num">Max DD</th><th class="num">Avg % Invested</th></tr></thead>
          <tbody id="stat-rows">{comparison_stat_rows}</tbody>
        </table>
      </div>
      <p class="note">Stats are computed from daily returns. Idle capital earns the cash proxy return; Sharpe and Sortino are calculated on excess returns over that same cash series.</p>
    </section>
    <section>
      <h2>Selected Strategy Rules</h2>
      <div id="rules-html">{default_payload["rulesHtml"]}</div>
    </section>
    <section>
      <h2>Growth of $10,000 (Log Scale)</h2>
      <div id="growth-controls" class="chart-controls">{growth_controls}</div>
      <div id="equity-chart" class="chart">{growth_chart}</div>
    </section>
    <section>
      <h2>Timing Gate Through Time</h2>
      <div id="signal-chart" class="chart">{default_payload["signalChart"]}</div>
    </section>
    <section>
      <h2>Recent Monthly Signal</h2>
      <table class="responsive-table">
        <thead><tr><th>Month</th><th class="num">Signal Score</th><th>Timing On</th><th>Position</th><th class="num">SPY ETF</th><th class="num">200D SMA</th></tr></thead>
        <tbody id="recent-rows">{default_payload["recentRows"]}</tbody>
      </table>
    </section>
  </main>
  <script id="strategy-data" type="application/json">{payload_json}</script>
  <script>
    const strategies = JSON.parse(document.getElementById("strategy-data").textContent);
    const select = document.getElementById("strategy-select");
    const chartInputs = Array.from(document.querySelectorAll(".chart-toggle input"));
    function updateGrowthLines() {{
      const visible = new Set(chartInputs.filter(input => input.checked).map(input => input.dataset.series));
      document.querySelectorAll(".growth-line").forEach(line => {{
        line.style.display = visible.has(line.dataset.series) ? "" : "none";
      }});
    }}
    chartInputs.forEach(input => input.addEventListener("change", updateGrowthLines));
    function updatePerformanceSelection(key) {{
      document.querySelectorAll("#stat-rows tr[data-row-kind='strategy']").forEach(row => {{
        if (row.dataset.strategyKey === key) {{
          row.classList.add("selected");
          row.classList.remove("muted");
        }} else {{
          row.classList.add("muted");
          row.classList.remove("selected");
        }}
      }});
    }}
    function renderStrategy(key) {{
      const strategy = strategies[key];
      const summary = strategy.summary;
      const selectedChartInput = document.querySelector('.chart-toggle input[data-series="' + key + '"]');
      if (selectedChartInput && !selectedChartInput.checked) {{
        selectedChartInput.checked = true;
        updateGrowthLines();
      }}
      document.getElementById("current-signal-card").className = "metric primary " + strategy.action.class;
      document.getElementById("current-headline").textContent = strategy.action.headline;
      document.getElementById("current-detail").textContent = strategy.action.detail;
      document.getElementById("trip-value").textContent = summary.tripCount + " / " + summary.indicatorCount;
      document.getElementById("trip-sub").textContent = "Score " + summary.signalScore + " / trigger " + summary.triggerScore;
      document.getElementById("position-value").textContent = summary.combinedInvested ? "Invested" : "Defensive";
      document.getElementById("position-date").textContent = summary.latestPriceDate;
      document.getElementById("position-date").href = summary.priceSourceUrl;
      document.getElementById("trend-value").textContent = summary.trendAboveSma ? "Above" : "Below";
      document.getElementById("trend-date").textContent = summary.latestPriceDate;
      document.getElementById("trend-date").href = summary.priceSourceUrl;
      document.getElementById("trend-sub").textContent = summary.spyClose + " vs " + summary.spySma200;
      document.getElementById("macro-date").textContent = summary.latestMacroReleaseDate;
      document.getElementById("indicator-rows").innerHTML = strategy.indicatorRows;
      updatePerformanceSelection(key);
      document.getElementById("rules-html").innerHTML = strategy.rulesHtml;
      document.getElementById("signal-chart").innerHTML = strategy.signalChart;
      document.getElementById("recent-rows").innerHTML = strategy.recentRows;
    }}
    select.addEventListener("change", event => renderStrategy(event.target.value));
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the static recession timing dashboard.")
    parser.add_argument("--refresh", action="store_true", help="Refresh raw data downloads instead of using cached files.")
    args = parser.parse_args()
    path = build_dashboard(refresh=args.refresh)
    print(path)
