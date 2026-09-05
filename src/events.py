"""Event-driven — earnings drift & index rebalance."""
import pandas as pd
import numpy as np

def _earnings_dates(data: dict[str, pd.DataFrame]) -> dict[str, list]:
    # try yfinance earnings_dates, fallback to synthetic spike proxy
    out={}
    for t, df in data.items():
        # synthetic: price jump >3 sigma as proxy event
        rets=df["close"].pct_change()
        thresh=float(rets.std()*3) if len(rets)>20 else 0.05
        spikes=df.index[rets.abs() > thresh].tolist()
        # limit to quarterly spacing (≥50d)
        filtered=[]
        last=None
        for d in spikes:
            if last is None or (d-last).days>=50:
                filtered.append(d); last=d
        out[t]=filtered[:8]  # at most 8 events
        # try real yfinance if available (optional)
        try:
            import yfinance as yf
            tk=yf.Ticker(t)
            ed=tk.earnings_dates
            if ed is not None and not ed.empty:
                real=[pd.to_datetime(d).tz_localize(None) for d in ed.index]
                # intersect with data range
                real=[d for d in real if d in df.index]
                if len(real)>=1:
                    out[t]=real[:8]
        except Exception:
            pass
    return out

def earnings_backtest(data: dict[str, pd.DataFrame], capital: float = 1_000_000, window: int = 5, hold: int = 10) -> tuple[list[dict], pd.DataFrame]:
    dates=sorted(set().union(*(set(df.index) for df in data.values())))
    events=_earnings_dates(data)
    # build event windows: long event stock 5d before, hold 10d after
    trades=[]
    cash=capital
    holdings={}
    # map date -> events
    date_events={}
    for t, ds in events.items():
        for d in ds:
            date_events.setdefault(d, []).append(t)
    eq_curve=[]
    for d in dates:
        # enter events starting today (window before)
        if d in date_events:
            for t in date_events[d]:
                if t in holdings: continue
                if d not in data[t].index: continue
                # notional 5% per event
                notional=capital*0.05
                price=float(data[t].loc[d,"close"])
                shares=int(notional//price)
                if shares==0 or shares*price > cash: continue
                cash-=shares*price*(1+0.001)
                holdings[t]={"shares":shares,"entry":d,"entry_price":price}
                trades.append({"ticker":t,"date":d,"action":"buy_event","price":price,"shares":shares})
        # exit after hold
        for t in list(holdings.keys()):
            if (d - holdings[t]["entry"]).days >= hold:
                if d in data[t].index:
                    price=float(data[t].loc[d,"close"])
                    cash+=holdings[t]["shares"]*price*(1-0.001)
                    pnl=(price-holdings[t]["entry_price"])*holdings[t]["shares"]
                    trades.append({"ticker":t,"date":d,"action":"sell_event","price":price,"shares":holdings[t]["shares"],"pnl":pnl})
                del holdings[t]
        val=cash + sum(holdings[t]["shares"]*float(data[t].loc[d,"close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date":d,"equity":float(val)})
    eq=pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq

def rebalance_backtest(data: dict[str, pd.DataFrame], capital: float = 1_000_000, hold: int = 10) -> tuple[list[dict], pd.DataFrame]:
    dates=sorted(set().union(*(set(df.index) for df in data.values())))
    # quarterly rebalance dates
    quarters=pd.Series(dates).dt.to_period("Q").unique() if dates else []
    q_dates=[]
    for p in quarters:
        ds=[d for d in dates if pd.Period(d,freq="Q")==p]
        if ds: q_dates.append(ds[0])
    trades=[]
    cash=capital
    holdings={}
    eq_curve=[]
    for d in dates:
        if d in q_dates:
            # buy bottom 20% momentum last 30d
            mom={}
            for t, df in data.items():
                if d not in df.index: continue
                idx=df.index.get_loc(d)
                if idx<30: continue
                mom[t]=float(df["close"].iloc[idx]/df["close"].iloc[idx-30]-1)
            if mom:
                sorted_t=sorted(mom, key=mom.get)
                bottom=sorted_t[:max(1,len(sorted_t)//5)]
                notional=capital*0.05
                for t in bottom:
                    if t in holdings: continue
                    price=float(data[t].loc[d,"close"])
                    shares=int(notional//price)
                    if shares==0 or shares*price>cash: continue
                    cash-=shares*price*(1+0.001)
                    holdings[t]={"shares":shares,"entry":d,"entry_price":price}
                    trades.append({"ticker":t,"date":d,"action":"buy_rebalance","price":price,"shares":shares})
        # exit after hold
        for t in list(holdings.keys()):
            if (d - holdings[t]["entry"]).days >= hold:
                if d in data[t].index:
                    price=float(data[t].loc[d,"close"])
                    cash+=holdings[t]["shares"]*price*(1-0.001)
                    trades.append({"ticker":t,"date":d,"action":"sell_rebalance","price":price,"shares":holdings[t]["shares"]})
                del holdings[t]
        val=cash + sum(holdings[t]["shares"]*float(data[t].loc[d,"close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date":d,"equity":float(val)})
    eq=pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq
