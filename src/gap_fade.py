"""Gap-fade mean-reversion — fade opening gap >2σ."""
import pandas as pd
import numpy as np

def backtest(data: dict[str, pd.DataFrame], thresh: float = 2.0, gap_window: int = 20) -> tuple[list[dict], pd.DataFrame]:
    # use equal-weight Nifty proxy as single series to fade: average gap across universe
    tickers=list(data.keys())
    if not tickers:
        raise ValueError("no data")
    # pick first ticker as proxy or average — simpler: run per ticker and aggregate
    all_dates=sorted(set().union(*(set(df.index) for df in data.values())))
    # build per-ticker gap_z
    trades=[]
    cash=1_000_000
    holdings={}  # ticker -> (shares, entry_price, expiry)
    equity_curve=[]
    # precompute gap_z per ticker
    gap_z_map={}
    for t, df in data.items():
        gap=df["open"] - df["close"].shift(1)
        std=gap.rolling(gap_window).std()
        z=gap/std
        gap_z_map[t]=z
    for d in all_dates:
        # exit holdings held 1 day
        for t in list(holdings.keys()):
            if holdings[t]["expiry"]==d:
                if d in data[t].index:
                    price=float(data[t].loc[d,"close"])
                    pnl=(price - holdings[t]["entry_price"])*holdings[t]["shares"] if holdings[t]["dir"]==1 else (holdings[t]["entry_price"]-price)*holdings[t]["shares"]
                    cash+= price*holdings[t]["shares"] if holdings[t]["dir"]==1 else 0 # for short, cover
                    # for long, sell; for short, buy back
                    if holdings[t]["dir"]==1:
                        cash+= holdings[t]["shares"]*price # already? simplify: holdings was long
                        # we already deducted at entry, so just add
                        pass
                    # track
                    trades.append({"ticker":t,"exit":d,"pnl":float(pnl),"dir":holdings[t]["dir"],"gap_z":holdings[t]["gap_z"]})
                del holdings[t]
        # entries
        for t in tickers:
            if t in holdings: continue
            if d not in data[t].index: continue
            z=gap_z_map[t].loc[d] if d in gap_z_map[t].index else np.nan
            if pd.isna(z) or abs(z) < thresh:
                continue
            # fade: gap up -> short, gap down -> long, hold 1 day
            direction=-1 if z>0 else 1
            price=float(data[t].loc[d,"open"]) if "open" in data[t].columns else float(data[t].loc[d,"close"])
            # size 2% per trade
            notional=1_000_000*0.02
            shares=int(notional//price)
            if shares==0: continue
            # for long, deduct cash; for short, receive cash (simplify: margin 50%)
            if direction==1:
                if shares*price > cash: continue
                cash-=shares*price*(1+0.001)
            else:
                cash+=shares*price*(1-0.001) # short proceeds
            # expiry next close
            idx=all_dates.index(d)
            expiry=all_dates[min(idx+1, len(all_dates)-1)]
            holdings[t]={"shares":shares,"entry_price":price,"dir":direction,"gap_z":float(z),"expiry":expiry}
            trades.append({"ticker":t,"entry":d,"price":price,"dir":direction,"gap_z":float(z),"shares":shares})
        # equity: cash + holdings unrealized at close
        val=cash
        for t, h in holdings.items():
            if d in data[t].index:
                cur=float(data[t].loc[d,"close"])
                if h["dir"]==1:
                    val+= h["shares"]*cur
                else:
                    # short: cash includes proceeds, unreal pnl = (entry - cur)*shares, so val = cash + unreal (cash already has proceeds)
                    # our cash already has short proceeds, so add unreal
                    val+= (h["entry_price"]-cur)*h["shares"]
        equity_curve.append({"date":d,"equity":float(val)})
    eq=pd.DataFrame(equity_curve).set_index("date") if equity_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "Gap-Fade Mean Reversion",
    "family": "MR",
    "params": {"thresh": 1.5},
    "description": "Open vs prev close gap > N sigma, fade intraday mean-reversion.",
}
