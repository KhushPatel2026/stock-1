"""Signal logic for the 6-rule strategy + per-strategy signals for paper trading."""
from __future__ import annotations
import pandas as pd


def is_entry(df: pd.DataFrame, idx: int, adx_thresh: float = 20) -> bool:
    """True if all three filters pass at idx."""
    if idx <= 0 or idx >= len(df):
        return False
    row = df.iloc[idx]
    prev = df.iloc[idx - 1]
    try:
        for col in ("close", "sma200", "sma20", "sma50", "adx"):
            if pd.isna(row[col]):
                return False
        if pd.isna(prev["sma20"]) or pd.isna(prev["sma50"]):
            return False
    except KeyError:
        return False

    trend = row["close"] > row["sma200"]
    crossover = row["sma20"] > row["sma50"] and prev["sma20"] <= prev["sma50"]
    regime = row["adx"] > adx_thresh
    return bool(trend and crossover and regime)


# ponytail: per-category signal fns instead of 50 bespoke ones.
# Each returns (signal, strength); signal ∈ {'long','short','flat'}, strength ∈ [0,1].
# Cross-sectional / always-invested strategies short-circuit to ('long', 0.3) at the
# signal level — the backtest handles ranking.

def _sig_trend_filter(df: pd.DataFrame) -> tuple[str, float]:
    """Long if close > SMA50 and SMA20 > SMA50; short the inverse."""
    if df.empty or len(df) < 50:
        return "flat", 0.0
    close = df["close"]
    sma20 = close.rolling(20).mean().iloc[-1]
    sma50 = close.rolling(50).mean().iloc[-1]
    last = float(close.iloc[-1])
    if pd.isna(sma20) or pd.isna(sma50) or sma50 == 0:
        return "flat", 0.0
    spread = float((sma20 - sma50) / sma50)
    if spread > 0 and last > sma50:
        return "long", min(1.0, abs(spread) * 50)
    if spread < 0 and last < sma50:
        return "short", min(1.0, abs(spread) * 50)
    return "flat", 0.0


def _sig_trend_breakout(df: pd.DataFrame) -> tuple[str, float]:
    """Long if close > 20-day high."""
    if df.empty or len(df) < 21:
        return "flat", 0.0
    high = df["high"].rolling(20).max().iloc[-2]
    last = float(df["close"].iloc[-1])
    if pd.isna(high) or high <= 0:
        return "flat", 0.0
    if last > high:
        return "long", min(1.0, (last - high) / high * 50)
    return "flat", 0.0


def _sig_mr_oversold(df: pd.DataFrame) -> tuple[str, float]:
    """Mean-reversion: z-score < -2 → long; > 2 → short."""
    if df.empty or len(df) < 25:
        return "flat", 0.0
    close = df["close"]
    sma = close.rolling(20).mean().iloc[-1]
    sd = close.rolling(20).std().iloc[-1]
    last = float(close.iloc[-1])
    if pd.isna(sma) or pd.isna(sd) or sd == 0:
        return "flat", 0.0
    z = (last - sma) / sd
    if z < -2:
        return "long", min(1.0, abs(float(z)) / 3)
    if z > 2:
        return "short", min(1.0, abs(float(z)) / 3)
    return "flat", 0.0


def _sig_mr_rsi(df: pd.DataFrame) -> tuple[str, float]:
    """RSI(2)-style: long <30, short >70."""
    if df.empty or len(df) < 10:
        return "flat", 0.0
    delta = df["close"].diff()
    up = delta.clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    rs = up / down.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    last = rsi.iloc[-1]
    if pd.isna(last):
        return "flat", 0.0
    if last < 30:
        return "long", min(1.0, (30 - last) / 30)
    if last > 70:
        return "short", min(1.0, (last - 70) / 30)
    return "flat", 0.0


def _sig_macd(df: pd.DataFrame) -> tuple[str, float]:
    if df.empty or len(df) < 35:
        return "flat", 0.0
    close = df["close"]
    m = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    s = m.ewm(span=9, adjust=False).mean()
    diff = m.iloc[-1] - s.iloc[-1]
    last = float(close.iloc[-1])
    if pd.isna(diff) or last == 0:
        return "flat", 0.0
    norm = abs(float(diff)) / last
    if diff > 0:
        return "long", min(1.0, norm * 100)
    if diff < 0:
        return "short", min(1.0, norm * 100)
    return "flat", 0.0


def _sig_obv_cross(df: pd.DataFrame) -> tuple[str, float]:
    if df.empty or len(df) < 30:
        return "flat", 0.0
    obv = (df["close"].diff().fillna(0) * df["volume"]).cumsum()
    sma = obv.rolling(20).mean()
    if len(obv) < 21 or pd.isna(sma.iloc[-1]) or pd.isna(obv.iloc[-1]):
        return "flat", 0.0
    if obv.iloc[-1] > sma.iloc[-1] and obv.iloc[-2] <= sma.iloc[-2]:
        return "long", 0.7
    if obv.iloc[-1] < sma.iloc[-1] and obv.iloc[-2] >= sma.iloc[-2]:
        return "short", 0.7
    return "flat", 0.0


def _sig_volume_spike(df: pd.DataFrame) -> tuple[str, float]:
    """Microstructure: vol spike + close near high → long."""
    if df.empty or len(df) < 25:
        return "flat", 0.0
    avg_vol = df["volume"].rolling(20).mean().iloc[-1]
    vol = float(df["volume"].iloc[-1])
    if pd.isna(avg_vol) or avg_vol == 0:
        return "flat", 0.0
    if vol > 1.5 * avg_vol:
        hi, lo, cl = float(df["high"].iloc[-1]), float(df["low"].iloc[-1]), float(df["close"].iloc[-1])
        rng = hi - lo
        if rng > 0 and (cl - lo) / rng > 0.7:
            return "long", min(1.0, vol / avg_vol / 3)
    return "flat", 0.0


