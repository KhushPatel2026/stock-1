"""Betting Against Beta (BAB) — Frazzini & Pedersen (AQR, 2014).

Long low-beta assets weighted by inverse beta (1/beta), capturing the anomaly
where low-beta assets deliver superior risk-adjusted returns due to institutional
leverage constraints.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def backtest(
    data: dict[str, pd.DataFrame],
    lookback_beta: int = 252,
    top_n: int = 5,
    cost: float = 0.001,
    capital: float = 1_000_000,
) -> tuple[list[dict], pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    if not all_dates:
        return [], pd.DataFrame(columns=["equity"])

    # Precompute daily returns for all tickers
    rets: dict[str, pd.Series] = {}
    for t, df in data.items():
        if df is not None and len(df) > 1 and "close" in df:
            rets[t] = df["close"].pct_change()

    months = pd.Series(all_dates).dt.to_period("M").unique()
    month_ends = []
    for p in months:
        ds = [d for d in all_dates if pd.Period(d, freq="M") == p]
        if ds:
            month_ends.append(max(ds))

    cash = capital
    holdings: dict[str, int] = {}
    trades: list[dict] = []
    eq_curve: list[dict] = []

    for d in all_dates:
        if d in month_ends:
            # Calculate market return proxy (equal-weighted average return on date d)
            betas: list[tuple[str, float]] = []
            for t, r_series in rets.items():
                if d not in r_series.index:
                    continue
                loc = r_series.index.get_loc(d)
                if loc < lookback_beta:
                    continue
                # 252-day window
                stock_ret = r_series.iloc[loc - lookback_beta + 1 : loc + 1]
                # Market proxy
                mkt_ret = pd.DataFrame([rets[k].iloc[loc - lookback_beta + 1 : loc + 1] for k in rets if len(rets[k]) > loc]).mean()
                if len(stock_ret) >= 60 and len(mkt_ret) >= 60:
                    cov = np.cov(stock_ret.dropna(), mkt_ret.dropna())
                    if cov.shape == (2, 2) and cov[1, 1] > 1e-6:
                        raw_beta = cov[0, 1] / cov[1, 1]
                        # Vasicek / Frazzini-Pedersen shrinkage towards 1.0
                        shrunk_beta = max(0.05, 0.6 * raw_beta + 0.4)
                        betas.append((t, shrunk_beta))

            # Select lowest-beta stocks
            if betas:
                betas.sort(key=lambda x: x[1])
                target_stocks = betas[:top_n]
                # Inverse-beta weighting
                inv_sum = sum(1.0 / b for _, b in target_stocks)
                target_weights = {t: (1.0 / b) / inv_sum for t, b in target_stocks}
            else:
                target_weights = {}

            # Sell positions not in target
            for t in list(holdings.keys()):
                if t not in target_weights and d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    cash += holdings[t] * price * (1 - cost)
                    trades.append({"ticker": t, "date": str(d), "action": "sell", "price": price, "shares": holdings[t]})
                    del holdings[t]

            # Reallocate
            if target_weights:
                curr_val = sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                total_port = curr_val + cash

                for t, w in target_weights.items():
                    if d not in data[t].index:
                        continue
                    price = float(data[t].loc[d, "close"])
                    target_notional = total_port * w
                    target_shares = int(target_notional // price)
                    current_shares = holdings.get(t, 0)

                    if target_shares > current_shares:
                        diff = target_shares - current_shares
                        trade_cost = diff * price * (1 + cost)
                        if cash >= trade_cost:
                            cash -= trade_cost
                            holdings[t] = current_shares + diff
                            trades.append({"ticker": t, "date": str(d), "action": "buy", "price": price, "shares": diff})
                    elif target_shares < current_shares:
                        diff = current_shares - target_shares
                        cash += diff * price * (1 - cost)
                        holdings[t] = target_shares
                        trades.append({"ticker": t, "date": str(d), "action": "sell", "price": price, "shares": diff})

        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})

    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "Betting Against Beta (BAB)",
    "family": "Factor",
    "params": {"capital": 1_000_000, "lookback_beta": 252, "top_n": 5, "cost": 0.001},
    "description": "Frazzini & Pedersen AQR anomaly: holds lowest-beta quintile weighted by inverse beta.",
}
