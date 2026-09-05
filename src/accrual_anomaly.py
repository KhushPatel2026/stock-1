"""Sloan (1996) Accrual Anomaly — High Cash Flow Earnings Quality.

Ranks stocks by cash flow relative to accounting net income and market capitalization.
Companies with low accruals (cash flow exceeds accounting earnings) exhibit superior
future earnings persistence and risk-adjusted excess returns.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.fundamentals import fetch_fundamentals


def backtest(
    data: dict[str, pd.DataFrame],
    rebalance_days: int = 42,
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

    # Cache fundamentals
    fund_cache = {}
    for t in data.keys():
        try:
            fund_cache[t] = fetch_fundamentals(t, use_cache=True)
        except Exception:
            fund_cache[t] = {}

    for i, d in enumerate(all_dates):
        if i % rebalance_days == 0 and i >= 63:
            ranked: list[tuple[str, float]] = []

            for t, df in data.items():
                if d not in df.index:
                    continue
                loc = df.index.get_loc(d)
                if loc < 63:
                    continue

                fund = fund_cache.get(t, {})
                ebitda = fund.get("ebitda") or 0.0
                mcap = fund.get("market_cap") or 1.0
                ey = fund.get("earnings_yield") or 0.0

                # Sloan cash-flow / accrual proxy:
                # High EBITDA/Mcap & high Earnings Yield = high cash backing per share
                # Combined with positive short-term price momentum to filter distressed value traps
                r_63 = float(df["close"].iloc[loc] / df["close"].iloc[loc - 63] - 1)
                cash_flow_yield = (ebitda / mcap) if mcap > 0 else 0.0

                # Quality score = Cash flow yield + 0.5 * Earnings Yield + 0.2 * Momentum
                score = cash_flow_yield + 0.5 * ey + 0.2 * max(-0.2, r_63)
                ranked.append((t, score))

            ranked.sort(key=lambda x: x[1], reverse=True)
            top_tickers = [x[0] for x in ranked[:top_n]]

            # Liquidate positions not selected
            for t in list(holdings.keys()):
                if t not in top_tickers and d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    cash += holdings[t] * price * (1 - cost)
                    trades.append({"ticker": t, "date": str(d), "action": "sell", "price": price, "shares": holdings[t]})
                    del holdings[t]

            # Reallocate
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
    "name": "Accrual & Cash-Flow Anomaly",
    "family": "Factor",
    "params": {"rebalance_days": 42, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Sloan (1996) quality anomaly: favors firms with high operational cash-flow relative to paper accounting income.",
}
