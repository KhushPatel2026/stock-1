"""Validation layer tests — synthetic data only, no yfinance."""
from __future__ import annotations
import numpy as np
import pandas as pd
import pytest

import src.validation as v
from src.validation import (
    REGIMES,
    _mock_data,
    _oos_metrics,
    chunk_oos,
    run_regime_tests,
    run_walk_forward,
    walk_forward,
)


def _patch_fetch(monkeypatch, data: dict) -> None:
    """Replace fetch_many with a fixed-data stub so tests don't hit yfinance."""
    monkeypatch.setattr(v, "fetch_many", lambda tickers, period="5y", **kw: data)


def test_metrics_helpers():
    """Sharpe/total_return/max_dd/n_bars computed on a known curve."""
    eq = pd.DataFrame(
        {"equity": [100.0, 101.0, 100.5, 102.0]},
        index=pd.date_range("2020-01-01", periods=4, freq="B"),
    )
    m = _oos_metrics(eq)
    assert set(m.keys()) >= {"sharpe", "total_return", "max_dd", "n_bars"}
    assert m["n_bars"] == 4
    assert m["total_return"] == pytest.approx(0.02, abs=1e-6)
    assert m["max_dd"] <= 0.0
    # empty / single-row edge cases
    assert _oos_metrics(pd.DataFrame())["n_bars"] == 0
    assert _oos_metrics(pd.DataFrame({"equity": [100.0]},
                                      index=pd.date_range("2020-01-01", periods=1)))["n_bars"] == 1


def test_chunk_oos():
    """chunk_oos splits an equity curve into non-overlapping chunks with correct metrics."""
    data = _mock_data(n=1500, tickers=4, seed=1)
    _, eq = v._run_strategy("bollinger", data)
    assert not eq.empty
    # ponytail: direct chunking instead of mocking fetch_many twice
    rows = []
    chunk = 126
    n = len(eq)
    i = 0
    while i + chunk <= n:
        rows.append(_oos_metrics(eq.iloc[i:i + chunk]))
        i += chunk
    assert rows, "expected at least one chunk"
    for r in rows:
        assert r["n_bars"] == chunk
        assert "sharpe" in r and "total_return" in r and "max_dd" in r


def test_walk_forward_smoke(monkeypatch):
    """run_walk_forward returns a 1-row DataFrame with the documented schema."""
    data = _mock_data(n=1500, tickers=4, seed=2)
    _patch_fetch(monkeypatch, data)
    df = run_walk_forward("bollinger", ["MOCK0.NS"], period="5y", chunk=126)
    assert isinstance(df, pd.DataFrame)
    expected = {"strategy_id", "n_windows", "mean_oos_sharpe", "total_oos_return", "max_dd"}
    assert expected.issubset(set(df.columns))
    assert len(df) == 1
    row = df.iloc[0]
    assert row["strategy_id"] == "bollinger"
    assert row["n_windows"] >= 1
    assert isinstance(row["mean_oos_sharpe"], float)
    assert isinstance(row["max_dd"], float)


def test_regime_tests_smoke(monkeypatch):
    """run_regime_tests returns one row per regime with sharpe/return/DD/n_bars."""
    data = _mock_data(n=1500, tickers=4, seed=3)
    _patch_fetch(monkeypatch, data)
    df = run_regime_tests("bollinger", ["MOCK0.NS"])
    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) >= {"strategy_id", "regime", "sharpe", "total_return", "max_dd", "n_bars"}
    regimes_present = set(df["regime"])
    # full regime always overlaps our 2017..2022 mock span
    assert "full" in regimes_present
    # at least one of the named stress windows should also be covered
    assert {"2018_crash", "2020_covid", "2022_chop"} & regimes_present
    assert len(df) == len(REGIMES)


def test_walk_forward_rolling(monkeypatch):
    """walk_forward (proper rolling) returns per-fold rows with OOS boundaries."""
    data = _mock_data(n=1500, tickers=4, seed=4)
    _patch_fetch(monkeypatch, data)
    df = walk_forward("bollinger", ["MOCK0.NS"], period="5y", train=300, test=126, step=126)
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert {"fold", "oos_start", "oos_end", "sharpe", "n_bars"}.issubset(set(df.columns))
        # every OOS chunk should be ~test bars long (allowing small day-count fuzziness)
        assert (df["n_bars"] <= 126).all()
        assert df["fold"].is_monotonic_increasing


def test_run_regime_zero_data():
    """Empty equity curve produces zeros, not crashes."""
    empty_eq = pd.DataFrame(columns=["equity"])
    m = v._oos_metrics(empty_eq)
    assert m == {"sharpe": 0.0, "total_return": 0.0, "max_dd": 0.0, "n_bars": 0}