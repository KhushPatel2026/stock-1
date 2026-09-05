import pandas as pd
import numpy as np

from src.intraday import backtest_orb, backtest_vwap, backtest_mom, backtest_overnight


def _make_intraday(n=78, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-02 09:15", periods=n, freq="h")
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    open_ = close + rng.normal(0, 0.2, n)
    high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.3, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.3, n))
    vol = rng.integers(10_000, 100_000, n)
    df = pd.DataFrame(
        {"close": close, "open": open_, "high": high, "low": low, "volume": vol},
        index=idx,
    )
    return {"TEST.NS": df}


def _make_daily(n=100, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(rng.normal(0.1, 1, n))
    return {"TEST.NS": pd.DataFrame(
        {"close": close, "open": close, "high": close, "low": close, "volume": 100000},
        index=idx,
    )}


def test_orb():
    data = _make_intraday()
    trades, eq = backtest_orb(data, lookback_bars=6, top_n=1, cost=0.0005)
    assert isinstance(eq, pd.DataFrame) and not eq.empty
    assert len(eq) == 78
    assert isinstance(trades, list)


def test_vwap_reversion():
    data = _make_intraday()
    trades, eq = backtest_vwap(data, std_mult=1.5, top_n=1, cost=0.0005)
    assert isinstance(eq, pd.DataFrame) and not eq.empty
    assert len(eq) == 78
    assert isinstance(trades, list)


def test_intraday_momentum():
    data = _make_intraday()
    trades, eq = backtest_mom(data, sma_bars=20, vol_mult=1.2, top_n=1, cost=0.0005)
    assert isinstance(eq, pd.DataFrame) and not eq.empty
    assert len(eq) == 78
    assert isinstance(trades, list)


def test_overnight_drift():
    data = _make_daily()
    trades, eq = backtest_overnight(data, top_n=1, cost=0.0005)
    assert isinstance(eq, pd.DataFrame) and not eq.empty
    assert len(eq) == 100
    assert isinstance(trades, list)