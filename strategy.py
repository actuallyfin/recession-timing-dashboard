from __future__ import annotations

import math

import numpy as np
import pandas as pd

from config import (
    INDICATORS,
    INITIAL_CAPITAL,
    INITIAL_INVESTMENT,
    TIMING_ON_TRIGGER_SCORE,
    TRADING_DAYS_PER_YEAR,
)
from data_loader import (
    cash_returns_on,
    load_cash_level,
    load_indicator_fred_events,
    load_initial_fred_events,
    load_spy_prices,
)


def _apply_transform(series: pd.Series, transform: str) -> pd.Series:
    if transform == "yoy":
        prior = series.copy()
        prior.index = prior.index + pd.DateOffset(years=1)
        return series / prior.reindex(series.index) - 1
    if transform == "above_12m_sma":
        return series - series.rolling(12, min_periods=12).mean()
    raise ValueError(f"Unknown transform: {transform}")


def _threshold_series(series: pd.Series, transform: str, threshold: float) -> pd.Series:
    if transform == "above_12m_sma":
        return series.rolling(12, min_periods=12).mean() + threshold
    if transform == "yoy":
        return pd.Series(threshold, index=series.index)
    raise ValueError(f"Unknown transform: {transform}")


def _is_tripped(value: float, threshold: float, direction: str) -> bool:
    if pd.isna(value):
        return False
    if direction == "below":
        return value < threshold
    if direction == "above":
        return value > threshold
    raise ValueError(f"Unknown direction: {direction}")


def _build_asof_indicator_events(events: pd.DataFrame, transform: str, threshold: float) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(
            columns=["available_date", "observation_date", "raw_value", "signal_value", "threshold"]
        )

    current_values: dict[pd.Timestamp, float] = {}
    rows = []
    for available_date, group in events.groupby("available_date", sort=True):
        for row in group.itertuples(index=False):
            current_values[pd.Timestamp(row.observation_date)] = float(row.value)
        snapshot = pd.Series(current_values).sort_index()
        signal = _apply_transform(snapshot, transform)
        threshold_values = _threshold_series(snapshot, transform, threshold)
        valid_signal = signal.dropna()
        if valid_signal.empty:
            continue
        observation_date = valid_signal.index[-1]
        rows.append(
            {
                "available_date": pd.Timestamp(available_date),
                "observation_date": pd.Timestamp(observation_date),
                "raw_value": float(snapshot.loc[observation_date]),
                "signal_value": float(signal.loc[observation_date]),
                "threshold": float(threshold_values.loc[observation_date]),
            }
        )
    return pd.DataFrame(rows)


def _build_asof_ratio_indicator_events(
    numerator_events: pd.DataFrame,
    denominator_events: pd.DataFrame,
    transform: str,
    threshold: float,
) -> pd.DataFrame:
    if numerator_events.empty or denominator_events.empty:
        return pd.DataFrame(
            columns=["available_date", "observation_date", "raw_value", "signal_value", "threshold"]
        )

    numerator = numerator_events.copy()
    denominator = denominator_events.copy()
    numerator["component"] = "numerator"
    denominator["component"] = "denominator"
    events = pd.concat([numerator, denominator], ignore_index=True).sort_values(
        ["available_date", "observation_date", "component"]
    )

    current_numerator: dict[pd.Timestamp, float] = {}
    current_denominator: dict[pd.Timestamp, float] = {}
    rows = []
    for available_date, group in events.groupby("available_date", sort=True):
        for row in group.itertuples(index=False):
            observation_date = pd.Timestamp(row.observation_date)
            if row.component == "numerator":
                current_numerator[observation_date] = float(row.value)
            else:
                current_denominator[observation_date] = float(row.value)
        common_dates = sorted(set(current_numerator).intersection(current_denominator))
        if not common_dates:
            continue
        snapshot = pd.Series(
            {
                date: current_numerator[date] / current_denominator[date]
                for date in common_dates
                if current_denominator[date] != 0
            }
        ).sort_index()
        if snapshot.empty:
            continue
        signal = _apply_transform(snapshot, transform)
        threshold_values = _threshold_series(snapshot, transform, threshold)
        valid_signal = signal.dropna()
        if valid_signal.empty:
            continue
        observation_date = valid_signal.index[-1]
        rows.append(
            {
                "available_date": pd.Timestamp(available_date),
                "observation_date": pd.Timestamp(observation_date),
                "raw_value": float(snapshot.loc[observation_date]),
                "signal_value": float(signal.loc[observation_date]),
                "threshold": float(threshold_values.loc[observation_date]),
            }
        )
    return pd.DataFrame(rows)


