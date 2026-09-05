"""Volatility Breakout — long when 1-day move exceeds k×ATR(14), exit next bar."""
import pandas as pd
from src.indicators import atr

META = {
    "name": "Volatility Breakout",
    "family": "Volatility",
    "params": {"k": 1.0, "atr_n": 14, "cost": 0.0005, "capital": 1_000_000},
    "description": "Long when (close - prev_close) > k * ATR(14); exit next bar (one-day hold).",
}

def _signal(df: pd.DataFrame, k: float, atr_n: int) -> pd.Series:
    a = atr(df, atr_n)
    move = df["close"] - df["close"].shift(1)
    return move > k * a

def backtest(data: dict, k=1.0, atr_n=14, cost=0.0005, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    sig = {t: _signal(df, k, atr_n) for t, df in data.items()}
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                close = float(data[t].loc[d, "close"])
                cash += holdings[t] * close * (1 - cost)
                trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                del holdings[t]
        candidates = [t for t, df in data.items()
                     if t not in holdings and d in df.index
                     and len(sig[t].loc[:d]) and bool(sig[t].loc[:d].iloc[-1])]
        if candidates and cash > 0:
            notional = cash / len(candidates)
            for t in candidates:
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