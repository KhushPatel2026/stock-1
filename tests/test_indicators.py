import pandas as pd
import numpy as np
from src.indicators import sma, atr, adx

def test_sma():
    s = pd.Series([1,2,3,4,5], dtype=float)
    assert sma(s, 3).iloc[2] == 2.0
    assert pd.isna(sma(s, 3).iloc[0])
    assert sma(s, 3).iloc[4] == 4.0

def test_atr_wilder():
    # manual 5-bar
    df = pd.DataFrame({
        "high": [10,11,12,13,14],
        "low": [9,9,10,11,12],
        "close": [9.5,10.5,11.5,12.5,13.5],
    })
    # TR: 1, 2, 2, 2, 2  (high-low dominates after first bar)
    # ATR3 seed = mean first 3 TR = (1+2+2)/3=1.666...
    # next = (1.666*2+2)/3=1.777..., next=(1.777*2+2)/3=1.8518
    result = atr(df, 3)
    assert abs(result.iloc[2] - 1.666666) < 1e-4
    assert abs(result.iloc[4] - 1.8518) < 1e-4

def test_adx_range():
    # trending up should give high ADX
    n=60
    df = pd.DataFrame({
        "high": np.arange(n, dtype=float)+1,
        "low": np.arange(n, dtype=float),
        "close": np.arange(n, dtype=float)+0.5,
    })
    result = adx(df, 14)
    # last value should be defined and 0-100
    assert not pd.isna(result.iloc[-1])
    assert 0 <= result.iloc[-1] <= 100

def test_adx_flat_low():
    n=60
    df = pd.DataFrame({
        "high": [10]*n,
        "low": [9]*n,
        "close": [9.5]*n,
    })
    result = adx(df, 14)
    # flat market ADX near 0
    assert result.iloc[-1] < 20
