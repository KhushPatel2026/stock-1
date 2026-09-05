"""Risk sizing and ATR-based exit levels."""
import math


def levels(entry: float, atr: float, sl_mult: float = 2.5, tp_mult: float = 4.0) -> tuple[float, float]:
    if entry <= 0 or atr <= 0:
        raise ValueError("entry and atr must be >0")
    return entry - sl_mult * atr, entry + tp_mult * atr


def position_size(capital: float, entry: float, stop: float, risk_pct: float = 0.01) -> int:
    if capital <= 0 or entry <= 0 or risk_pct <= 0:
        return 0
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return 0
    risk_amount = capital * risk_pct
    return math.floor(risk_amount / risk_per_share)
