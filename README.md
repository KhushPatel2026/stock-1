# stock-1 — Nifty 50 Trend-Following (Volatility-Adjusted Risk)

Long-only systematic strategy for Nifty 50 large-caps:

- **Trend filter:** close > SMA200
- **Entry:** SMA20 crosses above SMA50 + ADX > 20
- **Sizing:** 1% capital risk per trade (vol-adjusted)
- **Exits:** SL 2.5×ATR, TP 4×ATR (≈1.6R)
- **Diversification:** max 5 concurrent positions

## Quickstart
```bash
pip install -r requirements.txt
python -m src.backtest --tickers 15 --period 5y --capital 1000000
python -m pytest tests -q
```

## Structure
```
src/
  universe.py   — Nifty50 list
  data.py       — yfinance fetch + cache
  indicators.py — SMA / ATR / ADX (Wilder)
  signals.py    — is_entry()
  sizing.py     — levels() / position_size()
  portfolio.py  — run() backtest loop
  metrics.py    — CAGR / Sharpe / maxDD / win rate
  backtest.py   — CLI
tests/ — unit + integration
docs/
  prd/  — PRD
  api/  — contracts
  qa/   — QA report (Phase 7)
```

## Honest caveat
Solid starting point, not guaranteed edge. Needs walk-forward + regime checks (2018 crash, 2020 COVID, 2022 chop) before live capital. FEAT-001 costs not yet modeled (post-MVP); FEAT-002 models Indian costs (brokerage 0.03% + STT 0.025% + 5bps slippage).

## Also included: FEAT-002 — Pairs Trading (market-neutral)
```bash
python -m src.pair_backtest --tickers 15 --period 2y   # cointegration scan + top pair backtest
```
- Cointegration (Engle-Granger) same-sector scan, rolling beta (60), spread z-score (60)
- Entry z>±2, exit z→0 (±0.3), stop ±3.5, dollar-neutral, rolling re-validation quarterly

## Institutional Suite — FEAT-003
```bash
python3 -c "from src.factors import backtest; from src.data import fetch_many; from src.universe import NIFTY15; d=fetch_many(NIFTY15, period='2y'); t,eq=backtest(d); print(eq.tail())"
python3 -c "from src.options import covered_call_backtest; print(covered_call_backtest(d)[1].tail())"
python3 -c "from src.risk_overlay import apply_kill_switch; print(apply_kill_switch(eq['equity']).tail())"
python3 -c "from src.walk_forward import run; help(run)"
```
- **Factors:** `src/factors.py` — momentum/value/quality/lowvol composite, monthly top-decile rebalance
- **Options Vol:** `src/options.py` — Black-Scholes `bs_call()`, 5% OTM 30d covered call harvest
- **Events:** `src/events.py` — earnings ±5d + quarterly rebalance mean-reversion
- **Risk Overlay:** `src/risk_overlay.py` — 10% maxDD kill-switch, 15% vol targeting, correlation flag >0.7
- **Walk-Forward:** `src/walk_forward.py` — rolling train(504)/test(126) grid search, OOS Sharpe, no lookahead

## Advanced Quant — FEAT-004
```bash
python3 -c "from src.gap_fade import backtest; print(backtest(d)[1].tail())"
python3 -c "from src.sector_momentum import backtest; print(backtest(d)[1].tail())"
python3 -c "from src.microstructure import backtest; print(backtest(d)[1].tail())"
python3 -c "from src.beta_hedge import backtest; print(backtest(d, stock='RELIANCE.NS')[1].tail())"
python3 -c "from src.ml_overlay import backtest; print(backtest(d)[1].tail())"
```
- **Gap-Fade:** `src/gap_fade.py` — open vs prev_close gap >2σ, fade 1d mean-reversion
- **Sector-Neutral Mom:** `src/sector_momentum.py` — within-sector momentum long/short per sector, monthly
- **Microstructure:** `src/microstructure.py` — volume >2×20d + close near high → next-day continuation (daily proxy for order-flow)
- **Beta-Hedge:** `src/beta_hedge.py` — `rolling_beta()` cov/var, long stock + short beta×Nifty (synthetic equal-weight proxy)
- **ML Overlay:** `src/ml_overlay.py` — HistGradientBoosting on factors, walk-forward train/test, long top 3 probs

## Quant Classics — FEAT-005
Six canonical strategies that fill the family gaps left by FEAT-001..004. Each is a single backtest one-liner.
```bash
python3 -c "from src.bollinger import backtest; print(backtest(d)[1].tail())"
python3 -c "from src.rsi2 import backtest; print(backtest(d)[1].tail())"
python3 -c "from src.dual_momentum import backtest; print(backtest(d)[1].tail())"
python3 -c "from src.magic_formula import backtest; print(backtest(d)[1].tail())"
python3 -c "from src.risk_parity import backtest; print(backtest(d)[1].tail())"
python3 -c "from src.dividend_carry import backtest; print(backtest(d)[1].tail())"
```
- **Bollinger:** `src/bollinger.py` — 20d SMA ± 2σ, SMA200 trend filter, mean-reversion to middle band
- **RSI(2):** `src/rsi2.py` — Connors short-horizon reversal, exit on 5d SMA cross
- **Dual Momentum:** `src/dual_momentum.py` — Antonacci: 12M absolute gate + relative cross-section rank
- **Magic Formula:** `src/magic_formula.py` — Greenblatt EY+ROE composite (proxied from price — see ADR-005)
- **Risk Parity:** `src/risk_parity.py` — inverse-vol weighting, monthly selection + daily rebalance
- **Dividend Carry:** `src/dividend_carry.py` — top-quartile yield, monthly rebalance (static yield map)

**Total now: 50 strategies across 16 families, 77 tests pass.**

## Web Frontend

The repo ships with a React + shadcn/ui + Tailwind frontend that calls all 50 strategies through a FastAPI backend. Pick tickers, pick a strategy, hit Run.

```bash
# Backend
pip install -r requirements-api.txt
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

See [`frontend/README.md`](frontend/README.md) for details. The proxy in `vite.config.ts` forwards `/api/*` to the backend, so the same CORS-free setup works in dev and prod.

## API surface (when not using the UI)

```bash
curl http://127.0.0.1:8000/api/strategies                        # list all 50
curl http://127.0.0.1:8000/api/families                          # family counts
curl -X POST http://127.0.0.1:8000/api/backtest \
  -H "Content-Type: application/json" \
  -d '{"strategy_id":"bollinger","tickers":["RELIANCE.NS","TCS.NS"],"period":"2y","params":{"top_n":5}}'
```

## Ponytail notes
- No abstract Strategy class, no plugin system — straight functions until second strategy exists.
- No DB — parquet cache only.
- FEAT-001: yfinance + pandas only. FEAT-002 adds statsmodels (coint) — minimal justified dep.
- No Johansen/Kalman — Engle-Granger + rolling OLS until second pair model needed.
- FEAT-004: sklearn HGB only (already installed), daily proxies for tick data — replace with Zerodha Ticker feed when live. `// ponytail: daily proxy`
- FEAT-005: dividend yield is a static dict — refresh from NSE when live. Magic formula uses price-derived proxies (12M return + return/vol) — documented in ADR-005, swap for real EBIT/EV when fundamentals DB available.
- Options-based strategies (full VRP, iron condor, cash-secured put) skipped — need chain data, add when source wired.
