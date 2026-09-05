"""Intraday strategies — 60m bars (single-name) + close-to-open drift (daily).

Each strategy uses `data: dict[str, pd.DataFrame]` (one ticker). Intraday strategies
square off at the last bar of each day; overnight drift holds from today's close
to tomorrow's open.
"""
from __future__ import annotations
import pandas as pd
import numpy as np


# ponytail: single shared intraday loop — exit/entry signal Series per ticker.
# All four strategies differ only in how they compute entry/exit signals.
def _last_bar_per_day(df: pd.DataFrame) -> pd.Series:
    if len(df) == 0:
        return pd.Series(dtype=bool, index=df.index)
    dates = np.array([str(d) for d in df.index.date])
    is_last = pd.Series(True, index=df.index)
    if len(df) > 1:
        is_last.iloc[:-1] = dates[:-1] != dates[1:]
    return is_last


def _run_loop(
    data: dict,
    entry_sig: dict,
    exit_sig: dict,
    top_n: int = 1,
    cost: float = 0.0005,
    capital: float = 1_000_000,
) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings: dict[str, int] = {}
    trades: list[dict] = []
    eq_curve: list[dict] = []
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index and len(exit_sig[t].loc[:d]) and bool(exit_sig[t].loc[:d].iloc[-1]):
                price = float(data[t].loc[d, "close"])
                cash += holdings[t] * price * (1 - cost)
                trades.append({"ticker": t, "date": d, "action": "sell", "price": price, "shares": holdings[t]})
                del holdings[t]
        if len(holdings) < top_n:
            for t, df in data.items():
                if t in holdings or d not in df.index:
                    continue
                if len(entry_sig[t].loc[:d]) and bool(entry_sig[t].loc[:d].iloc[-1]):
                    price = float(data[t].loc[d, "close"])
                    slot_cash = cash / max(1, top_n - len(holdings))
                    shares = int(slot_cash // price)
                    if shares > 0 and shares * price * (1 + cost) <= cash:
                        cash -= shares * price * (1 + cost)
                        holdings[t] = shares
                        trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": shares})
                        if len(holdings) >= top_n:
                            break
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


# ---------- 1. Opening Range Breakout ----------

META_ORB = {
    "name": "Opening Range Breakout",
    "family": "Intraday",
    "params": {"lookback_bars": 6, "top_n": 1, "cost": 0.0005},
    "description": "Long when close > opening-range high; square off at EOD. Single-name 60m.",
}


def _orb_signals(df: pd.DataFrame, lookback_bars: int) -> tuple[pd.Series, pd.Series]:
    df = df.copy()
    df["_d"] = df.index.date
    or_high = df.groupby("_d")["high"].transform(lambda s: s.iloc[:lookback_bars].max())
    entry = df["close"] > or_high
    is_last = _last_bar_per_day(df)
    return entry, is_last


def backtest_orb(data: dict, lookback_bars: int = 6, top_n: int = 1, cost: float = 0.0005) -> tuple[list, pd.DataFrame]:
    entry_sig, exit_sig = {}, {}
    for t, df in data.items():
        e, x = _orb_signals(df, lookback_bars)
        entry_sig[t], exit_sig[t] = e, x
    return _run_loop(data, entry_sig, exit_sig, top_n=top_n, cost=cost)


# ---------- 2. VWAP Reversion ----------

META_VWAP = {
    "name": "VWAP Reversion",
    "family": "Intraday",
    "params": {"std_mult": 1.5, "top_n": 1, "cost": 0.0005},
    "description": "Long when close < VWAP - std_mult * std(close-VWAP) (today). Exit at VWAP; square off at EOD.",
}


def _vwap_signals(df: pd.DataFrame, std_mult: float) -> tuple[pd.Series, pd.Series]:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    pvol = tp * df["volume"]
    df = df.copy()
    df["_pvol"] = pvol
    df["_d"] = df.index.date
    cum_pvol = df.groupby("_d")["_pvol"].cumsum()
    cum_vol = df.groupby("_d")["volume"].cumsum()
    vwap = cum_pvol / cum_vol.replace(0, np.nan)
    dev = df["close"] - vwap
    df["_dev"] = dev
    # ponytail: expanding std within the day (data so far); sample std (ddof=1) to avoid div-by-1 == 0.
    std = df.groupby("_d")["_dev"].transform(lambda s: s.expanding().std(ddof=1))
    entry = df["close"] < (vwap - std_mult * std)
    exit_ = (df["close"] >= vwap) | _last_bar_per_day(df)
    return entry, exit_


def backtest_vwap(data: dict, std_mult: float = 1.5, top_n: int = 1, cost: float = 0.0005) -> tuple[list, pd.DataFrame]:
    entry_sig, exit_sig = {}, {}
    for t, df in data.items():
        e, x = _vwap_signals(df, std_mult)
        entry_sig[t], exit_sig[t] = e, x
    return _run_loop(data, entry_sig, exit_sig, top_n=top_n, cost=cost)


# ---------- 3. Intraday Momentum ----------

META_MOM = {
    "name": "Intraday Momentum",
    "family": "Intraday",
    "params": {"sma_bars": 20, "vol_mult": 1.2, "top_n": 1, "cost": 0.0005},
    "description": "Long when close > SMA(close, sma_bars) AND volume > vol_mult * SMA(volume, sma_bars). Exit at EOD.",
}


def _mom_signals(df: pd.DataFrame, sma_bars: int, vol_mult: float) -> tuple[pd.Series, pd.Series]:
    close_sma = df["close"].rolling(sma_bars).mean()
    vol_sma = df["volume"].rolling(sma_bars).mean()
    entry = (df["close"] > close_sma) & (df["volume"] > vol_mult * vol_sma)
    is_last = _last_bar_per_day(df)
    return entry, is_last


def backtest_mom(data: dict, sma_bars: int = 20, vol_mult: float = 1.2, top_n: int = 1, cost: float = 0.0005) -> tuple[list, pd.DataFrame]:
    entry_sig, exit_sig = {}, {}
    for t, df in data.items():
        e, x = _mom_signals(df, sma_bars, vol_mult)
        entry_sig[t], exit_sig[t] = e, x
    return _run_loop(data, entry_sig, exit_sig, top_n=top_n, cost=cost)


# ---------- 4. Overnight Drift (daily bars) ----------

META_OVERNIGHT = {
    "name": "Overnight Drift (Close-to-Open)",
    "family": "Intraday",
    "params": {"top_n": 1, "cost": 0.0005},
    "description": "Buy at today's close when close > yesterday's close; sell at tomorrow's open.",
}


def backtest_overnight(data: dict, top_n: int = 1, cost: float = 0.0005) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = 1_000_000
    holdings: dict[str, int] = {}
    trades: list[dict] = []
    eq_curve: list[dict] = []
    sig = {t: (df["close"] > df["close"].shift(1)).fillna(False) for t, df in data.items()}
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                open_price = float(data[t].loc[d, "open"])
                cash += holdings[t] * open_price * (1 - cost)
                trades.append({"ticker": t, "date": d, "action": "sell", "price": open_price, "shares": holdings[t]})
                del holdings[t]
        if len(holdings) < top_n:
            for t, df in data.items():
                if t in holdings or d not in df.index:
                    continue
                if bool(sig[t].loc[:d].iloc[-1]):
                    price = float(df.loc[d, "close"])
                    slot_cash = cash / max(1, top_n - len(holdings))
                    shares = int(slot_cash // price)
                    if shares > 0 and shares * price * (1 + cost) <= cash:
                        cash -= shares * price * (1 + cost)
                        holdings[t] = shares
                        trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": shares})
                        if len(holdings) >= top_n:
                            break
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


# ---------- dispatcher ----------

_FNS = {
    "orb": backtest_orb,
    "vwap": backtest_vwap,
    "mom": backtest_mom,
    "overnight": backtest_overnight,
}


def backtest(data: dict, strategy: str = "orb", **kwargs) -> tuple[list, pd.DataFrame]:
    if strategy not in _FNS:
        raise ValueError(f"unknown intraday strategy: {strategy}")
    return _FNS[strategy](data, **kwargs)


META = META_ORB