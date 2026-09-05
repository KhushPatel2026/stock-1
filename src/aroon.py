"""Aroon trend — long when Aroon Up > 80 and above Aroon Down; exit on Aroon Down > 50."""
import pandas as pd
import numpy as np

META = {
    "name": "Aroon Trend",
    "family": "Trend",
    "params": {"n": 25, "up_thresh": 80, "down_thresh": 50, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Long on Aroon Up breakout above threshold with Up > Down; exit when Down turns strong.",
}

def _aroon_up(high: pd.Series, n: int) -> pd.Series:
    days_since = high.rolling(n + 1).apply(lambda x: n - int(np.argmax(x[::-1])), raw=True)
    return ((n - days_since) / n) * 100

def _aroon_down(low: pd.Series, n: int) -> pd.Series:
    days_since = low.rolling(n + 1).apply(lambda x: n - int(np.argmin(x[::-1])), raw=True)
    return ((n - days_since) / n) * 100

def _entry(df: pd.DataFrame, n: int, up_thresh: int) -> pd.Series:
    up = _aroon_up(df["high"], n)
    dn = _aroon_down(df["low"], n)
    return (up > up_thresh) & (up > dn)

def _exit(df: pd.DataFrame, n: int, down_thresh: int) -> pd.Series:
    return _aroon_down(df["low"], n) > down_thresh

def backtest(data: dict, n=25, up_thresh=80, down_thresh=50, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    entry_sig = {t: _entry(df, n, up_thresh) for t, df in data.items()}
    exit_sig = {t: _exit(df, n, down_thresh) for t, df in data.items()}
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
