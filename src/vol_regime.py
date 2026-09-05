"""Volatility Regime Filter — long only when 20d realized vol > trailing 252-bar median."""
import pandas as pd

META = {
    "name": "Volatility Regime Filter",
    "family": "Volatility",
    "params": {"capital": 1_000_000, "vol_n": 20, "median_lookback": 252, "top_n": 5, "cost": 0.001},
    "description": "Long top-5 by 12M momentum only when realized vol(20) > median over last 252 bars.",
}

def backtest(data: dict, vol_n=20, median_lookback=252, top_n=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    months = pd.Series(all_dates).dt.to_period("M").unique() if all_dates else []
    month_ends = [max([d for d in all_dates if pd.Period(d, freq="M") == p]) for p in months]
    cash = capital
    holdings = {}
    trades = []
    eq_curve = []
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
            regime_on = {}
            for t in top:
                if d not in data[t].index:
                    continue
                idx = data[t].index.get_loc(d)
                if idx < median_lookback:
                    continue
                rets = data[t]["close"].pct_change()
                rets = rets.iloc[idx - median_lookback + 1: idx + 1].dropna()
                if len(rets) < vol_n + 1:
                    continue
                vols = rets.iloc[-vol_n:].std()
                hist = rets.rolling(vol_n).std().dropna()
                if len(hist) < 5:
                    continue
                med = float(hist.median())
                if pd.isna(vols) or pd.isna(med) or med <= 0:
                    continue
                if vols > med:
                    regime_on[t] = True
            for t in list(holdings.keys()):
                if t not in regime_on and d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    cash += holdings[t] * price * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": price, "shares": holdings[t]})
                    del holdings[t]
            if regime_on:
                port_val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                slot = len(regime_on)
                notional = port_val / slot
                for t in regime_on:
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