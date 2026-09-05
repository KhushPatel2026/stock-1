import math

import numpy as np
import pandas as pd
import pytest

from src.fundamentals import (
    CACHE_DIR,
    fetch_fundamentals,
)
from src.magic_formula import backtest as mf_backtest
from src.options_real import covered_call_real


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


def test_fetch_fundamentals_reliance():
    fd = fetch_fundamentals("RELIANCE.NS", use_cache=False)
    expected = {
        "ticker", "market_cap", "enterprise_value", "ebitda", "ebit",
        "total_debt", "total_cash", "return_on_equity", "earnings_yield",
        "pe_trailing", "pe_forward", "price_to_book", "dividend_yield",
        "book_value", "fetched_at",
    }
    assert expected.issubset(fd.keys()), f"missing keys: {expected - set(fd.keys())}"
    assert fd["ticker"] == "RELIANCE.NS"
    assert fd["market_cap"] is not None and fd["market_cap"] > 0
    assert fd["fetched_at"]
    cache_file = CACHE_DIR / "RELIANCE_NS.json"
    assert cache_file.exists(), "cache file should be written"


def test_earnings_yield_calculation():
    fd = fetch_fundamentals("RELIANCE.NS", use_cache=True)
    if fd.get("ebit") is not None and fd.get("enterprise_value") not in (None, 0):
        expected = fd["ebit"] / fd["enterprise_value"]
        assert fd["earnings_yield"] is not None
        assert math.isclose(fd["earnings_yield"], expected, rel_tol=1e-6)


def test_magic_formula_real_fundamentals():
    data = _make_data(600, 8, seed=11)
    trades, eq = mf_backtest(data, top_decile=0.25, cost=0.001, use_real_fundamentals=True)
    assert isinstance(trades, list)
    assert isinstance(eq, pd.DataFrame)
    assert len(eq) == 600

    trades_p, eq_p = mf_backtest(data, top_decile=0.25, cost=0.001, use_real_fundamentals=False)
    assert isinstance(trades_p, list)
    assert isinstance(eq_p, pd.DataFrame)
    assert len(eq_p) == 600


def test_options_real_fallback():
    trades, eq = covered_call_real("RELIANCE.NS", capital=1_000_000)
    assert isinstance(trades, list)
    assert isinstance(eq, pd.DataFrame)
    assert not eq.empty
    assert eq["equity"].iloc[0] > 0
    actions = {t["action"] for t in trades}
    assert "buy" in actions
    assert "sell_call" in actions
