# Changelog — Keep a Changelog, SemVer

## [Unreleased]
### Fixed — wrong-price data bug (critical) + live prices + uniform cards
- Root cause: yfinance frames were trusted blindly — crossed/multi-ticker responses
  under parallel load silently put one ticker's price on another's card (INFY showed
  HDFCBANK's ₹712.10, ITC showed TCS's ₹2,304). `src/data.py` rewritten: every download
  is ticker-verified (mismatch → retry → skip, never silent), one process-wide lock,
  per-(ticker, period, interval) CSV cache with 12h TTL (parquet engine was missing so
  the old cache never hit — every call refetched).
- Deleted 5 contaminated legacy cache files; verified all 5 screenshot tickers now distinct.
- Live entries: `live_price()` (1m bars → fast_info → daily fallback) anchors plan
  entry/SL/target; cards show "Entry · Live" + live timestamp.
- Uniform cards: sign-aware percents (no more "+-6.51%"), HOLD cards say "split X long
  vs Y short — no consensus", missing-plan fallback line, human strategy names
  (XS Momentum 12-1, Short-Term Reversal, Turn-of-Month, ...).
- Faster decisions: ONE shared 1y fetch feeds levels + all 89 OOS-weight runs
  (`validation.chunk_oos/run_walk_forward` accept `data=`); per-ticker retry.
### Added — free scrapers (no keys)
- `src/screener.py`: screener.in top ratios (PE/ROE/ROCE/PB/DY/book/EPS/mcap), polite
  1.5s spacing, {} on failure. Wired into `fetch_fundamentals` first, yfinance fills
  debt/cash/EV gaps. Verified live: RELIANCE PE 23.9, ROE 8.9%, CMP matches tape.
- `src/nse_options.py`: NSE equity chain handshake + ATM IV (24h cache, {} when blocked).
  Wired into `covered_call_real` as NSE-IV calibration for the BS fallback (`iv_override`).
- BacktestPanel: 1D/3D/1W/2W/1M quick-period presets above the horizon selector.
- Tests: `test_data_verify.py` (ticker-mismatch rejection, cache scoping, scraper fallbacks),
  live-entry + HOLD-split assertions in `test_trade_plan.py`; upstox suite hermetic
  (expired-token + .env pollution fixed) — 176 passed, 4 skipped.
### Added — market weather in Trade Idea (news + global + sector + commodity)
- `src/market_context.py` (all free, no keys): Nifty regime (trend/200DMA/VIX state),
  global snapshot (S&P 500, Nasdaq, US 10Y, USDINR, Brent, Gold, Copper, Silver),
  sector day-change + 1M vs Nifty, linked-commodity line (e.g. Brent for Reliance),
  headlines via Google News India RSS with keyword tone (yfinance fallback).
- `GET /api/context?ticker=X` (20-min cache). Trade Idea tab shows a market-weather
  card: summary line, chips, amber cautions (VIX fear, Nifty downtrend, weak US open,
  negative news skew), clickable headlines. Votes untouched — context informs, never
  silently changes the verdict.

## [v1.1.0] — 2026-09-05
### Added
- **Upstox Analytics integration** (`src/upstox.py`):
  - `POST /api/upstox/token` — store access token
  - `GET /api/portfolio` — fetch real Upstox holdings + P&L enriched with live yfinance prices
  - `GET /api/upstox/option-chain` — option chain with greeks
  - `GET /api/upstox/india-vix` — India VIX
  - `GET /api/upstox/pcr` — Put-Call Ratio
  - `GET /api/upstox/server-info` — returns your public IP for Upstox whitelist
- **Portfolio tab** — paste Upstox token, view holdings + P&L + concentration risk + India VIX + AI suggestions
- **AI Insights tab** (Gemini Flash Lite via `src/ai.py`):
  - Personalized next-steps based on your strategy usage
  - Ask about any strategy in plain English
  - Analyze my portfolio — Gemini reviews your actual holdings
- **SQLite paper trading** (`src/paper.py`) — multi-portfolio support, full history persisted in `data/paper.db`
- **Strategy selection tracking** (`src/tracking.py`) — logs every strategy run for personalization
- **Frontier strategies** — 33 more registered (xs_momentum, BAB, distance_pairs, vol_managed, chandelier, turn_of_month, expiry_drift, accrual_anomaly, almgren_chriss, ...) — total now 89
- **Capital parameter** on `/api/backtest` — replaces fixed 1M
- **Public IP** in `/api/upstox/server-info` for Upstox whitelist
- **Cross-tab navigation** — Signals → Paper, Library → Backtest
- **Dark/light theme toggle**

### Tests
- 164 pass (was 102)
- New: paper SQLite, upstox client, AI explanations, tracking, capital scaling, frontier strategies

## [Unreleased]
### Changed — dynamic capital everywhere (no more static ₹10L)
- All 89 registered strategies now accept `capital` (default 1_000_000, fully dynamic):
  every `backtest()` signature + all cash/sizing internals + `META["params"]`
- `run_backtest(..., capital=...)` — injected only into fns that accept it (inspect-based),
  replacing the old try/except-TypeError fallback that silently dropped ALL params on mismatch
- `POST /api/backtest` accepts top-level `capital` field (validated > 0); also passable via `params`
- `tests/test_capital.py` — proves every strategy starts at given capital and PnL scales with it
- Only remaining 1M literals: defaults, META defaults, paper-broker DB default (param), CLI defaults (args)
### Added — FEAT-011 Frontier batch (9 strategies, new Seasonal family)
- `src/xsection.py` — xs_momentum (12-1 Jegadeesh-Titman), st_reversal (1M fade), lt_reversal (2Y fade); one loop, three scores
- `src/bab.py` — betting-against-beta (Frazzini-Pedersen lite, legs scaled to beta 1; reuses `rolling_beta`)
- `src/distance_pairs.py` — Gatev min-SSD pair (no cointegration test), z-score traded
- `src/vol_managed.py` — Moreira-Muir 15% vol-target scaling (no leverage)
- `src/chandelier.py` — Donchian entry + ATR trailing-stop exit
- `src/seasonal.py` — turn_of_month + expiry_drift (Thursday/NSE expiry)
- Registry: 56 → 65 strategies, 17 families; signals mapped; 10 new tests (`tests/test_frontier.py`)

## [v1.0.0] — 2026-09-05
### Added — v1.0.0 milestones all shipped
- **FEAT-007 Validation layer** (`src/validation.py`)
  - Walk-forward OOS: rolling train/test window metrics per strategy
  - Regime tests: 2018 crash, 2020 COVID, 2022 chop, full sample
  - CSV + Markdown reports in `reports/`
  - CLI: `python3 scripts/run_validation.py --tickers RELIANCE.NS,TCS.NS --period 3y --workers 4`
- **FEAT-007C Real fundamentals** (`src/fundamentals.py`)
  - yfinance `.info` extraction with 7-day JSON cache
  - Real EBIT/EV/ROE for Greenblatt (`src/magic_formula.py` updated)
  - `magic_formula_real` strategy registered
- **FEAT-007D Real options** (`src/options_real.py`)
  - Uses `ticker.option_chain()` when available
  - Falls back to BS synthetic chain for NSE (.NS) tickers (yfinance limitation)
  - `covered_call_real` strategy registered
- **FEAT-008 Intraday** (`src/intraday.py`)
  - 4 strategies: ORB, VWAP Reversion, Intraday Momentum, Overnight Drift
  - 60m bar support via yfinance
- **FEAT-009 Paper trading** (`src/paper.py`, `src/paper_engine.py`)
  - `PaperBroker`: mock broker with state persistence (JSON), slippage model
  - Daily rebalance from any strategy's targets
  - Endpoints: POST /api/paper/order, POST /api/paper/rebalance, GET /api/paper/state, GET /api/paper/report
- **FEAT-010 Today's signals** (`src/signals.py`)
  - Per-strategy × per-ticker long/short/flat classification with strength
  - Endpoint: GET /api/signals
  - Powers the Signals tab in the frontend
- **Frontend additions**
  - Signals tab — all 56 strategies × NIFTY15 tickers, search + family filter
  - Paper tab — place orders, rebalance from strategy, view portfolio
  - Reports tab — view walk_forward.csv, regime_tests.csv, regime_tests.md
  - /reports static mount in FastAPI for direct file access
- Tests: 102 pass (was 77)
- Validation report generated at `reports/regime_tests.md`, `reports/walk_forward.csv`

### Caveats closed in v1.0.0
- ✅ Walk-forward + regime tests (was open since v0.4.0)
- ✅ Real Greenblatt using yfinance .info (was price-proxied)
- ✅ Intraday bars (60m via yfinance)
- ✅ Paper trading simulator (was no broker)
- ✅ Today's signals endpoint (was no real-time view)

### Caveats remaining (external blockers)
- ❌ Live Zerodha broker — needs real account + Kite API keys
- ❌ M&A event feed — yfinance has no announcements API
- ❌ Real short interest — NSE borrow data not on free APIs
- ❌ Real option chains for .NS — yfinance limitation, fallback to BS

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
