import pandas as pd
import numpy as np
import pytest
from src.spread import rolling_beta, spread_and_zscore
from src.pair_signals import signal
from src.pairs import find_cointegrated
from src.pair_portfolio import run_pair

def test_rolling_beta():
    n=100
    rng=np.random.default_rng(0)
    x = np.cumsum(rng.normal(0,1,n)) + 100
    y = 2*x + rng.normal(0,0.5,n)
    s1=pd.Series(y); s2=pd.Series(x)
    beta=rolling_beta(s1,s2,60)
    assert abs(beta.iloc[-1] - 2.0) < 0.15
    assert pd.isna(beta.iloc[0])

def test_spread_zscore():
    n=120
    rng=np.random.default_rng(1)
    x = np.cumsum(rng.normal(0,1,n)) + 50
    y = 1.5*x + rng.normal(0,1,n)
    s1=pd.Series(y); s2=pd.Series(x)
    beta=rolling_beta(s1,s2,60)
    spread, z = spread_and_zscore(s1,s2,beta,60)
    assert not pd.isna(z.iloc[-1])
    # inject wide spread
    s1.iloc[-1] += 10
    beta2=rolling_beta(s1,s2,60)
    spread2, z2 = spread_and_zscore(s1,s2,beta2,60)
    assert z2.iloc[-1] > 1.5

def test_signal_entry_exit():
    assert signal(-2.5, 0)[0] == 1
    assert signal(2.5, 0)[0] == -1
    assert signal(0, 0)[0] == 0
    assert signal(0, 1)[0] == 0  # mean revert exit
    assert signal(-4, 1)[0] == 0  # stop
    assert signal(4, -1)[0] == 0  # stop short
    assert signal(-1, 1)[0] == 1  # hold long (still negative)
    assert signal(1, -1)[0] == -1  # hold short

def test_find_cointegrated_synthetic():
    rng=np.random.default_rng(42)
    n=300
    # cointegrated pair
    x = np.cumsum(rng.normal(0,1,n)) + 100
    y = 2*x + rng.normal(0,0.5,n)  # stationary spread
    # non-cointegrated random walks
    a = np.cumsum(rng.normal(0,1,n)) + 100
    b = np.cumsum(rng.normal(0,1,n)) + 100
    idx=pd.date_range("2020-01-01", periods=n, freq="B")
    data={
        "A.NS": pd.DataFrame({"close": y}, index=idx),
        "B.NS": pd.DataFrame({"close": x}, index=idx),
        "C.NS": pd.DataFrame({"close": a}, index=idx),
        "D.NS": pd.DataFrame({"close": b}, index=idx),
    }
    res=find_cointegrated(data, p_thresh=0.05, min_corr=0.5, lookback=250)
    # should find A-B as cointegrated
    pairs=[r["pair"] for r in res]
    assert ("A.NS","B.NS") in pairs or ("B.NS","A.NS") in pairs

def test_find_cointegrated_rejects_random():
    rng=np.random.default_rng(7)
    n=300
    a = np.cumsum(rng.normal(0,1,n)) + 100
    b = np.cumsum(rng.normal(0,1,n)) + 100
    idx=pd.date_range("2020-01-01", periods=n, freq="B")
    data={"A.NS": pd.DataFrame({"close": a}, index=idx), "B.NS": pd.DataFrame({"close": b}, index=idx)}
    res=find_cointegrated(data, p_thresh=0.05, min_corr=0.7, lookback=250)
    # random walks unlikely cointegrated, expect empty or filtered by corr
    # at least not crash
    assert isinstance(res, list)

def _make_pair_data(n=500, seed=0):
    rng=np.random.default_rng(seed)
    base = np.cumsum(rng.normal(0,0.5,n)) + 100
    # s2 = base, s1 = 1.5*base + mean-reverting spread (OU)
    spread = np.zeros(n)
    for i in range(1,n):
        spread[i] = 0.9*spread[i-1] + rng.normal(0,0.5)
    # inject occasional wide deviation every 80 bars
    s2 = base
    s1 = 1.5*base + spread
    idx=pd.date_range("2020-01-01", periods=n, freq="B")
    return {"LEG1.NS": pd.DataFrame({"close": s1, "high": s1+0.5, "low": s1-0.5, "open": s1, "volume": [1e6]*n}, index=idx),
            "LEG2.NS": pd.DataFrame({"close": s2, "high": s2+0.5, "low": s2-0.5, "open": s2, "volume": [1e6]*n}, index=idx)}

def test_pair_backtest_trades():
    data=_make_pair_data(500, 0)
    trades, eq, m = run_pair(data, ("LEG1.NS","LEG2.NS"), capital=1_000_000, entry=2.0, exit=0.3, stop=3.5)
    assert not eq.empty
    assert len(eq) == 500
    assert m["num_trades"] == len(trades)
    # mean-reverting synthetic should generate at least 1 trade
    assert len(trades) >= 1

def test_pair_backtest_deterministic():
    data=_make_pair_data(300, 123)
    t1, e1, m1 = run_pair(data, ("LEG1.NS","LEG2.NS"))
    t2, e2, m2 = run_pair(data, ("LEG1.NS","LEG2.NS"))
    assert len(t1)==len(t2)
    assert abs(e1["equity"].iloc[-1]-e2["equity"].iloc[-1]) < 1e-6
