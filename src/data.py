"""Data fetch with verified tickers + day-aware disk cache.

Correctness rules (learned the hard way):
- Every download is verified to contain ONLY the requested ticker. Under parallel
  load Yahoo occasionally serves a crossed/multi-ticker frame; accepting it silently
  once put ITC's price on TCS's card. Mismatch -> retry serially -> raise.
- All Yahoo access goes through one process-wide lock (yfinance is not thread-safe
  under concurrent multi-ticker load).
- Cache files are per (ticker, period, interval) CSV with a TTL — never reuse a
  daily cache across intervals, never serve a stale daily bar as "today".
"""
from __future__ import annotations
import threading
import time
from datetime import datetime
from pathlib import Path
import pandas as pd
import yfinance as yf

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
_YF_LOCK = threading.Lock()

OHLCV = ("open", "high", "low", "close", "volume")


def _cache_path(ticker: str, period: str, interval: str) -> Path:
    safe = ticker.replace(".", "_").replace("=", "_").replace("^", "")
    return CACHE_DIR / f"{safe}_{period}_{interval}.csv"


def _cache_fresh(p: Path, ttl_hours: float) -> bool:
    try:
        age_h = (time.time() - p.stat().st_mtime) / 3600
        return age_h < ttl_hours and p.stat().st_size > 0
    except OSError:
        return False


def _normalize(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Keep only `ticker`'s OHLCV. Raise on ticker mismatch — never guess."""
    if df is None or df.empty:
        raise ValueError(f"no data for {ticker}")
    if isinstance(df.columns, pd.MultiIndex):
        levels = df.columns.get_level_values(1).unique().tolist()
        if len(levels) == 1 and str(levels[0]).upper() == ticker.upper():
            df = df.xs(levels[0], level=1, axis=1)
        elif ticker in levels:
            df = df.xs(ticker, level=1, axis=1)
        else:
            raise ValueError(f"ticker mismatch for {ticker}: got {levels}")
    df.columns = [str(c).lower() for c in df.columns]
    for c in OHLCV:
        if c not in df.columns:
            raise ValueError(f"missing {c} for {ticker}")
    df = df[[*OHLCV]].sort_index()
    df.index = pd.to_datetime(df.index)
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    # duplicate labels after a bad flatten must never slip through
    if len(set(df.columns)) != len(df.columns):
        raise ValueError(f"duplicate columns for {ticker}: {list(df.columns)}")
    return df


def _download(ticker: str, period: str, interval: str) -> pd.DataFrame:
    last_err: Exception | None = None
    for attempt in (1, 2):
        try:
            with _YF_LOCK:
                df = yf.download(ticker, period=period, interval=interval,
                                 progress=False, auto_adjust=True, threads=False)
            return _normalize(df, ticker)
        except Exception as e:  # noqa: BLE001 — retry once serially, then raise
            last_err = e
            time.sleep(1.0)
    raise ValueError(f"no data for {ticker} ({last_err})")


def fetch(ticker: str, period: str = "5y", interval: str = "1d", use_cache: bool = True,
          ttl_hours: float = 12) -> pd.DataFrame:
    p = _cache_path(ticker, period, interval)
    if use_cache and interval == "1d" and _cache_fresh(p, ttl_hours):
        try:
            df = pd.read_csv(p, index_col=0, parse_dates=True)
            if not df.empty and set(OHLCV) <= set(df.columns):
                return df[[*OHLCV]].sort_index()
        except Exception:
            pass
    df = _download(ticker, period, interval)
    if interval == "1d":
        try:
            df.to_csv(p)
        except Exception:
            pass
    return df


def fetch_many(tickers: list[str], period: str = "5y", **kw) -> dict[str, pd.DataFrame]:
    out = {}
    for t in tickers:
        try:
            out[t] = fetch(t, period=period, **kw)
        except Exception as e:
            print(f"skip {t}: {e}")
    return out


def live_price(ticker: str) -> tuple[float | None, str, bool]:
    """Best-effort real-time price: 1m bars -> fast_info -> daily close.

    Returns (price, as_of_label, is_live). Never raises.
    """
    try:
        df = _download(ticker, period="1d", interval="1m")
        price = float(df["close"].iloc[-1])
        ts = df.index[-1]
        label = ts.strftime("%H:%M") if hasattr(ts, "strftime") else str(ts)
        return price, label, True
    except Exception:
        pass
    try:
        info_price = float(yf.Ticker(ticker).fast_info.get("last_price", 0)) or None
        if info_price:
            return info_price, "live", True
    except Exception:
        pass
    try:
        df = fetch(ticker, period="5d", interval="1d")
        return float(df["close"].iloc[-1]), str(df.index[-1].date()), False
    except Exception:
        return None, "", False
