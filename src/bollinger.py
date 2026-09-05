"""Bollinger band mean reversion — single-stock, 20-day window, 2σ, SMA200 trend filter."""
import pandas as pd

def _entry_signal(df: pd.DataFrame, window=20, k=2.0) -> pd.Series:
    close = df["close"]
    sma = close.rolling(window).mean()
    sd = close.rolling(window).std()
    lower = sma - k * sd
    sma200 = close.rolling(200).mean()
    return (close < lower) & (close > sma200)

def backtest(data: dict, top_n=10, cost=0.0005, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                close = float(data[t].loc[d, "close"])
                sma20 = float(data[t]["close"].rolling(20).mean().loc[:d].iloc[-1])
                if pd.isna(sma20) or close >= sma20:
                    cash += holdings[t] * close * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                    del holdings[t]
        candidates = []
        for t, df in data.items():
            if t in holdings or d not in df.index:
                continue
            sig = _entry_signal(df).loc[:d]
            if len(sig) and bool(sig.iloc[-1]):
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


META = {
    "name": "Bollinger Mean Reversion",
    "family": "MR",
    "params": {"top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "20d SMA ±2σ with SMA200 trend filter.",
}
