# PRD — FEAT-003: Institutional Suite

Status: Draft | Date: 2026-08-27 | Branch: feat/FEAT-003-institutional-suite

## 1. Objective

Add 5 institutional-style layers that complement FEAT-001 (momentum) + FEAT-002 (mean-reversion) — all achievable at retail scale via Zerodha + public data.

## 2. Modules

| SUB | Owns | Reuses | Does NOT |
|---|---|---|---|
| 01 Factors | Monthly ranking on momentum (12M ret), value (P/E proxy via 1/price vs sector median — fallback if yfinance info missing), quality (ROE proxy via return/ maxDD), low-vol (1/ std). Composite z-score. Buy top decile (5), equal weight, monthly rebalance. | `data.py`, `universe.py` | Full Fama-French, 10 factors |
| 02 Options Vol | Covered calls 5% OTM 30d, Black-Scholes premium, harvest vol risk premium. Hold stock + short call, monthly roll. | `indicators` vol (ATR/std) | Real options chain, Greeks hedging |
| 03 Event-Driven | Earnings drift (±5d window) + index rebalance (±10d) — long event stock vs Nifty hedge, 10d hold. Uses yfinance earnings dates if available, else calendar-agnostic price-spike proxy. | `data.py` | Intraday block deals |
| 04 Risk Overlay | Portfolio-level: maxDD 10% kill-switch (cut to cash), vol-targeting (scale exposure = target_vol / realized_vol, cap 1.5x), correlation monitor (flag if strategy corr >0.7) | `metrics.py` equity curves | Intraday risk, VaR |
| 05 Walk-Forward | Rolling train/test (e.g., 504d train /126d test), param grid optimizer, OOS metrics, anti-overfit discipline. Generic `optimize(train_data, grid) -> best_params`. | All strategies | AutoML |

## 3. Data Model

- Factor row: `ticker, momentum, value, quality, lowvol, composite, rank`
- Option leg: `expiry, strike=close*1.05, premium (BS), stock close, expiry close, pnl`
- Event: `ticker, event_date, type, window return, pnl`
- Risk state: `drawdown, scaled_exposure, corr_matrix`
- Walk-forward fold: `train_start, train_end, test_start, test_end, best_params, oos_sharpe`

## 4. API (summary — full docs/api/institutional.md)

- `factors.rank(data, date) -> DataFrame ranked`
- `factors.backtest(data, capital) -> (trades, equity)`
- `options.bs_call(S,K,T,r,sigma) -> premium`
- `options.covered_call_backtest(data, capital, otm=0.05) -> (trades, equity)`
- `events.earnings_backtest(data, capital) / rebalance_backtest`
- `risk_overlay.apply(equity, target_vol=0.15) -> scaled_equity, triggers`
- `walk_forward.run(data, param_grid, train=504, test=126, strategy_fn) -> folds`

## 5. Success

- Factors: monthly rebalance completes, top decile backtest non-zero trades, metrics computed
- Options: covered call premium >0, fewer drawdowns than naked holding
- Events: detects events, backtest completes
- Risk: kill-switch triggers on synthetic 15% DD, vol scaling reduces exposure in high vol
- Walk-forward: finds best params on train, OOS Sharpe reported, no lookahead

## 6. Non-Goals

- Live options chain, live earnings feed, real index change feed — use yfinance/static proxies
- Intraday, Greeks delta-hedging, factor neutralization — post-MVP

## 7. Ponytail

- No factor library, no options pricing lib — closed-form BS in 10 lines + scipy norm
- Reuse existing metrics, data, universe — no new DB
- Each SUB is ~80-120 lines, pure functions, no class hierarchy

