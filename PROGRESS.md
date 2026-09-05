# Project Progress

## Project
Name: stock-1 — Nifty 50 Trend-Following Systematic Strategy
Repo: stock-1 (local, not yet pushed to standalone remote — parent is Khush/Softwares)
Tech Stack: Python 3.11+, pandas, numpy, yfinance, pytest
Started: 2026-08-27
Current Version: v0.4.0 (FEAT-001+002+003+004 MVP — RELEASED)
Repo: https://github.com/KhushPatel2026/stock-1

## Milestones
| Milestone | Description | Target Date | Status |
|---|---|---|---|
| MVP | Working backtest: data→indicators→signals→risk sizing→portfolio→metrics on real Nifty50 data | 2026-09-10 | In Progress |
| v1.0.0 | Walk-forward + regime tests (2018/2020/2022), transaction costs, paper-trading ready | 2026-09-20 | Planned |
| Backlog | Live trading adapter, dashboard, multi-timeframe | — | Open |

## Active Work
| ID | Type | Name | Parent | Phase | Branch | GH Issue |
|---|---|---|---|---|---|---|
| FEAT-001 | feature | Trend-Following with Volatility-Adjusted Risk (Nifty50) | — | P7 ✅ | feat/FEAT-001-trend-volatility-risk | — |
| FEAT-002 | feature | Stat-Arb / Pairs Trading (Market-Neutral) | — | P7 ✅ | feat/FEAT-002-pairs-trading | — |
| FEAT-003 | feature | Institutional Suite (Factors, Options Vol, Event-Driven, Risk Overlay, Walk-Forward) | — | P7 ✅ | feat/FEAT-003-institutional-suite | — |
| FEAT-004 | feature | Advanced Quant (Gap-Fade, Sector-Neutral Momentum, Microstructure, Beta-Hedge, ML Overlay) | — | P7 ✅ | feat/FEAT-004-advanced-quant | — |
| SUB-004-01 | sub-issue | Gap-Fade Mean-Reversion (Index/Nifty gap >2σ) | FEAT-004 | P7 ✅ | feat/SUB-004-01-gap-fade | — |
| SUB-004-02 | sub-issue | Sector-Neutral Cross-Sectional Momentum | FEAT-004 | P7 ✅ | feat/SUB-004-02-sector-neutral | — |
| SUB-004-03 | sub-issue | Microstructure (Volume Spike + Price Acceleration) | FEAT-004 | P7 ✅ | feat/SUB-004-03-microstructure | — |
| SUB-004-04 | sub-issue | Beta-Hedged Single-Stock (Nifty futures hedge) | FEAT-004 | P7 ✅ | feat/SUB-004-04-beta-hedge | — |
| SUB-004-05 | sub-issue | ML Overlay (GBM Combining Factors) | FEAT-004 | P7 ✅ | feat/SUB-004-05-ml-overlay | — |

## Phase Gate
| Phase | Name | Status |
|---|---|---|
| P0 | Orient | ✅ |
| P1 | Spec & Clarify | ✅ (FEAT-001/002/003/004 PRDs) |
| P2 | Plan & Task Breakdown | ✅ |
| P3 | API & Interface Design | ✅ (indicators, signals, portfolio, pairs, institutional, advanced-quant) |
| P4 | Build — TDD Loop | ✅ (38 tests pass — 16+7+7+8) |
| P5 | Verify | ✅ |
| P6 | Multi-Agent Review | ✅ (ponytail + logic review, all FEATs) |
| P7 | QA — All Test Types | ✅ — FEAT-001 PASS, FEAT-002 PASS, FEAT-003 PASS, FEAT-004 PASS |
| P8 | PR → dev | ✅ (dev branch pushed) |
| P9 | PR → staging | ✅ (staging branch pushed) |
| P10 | PR → main + Release | ✅ (tagged v0.4.0 on main, release notes in docs/releases/v0.4.0.md) |
| P11 | Docs & ADRs | ✅ (ADR-001/002/003/004, READMEs, CHANGELOG v0.4.0) |
| P12 | Ship & Observability | ✅ (runbook in docs/runbooks/strategies.md, release notes in docs/releases/v0.4.0.md) |

## Feature Registry
| FEAT-ID | Name | Status | SUBs | GH Issue | Version |
|---|---|---|---|---|---|
| FEAT-001 | Trend-Following with Volatility-Adjusted Risk | Done (P7) — awaiting release | 5 | — | v0.1.0 |
| FEAT-002 | Statistical Arbitrage / Pairs Trading (Market-Neutral, Cointegration) | Done (P7) — awaiting release | 4 | — | v0.2.0 |
| FEAT-003 | Institutional Suite (Factors/Options/Event/Risk/Walk-Forward) | Done (P7) — awaiting release | 5 | — | v0.3.0 |
| FEAT-004 | Advanced Quant (Gap-Fade/Sector-Neutral/Microstructure/Beta-Hedge/ML) | Done (P7) — awaiting release | 5 | — | v0.4.0 |