def build_indicator_history(
    refresh: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    values: dict[str, pd.Series] = {}
    thresholds: dict[str, pd.Series] = {}
    raw_values: dict[str, pd.Series] = {}
    observation_dates: dict[str, pd.Series] = {}
    available_dates: dict[str, pd.Series] = {}

    for rule in INDICATORS:
        series_events = load_indicator_fred_events(rule.fred_series, refresh=refresh)
        if rule.denominator_series:
            denominator_events = load_initial_fred_events(rule.denominator_series, refresh=refresh)
            by_release = _build_asof_ratio_indicator_events(
                series_events, denominator_events, rule.transform, rule.threshold
            ).set_index("available_date")
        else:
            by_release = _build_asof_indicator_events(
                series_events, rule.transform, rule.threshold
            ).set_index("available_date")

        values[rule.key] = by_release["signal_value"]
        thresholds[rule.key] = by_release["threshold"]
        raw_values[rule.key] = by_release["raw_value"]
        observation_dates[rule.key] = by_release["observation_date"]
        available_dates[rule.key] = pd.Series(by_release.index, index=by_release.index)

    indicator_values = pd.DataFrame(values).sort_index().ffill()
    indicator_thresholds = pd.DataFrame(thresholds).reindex(indicator_values.index).ffill()
    indicator_raw_values = pd.DataFrame(raw_values).reindex(indicator_values.index).ffill()
    indicator_observation_dates = pd.DataFrame(observation_dates).reindex(indicator_values.index).ffill()
    indicator_available_dates = pd.DataFrame(available_dates).reindex(indicator_values.index).ffill()
    trips: dict[str, pd.Series] = {}
    for rule in INDICATORS:
        trips[rule.key] = indicator_values[rule.key].apply(
            lambda value, r=rule: int(_is_tripped(value, r.threshold, r.direction))
        )

    indicator_trips = pd.DataFrame(trips).reindex(indicator_values.index).fillna(0).astype(int)
    indicator_trips["trip_count"] = indicator_trips.sum(axis=1)
    score = pd.Series(0.0, index=indicator_trips.index)
    for rule in INDICATORS:
        score = score + indicator_trips[rule.key] * rule.signal_score
    indicator_trips["signal_score"] = score
    indicator_trips["timing_on"] = indicator_trips["signal_score"] >= TIMING_ON_TRIGGER_SCORE
    return (
        indicator_values,
        indicator_trips,
        indicator_thresholds,
        indicator_raw_values,
        indicator_observation_dates,
        indicator_available_dates,
    )


def build_strategy(refresh: bool = False) -> dict[str, pd.DataFrame | dict[str, float | str | int | bool]]:
    (
        indicator_values,
        indicator_trips,
        indicator_thresholds,
        indicator_raw_values,
        indicator_observation_dates,
        indicator_available_dates,
    ) = build_indicator_history(refresh=refresh)
    prices = load_spy_prices(refresh=refresh)
    daily = prices[["Close"]].copy()
    cash_level = load_cash_level(daily.index, refresh=refresh)
    daily["cash_return"] = cash_returns_on(daily.index, cash_level)
    daily["sma_200"] = daily["Close"].rolling(200, min_periods=200).mean()
    daily["daily_return"] = daily["Close"].pct_change().fillna(0.0)
    daily["trend_above_sma"] = daily["Close"] > daily["sma_200"]

    timing_monthly = indicator_trips[["trip_count", "signal_score", "timing_on"]].copy()
    timing_daily = timing_monthly.reindex(daily.index, method="ffill")
    daily = daily.join(timing_daily)
    daily[["trip_count", "signal_score"]] = daily[["trip_count", "signal_score"]].fillna(0)
    daily["timing_on"] = daily["timing_on"].fillna(False).astype(bool)
    daily["trend_above_sma"] = daily["trend_above_sma"].fillna(False).astype(bool)
    first_valid_sma = daily["sma_200"].first_valid_index()
    if first_valid_sma is None:
        raise RuntimeError("SPY history is too short to compute a 200-day SMA.")
    daily = daily.loc[first_valid_sma:].copy()
    daily.loc[daily.index[0], ["daily_return", "cash_return"]] = 0.0

    daily["combined_invested"] = ((~daily["timing_on"]) | daily["trend_above_sma"]).astype(bool)
    daily["always_timing_invested"] = daily["trend_above_sma"].astype(bool)
    daily["buy_hold_invested"] = True

    combined_position = daily["combined_invested"].shift(1).fillna(True).astype(bool)
    always_timing_position = daily["always_timing_invested"].shift(1).fillna(False).astype(bool)
    daily["combined_return"] = daily["daily_return"].where(combined_position, daily["cash_return"])
    daily["always_timing_return"] = daily["daily_return"].where(
        always_timing_position, daily["cash_return"]
    )
    daily["buy_hold_return"] = daily["daily_return"]

    daily["combined_equity"] = INITIAL_CAPITAL * (1 + daily["combined_return"]).cumprod()
    daily["always_timing_equity"] = INITIAL_CAPITAL * (1 + daily["always_timing_return"]).cumprod()
    daily["buy_hold_equity"] = INITIAL_CAPITAL * (1 + daily["buy_hold_return"]).cumprod()
    daily["combined_growth_10k"] = INITIAL_INVESTMENT * daily["combined_equity"]
    daily["always_timing_growth_10k"] = INITIAL_INVESTMENT * daily["always_timing_equity"]
    daily["buy_hold_growth_10k"] = INITIAL_INVESTMENT * daily["buy_hold_equity"]

    monthly_signal = daily.resample("ME").last()
    monthly_signal = monthly_signal[
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
    latest_indicator_date = indicator_values.dropna(how="all").index[-1]
    latest_values = indicator_values.loc[latest_indicator_date]
    latest_thresholds = indicator_thresholds.loc[latest_indicator_date]
    latest_raw_values = indicator_raw_values.loc[latest_indicator_date]
    latest_observation_dates = indicator_observation_dates.loc[latest_indicator_date]
    latest_available_dates = indicator_available_dates.loc[latest_indicator_date]
    latest_trips = indicator_trips.loc[latest_indicator_date]

    current_rows = []
    for rule in INDICATORS:
        value = latest_values.get(rule.key, np.nan)
        threshold_value = latest_thresholds.get(rule.key, np.nan)
        raw_value = latest_raw_values.get(rule.key, np.nan)
        observation_date = latest_observation_dates.get(rule.key, pd.NaT)
        available_date = latest_available_dates.get(rule.key, pd.NaT)
        current_rows.append(
            {
                "key": rule.key,
                "name": rule.name,
                "rule": rule.display,
                "signal_score": rule.signal_score,
                "latest_raw_value": raw_value,
                "current_threshold": threshold_value,
                "data_through": observation_date.strftime("%Y-%m-%d") if pd.notna(observation_date) else "",
                "available_date": available_date.strftime("%Y-%m-%d") if pd.notna(available_date) else "",
                "latest_value": value,
                "tripped": bool(latest_trips.get(rule.key, 0)),
                "score_contribution": rule.signal_score if bool(latest_trips.get(rule.key, 0)) else 0.0,
                "source_url": rule.source_url,
            }
        )
    current_indicators = pd.DataFrame(current_rows)

    latest = daily.loc[latest_date]
    summary = {
        "latest_price_date": latest_date.strftime("%Y-%m-%d"),
        "latest_indicator_date": latest_indicator_date.strftime("%Y-%m-%d"),
        "latest_macro_release_date": latest_indicator_date.strftime("%Y-%m-%d"),
        "timing_on": bool(latest["timing_on"]),
        "trend_above_sma": bool(latest["trend_above_sma"]),
        "combined_invested": bool(latest["combined_invested"]),
        "trip_count": int(latest["trip_count"]),
        "signal_score": float(latest["signal_score"]),
        "trigger_score": TIMING_ON_TRIGGER_SCORE,
        "spy_close": float(latest["Close"]),
        "spy_sma_200": float(latest["sma_200"]) if not pd.isna(latest["sma_200"]) else math.nan,
    }

    stats = pd.DataFrame(
        [
            _performance_stats(daily, "combined", "Economic gate + 200D SMA"),
            _performance_stats(daily, "always_timing", "200D SMA always on"),
            _performance_stats(daily, "buy_hold", "Buy and hold"),
        ]
    )

    return {
        "daily": daily,
        "monthly_signal": monthly_signal,
        "indicator_values": indicator_values,
        "indicator_trips": indicator_trips,
        "indicator_thresholds": indicator_thresholds,
        "indicator_raw_values": indicator_raw_values,
        "indicator_observation_dates": indicator_observation_dates,
        "indicator_available_dates": indicator_available_dates,
        "current_indicators": current_indicators,
        "summary": summary,
        "stats": stats,
    }


def _performance_stats(daily: pd.DataFrame, prefix: str, label: str) -> dict[str, float | str]:
    returns = daily[f"{prefix}_return"].dropna()
    equity = daily[f"{prefix}_equity"].dropna()
    cash_returns = daily["cash_return"].reindex(returns.index).fillna(0.0)
    years = (returns.index[-1] - returns.index[0]).days / 365.25
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    cagr = equity.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    vol = returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    excess_returns = returns - cash_returns
    sharpe = (
        excess_returns.mean() / excess_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        if excess_returns.std() and not np.isnan(excess_returns.std())
        else np.nan
    )
    downside_returns = excess_returns.clip(upper=0)
    downside_deviation = np.sqrt((downside_returns**2).mean())
    sortino = (
        excess_returns.mean() / downside_deviation * np.sqrt(TRADING_DAYS_PER_YEAR)
        if downside_deviation and not np.isnan(downside_deviation)
        else np.nan
    )
    drawdown = equity / equity.cummax() - 1
    invested_col = f"{prefix}_invested"
    exposure = daily[invested_col].mean() if invested_col in daily else 1.0
    return {
        "start": returns.index[0].strftime("%Y-%m-%d"),
        "end": returns.index[-1].strftime("%Y-%m-%d"),
        "strategy": label,
        "final_equity": equity.iloc[-1] * INITIAL_INVESTMENT,
        "total_return": total_return,
        "cagr": cagr,
        "vol": vol,
        "max_drawdown": drawdown.min(),
        "sharpe": sharpe,
        "sortino": sortino,
        "avg_pct_invested": exposure,
    }
