# ADR-001: Use Wilder's RMA for ATR/ADX

Date: 2026-08-27 | Status: Accepted | Feature: FEAT-001

## Context
ATR and ADX require Wilder's smoothing, not SMA or EMA. Many retail implementations use EMA and get different values, breaking comparability with professional desks and TradingView.

## Decision
Implement `_wilder_rma` exactly: seed = mean(first window), then (prev*(w-1)+val)/w. ATR from True Range, ADX from +DM/-DM → +DI/-DI → DX → RMA.

## Alternatives Considered
| Option | Pros | Cons | Reason Rejected |
|---|---|---|---|
| Chosen — Wilder RMA | Correct per Wilder, matches TA standards | Slightly more code | Chosen |
| pandas `ewm(alpha=1/w)` | One-liner | Different seed, different ATR/ADX | Wrong smoothing |
| pandas-ta dependency | Already implements correctly | Extra dep, heavier, opaque | Ponytail: few lines > new dep |

## Consequences
Positive: Metrics match professional definitions, testable vs manual calc.
Negative: None.
Risks: DX 0/0 → NaN → handled via fillna(0) for flat markets.
Verification: Unit tests vs hand-computed ATR3, ADX trending vs flat.
Revisit trigger: If we add more indicators, re-evaluate pandas-ta adoption.
