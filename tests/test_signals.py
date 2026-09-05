import pandas as pd
from src.signals import is_entry

def _df(rows):
    return pd.DataFrame(rows)

def test_entry_true():
    df = _df([
        {"close": 100, "sma200": 90, "sma20": 95, "sma50": 96, "adx": 25},
        {"close": 101, "sma200": 90, "sma20": 97, "sma50": 96, "adx": 25},
    ])
    assert is_entry(df, 1) is True

def test_entry_fails_trend():
    df = _df([
        {"close": 80, "sma200": 90, "sma20": 95, "sma50": 96, "adx": 25},
        {"close": 80, "sma200": 90, "sma20": 97, "sma50": 96, "adx": 25},
    ])
    assert is_entry(df, 1) is False

def test_entry_fails_crossover():
    df = _df([
        {"close": 100, "sma200": 90, "sma20": 97, "sma50": 96, "adx": 25},
        {"close": 101, "sma200": 90, "sma20": 98, "sma50": 96, "adx": 25},
    ])
    # no crossover (already above)
    assert is_entry(df, 1) is False

def test_entry_fails_adx():
    df = _df([
        {"close": 100, "sma200": 90, "sma20": 95, "sma50": 96, "adx": 10},
        {"close": 101, "sma200": 90, "sma20": 97, "sma50": 96, "adx": 10},
    ])
    assert is_entry(df, 1) is False

def test_entry_nan_false():
    df = _df([
        {"close": 100, "sma200": 90, "sma20": 95, "sma50": 96, "adx": 25},
        {"close": 101, "sma200": float("nan"), "sma20": 97, "sma50": 96, "adx": 25},
    ])
    assert is_entry(df, 1) is False
