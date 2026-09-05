# QA Report — FEAT-005 Quant Classics

## Phase 7 — All test types

| Test type | Method | Result |
|-----------|--------|--------|
| Unit | Each module's `backtest` runs on synthetic data (10 tickers, 400 bars, deterministic seed) | ✅ 6/6 |
| Integration | Modules share data layer; no cross-test pollution | ✅ |
| Contract | `backtest(data, ...) -> (trades, equity)` shape preserved across all 6 | ✅ |
| Smoke | Equity curve has correct length (400 or 600 dates depending on test) | ✅ |
| Existing regression | All FEAT-001..004 tests still pass | ✅ 38/38 |

**Total: 44 tests pass (38 prior + 6 new), coverage delta +0% (overall ~82%, new modules also ≥80%)**

## Strategy-level QA

### 1. Bollinger mean reversion
- 400 bars, 10 tickers synthetic data
- Trend filter (close > SMA200) prevents catching falling knives
- Entry: close < SMA20 - 2σ; exit: close ≥ SMA20
- Test: equity curve built, no crashes, trades list correct shape
- Caveat: synthetic data may produce very few qualifying signals (random walk rarely breaches 2σ) — backtest still runs cleanly

### 2. RSI(2) — Connors
- Wilder smoothing on 2-period RSI (same as ADX/ATR in `src/indicators.py`)
- Entry: RSI(2) < 5; exit: close > 5-day SMA
- Test: RSI values bounded [0,100], backtest runs, max 5 concurrent
- Caveat: RSI(2) < 5 is rare in random data — backtest may produce few trades but should not error

### 3. Dual momentum (Antonacci)
- 12-month lookback; absolute gate (equal-weight universe return > 0)
- If gate fails → cash; if passes → top N by 12M return
- Test: 600 bars, monthly rebalance, top 3, runs cleanly
- Caveat: synthetic data trend may keep absolute gate mostly on → most of test is "top 3 momentum"

### 4. Magic formula (Greenblatt)
- EY + ROE composite z-score; top 20% monthly
- Test: rank function returns scored DataFrame, backtest runs
- Caveat: proxies (12M return for EY, return/vol for ROE) bias toward momentum — documented in ADR-005

### 5. Risk parity
- Inverse-volatility weighting; monthly selection (top 10 by 12M mom), daily rebalance
- Test: 400 bars, 10 tickers, backtest runs, weight rebalance loop executes
- Caveat: synthetic data → equal-ish vols → near-equal weights. The strategy is most useful with cross-sectional vol dispersion (real markets)

### 6. Dividend yield carry
- Static yield map (`YIELDS`), top 25% monthly
- Test: function runs even with synthetic data (no real dividend overlap), YIELDS dict well-formed
- Caveat: in production, only tickers with positive yield in YIELDS dict get considered. With all synthetic tickers T0..T9.NS, no overlap → empty trades; equity curve = flat 1,000,000. Test asserts shape, not PnL — appropriate for synthetic

## Honest caveats

- **All six strategies are in-sample and untested on real Nifty50 data through this QA cycle.** Test data is synthetic random walks. Real-data validation is the v1.0.0 walk-forward work.
- **No transaction cost model for risk_parity's daily rebalance.** 1bps assumption is aggressive; real NSE costs (brokerage + STT + impact) on daily turnover may erode the edge. Add when validated.
- **Magic formula proxies are biased.** See ADR-005 — this is a known limitation, not a bug.
- **Dividend yield is static.** NSE dividends change; refresh `YIELDS` manually or wire a live source.

## What's NOT in QA scope

- Live data backtest (no NSE live feed wired)
- Walk-forward optimization (v1.0.0)
- Regime stress tests (2018/2020/2022) — v1.0.0
- Comparison vs benchmark (Nifty50 TR) — would be added in v1.0.0 report
- Cross-strategy correlation analysis — would inform portfolio construction

## Sign-off
Phase 7 PASS for FEAT-005. Ready to ship as v0.5.0.
