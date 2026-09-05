"""Low-volatility factor — long bottom decile by 60d annualized vol, monthly rebalance."""
import pandas as pd
import numpy as np

META = {
    "name": "low_vol",
    "family": "Factor",
    "params": {"top_decile": 0.2, "cost": 0.001},
    "description": "Long bottom decile by 60d annualized realized vol, equal-weight, monthly rebalance.",
}

def _rank_at(data: dict, date) -> pd.DataFrame:
    rows = []
    for t, df in data.items():
        if date not in df.index:
            continue
        idx = df.index.get_loc(date)
        if idx < 60:
            continue
        rets = df["close"].pct_change().iloc[idx - 60 + 1: idx + 1]
        if len(rets) < 60:
            continue
        vol = float(rets.std()) * np.sqrt(252)
        rows.append({"ticker": t, "vol": vol})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("vol", ascending=True)

def backtest(data: dict, top_decile=0.2, cost=0.001) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    months = pd.Series(all_dates).dt.to_period("M").unique()
    month_ends = []
    for p in months:
        ds = [d for d in all_dates if pd.Period(d, freq="M") == p]
        if ds:
            month_ends.append(max(ds))
    cash = 1_000_000
    holdings = {}
    trades = []
    eq_curve = []
    for d in all_dates:
        if d in month_ends:
            ranked = _rank_at(data, d)
            n = max(1, int(len(ranked) * top_decile)) if not ranked.empty else 0
            top = ranked.head(n)["ticker"].tolist() if not ranked.empty else []
            for t in list(holdings.keys()):
                if t not in top and d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    cash += holdings[t] * price * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": price, "shares": holdings[t]})
                    del holdings[t]
            if top:
                cur_val = sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                port = cur_val + cash
                slot = max(n, len(holdings) + len(top))
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
