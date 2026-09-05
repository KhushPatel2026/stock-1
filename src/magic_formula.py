"""Magic formula (Greenblatt) — earnings-yield + ROE composite rank, monthly rebalance.

When use_real_fundamentals=True, pulls yfinance .info via src.fundamentals and uses
real EBIT/EV and ROE when available, falling back to the price-proxied values
(see ADR-005) for tickers where fundamentals are missing/invalid.
"""
import pandas as pd
from src.fundamentals import fetch_many_fundamentals

KEYS = ("market_cap", "enterprise_value", "ebit", "return_on_equity", "earnings_yield")


def _is_valid(row: dict | None) -> bool:
    if not row:
        return False
    return row.get("earnings_yield") is not None and row.get("return_on_equity") is not None


def _rank_at(data: dict, date, fundamentals: dict | None = None) -> pd.DataFrame:
    rows = []
    for t, df in data.items():
        if date not in df.index:
            continue
        idx = df.index.get_loc(date)
        if idx < 252:
            continue
        close = df["close"]
        ey_proxy = float(close.iloc[idx] / close.iloc[idx - 252] - 1)
        rets = close.pct_change().iloc[idx - 60 + 1: idx + 1]
        vol = float(rets.std()) if len(rets) == 60 else 0
        roe_proxy = ey_proxy / vol if vol > 0 else 0
        row = {"ticker": t, "ey": ey_proxy, "roe": roe_proxy}
        if fundamentals and t in fundamentals and _is_valid(fundamentals[t]):
            row["ey"] = float(fundamentals[t]["earnings_yield"])
            row["roe"] = float(fundamentals[t]["return_on_equity"])
            row["src"] = "real"
        else:
            row["src"] = "proxy"
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    for c in ["ey", "roe"]:
        m, s = out[c].mean(), out[c].std()
        out[c + "_z"] = (out[c] - m) / (s if s and s > 0 else 1)
    out["score"] = out["ey_z"] + out["roe_z"]
    return out.sort_values("score", ascending=False)


def backtest(data: dict, top_decile=0.2, cost=0.001, use_real_fundamentals=True) -> tuple[list, pd.DataFrame]:
    fundamentals: dict | None = None
    if use_real_fundamentals:
        try:
            fundamentals = fetch_many_fundamentals(list(data.keys()))
        except Exception:
            fundamentals = None

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
            ranked = _rank_at(data, d, fundamentals)
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


META = {
    "name": "Magic Formula (Greenblatt)",
    "family": "Factor",
    "params": {"top_n": 5, "cost": 0.001, "use_real_fundamentals": True},
    "description": "EY+ROE composite z-score; real yfinance .info when available, price-proxied fallback (ADR-005).",
}
