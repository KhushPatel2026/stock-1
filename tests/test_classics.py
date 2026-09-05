import pandas as pd, numpy as np
from src.bollinger import backtest as bollinger_backtest
from src.rsi2 import backtest as rsi_backtest, _rsi
from src.dual_momentum import backtest as dm_backtest
from src.magic_formula import backtest as mf_backtest, _rank_at
from src.risk_parity import backtest as rp_backtest
from src.dividend_carry import backtest as div_backtest, YIELDS

def _make_data(n=400, tickers=10, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    data = {}
    for i in range(tickers):
        close = 100 + np.cumsum(rng.normal(0.1, 0.8, n))
        open_ = close + rng.normal(0, 0.3, n)
        high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.5, n))
        low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.5, n))
        data[f"T{i}.NS"] = pd.DataFrame(
            {"close": close, "open": open_, "high": high, "low": low,
             "volume": rng.integers(500_000, 2_000_000, n)},
            index=idx,
        )
    return data

def test_bollinger():
    data = _make_data(400, 10, 0)
    trades, eq = bollinger_backtest(data, top_n=5)
    assert isinstance(eq, pd.DataFrame) and not eq.empty
    assert len(eq) == 400
    assert isinstance(trades, list)

def test_rsi():
    idx = pd.date_range("2020-01-01", periods=50, freq="B")
    s = pd.Series(np.cumsum(np.random.default_rng(0).normal(0, 1, 50)), index=idx)
    r = _rsi(s, 2)
    assert not r.empty
    assert r.dropna().between(0, 100).all()
    data = _make_data(400, 10, 1)
    trades, eq = rsi_backtest(data, max_n=3)
    assert not eq.empty
    assert len(eq) == 400

def test_dual_momentum():
    data = _make_data(600, 10, 2)
    trades, eq = dm_backtest(data, top_n=3)
    assert not eq.empty
    assert len(eq) == 600
    assert isinstance(trades, list)

def test_magic_formula():
    data = _make_data(600, 10, 3)
    date = list(data["T0.NS"].index)[300]
    ranked = _rank_at(data, date)
    assert not ranked.empty
    assert "score" in ranked.columns
    trades, eq = mf_backtest(data, top_decile=0.3)
    assert not eq.empty

def test_risk_parity():
    data = _make_data(400, 10, 4)
    trades, eq = rp_backtest(data, top_n=5)
    assert not eq.empty
    assert len(eq) == 400

def test_dividend_carry():
    data = _make_data(400, 10, 5)
    # data has no real dividend info; test uses static YIELDS map but tickers won't match
    # test that the function doesn't crash on empty intersection
    trades, eq = div_backtest(data, top_q=0.25)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 400
    # and that the YIELDS map is well-formed
    assert all(v >= 0 for v in YIELDS.values())
    assert "RELIANCE.NS" in YIELDS
    assert "TCS.NS" in YIELDS
