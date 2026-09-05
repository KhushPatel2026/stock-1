# API: Pairs Trading

Status: Draft | Version: v0.2.0 | Last Updated: 2026-08-27

## Overview
Purpose: Market-neutral pairs trading — cointegration scan, spread/zscore, dollar-neutral execution.
Owns: Pure functions, no I/O except data dict input.
Does NOT: Fetch data, manage live orders.

## Dependencies
| Module | Direction | Purpose |
|---|---|---|
| statsmodels.tsa.stattools.coint | uses | Engle-Granger |
| numpy, pandas | uses | OLS, rolling |

## Methods

### `find_cointegrated(data: dict[ticker→df], p_thresh=0.05, min_corr=0.7, lookback=252) -> list[Pair]`
- Candidates: same-sector pairs (sector map in universe.py). For MVP, if sector map incomplete, use all pairs but filter by correlation first (fast).
- For each pair, take last `lookback` closes, require corr>=min_corr, then `coint(s1, s2)` → pvalue. Return sorted by pvalue.
- **Errors:** ValueError if data <2 tickers.
- **Example:** finds HDFC/ICICI with p~0.02

### `rolling_beta(s1: Series, s2: Series, window=60) -> Series`
Rolling OLS beta: `s1 ~ beta*s2 + alpha` (with intercept). NaN for first window-1.
Implemented via `np.polyfit` or closed form `cov/var`.
**Output:** Series aligned to s1 index.

### `spread_and_zscore(s1, s2, beta: Series, window=60) -> (Series spread, Series z)`
`spread = s1 - beta*s2`, `z = (spread - rolling_mean)/rolling_std`. Std floor 1e-8.

### `pair_signal(z: float, position: int, entry=2.0, exit=0.3, stop=3.5) -> int`
- If flat (0): return 1 if z<-entry (long spread), -1 if z>+entry (short spread), else 0.
- If long (1): exit to 0 if z>-exit or z<-stop
- If short (-1): exit to 0 if z<exit or z>stop
Exit reason derived from which threshold hit.

### `run_pair(data, pair=(t1,t2), capital=1e6, entry=2.0, exit=0.3, stop=3.5, beta_window=60, z_window=60, cogs_bps=8) -> (trades, equity, metrics)`
Dollar-neutral: notional = capital * 0.1 per pair (or 10% — fixed fraction, ponytail: no Kelly). Shares: long_n = notional/price_long, short_n = notional/price_short.
Costs: `cost = notional * (brokerage+slippage)*2 + STT on sell leg`.
Equity: market-neutral PnL (spread convergence), not directional.

## Sector Map
Added to `universe.py`: SECTORS dict grouping Nifty50 into Banks, IT, Auto, Pharma, etc. Used to prune candidates from ~1225 to ~150 pairs.

## Performance
Scan 15 tickers (105 pairs) <2s; 50 tickers (1225 pairs) <8s on 1y data.

## Security
No auth, no PII.
