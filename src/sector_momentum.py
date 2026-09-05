"""Sector-neutral cross-sectional momentum — rank within sector."""
import pandas as pd
import numpy as np
from .universe import SECTORS

def backtest(data: dict[str, pd.DataFrame], top_n: int = 1) -> tuple[list[dict], pd.DataFrame]:
    all_dates=sorted(set().union(*(set(df.index) for df in data.values())))
    # month ends
    months=pd.Series(all_dates).dt.to_period("M").unique() if all_dates else []
    month_ends=[]
    for p in months:
        ds=[d for d in all_dates if pd.Period(d, freq="M")==p]
        if ds: month_ends.append(max(ds))
    trades=[]
    cash=1_000_000
    holdings={} # ticker -> shares (positive long, negative short)
    equity_curve=[]
    for d in all_dates:
        if d in month_ends:
            # close all
            for t, sh in list(holdings.items()):
                if d in data[t].index:
                    price=float(data[t].loc[d,"close"])
                    cash+= sh*price * (1 - 0.001*np.sign(sh)) # costs
                    trades.append({"ticker":t,"date":d,"action":"close","shares":sh,"price":price})
            holdings.clear()
            # build new portfolio sector-neutral
            longs=[]; shorts=[]
            for sector, members in SECTORS.items():
                m=[t for t in members if t in data and d in data[t].index]
                if len(m)<2: continue
                mom={}
                for t in m:
                    idx=data[t].index.get_loc(d)
                    if idx<252: continue
                    mom[t]=float(data[t]["close"].iloc[idx]/data[t]["close"].iloc[idx-252]-1)
                if len(mom)<2: continue
                sorted_m=sorted(mom, key=mom.get)
                longs.extend(sorted_m[-top_n:])
                shorts.extend(sorted_m[:top_n])
            # size: equal weight per leg, gross 20% long + 20% short (market-neutral)
            n_legs=len(longs)+len(shorts)
            if n_legs==0:
                pass
            else:
                gross_long=1_000_000*0.5  # 50% gross long
                gross_short=1_000_000*0.5
                per_long=gross_long/max(1,len(longs))
                per_short=gross_short/max(1,len(shorts))
                for t in longs:
                    price=float(data[t].loc[d,"close"])
                    shares=int(per_long//price)
                    if shares==0: continue
                    cash-=shares*price*(1+0.001)
                    holdings[t]=holdings.get(t,0)+shares
                    trades.append({"ticker":t,"date":d,"action":"long","shares":shares,"price":price})
                for t in shorts:
                    price=float(data[t].loc[d,"close"])
                    shares=int(per_short//price)
                    if shares==0: continue
                    cash+=shares*price*(1-0.001)
                    holdings[t]=holdings.get(t,0)-shares
                    trades.append({"ticker":t,"date":d,"action":"short","shares":-shares,"price":price})
        val=cash + sum(holdings[t]*float(data[t].loc[d,"close"]) for t in holdings if d in data[t].index)
        equity_curve.append({"date":d,"equity":float(val)})
    eq=pd.DataFrame(equity_curve).set_index("date") if equity_curve else pd.DataFrame(columns=["equity"])
    return trades, eq
