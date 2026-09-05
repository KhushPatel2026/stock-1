"""Ichimoku cloud — long when close above Senkou A/B and Tenkan > Kijun; exit on close < Kijun."""
import pandas as pd
import numpy as np

META = {
    "name": "Ichimoku Cloud",
    "family": "Trend",
    "params": {"tenkan_n": 9, "kijun_n": 26, "senkou_b_n": 52, "shift": 26, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Long above both Senkou spans with Tenkan > Kijun; exit when close drops below Kijun.",
}

def _ichimoku(df: pd.DataFrame, t_n: int, k_n: int, sb_n: int, shift: int):
    high, low = df["high"], df["low"]
    tenkan = (high.rolling(t_n).max() + low.rolling(t_n).min()) / 2
    kijun = (high.rolling(k_n).max() + low.rolling(k_n).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(shift)
    senkou_b = ((high.rolling(sb_n).max() + low.rolling(sb_n).min()) / 2).shift(shift)
    return tenkan, kijun, senkou_a, senkou_b

def _entry(df: pd.DataFrame, t_n: int, k_n: int, sb_n: int, shift: int) -> pd.Series:
    close = df["close"]
    tenkan, kijun, senkou_a, senkou_b = _ichimoku(df, t_n, k_n, sb_n, shift)
    return (close > senkou_a) & (close > senkou_b) & (tenkan > kijun)

def _exit(df: pd.DataFrame, t_n: int, k_n: int, sb_n: int, shift: int) -> pd.Series:
    close = df["close"]
    _, kijun, _, _ = _ichimoku(df, t_n, k_n, sb_n, shift)
    return close < kijun

def backtest(data: dict, tenkan_n=9, kijun_n=26, senkou_b_n=52, shift=26, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    entry_sig = {t: _entry(df, tenkan_n, kijun_n, senkou_b_n, shift) for t, df in data.items()}
    exit_sig = {t: _exit(df, tenkan_n, kijun_n, senkou_b_n, shift) for t, df in data.items()}
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
