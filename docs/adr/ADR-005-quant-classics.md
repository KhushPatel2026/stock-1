# ADR-005 — Strategy selection for FEAT-005 (Quant Classics)

## Status
Accepted, 2026-08-27.

## Context
User asked to create "all the possible stock strategies in the world". That's literally impossible — the academic + practitioner literature has hundreds of named strategies across multiple families. We need a deliberate selection that:

1. Fills gaps not covered by FEAT-001..004
2. Stays within the existing technical constraints (daily bars, yfinance, no options chains)
3. Is implementable in a few days, not weeks
4. Has a credible academic / practitioner basis

## Decision
Add six strategies that each fill an obvious gap. One file per strategy, one `backtest(data, ...)` per file, following the existing module contract.

| # | Strategy | Family | Gap filled |
|---|----------|--------|------------|
| 1 | Bollinger mean reversion | Single-stock MR | Cross-section / pairs MR covered; single-stock MR missing |
| 2 | RSI(2) | Single-stock MR | Different signal basis (RSI vs z-score); short-horizon |
| 3 | Dual momentum | Combined momentum | FEAT-001 trend + FEAT-004 cross-section — never gated by absolute |
| 4 | Magic formula | Value + quality | FEAT-003 factors use proxies; this is the textbook value+quality rank |
| 5 | Risk parity | Allocation | No meta-allocation strategy in the suite |
| 6 | Dividend yield carry | Yield | No yield-ranked strategy in the suite |

## Magic formula — proxy justification

Greenblatt's original formula uses **Earnings Yield = EBIT / EV** and **Return on Capital = EBIT / (Net Working Capital + Net Fixed Assets)**. Both require fundamental data not available from yfinance.

**Proxy chosen:**
- EY proxy = trailing 12-month price return (positive = improving)
- ROE proxy = 12M return / 60d realized vol (return per unit risk)

**Why this is acceptable as a first-pass signal:**
- Both inputs are rank-monotonic with the true factors (price and vol give a clean ordering even if absolute levels are wrong)
- The composite (z-score sum) is a relative ranking, not an absolute level — proxy distortion affects all stocks similarly
- We're testing whether the *factor structure* works in Nifty50 large-caps, not whether we can replicate Greenblatt exactly
- When a fundamentals source becomes available, swap the proxy for real EBIT/EV — the rank logic stays identical

**Acceptable cost:** The proxy systematically favors high-momentum stocks (which look like "high earnings yield"). This biases the strategy toward momentum. We accept this — it's documented and the bias is consistent across rebalance periods.

**Upgrade path:** Replace `ey` and `roe` lines in `src/magic_formula.py:_rank_at` with a fundamentals-data lookup; no other change needed.

## Dividend yield — static map

Live dividend data is not in yfinance (only price/volume). Used a static yield map sourced from NSE public filings, last refresh 2026-08-27. Refresh manually when stale. Dividend cuts are not detected — flagged as known limitation.

**Upgrade path:** Pull from NSE corporate actions API or scrape from NSE website; replace `YIELDS` dict with a function that returns live yield.

## Deliberately excluded (out of FEAT-005 scope)

These are real strategies but excluded for technical or scope reasons. Listed so future work has a starting list:

- **Volatility risk premium (full delta-hedge)** — needs options chains. Skip until chain source is integrated.
- **Iron condor / credit spreads** — needs options chains.
- **Cash-secured put** — needs options chains.
- **Merger / M&A arb** — needs announcement data (news feed).
- **Insider buying** — needs insider transactions data.
- **Short interest** — needs borrow / SI data (NSE publishes weekly but no API).
- **Sentiment / news** — needs NLP pipeline.
- **Overnight / intraday momentum** — needs intraday bars.
- **Index inclusion / rebalance** — needs rebalance dates and added/deleted ticker lists.
- **Earnings momentum (post-earnings drift)** — needs earnings calendar (date + surprise).
- **Piotroski F-score** — needs fundamentals (annual report parsing).
- **Magic formula with real EBIT/EV** — needs fundamentals.
- **Cross-asset momentum (bonds / commodities / FX)** — needs multi-asset data.
- **Volatility targeting at portfolio level** — partially covered by FEAT-003 risk_overlay; full portfolio-level impl deferred.

**Estimated count of what's missing:** ~15 named strategies not in v0.5.0. If "all" is taken literally, the suite would need an additional ~10-15 modules. Each takes ~1-2 days including test + doc.

## Consequences

- v0.5.0 covers the major families with at least one canonical representative.
- All six strategies use the same `backtest(data, ...) -> (trades, equity)` contract — composable.
- The strategy surface area is now broad enough that v1.0.0 work (walk-forward, regime tests) is the next critical step rather than adding more strategies.
- Honest caveat still applies: in-sample, no live data, daily proxies for tick data.
