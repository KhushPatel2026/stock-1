"""Strategy registry — single source of truth for all backtests exposed via API."""
from __future__ import annotations
import importlib
from typing import Callable
import pandas as pd

from src.data import fetch_many

_REGISTRY: list[dict] = []


def _reg(strategy_id: str, module: str, family: str, description: str, fn_name: str = "backtest", params: dict | None = None, name: str | None = None):
    _REGISTRY.append({
        "id": strategy_id,
        "module": module,
        "fn": fn_name,
        "name": name or strategy_id,
        "family": family,
        "description": description,
        "default_params": params or {},
    })


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
_reg("covered_call", "src.options", "Options", "Black-Scholes 5% OTM 30d covered call.")
_reg("earnings_drift", "src.events", "Event", "Earnings spike (proxy 3σ) ±5d → hold 10d.")
_reg("rebalance_drift", "src.events", "Event", "Quarterly rebalance ±10d mean-reversion.", fn_name="backtest_rebalance")

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
_reg("low_vol", "src.low_vol", "Factor", "Bottom decile by realized vol.")
_reg("quality", "src.quality", "Factor", "Return-per-risk top decile.")
_reg("value", "src.value", "Factor", "Price vs SMA200 discount (proxy).")
_reg("size_factor", "src.size_factor", "Factor", "Bottom decile by ADV (size proxy).")
_reg("high_52w", "src.high_52w", "Factor", "Closest to 52w high.")
_reg("breakout_volume", "src.breakout_volume", "Trend", "Donchian breakout gated by volume >1.5x avg.")

# FEAT-007 — Real fundamentals + real options
_reg("magic_formula_real", "src.magic_formula", "Factor", "Greenblatt with REAL yfinance .info (EBIT/EV/ROE) when available.", params={"use_real_fundamentals": True})
_reg("covered_call_real", "src.options_real", "Options", "Covered call using real option chains when available, BS fallback otherwise.")

# FEAT-008 — Intraday (4)
_reg("intraday_orb", "src.intraday", "Intraday", "Opening Range Breakout (60m).", fn_name="backtest_orb")
_reg("intraday_vwap", "src.intraday", "Intraday", "VWAP Reversion (60m).", fn_name="backtest_vwap")
_reg("intraday_mom", "src.intraday", "Intraday", "Intraday Momentum (60m).", fn_name="backtest_mom")
_reg("overnight_drift", "src.intraday", "Intraday", "Close-to-Open drift (daily).", fn_name="backtest_overnight")


def list_strategies() -> list[dict]:
    """Return metadata for all registered strategies (id, name, family, description, default_params)."""
    out = []
    for s in _REGISTRY:
        params = dict(s["default_params"])
        # introspect META if available
        try:
            mod = importlib.import_module(s["module"])
            if hasattr(mod, "META") and isinstance(mod.META, dict):
                params = {**mod.META.get("params", {}), **params}
                fam = s["family"] or mod.META.get("family", "Other")
                desc = mod.META.get("description", s["description"])
                name = mod.META.get("name", s["id"])
            else:
                fam, desc, name = s["family"], s["description"], s["name"]
        except Exception:
            fam, desc, name = s["family"], s["description"], s["name"]
        out.append({
            "id": s["id"],
            "name": name,
            "family": fam,
            "description": desc,
            "params": params,
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
