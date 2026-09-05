"""Tests for paper-trading simulator (FEAT-009)."""
import json
import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from src.paper import PaperBroker
from src.paper_engine import run_rebalance, daily_report
from src.signals import compute_signals, signal_for_strategy


@pytest.fixture
def tmp_state_path():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    if os.path.exists(path):
        os.unlink(path)
    try:
        yield path
    finally:
        if os.path.exists(path):
            os.unlink(path)


def _trending_df(direction: int, n: int = 60, start: float = 100.0) -> pd.DataFrame:
    """Pure trending OHLCV (no noise) — direction = +1 or -1."""
    prices = np.array([start * (1 + 0.01 * i * direction) for i in range(n)])
    return pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.005,
            "low": prices * 0.995,
            "close": prices,
            "volume": np.full(n, 100_000, dtype=float),
        },
        index=pd.date_range("2025-01-01", periods=n, freq="D"),
    )


def test_paper_broker_init(tmp_state_path):
    b = PaperBroker(capital=100_000, slippage_bps=5, state_path=tmp_state_path)
    assert b.cash == 100_000
    assert b.positions == {}
    assert b.capital == 100_000
    assert b.slippage_bps == 5
    assert b.trade_log == []
    assert b.prev_equity is None


def test_paper_broker_buy(tmp_state_path):
    b = PaperBroker(capital=100_000, slippage_bps=0, state_path=tmp_state_path)
    res = b.place_order("RELIANCE.NS", "buy", 10, 100.0)
    assert res["filled"] == 10
    assert b.cash == pytest.approx(99_000)
    assert b.positions["RELIANCE.NS"]["shares"] == 10
    assert b.positions["RELIANCE.NS"]["avg_cost"] == pytest.approx(100.0)
    assert len(b.trade_log) == 1


def test_paper_broker_sell(tmp_state_path):
    b = PaperBroker(capital=100_000, slippage_bps=0, state_path=tmp_state_path)
    b.place_order("RELIANCE.NS", "buy", 10, 100.0)
    res = b.place_order("RELIANCE.NS", "sell", 10, 110.0)
    assert res["filled"] == 10
    assert b.cash == pytest.approx(99_000 + 1_100)
    assert "RELIANCE.NS" not in b.positions


def test_paper_broker_slippage(tmp_state_path):
    """buy fills higher than ref, sell fills lower than ref."""
    b = PaperBroker(capital=100_000, slippage_bps=10, state_path=tmp_state_path)
    buy = b.place_order("RELIANCE.NS", "buy", 10, 100.0)
    assert buy["fill_price"] == pytest.approx(100.10)
    sell = b.place_order("RELIANCE.NS", "sell", 10, 100.0)
    assert sell["fill_price"] == pytest.approx(99.90)


def test_paper_broker_mark_to_market(tmp_state_path):
    b = PaperBroker(capital=100_000, slippage_bps=0, state_path=tmp_state_path)
    b.place_order("RELIANCE.NS", "buy", 10, 100.0)
    snap = b.mark_to_market({"RELIANCE.NS": 110.0})
    assert snap["equity"] == pytest.approx(99_000 + 1_100)
    assert snap["positions"]["RELIANCE.NS"]["unrealized_pnl"] == pytest.approx(100)
    assert snap["daily_pnl"] == 0  # first mark — no prior
    # second mark: price jumps again, daily_pnl = delta
    snap2 = b.mark_to_market({"RELIANCE.NS": 120.0})
    assert snap2["daily_pnl"] == pytest.approx(100)
    assert snap2["total_pnl"] == pytest.approx(200)


