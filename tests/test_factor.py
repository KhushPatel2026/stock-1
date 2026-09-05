import pandas as pd
import numpy as np
from src.low_vol import backtest as lv_backtest, _rank_at as lv_rank, META as LV_META
from src.quality import backtest as q_backtest, _rank_at as q_rank, META as Q_META
from src.value import backtest as v_backtest, _rank_at as v_rank, META as V_META
from src.size_factor import backtest as sf_backtest, _rank_at as sf_rank, META as SF_META
from src.high_52w import backtest as h_backtest, _rank_at as h_rank, META as H_META


def _make_data(n=600, tickers=15, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    data = {}
    for i in range(tickers):
        close = 100 + np.cumsum(rng.normal(0.1, 0.8, n))
        open_ = close + rng.normal(0, 0.3, n)
        high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.5, n))
        low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.5, n))
        volume = rng.integers(500_000, 5_000_000, n)
        data[f"T{i}.NS"] = pd.DataFrame(
            {"close": close, "open": open_, "high": high, "low": low, "volume": volume},
            index=idx,
        )
    return data


def test_low_vol():
    data = _make_data(600, 15, 0)
    date = list(data["T0.NS"].index)[300]
    ranked = lv_rank(data, date)
    assert not ranked.empty
    assert "vol" in ranked.columns
    assert ranked["vol"].is_monotonic_increasing
    trades, eq = lv_backtest(data, top_decile=0.2)
    assert isinstance(trades, list)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 600
    assert LV_META["family"] == "Factor"


def test_quality():
    data = _make_data(600, 15, 1)
    date = list(data["T0.NS"].index)[300]
    ranked = q_rank(data, date)
    assert not ranked.empty
    assert "score" in ranked.columns
    assert ranked["score"].is_monotonic_decreasing
    trades, eq = q_backtest(data, top_decile=0.2)
    assert isinstance(trades, list)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 600
    assert Q_META["family"] == "Factor"


def test_value():
    data = _make_data(600, 15, 2)
    date = list(data["T0.NS"].index)[300]
    ranked = v_rank(data, date)
    assert not ranked.empty
    assert "score" in ranked.columns
    assert ranked["score"].is_monotonic_decreasing
    trades, eq = v_backtest(data, top_decile=0.2)
    assert isinstance(trades, list)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 600
    assert V_META["family"] == "Factor"


def test_size_factor():
    data = _make_data(600, 15, 3)
    date = list(data["T0.NS"].index)[300]
    ranked = sf_rank(data, date)
    assert not ranked.empty
    assert "adv" in ranked.columns
    assert ranked["adv"].is_monotonic_increasing
    top = ranked.head(max(1, int(len(ranked) * 0.2)))["ticker"].tolist()
    assert set(top) == set(ranked.nsmallest(len(top), "adv")["ticker"].tolist())
    trades, eq = sf_backtest(data, top_decile=0.2)
    assert isinstance(trades, list)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 600
    assert SF_META["family"] == "Factor"


def test_high_52w():
    data = _make_data(600, 15, 4)
    date = list(data["T0.NS"].index)[300]
    ranked = h_rank(data, date)
    assert not ranked.empty
    assert "score" in ranked.columns
    assert ranked["score"].is_monotonic_decreasing
    trades, eq = h_backtest(data, top_decile=0.2)
    assert isinstance(trades, list)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 600
    assert H_META["family"] == "Factor"
