"""Signal logic for the 6-rule strategy."""
import pandas as pd


def is_entry(df: pd.DataFrame, idx: int, adx_thresh: float = 20) -> bool:
    """True if all three filters pass at idx."""
    if idx <= 0 or idx >= len(df):
        return False
    row = df.iloc[idx]
    prev = df.iloc[idx - 1]
    try:
        # require all needed fields present and not NaN
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
