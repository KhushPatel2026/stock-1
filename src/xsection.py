"""Cross-sectional momentum + reversals — monthly rank-sort, dollar-neutral.

Three strategies, one loop (scores differ only):
- xs_momentum: 12M return skipping most recent month (Jegadeesh-Titman / Moskowitz 12-1)
- st_reversal: fade past-1M return (Jegadeesh 1990 / Lehmann weekly)
- lt_reversal: fade past-2Y return (De Bondt-Thaler long-term reversal; 2Y proxy — 3-5Y needs longer history)
"""
import pandas as pd
import numpy as np

META = {
    "name": "xs_momentum",
    "family": "Momentum",
    "params": {"top_decile": 0.2, "cost": 0.001, "capital": 1_000_000},
    "description": "Long top decile / short bottom decile by 12-1M momentum, monthly.",
}


def _month_ends(all_dates):
    months = pd.Series(all_dates).dt.to_period("M").unique() if all_dates else []
    ends = []
    for p in months:
        ds = [d for d in all_dates if pd.Period(d, freq="M") == p]
        if ds:
            ends.append(max(ds))
    return ends


def _score_12_1(df, idx, lookback=252, skip=21):
    if idx < lookback:
        return None
    base = df["close"].iloc[idx - skip]
    past = df["close"].iloc[idx - lookback]
    return float(base / past - 1) if past != 0 else None


def _score_st_rev(df, idx, lookback=21):
    if idx < lookback:
        return None
    return -float(df["close"].iloc[idx] / df["close"].iloc[idx - lookback] - 1)


def _score_lt_rev(df, idx, lookback=504):
    if idx < lookback:
        return None
    return -float(df["close"].iloc[idx] / df["close"].iloc[idx - lookback] - 1)


def _run(data, score_fn, top_decile=0.2, cost=0.001, capital=1_000_000):
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    month_ends = _month_ends(all_dates)
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    for d in all_dates:
        if d in month_ends:
            for t, sh in list(holdings.items()):
                if d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    cash += sh * price * (1 - cost * np.sign(sh))
                    trades.append({"ticker": t, "date": d, "action": "close", "shares": sh, "price": price})
            holdings.clear()
            scored = []
            for t, df in data.items():
                if d not in df.index:
                    continue
                s = score_fn(df, df.index.get_loc(d))
                if s is not None and not pd.isna(s):
                    scored.append((t, s))
            scored.sort(key=lambda x: x[1])
            n = max(1, int(len(scored) * top_decile))
            shorts = [t for t, _ in scored[:n]]
            longs = [t for t, _ in scored[-n:]]
            if longs or shorts:
                for t in longs:
                    price = float(data[t].loc[d, "close"])
                    shares = int((capital * 0.5 / max(1, len(longs))) // price)
                    if shares:
                        cash -= shares * price * (1 + cost)
                        holdings[t] = holdings.get(t, 0) + shares
                        trades.append({"ticker": t, "date": d, "action": "long", "shares": shares, "price": price})
                for t in shorts:
                    price = float(data[t].loc[d, "close"])
                    shares = int((capital * 0.5 / max(1, len(shorts))) // price)
                    if shares:
                        cash += shares * price * (1 - cost)
                        holdings[t] = holdings.get(t, 0) - shares
                        trades.append({"ticker": t, "date": d, "action": "short", "shares": -shares, "price": price})
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


def backtest(data, top_decile=0.2, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    """Cross-sectional momentum 12-1: long winners, short losers."""
    return _run(data, _score_12_1, top_decile, cost, capital)


def backtest_st(data, top_decile=0.2, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    """Short-term reversal: long 1M losers, short 1M winners."""
    return _run(data, _score_st_rev, top_decile, cost, capital)


def backtest_lt(data, top_decile=0.2, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    """Long-term reversal: long 2Y losers, short 2Y winners."""
    return _run(data, _score_lt_rev, top_decile, cost, capital)
