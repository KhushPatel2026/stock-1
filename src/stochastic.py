"""Stochastic Oscillator mean reversion — %K(14) bullish cross from oversold zone."""
import pandas as pd
import numpy as np

META = {
    "name": "Stochastic Oscillator",
    "family": "MR",
    "params": {"k_n": 14, "d_n": 3, "oversold": 20, "overbought": 80, "exit_level": 50, "top_n": 5, "cost": 0.001},
    "description": "Long when %K < 20 AND %K > %D; exit when %K > 80 OR %K > 50.",
}

def _stoch_k(close: pd.Series, high: pd.Series, low: pd.Series, n: int) -> pd.Series:
    hh = high.rolling(n).max()
    ll = low.rolling(n).min()
    return (close - ll) / (hh - ll).replace(0, np.nan) * 100

def backtest(data: dict, k_n=14, d_n=3, oversold=20, overbought=80, exit_level=50, top_n=5, cost=0.001) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = 1_000_000
    holdings = {}
    trades = []
    eq_curve = []
    ks = {t: _stoch_k(df["close"], df["high"], df["low"], k_n) for t, df in data.items()}
    ds = {t: ks[t].rolling(d_n).mean() for t in data}
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                kk = ks[t].loc[:d].iloc[-1] if len(ks[t].loc[:d]) else np.nan
                if pd.isna(kk) or kk > overbought or kk > exit_level:
                    close = float(data[t].loc[d, "close"])
                    cash += holdings[t] * close * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                    del holdings[t]
        candidates = []
        for t, df in data.items():
            if t in holdings or d not in df.index:
                continue
            k_ser = ks[t].loc[:d]; d_ser = ds[t].loc[:d]
            if k_ser.empty or pd.isna(k_ser.iloc[-1]) or pd.isna(d_ser.iloc[-1]):
                continue
            if k_ser.iloc[-1] < oversold and k_ser.iloc[-1] > d_ser.iloc[-1]:
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