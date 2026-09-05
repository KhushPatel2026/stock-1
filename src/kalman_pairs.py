"""Kalman Filter Dynamic Pairs Stat-Arb.

Replaces static OLS cointegration with recursive state-space Kalman filtering.
Estimates the time-varying hedge ratio beta_t and spread innovation dynamically,
adapting to structural breaks and regime shifts without window lookback bias.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


class KalmanHedgeEstimator:
    """1D state-space Kalman filter tracking alpha_t and beta_t between pair (x, y)."""

    def __init__(self, delta: float = 1e-4, R: float = 1e-3):
        self.delta = delta
        self.R = R
        self.Vw = self.delta / (1 - self.delta) * np.eye(2)
        self.theta = np.zeros(2)  # [alpha, beta]
        self.P = np.zeros((2, 2))

    def update(self, x: float, y: float) -> tuple[float, float, float]:
        """Update filter with observation (x, y). Returns (error/spread, std_error, beta)."""
        H = np.array([1.0, x])
        # Predict
        self.P = self.P + self.Vw
        y_hat = float(H @ self.theta)
        error = y - y_hat
        Q_m = float(H @ self.P @ H.T + self.R)
        std_err = np.sqrt(max(1e-6, Q_m))

        # Update Kalman gain
        K = (self.P @ H.T) / Q_m
        self.theta = self.theta + K * error
        self.P = self.P - np.outer(K, H) @ self.P

        return error, std_err, float(self.theta[1])


def backtest(
    data: dict[str, pd.DataFrame],
    entry_z: float = 1.75,
    exit_z: float = 0.5,
    cost: float = 0.001,
    capital: float = 1_000_000,
) -> tuple[list[dict], pd.DataFrame]:
    tickers = list(data.keys())
    if len(tickers) < 2:
        return [], pd.DataFrame(columns=["equity"])

    # Pick the two most liquid or primary tickers
    t_y, t_x = tickers[0], tickers[1]
    df_y = data[t_y]
    df_x = data[t_x]

    common_dates = sorted(set(df_y.index).intersection(set(df_x.index)))
    if len(common_dates) < 20:
        return [], pd.DataFrame(columns=["equity"])

    kf = KalmanHedgeEstimator(delta=1e-4, R=1e-3)
    cash = capital
    holdings_y = 0
    holdings_x = 0
    trades: list[dict] = []
    eq_curve: list[dict] = []

    for d in common_dates:
        p_y = float(df_y.loc[d, "close"])
        p_x = float(df_x.loc[d, "close"])

        error, std_err, beta = kf.update(p_x, p_y)
        z = error / std_err

        # Trading rules:
        # z < -entry_z: spread is undervalued (y is too cheap relative to beta * x) -> Buy y
        # z > entry_z: spread is overvalued (y is too expensive) -> Sell/short y, hold cash
        # |z| < exit_z: mean-reversion achieved -> close positions

        if z < -entry_z and holdings_y == 0:
            # Long y position
            total_val = cash + holdings_y * p_y + holdings_x * p_x
            target_notional = total_val * 0.8  # 80% allocation
            shares_y = int(target_notional // p_y)
            if shares_y > 0 and cash >= shares_y * p_y * (1 + cost):
                cash -= shares_y * p_y * (1 + cost)
                holdings_y = shares_y
                trades.append({"ticker": t_y, "date": str(d), "action": "buy", "price": p_y, "shares": shares_y, "z": round(z, 2)})

        elif (z > exit_z or abs(z) < exit_z) and holdings_y > 0:
            # Close long position
            cash += holdings_y * p_y * (1 - cost)
            trades.append({"ticker": t_y, "date": str(d), "action": "sell", "price": p_y, "shares": holdings_y, "z": round(z, 2)})
            holdings_y = 0

        val = cash + holdings_y * p_y + holdings_x * p_x
        eq_curve.append({"date": d, "equity": float(val)})

    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "Kalman Filter Dynamic Pairs",
    "family": "Stat-arb",
    "params": {"capital": 1_000_000, "entry_z": 1.75, "exit_z": 0.5, "cost": 0.001},
    "description": "State-space recursive Bayesian pairs trading tracking dynamic hedge ratios without window lag.",
}
