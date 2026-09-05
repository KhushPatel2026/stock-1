import pandas as pd
import numpy as np

from src import donchian, keltner_break, aroon, macd, supertrend, ichimoku, hull_ma, parabolic_sar


def _make_data(n=400, tickers=10, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    data = {}
    for i in range(tickers):
        close = 100 + np.cumsum(rng.normal(0.1, 0.8, n))
        open_ = close + rng.normal(0, 0.3, n)
        high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.5, n))
        low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.5, n))
        data[f"T{i}.NS"] = pd.DataFrame(
            {"close": close, "open": open_, "high": high, "low": low,
             "volume": rng.integers(500_000, 2_000_000, n)},
            index=idx,
        )
    return data


def _check(mod, **kwargs):
    data = _make_data(400, 10, 0)
    trades, eq = mod.backtest(data, **kwargs)
    assert isinstance(eq, pd.DataFrame), "equity must be DataFrame"
    assert not eq.empty, "equity must not be empty"
    assert len(eq) == 400, f"equity length {len(eq)} != 400"
    assert isinstance(trades, list), "trades must be list"
    for t in trades:
        assert {"ticker", "date", "action", "price", "shares"} <= set(t.keys()), f"trade missing keys: {t}"
    return trades, eq


def _check_meta(mod, required):
    assert hasattr(mod, "META"), f"{mod.__name__} missing META"
    assert mod.META["family"] == "Trend"
    for k in required:
        assert k in mod.META["params"], f"{mod.__name__} META missing param {k}"


def test_donchian():
    _check_meta(donchian, ["entry_n", "exit_n", "top_n", "cost"])
    _check(donchian, entry_n=20, exit_n=10, top_n=5, cost=0.001)


def test_keltner_break():
    _check_meta(keltner_break, ["ema_n", "atr_n", "k", "top_n", "cost"])
    _check(keltner_break, ema_n=20, atr_n=14, k=2.0, top_n=5, cost=0.001)


def test_aroon():
    _check_meta(aroon, ["n", "up_thresh", "down_thresh", "top_n", "cost"])
    _check(aroon, n=25, up_thresh=80, down_thresh=50, top_n=5, cost=0.001)


def test_macd():
    _check_meta(macd, ["fast", "slow", "signal", "top_n", "cost"])
    _check(macd, fast=12, slow=26, signal=9, top_n=5, cost=0.001)


def test_supertrend():
    _check_meta(supertrend, ["atr_n", "mult", "top_n", "cost"])
    _check(supertrend, atr_n=14, mult=3.0, top_n=5, cost=0.001)


def test_ichimoku():
    _check_meta(ichimoku, ["tenkan_n", "kijun_n", "senkou_b_n", "shift", "top_n", "cost"])
    _check(ichimoku, tenkan_n=9, kijun_n=26, senkou_b_n=52, shift=26, top_n=5, cost=0.001)


def test_hull_ma():
    _check_meta(hull_ma, ["n", "top_n", "cost"])
    _check(hull_ma, n=20, top_n=5, cost=0.001)


def test_parabolic_sar():
    _check_meta(parabolic_sar, ["accel", "max_accel", "top_n", "cost"])
    _check(parabolic_sar, accel=0.02, max_accel=0.2, top_n=5, cost=0.001)
