"""Indicators: SMA, ATR (Wilder), ADX (Wilder) — pure pandas/numpy, no I/O."""
import pandas as pd
import numpy as np


def sma(series: pd.Series, window: int) -> pd.Series:
    if window < 2:
        raise ValueError("window must be >=2")
    return series.rolling(window).mean()


def _wilder_rma(series: pd.Series, window: int) -> pd.Series:
    """Wilder's RMA: seed = mean(first window), then (prev*(w-1)+val)/w"""
    n = len(series)
    out = pd.Series(np.nan, index=series.index, dtype=float)
    if n < window:
        return out
    # seed
    seed = series.iloc[:window].mean()
    out.iloc[window - 1] = seed
    for i in range(window, n):
        val = series.iloc[i]
        prev = out.iloc[i - 1]
        if pd.isna(val) or pd.isna(prev):
            out.iloc[i] = np.nan
        else:
            out.iloc[i] = (prev * (window - 1) + val) / window
    return out


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    for c in ("high", "low", "close"):
        if c not in df.columns:
            raise ValueError(f"missing column {c}")
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return _wilder_rma(tr, window)


def adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    for c in ("high", "low", "close"):
        if c not in df.columns:
            raise ValueError(f"missing column {c}")
    high, low, close = df["high"], df["low"], df["close"]
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)

    up = high - prev_high
    down = prev_low - low
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)

    # Wilder smoothing
    tr_s = _wilder_rma(tr, window)
    plus_s = _wilder_rma(plus_dm, window)
    minus_s = _wilder_rma(minus_dm, window)

    plus_di = 100 * plus_s / tr_s
    minus_di = 100 * minus_s / tr_s
    # handle div0
    plus_di = plus_di.replace([np.inf, -np.inf], np.nan)
    minus_di = minus_di.replace([np.inf, -np.inf], np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    dx = dx.replace([np.inf, -np.inf], np.nan).fillna(0)

    return _wilder_rma(dx, window)


def add_all(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience: add sma20/50/200, atr, adx columns."""
    out = df.copy()
    out["sma20"] = sma(out["close"], 20)
    out["sma50"] = sma(out["close"], 50)
    out["sma200"] = sma(out["close"], 200)
    out["atr"] = atr(out, 14)
    out["adx"] = adx(out, 14)
    return out
