# PRD — FEAT-001: Trend-Following with Volatility-Adjusted Risk (Nifty 50)

Status: Draft | Date: 2026-08-27 | Author: orchestrator
Feature: FEAT-001 | Branch: feat/FEAT-001-trend-volatility-risk

## 1. Objectives & Success Metrics

Build a long-only systematic backtesting system for Nifty 50 large-caps implementing the 6-rule professional trend strategy. Must run on real data and produce verifiable performance reports.

| Metric | Target | How measured |
|---|---|---|
| Runs end-to-end on 2018-2026 Nifty50 data without crash | Pass | `python -m src.backtest` completes |
| Strategy logic matches 6 rules exactly | Pass | Unit tests for each rule |
| Backtest shows realistic metrics (CAGR, Sharpe, maxDD, win rate, trades) | Pass | Metrics computed, non-zero trades on long history |
| Reproducible | Pass | Same seed/data → same equity curve |

## 2. User Roles

Single role: **Quant / Developer** running backtests locally. No auth, no multi-user. CLI only for MVP.

## 3. Module Breakdown

| Module | Owns | Does NOT |
|---|---|---|
| `src/universe.py` | Nifty50 ticker list (static) | Live index constituent changes |
| `src/data.py` | yfinance fetch, caching, OHLCV DataFrame | Intraday, other providers |
| `src/indicators.py` | SMA20/50/200, ATR (Wilder), ADX (Wilder) | Other indicators |
| `src/signals.py` | Trend filter, MA crossover, ADX>20 | Short signals |
| `src/sizing.py` | 1% risk sizing, ATR SL/TP levels | Leverage, shorts |
| `src/portfolio.py` | Portfolio loop, max 5 positions, equity curve | Intraday, slippage model beyond 1 bar |
| `src/metrics.py` | CAGR, Sharpe, maxDD, win rate, exposure | Transaction cost modeling (post-MVP) |
| `src/backtest.py` | CLI orchestrator | Live trading |

Ponytail check: No abstract Strategy class with one impl, no plugin system, no config service. Straight functions. Add abstraction only when second strategy exists.

## 4. Data Model

### OHLCV DataFrame (per ticker, indexed by Date)
| Field | Type | Constraints |
|---|---|---|
| open, high, low, close | float >0 | required |
| volume | int >=0 | required |
| sma20, sma50, sma200 | float | nullable until warmup (200 bars) |
| atr | float >0 | nullable until warmup (14 bars) |
| adx | float 0-100 | nullable until warmup (~28 bars) |
| signal | bool | entry trigger after filters |

### Position
| Field | Type | Constraints |
|---|---|---|
| ticker | str | Nifty50 member |
| entry_date, entry_price | date, float |  |
| shares | int >0 | sized by risk |
| stop, take_profit | float | entry ± ATR multiple |
| exit_date, exit_price, exit_reason | date, float, str | nullable |

### Trade → superset of Position with `pnl`, `return_pct`

## 5. API Contracts (summary — full in docs/api/*.md)

- `indicators.sma(series, window)` → Series
- `indicators.atr(df, window=14)` → Series (Wilder RMA)
- `indicators.adx(df, window=14)` → Series (Wilder RMA)
- `signals.is_entry(df, idx)` → bool : close>sma200 && sma20>sma50 && sma20_prev<=sma50_prev && adx>20
- `sizing.position_size(capital, entry, stop, risk_pct=0.01)` → shares:int
- `sizing.levels(entry, atr, sl_mult=2.5, tp_mult=4.0)` → (stop, tp)
- `portfolio.run(data: dict[ticker→df], capital=1_000_000)` → (trades, equity_curve)

Errors: ValueError on insufficient data / invalid inputs. No silent NaN propagation.

## 6. Test Strategy

- Unit: indicators vs manual calc, signals edge cases, sizing math, SL/TP
- Integration: data fetch mocked, 2-ticker portfolio run, max 5 enforcement
- E2E: 2-year backtest on 5 tickers, assert trades>0, equity curve monotonic-ish, metrics computed
- Determinism: same input → same output

## 7. MVP vs Post-MVP

**MVP (must ship):**
- Static Nifty50 list (~15 tickers representative if 50 too slow for CI), yfinance fetch+cache
- Indicators (SMA, ATR, ADX) — correct Wilder implementation
- Signal logic (all 3 filters)
- Risk sizing + ATR exits
- Backtest loop (daily, next-bar execution, long-only, max 5)
- Metrics + CLI print

**Post-MVP:**
- Full 50-ticker walk-forward across 2018/2020/2022 regimes
- Transaction costs, slippage, dividends
- Live paper trading, dashboard/UI
- Optimisation / parameter search

## 8. Non-Goals

- No shorts, no intraday, no options
- No UI for MVP
- No external DB, no user management
- No proprietary data provider

## 9. Existing Code to Reuse

None in stock-1 (greenfield). Adjacent Algo-trading project has yfinance patterns but not imported — copy minimal pattern if useful, don't depend.

## 10. Sub-Issue Breakdown

- SUB-001-01 Data & Universe
- SUB-001-02 Indicator Engine
- SUB-001-03 Signal & Entry Logic
- SUB-001-04 Risk, Sizing & Exits
- SUB-001-05 Backtest Engine & Evaluation

Confirmed: user strategy description is the spec. No further interview needed for this mechanical system.
