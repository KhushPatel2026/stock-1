"""Strategy registry — single source of truth for all backtests exposed via API."""
from __future__ import annotations
import importlib
from typing import Callable
import pandas as pd

from src.data import fetch_many

_REGISTRY: list[dict] = []


def _reg(strategy_id: str, module: str, family: str, description: str, fn_name: str = "backtest", params: dict | None = None, name: str | None = None, name_override: str | None = None, family_override: str | None = None, description_override: str | None = None):
    _REGISTRY.append({
        "id": strategy_id,
        "module": module,
        "fn": fn_name,
        "name": name or strategy_id,
        "family": family,
        "description": description,
        "default_params": params or {},
        "name_override": name_override,
        "family_override": family_override,
        "description_override": description_override,
    })


REASONS: dict[str, str] = {
    "trend_following": "Long-only trend: 200DMA filter + 20/50 SMA cross + ADX>20. Only trades in confirmed uptrends. Best in sustained bull markets, worst in chop.",
    "pairs_trading": "Market-neutral pair: dollar-neutral, bets on cointegration reversion. Pairs trade converges when the spread mean-reverts. Low beta to Nifty.",
    "factors": "Multi-factor composite: ranks Nifty50 by momentum/value/quality/low-vol z-scores monthly. Holds top decile. Diversified across factors.",
    "gap_fade": "Buys the close after intraday gap >2σ in either direction; exits next bar. Catches overreaction. Works best in mean-reverting regimes.",
    "sector_momentum": "Within-sector long/short momentum. Longs the strongest stock in each sector, shorts the weakest. Sector-neutral exposure.",
    "microstructure": "Volume >2×20d avg + close near high → next-day continuation. Daily proxy for order-flow imbalance.",
    "beta_hedge": "Long stock + short beta × Nifty (synthetic). Captures stock-specific alpha, removes market exposure. Sharpe is alpha Sharpe.",
    "ml_overlay": "HistGradientBoosting on price-derived factors, walk-forward CV, long top-N probabilities. ML meta-strategy on top of factor base.",
    "options": "Black-Scholes 5% OTM 30d covered call. Sells premium against long stock. Income strategy; caps upside.",
    "events": "Earnings spike (±5d, hold 10d) or quarterly rebalance (±10d) mean-reversion. Event-driven alpha.",
    "risk_overlay": "10% maxDD kill-switch + 15% vol target + correlation >0.7 flag. Sits on top of any strategy.",
    "walk_forward": "Rolling 504/126 train/test grid search. Reports OOS Sharpe — the only honest validation harness.",
    "bollinger": "20d SMA ±2σ with 200d SMA trend filter. Mean-revert to middle band in uptrends only.",
    "rsi2": "Connors RSI(2) < 5 → buy, exit on 5d SMA cross. Famous short-horizon reversal rule.",
    "dual_momentum": "Antonacci: 12M absolute gate (market >0?) + relative cross-section top-N. Defensive (cash) when market regime is negative.",
    "magic_formula": "Greenblatt EY+ROE composite (price-proxied: 12M return + return/vol). Top decile monthly. Cheap + profitable.",
    "risk_parity": "Inverse-vol weighting. Top 10 by 12M momentum, weighted by 1/vol. Equal risk contribution.",
    "dividend_carry": "Top quartile by static yield map. Monthly rebalance. Yield premium harvested without stock-selection alpha.",
    "magic_formula_real": "Greenblatt with REAL yfinance .info fundamentals (EBIT/EV/ROE). Same logic, real data when available.",
    "covered_call_real": "Covered call using real option chain when available, BS synthetic fallback for .NS.",
    "donchian": "Turtle-style: close > 20d high → buy, close < 10d low → sell. Classic trend breakout.",
    "keltner_break": "Close > EMA(20) + 2×ATR(14). Volatility-adjusted breakout.",
    "aroon": "Aroon Up > 80 AND Aroon Up > Aroon Down. Pure trend-strength filter.",
    "macd": "MACD line crosses signal. Classic trend-following signal.",
    "supertrend": "ATR-based supertrend flip. Long-only when close > supertrend line.",
    "ichimoku": "Above cloud + Tenkan/Kijun cross. Multi-factor trend confirmation.",
    "hull_ma": "Hull MA slope flip. Faster-reacting trend signal than SMA.",
    "parabolic_sar": "PSAR flip vs close. Wilder's stop-and-reverse system.",
    "stochastic": "%K < 20 from oversold. Mean-reversion entry.",
    "williams_r": "%R < -80 → reversal. Similar to RSI.",
    "cci": "CCI < -100 → reversal. Commodity channel adapted to equities.",
    "mfi": "Money Flow Index < 20. Volume-weighted mean reversion.",
    "keltner_mr": "Close < EMA - 2×ATR. Vol-adjusted mean reversion.",
    "zscore_mr": "Z-score of close vs SMA(20) < -2 with SMA200 trend filter.",
    "ou_process": "Ornstein-Uhlenbeck mean reversion on single ticker. Continuous-time model fit, traded via z-score.",
    "vol_breakout": "Daily range > k×ATR. Volatility expansion trade, one-day hold.",
    "vol_targeting": "Scale positions to 15% annualized vol target. Reduces risk in high-vol regimes.",
    "vol_regime": "Only trade when realized vol > 252d median. Volatility filter.",
    "garch_lite": "EWMA vol forecast vs realized. Trades volatility expansion.",
    "obv": "On-Balance Volume vs OBV-SMA cross. Volume-confirmed trend.",
    "vwap_dev": "Close vs rolling VWAP. Mean-reversion to VWAP.",
    "vpt": "Volume-Price Trend. Cumulative volume × return. Trend confirmation.",
    "ad_line": "Accumulation/Distribution line. Smart-money proxy.",
    "engulfing": "Bullish engulfing reversal pattern.",
    "hammer": "Hammer / shooting star reversal. Japanese candlestick.",
    "three_soldiers": "Three white soldiers. Three consecutive strong bullish candles.",
    "double_top": "Double top / bottom breakout. Classic chart pattern.",
    "low_vol": "Bottom decile by 60d realized vol. Low-volatility anomaly.",
    "quality": "Top decile by return / vol ratio. Quality = efficient return generation.",
    "value": "Top decile by price-vs-SMA200 discount. Value proxy when fundamentals unavailable.",
    "size_factor": "Bottom decile by 20d avg $-volume. Size proxy (smaller = higher).",
    "high_52w": "Closest to 52w high. Momentum via 52w-high proximity.",
    "breakout_volume": "Donchian breakout gated by volume >1.5× 20d avg. Higher-quality breakouts only.",
    "intraday_orb": "Opening Range Breakout on 60m bars. First hour range, buy high break.",
    "intraday_vwap": "VWAP reversion on 60m bars. Fade deviations > 1.5σ from VWAP.",
    "intraday_mom": "Intraday momentum: close > 20-bar SMA + volume confirmation, EOD exit.",
    "overnight_drift": "Close-to-open drift: buy at close, sell at next open. Captures overnight gap.",
}


