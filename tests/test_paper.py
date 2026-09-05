"""Tests for SQLite-backed paper trading broker + tracking."""
from __future__ import annotations
import pytest

from src.paper import PaperBroker
from src.tracking import (
    log_strategy_run,
    log_strategy_selection,
    get_most_used_strategies,
    get_recent_runs,
)


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "test_paper.db")


@pytest.fixture
def broker(db):
    return PaperBroker(name="test", db_path=db, capital=100_000, slippage_bps=0)


def test_db_initialization(db):
    """Fresh DB creates schema + default portfolio."""
    import sqlite3
    b = PaperBroker(name="alpha", db_path=db, capital=500_000, slippage_bps=5)
    assert b.capital == 500_000
    assert b.slippage_bps == 5
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert {"portfolios", "positions", "trades",
                "pnl_snapshots", "strategy_runs"} <= tables
        row = conn.execute(
            "SELECT name, capital, cash FROM portfolios WHERE name='alpha'"
        ).fetchone()
        assert row["name"] == "alpha"
        assert row["capital"] == 500_000
        assert row["cash"] == 500_000
    finally:
        conn.close()


def test_multiple_portfolios(db):
    """Different names = different portfolios sharing one DB."""
    a = PaperBroker(name="alpha", db_path=db, capital=100_000, slippage_bps=0)
    b = PaperBroker(name="bravo", db_path=db, capital=200_000, slippage_bps=0)
    a.place_order("RELIANCE.NS", "buy", 10, 100.0)

    assert a.get_state({"RELIANCE.NS": 100.0})["cash"] == pytest.approx(99_000)
    assert b.get_state()["cash"] == pytest.approx(200_000)
    assert "RELIANCE.NS" not in b.get_state()["positions"]

    out = b.list_portfolios()
    names = [p["name"] for p in out]
    assert names == ["alpha", "bravo"]
    assert {p["capital"] for p in out} == {100_000, 200_000}


def test_persistence_across_instances(db):
    """State survives broker reload."""
    b1 = PaperBroker(name="test", db_path=db, capital=100_000, slippage_bps=0)
    b1.place_order("RELIANCE.NS", "buy", 10, 100.0)
    b1.place_order("TCS.NS", "buy", 5, 200.0)
    snap = b1.snapshot_pnl({"RELIANCE.NS": 110.0, "TCS.NS": 210.0})

    b2 = PaperBroker(name="test", db_path=db, capital=100_000, slippage_bps=0)
    assert b2.capital == 100_000
    state = b2.get_state({"RELIANCE.NS": 110.0, "TCS.NS": 210.0})
    assert state["cash"] == pytest.approx(100_000 - 1_000 - 1_000)
    assert state["positions"]["RELIANCE.NS"]["shares"] == 10
    assert state["positions"]["TCS.NS"]["shares"] == 5
    assert len(b2.list_trades(limit=10)) == 2


def test_trade_history(db, broker):
    """place_order writes trade rows; list_trades returns them newest-first."""
    broker.place_order("RELIANCE.NS", "buy", 10, 100.0)
    broker.place_order("TCS.NS", "buy", 5, 200.0, strategy_id="bollinger")
    broker.place_order("RELIANCE.NS", "sell", 5, 110.0)

    trades = broker.list_trades(limit=10)
    assert len(trades) == 3
    assert trades[0]["ticker"] == "RELIANCE.NS"
    assert trades[0]["side"] == "sell"
    assert trades[0]["qty"] == 5
    assert trades[0]["fill_price"] == pytest.approx(110.0)
    assert trades[1]["strategy_id"] == "bollinger"
    assert trades[2]["strategy_id"] is None


def test_pnl_snapshots(db, broker):
    """snapshot_pnl inserts a row + returns state."""
    broker.place_order("RELIANCE.NS", "buy", 10, 100.0)
    snap = broker.snapshot_pnl({"RELIANCE.NS": 110.0})
    assert snap["cash"] == pytest.approx(99_000)
    assert snap["equity"] == pytest.approx(99_000 + 1_100)
    assert snap["positions_value"] == pytest.approx(1_100)

    # second snapshot at higher price — positions_value should grow
    snap2 = broker.snapshot_pnl({"RELIANCE.NS": 120.0})
    assert snap2["equity"] == pytest.approx(99_000 + 1_200)

    import sqlite3
    conn = sqlite3.connect(db)
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM pnl_snapshots WHERE portfolio_id IN "
            "(SELECT id FROM portfolios WHERE name='test')"
        ).fetchone()[0]
        assert n == 2
    finally:
        conn.close()


def test_rebalance_to_targets(db, broker):
    """Sells excess, buys to target weights."""
    prices = {"RELIANCE.NS": 100.0, "TCS.NS": 200.0}
    res = broker.rebalance_to_targets(
        {"RELIANCE.NS": 0.6, "TCS.NS": 0.4}, prices, strategy_id="test_strat"
    )
    assert res["n_trades"] == 2
    state = broker.get_state(prices)
    rel_w = state["positions"]["RELIANCE.NS"]["shares"] * 100.0 / state["equity"]
    tcs_w = state["positions"]["TCS.NS"]["shares"] * 200.0 / state["equity"]
    assert rel_w == pytest.approx(0.6, abs=0.01)
    assert tcs_w == pytest.approx(0.4, abs=0.01)
    for t in broker.list_trades(limit=10):
        if t["ticker"] in ("RELIANCE.NS", "TCS.NS"):
            assert t["strategy_id"] == "test_strat"


def test_rebalance_trims_existing(db, broker):
    """Existing positions get trimmed if target weight is smaller or zero."""
    broker.place_order("RELIANCE.NS", "buy", 500, 100.0)  # ~50% of capital
    prices = {"RELIANCE.NS": 100.0, "TCS.NS": 200.0}
    res = broker.rebalance_to_targets({"TCS.NS": 1.0}, prices)
    assert res["n_trades"] >= 2  # sell RELIANCE, buy TCS
    state = broker.get_state(prices)
    assert "RELIANCE.NS" not in state["positions"]
    assert state["positions"]["TCS.NS"]["shares"] > 0


def test_slippage(db):
    """Buy fills higher, sell fills lower by slippage_bps."""
    b = PaperBroker(name="slip", db_path=db, capital=100_000, slippage_bps=10)
    buy = b.place_order("RELIANCE.NS", "buy", 10, 100.0)
    assert buy["fill_price"] == pytest.approx(100.10)
    sell = b.place_order("RELIANCE.NS", "sell", 10, 100.0)
    assert sell["fill_price"] == pytest.approx(99.90)


def test_reset(db, broker):
    """reset() clears positions, trades, snapshots; restores cash to capital."""
    broker.place_order("RELIANCE.NS", "buy", 10, 100.0)
    broker.snapshot_pnl({"RELIANCE.NS": 100.0})
    broker.reset()
    state = broker.get_state()
    assert state["cash"] == 100_000
    assert state["positions"] == {}
    assert state["n_positions"] == 0
    assert broker.list_trades(limit=10) == []


def test_insufficient_cash(db):
    """Buy qty larger than cash budget gets capped or rejected."""
    b = PaperBroker(name="poor", db_path=db, capital=1_000, slippage_bps=0)
    res = b.place_order("EXPENSIVE.NS", "buy", 100, 100.0)  # would cost 10_000
    assert res["filled"] == 10  # capped to what 1000 / 100 allows
    assert b.get_state()["cash"] == pytest.approx(0)


def test_strategy_selection_logging(db):
    """log_strategy_selection writes a row; get_most_used_strategies counts it."""
    log_strategy_selection("bollinger", db_path=db)
    log_strategy_selection("bollinger", db_path=db)
    log_strategy_selection("macd", db_path=db)

    top = get_most_used_strategies(limit=10, db_path=db)
    by_id = {r["strategy_id"]: r for r in top}
    assert by_id["bollinger"]["count"] == 2
    assert by_id["macd"]["count"] == 1
    assert top[0]["strategy_id"] == "bollinger"
    assert "last_used" in top[0]


def test_strategy_run_logging(db):
    """log_strategy_run stores metrics + serializes tickers as JSON."""
    rid = log_strategy_run(
        "rsi2", ["AAPL", "MSFT"], "1y", 100_000.0,
        {"sharpe": 1.5, "total_return": 0.23, "max_drawdown": -0.10, "n_trades": 42},
        db_path=db,
    )
    assert rid > 0
    runs = get_recent_runs(limit=10, db_path=db)
    assert runs[0]["strategy_id"] == "rsi2"
    assert runs[0]["tickers"] == ["AAPL", "MSFT"]
    assert runs[0]["sharpe"] == pytest.approx(1.5)
    assert runs[0]["total_return"] == pytest.approx(0.23)
    assert runs[0]["max_dd"] == pytest.approx(-0.10)
    assert runs[0]["n_trades"] == 42
    assert runs[0]["period"] == "1y"


def test_most_used_strategies_ordering(db):
    """Counts aggregate selections + runs; ordered by count desc."""
    for _ in range(5):
        log_strategy_selection("alpha_strat", db_path=db)
    for _ in range(3):
        log_strategy_selection("beta_strat", db_path=db)
    for _ in range(7):
        log_strategy_run("alpha_strat", ["X"], "3mo", 1000.0, {}, db_path=db)

    top = get_most_used_strategies(limit=10, db_path=db)
    assert top[0]["strategy_id"] == "alpha_strat"
    assert top[0]["count"] == 12
    assert top[1]["strategy_id"] == "beta_strat"
    assert top[1]["count"] == 3


def test_default_portfolio_persists_capital(db):
    """Reopening default portfolio with different capital does NOT reset existing cash."""
    PaperBroker(name="default", db_path=db, capital=50_000, slippage_bps=0)
    PaperBroker(name="default", db_path=db, capital=999_999, slippage_bps=0)
    state = PaperBroker(name="default", db_path=db, capital=999_999, slippage_bps=0)
    assert state.capital == 50_000  # original capital preserved
    assert state.get_state()["cash"] == pytest.approx(50_000)


def test_list_portfolios_with_positions(db):
    """list_portfolios reports equity using avg_cost when no live prices."""
    a = PaperBroker(name="a", db_path=db, capital=100_000, slippage_bps=0)
    b = PaperBroker(name="b", db_path=db, capital=100_000, slippage_bps=0)
    a.place_order("X", "buy", 100, 50.0)
    b.place_order("Y", "buy", 200, 100.0)

    portfolios = PaperBroker(name="x", db_path=db).list_portfolios()
    by_name = {p["name"]: p for p in portfolios}
    assert by_name["a"]["positions_value"] == pytest.approx(5_000)
    assert by_name["b"]["positions_value"] == pytest.approx(20_000)
    # At avg_cost there's no mark-to-market gain/loss → pnl == 0 for both.
    assert by_name["a"]["total_pnl"] == pytest.approx(0)
    assert by_name["b"]["total_pnl"] == pytest.approx(0)
    assert by_name["a"]["equity"] == pytest.approx(100_000)
    assert by_name["b"]["equity"] == pytest.approx(100_000)
