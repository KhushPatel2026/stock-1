# ADR-002: Engle-Granger for Pairs Discovery (not Johansen)

Date: 2026-08-27 | Status: Accepted | Feature: FEAT-002

## Context
Need to find cointegrated pairs among Nifty50. Options: Engle-Granger (pairwise coint test) vs Johansen (multivariate). Johansen finds cointegrating vectors across >2 series but is complex and needs larger lookback.

## Decision
Use Engle-Granger via `statsmodels.tsa.stattools.coint` for MVP. Scan same-sector pairs only (~150 vs 1225), filter by correlation ≥0.7 then p≤0.05. Rolling beta via OLS `np.polyfit`.

## Alternatives Considered
| Option | Pros | Cons | Reason Rejected |
|---|---|---|---|
| Engle-Granger (chosen) | Simple, pairwise, well-understood, fast | Misses multivariate cointegration | Chosen — sufficient for 2-leg pairs |
| Johansen | Finds multiple vectors, more rigorous | Heavy, needs >300 bars, overkill for pairs | Post-MVP |
| Correlation only | Fastest | Spurious, drifts permanently | Rejected — not stationary guarantee |
| Kalman filter hedge ratio | Dynamic beta | Complexity, needs tuning | Post-MVP |

## Consequences
Positive: Fast scan (<2s for 15 tickers), interpretable pvalue.
Negative: May miss time-varying beta — mitigated by rolling beta in execution.
Risks: Pairs break — mitigated by quarterly re-validation (same test, p>0.10 flag).
Verification: Synthetic cointegrated pair p<0.05, random walks p>0.2 — tests pass.
Revisit trigger: If we run multi-leg basket or need half-life sizing.
