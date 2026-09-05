"""Keltner Channel mean reversion — long on close below EMA20 - 2*ATR14, exit on EMA cross up."""
import pandas as pd
import numpy as np
from src.indicators import atr

META = {
    "name": "Keltner Channel MR",
    "family": "MR",
    "params": {"ema_n": 20, "atr_n": 14, "k": 2.0, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Long when close < EMA(20) - 2*ATR(14); exit when close >= EMA(20).",
}

def backtest(data: dict, ema_n=20, atr_n=14, k=2.0, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    ema = {t: df["close"].ewm(span=ema_n, adjust=False).mean() for t, df in data.items()}
    a = {t: atr(df[["high", "low", "close"]], atr_n) for t, df in data.items()}
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                e = ema[t].loc[:d].iloc[-1] if len(ema[t].loc[:d]) else np.nan
                close = float(data[t].loc[d, "close"])
                if pd.isna(e) or close >= e:
                    cash += holdings[t] * close * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                    del holdings[t]
        candidates = []
        for t, df in data.items():
            if t in holdings or d not in df.index:
                continue
            e = ema[t].loc[:d].iloc[-1] if len(ema[t].loc[:d]) else np.nan
            av = a[t].loc[:d].iloc[-1] if len(a[t].loc[:d]) else np.nan
            if pd.isna(e) or pd.isna(av):
                continue
            close = float(df.loc[d, "close"])
            if close < e - k * av:
                candidates.append(t)
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