## Sub-Issue Registry
| SUB-ID | Parent FEAT | Name | Phase | Branch | GH Issue | Status |
|---|---|---|---|---|---|---|
| SUB-001-01 | FEAT-001 | Data & Universe | P7 ✅ | feat/SUB-001-01-data-universe | — | Done |
| SUB-001-02 | FEAT-001 | Indicator Engine | P7 ✅ | feat/SUB-001-02-indicators | — | Done |
| SUB-001-03 | FEAT-001 | Signal & Entry Logic | P7 ✅ | feat/SUB-001-03-signals | — | Done |
| SUB-001-04 | FEAT-001 | Risk, Sizing & Exits | P7 ✅ | feat/SUB-001-04-risk-sizing | — | Done |
| SUB-001-05 | FEAT-001 | Backtest Engine & Evaluation | P7 ✅ | feat/SUB-001-05-backtest-eval | — | Done |
| SUB-002-01 | FEAT-002 | Pair Discovery (Cointegration Scan) | P7 ✅ | feat/SUB-002-01-pair-discovery | — | Done |
| SUB-002-02 | FEAT-002 | Spread & Z-Score Engine | P7 ✅ | feat/SUB-002-02-spread-zscore | — | Done |
| SUB-002-03 | FEAT-002 | Pair Execution (Entry/Exit, Dollar-Neutral Sizing) | P7 ✅ | feat/SUB-002-03-pair-execution | — | Done |
| SUB-002-04 | FEAT-002 | Pair Backtest + Indian Costs + Validation | P7 ✅ | feat/SUB-002-04-pair-backtest | — | Done |
| SUB-003-01 | FEAT-003 | Multi-Factor Equity Model | P7 ✅ | feat/SUB-003-01-factors | — | Done |
| SUB-003-02 | FEAT-003 | Volatility / Options Premium | P7 ✅ | feat/SUB-003-02-options-vol | — | Done |
| SUB-003-03 | FEAT-003 | Event-Driven | P7 ✅ | feat/SUB-003-03-events | — | Done |
| SUB-003-04 | FEAT-003 | Portfolio Risk Overlay | P7 ✅ | feat/SUB-003-04-risk-overlay | — | Done |
| SUB-003-05 | FEAT-003 | Walk-Forward Optimization | P7 ✅ | feat/SUB-003-05-walk-forward | — | Done |
| SUB-004-01 | FEAT-004 | Gap-Fade Mean-Reversion | P7 ✅ | feat/SUB-004-01-gap-fade | — | Done |
| SUB-004-02 | FEAT-004 | Sector-Neutral Momentum | P7 ✅ | feat/SUB-004-02-sector-neutral | — | Done |
| SUB-004-03 | FEAT-004 | Microstructure Signals | P7 ✅ | feat/SUB-004-03-microstructure | — | Done |
| SUB-004-04 | FEAT-004 | Beta-Hedged Single Stock | P7 ✅ | feat/SUB-004-04-beta-hedge | — | Done |
| SUB-004-05 | FEAT-004 | ML Overlay | P7 ✅ | feat/SUB-004-05-ml-overlay | — | Done |

