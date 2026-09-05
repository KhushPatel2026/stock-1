"""GARCH-Lite — EWMA(λ=0.94) variance forecast; long when forecast vol > realized vol."""
import pandas as pd
import numpy as np

META = {
    "name": "GARCH-Lite (EWMA Vol Forecast)",
    "family": "Volatility",
    "params": {"capital": 1_000_000, "lam": 0.94, "realized_n": 20, "top_n": 5, "cost": 0.001},
    "description": "EWMA variance forecast vs 20d realized vol; long top-5 by 12M momentum when expansion expected.",
}

def _ewma_var(rets: pd.Series, lam: float) -> pd.Series:
    n = len(rets)
    out = pd.Series(np.nan, index=rets.index, dtype=float)
    valid = rets.dropna()
    if len(valid) == 0:
        return out
    seed = float((valid.iloc[0] ** 2))
    idx0 = valid.index[0]
    out.loc[idx0] = seed
    prev = seed
    for i in range(1, len(valid)):
        v = float(valid.iloc[i] ** 2)
        prev = lam * prev + (1 - lam) * v
        out.loc[valid.index[i]] = prev
    return out

def backtest(data: dict, lam=0.94, realized_n=20, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    months = pd.Series(all_dates).dt.to_period("M").unique() if all_dates else []
    month_ends = [max([d for d in all_dates if pd.Period(d, freq="M") == p]) for p in months]
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
    forecast = {t: _ewma_var(df["close"].pct_change(), lam) for t, df in data.items()}
    for d in all_dates:
        if d in month_ends:
            ranks = []
            for t, df in data.items():
                if d not in df.index:
                    continue
                idx = df.index.get_loc(d)
                if idx < 252:
                    continue
                ret12 = float(df["close"].iloc[idx] / df["close"].iloc[idx - 252] - 1)
                ranks.append((t, ret12))
            ranks.sort(key=lambda x: -x[1])
            top = [t for t, _ in ranks[:top_n]]
            pick = {}
            for t in top:
                if d not in data[t].index:
                    continue
                fv = forecast[t].loc[:d].iloc[-1]
                if pd.isna(fv):
                    continue
                rets = data[t]["close"].pct_change().iloc[-realized_n:].dropna()
                if len(rets) < realized_n - 2:
                    continue
                rv = float(rets.std())
                if pd.isna(rv) or rv <= 0:
                    continue
                if float(np.sqrt(fv)) > rv:
                    pick[t] = True
            for t in list(holdings.keys()):
                if t not in pick and d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    cash += holdings[t] * price * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": price, "shares": holdings[t]})
                    del holdings[t]
            if pick:
                port_val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                slot = len(pick)
                notional = port_val / slot
                for t in pick:
                    if t in holdings or d not in data[t].index:
                        continue
                    price = float(data[t].loc[d, "close"])
                    shares = int(notional // price)
                    if shares > 0:
                        cash -= shares * price * (1 + cost)
                        holdings[t] = shares
                        trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": shares})
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq