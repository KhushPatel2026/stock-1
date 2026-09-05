import pandas as pd, numpy as np
from src.factors import rank, backtest as factor_backtest
from src.options import bs_call, covered_call_backtest
from src.events import earnings_backtest, rebalance_backtest
from src.risk_overlay import max_drawdown_kill, vol_target_scale, correlation_flag, apply_kill_switch, apply_vol_target
from src.walk_forward import run as wf_run

def _make_data(n=400, tickers=5, seed=0):
    rng=np.random.default_rng(seed)
    idx=pd.date_range("2020-01-01", periods=n, freq="B")
    data={}
    for i in range(tickers):
        close=100 + np.cumsum(rng.normal(0.1,1,n))
        data[f"T{i}.NS"]=pd.DataFrame({"close":close,"high":close+0.5,"low":close-0.5,"open":close,"volume":[1e6]*n}, index=idx)
    return data

def test_factors_rank():
    data=_make_data(300, 5, 0)
    date=list(data["T0.NS"].index)[260]
    df=rank(data, date)
    assert not df.empty
    assert "composite" in df.columns
    assert len(df)<=5

def test_factors_backtest():
    data=_make_data(400, 5, 1)
    trades, eq=factor_backtest(data, capital=1_000_000, top_n=2)
    assert not eq.empty
    assert len(eq)==400

def test_bs_call():
    # ATM call ~ 0.5*vol approx; deep ITM ~ S-K discounted
    prem=bs_call(100,100,30/365,0.06,0.2)
    assert 1 < prem < 10
    assert bs_call(100,150,0.08,0.06,0.2) < 1
    assert bs_call(100,50,0.08,0.06,0.2) > 40

def test_covered_call():
    data=_make_data(400, 3, 2)
    trades, eq=covered_call_backtest(data, capital=1_000_000)
    assert not eq.empty
    assert any(t["action"]=="sell_call" for t in trades)

def test_events():
    data=_make_data(400, 4, 3)
    t1, eq1=earnings_backtest(data)
    assert not eq1.empty
    t2, eq2=rebalance_backtest(data)
    assert not eq2.empty

def test_risk_overlay():
    eq=pd.Series([100,105,90,80,85], index=pd.date_range("2020-01-01", periods=5))
    breaches=max_drawdown_kill(eq, 0.10)
    assert len(breaches)>=1
    killed=apply_kill_switch(eq, 0.10)
    assert killed.iloc[-1]==killed.iloc[2]  # flat after breach
    # vol targeting
    idx=pd.date_range("2020-01-01", periods=100, freq="B")
    rets=np.random.default_rng(0).normal(0,0.01,100)
    eq2=pd.Series(100*np.cumprod(1+rets), index=idx)
    w=vol_target_scale(eq2)
    assert not w.empty
    scaled=apply_vol_target(eq2)
    assert len(scaled)==100
    # correlation — make returns correlated
    r=np.random.default_rng(0).normal(0,0.01,100)
    a=pd.Series(100*np.cumprod(1+r), index=idx)
    b=pd.Series(100*np.cumprod(1+r+np.random.default_rng(1).normal(0,0.001,100)), index=idx)
    c=pd.Series(100*np.cumprod(1+np.random.default_rng(2).normal(0,0.01,100)), index=idx)
    res=correlation_flag({"A":a,"B":b,"C":c})
    assert len(res["flags"])>=1  # A-B highly correlated

def test_walk_forward():
    data=_make_data(600, 3, 4)
    def strat(d, p):
        # dummy: return equity as monotonic with param scale
        n=len(next(iter(d.values()))) if d else 0
        scale=p.get("scale",1)
        # more scale -> higher vol but also slightly higher mean
        rng=np.random.default_rng(int(scale*10))
        rets=rng.normal(0.0005*scale, 0.01, n)
        idx=next(iter(d.values())).index if d else pd.date_range("2020-01-01", periods=n)
        return pd.Series(100*np.cumprod(1+rets), index=idx)
    folds=wf_run(data, [{"scale":1},{"scale":2}], train=200, test=100, strategy_fn=strat)
    assert len(folds)>=2
    assert "best_params" in folds[0]
    assert "oos_sharpe" in folds[0]
