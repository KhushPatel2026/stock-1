"""Paper trading engine — runs strategies, derives target weights, drives rebalance + reports."""
from __future__ import annotations
import importlib
import pandas as pd
from src.paper import PaperBroker
from src.data import fetch_many
from src.universe import NIFTY15
from src.registry import _REGISTRY


def get_latest_prices(tickers: list[str], period: str = "5d") -> dict[str, float]:
    """Last close per ticker. Empty dict if fetch fails (caller decides fallback)."""
    try:
        data = fetch_many(tickers, period=period)
        return {t: float(df["close"].iloc[-1]) for t, df in data.items() if df is not None and not df.empty}
    except Exception:
        return {}


def _accumulate_shares(trades: list[dict], as_of: pd.Timestamp) -> dict[str, int]:
    """Walk trade log up to as_of; return per-ticker net share count.

    Handles actions: buy (+qty), sell (-qty), long (+qty), short (-qty), close (→0).
    """
    shares: dict[str, int] = {}
    for t in trades:
        d_raw = t.get("date")
        try:
            d = pd.Timestamp(d_raw)
        except Exception:
            continue
        if d > as_of:
            continue
        tk = t.get("ticker")
        action = t.get("action")
        qty = int(t.get("shares", 0) or 0)
        if action in ("buy", "long"):
            shares[tk] = shares.get(tk, 0) + qty
        elif action == "sell":
            shares[tk] = shares.get(tk, 0) - qty
        elif action == "short":
            # sector_momentum logs shares=-qty for shorts; we want net -qty
            raw = int(t.get("shares", 0) or 0)
            shares[tk] = shares.get(tk, 0) + raw
        elif action == "close":
            shares[tk] = 0
    return shares


def run_rebalance(broker: PaperBroker, strategy_id: str = "bollinger",
                  tickers: list[str] | None = None, period: str = "3mo") -> dict:
    """Run a strategy, derive target weights at the last bar, rebalance broker."""
    if tickers is None:
        tickers = NIFTY15

    entry = next((s for s in _REGISTRY if s["id"] == strategy_id), None)
    if entry is None:
        raise ValueError(f"unknown strategy: {strategy_id}")

    mod = importlib.import_module(entry["module"])
    fn = getattr(mod, entry["fn"])
    try:
        data = fetch_many(tickers, period=period)
    except Exception as e:
        return {"strategy": strategy_id, "trades": [], "n_trades": 0, "error": f"fetch failed: {e}"}
    if not data:
        return {"strategy": strategy_id, "trades": [], "n_trades": 0, "note": "no data"}

    merged = {**entry["default_params"]}
    if hasattr(mod, "META"):
        merged.update(mod.META.get("params", {}))
    try:
        result = fn(data, **merged)
    except TypeError:
        result = fn(data)
    except Exception as e:
        return {"strategy": strategy_id, "trades": [], "n_trades": 0, "error": f"backtest failed: {e}"}

    trades, eq = result[0], result[1]
    if eq is None or len(eq) == 0:
        return {"strategy": strategy_id, "trades": [], "n_trades": 0, "note": "empty equity curve"}

    last_date = pd.Timestamp(eq.index[-1])
    last_eq = float(eq["equity"].iloc[-1])
    prices: dict[str, float] = {}
    for t in tickers:
        df = data.get(t)
        if df is None or df.empty:
            continue
        try:
            prices[t] = float(df["close"].iloc[-1])
        except Exception:
            continue

    net = _accumulate_shares(trades, last_date)
    targets: dict[str, float] = {}
    for t, sh in net.items():
        if sh <= 0 or t not in prices or last_eq <= 0:
            continue  # ponytail: long-only paper broker
        w = (sh * prices[t]) / last_eq
        if w > 0:
            targets[t] = round(float(w), 4)

    rebalance = broker.rebalance_to_targets(targets, prices)
    return {
        "strategy": strategy_id,
        "as_of": str(last_date.date()),
        "targets": targets,
        "rebalance": rebalance,
    }


def daily_report(broker: PaperBroker) -> dict:
    """Daily P&L snapshot + recent trades."""
    snap = broker.mark_to_market(dict(broker.last_prices))
    return {
        "as_of": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "cash": snap["cash"],
        "equity": snap["equity"],
        "daily_pnl": snap["daily_pnl"],
        "total_pnl": snap["total_pnl"],
        "n_positions": snap["n_positions"],
        "n_trades": len(broker.trade_log),
        "positions": snap["positions"],
        "recent_trades": broker.trade_log[-10:],
    }