def test_paper_broker_persist(tmp_state_path):
    b1 = PaperBroker(capital=100_000, slippage_bps=0, state_path=tmp_state_path)
    b1.place_order("RELIANCE.NS", "buy", 10, 100.0)
    b1.mark_to_market({"RELIANCE.NS": 110.0})

    assert os.path.exists(tmp_state_path)
    raw = json.loads(open(tmp_state_path).read())
    assert raw["cash"] == pytest.approx(99_000)

    b2 = PaperBroker(capital=100_000, slippage_bps=0, state_path=tmp_state_path)
    assert b2.cash == pytest.approx(99_000)
    assert b2.positions["RELIANCE.NS"]["shares"] == 10
    assert b2.positions["RELIANCE.NS"]["avg_cost"] == pytest.approx(100.0)
    assert len(b2.trade_log) >= 1


def test_paper_broker_reset(tmp_state_path):
    b = PaperBroker(capital=100_000, slippage_bps=0, state_path=tmp_state_path)
    b.place_order("RELIANCE.NS", "buy", 10, 100.0)
    b.reset()
    assert b.cash == 100_000
    assert b.positions == {}
    assert b.trade_log == []
    assert b.prev_equity is None


def test_paper_rebalance(tmp_state_path):
    b = PaperBroker(capital=100_000, slippage_bps=0, state_path=tmp_state_path)
    prices = {"RELIANCE.NS": 100.0, "TCS.NS": 200.0}
    res = b.rebalance_to_targets({"RELIANCE.NS": 0.6, "TCS.NS": 0.4}, prices)
    assert res["n_trades"] == 2
    snap = b.mark_to_market(prices)
    rel_w = (b.positions["RELIANCE.NS"]["shares"] * 100.0) / snap["equity"]
    tcs_w = (b.positions["TCS.NS"]["shares"] * 200.0) / snap["equity"]
    assert rel_w == pytest.approx(0.6, abs=0.01)
    assert tcs_w == pytest.approx(0.4, abs=0.01)


def test_paper_rebalance_trims_existing(tmp_state_path):
    b = PaperBroker(capital=100_000, slippage_bps=0, state_path=tmp_state_path)
    prices = {"RELIANCE.NS": 100.0, "TCS.NS": 200.0}
    b.place_order("RELIANCE.NS", "buy", 500, 100.0)  # ~50% of capital
    res = b.rebalance_to_targets({"TCS.NS": 1.0}, prices)
    assert res["n_trades"] >= 2  # at least sell RELIANCE, buy TCS
    assert "RELIANCE.NS" not in b.positions
    assert b.positions["TCS.NS"]["shares"] > 0


def test_signals_long_short_flat():
    """Pure-trend data produces correct classification for macd."""
    up = _trending_df(direction=1, n=80)
    down = _trending_df(direction=-1, n=80)
    flat_df = _trending_df(direction=0, n=80)  # constant price

    up_sig, up_str = signal_for_strategy("macd", up)
    assert up_sig == "long"
    assert 0 < up_str <= 1

    down_sig, down_str = signal_for_strategy("macd", down)
    assert down_sig == "short"
    assert 0 < down_str <= 1

    # flat price: macd diff == 0 → flat
    flat_sig, _ = signal_for_strategy("macd", flat_df)
    assert flat_sig == "flat"

    # MR: extreme drop → long via z-score
    mr_down = _trending_df(direction=-1, n=120)  # sustained downtrend → z << 0
    mr_sig, _ = signal_for_strategy("bollinger", mr_down)
    assert mr_sig in ("long", "flat")  # may or may not be triggered depending on z


def test_signals_smoke():
    """compute_signals returns proper structure (skip on yfinance failure)."""
    from src.universe import NIFTY15

    try:
        result = compute_signals(NIFTY15[:3], period="5d")
    except Exception as e:
        pytest.skip(f"yfinance unavailable: {e}")

    assert "as_of" in result
    assert "signals" in result
    assert isinstance(result["signals"], list)
    if not result["signals"]:
        pytest.skip("no signals (empty fetch)")
    for s in result["signals"]:
        assert "strategy_id" in s
        assert "ticker" in s
        assert "signal" in s
        assert s["signal"] in ("long", "flat", "short")
        assert 0 <= s["strength"] <= 1
