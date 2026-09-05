"""Dual momentum (Antonacci) — absolute 12M momentum gate + relative cross-section rank, monthly."""
import pandas as pd

def backtest(data: dict, lookback=252, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    months = pd.Series(all_dates).dt.to_period("M").unique()
    month_ends = []
    for p in months:
        ds = [d for d in all_dates if pd.Period(d, freq="M") == p]
        if ds:
            month_ends.append(max(ds))
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    for d in all_dates:
        if d in month_ends:
            ranked = []
            for t, df in data.items():
                if d not in df.index:
                    continue
                idx = df.index.get_loc(d)
                if idx < lookback:
                    continue
                ret = float(df["close"].iloc[idx] / df["close"].iloc[idx - lookback] - 1)
                ranked.append((t, ret))
            top = []
            if ranked:
                mkt_ret = sum(r for _, r in ranked) / len(ranked)
                if mkt_ret > 0:
                    ranked.sort(key=lambda x: -x[1])
                    top = [t for t, _ in ranked[:top_n]]
            for t in list(holdings.keys()):
                if t not in top and d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    cash += holdings[t] * price * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": price, "shares": holdings[t]})
                    del holdings[t]
            if top:
                cur_val = sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                port = cur_val + cash
                slot = max(top_n, len(holdings) + len(top))
                notional = port / slot
                for t in top:
                    if t in holdings or d not in data[t].index:
                        continue
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
    "name": "Dual Momentum (Antonacci)",
    "family": "Momentum",
    "params": {"top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "12M absolute gate + relative cross-section rank.",
}
