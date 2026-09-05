"""Vol Targeting Portfolio — inverse-vol weights on top-10 momentum, daily rebalance."""
import pandas as pd
import numpy as np

META = {
    "name": "Vol Targeting Portfolio",
    "family": "Volatility",
    "params": {"target_vol": 0.15, "vol_n": 20, "top_n": 10, "lookback": 252, "max_w": 0.1, "cost_bps": 1.0},
    "description": "Inverse-vol weighting on monthly top-10 by 12M momentum; daily rebalance; 1bps turnover cost.",
}

def backtest(data: dict, target_vol=0.15, vol_n=20, top_n=10, lookback=252, max_w=0.1, cost_bps=1.0) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    months = pd.Series(all_dates).dt.to_period("M").unique() if all_dates else []
    month_ends = [max([d for d in all_dates if pd.Period(d, freq="M") == p]) for p in months]
    cost = cost_bps / 10000
    cash = 1_000_000
    holdings = {}
    target_w = {}
    trades = []
    eq_curve = []
    for d in all_dates:
        if d in month_ends:
            ranks = []
            for t, df in data.items():
                if d not in df.index:
                    continue
                idx = df.index.get_loc(d)
                if idx < lookback:
                    continue
                ret12 = float(df["close"].iloc[idx] / df["close"].iloc[idx - lookback] - 1)
                ranks.append((t, ret12))
            ranks.sort(key=lambda x: -x[1])
            investable = [t for t, _ in ranks[:top_n]]
            ivs = {}
            for t in investable:
                rets = data[t]["close"].pct_change().iloc[-vol_n:].dropna()
                if len(rets) >= vol_n - 2:
                    v = float(rets.std())
                    if v > 0:
                        ann_v = v * np.sqrt(252)
                        if ann_v > 0:
                            ivs[t] = target_vol / ann_v
            clipped = {t: min(w, max_w) for t, w in ivs.items()}
            total = sum(clipped.values())
            target_w = {t: w / total for t, w in clipped.items()} if total > 0 else {}
        if target_w:
            port_val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
            for t in list(target_w.keys()):
                if d not in data[t].index:
                    continue
                price = float(data[t].loc[d, "close"])
                tgt = int((port_val * target_w[t]) // price)
                cur = holdings.get(t, 0)
                diff = tgt - cur
                if diff > 0:
                    amt = diff * price * (1 + cost)
                    if amt <= cash:
                        cash -= amt
                        holdings[t] = tgt
                        trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": diff})
                elif diff < 0:
                    cash += (-diff) * price * (1 - cost)
                    if tgt == 0:
                        del holdings[t]
                    else:
                        holdings[t] = tgt
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": price, "shares": -diff})
        for t in list(holdings.keys()):
            if t not in target_w and d in data[t].index:
                price = float(data[t].loc[d, "close"])
                cash += holdings[t] * price * (1 - cost)
                trades.append({"ticker": t, "date": d, "action": "sell", "price": price, "shares": holdings[t]})
                del holdings[t]
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq