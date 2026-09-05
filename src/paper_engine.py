"""Paper trading engine — runs strategies, derives target weights, drives rebalance + reports."""
from __future__ import annotations
import pandas as pd

from src.paper import PaperBroker
from src.data import fetch_many
from src.universe import NIFTY15


def get_latest_prices(tickers: list[str], period: str = "5d") -> dict[str, float]:
    """Last close per ticker. Empty dict if fetch fails (caller decides fallback)."""
    try:
        data = fetch_many(tickers, period=period)
        return {t: float(df["close"].iloc[-1]) for t, df in data.items()
                if df is not None and not df.empty}
    except Exception:
        return {}


def run_rebalance(broker: PaperBroker, strategy_id: str,
                  tickers: list[str], period: str = "3mo") -> dict:
    """Run a strategy on recent data, derive target weights, rebalance broker.

    Simplified: top-N tickers held in recent backtest trades get equal weight.
    """
    from src.registry import run_backtest
    from src.tracking import log_strategy_run

    result = run_backtest(strategy_id, tickers, period=period)
    trades = result.get("trades", [])
    held: list[str] = []
    seen: set[str] = set()
    for t in trades[-30:]:
        if t.get("action") == "buy":
            tk = t.get("ticker")
            if tk and tk not in seen:
                seen.add(tk)
                held.append(tk)
        if len(held) >= 5:
            break
    held = held[:5]

    prices = get_latest_prices(held or tickers)
    n = len(held)
    targets = {t: 1.0 / n for t in held} if held else {}
    result_trades = broker.rebalance_to_targets(targets, prices, strategy_id=strategy_id)

    metrics = dict(result.get("metrics", {}))
    metrics["n_trades"] = result.get("info", {}).get("n_trades")
    log_strategy_run(strategy_id, tickers, period, broker.capital, metrics)

    return {
        "strategy_id": strategy_id,
        "targets": targets,
        "trades": result_trades,
        "metrics": result.get("metrics", {}),
    }


def daily_report(broker: PaperBroker) -> dict:
    """Generate daily P&L snapshot + recent trades."""
    snap_prices = get_latest_prices(["RELIANCE.NS", "TCS.NS", "INFY.NS",
                                     "HDFCBANK.NS", "ITC.NS"])
    snap = broker.snapshot_pnl(snap_prices)
    state = broker.mark_to_market(snap_prices)
    return {
        "as_of": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "cash": snap["cash"],
        "equity": snap["equity"],
        "positions_value": snap["positions_value"],
        "daily_pnl": state["daily_pnl"],
        "total_pnl": snap["total_pnl"],
        "n_positions": snap["n_positions"],
        "positions": snap["positions"],
        "recent_trades": broker.list_trades(limit=10),
    }
