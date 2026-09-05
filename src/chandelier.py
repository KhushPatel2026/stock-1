"""Chandelier exit trend — Donchian entry, ATR trailing stop.

Long-only per name: enter on close > N-day high, exit on close < highest-high-
since-entry − mult × ATR. Lets winners run, cuts losers — the upgrade over
fixed SL/TP in src/portfolio.py.
"""
import pandas as pd
import numpy as np

META = {
    "name": "chandelier",
    "family": "Trend",
    "params": {"entry_n": 20, "atr_n": 14, "mult": 3.0, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Donchian breakout entry + ATR trailing-stop exit, long-only.",
}


def _atr(df: pd.DataFrame, n: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def backtest(data: dict, entry_n=20, atr_n=14, mult=3.0, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    sig = {}
    for t, df in data.items():
        if len(df) < entry_n + atr_n + 5:
            continue
        hi = df["high"].rolling(entry_n).max().shift(1)
        entry = df["close"] > hi
        sig[t] = {"entry": entry, "atr": _atr(df, atr_n), "high": df["high"], "close": df["close"]}
    cash, holdings, trail, trades, eq_curve = capital, {}, {}, [], []
    for d in all_dates:
        for t in list(holdings.keys()):
            if d not in data[t].index:
                continue
            px = float(data[t].loc[d, "close"])
            hh = max(float(data[t].loc[d, "high"]), trail[t][0])
            atr = float(sig[t]["atr"].loc[d]) if not pd.isna(sig[t]["atr"].loc[d]) else 0.0
            stop = hh - mult * atr
            trail[t] = (hh, stop)
            if px < stop:
                cash += holdings[t] * px * (1 - cost)
                trades.append({"ticker": t, "date": d, "action": "sell", "shares": holdings[t], "price": px})
                del holdings[t]
                del trail[t]
        if len(holdings) < top_n:
            for t, s in sig.items():
                if t in holdings or d not in data[t].index:
                    continue
                try:
                    if bool(s["entry"].loc[d]):
                        px = float(data[t].loc[d, "close"])
                        shares = int((cash / (top_n - len(holdings))) // px)
                        if shares and shares * px * (1 + cost) <= cash:
                            cash -= shares * px * (1 + cost)
                            holdings[t] = shares
                            trail[t] = (float(data[t].loc[d, "high"]), float(data[t].loc[d, "high"]))
                            trades.append({"ticker": t, "date": d, "action": "buy", "shares": shares, "price": px})
                            if len(holdings) >= top_n:
                                break
                except KeyError:
                    continue
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq
