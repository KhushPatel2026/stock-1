"""Money Flow Index mean reversion — volume-weighted RSI on typical price, oversold bounce."""
import pandas as pd
import numpy as np

META = {
    "name": "Money Flow Index",
    "family": "MR",
    "params": {"n": 14, "oversold": 20, "exit_level": 50, "top_n": 5, "cost": 0.001},
    "description": "Long when MFI(14) < 20; exit when MFI > 50.",
}

def _mfi(df: pd.DataFrame, n: int) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    mf = tp * df["volume"]
    direction = np.sign(tp.diff()).fillna(0)
    pos = mf.where(direction > 0, 0.0)
    neg = mf.where(direction < 0, 0.0)
    sum_pos = pos.rolling(n).sum()
    sum_neg = neg.rolling(n).sum()
    ratio = sum_pos / sum_neg.replace(0, np.nan)
    return 100 - 100 / (1 + ratio)

def backtest(data: dict, n=14, oversold=20, exit_level=50, top_n=5, cost=0.001) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = 1_000_000
    holdings = {}
    trades = []
    eq_curve = []
    mfis = {t: _mfi(df, n) for t, df in data.items()}
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                m = mfis[t].loc[:d].iloc[-1] if len(mfis[t].loc[:d]) else np.nan
                if pd.isna(m) or m > exit_level:
                    close = float(data[t].loc[d, "close"])
                    cash += holdings[t] * close * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                    del holdings[t]
        candidates = []
        for t, df in data.items():
            if t in holdings or d not in df.index:
                continue
            m_ser = mfis[t].loc[:d]
            if m_ser.empty or pd.isna(m_ser.iloc[-1]):
                continue
            if m_ser.iloc[-1] < oversold:
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