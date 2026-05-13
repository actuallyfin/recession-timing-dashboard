from __future__ import annotations

import io
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from config import SPY_FIRST_TRADING_DATE, SPY_INCEPTION_EXPENSE_RATIO, START_DATE


RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
FRED_API = "https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={api_key}&file_type=json"
FRED_INITIAL_API = (
    "https://api.stlouisfed.org/fred/series/observations?"
    "series_id={series}&api_key={api_key}&file_type=json&output_type=4"
    "&realtime_start=1776-07-04&realtime_end=9999-12-31"
)
FRED_REVISIONS_API = (
    "https://api.stlouisfed.org/fred/series/observations?"
    "series_id={series}&api_key={api_key}&file_type=json&output_type=3"
    "&realtime_start=1776-07-04&realtime_end=9999-12-31"
)
FRED_SERIES_RELEASE_API = (
    "https://api.stlouisfed.org/fred/series/release?"
    "series_id={series}&api_key={api_key}&file_type=json"
)
FRED_RELEASE_DATES_API = (
    "https://api.stlouisfed.org/fred/release/dates?"
    "release_id={release_id}&api_key={api_key}&file_type=json"
    "&include_release_dates_with_no_data=true&limit=1000&sort_order=desc"
)
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start}&period2={end}&interval=1d&events=history&includeAdjustedClose=true"
MARKET_CLOSE_BUFFER = (16, 10)


SP500_TOTAL_RETURNS = {
    1958: 0.4336,
    1959: 0.1196,
    1960: 0.0047,
    1961: 0.2689,
    1962: -0.0873,
    1963: 0.2280,
    1964: 0.1648,
    1965: 0.1245,
    1966: -0.1006,
    1967: 0.2398,
    1968: 0.1106,
    1969: -0.0850,
    1970: 0.0401,
    1971: 0.1431,
    1972: 0.1898,
    1973: -0.1466,
    1974: -0.2647,
    1975: 0.3720,
    1976: 0.2384,
    1977: -0.0718,
    1978: 0.0656,
    1979: 0.1844,
    1980: 0.3242,
    1981: -0.0491,
    1982: 0.2155,
    1983: 0.2256,
    1984: 0.0627,
    1985: 0.3173,
    1986: 0.1867,
    1987: 0.0525,
    1988: 0.1661,
    1989: 0.3169,
    1990: -0.0310,
    1991: 0.3047,
    1992: 0.0762,
    1993: 0.1008,
}


def _download_text(url: str, timeout: int = 90) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except (TimeoutError, urllib.error.URLError) as error:
            last_error = error
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not download {url}") from last_error


def _read_cached_or_download(path: Path, url: str, refresh: bool) -> str:
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")
    try:
        text = _download_text(url)
    except RuntimeError:
        if path.exists():
            return path.read_text(encoding="utf-8")
        raise
    path.write_text(text, encoding="utf-8")
    time.sleep(0.2)
    return text


def load_fred_series(series: str, refresh: bool = False) -> pd.Series:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("FRED_API_KEY")
    if api_key:
        cache_path = RAW_DIR / f"fred_{series}.json"
        url = FRED_API.format(series=series, api_key=api_key)
        text = _read_cached_or_download(cache_path, url, refresh)
        payload = json.loads(text)
        frame = pd.DataFrame(payload["observations"])[["date", "value"]]
        date_col = "date"
        value_col = "value"
    else:
        cache_path = RAW_DIR / f"fred_{series}.csv"
        url = FRED_CSV.format(series=series)
        try:
            text = _read_cached_or_download(cache_path, url, refresh)
        except RuntimeError as error:
            raise RuntimeError(
                "FRED graph CSV download failed and FRED_API_KEY is not set. "
                "Set FRED_API_KEY to use the official FRED API, or rerun without "
                "--refresh if cached raw files already exist."
            ) from error
        frame = pd.read_csv(io.StringIO(text))
        date_col = "observation_date" if "observation_date" in frame.columns else "DATE"
        value_col = series if series in frame.columns else frame.columns[-1]

    frame[date_col] = pd.to_datetime(frame[date_col])
    frame[value_col] = pd.to_numeric(frame[value_col].replace(".", pd.NA), errors="coerce")
    out = frame.dropna(subset=[value_col]).set_index(date_col)[value_col].sort_index()
    out.name = series
    return out.loc[out.index >= pd.Timestamp(START_DATE) - pd.DateOffset(years=2)]