def _sig_gap_fade(df: pd.DataFrame) -> tuple[str, float]:
    """Gap down > Nσ fades → long; gap up → short."""
    if df.empty or len(df) < 25:
        return "flat", 0.0
    gap = (df["open"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]
    sd = df["close"].pct_change().rolling(20).std().iloc[-1]
    if pd.isna(sd) or sd == 0:
        return "flat", 0.0
    z = gap / sd
    if z < -2:
        return "long", min(1.0, abs(float(z)) / 3)
    if z > 2:
        return "short", min(1.0, abs(float(z)) / 3)
    return "flat", 0.0


def _sig_always_long(df: pd.DataFrame) -> tuple[str, float]:
    return "long", 0.3


def _sig_always_flat(df: pd.DataFrame) -> tuple[str, float]:
    return "flat", 0.0


_STRATEGY_SIGNAL_FN: dict[str, "callable"] = {
    # MR
    "bollinger": _sig_mr_oversold,
    "rsi2": _sig_mr_rsi,
    "stochastic": _sig_mr_rsi,
    "williams_r": _sig_mr_rsi,
    "cci": _sig_mr_oversold,
    "mfi": _sig_mr_rsi,
    "keltner_mr": _sig_mr_oversold,
    "zscore_mr": _sig_mr_oversold,
    "ou_process": _sig_mr_oversold,
    "vwap_dev": _sig_mr_oversold,
    "gap_fade": _sig_gap_fade,
    # Trend
    "trend_following": _sig_trend_filter,
    "donchian": _sig_trend_breakout,
    "keltner_break": _sig_trend_breakout,
    "aroon": _sig_trend_filter,
    "macd": _sig_macd,
    "supertrend": _sig_trend_filter,
    "ichimoku": _sig_trend_filter,
    "hull_ma": _sig_trend_filter,
    "parabolic_sar": _sig_trend_filter,
    "breakout_volume": _sig_trend_breakout,
    # Pattern
    "engulfing": _sig_trend_filter,
    "hammer": _sig_trend_filter,
    "three_soldiers": _sig_trend_filter,
    "double_top": _sig_trend_breakout,
    # Volume
    "obv": _sig_obv_cross,
    "vpt": _sig_obv_cross,
    "ad_line": _sig_obv_cross,
    "microstructure": _sig_volume_spike,
    # Volatility
    "vol_breakout": _sig_trend_breakout,
    "vol_regime": _sig_trend_filter,
    "garch_lite": _sig_trend_filter,
    "vol_targeting": _sig_always_long,
    # Factor & cross-sect — rank handled by backtest; signal-level = always long
    "low_vol": _sig_always_long,
    "quality": _sig_always_long,
    "value": _sig_always_long,
    "size_factor": _sig_always_long,
    "high_52w": _sig_always_long,
    "magic_formula": _sig_always_long,
    "magic_formula_real": _sig_always_long,
    "factors": _sig_always_long,
    "ml_overlay": _sig_always_long,
    "dual_momentum": _sig_always_long,
    "sector_momentum": _sig_always_long,
    # Allocation / Carry / Hedge
    "risk_parity": _sig_always_long,
    "dividend_carry": _sig_always_long,
    "beta_hedge": _sig_always_long,
    # Event
    "earnings_drift": _sig_trend_filter,
    "rebalance_drift": _sig_trend_filter,
    # Options
    "covered_call": _sig_always_long,
    "covered_call_real": _sig_always_long,
    # Intraday (60m) — skip at daily signal level
    "intraday_orb": _sig_always_flat,
    "intraday_vwap": _sig_always_flat,
    "intraday_mom": _sig_always_flat,
    "overnight_drift": _sig_always_flat,
    # Pairs (pair-level signal, not single-name)
    "pairs_trading": _sig_always_flat,
}


def signal_for_strategy(strategy_id: str, df: pd.DataFrame) -> tuple[str, float]:
    """Public for testing. Per-strategy signal at the last bar of df."""
    fn = _STRATEGY_SIGNAL_FN.get(strategy_id, _sig_trend_filter)
    try:
        sig, strength = fn(df)
        return sig, max(0.0, min(1.0, float(strength)))
    except Exception:
        return "flat", 0.0


def compute_signals(tickers: list[str] | None = None, period: str = "3mo") -> dict:
    """Compute current long/flat/short signal for each (strategy, ticker) at the latest bar.

    Returns: {'as_of': 'YYYY-MM-DD', 'signals': [{strategy_id, ticker, signal, strength}, ...]}
    """
    from src.data import fetch_many
    from src.registry import list_strategies
    from src.universe import NIFTY15

    if tickers is None:
        tickers = NIFTY15

    data: dict[str, pd.DataFrame] = {}
    try:
        data = fetch_many(tickers, period=period) or {}
    except Exception:
        data = {}

    as_of = pd.Timestamp.now().strftime("%Y-%m-%d")
    if data:
        try:
            as_of = max(df.index[-1] for df in data.values() if df is not None and not df.empty).strftime("%Y-%m-%d")
        except Exception:
            pass

    try:
        strategy_ids = [s["id"] for s in list_strategies()]
    except Exception:
        strategy_ids = list(_STRATEGY_SIGNAL_FN.keys())

    signals: list[dict] = []
    for sid in strategy_ids:
        for t in tickers:
            df = data.get(t)
            if df is None or df.empty:
                continue
            sig, strength = signal_for_strategy(sid, df)
            signals.append({
                "strategy_id": sid,
                "ticker": t,
                "signal": sig,
                "strength": round(float(strength), 3),
            })

    return {"as_of": as_of, "signals": signals}
