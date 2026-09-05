# API: Signals & Sizing

Status: Draft | Version: v0.1.0 | Last Updated: 2026-08-27

## Overview
Purpose: Entry filter + position sizing + exit levels for the 6-rule strategy.
Owns: Pure functions, no state, no I/O.
Does NOT: Run backtest loop, fetch data.

## Methods

### `is_entry(df: DataFrame, idx: int, adx_thresh: float=20) -> bool`
Checks at row idx (requires idx>=1):
- close[idx] > sma200[idx]
- sma20[idx] > sma50[idx] AND sma20[idx-1] <= sma50[idx-1]  (crossover)
- adx[idx] > adx_thresh
All referenced values must be non-NaN else False.
**Errors:** IndexError if idx out of range → return False (not throw)

### `levels(entry: float, atr: float, sl_mult: float=2.5, tp_mult: float=4.0) -> (float, float)`
Returns (stop=entry - sl_mult*atr, take=entry + tp_mult*atr)
**Errors:** ValueError if atr<=0 or entry<=0

### `position_size(capital: float, entry: float, stop: float, risk_pct: float=0.01) -> int`
risk_amount = capital * risk_pct
risk_per_share = entry - stop (>0)
shares = floor(risk_amount / risk_per_share)
Returns 0 if risk_per_share<=0 or capital<=0.
No partial shares (int).

## Example
```python
stop, tp = levels(100, 2)  # (95.0, 108.0)
shares = position_size(1_000_000, 100, 95, 0.01)  # 2000
is_entry(df, 250)  # True/False
```
