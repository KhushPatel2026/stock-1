"""Volatility-managed overlay (Moreira-Muir) — scale market exposure by 1/lagged variance.

Trades the equal-weight universe proxy: exposure_t = target_vol / realized_vol(21d),
capped at [0, 1] (no leverage in a cash backtest). Same signal, less crash.
"""
import pandas as pd
import numpy as np

META = {
    "name": "vol_managed",
    "family": "Allocation",
    "params": {"capital": 1_000_000, "target_vol": 0.15, "vol_window": 21, "cost": 0.0002},
    "description": "Scale equal-weight exposure to 15% vol target; deleverages into stress.",
}


def backtest(data: dict, target_vol=0.15, vol_window=21, cost=0.0002, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    tickers = [t for t in data if not data[t].empty]
    if not tickers:
        return [], pd.DataFrame(columns=["equity"])
    all_dates = sorted(set().union(*(set(data[t].index) for t in tickers)))
    proxy = pd.concat([data[t]["close"].rename(t) for t in tickers], axis=1).mean(axis=1).reindex(all_dates)
    rets = proxy.pct_change()
    rv = rets.rolling(vol_window).std() * np.sqrt(252)
    exposure = (target_vol / rv).clip(0, 1).fillna(0)
    cash, invested, trades, eq_curve = capital, 0.0, [], []
    prev_exp = 0.0
    for d in all_dates[1:]:
        px = float(proxy.loc[d])
        r = float(rets.loc[d]) if not pd.isna(rets.loc[d]) else 0.0
        port = cash + invested
        tgt_exp = float(exposure.loc[d]) if not pd.isna(exposure.loc[d]) else 0.0
        tgt_invested = port * tgt_exp
        if abs(tgt_invested - invested) > 1e-6 and port > 0:
            delta = tgt_invested - invested
            cash -= delta * (1 + cost * np.sign(delta))
            invested = tgt_invested
            if prev_exp == 0 and tgt_exp > 0:
                trades.append({"ticker": "UNIVERSE", "date": d, "action": "buy", "shares": 1, "price": px})
            elif prev_exp > 0 and tgt_exp == 0:
                trades.append({"ticker": "UNIVERSE", "date": d, "action": "sell", "shares": 1, "price": px})
            prev_exp = tgt_exp
        invested *= (1 + r)
        eq_curve.append({"date": d, "equity": float(cash + invested)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq
