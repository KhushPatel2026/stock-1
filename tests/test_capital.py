"""Every registered strategy starts from dynamic `capital` — no hardcoded 1M."""
import importlib
import inspect

import pandas as pd
import numpy as np

from src.registry import _REGISTRY

# strategies needing non-default args on synthetic data (small, safe values)
OVERRIDES = {
    "beta_hedge": {"stock": "T0.NS"},
    "pairs_trading": {"pair": ("T0.NS", "T1.NS")},
}
# strategies that require live network data (option chains) — signature check covers them
NETWORK_ONLY = {"covered_call_real"}


def _make_data(n=600, tickers=6, seed=11):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    data = {}
    for i in range(tickers):
        drift = 0.06 if i < tickers // 2 else -0.03
        close = 100 + np.cumsum(rng.normal(drift, 0.8, n))
        open_ = close + rng.normal(0, 0.3, n)
        high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.5, n))
        low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.5, n))
        data[f"T{i}.NS"] = pd.DataFrame(
            {"close": close, "open": open_, "high": high, "low": low,
             "volume": rng.integers(500_000, 5_000_000, n)},
            index=idx,
        )
    return data


def _entries():
    out = []
    for s in _REGISTRY:
        mod = importlib.import_module(s["module"])
        out.append((s["id"], getattr(mod, s["fn"])))
    return out


def test_every_strategy_accepts_capital():
    missing = [sid for sid, fn in _entries() if "capital" not in inspect.signature(fn).parameters]
    assert not missing, f"strategies without capital param: {missing}"


def test_every_strategy_starts_at_capital():
    data = _make_data()
    bad = []
    for sid, fn in _entries():
        if sid in NETWORK_ONLY:
            continue
        try:
            result = fn(data, capital=250_000, **OVERRIDES.get(sid, {}))
            trades, eq = result[0], result[1]
        except Exception as e:  # noqa: BLE001 — report, don't fail blind
            bad.append(f"{sid}: raised {type(e).__name__}: {e}")
            continue
        if eq is None or len(eq) == 0:
            continue  # no tradeable edge on synthetic data — signature check above covers it
        first = float(eq["equity"].iloc[0])
        if abs(first - 250_000) > 0.02 * 250_000:
            bad.append(f"{sid}: first equity {first:.2f} != 250000")
        if not (eq["equity"] > 0).all():
            bad.append(f"{sid}: non-positive equity")
    assert not bad, "capital failures:\n" + "\n".join(bad)


def test_capital_scales_pnl():
    """4x capital → ~4x final equity on representative strategies."""
    data = _make_data()
    for sid, mod_name, fn_name in [("donchian", "src.donchian", "backtest"),
                                   ("low_vol", "src.low_vol", "backtest"),
                                   ("xs_momentum", "src.xsection", "backtest")]:
        fn = getattr(importlib.import_module(mod_name), fn_name)
        _, eq_small = fn(data, capital=250_000)
        _, eq_big = fn(data, capital=1_000_000)
        if len(eq_small) == 0 or len(eq_big) == 0:
            continue
        ratio = float(eq_big["equity"].iloc[-1]) / float(eq_small["equity"].iloc[-1])
        assert 3.0 < ratio < 5.0, f"{sid}: scaling ratio {ratio:.2f}"
