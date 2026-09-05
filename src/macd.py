"""MACD signal crossover — long on MACD crossing above signal line, exit on cross below."""
import pandas as pd
import numpy as np

META = {
    "name": "MACD Signal",
    "family": "Trend",
    "params": {"fast": 12, "slow": 26, "signal": 9, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Long on MACD crossing above signal EMA; exit on cross below.",
}

def _macd(close: pd.Series, fast: int, slow: int, signal: int) -> tuple[pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig

def _entry(df: pd.DataFrame, fast: int, slow: int, signal: int) -> pd.Series:
    m, s = _macd(df["close"], fast, slow, signal)
    prev_diff = m.shift(1) - s.shift(1)
    cur_diff = m - s
    return (cur_diff > 0) & (prev_diff <= 0)

def _exit(df: pd.DataFrame, fast: int, slow: int, signal: int) -> pd.Series:
    m, s = _macd(df["close"], fast, slow, signal)
    prev_diff = m.shift(1) - s.shift(1)
    cur_diff = m - s
    return (cur_diff < 0) & (prev_diff >= 0)

def backtest(data: dict, fast=12, slow=26, signal=9, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    entry_sig = {t: _entry(df, fast, slow, signal) for t, df in data.items()}
    exit_sig = {t: _exit(df, fast, slow, signal) for t, df in data.items()}
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
