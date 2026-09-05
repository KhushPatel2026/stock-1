"""Value factor — price-vs-SMA200 discount, long top decile by discount, monthly rebalance."""
# ponytail: real value uses P/B or P/E; SMA200 discount is a price-derived proxy
import pandas as pd
import numpy as np

META = {
    "name": "value",
    "family": "Factor",
    "params": {"top_decile": 0.2, "cost": 0.001},
    "description": "Long top decile by (SMA200 - close)/close discount, equal-weight, monthly rebalance. SMA200 proxy for fair value.",
}

def _rank_at(data: dict, date) -> pd.DataFrame:
    rows = []
    for t, df in data.items():
        if date not in df.index:
            continue
        idx = df.index.get_loc(date)
        if idx < 200:
            continue
        close = df["close"]
        sma200 = float(close.iloc[idx - 199: idx + 1].mean())
        px = float(close.iloc[idx])
        score = (sma200 - px) / px if px > 0 else 0
        rows.append({"ticker": t, "sma200": sma200, "close": px, "score": score})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("score", ascending=False)

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
