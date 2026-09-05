"""Time-Series Momentum (TSMOM) — Moskowitz, Ooi, Pedersen (2012).

Absolute multi-horizon trend strategy scaled by inverse realized volatility.
Positions in assets with positive time-series momentum are sized to a constant
annualized risk target (e.g. 15% target vol), cutting position size in high-vol
regimes and expanding size in calm, steady bull runs.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def backtest(
    data: dict[str, pd.DataFrame],
    target_vol: float = 0.15,
    vol_lookback: int = 60,
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

    for i, d in enumerate(all_dates):
        # Bi-weekly rebalance to control turnover while maintaining vol target
        if i % 10 == 0 and i >= 252:
            target_weights: dict[str, float] = {}
            raw_weights: dict[str, float] = {}

            for t, df in data.items():
                if d not in df.index:
                    continue
                loc = df.index.get_loc(d)
                if loc < 252:
                    continue

                close = df["close"].iloc[loc - 252 : loc + 1]
                # Multi-horizon trend signals (1M, 3M, 12M)
                r_1m = float(close.iloc[-1] / close.iloc[-21] - 1)
                r_3m = float(close.iloc[-1] / close.iloc[-63] - 1)
                r_12m = float(close.iloc[-1] / close.iloc[0] - 1)

                # Composite TSMOM signal: positive across multiple horizons
                tsmom_signal = (r_1m > 0) * 0.2 + (r_3m > 0) * 0.3 + (r_12m > 0) * 0.5

                if tsmom_signal >= 0.5:
                    rets_60 = close.iloc[-vol_lookback:].pct_change().dropna()
                    realized_vol = float(rets_60.std() * np.sqrt(252))
                    realized_vol = max(0.08, min(1.0, realized_vol))
                    # Weight inversely proportional to realized volatility (volatility targeting)
                    raw_weights[t] = (target_vol / realized_vol)

            if raw_weights:
                total_w = sum(raw_weights.values())
                # Cap maximum gross leverage at 1.0 (long-only cash conservation)
                scaling = min(1.0, 1.0 / total_w)
                target_weights = {t: (w / total_w) * scaling for t, w in raw_weights.items()}

            # Liquidate positions not in target
            for t in list(holdings.keys()):
                if t not in target_weights and d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    cash += holdings[t] * price * (1 - cost)
                    trades.append({"ticker": t, "date": str(d), "action": "sell", "price": price, "shares": holdings[t]})
                    del holdings[t]

            # Rebalance
            if target_weights:
                cur_val = sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                total_port = cur_val + cash

                for t, w in target_weights.items():
                    if d not in data[t].index:
                        continue
                    price = float(data[t].loc[d, "close"])
                    target_shares = int((total_port * w) // price)
                    cur_shares = holdings.get(t, 0)

                    if target_shares > cur_shares:
                        diff = target_shares - cur_shares
                        trade_cost = diff * price * (1 + cost)
                        if cash >= trade_cost:
                            cash -= trade_cost
                            holdings[t] = cur_shares + diff
                            trades.append({"ticker": t, "date": str(d), "action": "buy", "price": price, "shares": diff})
                    elif target_shares < cur_shares:
                        diff = cur_shares - target_shares
                        cash += diff * price * (1 - cost)
                        holdings[t] = target_shares
                        trades.append({"ticker": t, "date": str(d), "action": "sell", "price": price, "shares": diff})

        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})

    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "Time-Series Momentum (TSMOM)",
    "family": "Momentum",
    "params": {"target_vol": 0.15, "vol_lookback": 60, "cost": 0.001, "capital": 1_000_000},
    "description": "Moskowitz, Ooi, Pedersen (2012): Absolute multi-horizon trend scaled by inverse realized volatility.",
}
