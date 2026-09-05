"""Parabolic SAR — long when PSAR < close, exit when PSAR > close (Wilder accel 0.02..0.2)."""
import pandas as pd
import numpy as np

META = {
    "name": "Parabolic SAR",
    "family": "Trend",
    "params": {"accel": 0.02, "max_accel": 0.2, "top_n": 5, "cost": 0.001},
    "description": "Wilder PSAR; long when PSAR sits below close, exit when PSAR flips above.",
}

def _psar(df: pd.DataFrame, accel: float, max_accel: float) -> tuple[pd.Series, pd.Series]:
    high, low, close = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    n = len(df)
    psar = np.full(n, np.nan)
    trend = np.zeros(n, dtype=int)
    if n < 2:
        return pd.Series(psar, index=df.index), pd.Series(trend, index=df.index)
    psar[0] = low[0]
    trend[0] = 1  # start uptrend
    ep = high[0]
    af = accel
    for i in range(1, n):
        prev_psar = psar[i - 1]
        if trend[i - 1] == 1:
            new_psar = prev_psar + af * (ep - prev_psar)
            if i >= 2:
                new_psar = min(new_psar, low[i - 1], low[i - 2])
            else:
                new_psar = min(new_psar, low[i - 1])
            if low[i] < new_psar:
                trend[i] = -1
                psar[i] = ep
                ep = low[i]
                af = accel
            else:
                trend[i] = 1
                psar[i] = new_psar
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + accel, max_accel)
        else:
            new_psar = prev_psar + af * (ep - prev_psar)
            if i >= 2:
                new_psar = max(new_psar, high[i - 1], high[i - 2])
            else:
                new_psar = max(new_psar, high[i - 1])
            if high[i] > new_psar:
                trend[i] = 1
                psar[i] = ep
                ep = high[i]
                af = accel
            else:
                trend[i] = -1
                psar[i] = new_psar
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + accel, max_accel)
    return pd.Series(psar, index=df.index), pd.Series(trend, index=df.index)

def _signal(df: pd.DataFrame, accel: float, max_accel: float) -> tuple[pd.Series, pd.Series]:
    psar, trend = _psar(df, accel, max_accel)
    close = df["close"]
    return psar < close, psar > close

def backtest(data: dict, accel=0.02, max_accel=0.2, top_n=5, cost=0.001) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = 1_000_000
    holdings = {}
    trades = []
    eq_curve = []
    entry_sig = {}
    exit_sig = {}
    for t, df in data.items():
        long, short = _signal(df, accel, max_accel)
        entry_sig[t] = long
        exit_sig[t] = short
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