# FEAT-001..005 (12 existing with backtest)
_reg("bollinger", "src.bollinger", "MR", "20d SMA ±2σ with SMA200 trend filter.")
_reg("rsi2", "src.rsi2", "MR", "Connors RSI(2) short-horizon reversal.")
_reg("dual_momentum", "src.dual_momentum", "Momentum", "Antonacci absolute + relative momentum.")
_reg("magic_formula", "src.magic_formula", "Factor", "Greenblatt EY+ROE composite (price-proxied).")
_reg("risk_parity", "src.risk_parity", "Allocation", "Inverse-vol weighting, monthly + daily rebalance.")
_reg("dividend_carry", "src.dividend_carry", "Carry", "Top quartile by static yield, monthly.")
_reg("factors", "src.factors", "Factor", "Multi-factor composite (mom/value/qual/lowvol).")
_reg("gap_fade", "src.gap_fade", "MR", "Open-vs-prev-close gap >Nσ fade.")
_reg("sector_momentum", "src.sector_momentum", "Cross-sect", "Within-sector long/short monthly.")
_reg("microstructure", "src.microstructure", "Volume", "Vol spike + close near high → next-day continuation.")
_reg("beta_hedge", "src.beta_hedge", "Hedge", "Long stock + short beta × Nifty.")
_reg("ml_overlay", "src.ml_overlay", "ML", "HistGradientBoosting on factors, walk-forward.")

# FEAT-001..005 wrappers added
_reg("trend_following", "src.portfolio", "Trend", "SMA200 filter + SMA20/50 cross + ADX>20 + ATR SL/TP.")
_reg("pairs_trading", "src.pair_portfolio", "Stat-arb", "Engle-Granger cointegration pair trade, dollar-neutral, Indian costs.")
_reg("covered_call", "src.options", "Options", "Black-Scholes 5% OTM 30d covered call.", name_override="Covered Call (BS)")
_reg("earnings_drift", "src.events", "Event", "Earnings spike (proxy 3σ) ±5d → hold 10d.", name_override="Earnings Drift")
_reg("rebalance_drift", "src.events", "Event", "Quarterly rebalance ±10d mean-reversion.", fn_name="backtest_rebalance", name_override="Index Rebalance Drift")

