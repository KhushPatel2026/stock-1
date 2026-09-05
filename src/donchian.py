"""Donchian channel breakout — long on N-bar high break, exit on N/2-bar low break."""
import pandas as pd
import numpy as np

META = {
    "name": "Donchian Breakout",
    "family": "Trend",
    "params": {"entry_n": 20, "exit_n": 10, "top_n": 5, "cost": 0.001},
    "description": "Long when close breaks above prior N-bar high; exit on close below prior N/2-bar low.",
}

def _entry(df: pd.DataFrame, n: int) -> pd.Series:
    hh = df["high"].rolling(n).max()
    return df["close"] > hh.shift(1)

def _exit(df: pd.DataFrame, n: int) -> pd.Series:
    ll = df["low"].rolling(n).min()
    return df["close"] < ll.shift(1)

def backtest(data: dict, entry_n=20, exit_n=10, top_n=5, cost=0.001) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = 1_000_000
    holdings = {}
    trades = []
    eq_curve = []
    entry_sig = {t: _entry(df, entry_n) for t, df in data.items()}
    exit_sig = {t: _exit(df, exit_n) for t, df in data.items()}
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index and bool(exit_sig[t].loc[:d].iloc[-1]):
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
