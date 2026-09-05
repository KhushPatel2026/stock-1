from src.sizing import levels, position_size
import pytest

def test_levels():
    sl, tp = levels(100, 2, 2.5, 4.0)
    assert sl == 95
    assert tp == 108

def test_levels_invalid():
    try:
        levels(100, 0)
        assert False
    except ValueError:
        pass

def test_position_size():
    assert position_size(1_000_000, 100, 95, 0.01) == 2000
    assert position_size(100_000, 100, 95, 0.01) == 200
    assert position_size(0, 100, 95, 0.01) == 0
    assert position_size(1_000_000, 100, 100, 0.01) == 0
    assert position_size(1_000_000, 100, 105, 0.01) == 0
