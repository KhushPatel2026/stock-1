"""Risk parity — inverse-volatility weighting, monthly selection (top 12M momentum) + daily rebalance."""
import pandas as pd

def backtest(data: dict, lookback=60, top_n=10, cost_bps=1, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    months = pd.Series(all_dates).dt.to_period("M").unique()
    month_ends = []
    for p in months:
        ds = [d for d in all_dates if pd.Period(d, freq="M") == p]
        if ds:
            month_ends.append(max(ds))
    cash = capital
    holdings = {}
    target_w = {}
    trades = []
    eq_curve = []
    cost = cost_bps / 10000
    for d in all_dates:
        if d in month_ends:
            ranks = []
            for t, df in data.items():
                if d not in df.index:
                    continue
                idx = df.index.get_loc(d)
                if idx < 252:
                    continue
                ret12 = float(df["close"].iloc[idx] / df["close"].iloc[idx - 252] - 1)
                ranks.append((t, ret12))
            ranks.sort(key=lambda x: -x[1])
            investable = [t for t, _ in ranks[:top_n]]
            inv_vols = {}
            for t in investable:
                rets = data[t]["close"].pct_change().iloc[-lookback:].dropna()
                if len(rets) >= lookback - 5:
                    v = float(rets.std())
                    if v > 0:
                        inv_vols[t] = 1 / v
            total = sum(inv_vols.values())
            target_w = {t: iv / total for t, iv in inv_vols.items()} if total > 0 else {}
            for t in list(holdings.keys()):
                if t not in target_w and d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    cash += holdings[t] * price * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": price, "shares": holdings[t]})
                    del holdings[t]
        if target_w:
            port_val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
            for t, w in target_w.items():
                if d not in data[t].index:
                    continue
                price = float(data[t].loc[d, "close"])
                tgt = int((port_val * w) // price)
                cur = holdings.get(t, 0)
                diff = tgt - cur
                if diff > 0:
                    cost_amt = diff * price * (1 + cost)
                    if cost_amt <= cash:
                        cash -= cost_amt
                        holdings[t] = tgt
                        trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": diff})
                elif diff < 0:
                    cash += (-diff) * price * (1 - cost)
                    if tgt == 0:
                        del holdings[t]
                    else:
                        holdings[t] = tgt
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": price, "shares": -diff})
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "Risk Parity (Inverse Vol)",
    "family": "Allocation",
    "params": {"capital": 1_000_000, "top_n": 5, "cost": 0.001},
    "description": "Inverse-vol weighting, daily rebalance.",
}
