"""Spread & z-score — rolling beta, spread, z."""
import pandas as pd
import numpy as np

def rolling_beta(s1: pd.Series, s2: pd.Series, window: int = 60) -> pd.Series:
    # y = s1, x = s2 — OLS with intercept, beta = cov/var
    n = len(s1)
    out = pd.Series(np.nan, index=s1.index, dtype=float)
    for i in range(window - 1, n):
        y = s1.iloc[i - window + 1: i + 1].values
        x = s2.iloc[i - window + 1: i + 1].values
        # beta without intercept: cov/variance, but with intercept is more stable
        # use polyfit degree 1: y = beta*x + alpha
        try:
            beta, _ = np.polyfit(x, y, 1)
        except Exception:
            beta = np.nan
        out.iloc[i] = beta
    return out

def spread_and_zscore(s1: pd.Series, s2: pd.Series, beta: pd.Series, window: int = 60) -> tuple[pd.Series, pd.Series]:
    spread = s1 - beta * s2
    mean = spread.rolling(window).mean()
    std = spread.rolling(window).std().clip(lower=1e-8)
    z = (spread - mean) / std
    return spread, z
