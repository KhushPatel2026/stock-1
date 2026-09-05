"""Hull moving average — long when close > HMA, exit when close < HMA."""
import pandas as pd
import numpy as np

META = {
    "name": "Hull Moving Average",
    "family": "Trend",
    "params": {"n": 20, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "HMA = WMA(2*WMA(n/2) - WMA(n), sqrt(n)); long on close > HMA, exit on close < HMA.",
}

def _wma(s: pd.Series, n: int) -> pd.Series:
    weights = np.arange(1, n + 1, dtype=float)
    weights /= weights.sum()
    return s.rolling(n).apply(lambda x: float((x * weights).sum()), raw=True)

def _hma(close: pd.Series, n: int) -> pd.Series:
    half = max(2, n // 2)
    sqrt_n = max(2, int(round(np.sqrt(n))))
    fast = _wma(close, half)
    slow = _wma(close, n)
    return _wma(2 * fast - slow, sqrt_n)

def _signal(df: pd.DataFrame, n: int) -> tuple[pd.Series, pd.Series]:
    h = _hma(df["close"], n)
    return df["close"] > h, df["close"] < h

def backtest(data: dict, n=20, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    entry_sig = {}
    exit_sig = {}
    for t, df in data.items():
        long, short = _signal(df, n)
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
