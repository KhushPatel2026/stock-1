"""Validation: walk-forward OOS chunks + regime-conditioned metrics (FEAT-007A/B).

Public API:
    `run_walk_forward(strategy_id, tickers, period, chunk)` — chunked OOS, summary row.
    `run_regime_tests(strategy_id, tickers)` — per-regime metrics (Sharpe/ret/DD).
    `run_all(tickers, output_dir)` — iterate every registered strategy, write CSVs + MD.

Internal: `chunk_oos`, `walk_forward`, `_run_strategy`, `_oos_metrics`, `_mock_data`.
"""
from __future__ import annotations
import importlib
from pathlib import Path

import numpy as np
import pandas as pd

from src.registry import _REGISTRY
from src.data import fetch_many


REGIMES: dict[str, tuple[str, str]] = {
    "2018_crash": ("2018-01-01", "2018-12-31"),
    "2020_covid": ("2020-02-01", "2020-07-31"),
    "2022_chop":  ("2022-01-01", "2022-12-31"),
    "full":       ("2017-01-01", "2025-12-31"),
}


def _run_strategy(strategy_id: str, data: dict, params: dict | None = None) -> tuple[list, pd.DataFrame]:
    """Invoke a strategy's registered `backtest` function with merged params."""
    entry = next(s for s in _REGISTRY if s["id"] == strategy_id)
    mod = importlib.import_module(entry["module"])
    fn = getattr(mod, entry["fn"])
    merged: dict = {}
    if hasattr(mod, "META") and isinstance(mod.META, dict):
        merged.update(mod.META.get("params", {}))
    merged.update(entry["default_params"])
    if params:
        for k, v in params.items():
            if v is not None:
                merged[k] = v
    try:
        result = fn(data, **merged)
    except TypeError:
        result = fn(data)
    trades, eq = result[0], result[1]
    if not isinstance(eq, pd.DataFrame):
        eq = pd.DataFrame(eq)
    if eq.empty:
        return trades, eq
    if "equity" not in eq.columns:
        eq = eq.rename(columns={eq.columns[0]: "equity"})
    eq = eq[["equity"]].copy()
    eq.index = pd.to_datetime(eq.index)
    eq = eq[~eq.index.duplicated(keep="last")].sort_index()
    return trades, eq


