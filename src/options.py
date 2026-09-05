"""Volatility / Options — Black-Scholes covered call."""
import math
import pandas as pd
import numpy as np
try:
    from scipy.stats import norm
except Exception:
    # fallback: erf approximation
    import math as _m
    class _Norm:
        @staticmethod
        def cdf(x): return 0.5*(1+_m.erf(x/_m.sqrt(2)))
    norm=_Norm()

def bs_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if S<=0 or K<=0 or T<=0 or sigma<=0:
        return max(S-K,0)
    sigma=max(sigma,0.01)
    d1=(math.log(S/K)+(r+0.5*sigma*sigma)*T)/(sigma*math.sqrt(T))
    d2=d1 - sigma*math.sqrt(T)
    return S*norm.cdf(d1) - K*math.exp(-r*T)*norm.cdf(d2)

def covered_call_backtest(data: dict[str, pd.DataFrame], capital: float = 1_000_000, otm: float = 0.05, dte: int = 30, r: float = 0.06, iv_override: float | None = None) -> tuple[list[dict], pd.DataFrame]:
    # pick first ticker for simplicity — institutional would run per stock, we run portfolio equal weight
    tickers=list(data.keys())
    if not tickers:
        raise ValueError("no data")
    all_dates=sorted(set().union(*(set(df.index) for df in data.values())))
    # monthly expiry approx: every dte days
    expiries=set(all_dates[dte::dte])
    trades=[]
    cash=capital
    holdings={t:0 for t in tickers}
    # init: buy equal weight
    first=all_dates[0]
    per = capital / len(tickers)
    for t in tickers:
        if first in data[t].index:
            p=float(data[t].loc[first,"close"])
            shares=int(per//p)
            if shares>0:
                holdings[t]=shares
                cash-=shares*p
                trades.append({"ticker": t, "date": first, "action":"buy","price":p,"shares":shares})
    equity_curve=[]
    pending_calls=[]  # list of (ticker, expiry, strike, premium, shares)
    for i, d in enumerate(all_dates):
        # expire calls
        for c in pending_calls[:]:
            if c["expiry"]==d:
                p=float(data[c["ticker"]].loc[d,"close"]) if d in data[c["ticker"]].index else c["strike"]
                if p > c["strike"]:
                    # called away — sell stock at strike
                    cash += c["shares"]*c["strike"]
                    holdings[c["ticker"]] -= c["shares"]
                    trades.append({"ticker": c["ticker"], "date": d, "action":"call_exercised","price":c["strike"],"shares":c["shares"]})
                pending_calls.remove(c)
        # sell new calls monthly
        if d in expiries:
            for t in tickers:
                if holdings[t]==0 or d not in data[t].index: continue
                S=float(data[t].loc[d,"close"])
                # realized vol 60d
                rets=data[t]["close"].pct_change().tail(60).dropna()
                sigma=float(rets.std()*math.sqrt(252)) if len(rets)>=20 else 0.2
                # NSE ATM IV (when available) beats realized vol for pricing new calls
                if iv_override:
                    sigma=max(sigma, float(iv_override))
                sigma=max(sigma,0.15)
                K=S*(1+otm)
                T=dte/365
                prem=bs_call(S,K,T,r,sigma)
                # sell call per share held
                cash += prem*holdings[t]*(1 - 0.001)  # minus cost
                # find expiry
                exp_idx=all_dates.index(d) + dte
                expiry=all_dates[min(exp_idx, len(all_dates)-1)]
                pending_calls.append({"ticker": t, "expiry": expiry, "strike": K, "premium": prem, "shares": holdings[t]})
                trades.append({"ticker": t, "date": d, "action":"sell_call","strike":K,"premium":prem,"shares":holdings[t]})
        val=cash + sum(holdings[t]*float(data[t].loc[d,"close"]) for t in tickers if d in data[t].index and holdings[t]>0)
        equity_curve.append({"date": d, "equity": float(val)})
    eq=pd.DataFrame(equity_curve).set_index("date") if equity_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


def backtest(data: dict, capital: float = 1_000_000, otm: float = 0.05, dte: int = 30, r: float = 0.06) -> tuple[list, pd.DataFrame]:
    """Strategy-library contract alias."""
    return covered_call_backtest(data, capital=capital, otm=otm, dte=dte, r=r)


META = {
    "name": "Covered Call (BS)",
    "family": "Options",
    "params": {"capital": 1_000_000, "otm": 0.05, "dte": 30, "r": 0.06},
    "description": "Black-Scholes 5% OTM 30-day covered call, premium harvest.",
}
