"""Accumulation/Distribution Line — long when A/D > A/D SMA(20) and close > SMA(50)."""
import pandas as pd
import numpy as np

META = {
    "name": "Accumulation/Distribution Line",
    "family": "Volume",
    "params": {"ad_n": 20, "sma_n": 50, "max_holdings": 5, "cost": 0.001},
    "description": "A/D = cumsum(MFM * volume); long when A/D > SMA(A/D,20) and close > SMA(close,50).",
}

def _ad(df: pd.DataFrame) -> pd.Series:
    rng_ = df["high"] - df["low"]
    mfm = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / rng_.replace(0, np.nan)
    mfm = mfm.fillna(0)
    return (mfm * df["volume"]).cumsum()

def _signal(df: pd.DataFrame, ad_n: int, sma_n: int) -> tuple[pd.Series, pd.Series]:
    ad = _ad(df)
    ad_sma = ad.rolling(ad_n).mean()
    sma = df["close"].rolling(sma_n).mean()
    entry = (ad > ad_sma) & (df["close"] > sma)
    exit_ = (ad < ad_sma) | (df["close"] < sma)
    return entry, exit_

def backtest(data: dict, ad_n=20, sma_n=50, max_holdings=5, cost=0.001) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = 1_000_000
    holdings = {}
    trades = []
    eq_curve = []
    entry_sig, exit_sig = {}, {}
    for t, df in data.items():
        e, x = _signal(df, ad_n, sma_n)
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