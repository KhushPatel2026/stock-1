"""RSI(2) mean reversion — Connors-style short-horizon reversal, exit on 5d SMA cross."""
import pandas as pd
import numpy as np

def _rsi(close: pd.Series, n=2) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1/n, adjust=False).mean()
    roll_down = down.ewm(alpha=1/n, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def backtest(data: dict, rsi_thresh=5, exit_ma=5, max_n=5, cost=0.0005, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                close = float(data[t].loc[d, "close"])
                sma = float(data[t]["close"].rolling(exit_ma).mean().loc[:d].iloc[-1])
                if pd.isna(sma) or close > sma:
                    cash += holdings[t] * close * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                    del holdings[t]
        if len(holdings) < max_n:
            for t, df in data.items():
                if t in holdings or d not in df.index:
                    continue
                rsi = _rsi(df["close"]).loc[:d]
                if rsi.empty or pd.isna(rsi.iloc[-1]):
                    continue
                if rsi.iloc[-1] < rsi_thresh:
                    price = float(df.loc[d, "close"])
                    notional = cash / max(1, max_n - len(holdings))
                    shares = int(notional // price)
                    if shares > 0:
                        cash -= shares * price * (1 + cost)
                        holdings[t] = shares
                        trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": shares})
                        if len(holdings) >= max_n:
                            break
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "RSI(2) Connors Reversal",
    "family": "MR",
    "params": {"top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Connors short-horizon reversal, exit on 5d SMA cross.",
}
