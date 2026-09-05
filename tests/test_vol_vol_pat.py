import pandas as pd
import numpy as np

from src import (
    vol_breakout, vol_targeting, vol_regime, garch_lite,
    obv, vwap_dev, vpt, ad_line,
    engulfing, hammer, three_soldiers, double_top,
)


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


def _check(mod, expected_family, required_params, **kwargs):
    data = _make_data(400, 10, 0)
    trades, eq = mod.backtest(data, **kwargs)
    assert hasattr(mod, "META"), f"{mod.__name__} missing META"
    assert isinstance(eq, pd.DataFrame), "equity must be DataFrame"
    assert not eq.empty, "equity must not be empty"
    assert len(eq) == 400, f"equity length {len(eq)} != 400"
    assert isinstance(trades, list), "trades must be list"
    assert mod.META["family"] == expected_family
    for k in required_params:
        assert k in mod.META["params"], f"{mod.__name__} META missing param {k}"


def test_vol_breakout():
    _check(vol_breakout, "Volatility", ["k", "atr_n", "cost"], k=1.0, atr_n=14, cost=0.0005)


def test_vol_targeting():
    _check(vol_targeting, "Volatility", ["target_vol", "vol_n", "top_n", "lookback", "max_w", "cost_bps"],
           target_vol=0.15, vol_n=20, top_n=10, lookback=252, max_w=0.1, cost_bps=1.0)


def test_vol_regime():
    _check(vol_regime, "Volatility", ["vol_n", "median_lookback", "top_n", "cost"],
           vol_n=20, median_lookback=252, top_n=5, cost=0.001)


def test_garch_lite():
    _check(garch_lite, "Volatility", ["lam", "realized_n", "top_n", "cost"],
           lam=0.94, realized_n=20, top_n=5, cost=0.001)


def test_obv():
    _check(obv, "Volume", ["obv_n", "sma_n", "max_holdings", "cost"],
           obv_n=20, sma_n=50, max_holdings=5, cost=0.001)


def test_vwap_dev():
    _check(vwap_dev, "Volume", ["vwap_n", "sma_n", "dev", "max_holdings", "cost"],
           vwap_n=20, sma_n=200, dev=0.98, max_holdings=5, cost=0.001)


def test_vpt():
    _check(vpt, "Volume", ["vpt_n", "sma_n", "max_holdings", "cost"],
           vpt_n=20, sma_n=50, max_holdings=5, cost=0.001)


def test_ad_line():
    _check(ad_line, "Volume", ["ad_n", "sma_n", "max_holdings", "cost"],
           ad_n=20, sma_n=50, max_holdings=5, cost=0.001)


def test_engulfing():
    _check(engulfing, "Pattern", ["hold_bars", "max_holdings", "cost"],
           hold_bars=5, max_holdings=5, cost=0.001)


def test_hammer():
    _check(hammer, "Pattern", ["hold_bars", "trend_n", "max_holdings", "cost"],
           hold_bars=5, trend_n=20, max_holdings=5, cost=0.001)


def test_three_soldiers():
    _check(three_soldiers, "Pattern", ["hold_bars", "max_holdings", "cost"],
           hold_bars=5, max_holdings=5, cost=0.001)


def test_double_top():
    _check(double_top, "Pattern", ["lookback", "tol", "min_sep", "max_holdings", "cost"],
           lookback=60, tol=0.05, min_sep=10, max_holdings=5, cost=0.001)