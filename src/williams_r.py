"""Williams %R mean reversion — long on deeply oversold, exit on recovery to mid-range."""
import pandas as pd
import numpy as np

META = {
    "name": "Williams %R",
    "family": "MR",
    "params": {"n": 14, "oversold": -80, "exit_level": -50, "top_n": 5, "cost": 0.001},
    "description": "Long when %R < -80; exit when %R > -50.",
}

def _williams_r(close: pd.Series, high: pd.Series, low: pd.Series, n: int) -> pd.Series:
    hh = high.rolling(n).max()
    ll = low.rolling(n).min()
    return (hh - close) / (hh - ll).replace(0, np.nan) * -100

def backtest(data: dict, n=14, oversold=-80, exit_level=-50, top_n=5, cost=0.001) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = 1_000_000
    holdings = {}
    trades = []
    eq_curve = []
    wrs = {t: _williams_r(df["close"], df["high"], df["low"], n) for t, df in data.items()}
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                w = wrs[t].loc[:d].iloc[-1] if len(wrs[t].loc[:d]) else np.nan
                if pd.isna(w) or w > exit_level:
                    close = float(data[t].loc[d, "close"])
                    cash += holdings[t] * close * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                    del holdings[t]
        candidates = []
        for t, df in data.items():
            if t in holdings or d not in df.index:
                continue
            w_ser = wrs[t].loc[:d]
            if w_ser.empty or pd.isna(w_ser.iloc[-1]):
                continue
            if w_ser.iloc[-1] < oversold:
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