import numpy as np
import pandas as pd
from src.bab import backtest as bab_backtest
from src.fama_french import backtest as ff_backtest
from src.piotroski_f import backtest as piotroski_backtest
from src.accrual_anomaly import backtest as accrual_backtest
from src.tsmom import backtest as tsmom_backtest
from src.pca_stat_arb import backtest as pca_backtest
from src.kalman_pairs import backtest as kalman_backtest
from src.johansen_basket import backtest as johansen_backtest
from src.lead_lag import backtest as lead_lag_backtest
from src.vrp import backtest as vrp_backtest
from src.macro_roro import backtest as roro_backtest
from src.almgren_chriss import backtest as ac_backtest, compute_optimal_schedule
from src.registry import list_strategies, run_backtest
from src.signals import compute_signals


def _make_data(n=350, tickers=5, seed=42):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    data = {}
    for i in range(tickers):
        close = 100.0 + np.cumsum(rng.normal(0.08, 0.7, n))
        open_ = close + rng.normal(0, 0.2, n)
        high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.4, n))
        low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.4, n))
        vol = rng.integers(100_000, 2_000_000, n)
        data[f"T{i}.NS"] = pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close, "volume": vol},
            index=idx,
        )
    return data


def test_bab():
    data = _make_data(300, 5, 1)
    trades, eq = bab_backtest(data, lookback_beta=120, top_n=2)
    assert not eq.empty
    assert len(eq) == 300
    assert isinstance(trades, list)


def test_fama_french():
    data = _make_data(300, 5, 2)
    trades, eq = ff_backtest(data, rebalance_days=21, top_n=2)
    assert not eq.empty
    assert len(eq) == 300
    assert isinstance(trades, list)


def test_piotroski_f():
    data = _make_data(200, 4, 3)
    trades, eq = piotroski_backtest(data, min_f_score=3, rebalance_days=21, top_n=2)
    assert not eq.empty
    assert len(eq) == 200
    assert isinstance(trades, list)


def test_accrual_anomaly():
    data = _make_data(200, 4, 4)
    trades, eq = accrual_backtest(data, rebalance_days=21, top_n=2)
    assert not eq.empty
    assert len(eq) == 200


def test_tsmom():
    data = _make_data(300, 5, 5)
    trades, eq = tsmom_backtest(data, target_vol=0.15, vol_lookback=30)
    assert not eq.empty
    assert len(eq) == 300


def test_pca_stat_arb():
    data = _make_data(200, 4, 6)
    trades, eq = pca_backtest(data, lookback=40, n_components=2, z_entry=1.0, z_exit=0.4)
    assert not eq.empty
    assert len(eq) == 200


def test_kalman_pairs():
    data = _make_data(150, 2, 7)
    trades, eq = kalman_backtest(data, entry_z=1.5, exit_z=0.5)
    assert not eq.empty
    assert len(eq) == 150


def test_johansen_basket():
    data = _make_data(180, 3, 8)
    trades, eq = johansen_backtest(data, lookback=60, entry_z=1.0, exit_z=0.5)
    assert not eq.empty
    assert len(eq) == 180


def test_lead_lag():
    data = _make_data(150, 3, 9)
    trades, eq = lead_lag_backtest(data, lookback=40, lead_thresh_sigma=1.0)
    assert not eq.empty
    assert len(eq) == 150


def test_vrp():
    data = _make_data(150, 4, 10)
    trades, eq = vrp_backtest(data, vrp_lookback=15)
    assert not eq.empty
    assert len(eq) == 150


def test_macro_roro():
    data = _make_data(150, 3, 11)
    trades, eq = roro_backtest(data, lookback=30)
    assert not eq.empty
    assert len(eq) == 150


def test_almgren_chriss_schedule():
    sched = compute_optimal_schedule(total_shares=1000, n_steps=5, volatility=0.02, risk_aversion=1e-5)
    assert len(sched) == 5
    assert sum(sched) == 1000

    data = _make_data(100, 3, 12)
    trades, eq = ac_backtest(data)
    assert not eq.empty


def test_registry_integration():
    strats = list_strategies()
    s_ids = [s["id"] for s in strats]
    for expected in [
        "bab",
        "fama_french",
        "piotroski_f",
        "accrual_anomaly",
        "tsmom",
        "pca_stat_arb",
        "kalman_pairs",
        "johansen_basket",
        "lead_lag",
        "vrp",
        "macro_roro",
        "almgren_chriss",
    ]:
        assert expected in s_ids, f"Missing strategy {expected} in registry"
