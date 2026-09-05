"""Actionable trade plan per ticker — entry, stop-loss, target, timeframe + insight.

Levels use the house convention (FEAT-001): stop = 2.5 x 14d ATR, target = 4 x ATR
(~1.6R). Timeframe comes from the dominant voter family. Insight is a plain-English
summary of the vote — numbers first, no hype.
"""
from __future__ import annotations
import pandas as pd
import numpy as np

from .indicators import atr

SL_ATR_MULT = 2.5
TP_ATR_MULT = 4.0

# family -> (timeframe label, holding detail)
FAMILY_TIMEFRAME: dict[str, tuple[str, str]] = {
    "Intraday": ("Intraday", "Exit by 3:20 PM IST the same day"),
    "MR": ("Short-term swing", "3–10 trading days"),
    "Volatility": ("Short-term swing", "3–10 trading days"),
    "Volume": ("Short-term swing", "3–10 trading days"),
    "Pattern": ("Short-term swing", "3–10 trading days"),
    "Trend": ("Swing", "2–8 weeks"),
    "Momentum": ("Swing", "2–8 weeks"),
    "Cross-sect": ("Swing", "2–8 weeks"),
}
_DEFAULT_TF = ("Positional", "1–3 months")


def _dominant_timeframe(voters: list[tuple[str, float]], families: dict[str, str]) -> tuple[str, str]:
    buckets: dict[str, float] = {}
    for sid, w in voters:
        label = FAMILY_TIMEFRAME.get(families.get(sid, ""), _DEFAULT_TF)[0]
        buckets[label] = buckets.get(label, 0.0) + (w or 0)
    if not buckets:
        return _DEFAULT_TF
    top = max(buckets, key=lambda k: buckets[k])
    for _label, detail in list(FAMILY_TIMEFRAME.values()) + [_DEFAULT_TF]:
        if _label == top:
            return top, detail
    return _DEFAULT_TF


def build_plan(
    ticker: str,
    df: pd.DataFrame,
    decision: str,
    confidence: float,
    long_voters: list[tuple[str, float]],
    short_voters: list[tuple[str, float]],
    families: dict[str, str] | None = None,
    names: dict[str, str] | None = None,
    entry: float | None = None,
    entry_label: str = "",
) -> dict:
    """Build the full trade card for one ticker. Never raises on thin data.

    `entry`: live price override. Levels/SL/TP anchor to it; ATR/SMA stay on daily bars.
    """
    families = families or {}
    names = names or {}
    close = df["close"].astype(float)
    last_close = float(close.iloc[-1])
    price = float(entry) if entry else last_close
    live = bool(entry)
    a = float(atr(df, 14).iloc[-1]) if len(df) >= 20 else 0.0
    if not np.isfinite(a) or a <= 0:
        a = price * 0.02  # ponytail: 2% fallback when ATR unavailable
    sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
    prev = float(close.iloc[-2]) if len(close) >= 2 else price
    day_chg = (price / prev - 1) * 100 if prev else 0.0
    price_bit = f"live ₹{price:,.2f}" if live else f"₹{price:,.2f}"

    if decision == "BUY":
        sl, tp = price - SL_ATR_MULT * a, price + TP_ATR_MULT * a
        voters = long_voters
    elif decision == "SELL":
        sl, tp = price + SL_ATR_MULT * a, price - TP_ATR_MULT * a
        voters = short_voters
    else:  # HOLD — show the watch band, no direction
        sl, tp = price - SL_ATR_MULT * a, price + TP_ATR_MULT * a
        voters = sorted(long_voters + short_voters, key=lambda x: -x[1])

    rr = abs(tp - price) / max(abs(price - sl), 1e-9)
    tf, tf_detail = _dominant_timeframe(voters, families)
    leaders = [names.get(sid, sid) for sid, _ in voters[:2]]
    w_total = sum(w for _, w in long_voters) + sum(w for _, w in short_voters) + 1e-9
    w_side = sum(w for _, w in voters) / w_total * 100
    n_total = len(long_voters) + len(short_voters)
    if decision == "HOLD":
        vote_bit = (f"split {len(long_voters)} long vs {len(short_voters)} short — "
                    f"no consensus")
    else:
        vote_bit = (f"{len(voters)}/{n_total} strategies vote {decision} "
                    f"with {w_side:.0f}% of OOS-Sharpe weight")
    lead_bit = f", led by {' + '.join(leaders)}" if leaders else ""

    trend_bit = (
        "above" if sma200 is not None and price > sma200
        else "below" if sma200 is not None
        else "n/a vs"
    )
    sma_bit = f", {trend_bit} 200DMA" if sma200 is not None else ""
    lead_bit = f", led by {' + '.join(leaders)}" if leaders else ""
    if decision == "BUY":
        action = f"Plan: buy near ₹{price:,.2f}{' (live)' if live else ''}, stop ₹{sl:,.2f} ({(sl / price - 1) * 100:+.1f}%), target ₹{tp:,.2f} ({(tp / price - 1) * 100:+.1f}%)."
    elif decision == "SELL":
        action = f"Plan: sell near ₹{price:,.2f}{' (live)' if live else ''}, stop ₹{sl:,.2f} ({(sl / price - 1) * 100:+.1f}%), target ₹{tp:,.2f} ({(tp / price - 1) * 100:+.1f}%)."
    else:
        action = f"No edge: wait outside ₹{sl:,.2f}–₹{tp:,.2f}. A close beyond the band with volume is the trigger."
    insight = (
        f"{vote_bit}{lead_bit}. "
        f"{ticker} {price_bit} ({day_chg:+.1f}% vs prev close){sma_bit}, 14d ATR ₹{a:,.2f} ({a / price * 100:.1f}%). "
        f"{action} {tf} holding ({tf_detail.lower()})."
    )
    return {
        "ticker": ticker,
        "decision": decision,
        "confidence": round(float(confidence), 1),
        "entry": round(price, 2),
        "stop_loss": round(sl, 2),
        "target": round(tp, 2),
        "stop_pct": round((sl / price - 1) * 100, 2),
        "target_pct": round((tp / price - 1) * 100, 2),
        "risk_reward": round(float(rr), 2),
        "timeframe": tf,
        "timeframe_detail": tf_detail,
        "price": round(price, 2),
        "atr": round(a, 2),
        "atr_pct": round(a / price * 100, 2),
        "day_change_pct": round(day_chg, 2),
        "above_sma200": None if sma200 is None else bool(price > sma200),
        "leaders": leaders,
        "voter_weight_pct": round(w_side, 1),
        "insight": insight,
        "live_entry": live,
        "entry_label": entry_label,
        "note": "Levels auto-computed from 14d ATR (2.5x stop / 4x target). Risk guide, not financial advice — validate and paper-trade first.",
        "as_of": str(df.index[-1].date()),
    }
