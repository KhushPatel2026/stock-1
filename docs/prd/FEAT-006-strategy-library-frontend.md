# PRD — FEAT-006 Strategy Library (50+ strategies) + Frontend

## Goal
Two parallel deliverables:
1. **Strategy library expansion** — implement the missing ~35 canonical quant strategies so the suite covers 50+ named strategies across all major families.
2. **Web frontend** — React + Vite + shadcn/ui + Tailwind SPA that lets a user pick any Nifty50 stock (or basket), pick any strategy, set parameters, run a backtest, and see the equity curve + metrics.

## Strategy inventory (50 total)

### Existing (18)
| # | Strategy | Module | Family |
|---|----------|--------|--------|
| 1 | Trend-Following (SMA+ADX) | src/portfolio.py (FEAT-001) | Trend |
| 2 | Pairs Trading | src/pair_portfolio.py (FEAT-002) | Stat-arb |
| 3 | Multi-Factor | src/factors.py (FEAT-003) | Factor |
| 4 | Covered Call | src/options.py (FEAT-003) | Options |
| 5 | Event-Driven | src/events.py (FEAT-003) | Event |
| 6 | Risk Overlay | src/risk_overlay.py (FEAT-003) | Overlay |
| 7 | Walk-Forward | src/walk_forward.py (FEAT-003) | Meta |
| 8 | Gap-Fade | src/gap_fade.py (FEAT-004) | MR |
| 9 | Sector Momentum | src/sector_momentum.py (FEAT-004) | Cross-sect |
| 10 | Microstructure | src/microstructure.py (FEAT-004) | Volume |
| 11 | Beta-Hedge | src/beta_hedge.py (FEAT-004) | Hedge |
| 12 | ML Overlay | src/ml_overlay.py (FEAT-004) | ML |
| 13 | Bollinger MR | src/bollinger.py (FEAT-005) | MR |
| 14 | RSI(2) Connors | src/rsi2.py (FEAT-005) | MR |
| 15 | Dual Momentum | src/dual_momentum.py (FEAT-005) | Momentum |
| 16 | Magic Formula | src/magic_formula.py (FEAT-005) | Factor |
| 17 | Risk Parity | src/risk_parity.py (FEAT-005) | Allocation |
| 18 | Dividend Carry | src/dividend_carry.py (FEAT-005) | Carry |

### New (32) — to implement
| # | Strategy | Module | Family | Signal (one-liner) |
|---|----------|--------|--------|---------------------|
| 19 | Donchian Breakout | src/donchian.py | Trend | close > N-day high |
| 20 | Keltner Breakout | src/keltner_break.py | Trend | close > EMA + 2×ATR |
| 21 | Aroon Trend | src/aroon.py | Trend | aroon_up > aroon_down + threshold |
| 22 | MACD Signal | src/macd.py | Trend | macd line crosses signal |
| 23 | Supertrend | src/supertrend.py | Trend | close vs supertrend line flip |
| 24 | Ichimoku Cloud | src/ichimoku.py | Trend | close > cloud, TK cross |
| 25 | Hull MA | src/hull_ma.py | Trend | HMA slope flip |
| 26 | Parabolic SAR | src/parabolic_sar.py | Trend | SAR flip vs close |
| 27 | Stochastic | src/stochastic.py | MR | %K < 20, exit %K > 50 |
| 28 | Williams %R | src/williams_r.py | MR | %R < -80, exit > -50 |
| 29 | CCI | src/cci.py | MR | CCI < -100, exit > 0 |
| 30 | MFI | src/mfi.py | MR | MFI < 20, exit > 50 |
| 31 | Keltner MR | src/keltner_mr.py | MR | close < EMA - 2×ATR |
| 32 | Single-Stock Z-Score | src/zscore_mr.py | MR | z(close vs SMA) < -2 |
| 33 | O-U Mean Reversion | src/ou_process.py | MR | OU spread z-score (single ticker O-U on returns) |
| 34 | Volatility Breakout | src/vol_breakout.py | Vol | close > prev close + k×ATR |
| 35 | Vol Targeting Portfolio | src/vol_targeting.py | Vol | scale positions to 15% target vol |
| 36 | Vol Regime Filter | src/vol_regime.py | Vol | trade only when vol > median |
| 37 | GARCH-Lite | src/garch_lite.py | Vol | EWMA vol forecast vs realized |
| 38 | OBV Trend | src/obv.py | Volume | OBV SMA cross |
| 39 | VWAP Deviation | src/vwap_dev.py | Volume | close vs rolling VWAP |
| 40 | Volume-Price Trend | src/vpt.py | Volume | VPT slope flip |
| 41 | Accumulation/Distribution | src/ad_line.py | Volume | A/D line slope flip |
| 42 | Engulfing | src/engulfing.py | Pattern | bullish/bearish engulfing |
| 43 | Hammer / Shooting Star | src/hammer.py | Pattern | reversal candle pattern |
| 44 | Three Soldiers / Crows | src/three_soldiers.py | Pattern | 3 consecutive strong candles |
| 45 | Double Top/Bottom | src/double_top.py | Pattern | M/W shape breakout |
| 46 | Low-Vol Factor | src/low_vol.py | Factor | bottom decile by 60d vol |
| 47 | Quality Factor | src/quality.py | Factor | top decile by return/vol ratio |
| 48 | Value Factor | src/value.py | Factor | top decile by price vs SMA200 discount |
| 49 | Size Factor | src/size_factor.py | Factor | small-cap proxy (avg daily $ vol bottom decile) |
| 50 | 52-Week High Mom | src/high_52w.py | Factor | top decile by % off 52w high |

