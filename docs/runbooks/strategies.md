# Runbook — stock-1 strategy suites

How to run each strategy locally. All commands assume `cd` to repo root.

## Common setup
```bash
pip install -r requirements.txt
python3 -m pytest tests -q           # 38 tests, ~20s
```

Data is fetched on-demand via yfinance and cached to `data/cache/`. First run per ticker is slow; subsequent runs read parquet.

## FEAT-001 — Trend-following (long-only)
```bash
python -m src.backtest --tickers 15 --period 5y --capital 1000000
```
Outputs: equity curve + metrics (CAGR / Sharpe / maxDD / win rate / exposure).

## FEAT-002 — Pairs trading (market-neutral)
```bash
python -m src.pair_backtest --tickers 15 --period 2y
```
Scans same-sector cointegration, picks top pair, runs dollar-neutral backtest with Indian costs (brokerage 0.03% + STT 0.025% + 5bps slippage).

## FEAT-003 — Institutional suite
Each module is a one-liner:
```bash
python3 -c "from src.data import fetch_many; from src.universe import NIFTY15; d=fetch_many(NIFTY15, period='2y')"
python3 -c "from src.factors import backtest as f; from src.data import fetch_many; from src.universe import NIFTY15; _,eq=f(fetch_many(NIFTY15, period='2y')); print(eq.tail())"
python3 -c "from src.options import covered_call_backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(covered_call_backtest(fetch_many(NIFTY15[:3], period='1y'))[1].tail())"
python3 -c "from src.events import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'))[1].tail())"
python3 -c "from src.risk_overlay import apply_kill_switch; import pandas as pd, numpy as np; eq=pd.Series(np.cumprod(1+np.random.normal(0.0005,0.01,500))); print(apply_kill_switch(eq).tail())"
python3 -c "from src.walk_forward import run; help(run)"
```

## FEAT-004 — Advanced quant
```bash
python3 -c "from src.data import fetch_many; from src.universe import NIFTY15; d=fetch_many(NIFTY15, period='2y')"  # cache once
python3 -c "from src.gap_fade import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'))[1].tail())"
python3 -c "from src.sector_momentum import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'))[1].tail())"
python3 -c "from src.microstructure import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'))[1].tail())"
python3 -c "from src.beta_hedge import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'), stock='RELIANCE.NS')[1].tail())"
python3 -c "from src.ml_overlay import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'))[1].tail())"
```

## Sanity-check before any change
```bash
python3 -m pytest tests -q --no-header
```

## FEAT-005 — Quant Classics
```bash
python3 -c "from src.data import fetch_many; from src.universe import NIFTY15; d=fetch_many(NIFTY15, period='2y')"  # cache once
python3 -c "from src.bollinger import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'))[1].tail())"
python3 -c "from src.rsi2 import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'))[1].tail())"
python3 -c "from src.dual_momentum import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'))[1].tail())"
python3 -c "from src.magic_formula import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'))[1].tail())"
python3 -c "from src.risk_parity import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'))[1].tail())"
python3 -c "from src.dividend_carry import backtest; from src.data import fetch_many; from src.universe import NIFTY15; print(backtest(fetch_many(NIFTY15, period='2y'))[1].tail())"
```

## Known limits
- FEAT-001 backtest does not model transaction costs (post-MVP).
- FEAT-004 microstructure uses daily proxies for tick data; replace with Zerodha feed when live. `// ponytail: daily proxy`
- Walk-forward and regime tests (2018 crash / 2020 COVID / 2022 chop) are in scope for v1.0.0 — not in v0.5.0.
- Magic formula uses price-derived proxies (12M return + return/vol) for EY/ROE; documented in ADR-005. Swap for real EBIT/EV when fundamentals DB is available.
- Dividend yield is a static `YIELDS` dict in `src/dividend_carry.py`; refresh manually or wire a live NSE source.
