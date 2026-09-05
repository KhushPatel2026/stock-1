"""Supertrend — long when close > supertrend line (ATR-based flip), exit when close < line."""
import pandas as pd
import numpy as np
from src.indicators import atr

META = {
    "name": "Supertrend",
    "family": "Trend",
    "params": {"atr_n": 14, "mult": 3.0, "top_n": 5, "cost": 0.001},
    "description": "Long when close above ATR-based supertrend band; exit on flip below.",
}

def _supertrend(df: pd.DataFrame, atr_n: int, mult: float) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    a = atr(df[["high", "low", "close"]], atr_n)
    hl2 = (high + low) / 2.0
    upper = hl2 + mult * a
    lower = hl2 - mult * a
    n = len(df)
    st = pd.Series(np.nan, index=df.index, dtype=float)
    trend = pd.Series(1, index=df.index, dtype=int)
    for i in range(1, n):
        prev_st = st.iloc[i - 1]
        if pd.isna(prev_st):
            continue
        prev_upper = upper.iloc[i - 1]
        prev_lower = lower.iloc[i - 1]
        new_lower = lower.iloc[i]
        new_upper = upper.iloc[i]
        # tight bands cannot widen against prior trend
        if new_lower < prev_lower or close.iloc[i - 1] < prev_lower:
            pass
        else:
            new_lower = prev_lower
        if new_upper > prev_upper or close.iloc[i - 1] > prev_upper:
            pass
        else:
            new_upper = prev_upper
        if trend.iloc[i - 1] == 1:
            if close.iloc[i] < new_lower:
                trend.iloc[i] = -1
                st.iloc[i] = new_upper
            else:
                trend.iloc[i] = 1
                st.iloc[i] = new_lower
        else:
            if close.iloc[i] > new_upper:
                trend.iloc[i] = 1
                st.iloc[i] = new_lower
            else:
                trend.iloc[i] = -1
                st.iloc[i] = new_upper
    return st

def _signal(df: pd.DataFrame, atr_n: int, mult: float) -> tuple[pd.Series, pd.Series]:
    st = _supertrend(df, atr_n, mult)
    long = df["close"] > st
    short = df["close"] < st
    return long, short

def backtest(data: dict, atr_n=14, mult=3.0, top_n=5, cost=0.001) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = 1_000_000
    holdings = {}
    trades = []
    eq_curve = []
    entry_sig = {}
    exit_sig = {}
    for t, df in data.items():
        long, short = _signal(df, atr_n, mult)
        entry_sig[t] = long
        exit_sig[t] = short
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index and len(exit_sig[t].loc[:d]) and bool(exit_sig[t].loc[:d].iloc[-1]):
                close = float(data[t].loc[d, "close"])
                cash += holdings[t] * close * (1 - cost)
                trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                del holdings[t]
        candidates = [t for t, df in data.items()
                     if t not in holdings and d in df.index
                     and len(entry_sig[t].loc[:d]) and bool(entry_sig[t].loc[:d].iloc[-1])]
        if candidates and cash > 0:
            notional = cash / min(top_n, len(candidates))
            for t in candidates[:top_n]:
                price = float(data[t].loc[d, "close"])
                shares = int(notional // price)
                if shares > 0:
                    cash -= shares * price * (1 + cost)
                    holdings[t] = shares
                    trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": shares})
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq
