"""Commodity Channel Index mean reversion — long on deeply negative CCI, exit on mean cross."""
import pandas as pd
import numpy as np

META = {
    "name": "Commodity Channel Index",
    "family": "MR",
    "params": {"n": 20, "oversold": -100, "exit_level": 0, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "CCI = (TP - SMA20(TP)) / (0.015 * mean_dev(TP,20)); long when CCI < -100; exit when CCI > 0.",
}

def _cci(df: pd.DataFrame, n: int) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma = tp.rolling(n).mean()
    md = tp.rolling(n).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return (tp - sma) / (0.015 * md.replace(0, np.nan))

def backtest(data: dict, n=20, oversold=-100, exit_level=0, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    ccis = {t: _cci(df, n) for t, df in data.items()}
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                c = ccis[t].loc[:d].iloc[-1] if len(ccis[t].loc[:d]) else np.nan
                if pd.isna(c) or c > exit_level:
                    close = float(data[t].loc[d, "close"])
                    cash += holdings[t] * close * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                    del holdings[t]
        candidates = []
        for t, df in data.items():
            if t in holdings or d not in df.index:
                continue
            c_ser = ccis[t].loc[:d]
            if c_ser.empty or pd.isna(c_ser.iloc[-1]):
                continue
            if c_ser.iloc[-1] < oversold:
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