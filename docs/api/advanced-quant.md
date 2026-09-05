# API: Advanced Quant (Gap-Fade, Sector-Neutral, Microstructure, Beta-Hedge, ML)

Status: Draft | Version: v0.4.0 | Last Updated: 2026-08-27

## 1. Gap-Fade — `src/gap_fade.py`

### `backtest(data, thresh=2.0, gap_window=20) -> (trades, equity)`
- gap = open - prev_close (prev_close = close.shift(1))
- gap_z = gap / rolling_std(gap, gap_window)
- Entry: if gap_z > thresh → short (fade up gap), if < -thresh → long; hold 1 day (close at next close), costs 0.1%
- Returns trades with gap_z, direction, pnl. Nifty ETF proxy: average universe if needed.

## 2. Sector-Neutral Momentum — `src/sector_momentum.py`

### `backtest(data, top_n=1) -> (trades, equity)`
- For each month-end, for each sector with ≥2 stocks, rank momentum 12M within sector, long top_n, short bottom_n per sector, equal weight per leg, monthly rebalance.
- `SECTORS` from universe.py. Skips sectors with <2.

## 3. Microstructure — `src/microstructure.py`

### `backtest(data, vol_mult=2.0) -> (trades, equity)`
- Volume spike = volume > vol_mult * rolling_mean(volume,20)
- Acceleration = (high - close) < 0.5*(high-low) and close > open*1.005 (strong close near high)
- Signal: spike + acceleration → long next open, exit next close (intraday continuation). Short opposite not used for MVP.

## 4. Beta-Hedge — `src/beta_hedge.py`

### `rolling_beta(stock_rets, nifty_rets, window=60) -> Series`
`beta = cov(stock, nifty)/var(nifty)`

### `backtest(data, stock, nifty_proxy=None, lookback=60) -> (trades, equity, betas)`
- nifty_proxy = equal-weight avg of all closes if not supplied
- Long stock 10% notional, short beta*notional Nifty, daily rebalance beta, hold.

## 5. ML Overlay — `src/ml_overlay.py`

### `make_features(data, date) -> DataFrame`
Features per ticker: momentum, value, quality, lowvol (same as factors) + gap_z, rel volume. Label: 5d forward return >0.

### `train_predict(data, train=252, test=60) -> (model, preds, backtest)`
- Walk-forward: train HistGradientBoostingClassifier on train window, predict test, backtest long top 3 preds per month. Uses `sklearn.ensemble.HistGradientBoostingClassifier` (already installed).
- Returns OOS equity; warns if OOS Sharpe < train Sharpe (overfit flag).

## Dependencies
pandas, numpy, scipy, sklearn (already installed). No new dep.

## Performance
All 5 on 15 tickers 2y <4s.
