from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd


DEFAULT_MARKET_CLOSE_BUFFER = (16, 10)
YAHOO_CHART = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?period1={start}&period2={end}&interval=1d&events=history"
    "&includeAdjustedClose=true"
)


def download_text(url: str, timeout: int = 90) -> str:
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


def read_cached_or_download(path: Path, url: str, refresh: bool) -> str:
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")
    try:
        text = download_text(url)
    except RuntimeError:
        if path.exists():
            return path.read_text(encoding="utf-8")
        raise
    path.write_text(text, encoding="utf-8")
    time.sleep(0.2)
    return text


def yahoo_cache_name(symbol: str) -> str:
    return f"{symbol.lower().replace('^', '').replace('.', '_')}_yahoo_chart.json"


def load_yahoo_prices(
    symbol: str,
    raw_dir: Path,
    refresh: bool = False,
    start_date: str = "1990-01-01",
    fallback_csv: Path | None = None,
    market_close_buffer: tuple[int, int] = DEFAULT_MARKET_CLOSE_BUFFER,
) -> pd.DataFrame:
    raw_dir.mkdir(parents=True, exist_ok=True)
    end = int((pd.Timestamp.today() + pd.Timedelta(days=1)).timestamp())
    start = int(pd.Timestamp(start_date).timestamp())
    cache_path = raw_dir / yahoo_cache_name(symbol)
    url = YAHOO_CHART.format(symbol=symbol, start=start, end=end)

    try:
        text = read_cached_or_download(cache_path, url, refresh)
    except RuntimeError:
        if fallback_csv is None or not fallback_csv.exists():
            raise
        return load_local_yfinance_csv(fallback_csv, start_date=start_date)
    cache_timestamp = None
    if cache_path.exists():
        cache_timestamp = pd.Timestamp.fromtimestamp(
            cache_path.stat().st_mtime, tz="America/New_York"
        )

    payload = json.loads(text)
    result = payload["chart"]["result"][0]
    timestamps = (
        pd.to_datetime(result["timestamp"], unit="s")
        .tz_localize("UTC")
        .tz_convert("America/New_York")
        .tz_localize(None)
        .normalize()
    )
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
    return drop_incomplete_current_session(
        frame,
        now=cache_timestamp,
        market_close_buffer=market_close_buffer,
    )


def drop_incomplete_current_session(
    frame: pd.DataFrame,
    now: pd.Timestamp | None = None,
    market_close_buffer: tuple[int, int] = DEFAULT_MARKET_CLOSE_BUFFER,
) -> pd.DataFrame:
    if frame.empty:
        return frame
    now = now if now is not None else pd.Timestamp.now(tz="America/New_York")
    if frame.index[-1].date() == now.date() and (now.hour, now.minute) < market_close_buffer:
        return frame.iloc[:-1]
    return frame


def scale_to_anchor(
    frame: pd.DataFrame,
    anchor_date: pd.Timestamp,
    anchor_value: float,
    price_col: str = "Close",
) -> pd.DataFrame:
    anchor_rows = frame.loc[frame.index <= anchor_date]
    if frame.empty or anchor_rows.empty:
        return frame.copy()
    scaled = frame.copy()
    scaled[price_col] = scaled[price_col] * (anchor_value / float(anchor_rows[price_col].iloc[-1]))
    return scaled


def source_history_url(symbol: str, date_text: object, days: int = 2) -> str:
    date = pd.Timestamp(str(date_text))
    if date.tzinfo is None:
        date = date.tz_localize("UTC")
    else:
        date = date.tz_convert("UTC")
    end = date + pd.Timedelta(days=days)
    return (
        f"https://finance.yahoo.com/quote/{symbol}/history/"
        f"?period1={int(date.timestamp())}&period2={int(end.timestamp())}"
        "&interval=1d&filter=history&frequency=1d"
    )


def load_local_yfinance_csv(path: Path, start_date: str | None = None) -> pd.DataFrame:
    frame = pd.read_csv(path, skiprows=[1, 2])
    frame = frame.rename(columns={frame.columns[0]: "Date"})
    frame["Date"] = pd.to_datetime(frame["Date"])
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    out = frame.sort_values("Date").set_index("Date")[["Close"]].dropna()
    if start_date is not None:
        out = out.loc[pd.Timestamp(start_date) :]
    return out
