"""Piotroski F-Score & Mohanram G-Score Fundamental Quality Strategy.

Scores companies across:
- Profitability: Positive ROE, Positive EBITDA, Positive Cash-to-Debt
- Leverage & Liquidity: Low Total Debt/Equity, Net Cash or Low Net Debt
- Operational Efficiency: High Earnings Yield (EBIT/EV), Return per Volatility
- Valuation Safety: Reasonable P/B and P/E metrics
Ranks stocks and holds top quality portfolio (F-Score >= min_f_score).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.fundamentals import fetch_fundamentals


def compute_f_score(fund: dict, price_ret_1y: float) -> int:
    """Evaluate Piotroski/Mohanram accounting quality composite score (0 to 9)."""
    score = 0
    # 1. Net Profitability (ROE > 0)
    roe = fund.get("return_on_equity")
    if roe is not None and roe > 0.05:
        score += 1

    # 2. Operating Cash/EBITDA Generation
    ebitda = fund.get("ebitda")
    if ebitda is not None and ebitda > 0:
        score += 1

    # 3. Earnings Yield Quality (EBIT / EV > 0.04)
    ey = fund.get("earnings_yield")
    if ey is not None and ey > 0.04:
        score += 1

    # 4. Solvency: Low Debt vs Market Cap (< 50%)
    debt = fund.get("total_debt") or 0.0
    mcap = fund.get("market_cap") or 1.0
    if mcap > 0 and (debt / mcap) < 0.5:
        score += 1

    # 5. Liquidity: Cash Reserve (> 10% of debt or net cash)
    cash = fund.get("total_cash") or 0.0
    if cash > (debt * 0.2) or debt == 0:
        score += 1

    # 6. Valuation Discipline (P/B reasonable < 6 or positive)
    pb = fund.get("price_to_book")
    if pb is not None and 0 < pb < 8:
        score += 1

    # 7. Price Quality / Market Confirmation (1Y return > 0)
    if price_ret_1y > 0:
        score += 1

    # 8. Earnings multiple stability (PE < 40 and > 0)
    pe = fund.get("pe_trailing")
    if pe is not None and 0 < pe < 40:
        score += 1

    # 9. Operating Momentum (Return > 10% in last year)
    if price_ret_1y > 0.10:
        score += 1

    return score


def backtest(
    data: dict[str, pd.DataFrame],
    min_f_score: int = 5,
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

    # Pre-fetch cached fundamentals
    fund_cache = {}
    for t in data.keys():
        try:
            fund_cache[t] = fetch_fundamentals(t, use_cache=True)
        except Exception:
            fund_cache[t] = {}

    for i, d in enumerate(all_dates):
        if i % rebalance_days == 0 and i >= 126:
            ranked: list[tuple[str, int, float]] = []
            for t, df in data.items():
                if d not in df.index:
                    continue
                loc = df.index.get_loc(d)
                if loc < 126:
                    continue

                r_1y = float(df["close"].iloc[loc] / df["close"].iloc[loc - min(loc, 252)] - 1)
                fund = fund_cache.get(t, {})
                f_score = compute_f_score(fund, r_1y)

                if f_score >= min_f_score:
                    ranked.append((t, f_score, r_1y))

            # Rank by F-score descending, secondary by momentum
            ranked.sort(key=lambda x: (x[1], x[2]), reverse=True)
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
    "name": "Piotroski F-Score & Mohanram Quality",
    "family": "Factor",
    "params": {"min_f_score": 5, "rebalance_days": 42, "top_n": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "9-point accounting health score measuring profitability, capital structure safety, and operating momentum.",
}
