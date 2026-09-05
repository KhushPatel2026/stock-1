"""Keltner channel breakout — long on close > EMA20 + 2*ATR14, exit on close < EMA20."""
import pandas as pd
import numpy as np
from src.indicators import atr

META = {
    "name": "Keltner Channel Breakout",
    "family": "Trend",
    "params": {"ema_n": 20, "atr_n": 14, "k": 2.0, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Long when close breaks above EMA(N) + k*ATR; exit when close drops below EMA(N).",
}

def _entry(df: pd.DataFrame, ema_n: int, atr_n: int, k: float) -> pd.Series:
    close = df["close"]
    ema = close.ewm(span=ema_n, adjust=False).mean()
    a = atr(df[["high", "low", "close"]], atr_n)
    return close > (ema + k * a)

def _exit(df: pd.DataFrame, ema_n: int) -> pd.Series:
    close = df["close"]
    ema = close.ewm(span=ema_n, adjust=False).mean()
    return close < ema

def backtest(data: dict, ema_n=20, atr_n=14, k=2.0, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    entry_sig = {t: _entry(df, ema_n, atr_n, k) for t, df in data.items()}
    exit_sig = {t: _exit(df, ema_n) for t, df in data.items()}
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
