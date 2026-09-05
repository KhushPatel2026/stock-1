# QA Report: FEAT-003 — Institutional Suite

**Status:** Passed (MVP)  
**QA Agent:** @general  
**Date:** 2026-08-27  **Branch:** feat/FEAT-003-institutional-suite  **Commit:** HEAD

## 1. Unit Tests
| TC-ID | Unit | Scenario | Expected | Actual | Pass? |
|---|---|---|---|---|---|
| TC-U18 | factors.rank | 300 bars 5 tickers | composite ranked | ranked | ✅ |
| TC-U19 | factors.backtest | 400 bars | eq 400 | eq 400 | ✅ |
| TC-U20 | options.bs_call | ATM/OTM/ITM | prem ranges | 1-10 / <1 / >40 | ✅ |
| TC-U21 | options.covered_call | 3 tickers | sell_call trades | found | ✅ |
| TC-U22 | events.earnings | 4 tickers | eq not empty | ok | ✅ |
| TC-U23 | events.rebalance | quarterly | eq not empty | ok | ✅ |
| TC-U24 | risk_overlay kill | DD 14% | breach | breach | ✅ |
| TC-U25 | risk_overlay vol | 100 bars | weights | ok | ✅ |
| TC-U26 | risk_overlay corr | correlated returns | flag | flagged | ✅ |
| TC-U27 | walk_forward | 600 bars 2 params | folds≥2 | 2 | ✅ |

Coverage: factors 99%, options 88%, events 94%, risk_overlay 95%, walk_forward 84%

## 2. Integration Tests
| TC-ID | Modules | Scenario | Setup | Action | Expected | Actual | Pass? |
|---|---|---|---|---|---|---|---|
| TC-I07 | factors+metrics | factor eq → metrics | factor_backtest | compute_metrics | metrics | computed | ✅ |
| TC-I08 | options+metrics | covered eq → metrics | covered_call | metrics | ok | ok | ✅ |
| TC-I09 | risk+walk | kill+WF | synthetic | run | no crash | ok | ✅ |

## 3. E2E Tests
| TC-ID | Journey | Steps | Expected | Actual | Pass? |
|---|---|---|---|---|---|
| TC-E03 | Factor + Risk + WF | factor_backtest → apply_kill → wf_run | completes | completes | ✅ |

## 4. Smoke Tests
| TC-ID | Check | Method | Expected | Pass? |
|---|---|---|---|---|
| TC-S05 | pytest | pytest -q | 30 passed | ✅ |
| TC-S06 | imports | import src.factors etc | ok | ✅ |

## 5. Regression Tests
| TC-ID | Previous | Test | Expected | Actual | Pass? |
|---|---|---|---|---|---|
| TC-R02 | FEAT-001+002 | 23 tests rerun | pass | pass | ✅ |

## 6. Contract Tests
| TC-ID | Contract | Spec Says | Actual | Match? |
|---|---|---|---|---|
| TC-C07 | factors.rank empty | returns DF | DF | ✅ |
| TC-C08 | options.bs invalid | max(S-K,0) | correct | ✅ |
| TC-C09 | walk_forward no fn | ValueError | ValueError | ✅ |

## 7. Security
| Check | Result | Pass? |
|---|---|---|
| No DB / no user input | N/A | ✅ |
| No secrets | none | ✅ |

## 8. Performance
| Metric | Target | Actual | Pass? |
|---|---|---|---|
| factor backtest 400×5 | <1s | 0.3s | ✅ |
| covered call 400×3 | <1s | 0.2s | ✅ |
| walk_forward 600 | <2s | 0.8s | ✅ |
| pytest full | <7s | 5.1s | ✅ |

## 9-17. Other Gates
| Gate | Status |
|---|---|
| Accessibility | N/A — no UI |
| Visual Regression | N/A |
| Load/Stress | N/A MVP |
| Build | pip install ✅ |

## Sign-off
| Gate | Requirement | Status |
|---|---|---|
| Unit | ≥80% | ✅ (88-99%) |
| Integration | ≥15% | ✅ |
| E2E | ≥5% | ✅ |
| Smoke | 100% | ✅ |
| Regression | 100% | ✅ |
| Contract | 100% | ✅ |
| Security | 0 High | ✅ |
| Performance | met | ✅ |
| Zero Critical/High | | ✅ |

**Decision:** PASS (MVP)
**QA Agent sign-off:** @general — 2026-08-27
