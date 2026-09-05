"""Multi-factor equity model — momentum/value/quality/lowvol composite, monthly rebalance."""
import pandas as pd
import numpy as np

def _factors_at(data: dict[str, pd.DataFrame], date) -> pd.DataFrame:
    rows=[]
    for t, df in data.items():
        if date not in df.index:
            continue
        idx = df.index.get_loc(date)
        if idx < 252:
            continue
        close = df["close"]
        # momentum 12M
        mom = float(close.iloc[idx] / close.iloc[idx-252] - 1) if close.iloc[idx-252]!=0 else 0
        # value proxy: price vs 200DMA (cheaper if below)
        sma200 = close.rolling(200).mean().iloc[idx]
        val = float((sma200 - close.iloc[idx]) / close.iloc[idx]) if not pd.isna(sma200) else 0
        # lowvol: 1/std 60d
        rets = close.pct_change().iloc[idx-60+1: idx+1]
        vol = float(rets.std()) if len(rets)==60 else np.nan
        lowvol = 1/vol if vol and vol>0 else 0
        # quality proxy: mom / maxDD 252d
        window = close.iloc[idx-252: idx+1]
        peak = window.cummax()
        dd = float(((window - peak)/peak).min())
        qual = mom / (abs(dd)+0.01)
        rows.append({"ticker": t, "momentum": mom, "value": val, "quality": qual, "lowvol": lowvol})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for c in ["momentum","value","quality","lowvol"]:
        m, s = df[c].mean(), df[c].std()
        df[c+"_z"] = (df[c]-m)/(s if s and s>0 else 1)
    df["composite"] = df[["momentum_z","value_z","quality_z","lowvol_z"]].mean(axis=1)
    return df.sort_values("composite", ascending=False)

def rank(data, date):
    return _factors_at(data, date)

def backtest(data: dict[str, pd.DataFrame], capital: float = 1_000_000, top_n: int = 5) -> tuple[list[dict], pd.DataFrame]:
    # monthly last trading day
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    # group by month
    months = pd.Series(all_dates).dt.to_period("M").unique() if all_dates else []
    month_ends = []
    for p in months:
        ds = [d for d in all_dates if pd.Period(d, freq="M")==p]
        if ds: month_ends.append(max(ds))
    trades=[]
    equity_curve=[]
    cash=capital
    holdings={}  # ticker -> shares
    holdings_cost={}
    for d in all_dates:
        # rebalance on month end
        if d in month_ends:
            ranked = _factors_at(data, d)
            top = ranked.head(top_n)["ticker"].tolist() if not ranked.empty else []
            # sell not in top
            for t in list(holdings.keys()):
                if t not in top:
                    price = float(data[t].loc[d, "close"]) if d in data[t].index else None
                    if price:
                        cash += holdings[t]*price * (1 - 0.001)  # 0.1% cost
                        trades.append({"ticker": t, "date": d, "action": "sell", "price": price, "shares": holdings[t]})
                    del holdings[t]; holdings_cost.pop(t, None)
            # buy top not held
            if top:
                notional = (cash + sum(holdings[t]*float(data[t].loc[d,"close"]) for t in holdings if d in data[t].index)) / top_n if holdings else capital / top_n
                for t in top:
                    if t in holdings: continue
                    if d not in data[t].index: continue
                    price = float(data[t].loc[d,"close"])
                    shares = int((notional // price))
                    if shares==0: continue
                    cost = shares*price*(1+0.001)
                    if cost > cash: continue
                    cash -= cost
                    holdings[t]=shares
                    holdings_cost[t]=price
                    trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": shares})
        # equity
        val = cash + sum(holdings[t]*float(data[t].loc[d,"close"]) for t in holdings if d in data[t].index)
        equity_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(equity_curve).set_index("date") if equity_curve else pd.DataFrame(columns=["equity"])
    return trades, eq
