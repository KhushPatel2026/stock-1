"""Portfolio risk overlay — maxDD kill-switch, vol targeting, correlation monitor."""
import pandas as pd
import numpy as np

def max_drawdown_kill(equity: pd.Series, thresh: float = 0.10) -> list:
    peak=equity.cummax()
    dd=(equity-peak)/peak
    # first breach
    breaches=dd[dd <= -thresh].index.tolist()
    return breaches

def apply_kill_switch(equity: pd.Series, thresh: float = 0.10) -> pd.Series:
    breaches=max_drawdown_kill(equity, thresh)
    if not breaches:
        return equity
    first=breaches[0]
    # after breach, flatline at breach value (cut to cash)
    out=equity.copy()
    val=out.loc[first]
    out.loc[first:] = val
    return out

def vol_target_scale(equity: pd.Series, target: float = 0.15, lookback: int = 60) -> pd.Series:
    rets=equity.pct_change()
    vol=rets.rolling(lookback).std() * np.sqrt(252)
    weight=(target / vol).clip(lower=0.2, upper=1.5).fillna(1.0)
    return weight

def apply_vol_target(equity: pd.Series, target: float = 0.15) -> pd.Series:
    w=vol_target_scale(equity, target)
    rets=equity.pct_change().fillna(0)
    scaled_rets=rets * w.shift(1).fillna(1.0)
    return (1+scaled_rets).cumprod() * equity.iloc[0]

def correlation_flag(equities: dict[str, pd.Series], thresh: float = 0.7) -> dict:
    if len(equities)<2:
        return {"matrix": pd.DataFrame(), "flags": []}
    df=pd.DataFrame(equities).pct_change().dropna()
    corr=df.corr()
    flags=[]
    for i in corr.columns:
        for j in corr.columns:
            if i<j and abs(corr.loc[i,j]) > thresh:
                flags.append((i,j, float(corr.loc[i,j])))
    return {"matrix": corr, "flags": flags}
