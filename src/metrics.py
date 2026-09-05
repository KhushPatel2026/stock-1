"""Metrics: CAGR, Sharpe, maxDD, win rate."""
import pandas as pd
import numpy as np

def compute_metrics(trades: list[dict], equity: pd.DataFrame, initial: float = 1_000_000) -> dict:
    if equity.empty:
        return {"cagr": 0, "sharpe": 0, "max_dd": 0, "win_rate": 0, "num_trades": 0, "exposure": 0}
    n_days = len(equity)
    final = float(equity["equity"].iloc[-1])
    years = n_days / 252
    cagr = (final / initial) ** (1 / years) - 1 if years > 0 and initial > 0 else 0

    rets = equity["equity"].pct_change().dropna()
    sharpe = float(rets.mean() / rets.std() * np.sqrt(252)) if rets.std() != 0 and len(rets) > 1 else 0

    peak = equity["equity"].cummax()
    dd = (equity["equity"] - peak) / peak
    max_dd = float(dd.min())

    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    win_rate = wins / len(trades) if trades else 0

    # exposure: fraction of days with at least one position (approx from equity vs initial diff)
    # better: computed in portfolio; fallback 0
    exposure = 0  # filled by portfolio if needed
    return {
        "cagr": float(cagr),
        "sharpe": float(sharpe),
        "max_dd": float(max_dd),
        "win_rate": float(win_rate),
        "num_trades": len(trades),
        "exposure": float(exposure),
        "final_equity": final,
    }