# FEAT-006 — Trend (8)
_reg("donchian", "src.donchian", "Trend", "N-day high breakout.")
_reg("keltner_break", "src.keltner_break", "Trend", "Close > EMA + 2×ATR breakout.")
_reg("aroon", "src.aroon", "Trend", "Aroon up > threshold.")
_reg("macd", "src.macd", "Trend", "MACD line crosses signal.")
_reg("supertrend", "src.supertrend", "Trend", "ATR-based supertrend flip.")
_reg("ichimoku", "src.ichimoku", "Trend", "Above cloud + Tenkan/Kijun cross.")
_reg("hull_ma", "src.hull_ma", "Trend", "Hull MA slope flip.")
_reg("parabolic_sar", "src.parabolic_sar", "Trend", "PSAR vs close flip.")

# FEAT-006 — MR (7)
_reg("stochastic", "src.stochastic", "MR", "%K < 20 from oversold.")
_reg("williams_r", "src.williams_r", "MR", "%R < -80 reversal.")
_reg("cci", "src.cci", "MR", "CCI < -100 reversal.")
_reg("mfi", "src.mfi", "MR", "Money flow < 20 reversal.")
_reg("keltner_mr", "src.keltner_mr", "MR", "Close < EMA - 2×ATR.")
_reg("zscore_mr", "src.zscore_mr", "MR", "Z-score < -2 with SMA200 filter.")
_reg("ou_process", "src.ou_process", "MR", "Ornstein-Uhlenbeck process reversal.")

# FEAT-006 — Volatility (4)
_reg("vol_breakout", "src.vol_breakout", "Volatility", "Daily range > k×ATR breakout.")
_reg("vol_targeting", "src.vol_targeting", "Volatility", "Scale weights to target vol.")
_reg("vol_regime", "src.vol_regime", "Volatility", "Trade only when vol > median.")
_reg("garch_lite", "src.garch_lite", "Volatility", "EWMA vol forecast vs realized.")

# FEAT-006 — Volume (4)
_reg("obv", "src.obv", "Volume", "OBV vs OBV-SMA cross.")
_reg("vwap_dev", "src.vwap_dev", "Volume", "Close vs rolling VWAP.")
_reg("vpt", "src.vpt", "Volume", "Volume-Price Trend.")
_reg("ad_line", "src.ad_line", "Volume", "Accumulation/Distribution line.")

# FEAT-006 — Pattern (4)
_reg("engulfing", "src.engulfing", "Pattern", "Bullish engulfing reversal.")
_reg("hammer", "src.hammer", "Pattern", "Hammer / shooting star.")
_reg("three_soldiers", "src.three_soldiers", "Pattern", "Three white soldiers.")
_reg("double_top", "src.double_top", "Pattern", "Double top/bottom breakout.")

# FEAT-006 — Factor (5)
_reg("low_vol", "src.low_vol", "Factor", "Bottom decile by realized vol.", name_override="Low Volatility Factor")
_reg("quality", "src.quality", "Factor", "Return-per-risk top decile.", name_override="Quality Factor")
_reg("value", "src.value", "Factor", "Price vs SMA200 discount (proxy).", name_override="Value Factor (Price Proxy)")
_reg("size_factor", "src.size_factor", "Factor", "Bottom decile by ADV (size proxy).", name_override="Size Factor (ADV Proxy)")
_reg("high_52w", "src.high_52w", "Factor", "Closest to 52w high.", name_override="52-Week High Momentum")
_reg("breakout_volume", "src.breakout_volume", "Trend", "Donchian breakout gated by volume >1.5x avg.")

# FEAT-007 — Real fundamentals + real options
_reg("magic_formula_real", "src.magic_formula", "Factor", "Greenblatt with REAL yfinance .info (EBIT/EV/ROE) when available.", params={"use_real_fundamentals": True}, name_override="Magic Formula (Real Fundamentals)")
_reg("covered_call_real", "src.options_real", "Options", "Covered call using real option chains when available, BS fallback otherwise.", name_override="Covered Call (Real Chain)")

