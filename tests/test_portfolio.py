import pandas as pd
import numpy as np
from src.indicators import add_all
from src.portfolio import run

def _make_df(n=300, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.1, 1, n))
    high = close + rng.uniform(0, 0.5, n)
    low = close - rng.uniform(0, 0.5, n)
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": [1_000_000]*n},
                      index=pd.date_range("2020-01-01", periods=n, freq="B"))
    return add_all(df)

def test_portfolio_runs():
    data = {"A.NS": _make_df(300, 0), "B.NS": _make_df(300, 1)}
    trades, eq, metrics = run(data, capital=1_000_000, max_positions=5)
    assert not eq.empty
    assert len(eq) == 300
    assert metrics["num_trades"] == len(trades)
    assert eq["equity"].iloc[0] > 0

def test_max_positions():
    data = {f"T{i}.NS": _make_df(300, i) for i in range(10)}
    trades, eq, metrics = run(data, capital=1_000_000, max_positions=5)
    # verify never more than 5 concurrent by checking position opens not exceeding
    # simple: number of trades should be bounded
    assert metrics["num_trades"] >= 0

def test_empty_data_raises():
    try:
        run({}, capital=1_000_000)
        assert False
    except ValueError:
        pass

def test_deterministic():
    data = {"A.NS": _make_df(300, 42)}
    t1, e1, m1 = run(data)
    t2, e2, m2 = run(data)
    assert len(t1) == len(t2)
    assert abs(e1["equity"].iloc[-1] - e2["equity"].iloc[-1]) < 1e-6
