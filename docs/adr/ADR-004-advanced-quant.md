# ADR-004: Advanced Quant — Gap-Fade, Sector-Neutral, Microstructure Proxy, Beta-Hedge, ML Overlay

Date: 2026-08-27 | Status: Accepted | Feature: FEAT-004

## Context
User requested 5 more institutional techniques. Each normally needs tick data, futures, or feature store. At retail scale with Yahoo daily data, we need proxies.

## Decision
- Gap-Fade: daily gap = open - prev_close, z >2 → fade 1d. Not futures basis.
- Sector-Neutral: within-sector momentum rank (not cross-market). Reuses SECTORS dict.
- Microstructure: volume >2×20d avg + close near high (>open*1.005) as proxy for order-flow imbalance. Not book depth.
- Beta-Hedge: synthetic Nifty = equal-weight avg of universe, rolling cov/var beta, short beta×notional. Not real futures.
- ML: HistGradientBoostingClassifier on 4 factor features, walk-forward train/test, long top 3 probs. Not XGB/LightGBM tuning.

## Alternatives Considered
| Option | Pros | Cons | Reason Rejected |
|---|---|---|---|
| Tick OB / Zerodha feed | Real microstructure | Vendor, infra, cost | Proxy sufficient for MVP |
| Real Nifty futures | Exact hedge | Contract rolls, margin | Synthetic avg for framework |
| LightGBM/XGBoost | Slightly better | New dep, tuning | sklearn HGB already installed, sufficient |
| Deep nets | Expressive | Overfit, needs more data | GBM + walk-forward is honest baseline |

## Consequences
Positive: All 5 runnable offline on Yahoo daily, 38 tests pass, 82% coverage.
Negative: Proxies understate edge vs real tick/futures; flagged as known ceiling.
Risks: Gap-fade with 1d hold is simplistic — needs intraday exit for live; sector-neutral short needs borrowing.
Verification: Synthetic tests with known gaps/spikes/betas pass; ML OOS preds non-empty.
Revisit trigger: When tick data or futures feed available, replace proxies with real.

## Verification
38 tests, gap_fade 98%, microstructure 100%, ml 98%, beta 93%.

## Ponytail Note
`// ponytail: daily proxy for tick microstructure — replace with Zerodha Ticker feed when live`
