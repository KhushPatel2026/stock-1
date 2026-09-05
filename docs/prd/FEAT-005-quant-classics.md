# PRD — FEAT-005 Quant Classics (mean reversion, momentum, factors, allocation, carry)

## Goal
Round out the strategy suite with the canonical quant classics that the existing FEAT-001..004 do not cover. Six independent strategies, each in its own module, each with a backtest, CLI one-liner, and tests.

## Why these six
The current suite is heavy on **trend / cross-section momentum / pairs / event-driven / microstructure / factor composite**. The classics below fill the obvious gaps:

| # | Strategy | Family | Why missing before |
|---|----------|--------|--------------------|
| 1 | Bollinger mean reversion | Single-stock mean reversion | Only pairs / cross-section mean reversion covered (FEAT-002, SUB-004-01 gap-fade) |
| 2 | RSI(2) / Connors | Short-horizon mean reversion | Same as #1 — different signal basis (z vs RSI) |
| 3 | Dual momentum (Antonacci) | Time-series + cross-section momentum combined | FEAT-004 sector-neutral is cross-section only; FEAT-001 trend is time-series only — never combined |
| 4 | Magic formula (Greenblatt) | Value + quality composite | FEAT-003 multi-factor uses proxies (P/E not directly accessible); magic formula is the textbook value+quality rank |
| 5 | Risk parity | Allocation method | Not a strategy per se but the canonical "equal risk contribution" allocation; sits at the meta-layer |
| 6 | Dividend yield carry | Yield / carry | No yield-ranked strategy in current suite |

## Scope
- **In:** Six `src/<strategy>.py` modules, each with `backtest(data, ...) -> (trades, equity_df)` following existing contract. One `tests/test_classics.py` with one test per strategy. ADR-005 + QA doc + runbook updates + README.
- **Out (deliberate):** Strategies that need non-yfinance data (options chains for full VRP, M&A announcement data for merger arb, intraday ticks for HFT, news/sentiment, fundamentals beyond price-derived proxies).

## Rules

### 1. Bollinger mean reversion
- Window 20, k=2σ
- Entry long: close < lower band, **and** 20-day trend filter (close > SMA200)
- Exit: close ≥ SMA20 (middle)
- Equal-weight across qualifying tickers, max 10 holdings
- Costs: 5bps round-trip

### 2. RSI(2) — Connors
- RSI(2) on close, entry long when RSI(2) < 5
- Exit when close > 5-day SMA
- Max 5 concurrent, equal-weight
- Costs: 5bps round-trip

### 3. Dual momentum (Antonacci)
- Monthly rebalance
- Absolute momentum: 12-month return > 0
- Relative momentum: rank tickers by 12M return, hold top N
- If absolute momentum fails → move to "defensive" (cash proxy: hold nothing in this single-asset-class variant)
- Top N=5, equal-weight, monthly

### 4. Magic formula (Greenblatt)
- Monthly rank by composite of (earnings yield + ROE), both z-scored
- Earnings yield proxy: inverse of P/E approximated via 12-month total return as a rank input (no fundamental DB) — see ADR-005
- ROE proxy: 12M return / 60-day realized vol (positive = efficient return generation)
- Top decile, equal-weight, monthly, 0.1% cost

### 5. Risk parity
- Compute 60-day realized vol per ticker
- Weight inversely to vol: `w_i = (1/σ_i) / Σ(1/σ_j)`
- Daily rebalance, monthly entry selection (top 10 by 12M momentum for the investable set)
- Cost: 1bps daily turnover

### 6. Dividend yield carry
- Static dividend yield map (annual % per ticker) — sourced from NSE public data; documented in code
- Monthly rebalance: long top-quartile by yield
- Filter: yield > 0 and not a stock that cut dividends historically (skip filter, documented limitation)
- Costs: 0.1%

## Honest caveats
- Magic formula uses price-derived proxies because fundamentals DB is out of scope. Real Greenblatt uses EY = EBIT/EV; here it's a 12M return rank. See ADR-005 for justification.
- Dividend yield is a static map; no live dividend cuts. Real impl would pull from NSE.
- All strategies are long-only. Short variants out of scope (no borrow data, plus Nifty50 large-caps shorting is restricted).
- All in-sample. Walk-forward + regime tests are v1.0.0 work.

## Non-goals
- Live trading, paper trading, broker integration.
- Multi-timeframe (daily bars only).
- Options-based strategies (would need chain data).
- HFT / microstructure at tick resolution.
