"""PCA / Eigenmode Residual Statistical Arbitrage — Avellaneda & Lee (2010).

Decomposes the return correlation matrix of the stock universe into top K
eigenmodes (systematic market and sector risk). Isolates idiosyncratic residual
returns, models them as continuous-time Ornstein-Uhlenbeck processes, and trades
reversion on the residual s-score (z-score).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA


def backtest(
    data: dict[str, pd.DataFrame],
    lookback: int = 60,
    n_components: int = 3,
    z_entry: float = 1.25,
    z_exit: float = 0.5,
    cost: float = 0.001,
    capital: float = 1_000_000,
) -> tuple[list[dict], pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    if not all_dates or len(data) < 2:
        return [], pd.DataFrame(columns=["equity"])

    # Build synchronous daily return matrix
    df_closes = pd.DataFrame({t: df["close"] for t, df in data.items() if "close" in df}).dropna(how="all")
    rets = df_closes.pct_change()

    cash = capital
    holdings: dict[str, int] = {}
    trades: list[dict] = []
    eq_curve: list[dict] = []

    # Rolling estimation
    for i, d in enumerate(all_dates):
        if i >= lookback and d in rets.index:
            window_rets = rets.loc[:d].iloc[-lookback:].dropna(axis=1, thresh=int(lookback * 0.8)).fillna(0.0)
            valid_cols = window_rets.columns.tolist()

            if len(valid_cols) >= max(3, n_components + 1):
                # Standardize returns
                standardized = (window_rets - window_rets.mean()) / window_rets.std().replace(0, 1)

                # Fit PCA
                k = min(n_components, len(valid_cols) - 1)
                pca = PCA(n_components=k)
                factors = pca.fit_transform(standardized)  # (lookback, k)

                # Regress each stock on factors to get residuals
                s_scores: dict[str, float] = {}
                for col in valid_cols:
                    y = standardized[col].values
                    # OLS regression y on factors with intercept
                    X = np.column_stack([np.ones(len(y)), factors])
                    try:
                        beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
                        residuals = y - X @ beta
                        # Cumulative residual process
                        cum_res = np.cumsum(residuals)
                        # AR(1) proxy for Ornstein-Uhlenbeck: X_t = a + b * X_{t-1} + e
                        x_lag = cum_res[:-1]
                        x_curr = cum_res[1:]
                        if len(x_lag) > 10:
                            A = np.column_stack([np.ones(len(x_lag)), x_lag])
                            b_coef, _, _, _ = np.linalg.lstsq(A, x_curr, rcond=None)
                            b_val = b_coef[1]
                            if 0 < b_val < 1.0:
                                # Mean-reversion detected
                                resid_var = np.var(x_curr - A @ b_coef)
                                eq_var = resid_var / (1.0 - b_val**2) if (1.0 - b_val**2) > 1e-4 else 1.0
                                eq_std = np.sqrt(max(eq_var, 1e-6))
                                eq_mean = b_coef[0] / (1.0 - b_val)
                                s_score = (cum_res[-1] - eq_mean) / eq_std
                                s_scores[col] = s_score
                    except Exception:
                        pass

                # Trading signals:
                # Buy oversold residuals (s_score < -z_entry)
                # Exit when reverted (|s_score| < z_exit)
                target_longs = [t for t, s in s_scores.items() if s < -z_entry]

                # Close positions that have mean-reverted or flipped
                for t in list(holdings.keys()):
                    s = s_scores.get(t, 0.0)
                    if abs(s) < z_exit or s > 0 or t not in target_longs:
                        if d in data[t].index:
                            price = float(data[t].loc[d, "close"])
                            cash += holdings[t] * price * (1 - cost)
                            trades.append({"ticker": t, "date": str(d), "action": "sell", "price": price, "shares": holdings[t]})
                            del holdings[t]

                # Enter new oversold positions
                if target_longs:
                    cur_val = sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                    total_port = cur_val + cash
                    target_notional = total_port / max(3, len(target_longs) + len(holdings))

                    for t in target_longs:
                        if t in holdings or d not in data[t].index:
                            continue
                        price = float(data[t].loc[d, "close"])
                        shares = int(target_notional // price)
                        if shares > 0 and cash >= shares * price * (1 + cost):
                            cash -= shares * price * (1 + cost)
                            holdings[t] = shares
                            trades.append({"ticker": t, "date": str(d), "action": "buy", "price": price, "shares": shares})

        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})

    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "PCA Residual Stat-Arb (Avellaneda-Lee)",
    "family": "Stat-arb",
    "params": {"capital": 1_000_000, "lookback": 60, "n_components": 3, "z_entry": 1.25, "z_exit": 0.5, "cost": 0.001},
    "description": "Avellaneda & Lee (2010): Eigenmode factor decomposition with Ornstein-Uhlenbeck residual mean-reversion.",
}
