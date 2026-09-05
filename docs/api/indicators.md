# API: Indicators

Status: Draft | Version: v0.1.0 | Last Updated: 2026-08-27

## Overview
Purpose: Compute SMA, ATR, ADX using Wilder's RMA where applicable.
Owns: Correct warmup handling (NaN until enough bars), no external calls.
Does NOT: Fetch data, generate signals, manage state.

## Dependencies
| Module | Direction | Purpose |
|---|---|---|
| pandas, numpy | uses | rolling / RMA |

## Data Model
Input: DataFrame with columns open/high/low/close/volume (float), Date index sorted asc.
Output: Series aligned to input index, float, NaN for warmup.

## Endpoints / Methods

### `sma(series: Series, window: int) -> Series`
**Input:** series float, window int >1
**Output:** Series, NaN for first window-1 rows
**Errors:** ValueError if window<2 or len<window
**Example:** sma(close, 20)[19] == mean(close[0:20])

### `atr(df: DataFrame, window: int=14) -> Series`
Wilder's RMA on True Range. TR = max(high-low, abs(high-close_prev), abs(low-close_prev)).
Seed: mean TR of first window bars, then RMA = (prev* (window-1) + TR)/window
**Errors:** ValueError if missing columns
**Example:** atr(df,14).iloc[13] == mean TR 0:14

### `adx(df: DataFrame, window: int=14) -> Series`
Wilder ADX: +DM, -DM, TR → smoothed → +DI, -DI → DX → ADX (RMA of DX). Returns 0-100.
Warmup ~ 2*window bars NaN, then valid.
**Errors:** ValueError if missing columns

## Security / Performance
No auth. p50 <50ms for 5k bars. Pure pandas/numpy, no I/O.

## Verification
Unit tests compare manual calc on 30-bar fixture. Tolerance 1e-6.
