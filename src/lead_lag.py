"""Cross-Autoregressive Lead-Lag Information Spillover.

Exploits delayed information diffusion where high-liquidity market leaders
incorporate macroeconomic, foreign institutional, and sector news faster than
secondary constituents. Detects lead-lag relationships and enters laggards
when leaders display strong persistent momentum.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def backtest(
    data: dict[str, pd.DataFrame],
    lookback: int = 60,
    lead_thresh_sigma: float = 1.25,
    hold_days: int = 2,
    cost: float = 0.001,
    capital: float = 1_000_000,
) -> tuple[list[dict], pd.DataFrame]:
    tickers = list(data.keys())
    if len(tickers) < 2:
        return [], pd.DataFrame(columns=["equity"])

    df_closes = pd.DataFrame({t: df["close"] for t, df in data.items() if "close" in df}).dropna(how="all")
    rets = df_closes.pct_change()
    all_dates = list(rets.index)

    cash = capital
    holdings: dict[str, dict] = {}  # {ticker: {"shares": n, "entry_day": i}}
    trades: list[dict] = []
    eq_curve: list[dict] = []

    # Designate the highest volume / first ticker as leader, others as laggards
    leader = tickers[0]
    laggards = tickers[1:]

    for i, d in enumerate(all_dates):
        if i >= lookback and d in rets.index:
            # Check leader return on previous day
            prev_d = all_dates[i - 1]
            leader_ret = rets.loc[prev_d, leader] if prev_d in rets.index and leader in rets else 0.0

            # Leader historical rolling volatility
            leader_window = rets[leader].iloc[i - lookback : i]
            leader_std = leader_window.std()
            leader_z = (leader_ret - leader_window.mean()) / leader_std if leader_std > 1e-4 else 0.0

            # Exit expired positions
            for t in list(holdings.keys()):
                if i - holdings[t]["entry_day"] >= hold_days and d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    shares = holdings[t]["shares"]
                    cash += shares * price * (1 - cost)
                    trades.append({"ticker": t, "date": str(d), "action": "sell", "price": price, "shares": shares})
                    del holdings[t]

            # If leader made a strong upward shock (> lead_thresh_sigma)
            if leader_z > lead_thresh_sigma:
                # Identify laggards that have high positive correlation with leader but haven't moved yet
                cur_val = sum(holdings[t]["shares"] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                total_port = cur_val + cash
                target_notional = (total_port * 0.5) / max(1, len(laggards))

                for t in laggards:
                    if t not in holdings and d in data[t].index:
                        # Check correlation
                        pair_cov = np.cov(rets[leader].iloc[i - lookback : i].dropna(), rets[t].iloc[i - lookback : i].dropna())
                        corr = pair_cov[0, 1] / (np.sqrt(pair_cov[0, 0] * pair_cov[1, 1])) if pair_cov.shape == (2, 2) and pair_cov[0, 0] > 0 and pair_cov[1, 1] > 0 else 0.0

                        if corr > 0.3:
                            price = float(data[t].loc[d, "close"])
                            shares = int(target_notional // price)
                            if shares > 0 and cash >= shares * price * (1 + cost):
                                cash -= shares * price * (1 + cost)
                                holdings[t] = {"shares": shares, "entry_day": i}
                                trades.append({"ticker": t, "date": str(d), "action": "buy", "price": price, "shares": shares})

        val = cash + sum(holdings[t]["shares"] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})

    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "Lead-Lag Information Spillover",
    "family": "Cross-sect",
    "params": {"capital": 1_000_000, "lookback": 60, "lead_thresh_sigma": 1.25, "hold_days": 2, "cost": 0.001},
    "description": "Exploits delayed price discovery: buys correlated sector peers following institutional shocks in the market leader.",
}
