"""Fama-French 5-Factor + Momentum (Carhart) Multi-Factor Model.

Ranks cross-section by:
- Size (SMB): Smaller dollar volume / market cap
- Value (HML): Price discount to 52-week moving average (book-to-price proxy)
- Profitability (RMW): Operating return-to-volatility efficiency
- Investment (CMA): Low 1-year asset growth / low volatility expansion
- Momentum (UMD): 12M minus 1M return (Carhart momentum)
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def backtest(
    data: dict[str, pd.DataFrame],
    rebalance_days: int = 21,
    top_n: int = 5,
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
        if i % rebalance_days == 0 and i >= 252:
            scores: dict[str, float] = {}

            # Gather raw factors for each ticker
            raw_factors: list[dict] = []
            valid_tickers: list[str] = []

            for t, df in data.items():
                if d not in df.index:
                    continue
                loc = df.index.get_loc(d)
                if loc < 252:
                    continue

                close = df["close"].iloc[loc - 252 : loc + 1]
                vol = df["volume"].iloc[loc - 252 : loc + 1] if "volume" in df else None

                # 1. Carhart Momentum (12M minus 1M)
                r_12m = float(close.iloc[-1] / close.iloc[0] - 1)
                r_1m = float(close.iloc[-1] / close.iloc[-21] - 1) if loc >= 21 else 0.0
                mom = r_12m - r_1m

                # 2. Value Proxy (discount to SMA200)
                sma200 = float(close.iloc[-200:].mean())
                value = (sma200 - float(close.iloc[-1])) / sma200 if sma200 > 0 else 0.0

                # 3. Quality / Profitability (RMW: return per annualized unit of vol)
                rets = close.pct_change().dropna()
                volatility = float(rets.std() * np.sqrt(252)) if len(rets) > 20 else 1.0
                profitability = r_12m / max(volatility, 0.05)

                # 4. Investment / Low Expansion (CMA: low asset volatility / conservative)
                conservative = -volatility

                # 5. Size (SMB: ADV inverse proxy)
                size_score = -float(vol.iloc[-20:].mean()) if vol is not None and len(vol) >= 20 else 0.0

                raw_factors.append({
                    "mom": mom,
                    "val": value,
                    "prof": profitability,
                    "cons": conservative,
                    "size": size_score,
                })
                valid_tickers.append(t)

            if len(raw_factors) >= top_n:
                fact_df = pd.DataFrame(raw_factors, index=valid_tickers)
                # Compute cross-sectional z-scores
                z_df = (fact_df - fact_df.mean()) / fact_df.std().replace(0, 1)
                # Composite score: equal weighting of the 5 canonical factors
                composite = z_df.mean(axis=1)
                top_tickers = composite.nlargest(top_n).index.tolist()
            else:
                top_tickers = []

            # Liquidate non-selected holdings
            for t in list(holdings.keys()):
                if t not in top_tickers and d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    cash += holdings[t] * price * (1 - cost)
                    trades.append({"ticker": t, "date": str(d), "action": "sell", "price": price, "shares": holdings[t]})
                    del holdings[t]

            # Rebalance into top quintile
            if top_tickers:
                cur_val = sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                total_port = cur_val + cash
                target_notional = total_port / len(top_tickers)

                for t in top_tickers:
                    if d not in data[t].index:
                        continue
                    price = float(data[t].loc[d, "close"])
                    target_shares = int(target_notional // price)
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
    "name": "Fama-French 5-Factor + Momentum",
    "family": "Factor",
    "params": {"rebalance_days": 21, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Cross-sectional ranking by Size, Value, Profitability, Conservative Investment, and Carhart Momentum.",
}
