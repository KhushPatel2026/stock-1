"""Data fetch with simple disk cache (parquet/csv fallback)."""
from pathlib import Path
import pandas as pd
import yfinance as yf

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

def _cache_path(ticker: str) -> Path:
    return CACHE_DIR / f"{ticker.replace('.','_')}.parquet"

def fetch(ticker: str, period: str = "5y", interval: str = "1d", use_cache: bool = True) -> pd.DataFrame:
    p = _cache_path(ticker)
    if use_cache and p.exists():
        try:
            df = pd.read_parquet(p)
            if not df.empty:
                return df
        except Exception:
            pass
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if df.empty:
        raise ValueError(f"no data for {ticker}")
    # yfinance may return MultiIndex columns when auto_adjust
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    # ensure expected cols
    df = df.rename(columns={c: c.lower() for c in df.columns})
    # keep only OHLCV
    for c in ("open", "high", "low", "close", "volume"):
        if c not in df.columns:
            raise ValueError(f"missing {c} for {ticker}")
    df = df[["open", "high", "low", "close", "volume"]].sort_index()
    df.index = pd.to_datetime(df.index)
    # cache
    try:
        df.to_parquet(p)
    except Exception:
        try:
            df.to_csv(p.with_suffix(".csv"))
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
