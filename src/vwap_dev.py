"""VWAP Deviation — long when close < rolling-VWAP * 0.98 and close > SMA(200)."""
import pandas as pd
import numpy as np

META = {
    "name": "VWAP Deviation",
    "family": "Volume",
    "params": {"vwap_n": 20, "sma_n": 200, "dev": 0.98, "max_holdings": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Rolling VWAP (20-bar proxy for daily VWAP); long when close < 0.98*VWAP and above SMA(200); exit at VWAP.",
}

def _vwap(df: pd.DataFrame, n: int) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    pvol = tp * df["volume"]
    num = pvol.rolling(n).sum()
    den = df["volume"].rolling(n).sum()
    return num / den.replace(0, np.nan)

def _signal(df: pd.DataFrame, n: int, sma_n: int, dev: float) -> tuple[pd.Series, pd.Series]:
    vwap = _vwap(df, n)
    sma = df["close"].rolling(sma_n).mean()
    entry = (df["close"] < vwap * dev) & (df["close"] > sma)
    exit_ = df["close"] >= vwap
    return entry, exit_

def backtest(data: dict, vwap_n=20, sma_n=200, dev=0.98, max_holdings=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    entry_sig, exit_sig = {}, {}
    for t, df in data.items():
        e, x = _signal(df, vwap_n, sma_n, dev)
        entry_sig[t], exit_sig[t] = e, x
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index and len(exit_sig[t].loc[:d]) and bool(exit_sig[t].loc[:d].iloc[-1]):
                close = float(data[t].loc[d, "close"])
                cash += holdings[t] * close * (1 - cost)
                trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                del holdings[t]
        if len(holdings) < max_holdings:
            for t, df in data.items():
                if t in holdings or d not in df.index:
                    continue
                if len(entry_sig[t].loc[:d]) and bool(entry_sig[t].loc[:d].iloc[-1]):
                    price = float(data[t].loc[d, "close"])
                    slot_cash = cash / max(1, max_holdings - len(holdings))
                    shares = int(slot_cash // price)
                    if shares > 0 and shares * price * (1 + cost) <= cash:
                        cash -= shares * price * (1 + cost)
                        holdings[t] = shares
                        trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": shares})
                        if len(holdings) >= max_holdings:
                            break
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq