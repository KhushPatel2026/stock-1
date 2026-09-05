# PRD — FEAT-007 Validation Layer + FEAT-008 Intraday + FEAT-009 Paper Trading + FEAT-010 Signals

## Goal
Close the v1.0.0 milestones: walk-forward validation, regime stress tests, real fundamentals, intraday strategies, paper trading simulator, and a "today's signals" endpoint. Solve all caveats that have a workable data source.

## Components

### FEAT-007A: Walk-forward validation
- `src/validation.py` — `walk_forward(strategy_fn, data, train=504, test=126)` → list of OOS windows with metrics
- Apply to all 50 strategies via `src/registry.py`
- Output: per-strategy OOS Sharpe, total return, max DD across windows
- CSV: `reports/walk_forward.csv`

### FEAT-007B: Regime tests
- 3 named regimes: 2018 (crash), 2020 (COVID), 2022 (chop)
- Per regime: per-strategy metrics (Sharpe, total return, max DD)
- Output: `reports/regime_tests.csv` + `reports/regime_tests.md`

### FEAT-007C: Real fundamentals for Greenblatt
- Replace price-derived EY/ROE proxies with real `yfinance.Ticker.info`
- EBIT proxy = EBITDA (yfinance gives EBITDA, not EBIT directly)
- EV = marketCap + totalDebt - totalCash
- EY = EBITDA / EV
- ROE = returnOnEquity (direct from .info)
- `src/fundamentals.py` — caching helper that pulls `.info` once per ticker and caches to JSON
- Update `src/magic_formula.py` to use real fundamentals when available, fall back to proxy if not

### FEAT-007D: Real options via yfinance (where available)
- `src/options_real.py` — `covered_call_real(ticker)` uses `ticker.option_chain()` when available
- Falls back to BS synthetic chain if option_chain returns empty (which it does for .NS)
- Documented: "real options data unavailable for NSE; using BS synthetic chain — same source as before, just more explicit about the gap"

### FEAT-008: Intraday strategies (60m bars)
- `src/intraday.py` — module with 4 strategies using 60m bars:
  1. Opening Range Breakout (ORB) — buy high of first hour, stop low of first hour
  2. VWAP Reversion — fade deviations > 1σ from rolling VWAP
  3. Intraday Momentum — buy when 60m close > 60m SMA20 with volume confirmation
  4. Close-to-Open Drift — buy at close, sell at next open (overnight momentum)
- Same `backtest(data, ...)` contract, but data is 60m bars
- Tests with synthetic intraday data

### FEAT-009: Paper trading simulator
- `src/paper.py` — `PaperBroker` class
  - Tracks cash, positions, fills (with mock slippage)
  - Persists state to `data/paper_state.json`
  - `place_order(ticker, side, qty, price)` — fills at last close ± slippage
  - `mark_to_market()` — current portfolio value
- `src/paper_engine.py` — runs all 50 strategies on latest data, generates target positions, applies via PaperBroker
- Daily report: `reports/paper_<date>.md`

### FEAT-010: Today's signals endpoint
- `GET /api/signals` — returns current signal for each strategy on each ticker (long/flat/short)
- Computed from latest data, no full backtest
- Powers a "Today's Signals" tab in the frontend

## Frontend additions
- Tab: **Signals** — grid of all strategies × all tickers, current position
- Tab: **Paper Portfolio** — mock broker state, today's P&L
- Tab: **Reports** — links to walk_forward.csv, regime_tests.md, validation report

## Caveats that remain after this FEAT
- Live broker integration (Zerodha Kite) — requires real account + API keys
- M&A announcement data — yfinance has no M&A feed
- Short interest — NSE borrow data not available via free APIs

These three are documented as "external integration blockers" in the README. The first (Zerodha) is the only one that's truly unblocked; the other two require paid data sources.

## Sub-agent allocation

- **Agent A**: validation.py (walk-forward + regime), tests for both, runs validation across all 50 → CSV outputs
- **Agent B**: fundamentals.py + update magic_formula.py + options_real.py
- **Agent C**: intraday.py (4 strategies) + tests + integration with API
- **Agent D**: paper.py (PaperBroker) + paper_engine.py + signals API endpoint

All agents write into src/, share the existing contract. Owner verifies and integrates.

## Tests

- Each new module gets tests
- Final: `pytest tests -q` → 77+ pass (all existing + new)
- Validation report is computed by `python -m src.validation --run-all` and saved to `reports/`