## Task Registry
| TASK-ID | Parent | Description | Size | MVP? | GH Issue | Status |
|---|---|---|---|---|---|---|
| SUB-001-01-T01 | SUB-001-01 | Nifty50 universe list + yfinance fetch with caching | M | MVP | — | Done |
| SUB-001-02-T01 | SUB-001-02 | SMA20/50/200 calculation | S | MVP | — | Done |
| SUB-001-02-T02 | SUB-001-02 | ATR calculation | S | MVP | — | Done |
| SUB-001-02-T03 | SUB-001-02 | ADX (Wilder) calculation | M | MVP | — | Done |
| SUB-001-03-T01 | SUB-001-03 | Trend filter (close>SMA200) + entry trigger (SMA20>SMA50 crossover) + ADX>20 | M | MVP | — | Done |
| SUB-001-04-T01 | SUB-001-04 | 1% risk position sizing (vol-adjusted) | M | MVP | — | Done |
| SUB-001-04-T02 | SUB-001-04 | ATR-based SL (2.5×) & TP (4×), max 5 positions | S | MVP | — | Done |
| SUB-001-05-T01 | SUB-001-05 | Portfolio loop + backtest runner (long-only, next-bar execution) | M | MVP | — | Done |
| SUB-001-05-T02 | SUB-001-05 | Metrics: CAGR, Sharpe, maxDD, win rate, exposure | S | MVP | — | Done |
| SUB-001-05-T03 | SUB-001-05 | CLI + report (walk-forward ready) | S | MVP | — | Done |
| SUB-002-01-T01 | SUB-002-01 | Cointegration scan (Engle-Granger) across Nifty50 same-sector pairs | M | MVP | — | Done |
| SUB-002-02-T01 | SUB-002-02 | Rolling beta + spread + z-score (window 60, entry ±2) | M | MVP | — | Done |
| SUB-002-03-T01 | SUB-002-03 | Dollar-neutral sizing, entry/exit (z→0), stop at ±3.5 | M | MVP | — | Done |
| SUB-002-04-T01 | SUB-002-04 | Pair backtest loop with Indian costs (brokerage+STT+slippage) + rolling re-validation | M | MVP | — | Done |
| SUB-002-04-T02 | SUB-002-04 | Metrics + CLI for pairs | S | MVP | — | Done |
| SUB-003-01-T01 | SUB-003-01 | Factor ranking (momentum 12M, value P/E proxy, quality ROE proxy, low-vol) + top-decile monthly rebalance | M | MVP | — | Done |
| SUB-003-02-T01 | SUB-003-02 | Black-Scholes covered call (5% OTM, 30d) + harvest premium | M | MVP | — | Done |
| SUB-003-03-T01 | SUB-003-03 | Event windows (earnings ±5d, index rebalance ±10d) + drift backtest | M | MVP | — | Done |
| SUB-003-04-T01 | SUB-003-04 | Risk overlay (10% maxDD kill-switch, vol targeting, correlation monitor) | M | MVP | — | Done |
| SUB-003-05-T01 | SUB-003-05 | Walk-forward engine (train/test rolling, param grid, OOS metrics) | M | MVP | — | Done |
| SUB-004-01-T01 | SUB-004-01 | Gap-fade (gap>2σ, intraday mean-reversion) | M | MVP | — | Done |
| SUB-004-02-T01 | SUB-004-02 | Sector-neutral momentum (within-sector rank) | M | MVP | — | Done |
| SUB-004-03-T01 | SUB-004-03 | Microstructure (vol spike + acceleration) | S | MVP | — | Done |
| SUB-004-04-T01 | SUB-004-04 | Beta-hedge (beta via covariance, Nifty short) | M | MVP | — | Done |
| SUB-004-05-T01 | SUB-004-05 | ML overlay (GBM on factors, walk-forward CV) | M | MVP | — | Done |

## Bug Tracker
| BUG-ID | Severity | Feature | Description | Status | Fixed In |
|---|---|---|---|---|---|

## Completed Work
| ID | Type | Name | PR | Version | Date |
|---|---|---|---|---|---|
| FEAT-001 | feature | Trend-Following with Volatility-Adjusted Risk | — | v0.1.0 | 2026-08-27 |
| FEAT-002 | feature | Stat-Arb / Pairs Trading | — | v0.2.0 | 2026-08-27 |

## Document Index
| Document | Path | Feature | Last Updated |
|---|---|---|---|
| PRD | docs/prd/FEAT-001-trend-volatility-risk.md | FEAT-001 | 2026-08-27 |
| PRD | docs/prd/FEAT-002-pairs-trading.md | FEAT-002 | 2026-08-27 |
| PRD | docs/prd/FEAT-003-institutional-suite.md | FEAT-003 | 2026-08-27 |
| PRD | docs/prd/FEAT-004-advanced-quant.md | FEAT-004 | 2026-08-27 |
| API — Indicators | docs/api/indicators.md | FEAT-001 | 2026-08-27 |
| API — Signals | docs/api/signals.md | FEAT-001 | 2026-08-27 |
| API — Portfolio | docs/api/portfolio.md | FEAT-001 | 2026-08-27 |
| API — Pairs | docs/api/pairs.md | FEAT-002 | 2026-08-27 |
| API — Institutional | docs/api/institutional.md | FEAT-003 | 2026-08-27 |
| API — Advanced Quant | docs/api/advanced-quant.md | FEAT-004 | 2026-08-27 |
| QA — FEAT-001 | docs/qa/FEAT-001-trend-volatility-risk.md | FEAT-001 | 2026-08-27 |
| QA — FEAT-002 | docs/qa/FEAT-002-pairs-trading.md | FEAT-002 | 2026-08-27 |
| QA — FEAT-003 | docs/qa/FEAT-003-institutional-suite.md | FEAT-003 | 2026-08-27 |
| QA — FEAT-004 | docs/qa/FEAT-004-advanced-quant.md | FEAT-004 | 2026-08-27 |
| ADR-001 | docs/adr/ADR-001-wilder-rma.md | FEAT-001 | 2026-08-27 |
| ADR-002 | docs/adr/ADR-002-engle-granger-vs-johansen.md | FEAT-002 | 2026-08-27 |
| ADR-003 | docs/adr/ADR-003-institutional-suite.md | FEAT-003 | 2026-08-27 |
| ADR-004 | docs/adr/ADR-004-advanced-quant.md | FEAT-004 | 2026-08-27 |
| Runbook | docs/runbooks/strategies.md | all | 2026-08-27 |
| Release notes | docs/releases/v0.4.0.md | all | 2026-08-27 |
| README | README.md | — | 2026-08-27 |
| CHANGELOG | CHANGELOG.md | — | 2026-08-27 |
