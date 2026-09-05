"""Z-Score mean reversion — long on z(20) < -2 with SMA200 trend filter, exit on z > 0."""
import pandas as pd
import numpy as np

META = {
    "name": "Z-Score MR",
    "family": "MR",
    "params": {"n": 20, "trend_n": 200, "entry_z": -2.0, "exit_z": 0.0, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Long when (close - SMA20)/std20 < -2 AND close > SMA200; exit when z > 0.",
}

def _zscore(close: pd.Series, n: int) -> pd.Series:
    sma = close.rolling(n).mean()
    sd = close.rolling(n).std()
    return (close - sma) / sd.replace(0, np.nan)

def backtest(data: dict, n=20, trend_n=200, entry_z=-2.0, exit_z=0.0, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    zs = {t: _zscore(df["close"], n) for t, df in data.items()}
    trends = {t: df["close"].rolling(trend_n).mean() for t, df in data.items()}
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                z = zs[t].loc[:d].iloc[-1] if len(zs[t].loc[:d]) else np.nan
                if pd.isna(z) or z > exit_z:
                    close = float(data[t].loc[d, "close"])
                    cash += holdings[t] * close * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                    del holdings[t]
        candidates = []
        for t, df in data.items():
            if t in holdings or d not in df.index:
                continue
            z_ser = zs[t].loc[:d]; tr_ser = trends[t].loc[:d]
            if z_ser.empty or pd.isna(z_ser.iloc[-1]) or pd.isna(tr_ser.iloc[-1]):
                continue
            close = float(df.loc[d, "close"])
            if z_ser.iloc[-1] < entry_z and close > tr_ser.iloc[-1]:
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