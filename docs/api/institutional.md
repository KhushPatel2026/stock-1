# API: Institutional Suite (Factors, Options, Events, Risk, Walk-Forward)

Status: Draft | Version: v0.3.0 | Last Updated: 2026-08-27

## Overview
5 modules sharing data/universe/metrics. All pure functions, no I/O except data dict.

## 1. Factors — `src/factors.py`

### `rank(data: dict[ticker→df], date) -> DataFrame`
Computes per ticker at month-end `date`:
- momentum = close / close.shift(252) -1 (12M)
- value = 1 / (close / median_close_sector) proxy (or 0 if info unavailable) — ponytail: price relative to sector median
- quality = momentum / (maxDD+0.01) proxy
- lowvol = 1 / std(returns 60d)
Each z-scored cross-sectionally, composite = mean(z). Rank desc.

### `backtest(data, capital=1e6, top_n=5) -> (trades, equity)`
Monthly rebalance (last trading day), equal weight top_n, costs 0.1% per rebalance.

## 2. Options — `src/options.py`

### `bs_call(S,K,T,r,sigma) -> float`
Black-Scholes call: `N(d1)*S - N(d2)*K*exp(-rT)`, `d1=(ln(S/K)+(r+0.5σ²)T)/σ√T`. Uses `scipy.stats.norm.cdf`. No div0: σ floor 0.01.

### `covered_call_backtest(data, capital, otm=0.05, dte=30) -> (trades, equity)`
Per ticker monthly: hold stock, sell call 5% OTM 30d, premium added to cash, if expiry close > strike → stock called away (sell at strike). Else keep stock. Vol σ = 60d realized vol annualized.

## 3. Events — `src/events.py`

### `earnings_backtest(data, capital, window=5) -> (trades, equity)`
For each ticker, find earnings dates via `yfinance.Ticker.earnings_dates` if available else synthetic: price spikes >3σ as proxy. Long stock window±5d, hedge short Nifty proxy (equal notional), hold 10d. If no dates, returns empty trades (graceful).

### `rebalance_backtest(data, capital) -> (trades, equity)`
Simulate index rebalance: on first trading day each quarter, long weakest recent performer (mean-reversion bet on rebalance pressure). Simplified: buy bottom 20% momentum last 30d, hold 10d.

## 4. Risk Overlay — `src/risk_overlay.py`

### `max_drawdown_kill(equity: Series, thresh=0.10) -> trigger_dates`
If peak-to-trough >10%, flag — portfolio cuts to cash thereafter (or scales to 0).

### `vol_target_scale(returns: Series, target=0.15, lookback=60) -> Series weights`
`weight = target / (realized_vol*√252)` clipped 0.2-1.5. Applied to position sizing.

### `correlation_flag(equities: dict[str→Series], thresh=0.7) -> dict corr_matrix + flags`
Pearson corr of strategy returns; flag if >0.7 (diversification broken).

## 5. Walk-Forward — `src/walk_forward.py`

### `run(data, param_grid: list[dict], train=504, test=126, strategy_fn) -> list[Fold]`
Splits index into rolling windows: train on window, grid-search best by train Sharpe/CAGR, evaluate OOS on test. Returns folds with `best_params, train_sharpe, oos_sharpe, oos_metrics`. No lookahead: test data never used for selection.

### Example
```python
folds = run(data, [{"sma":20},{"sma":50}], strategy_fn=lambda d, p: backtest(d, sma=p["sma"]))
```

## Dependencies
| Module | Direction |
|---|---|
| scipy.stats.norm | uses (BS) |
| yfinance | optional for earnings |
| pandas/numpy | uses |

## Performance
Full suite on 15 tickers 2y <5s.
