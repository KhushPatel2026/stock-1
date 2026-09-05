# PRD — FEAT-004: Advanced Quant (Gap-Fade, Sector-Neutral, Microstructure, Beta-Hedge, ML)

Status: Draft | Date: 2026-08-27 | Branch: feat/FEAT-004-advanced-quant

## 1. Objective

Round out retail-achievable institutional menu with 5 remaining techniques. Each is pure function, reuses data/universe/metrics, no tick feed required.

## 2. Modules

| SUB | Owns | Reuses | Does NOT |
|---|---|---|---|
| 01 Gap-Fade | Daily gap = open - prev_close, z = gap / rolling std(gap) 20d, fade if |z|>2, intraday close (hold 1d), bet gap closes | data | Futures basis, tick |
| 02 Sector-Neutral Mom | Rank momentum 12M *within* each sector, long top 1 / short bottom 1 per sector, equal weight, monthly | universe.SE​CTORS, factors | Sector ETF short |
| 03 Microstructure | Volume spike (>2× 20d avg) + price acceleration (high>close 1% + close>open), intraday continuation bet next day | data volume | Order-book depth |
| 04 Beta-Hedge | Beta = cov(stock, Nifty)/var(Nifty) 60d, hedge directional stock bet with Nifty futures short beta×notional | data (Nifty proxy = avg of universe) | Real Nifty futures |
| 05 ML Overlay | GBM (HistGradientBoostingClassifier) on factor features → predict 5d forward return sign, combine into composite, walk-forward CV | factors, sklearn | Deep nets, HPO |

## 3. API Summary — docs/api/advanced-quant.md

- `gap_fade.backtest(data, thresh=2.0) -> (trades, equity)`
- `sector_momentum.backtest(data, top_n=1) -> (trades, equity)`
- `microstructure.backtest(data, vol_mult=2.0) -> (trades, equity)`
- `beta_hedge.backtest(data, stock, nifty_proxy, lookback=60) -> (trades, equity, betas)`
- `ml_overlay.train_predict(data, lookback=252) -> model, preds, backtest`

## 4. Success

- Gap-fade: detects gaps, trades when |z|>2, metrics computed
- Sector-neutral: within-sector ranks, long/short per sector, monthly
- Microstructure: volume spike + acceleration triggers, next-day hold
- Beta-hedge: beta ≈1 for large-cap, hedged PnL market-neutral
- ML: GBM trains on factors, OOS preds via walk-forward, no lookahead

## 5. Non-Goals

- Tick-level OB, options basis, futures rolls — daily proxies only
- Real hedge with NIFTY futures contract — synthetic Nifty proxy
- Deep ML/tuning — single HistGradientBoosting with default + walk-forward

## 6. Ponytail

- No tick store, no OB simulator, no feature store — 10-20 lines per signal + sklearn
- Reuse factors/metrics, no new infra
- Each SUB ~60-90 lines

