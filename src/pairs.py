"""Pair discovery — Engle-Granger cointegration scan."""
import pandas as pd
from statsmodels.tsa.stattools import coint
from .universe import same_sector_pairs

def find_cointegrated(data: dict[str, pd.DataFrame], p_thresh: float = 0.05, min_corr: float = 0.7, lookback: int = 252) -> list[dict]:
    if len(data) < 2:
        raise ValueError("need >=2 tickers")
    tickers = list(data.keys())
    # candidate pairs: same-sector first, fallback to all if none
    cands = same_sector_pairs(tickers)
    if not cands:
        cands = [(tickers[i], tickers[j]) for i in range(len(tickers)) for j in range(i+1, len(tickers))]
    out = []
    for t1, t2 in cands:
        s1 = data[t1]["close"].tail(lookback)
        s2 = data[t2]["close"].tail(lookback)
        # align
        df = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(df) < lookback * 0.8:
            continue
        s1a, s2a = df.iloc[:, 0], df.iloc[:, 1]
        corr = s1a.corr(s2a)
        if corr is None or corr < min_corr:
            continue
        try:
            _, pval, _ = coint(s1a, s2a)
        except Exception:
            continue
        if pval <= p_thresh:
            # beta from last rolling window for reporting
            from .spread import rolling_beta
            beta = rolling_beta(s1a, s2a, window=min(60, len(s1a))).iloc[-1]
            out.append({"pair": (t1, t2), "pvalue": float(pval), "corr": float(corr), "beta": float(beta) if not pd.isna(beta) else 1.0})
    out.sort(key=lambda x: x["pvalue"])
    return out
