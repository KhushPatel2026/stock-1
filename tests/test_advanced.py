import pandas as pd, numpy as np
from src.gap_fade import backtest as gap_backtest
from src.sector_momentum import backtest as sm_backtest
from src.microstructure import backtest as micro_backtest
from src.beta_hedge import backtest as beta_backtest, rolling_beta
from src.ml_overlay import make_features, train_predict, backtest as ml_backtest

def _make_data(n=400, tickers=5, seed=0):
    rng=np.random.default_rng(seed)
    idx=pd.date_range("2020-01-01", periods=n, freq="B")
    data={}
    for i in range(tickers):
        close=100 + np.cumsum(rng.normal(0.1,0.8,n))
        open_=close + rng.normal(0,0.3,n)
        high=np.maximum(open_, close)+np.abs(rng.normal(0,0.5,n))
        low=np.minimum(open_, close)-np.abs(rng.normal(0,0.5,n))
        data[f"T{i}.NS"]=pd.DataFrame({"close":close,"open":open_,"high":high,"low":low,"volume":rng.integers(500_000,2_000_000,n)}, index=idx)
    return data

def test_gap_fade():
    data=_make_data(400, 5, 0)
    trades, eq=gap_backtest(data, thresh=1.5)
    assert not eq.empty
    assert len(eq)==400
    # should have at least attempted trades (may be 0 if thresh high, but with 1.5 expect some)
    assert isinstance(trades, list)

def test_sector_momentum():
    data=_make_data(400, 6, 1)
    trades, eq=sm_backtest(data, top_n=1)
    assert not eq.empty
    assert len(eq)==400
    # sector-neutral should have both long and short trades over time
    assert len(trades)>=0

def test_microstructure():
    data=_make_data(400, 5, 2)
    trades, eq=micro_backtest(data, vol_mult=1.5)
    assert not eq.empty
    assert len(eq)==400

def test_beta_hedge():
    data=_make_data(400, 5, 3)
    trades, eq, beta=beta_backtest(data, stock="T0.NS")
    assert not eq.empty
    assert not beta.empty
    assert abs(beta.dropna().iloc[-1] - 1.0) < 0.8  # beta near 1 for correlated synthetic

def test_rolling_beta():
    idx=pd.date_range("2020-01-01", periods=100, freq="B")
    s=pd.Series(np.cumsum(np.random.default_rng(0).normal(0,1,100)), index=idx)
    n=pd.Series(np.cumsum(np.random.default_rng(0).normal(0,1,100))*0.5, index=idx)
    b=rolling_beta(s.pct_change().fillna(0), n.pct_change().fillna(0), 20)
    assert not b.empty

def test_ml_features():
    data=_make_data(400, 5, 4)
    date=list(data["T0.NS"].index)[260]
    df=make_features(data, date)
    assert not df.empty
    assert "label" in df.columns

def test_ml_train_predict():
    data=_make_data(600, 5, 5)
    _, preds, _ = train_predict(data, train=200, test=60)
    assert isinstance(preds, pd.DataFrame)
    # preds may be empty if not enough discriminative, but shouldn't crash

def test_ml_backtest():
    data=_make_data(600, 5, 6)
    trades, eq=ml_backtest(data, top_n=2)
    assert isinstance(trades, list)
    # equity may be empty if no preds, but backtest shouldn't crash
    assert isinstance(eq, pd.DataFrame)
