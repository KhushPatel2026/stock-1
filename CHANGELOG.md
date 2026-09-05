# Changelog — Keep a Changelog, SemVer

## [Unreleased]

## [v0.6.0] — 2026-08-27
### Added
- FEAT-006: 50-Strategy Library + Web Frontend
- 32 new strategy modules + tests (77 total tests pass):
  - Trend (8): donchian, keltner_break, aroon, macd, supertrend, ichimoku, hull_ma, parabolic_sar
  - Mean Reversion (7): stochastic, williams_r, cci, mfi, keltner_mr, zscore_mr, ou_process
  - Volatility (4): vol_breakout, vol_targeting, vol_regime, garch_lite
  - Volume (4): obv, vwap_dev, vpt, ad_line
  - Pattern (4): engulfing, hammer, three_soldiers, double_top
  - Factor (5): low_vol, quality, value, size_factor, high_52w
  - Trend add-on (1): breakout_volume
- FastAPI backend (`api/main.py`) — exposes all 50 strategies as REST:
  - GET /api/strategies (list with metadata)
  - GET /api/strategies/{id}
  - GET /api/tickers (Nifty50)
  - GET /api/families (counts)
  - POST /api/backtest (run a backtest)
  - GET /api/health
- React + Vite + TypeScript + shadcn/ui + Tailwind frontend (`frontend/`)
  - Tabs: Backtest | Strategy Library | About
  - Single-stock + basket backtest, equity curve (recharts), metrics table, recent trades
  - Strategy search + family filter
- Strategy registry (`src/registry.py`) — single source of truth
- META dict added to all existing FEAT-001..005 strategies for consistency
- Frontend dev server proxies /api → backend on port 8000

## [v0.5.0] — 2026-08-27
### Added
- FEAT-005: Quant Classics — 6 modules: Bollinger mean reversion (20d/2σ with SMA200 trend filter), RSI(2) Connors reversal, dual momentum (Antonacci absolute+relative), magic formula (Greenblatt EY+ROE, price-proxied per ADR-005), risk parity (inverse-vol daily rebalance), dividend yield carry (top quartile, static yield map)
- 6 new tests (44 total), coverage ~82%
- ADR-005 documenting strategy selection + magic formula proxy justification + excluded-strategy list
- QA report + runbook updates for FEAT-005

## [v0.4.0] — 2026-08-27
### Added
- FEAT-004: Advanced Quant — 5 modules: gap-fade (gap>2σ 1d), sector-neutral momentum (within-sector long/short), microstructure (vol spike + acceleration), beta-hedge (rolling cov/var, Nifty short), ML overlay (HistGradientBoosting on factors, walk-forward)
- 8 new tests (38 total), coverage 82%

## [v0.3.0] — 2026-08-27
### Added
- FEAT-003: Institutional Suite — 5 modules: multi-factor (momentum/value/quality/lowvol monthly), options vol (Black-Scholes 5% OTM covered call), event-driven (earnings/rebalance), risk overlay (10% DD kill, vol targeting 15%, corr>0.7), walk-forward (504/126 rolling OOS)
- 7 new tests (30 total), coverage 79% (core 88-99%)

## [v0.2.0] — 2026-08-27
### Added
- FEAT-002: Stat-Arb / Pairs Trading — Engle-Granger scan, rolling beta/spread/z-score, dollar-neutral execution, Indian costs, pair backtest CLI
- 7 new tests (23 total), coverage 69% (core 87-93%)

## [v0.1.0] — 2026-08-27
### Added
- FEAT-001: Trend-Following with Volatility-Adjusted Risk — all 6 rules, backtest engine, metrics, CLI
- 16 unit/integration tests, 65% coverage
