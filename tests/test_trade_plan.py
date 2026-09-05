import pandas as pd
import numpy as np
from src.trade_plan import build_plan


def _df(n=300, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(rng.normal(0.1, 1.0, n)) + 200
    open_ = close + rng.normal(0, 0.5, n)
    high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.8, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.8, n))
    return pd.DataFrame(
        {"close": close, "open": open_, "high": high, "low": low,
         "volume": rng.integers(500_000, 2_000_000, n)}, index=idx)


def test_buy_plan_numbers():
    df = _df()
    p = build_plan("RELIANCE.NS", df, "BUY", 72.5,
                   [("donchian", 1.2), ("supertrend", 0.8)], [("rsi2", 0.2)],
                   {"donchian": "Trend", "supertrend": "Trend", "rsi2": "MR"},
                   {"donchian": "Donchian", "supertrend": "Supertrend", "rsi2": "RSI2"})
    assert p["decision"] == "BUY"
    assert p["stop_loss"] < p["entry"] < p["target"]
    assert p["stop_pct"] < 0 < p["target_pct"]
    assert 1.5 < p["risk_reward"] < 1.7  # 4x ATR / 2.5x ATR
    assert p["timeframe"] == "Swing"
    assert "RELIANCE.NS" in p["insight"] and "Donchian" in p["insight"]
    assert p["above_sma200"] in (True, False)
    assert p["as_of"] == str(df.index[-1].date())


def test_sell_plan_mirrored():
    df = _df()
    p = build_plan("TCS.NS", df, "SELL", 60.0,
                   [("bollinger", 0.4)], [("macd", 1.0), ("donchian", 0.9)],
                   {"bollinger": "MR", "macd": "Trend", "donchian": "Trend"})
    assert p["target"] < p["entry"] < p["stop_loss"]
    assert p["target_pct"] < 0 < p["stop_pct"]
    assert 1.5 < p["risk_reward"] < 1.7


def test_hold_plan_band_and_short_history():
    df = _df(n=30)  # no SMA200, thin ATR — must not raise
    p = build_plan("INFY.NS", df, "HOLD", 40.0, [("a", 0.3)], [("b", 0.3)], {}, {})
    assert p["stop_loss"] < p["entry"] < p["target"]
    assert p["above_sma200"] is None
    assert "wait" in p["insight"].lower()


def test_intraday_timeframe():
    df = _df()
    p = build_plan("T.NS", df, "BUY", 55.0, [("intraday_orb", 1.0)], [],
                   {"intraday_orb": "Intraday"})
    assert p["timeframe"] == "Intraday"
    assert "3:20" in p["timeframe_detail"]
