"""Data layer: ticker verification rejects crossed frames; cache round-trips."""
import pandas as pd
import numpy as np
import pytest

from src.data import _normalize, _cache_path, CACHE_DIR


def _frame(tickers=("RELIANCE.NS",), n=60, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    cols = {}
    for t in tickers:
        close = 100 + np.cumsum(rng.normal(0.1, 1.0, n))
        cols[("Open", t)] = close - 1
        cols[("High", t)] = close + 1
        cols[("Low", t)] = close - 2
        cols[("Close", t)] = close
        cols[("Volume", t)] = np.full(n, 1_000_000)
    df = pd.DataFrame(cols, index=idx)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


def test_normalize_single_ticker_ok():
    df = _normalize(_frame(("RELIANCE.NS",)), "RELIANCE.NS")
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 60


def test_normalize_rejects_wrong_single_ticker():
    with pytest.raises(ValueError, match="mismatch"):
        _normalize(_frame(("HDFCBANK.NS",)), "RELIANCE.NS")


def test_normalize_picks_requested_from_multi():
    df = _normalize(_frame(("HDFCBANK.NS", "ITC.NS"), seed=1), "ITC.NS")
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    raw = _frame(("HDFCBANK.NS", "ITC.NS"), seed=1)
    assert float(df["close"].iloc[-1]) == float(raw[("Close", "ITC.NS")].iloc[-1])


def test_normalize_rejects_unknown_in_multi():
    with pytest.raises(ValueError, match="mismatch"):
        _normalize(_frame(("HDFCBANK.NS", "ITC.NS")), "RELIANCE.NS")


def test_cache_paths_are_period_scoped():
    assert _cache_path("RELIANCE.NS", "1y", "1d") != _cache_path("RELIANCE.NS", "5y", "1d")
    assert _cache_path("RELIANCE.NS", "1y", "1d") != _cache_path("RELIANCE.NS", "1y", "1m")
    assert _cache_path("RELIANCE.NS", "1y", "1d").suffix == ".csv"


def test_screener_bogus_ticker_returns_empty_without_raising():
    from src.screener import fetch_ratios
    assert fetch_ratios("ZZZQWERTY123.NS") == {}


def test_nse_bogus_symbol_returns_empty_without_raising():
    from src.nse_options import fetch_chain, atm_iv
    assert fetch_chain("ZZZQWERTY123") == {}
    assert atm_iv("ZZZQWERTY123") is None
