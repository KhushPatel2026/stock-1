"""Microstructure proxy — volume spike + price acceleration."""
import pandas as pd
import numpy as np

def backtest(data: dict[str, pd.DataFrame], vol_mult: float = 2.0) -> tuple[list[dict], pd.DataFrame]:
    all_dates=sorted(set().union(*(set(df.index) for df in data.values())))
    trades=[]
    cash=1_000_000
    holdings={} # ticker -> shares, expiry
    vol_ma={t: data[t]["volume"].rolling(20).mean() for t in data}
    equity_curve=[]
    for d in all_dates:
        # exit
        for t in list(holdings.keys()):
            if holdings[t]["expiry"]==d:
                if d in data[t].index:
                    price=float(data[t].loc[d,"close"])
                    cash+=holdings[t]["shares"]*price*(1-0.001)
                    trades.append({"ticker":t,"exit":d,"price":price,"pnl":float((price-holdings[t]["entry"])*holdings[t]["shares"])})
                del holdings[t]
        # entries: volume spike + acceleration (close near high, >open)
        for t in data:
            if t in holdings: continue
            if d not in data[t].index: continue
            vol=float(data[t].loc[d,"volume"])
            ma=vol_ma[t].loc[d] if d in vol_ma[t].index else np.nan
            if pd.isna(ma) or ma==0: continue
            if vol < vol_mult*ma: continue
            row=data[t].loc[d]
            # acceleration: close > open*1.005 and close within 30% of high-low range from top
            if not (float(row["close"]) > float(row["open"])*1.005): continue
            rng=float(row["high"])-float(row["low"])
            if rng==0: continue
            if (float(row["high"])-float(row["close"])) > 0.3*rng: continue
            price=float(row["close"])
            notional=1_000_000*0.02
            shares=int(notional//price)
            if shares==0 or shares*price>cash: continue
            cash-=shares*price*(1+0.001)
            idx=all_dates.index(d)
            expiry=all_dates[min(idx+1, len(all_dates)-1)]
            holdings[t]={"shares":shares,"entry":price,"expiry":expiry}
            trades.append({"ticker":t,"entry":d,"price":price,"shares":shares})
        val=cash + sum(holdings[t]["shares"]*float(data[t].loc[d,"close"]) for t in holdings if d in data[t].index)
        equity_curve.append({"date":d,"equity":float(val)})
    eq=pd.DataFrame(equity_curve).set_index("date") if equity_curve else pd.DataFrame(columns=["equity"])
    return trades, eq
