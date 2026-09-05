"""Almgren-Chriss (2000) Optimal Execution Engine.

Solves the calculus of variations trade-off between market impact costs
(temporary and permanent price displacement) and timing volatility risk.
Calculates the optimal liquidation/acquisition trajectory:
    x_j = [sinh(kappa * (T - t_j)) / sinh(kappa * T)] * Total_Shares
where urgency kappa = sqrt(lambda * sigma^2 / eta).
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def compute_optimal_schedule(
    total_shares: int,
    n_steps: int = 5,
    volatility: float = 0.02,
    risk_aversion: float = 1e-5,
    temp_impact_eta: float = 2.5e-6,
) -> list[int]:
    """Compute share amounts to trade in each step under Almgren-Chriss trajectory."""
    if n_steps <= 1 or total_shares <= 0:
        return [total_shares]

    # Urgency parameter kappa
    kappa = np.sqrt(max(1e-9, (risk_aversion * (volatility ** 2)) / temp_impact_eta))
    T = float(n_steps)
    t_points = np.linspace(0, T, n_steps + 1)

    # Remaining shares trajectory x(t)
    sinh_kappa_T = np.sinh(kappa * T)
    if sinh_kappa_T == 0 or np.isinf(sinh_kappa_T):
        # Fallback to linear TWAP
        step_size = total_shares // n_steps
        sched = [step_size] * n_steps
        sched[-1] += total_shares - sum(sched)
        return sched

    remaining = [int(np.sinh(kappa * (T - t)) / sinh_kappa_T * total_shares) for t in t_points]

    # Differences give trade sizes per interval
    schedule = []
    for j in range(n_steps):
        trade_size = remaining[j] - remaining[j + 1]
        schedule.append(max(0, trade_size))

    # Adjust rounding discrepancy
    diff = total_shares - sum(schedule)
    if schedule:
        schedule[0] += diff

    return schedule


def backtest(
    data: dict[str, pd.DataFrame],
    target_holding_days: int = 5,
    urgency: float = 1e-5,
    cost: float = 0.001,
    capital: float = 1_000_000,
) -> tuple[list[dict], pd.DataFrame]:
    """Demonstrates Almgren-Chriss optimal execution on signals."""
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    if not all_dates:
        return [], pd.DataFrame(columns=["equity"])

    cash = capital
    holdings: dict[str, int] = {}
    trades: list[dict] = []
    eq_curve: list[dict] = []

    tickers = [t for t in data.keys() if len(data[t]) >= 30]

    for i, d in enumerate(all_dates):
        if i >= 30 and i % 10 == 0 and tickers:
            # Generate trend signal
            for t in tickers[:3]:
                if d in data[t].index:
                    loc = data[t].index.get_loc(d)
                    if loc >= 20:
                        c = data[t]["close"].iloc[loc]
                        sma20 = data[t]["close"].iloc[loc - 20 : loc + 1].mean()
                        if c > sma20 and t not in holdings:
                            total_port = cash + sum(holdings[k] * float(data[k].loc[d, "close"]) for k in holdings if d in data[k].index)
                            target_notional = total_port * 0.25
                            shares = int(target_notional // c)

                            # Calculate Almgren-Chriss schedule slices
                            schedule = compute_optimal_schedule(shares, n_steps=3, risk_aversion=urgency)
                            executed_shares = sum(schedule)

                            if executed_shares > 0 and cash >= executed_shares * c * (1 + cost):
                                cash -= executed_shares * c * (1 + cost)
                                holdings[t] = executed_shares
                                trades.append({
                                    "ticker": t,
                                    "date": str(d),
                                    "action": "buy",
                                    "price": c,
                                    "shares": executed_shares,
                                    "schedule": schedule,
                                })

                        elif c < sma20 and t in holdings:
                            c = float(data[t].loc[d, "close"])
                            shares = holdings[t]
                            cash += shares * c * (1 - cost)
                            trades.append({"ticker": t, "date": str(d), "action": "sell", "price": c, "shares": shares})
                            del holdings[t]

        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})

    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "Almgren-Chriss Optimal Execution",
    "family": "Allocation",
    "params": {"capital": 1_000_000, "urgency": 1e-5, "cost": 0.001},
    "description": "Calculus of variations optimal execution scheduling: minimizes market impact and volatility timing risk.",
}
