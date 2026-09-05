"""Ornstein-Uhlenbeck mean reversion — rolling OLS on dx = a + b*x, z-score to O-U fair value."""
import pandas as pd
import numpy as np

META = {
    "name": "Ornstein-Uhlenbeck MR",
    "family": "MR",
    "params": {"n": 60, "entry_z": -2.0, "exit_z": 0.0, "top_n": 5, "cost": 0.001},
    "description": "Fit dx = a + b*x on rolling window; spread = (close - mu)/sigma; long when z < -2; exit when z > 0.",
}

def _ou_z(close: pd.Series, n: int) -> pd.Series:
    x = close.values
    out = np.full_like(x, np.nan, dtype=float)
    for i in range(n - 1, len(x)):
        window = x[i - n + 1: i + 1]
        x_lag = window[:-1]
        dx = np.diff(window)
        x_mean = x_lag.mean()
        dx_mean = dx.mean()
        num = np.sum((x_lag - x_mean) * (dx - dx_mean))
        den = np.sum((x_lag - x_mean) ** 2)
        if den == 0:
            continue
        b = num / den
        a = dx_mean - b * x_mean
        theta = -b
        if theta <= 0:
            continue
        mu = -a / b
        resid = window[-1] - mu
        sigma = np.std(window, ddof=1)
        if sigma == 0:
            continue
        out[i] = resid / sigma
    return pd.Series(out, index=close.index)

def backtest(data: dict, n=60, entry_z=-2.0, exit_z=0.0, top_n=5, cost=0.001) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = 1_000_000
    holdings = {}
    trades = []
    eq_curve = []
    zs = {t: _ou_z(df["close"], n) for t, df in data.items()}
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
            z_ser = zs[t].loc[:d]
            if z_ser.empty or pd.isna(z_ser.iloc[-1]):
                continue
            if z_ser.iloc[-1] < entry_z:
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