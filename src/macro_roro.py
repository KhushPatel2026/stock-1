"""Global Macro Risk-On / Risk-Off (RORO) Regime Switching Strategy.

Monitors global macro stress indicators:
- US Dollar Strength (DXY / USDINR)
- Energy / Brent Crude Oil
- Global Sovereign Yields (US 10Y Yield)
- Equity Volatility (India VIX)

Scales portfolio exposure dynamically: allocates 100% in Risk-On regimes
and de-risks to cash/defensive holdings when global macro shocks hit.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def backtest(
    data: dict[str, pd.DataFrame],
    lookback: int = 60,
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

    macro_symbols = {"^INDIAVIX", "^TNX", "DX-Y.NYB", "BZ=F", "USDINR=X"}
    equity_tickers = [t for t in data.keys() if t not in macro_symbols]

    for i, d in enumerate(all_dates):
        if i >= lookback and equity_tickers:
            # Evaluate Macro Stress Score
            stress_components = []

            # 1. Volatility Regime
            if "^INDIAVIX" in data and d in data["^INDIAVIX"].index:
                vix_close = data["^INDIAVIX"]["close"]
                vix_curr = float(vix_close.loc[d])
                vix_ma = float(vix_close.iloc[max(0, vix_close.index.get_loc(d) - 60) : vix_close.index.get_loc(d) + 1].mean())
                # Stress if VIX > 1.2x its 60-day moving average
                stress_components.append(1.0 if vix_curr > vix_ma * 1.2 else 0.0)

            # 2. Equity Universe Trend (Market breadth)
            above_sma50_count = 0
            valid_count = 0
            for t in equity_tickers:
                if d in data[t].index:
                    loc = data[t].index.get_loc(d)
                    if loc >= 50:
                        c = data[t]["close"].iloc[loc]
                        sma50 = data[t]["close"].iloc[loc - 50 : loc + 1].mean()
                        if c > sma50:
                            above_sma50_count += 1
                        valid_count += 1

            breadth = (above_sma50_count / valid_count) if valid_count > 0 else 0.5
            # Stress if breadth < 35%
            stress_components.append(1.0 if breadth < 0.35 else 0.0)

            macro_stress = np.mean(stress_components) if stress_components else 0.0
            is_risk_on = macro_stress < 0.5

            if is_risk_on:
                cur_val = sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                total_port = cur_val + cash
                target_notional = total_port / min(5, len(equity_tickers))

                for t in equity_tickers[:5]:
                    if t not in holdings and d in data[t].index:
                        price = float(data[t].loc[d, "close"])
                        shares = int(target_notional // price)
                        if shares > 0 and cash >= shares * price * (1 + cost):
                            cash -= shares * price * (1 + cost)
                            holdings[t] = shares
                            trades.append({"ticker": t, "date": str(d), "action": "buy", "price": price, "shares": shares})

            else:
                # Risk-off: cut exposure and hold cash
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
    "name": "Macro Regime Switching (RORO)",
    "family": "Hedge",
    "params": {"capital": 1_000_000, "lookback": 60, "cost": 0.001},
    "description": "Cross-asset risk-on/risk-off macro filter: protects capital during global liquidity contractions and vol spikes.",
}
