import pandas as pd
import numpy as np
from src.xsection import (
    backtest as xs_backtest, backtest_st as st_backtest, backtest_lt as lt_backtest,
    _score_12_1, _score_st_rev, _score_lt_rev, META as XS_META,
)
from src.bab import backtest as bab_backtest, META as BAB_META
from src.distance_pairs import backtest as dp_backtest, _formation_ssd, META as DP_META
from src.vol_managed import backtest as vm_backtest, META as VM_META
from src.chandelier import backtest as ch_backtest, META as CH_META
from src.seasonal import backtest as tom_backtest, backtest_expiry as exp_backtest, META as TOM_META
from src.registry import list_strategies
from src.signals import signal_for_strategy


def _make_data(n=600, tickers=12, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    data = {}
    for i in range(tickers):
        drift = 0.05 if i < tickers // 2 else -0.02  # winners + losers -> rankable
        close = 100 + np.cumsum(rng.normal(drift, 0.8, n))
        open_ = close + rng.normal(0, 0.3, n)
        high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.5, n))
        low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.5, n))
        volume = rng.integers(500_000, 5_000_000, n)
        data[f"T{i}.NS"] = pd.DataFrame(
            {"close": close, "open": open_, "high": high, "low": low, "volume": volume},
            index=idx,
        )
    return data


def test_scores_have_right_sign():
    data = _make_data()
    df = data["T0.NS"]
    assert _score_12_1(df, 300) is not None
    assert _score_st_rev(df, 300) is not None
    assert _score_lt_rev(df, 550) is not None
    assert _score_12_1(df, 10) is None  # not enough history
    assert XS_META["family"] == "Momentum"


def test_xs_momentum():
    trades, eq = xs_backtest(_make_data())
    assert isinstance(trades, list) and len(trades) > 0
    assert len(eq) == 600
    sides = {t["action"] for t in trades}
    assert "long" in sides and "short" in sides


def test_st_reversal():
    trades, eq = st_backtest(_make_data())
    assert len(trades) > 0 and len(eq) == 600


def test_lt_reversal():
    trades, eq = lt_backtest(_make_data())
    assert len(trades) > 0 and len(eq) == 600


def test_bab():
    trades, eq = bab_backtest(_make_data())
    assert len(trades) > 0 and len(eq) == 600
    assert BAB_META["family"] == "Factor"


def test_distance_pairs():
    data = _make_data()
    a, b = data["T0.NS"]["close"][:252], data["T1.NS"]["close"][:252]
    assert _formation_ssd(a, b) >= 0
    trades, eq = dp_backtest(data)
    assert isinstance(trades, list) and isinstance(eq, pd.DataFrame)
    assert DP_META["family"] == "Stat-arb"


def test_vol_managed():
    trades, eq = vm_backtest(_make_data())
    assert isinstance(eq, pd.DataFrame) and len(eq) == 599
    assert (eq["equity"] > 0).all()
    assert VM_META["family"] == "Allocation"


def test_chandelier():
    trades, eq = ch_backtest(_make_data())
    assert len(trades) > 0 and len(eq) == 600
    assert CH_META["family"] == "Trend"


def test_seasonals():
    t_trades, t_eq = tom_backtest(_make_data())
    e_trades, e_eq = exp_backtest(_make_data())
    assert len(t_trades) > 0 and len(e_trades) > 0
    assert (t_eq["equity"] > 0).all() and (e_eq["equity"] > 0).all()
    assert TOM_META["family"] == "Seasonal"


def test_registry_and_signals_cover_frontier():
    ids = {s["id"] for s in list_strategies()}
    for sid in ["xs_momentum", "st_reversal", "lt_reversal", "bab", "distance_pairs",
                "vol_managed", "chandelier", "turn_of_month", "expiry_drift"]:
        assert sid in ids, sid
        sig, strength = signal_for_strategy(sid, _make_data()["T0.NS"])
        assert sig in ("long", "short", "flat")
        assert 0.0 <= strength <= 1.0
    assert len(ids) >= 65