**Total: 50 strategies.**

## Contract for all new modules

Every new module exports `backtest(data: dict[str, pd.DataFrame], **params) -> tuple[list[dict], pd.DataFrame]` matching existing modules.

`data` is `{ticker: DataFrame}` where DataFrame has columns: `close, open, high, low, volume` indexed by date.

Each module also exports a `META` dict:
```python
META = {
    "name": "Bollinger Mean Reversion",
    "family": "MR",
    "params": {"top_n": int, "cost": float, ...},
    "description": "...",
}
```

The backend introspects this to expose strategy metadata to the frontend.

## Frontend

### Stack
- Vite + React 18 + TypeScript
- shadcn/ui (Button, Card, Select, Input, Tabs, Table)
- Tailwind CSS v3
- recharts for equity curve
- lucide-react for icons

### Routes / pages
Single page app with tabs:
1. **Single-Stock Backtest** — pick 1 ticker, 1 strategy, params, run, see equity curve + metrics
2. **Multi-Stock Basket** — pick basket, pick strategy, run portfolio backtest
3. **Strategy List** — table of all 50 strategies with descriptions

### Backend (FastAPI)
- `GET /api/strategies` — list all 50 with metadata
- `GET /api/tickers` — list of Nifty50 tickers
- `POST /api/backtest` — run backtest, returns JSON { equity_curve, metrics, trades }
- `GET /api/health`

Port: 8000 (backend), 5173 (frontend dev). CORS enabled for frontend.

## Honest caveats
- Many strategies are single-name research reproductions. Some are toy implementations because yfinance doesn't have the real source data (e.g., no fundamentals, no earnings calendar, no options chain beyond prices). Documented per strategy in code.
- All in-sample. Walk-forward + regime tests still v1.0.0 work.
- 35 new strategies in one shot = some will be rough. Sub-agent batching is for speed, not depth.

## Sub-agent allocation

To parallelize the 32 new strategy implementations, batch by family:

- **Batch A (Trend):** sub-agent implements modules 19-26 (8 strategies)
- **Batch B (Mean Reversion):** sub-agent implements modules 27-33 (7 strategies)
- **Batch C (Volume + Pattern):** sub-agent implements modules 34-45 (8 strategies + vol family)
- **Batch D (Factor + Carry):** sub-agent implements modules 46-50 + Earnings yield (5 strategies)

Each sub-agent writes:
- 5-8 strategy modules
- One consolidated test file `tests/test_batch_*.py` covering each
- Returns a summary of files created

Owner verifies each batch before merge.

## Out of scope (deliberate, deferred to v1.0.0+)
- Live broker integration (Zerodha Kite)
- Intraday strategies (need tick/5min bars)
- Real options-based strategies (full VRP, condors, CSP) — need chain data
- Real event-driven (M&A, earnings calendar, insider)
- Real sentiment / news
- Walk-forward + regime tests across 2018/2020/2022