def load_fred_initial_release_observations(series: str, refresh: bool = False) -> pd.DataFrame:
    """Initial-release FRED observations.

    Returned rows are dated two ways:
    - observation_date: the economic period being measured
    - release_date: the first FRED/ALFRED vintage date for that observation
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is required for initial-release observations.")

    cache_path = RAW_DIR / f"fred_{series}_initial.json"
    observation_start = (pd.Timestamp(START_DATE) - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
    url = FRED_INITIAL_API.format(series=series, api_key=api_key) + f"&observation_start={observation_start}"
    try:
        text = _read_cached_or_download(cache_path, url, refresh)
        payload = json.loads(text)
    except RuntimeError:
        initial = load_fred_initial_release_observations(series, refresh=refresh)
        return initial.rename(columns={"release_date": "available_date"})
    frame = pd.DataFrame(payload["observations"])
    if frame.empty:
        return pd.DataFrame(columns=["observation_date", "release_date", "value"])

    frame = frame.rename(columns={"date": "observation_date", "realtime_start": "release_date"})
    frame["observation_date"] = pd.to_datetime(frame["observation_date"])
    frame["release_date"] = pd.to_datetime(frame["release_date"])
    frame["value"] = pd.to_numeric(frame["value"].replace(".", pd.NA), errors="coerce")
    frame = frame.dropna(subset=["value"]).sort_values(["observation_date", "release_date"])
    frame = frame.drop_duplicates(subset=["observation_date"], keep="first")
    return frame[["observation_date", "release_date", "value"]].reset_index(drop=True)


def load_fred_revision_events(series: str, refresh: bool = False) -> pd.DataFrame:
    """New and revised FRED observations as point-in-time update events."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is required for real-time revision events.")

    cache_path = RAW_DIR / f"fred_{series}_revisions.json"
    observation_start = (pd.Timestamp(START_DATE) - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
    url = FRED_REVISIONS_API.format(series=series, api_key=api_key) + f"&observation_start={observation_start}"
    try:
        text = _read_cached_or_download(cache_path, url, refresh)
        payload = json.loads(text)
    except RuntimeError:
        initial = load_fred_initial_release_observations(series, refresh=refresh)
        return initial.rename(columns={"release_date": "available_date"})
    rows = []
    prefix = f"{series}_"
    for obs in payload.get("observations", []):
        observation_date = pd.to_datetime(obs.get("date"))
        for key, value in obs.items():
            if not key.startswith(prefix):
                continue
            vintage = key[len(prefix) :]
            if len(vintage) != 8 or not vintage.isdigit():
                continue
            rows.append(
                {
                    "observation_date": observation_date,
                    "available_date": pd.to_datetime(vintage, format="%Y%m%d"),
                    "value": pd.to_numeric(value, errors="coerce"),
                }
            )
    if not rows:
        return pd.DataFrame(columns=["observation_date", "available_date", "value"])
    frame = pd.DataFrame(rows).dropna(subset=["value"])
    return frame.sort_values(["available_date", "observation_date"]).reset_index(drop=True)


def load_fred_series_release(series: str, refresh: bool = False) -> dict[str, object]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is required for FRED release metadata.")

    cache_path = RAW_DIR / f"fred_{series}_release.json"
    url = FRED_SERIES_RELEASE_API.format(series=series, api_key=api_key)
    text = _read_cached_or_download(cache_path, url, refresh)
    payload = json.loads(text)
    releases = payload.get("releases", [])
    if not releases:
        raise RuntimeError(f"No FRED release metadata found for {series}.")
    return releases[0]


def load_fred_release_dates(release_id: int, refresh: bool = False) -> pd.DataFrame:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is required for FRED release dates.")

    cache_path = RAW_DIR / f"fred_release_{release_id}_dates.json"
    url = FRED_RELEASE_DATES_API.format(release_id=release_id, api_key=api_key)
    text = _read_cached_or_download(cache_path, url, refresh)
    payload = json.loads(text)
    frame = pd.DataFrame(payload.get("release_dates", []))
    if frame.empty or "date" not in frame:
        return pd.DataFrame(columns=["date"])
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.sort_values("date").reset_index(drop=True)


def estimate_next_monthly_release_date(latest_available_date: pd.Timestamp | str) -> pd.Timestamp | None:
    if pd.isna(latest_available_date):
        return None
    return pd.Timestamp(latest_available_date) + pd.DateOffset(months=1)


def next_fred_release_date(
    series: str,
    latest_available_date: pd.Timestamp | str,
    refresh: bool = False,
) -> tuple[pd.Timestamp | None, bool]:
    """Return the next scheduled FRED release date if available.

    The boolean indicates whether the returned date came from FRED's release
    calendar. If the calendar is unavailable, fall back to a rough one-month
    estimate from the latest available release date.
    """
    fallback = estimate_next_monthly_release_date(latest_available_date)
    try:
        release = load_fred_series_release(series, refresh=refresh)
        dates = load_fred_release_dates(int(release["id"]), refresh=refresh)
    except Exception:
        return fallback, False

    if dates.empty:
        return fallback, False
    today = pd.Timestamp.today().normalize()
    scheduled = dates.loc[dates["date"] > today, "date"]
    if scheduled.empty:
        return fallback, False
    return pd.Timestamp(scheduled.iloc[0]), True


def _final_fred_events_before_vintages(
    series: str, revision_events: pd.DataFrame, refresh: bool = False
) -> pd.DataFrame:
    final = load_fred_series(series, refresh=refresh).rename("value").reset_index()
    final.columns = ["observation_date", "value"]
    final["available_date"] = final["observation_date"] + pd.offsets.MonthEnd(1)
    if not revision_events.empty:
        final = final.loc[final["available_date"] < revision_events["available_date"].min()]
    return final[["observation_date", "available_date", "value"]]


def load_spy_prices(refresh: bool = False) -> pd.DataFrame:
    return load_us_equity_prices(refresh=refresh).loc[START_DATE:]


def load_us_equity_prices(refresh: bool = False) -> pd.DataFrame:
    """SPY total-return proxy stitched to a synthetic pre-SPY S&P 500 series.

    SPY adjusted close is used after inception. The official Yahoo
    ^SP500TR daily total-return index is used where available before SPY.
    Before ^SP500TR starts, daily S&P 500 price index returns are adjusted
    to match published annual S&P 500 total returns, then reduced by SPY's
    inception-era annual expense assumption.
    """
    spy = load_yahoo_prices("SPY", refresh=refresh)
    spy_start = pd.Timestamp(SPY_FIRST_TRADING_DATE)
    post_spy = spy.loc[spy.index >= spy_start, ["Close", "Unadjusted Close", "Volume"]].copy()
    official_tr = load_yahoo_prices("^SP500TR", refresh=refresh, start_date="1988-01-01")
    official_tr = official_tr[["Close", "Unadjusted Close", "Volume"]]
    synthetic = _load_pre_spy_total_return_proxy(refresh=refresh)

    if not official_tr.empty and not post_spy.empty:
        official_tr = _scale_to_anchor(
            official_tr, spy_start, float(post_spy["Close"].iloc[0])
        )

    if not synthetic.empty and not official_tr.empty:
        first_official_date = official_tr.index[0]
        synthetic = _scale_to_anchor(
            synthetic, first_official_date, float(official_tr["Close"].iloc[0])
        )
        synthetic = synthetic.loc[synthetic.index < first_official_date]

    official_tr = official_tr.loc[official_tr.index < spy_start]

    pre_spy = pd.concat([synthetic, official_tr]).sort_index()
    if pre_spy.empty:
        return post_spy
    pre_spy["Unadjusted Close"] = pre_spy["Close"]
    pre_spy["Volume"] = np.nan
    stitched = pd.concat([pre_spy, post_spy]).sort_index()
    return stitched[~stitched.index.duplicated(keep="last")]


def _scale_to_anchor(frame: pd.DataFrame, anchor_date: pd.Timestamp, anchor_value: float) -> pd.DataFrame:
    anchor_rows = frame.loc[frame.index <= anchor_date]
    if frame.empty or anchor_rows.empty:
        return frame.copy()
    scaled = frame.copy()
    scaled["Close"] = scaled["Close"] * (anchor_value / float(anchor_rows["Close"].iloc[-1]))
    return scaled


def _load_pre_spy_total_return_proxy(refresh: bool = False) -> pd.DataFrame:
    path = RAW_DIR / "gspc_yahoo_chart.json"
    if not path.exists():
        load_yahoo_prices("^GSPC", refresh=refresh, start_date="1958-01-01")
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload["chart"]["result"][0]
    timestamps = pd.to_datetime(result["timestamp"], unit="s").tz_localize("UTC").tz_convert("America/New_York").tz_localize(None).normalize()
    quote = result["indicators"]["quote"][0]
    frame = pd.DataFrame({"price": quote["close"]}, index=timestamps)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame = frame.dropna(subset=["price"])
    price_return = frame["price"].pct_change(fill_method=None)
    synthetic_return = price_return.copy()
    daily_expense = (1 - SPY_INCEPTION_EXPENSE_RATIO) ** (1 / 252) - 1
    for year, total_return in SP500_TOTAL_RETURNS.items():
        mask = synthetic_return.index.year == year
        year_price_returns = price_return.loc[mask].dropna()
        if year_price_returns.empty:
            continue
        price_growth = float((1 + year_price_returns).prod())
        target_growth = 1 + total_return
        daily_adjustment = (target_growth / price_growth) ** (1 / len(year_price_returns)) - 1
        synthetic_return.loc[year_price_returns.index] = (
            (1 + year_price_returns) * (1 + daily_adjustment) * (1 + daily_expense) - 1
        )
    synthetic_return = synthetic_return.fillna(0.0)
    level = (1 + synthetic_return).cumprod()
    return pd.DataFrame({"Close": level}, index=level.index)


def load_yahoo_prices(symbol: str, refresh: bool = False, start_date: str = "1990-01-01") -> pd.DataFrame:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    end = int((pd.Timestamp.today() + pd.Timedelta(days=1)).timestamp())
    start = int(pd.Timestamp(start_date).timestamp())
    safe_symbol = symbol.lower().replace("^", "").replace(".", "_")
    cache_path = RAW_DIR / f"{safe_symbol}_yahoo_chart.json"
    url = YAHOO_CHART.format(symbol=symbol, start=start, end=end)

    try:
        text = _read_cached_or_download(cache_path, url, refresh)
    except (urllib.error.URLError, RuntimeError):
        if symbol.upper() != "SPY":
            raise
        fallback = Path(__file__).resolve().parents[1] / "spy_daily.csv"
        if not fallback.exists():
            raise
        return _load_local_yfinance_csv(fallback)

    payload = json.loads(text)
    result = payload["chart"]["result"][0]
    timestamps = pd.to_datetime(result["timestamp"], unit="s").tz_localize("UTC").tz_convert("America/New_York").tz_localize(None).normalize()
    quote = result["indicators"]["quote"][0]
    adjclose = result["indicators"].get("adjclose", [{}])[0].get("adjclose", quote["close"])
    frame = pd.DataFrame(
        {
            "Close": adjclose,
            "Unadjusted Close": quote["close"],
            "Volume": quote.get("volume"),
        },
        index=timestamps,
    )
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    frame["Unadjusted Close"] = pd.to_numeric(frame["Unadjusted Close"], errors="coerce")
    frame = frame.dropna(subset=["Close"])
    return _drop_incomplete_current_session(frame)


def _drop_incomplete_current_session(
    frame: pd.DataFrame, now: pd.Timestamp | None = None
) -> pd.DataFrame:
    if frame.empty:
        return frame
    now = now if now is not None else pd.Timestamp.now(tz="America/New_York")
    if frame.index[-1].date() == now.date() and (now.hour, now.minute) < MARKET_CLOSE_BUFFER:
        return frame.iloc[:-1]
    return frame


def load_cash_level(daily_index: pd.DatetimeIndex, refresh: bool = False) -> pd.Series:
    """BIL total-return level stitched with synthetic pre-BIL TB3MS cash.

    This follows the country-CAPE project pattern: BIL adjusted close is used
    after inception, and the pre-BIL span compounds the monthly FRED TB3MS
    annualized rate at a daily 252-day rate.
    """
    bil = load_yahoo_prices("BIL", refresh=refresh)["Close"].rename("cash")
    bil = bil[~bil.index.duplicated(keep="last")].sort_index()
    bil_start = bil.index[0]
    pre_idx = daily_index[daily_index < bil_start]
    if len(pre_idx) == 0:
        return bil

    tb3ms_revisions = load_fred_revision_events("TB3MS", refresh=refresh)
    tb3ms_obs = pd.concat(
        [
            _final_fred_events_before_vintages("TB3MS", tb3ms_revisions, refresh=refresh),
            tb3ms_revisions,
        ],
        ignore_index=True,
    ).sort_values(["available_date", "observation_date"])
    current_values: dict[pd.Timestamp, float] = {}
    rows = []
    for available_date, group in tb3ms_obs.groupby("available_date", sort=True):
        for row in group.itertuples(index=False):
            current_values[pd.Timestamp(row.observation_date)] = float(row.value)
        latest_observation = max(current_values)
        rows.append(
            {
                "available_date": pd.Timestamp(available_date),
                "value": current_values[latest_observation],
            }
        )
    tb3ms = pd.DataFrame(rows).set_index("available_date")["value"].sort_index() / 100.0
    daily_ann = tb3ms.reindex(pre_idx.union(tb3ms.index)).sort_index().ffill().reindex(pre_idx)
    daily_ret = ((1 + daily_ann) ** (1 / 252) - 1).fillna(0.0)
    synthetic = (1 + daily_ret).cumprod()
    synthetic = synthetic * (bil.iloc[0] / synthetic.iloc[-1])
    stitched = pd.concat([synthetic, bil]).sort_index()
    return stitched[~stitched.index.duplicated(keep="last")].rename("cash")


def cash_returns_on(index: pd.DatetimeIndex, cash_level: pd.Series | None) -> pd.Series:
    if cash_level is None:
        return pd.Series(0.0, index=index)
    level = cash_level.reindex(index.union(cash_level.index)).sort_index().ffill().reindex(index)
    return level.pct_change(fill_method=None).fillna(0.0)


def _load_local_yfinance_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, skiprows=[1, 2])
    frame = frame.rename(columns={frame.columns[0]: "Date"})
    frame["Date"] = pd.to_datetime(frame["Date"])
    close_col = "Close"
    frame[close_col] = pd.to_numeric(frame[close_col], errors="coerce")
    return frame.sort_values("Date").set_index("Date")[[close_col]].dropna().loc[START_DATE:]
