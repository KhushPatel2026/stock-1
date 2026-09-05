"""Volume-Price Trend (VPT) — long when VPT > VPT SMA(20) and close > SMA(50)."""
import pandas as pd

META = {
    "name": "Volume-Price Trend",
    "family": "Volume",
    "params": {"vpt_n": 20, "sma_n": 50, "max_holdings": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "VPT = cumsum(vol * pct_change); long when VPT > SMA(VPT,20) and close > SMA(close,50).",
}

def _vpt(df: pd.DataFrame) -> pd.Series:
    ret = df["close"].pct_change().fillna(0)
    return (df["volume"] * ret).cumsum()

def _signal(df: pd.DataFrame, vpt_n: int, sma_n: int) -> tuple[pd.Series, pd.Series]:
    vpt = _vpt(df)
    vpt_sma = vpt.rolling(vpt_n).mean()
    sma = df["close"].rolling(sma_n).mean()
    entry = (vpt > vpt_sma) & (df["close"] > sma)
    exit_ = (vpt < vpt_sma) | (df["close"] < sma)
    return entry, exit_

def backtest(data: dict, vpt_n=20, sma_n=50, max_holdings=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    entry_sig, exit_sig = {}, {}
    for t, df in data.items():
        e, x = _signal(df, vpt_n, sma_n)
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