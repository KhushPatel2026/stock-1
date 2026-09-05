"""Real options chain via yfinance, with BS synthetic fallback for tickers that
have no listed options (typical for .NS Indian stocks).
"""
from __future__ import annotations
import math
import pandas as pd
import yfinance as yf

from src.options import covered_call_backtest


def _has_real_chain(ticker: str) -> bool:
    try:
        return bool(yf.Ticker(ticker).options)
    except Exception:
        return False


def covered_call_real(ticker: str, capital: float = 1_000_000, otm: float = 0.05, dte: int = 30, r: float = 0.06) -> tuple[list, pd.DataFrame]:
    """Covered call using real yfinance option chain when available.

    If `ticker.options` is empty (typical for Indian .NS stocks), falls back to
    `src.options.covered_call_backtest` which uses a Black-Scholes synthetic chain.
    """
    if not _has_real_chain(ticker):
        # need a per-ticker data dict for the BS fallback
        from src.data import fetch
        df = fetch(ticker, period="2y")
        return covered_call_backtest({ticker: df}, capital=capital, otm=otm, dte=dte, r=r)

    # Real chain path: build a per-day simulation using listed expiries closest to dte.
    from src.data import fetch
    df = fetch(ticker, period="2y")
    data = {ticker: df}
    all_dates = sorted(df.index)
    t = yf.Ticker(ticker)
    expiries = list(t.options)
    if not expiries:
        return covered_call_backtest(data, capital=capital, otm=otm, dte=dte, r=r)

    cash = capital
    holdings = 0
    first = all_dates[0]
    price0 = float(df.loc[first, "close"])
    shares = int(capital // price0)
    if shares > 0:
        holdings = shares
        cash -= shares * price0 * (1 + 0.001)
    trades = [{"ticker": ticker, "date": first, "action": "buy", "price": price0, "shares": shares}]
    pending: list[dict] = []
    equity_curve = []

    # pick an expiry ~dte days out, refresh weekly
    months_idx = pd.Series(all_dates).dt.to_period("M").unique()
    month_ends = []
    for p in months_idx:
        ds = [d for d in all_dates if pd.Period(d, freq="M") == p]
        if ds:
            month_ends.append(max(ds))

    chosen_expiry = expiries[0]
    for d in all_dates:
        # pick expiry nearest to ~dte days from d
        target_ts = pd.Timestamp(d) + pd.Timedelta(days=dte)
        best = min(expiries, key=lambda e: abs(pd.Timestamp(e) - target_ts))
        chosen_expiry = best

        for c in pending[:]:
            if pd.Timestamp(c["expiry"]) <= d:
                p = float(df.loc[d, "close"]) if d in df.index else c["strike"]
                if p > c["strike"]:
                    cash += c["shares"] * c["strike"]
                    holdings -= c["shares"]
                    trades.append({"ticker": ticker, "date": d, "action": "call_exercised", "price": c["strike"], "shares": c["shares"]})
                pending.remove(c)

        if d in month_ends and holdings > 0 and d in df.index:
            S = float(df.loc[d, "close"])
            try:
                chain = t.option_chain(chosen_expiry)
                calls = chain.calls
                # find strike ~ otm% OTM
                target_K = S * (1 + otm)
                if not calls.empty and "strike" in calls.columns:
                    idx = (calls["strike"] - target_K).abs().idxmin()
                    bid = float(calls.loc[idx, "bid"]) if calls.loc[idx, "bid"] not in (None, float("nan")) else 0.0
                    ask = float(calls.loc[idx, "ask"]) if calls.loc[idx, "ask"] not in (None, float("nan")) else 0.0
                    premium = max((bid + ask) / 2, bid)
                    K = float(calls.loc[idx, "strike"])
                else:
                    premium = 0.0
                    K = S * (1 + otm)
            except Exception:
                premium = 0.0
                K = S * (1 + otm)
            cash += premium * holdings * (1 - 0.001)
            pending.append({"expiry": chosen_expiry, "strike": K, "premium": premium, "shares": holdings})
            trades.append({"ticker": ticker, "date": d, "action": "sell_call", "strike": K, "premium": premium, "shares": holdings})

        val = cash + holdings * (float(df.loc[d, "close"]) if d in df.index else 0)
        equity_curve.append({"date": d, "equity": float(val)})

    eq = pd.DataFrame(equity_curve).set_index("date") if equity_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


def backtest(data: dict, capital: float = 1_000_000, otm: float = 0.05, dte: int = 30, r: float = 0.06) -> tuple[list, pd.DataFrame]:
    """Strategy-library contract alias. Picks the first ticker."""
    tickers = list(data.keys())
    if not tickers:
        raise ValueError("no data")
    return covered_call_real(tickers[0], capital=capital, otm=otm, dte=dte, r=r)


META = {
    "name": "Covered Call (Real Chain)",
    "family": "Options",
    "params": {"capital": 1_000_000, "otm": 0.05, "dte": 30, "r": 0.06},
    "description": "Covered call using real yfinance option chains; BS synthetic fallback when unavailable (.NS).",
}
