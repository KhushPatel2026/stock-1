import pandas as pd, numpy as np
from src.breakout_volume import backtest

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

def test_breakout_volume():
    data = _make_data(400, 10, 99)
    trades, eq = backtest(data, lookback=20, vol_mult=1.5, top_n=3)
    assert isinstance(eq, pd.DataFrame) and not eq.empty
    assert len(eq) == 400
    assert isinstance(trades, list)