# FEAT-008 — Intraday (4)
_reg("intraday_orb", "src.intraday", "Intraday", "Opening Range Breakout (60m).", fn_name="backtest_orb", name_override="Opening Range Breakout")
_reg("intraday_vwap", "src.intraday", "Intraday", "VWAP Reversion (60m).", fn_name="backtest_vwap", name_override="VWAP Reversion")
_reg("intraday_mom", "src.intraday", "Intraday", "Intraday Momentum (60m).", fn_name="backtest_mom", name_override="Intraday Momentum")
_reg("overnight_drift", "src.intraday", "Intraday", "Close-to-Open drift (daily).", fn_name="backtest_overnight", name_override="Overnight Drift")


def list_strategies() -> list[dict]:
    """Return metadata for all registered strategies (id, name, family, description, default_params, reason)."""
    out = []
    for s in _REGISTRY:
        params = dict(s["default_params"])
        name_override = s.get("name_override")
        desc_override = s.get("description_override")
        fam_override = s.get("family_override")
        try:
            mod = importlib.import_module(s["module"])
            if hasattr(mod, "META") and isinstance(mod.META, dict):
                params = {**mod.META.get("params", {}), **params}
                fam = fam_override or s["family"] or mod.META.get("family", "Other")
                desc = desc_override or mod.META.get("description", s["description"])
                name = name_override or mod.META.get("name", s["id"])
            else:
                fam, desc, name = (fam_override or s["family"]), (desc_override or s["description"]), (name_override or s["name"])
        except Exception:
            fam, desc, name = (fam_override or s["family"]), (desc_override or s["description"]), (name_override or s["name"])
        out.append({
            "id": s["id"],
            "name": name,
            "family": fam,
            "description": desc,
            "params": params,
            "reason": REASONS.get(s["id"], ""),
        })
    return out


def get_strategy(strategy_id: str) -> dict | None:
    for s in list_strategies():
        if s["id"] == strategy_id:
            return s
    return None


def run_backtest(strategy_id: str, tickers: list[str], params: dict | None = None, period: str = "2y") -> dict:
    """Run a strategy and return {equity_curve, metrics, trades, info}."""
    entry = next((s for s in _REGISTRY if s["id"] == strategy_id), None)
    if entry is None:
        raise ValueError(f"unknown strategy: {strategy_id}")
    mod = importlib.import_module(entry["module"])
    fn = getattr(mod, entry["fn"])
    # fetch data
    data = fetch_many(tickers, period=period)
    if not data:
        return {"equity_curve": [], "metrics": {}, "trades": [], "info": {"warning": "no data fetched"}}
    # filter params to known defaults
    merged = {**entry["default_params"]}
    if hasattr(mod, "META"):
        merged.update(mod.META.get("params", {}))
    if params:
        for k, v in params.items():
            if v is not None:
                merged[k] = v
    # run
    try:
        result = fn(data, **merged)
    except TypeError as e:
        # param mismatch; fall back to defaults
        result = fn(data)
    trades, eq = result[0], result[1]
    # metrics
    metrics = _compute_metrics(eq)
    # serialize
    eq_curve = [{"date": str(idx.date()), "equity": float(row["equity"])} for idx, row in eq.iterrows()]
    trades_out = [{k: (str(v) if hasattr(v, "date") else v) for k, v in t.items()} for t in trades[:500]]
    return {
        "equity_curve": eq_curve,
        "metrics": metrics,
        "trades": trades_out,
        "info": {"strategy": strategy_id, "tickers": tickers, "params": merged, "n_trades": len(trades)},
    }


def _compute_metrics(eq: pd.DataFrame) -> dict:
    if eq.empty or len(eq) < 2:
        return {}
    s = eq["equity"].astype(float)
    rets = s.pct_change().dropna()
    if rets.empty:
        return {}
    n = len(rets)
    cagr = (s.iloc[-1] / s.iloc[0]) ** (252 / max(n, 1)) - 1 if s.iloc[0] > 0 else 0
    sharpe = float(rets.mean() / rets.std() * (252 ** 0.5)) if rets.std() > 0 else 0
    peak = s.cummax()
    dd = (s - peak) / peak
    max_dd = float(dd.min())
    total_ret = float(s.iloc[-1] / s.iloc[0] - 1) if s.iloc[0] > 0 else 0
    return {
        "total_return": round(total_ret, 4),
        "cagr": round(cagr, 4),
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_dd, 4),
        "n_bars": n,
        "final_equity": round(float(s.iloc[-1]), 2),
    }
