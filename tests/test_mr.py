import pandas as pd
import numpy as np
from src.stochastic import backtest as stoch_bt, META as stoch_meta
from src.williams_r import backtest as wr_bt, META as wr_meta
from src.cci import backtest as cci_bt, META as cci_meta
from src.mfi import backtest as mfi_bt, META as mfi_meta
from src.keltner_mr import backtest as kel_bt, META as kel_meta
from src.zscore_mr import backtest as z_bt, META as z_meta
from src.ou_process import backtest as ou_bt, META as ou_meta


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


def test_stochastic():
    data = _make_data(400, 10, 0)
    assert stoch_meta["family"] == "MR"
    trades, eq = stoch_bt(data, top_n=5)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 400
    assert isinstance(trades, list)


def test_williams_r():
    data = _make_data(400, 10, 1)
    assert wr_meta["family"] == "MR"
    trades, eq = wr_bt(data, top_n=5)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 400
    assert isinstance(trades, list)


def test_cci():
    data = _make_data(400, 10, 2)
    assert cci_meta["family"] == "MR"
    trades, eq = cci_bt(data, top_n=5)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 400
    assert isinstance(trades, list)


def test_mfi():
    data = _make_data(400, 10, 3)
    assert mfi_meta["family"] == "MR"
    trades, eq = mfi_bt(data, top_n=5)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 400
    assert isinstance(trades, list)


def test_keltner_mr():
    data = _make_data(400, 10, 4)
    assert kel_meta["family"] == "MR"
    trades, eq = kel_bt(data, top_n=5)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 400
    assert isinstance(trades, list)


def test_zscore_mr():
    data = _make_data(400, 10, 5)
    assert z_meta["family"] == "MR"
    trades, eq = z_bt(data, top_n=5)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 400
    assert isinstance(trades, list)


def test_ou_process():
    data = _make_data(400, 10, 6)
    assert ou_meta["family"] == "MR"
    trades, eq = ou_bt(data, top_n=5)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 400
    assert isinstance(trades, list)