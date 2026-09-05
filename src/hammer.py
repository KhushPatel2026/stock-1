"""Hammer / Shooting Star — hammer: long shadow > 2x body, short shadow < body/2, in downtrend."""
import pandas as pd

META = {
    "name": "Hammer / Shooting Star",
    "family": "Pattern",
    "params": {"hold_bars": 5, "trend_n": 20, "max_holdings": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Hammer in SMA(20) downtrend → long 5 bars; shooting star short-candidates skipped (long-only).",
}

def _signal(df: pd.DataFrame, trend_n: int) -> pd.Series:
    o, h, l_, c = df["open"], df["high"], df["low"], df["close"]
    body = (c - o).abs()
    upper = h - pd.concat([c, o], axis=1).max(axis=1)
    lower = pd.concat([c, o], axis=1).min(axis=1) - l_
    sma = c.rolling(trend_n).mean()
    hammer = (lower > 2 * body) & (upper < body / 2) & (c < sma)
    return hammer.fillna(False)

def backtest(data: dict, hold_bars=5, trend_n=20, max_holdings=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    entry_bar_idx = {}
    bar_index_map = {t: {d: i for i, d in enumerate(df.index)} for t, df in data.items()}
    sig = {t: _signal(df, trend_n) for t, df in data.items()}
    trades = []
    eq_curve = []
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                idx = bar_index_map[t][d]
                if idx - entry_bar_idx[t] >= hold_bars:
                    close = float(data[t].loc[d, "close"])
                    cash += holdings[t] * close * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                    del holdings[t]
                    del entry_bar_idx[t]
        if len(holdings) < max_holdings:
            for t, df in data.items():
                if t in holdings or d not in df.index:
                    continue
                idx = bar_index_map[t][d]
                if idx < 1:
                    continue
                if not bool(sig[t].iloc[idx - 1]):
                    continue
                price = float(df.loc[d, "open"])
                slot_cash = cash / max(1, max_holdings - len(holdings))
                shares = int(slot_cash // price)
                if shares > 0 and shares * price * (1 + cost) <= cash:
                    cash -= shares * price * (1 + cost)
                    holdings[t] = shares
                    entry_bar_idx[t] = idx
                    trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": shares})
                    if len(holdings) >= max_holdings:
                        break
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq