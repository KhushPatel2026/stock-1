"""Volume-confirmed breakout — close > N-day high AND volume > 1.5x avg."""
import pandas as pd
import numpy as np

META = {
    "name": "Volume-Confirmed Breakout",
    "family": "Trend",
    "params": {"lookback": 20, "vol_mult": 1.5, "top_n": 5, "cost": 0.001},
    "description": "Donchian-style breakout gated by volume > 1.5x 20-day avg.",
}


def backtest(data: dict, lookback: int = 20, vol_mult: float = 1.5, top_n: int = 5, cost: float = 0.001) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = 1_000_000
    holdings = {}
    trades = []
    eq_curve = []
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                close = float(data[t].loc[d, "close"])
                lo = float(data[t]["low"].rolling(lookback // 2).min().loc[:d].iloc[-1])
                if pd.isna(lo) or close < lo:
                    cash += holdings[t] * close * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                    del holdings[t]
        candidates = []
        for t, df in data.items():
            if t in holdings or d not in df.index:
                continue
            close = float(df.loc[d, "close"])
            hi = float(df["high"].rolling(lookback).max().loc[:d].iloc[-1])
            avg_vol = float(df["volume"].rolling(20).mean().loc[:d].iloc[-1])
            vol = float(df.loc[d, "volume"])
            if pd.isna(hi) or pd.isna(avg_vol):
                continue
            if close > hi and vol > vol_mult * avg_vol:
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
