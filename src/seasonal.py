"""Calendar seasonals — time-based long exposure on the equal-weight basket.

- turn_of_month: invested only on the last trading day + first 3 trading days
  of each month (classic TOM effect), cash otherwise.
- expiry_drift: invested only on Thursdays (NSE weekly expiry day) — expiry-day
  drift proxy. Enter Wed close, exit Thu close.
"""
import pandas as pd
import numpy as np

META = {
    "name": "turn_of_month",
    "family": "Seasonal",
    "params": {"pre_days": 1, "post_days": 3, "cost": 0.0002, "capital": 1_000_000},
    "description": "Long basket on last-1 + first-3 trading days of month.",
}


def _basket(data: dict):
    tickers = [t for t in data if not data[t].empty]
    all_dates = sorted(set().union(*(set(data[t].index) for t in tickers)))
    proxy = pd.concat([data[t]["close"].rename(t) for t in tickers], axis=1).mean(axis=1).reindex(all_dates)
    return proxy, proxy.pct_change()


def _run_windows(data: dict, in_window: pd.Series, cost=0.0002, label="SEASONAL", capital=1_000_000):
    proxy, rets = _basket(data)
    cash, invested, trades, eq_curve = float(capital), 0.0, [], []
    was_in = False
    for d in proxy.index[1:]:
        want_in = bool(in_window.loc[d])
        r = float(rets.loc[d]) if not pd.isna(rets.loc[d]) else 0.0
        if want_in and not was_in:
            port = cash + invested
            invested = port * (1 - cost)
            cash = 0.0
            trades.append({"ticker": label, "date": d, "action": "buy", "shares": 1, "price": float(proxy.loc[d])})
        elif not want_in and was_in:
            cash = (cash + invested) * (1 - cost)
            invested = 0.0
            trades.append({"ticker": label, "date": d, "action": "sell", "shares": 1, "price": float(proxy.loc[d])})
        was_in = want_in
        invested *= (1 + r)
        eq_curve.append({"date": d, "equity": float(cash + invested)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


def backtest(data: dict, pre_days=1, post_days=3, cost=0.0002, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    """Turn-of-month: long last `pre_days` + first `post_days` trading days."""
    proxy, _ = _basket(data)
    months = proxy.index.to_period("M")
    pos_in_month = proxy.groupby(months).cumcount() + 1
    month_len = proxy.groupby(months).transform("size")
    in_window = ((month_len - pos_in_month) < pre_days) | (pos_in_month <= post_days)
    return _run_windows(data, in_window, cost, label="TOM", capital=capital)


def backtest_expiry(data: dict, cost=0.0002, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    """Expiry-day drift: long basket on Thursdays (NSE weekly expiry)."""
    proxy, _ = _basket(data)
    in_window = pd.Series(proxy.index.weekday == 3, index=proxy.index)
    return _run_windows(data, in_window, cost, label="EXPIRY", capital=capital)
