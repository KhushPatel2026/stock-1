"""Pair signals — entry ±2, exit →0, stop ±3.5"""
def signal(z: float, position: int, entry: float = 2.0, exit: float = 0.3, stop: float = 3.5) -> tuple[int, str]:
    """Returns (new_position, reason). Position: 0 flat, 1 long spread, -1 short spread."""
    import math
    if math.isnan(z):
        return position, "hold"
    if position == 0:
        if z < -entry:
            return 1, "long_spread"
        if z > entry:
            return -1, "short_spread"
        return 0, "hold"
    if position == 1:
        if z > -exit:
            return 0, "mean_revert"
        if z < -stop:
            return 0, "stop"
        return 1, "hold"
    if position == -1:
        if z < exit:
            return 0, "mean_revert"
        if z > stop:
            return 0, "stop"
        return -1, "hold"
    return 0, "hold"
