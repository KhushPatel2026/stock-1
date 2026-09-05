# API: Portfolio & Backtest

Status: Draft | Version: v0.1.0 | Last Updated: 2026-08-27

## Overview
Purpose: Run long-only daily backtest across Nifty50 universe.
Owns: Position lifecycle, max 5 concurrency, equity curve, trade log.
Does NOT: Data fetch, indicator calc, signal logic (calls them).

## Dependencies
| Module | Direction | Purpose |
|---|---|---|
| signals, sizing, indicators | uses | entry + sizing + exits |
| data | uses | OHLCV dict |

## Data Model
### Input
`data: dict[str, DataFrame]` — each DF has OHLCV + indicators precomputed, date index.
`capital: float` — starting capital
`max_positions: int =5`

### Output
- `trades: list[dict]` with ticker, entry_date/price, exit_date/price, exit_reason (SL/TP/signal_end), shares, pnl, return_pct
- `equity: DataFrame` with date, equity, drawdown
- `metrics: dict` with CAGR, sharpe, maxDD, win_rate, num_trades, exposure

## Methods

### `run(data, capital=1_000_000, max_positions=5) -> (trades, equity)`
Loop dates sorted. For each date:
1. Check exits first (low <= stop → SL, high >= tp → TP; if both same bar, SL priority — conservative)
2. Then entries: iterate tickers, if `is_entry(df, idx)` and positions<len(max) and not already held, compute sizing, enter at close (or next open if available — MVP: same close for simplicity, ponytail: one price).
3. Update equity = capital + unrealized PnL.

### `compute_metrics(trades, equity) -> dict`
CAGR = (final/initial)^(252/n_days)-1, Sharpe = mean(daily_ret)/std(daily_ret)*sqrt(252), maxDD from equity peak, win_rate = wins/trades.

## Errors
ValueError if data empty. Warn if no trades.

## Performance
1000 days × 15 tickers <2s.