def _oos_metrics(eq: pd.DataFrame) -> dict:
    """Sharpe, total_return, max_dd, n_bars for an equity curve slice."""
    if eq is None or eq.empty or len(eq) < 2:
        return {"sharpe": 0.0, "total_return": 0.0, "max_dd": 0.0, "n_bars": int(len(eq)) if eq is not None else 0}
    s = eq["equity"].astype(float)
    rets = s.pct_change().dropna()
    sharpe = float(rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 and len(rets) > 1 else 0.0
    total_ret = float(s.iloc[-1] / s.iloc[0] - 1) if s.iloc[0] > 0 else 0.0
    dd = (s - s.cummax()) / s.cummax()
    max_dd = float(dd.min()) if not dd.empty else 0.0
    return {
        "sharpe": round(sharpe, 4),
        "total_return": round(total_ret, 4),
        "max_dd": round(max_dd, 4),
        "n_bars": int(len(eq)),
    }


def _slice_period(eq: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    if eq.empty:
        return eq
    return eq.loc[pd.Timestamp(start):pd.Timestamp(end)]


def chunk_oos(strategy_id: str, tickers: list[str], period: str = "5y", chunk: int = 126,
              data: dict | None = None) -> pd.DataFrame:
    """Run full backtest, split equity into non-overlapping chunks of size `chunk`."""
    if data is None:
        data = fetch_many(tickers, period=period)
    _, eq = _run_strategy(strategy_id, data)
    if eq.empty:
        return pd.DataFrame(columns=["strategy_id", "window", "start", "end", "sharpe", "total_return", "max_dd", "n_bars"])
    rows = []
    n = len(eq)
    i = 0
    w = 0
    while i + chunk <= n:
        sub = eq.iloc[i:i + chunk]
        m = _oos_metrics(sub)
        rows.append({
            "strategy_id": strategy_id,
            "window": w,
            "start": str(sub.index[0].date()),
            "end": str(sub.index[-1].date()),
            **m,
        })
        i += chunk
        w += 1
    if i < n and n - i >= 30:
        sub = eq.iloc[i:]
        m = _oos_metrics(sub)
        rows.append({
            "strategy_id": strategy_id,
            "window": w,
            "start": str(sub.index[0].date()),
            "end": str(sub.index[-1].date()),
            **m,
        })
    return pd.DataFrame(rows)


def walk_forward(strategy_id: str, tickers: list[str], period: str = "5y",
                 train: int = 504, test: int = 126, step: int = 126) -> pd.DataFrame:
    """Rolling walk-forward: per fold, run backtest on [i, i+train+test), OOS = last `test` bars."""
    data = fetch_many(tickers, period=period)
    if not data:
        return pd.DataFrame(columns=["strategy_id", "fold", "oos_start", "oos_end", "sharpe", "total_return", "max_dd", "n_bars"])
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    n = len(all_dates)
    rows = []
    fold = 0
    i = 0
    while i + train + test <= n:
        win_dates = all_dates[i:i + train + test]
        sliced = {t: df.loc[win_dates[0]:win_dates[-1]] for t, df in data.items()}
        sliced = {t: d for t, d in sliced.items() if not d.empty}
        if sliced:
            try:
                _, eq = _run_strategy(strategy_id, sliced)
            except Exception:
                eq = pd.DataFrame(columns=["equity"])
            if not eq.empty and len(eq) >= test:
                oos = eq.iloc[-test:]
                m = _oos_metrics(oos)
                rows.append({
                    "strategy_id": strategy_id,
                    "fold": fold,
                    "oos_start": str(oos.index[0].date()),
                    "oos_end": str(oos.index[-1].date()),
                    **m,
                })
        i += step
        fold += 1
    return pd.DataFrame(rows)


def run_walk_forward(strategy_id: str, tickers: list[str], period: str = "5y", chunk: int = 126,
                     data: dict | None = None) -> pd.DataFrame:
    """Public wrapper around `chunk_oos` returning a single summary row per strategy."""
    df = chunk_oos(strategy_id, tickers, period=period, chunk=chunk, data=data)
    if df.empty:
        return pd.DataFrame([{
            "strategy_id": strategy_id, "n_windows": 0,
            "mean_oos_sharpe": 0.0, "total_oos_return": 0.0, "max_dd": 0.0,
        }])
    mean_sharpe = float(df["sharpe"].mean())
    compounded = float((1 + df["total_return"]).prod() - 1)
    worst_dd = float(df["max_dd"].min())
    return pd.DataFrame([{
        "strategy_id": strategy_id,
        "n_windows": int(len(df)),
        "mean_oos_sharpe": round(mean_sharpe, 4),
        "total_oos_return": round(compounded, 4),
        "max_dd": round(worst_dd, 4),
    }])


def run_regime_tests(strategy_id: str, tickers: list[str]) -> pd.DataFrame:
    """Run full-period backtest, slice equity into each regime window, compute metrics."""
    data = fetch_many(tickers, period="10y")
    _, eq = _run_strategy(strategy_id, data)
    rows = []
    for regime, (start, end) in REGIMES.items():
        sub = _slice_period(eq, start, end)
        m = _oos_metrics(sub) if not sub.empty else {"sharpe": 0.0, "total_return": 0.0, "max_dd": 0.0, "n_bars": 0}
        rows.append({"strategy_id": strategy_id, "regime": regime, **m})
    return pd.DataFrame(rows)


def _mock_data(n: int = 1500, tickers: int = 8, seed: int = 0) -> dict[str, pd.DataFrame]:
    """Deterministic synthetic OHLCV covering 2017..2022+ for tests."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2017-01-01", periods=n, freq="B")
    out: dict[str, pd.DataFrame] = {}
    for i in range(tickers):
        close = 100 + np.cumsum(rng.normal(0.05, 1.0, n))
        open_ = close + rng.normal(0, 0.3, n)
        high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.5, n))
        low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.5, n))
        out[f"MOCK{i}.NS"] = pd.DataFrame(
            {"close": close, "open": open_, "high": high, "low": low,
             "volume": rng.integers(500_000, 2_000_000, n)},
            index=idx,
        )
    return out


def _md_table(df: pd.DataFrame, headers: list[str], align: list[str] | None = None) -> str:
    """Hand-rolled markdown table (no tabulate dep)."""
    if df.empty:
        return "| " + " | ".join(headers) + " |\n|" + "|".join(["---"] * len(headers)) + "|\n"
    align = align or ["---"] * len(headers)
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join(f" {a} " for a in align) + "|"
    lines = [head, sep]
    for _, row in df.iterrows():
        cells = []
        for h in headers:
            v = row[h]
            if isinstance(v, float):
                cells.append(f"{v:.4f}" if abs(v) < 100 else f"{v:.2f}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _format_regime_md(regimes_df: pd.DataFrame) -> str:
    """Pivot regime_df into strategy rows × regime-column Sharpe table."""
    if regimes_df.empty:
        return "*(no regime data)*\n"
    pivot = regimes_df.pivot(index="strategy_id", columns="regime", values="sharpe").reset_index()
    regime_order = [r for r in REGIMES.keys() if r in pivot.columns]
    headers = ["strategy_id"] + regime_order
    align = ["---"] + ["---:"] * len(regime_order)
    sub = pivot[headers].copy()
    for c in regime_order:
        sub[c] = sub[c].map(lambda x: round(float(x), 2) if pd.notna(x) else None)
    return _md_table(sub, headers, align)


def run_all(tickers: list[str] | None = None, output_dir: str = "reports") -> dict:
    """Iterate every registered strategy, write walk_forward.csv, regime_tests.csv, regime_tests.md."""
    if tickers is None:
        tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    wf_rows: list[dict] = []
    regime_rows: list[pd.DataFrame] = []
    for entry in _REGISTRY:
        sid = entry["id"]
        try:
            wf = run_walk_forward(sid, tickers, period="5y", chunk=126)
            wf_rows.append(wf.iloc[0].to_dict())
        except Exception as e:  # ponytail: don't lose a strategy on transient failure
            wf_rows.append({
                "strategy_id": sid, "n_windows": 0,
                "mean_oos_sharpe": 0.0, "total_oos_return": 0.0, "max_dd": 0.0,
                "error": str(e)[:120],
            })
        try:
            reg = run_regime_tests(sid, tickers)
            regime_rows.append(reg)
        except Exception as e:
            print(f"regime {sid} failed: {e}")

    wf_df = pd.DataFrame(wf_rows)
    reg_df = pd.concat(regime_rows, ignore_index=True) if regime_rows else pd.DataFrame(
        columns=["strategy_id", "regime", "sharpe", "total_return", "max_dd", "n_bars"]
    )

    wf_df.to_csv(out / "walk_forward.csv", index=False)
    reg_df.to_csv(out / "regime_tests.csv", index=False)

    md = ["# Regime tests — Sharpe per regime\n", _format_regime_md(reg_df)]
    (out / "regime_tests.md").write_text("\n".join(md))

    return {
        "walk_forward": wf_df,
        "regime_tests": reg_df,
        "md_path": str(out / "regime_tests.md"),
        "csv_paths": [str(out / "walk_forward.csv"), str(out / "regime_tests.csv")],
    }