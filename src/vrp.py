"""Variance Risk Premium (VRP) — Implied Volatility vs Realized Volatility Spread.

Harvests the systematic premium where market implied volatility (India VIX / IV)
trades higher than subsequent realized volatility due to structural demand for
crash insurance. Scales equity exposure when the variance risk premium is elevated
and hedges to cash when implied volatility inverts during panic selloffs.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def backtest(
    data: dict[str, pd.DataFrame],
    vrp_lookback: int = 21,
    vol_spread_thresh: float = 0.02,
    cost: float = 0.001,
    capital: float = 1_000_000,
) -> tuple[list[dict], pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    if not all_dates:
        return [], pd.DataFrame(columns=["equity"])

    cash = capital
    holdings: dict[str, int] = {}
    trades: list[dict] = []
    eq_curve: list[dict] = []

    # Try fetching ^INDIAVIX if available, else estimate implied vs realized Parkinson/Garman-Klass vol
    vix_df = data.get("^INDIAVIX")

    for i, d in enumerate(all_dates):
        if i >= 60:
            # Estimate realized volatility of the universe
            rets_universe = []
            for t, df in data.items():
                if t == "^INDIAVIX" or d not in df.index:
                    continue
                loc = df.index.get_loc(d)
                if loc >= vrp_lookback:
                    r = float(df["close"].iloc[loc] / df["close"].iloc[loc - 1] - 1)
                    rets_universe.append(r)

            # Universe rolling realized vol
            realized_vol = float(np.std(rets_universe) * np.sqrt(252)) if len(rets_universe) > 1 else 0.15

            # Implied volatility proxy: India VIX or 21-day Garman-Klass / Parkinson high-low proxy
            if vix_df is not None and d in vix_df.index:
                implied_vol = float(vix_df.loc[d, "close"]) / 100.0
            else:
                # Parkinson high-low volatility proxy when VIX not explicitly passed
                hl_vols = []
                for t, df in data.items():
                    if t != "^INDIAVIX" and d in df.index and "high" in df and "low" in df:
                        loc = df.index.get_loc(d)
                        if loc >= vrp_lookback:
                            window_df = df.iloc[loc - vrp_lookback + 1 : loc + 1]
                            hl = np.log(window_df["high"] / window_df["low"]) ** 2
                            hl_vol = np.sqrt(hl.mean() / (4 * np.log(2)) * 252)
                            hl_vols.append(hl_vol)
                implied_vol = float(np.mean(hl_vols)) if hl_vols else realized_vol + 0.03

            vrp_spread = implied_vol - realized_vol

            # If VRP spread is positive and healthy (options premium overpriced) -> Long equities
            # If VRP spread inverts severely (panic dislocation) -> De-risk to cash
            should_invest = vrp_spread >= -0.01

            valid_stocks = [t for t in data.keys() if t != "^INDIAVIX" and d in data[t].index]

            if should_invest and valid_stocks:
                cur_val = sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                total_port = cur_val + cash
                target_notional = total_port / min(5, len(valid_stocks))

                for t in valid_stocks[:5]:
                    if t not in holdings:
                        price = float(data[t].loc[d, "close"])
                        shares = int(target_notional // price)
                        if shares > 0 and cash >= shares * price * (1 + cost):
                            cash -= shares * price * (1 + cost)
                            holdings[t] = shares
                            trades.append({"ticker": t, "date": str(d), "action": "buy", "price": price, "shares": shares})

            elif not should_invest and holdings:
                # Liquidate to cash during severe volatility inversion
                for t in list(holdings.keys()):
                    if d in data[t].index:
                        price = float(data[t].loc[d, "close"])
                        cash += holdings[t] * price * (1 - cost)
                        trades.append({"ticker": t, "date": str(d), "action": "sell", "price": price, "shares": holdings[t]})
                        del holdings[t]

        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})

    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "Variance Risk Premium (VRP)",
    "family": "Volatility",
    "params": {"capital": 1_000_000, "vrp_lookback": 21, "vol_spread_thresh": 0.02, "cost": 0.001},
    "description": "Exploits the spread between Implied Volatility and Realized Volatility, scaling equity exposure during positive premium carry.",
}
