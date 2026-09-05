# PRD — FEAT-002: Statistical Arbitrage / Pairs Trading

Status: Draft | Date: 2026-08-27 | Feature: FEAT-002 | Branch: feat/FEAT-002-pairs-trading

## 1. Objectives & Success

Build a market-neutral pairs trading system for Nifty50 that is genuinely complementary to FEAT-001 (momentum) — mean-reversion on the spread of cointegrated same-sector pairs.

| Metric | Target |
|---|---|
| Finds cointegrated pairs via Engle-Granger on Nifty50 | ≥1 pair with p<0.05 on 2y history |
| Backtest runs end-to-end, dollar-neutral, with realistic Indian costs | completes |
| Produces metrics (CAGR, Sharpe, maxDD, win rate, exposure) | non-zero trades on synthetic with known spread |
| Rolling re-validation detects broken pairs | flag when p>0.10 |

## 2. User Role

Same quant/developer CLI — no auth, no UI.

## 3. Module Breakdown

| Module | Owns | Reuses | Does NOT |
|---|---|---|---|
| `src/pairs.py` | Cointegration scan (Engle-Granger), same-sector candidates | `universe.py` sector map | Johansen (post-MVP) |
| `src/spread.py` | Rolling beta (OLS), spread, z-score | pandas/numpy | Intraday |
| `src/pair_signals.py` | Entry z>±2, exit z→0, stop ±3.5 | `spread.py` | Short-only standalone |
| `src/pair_portfolio.py` | Dollar-neutral pair backtest, Indian costs, rolling re-test | `metrics.py`, `data.py` | Live trading |
| `src/pair_backtest.py` | CLI | `data.py` | Dashboard |

Ponytail check: No abstract PairStrategy base, no multi-method cointegration framework — one Engle-Granger path. Johansen, half-life, Kalman post-MVP.

## 4. Data Model

**Pair:** `(leg1, leg2, beta, pvalue, sector)`
**Spread row:** `date, leg1_close, leg2_close, beta, spread (= leg1 - beta*leg2), zscore`

**Position:** two legs: long loser / short winner, equal dollar notional. `entry_z, exit_z, exit_reason (mean/stop/break)`

## 5. API Contracts (summary — full in docs/api/pairs.md)

- `pairs.find_cointegrated(data, p_thresh=0.05, min_corr=0.7) -> list[(t1,t2,beta,pval)]`
- `spread.rolling_beta(s1, s2, window=60) -> Series beta`
- `spread.zscore(spread_series, window=60) -> Series z`
- `pair_signals.signal(z, entry=2.0, exit=0.3, stop=3.5) -> {0:flat, 1:long_spread, -1:short_spread}`
- `pair_portfolio.run_pair(data, pair, capital=1e6, costs=...) -> (trades, equity, metrics)`

Costs: brokerage 0.03% per leg, STT 0.025% sell, slippage 5bps — modeled per fill.

## 6. Test Strategy

- Unit: synthetic cointegrated pair (y = 2x + noise) → p<0.05; non-cointegrated random walk → p>0.2
- Spread: rolling beta ≈2, zscore on known widening → triggers entry
- Integration: pair backtest on synthetic mean-reverting spread → trades>0, dollar-neutral
- E2E: scan Nifty15 for 1y → at least attempts, backtest top pair completes

## 7. MVP vs Post-MVP

**MVP:** Engle-Granger only, z 2/0/3.5, dollar-neutral, Indian costs, top-1 pair backtest, rolling re-test quarterly (same coint test)
**Post-MVP:** Johansen, half-life sizing, multiple pairs portfolio, walk-forward 2018/2020/2022 regimes, full cost sensitivity

## 8. Non-Goals

- No HFT, no colocation, no FPGA — realistic retail stat-arb
- No Johansen/copula, no intraday, no cross-sector pairs for MVP

## 9. Existing Code to Reuse

`universe.py` (sector grouping), `data.py` (fetch), `metrics.py` (CAGR/Sharpe/maxDD) — extends to pair equity (market-neutral returns). No duplication.

## 10. Sub-Issues

SUB-002-01 discovery, SUB-002-02 spread, SUB-002-03 execution, SUB-002-04 backtest+costs
