"""Engulfing Pattern — bullish engulfing: prev red, current green, current close > prev open; hold 5 bars."""
import pandas as pd

META = {
    "name": "Engulfing Pattern",
    "family": "Pattern",
    "params": {"hold_bars": 5, "max_holdings": 5, "cost": 0.001},
    "description": "Bullish engulfing (prev red, current green, current close > prev open); long next bar, hold 5 bars.",
}

def _signal(df: pd.DataFrame) -> pd.Series:
    prev_red = df["close"].shift(1) < df["open"].shift(1)
    cur_green = df["close"] > df["open"]
    engulf = cur_green & prev_red & (df["close"] > df["open"].shift(1))
    return engulf.fillna(False)

def backtest(data: dict, hold_bars=5, max_holdings=5, cost=0.001) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = 1_000_000
    holdings = {}
    entry_bar_idx = {}
    bar_index_map = {t: {d: i for i, d in enumerate(df.index)} for t, df in data.items()}
    sig = {t: _signal(df) for t, df in data.items()}
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