# ADR-003: Institutional Suite — Factors/Options/Event/Risk/Walk-Forward Minimal Design

Date: 2026-08-27 | Status: Accepted | Feature: FEAT-003

## Context
User requested 5 institutional layers beyond trend + pairs. Each could be a full system (AQR factors, options vol harvesting, event-driven, risk overlay, walk-forward). Need MVP that is runnable at retail scale without options chain or live event feed.

## Decision
- Factors: 4-factor composite z-scored monthly, top decile equal weight — not 10-factor Fama-French.
- Options: Black-Scholes closed form (10 lines) with 60d realized vol, 5% OTM 30d covered call — not full chain Greeks.
- Events: Synthetic spike proxy + yfinance earnings_dates fallback, quarterly rebalance mean-reversion — not block-deal feed.
- Risk: MaxDD 10% kill-switch, vol-target 15%, correlation flag 0.7 — not VaR/CVaR.
- Walk-Forward: Rolling train/test grid search — generic, reuses any strategy_fn.

## Alternatives Considered
| Option | Pros | Cons | Reason Rejected |
|---|---|---|---|
| Factor library (alphalens) | Full factor analysis | Heavy, needs fundamentals DB | Overkill MVP |
| Options chain via yfinance | Real premiums | Sparse for Nifty, slow, API limits | Synthetic BS sufficient |
| Full event DB (earnings, index changes) | Precise | Needs data vendor, licensing | Synthetic proxy for framework |
| PyPortfolioOpt / riskfolio | Full optimization | New dep, complexity | Simple overlay first |
| Custom walk-forward per strategy | Tailored | Duplication | Generic engine reuses all |

## Consequences
Positive: All 5 runnable on existing data/universe/metrics, <600 lines total, 79% coverage, <7s tests.
Negative: Value/fundamentals proxied via price, not real P/E/B — marked as known ceiling.
Risks: Options vol estimated from realized (not implied) — premium may be mispriced vs live; flagged in README.
Verification: Each module has synthetic test with known outcome; full suite 30 tests pass.
Revisit trigger: When live fundamentals (yfinance info stable) or real options chain available, replace proxies.
