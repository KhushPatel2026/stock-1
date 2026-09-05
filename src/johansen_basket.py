"""Johansen Multi-Asset Cointegrated Basket Stat-Arb.

Tests for stationary cointegrating vectors across N assets using the Johansen
eigenvalue test. Builds a multi-asset stationary synthetic portfolio and trades
mean-reversion of the cointegrated basket spread.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen


def backtest(
    data: dict[str, pd.DataFrame],
    lookback: int = 126,
    entry_z: float = 1.5,
    exit_z: float = 0.5,
    cost: float = 0.001,
    capital: float = 1_000_000,
) -> tuple[list[dict], pd.DataFrame]:
    tickers = list(data.keys())
    if len(tickers) < 3:
        return [], pd.DataFrame(columns=["equity"])

    # Align price series
    df_closes = pd.DataFrame({t: df["close"] for t, df in data.items() if "close" in df}).dropna()
    if len(df_closes) < lookback:
        return [], pd.DataFrame(columns=["equity"])

    all_dates = list(df_closes.index)
    cash = capital
    holdings: dict[str, int] = {}
    trades: list[dict] = []
    eq_curve: list[dict] = []

    # Rolling cointegration vector
    coint_weights = None
    rolling_spread: list[float] = []

    for i, d in enumerate(all_dates):
        # Update Johansen cointegration vector periodically (every 21 days)
        if i >= lookback and (i % 21 == 0 or coint_weights is None):
            window = df_closes.iloc[i - lookback : i]
            try:
                # order 0 = constant term inside cointegration space
                res = coint_johansen(window.values, det_order=0, k_ar_diff=1)
                # First eigenvector corresponding to largest eigenvalue
                v = res.evec[:, 0]
                # Normalize so sum of absolute weights is 1.0
                if np.sum(np.abs(v)) > 1e-6:
                    coint_weights = v / np.sum(np.abs(v))
            except Exception:
                pass

        if coint_weights is not None and i >= lookback:
            prices = df_closes.loc[d].values
            current_spread = float(np.dot(coint_weights, prices))
            rolling_spread.append(current_spread)

            if len(rolling_spread) >= 30:
                s_window = rolling_spread[-60:]
                s_mean = np.mean(s_window)
                s_std = np.std(s_window)
                z = (current_spread - s_mean) / s_std if s_std > 1e-4 else 0.0

                # Spread < -entry_z: basket is cheap -> buy positive weight components
                # Spread > exit_z or |z| < exit_z: close positions
                if z < -entry_z and not holdings:
                    cur_port = cash
                    # Filter positive weight constituents
                    pos_weights = {tickers[k]: coint_weights[k] for k in range(len(tickers)) if coint_weights[k] > 0}
                    if pos_weights:
                        sum_w = sum(pos_weights.values())
                        for t, w in pos_weights.items():
                            p = float(df_closes.loc[d, t])
                            alloc = (cur_port * 0.8) * (w / sum_w)
                            shares = int(alloc // p)
                            if shares > 0 and cash >= shares * p * (1 + cost):
                                cash -= shares * p * (1 + cost)
                                holdings[t] = shares
                                trades.append({"ticker": t, "date": str(d), "action": "buy", "price": p, "shares": shares})

                elif (z > exit_z or abs(z) < exit_z) and holdings:
                    for t in list(holdings.keys()):
                        p = float(df_closes.loc[d, t])
                        cash += holdings[t] * p * (1 - cost)
                        trades.append({"ticker": t, "date": str(d), "action": "sell", "price": p, "shares": holdings[t]})
                        del holdings[t]

        val = cash + sum(holdings[t] * float(df_closes.loc[d, t]) for t in holdings)
        eq_curve.append({"date": d, "equity": float(val)})

    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "Johansen Cointegrated Basket Stat-Arb",
    "family": "Stat-arb",
    "params": {"capital": 1_000_000, "lookback": 126, "entry_z": 1.5, "exit_z": 0.5, "cost": 0.001},
    "description": "Multi-asset Johansen eigenvalue cointegration modeling stationary baskets across sector peer groups.",
}
