"""Pair backtest — dollar-neutral, Indian costs."""
import pandas as pd
import numpy as np
from .spread import rolling_beta, spread_and_zscore
from .pair_signals import signal
from .metrics import compute_metrics

# Indian costs: 0.03% brokerage per leg + 5bps slippage + STT 0.025% on sell
BROKERAGE = 0.0003
SLIPPAGE = 0.0005
STT = 0.00025

def run_pair(data: dict[str, pd.DataFrame], pair: tuple[str,str], capital: float = 1_000_000,
             entry: float = 2.0, exit: float = 0.3, stop: float = 3.5,
             beta_window: int = 60, z_window: int = 60, notional_pct: float = 0.1) -> tuple[list[dict], pd.DataFrame, dict]:
    t1, t2 = pair
    df1, df2 = data[t1], data[t2]
    # align dates
    idx = df1.index.intersection(df2.index).sort_values()
    if len(idx) < max(beta_window, z_window) + 10:
        raise ValueError("not enough overlapping data")
    s1 = df1.loc[idx, "close"]
    s2 = df2.loc[idx, "close"]
    beta = rolling_beta(s1, s2, beta_window)
    spread, z = spread_and_zscore(s1, s2, beta, z_window)

    position = 0
    entry_z = None
    entry_date = None
    entry_p1 = entry_p2 = 0.0
    shares1 = shares2 = 0
    notional = capital * notional_pct
    trades = []
    equity = capital
    eq_curve = []
    # track cash
    cash = capital

    for i, d in enumerate(idx):
        zi = z.iloc[i]
        bi = beta.iloc[i]
        if pd.isna(zi) or pd.isna(bi):
            eq_curve.append({"date": d, "equity": equity})
            continue
        p1 = float(s1.iloc[i]); p2 = float(s2.iloc[i])

        new_pos, reason = signal(zi, position, entry, exit, stop)

        # exit
        if position != 0 and new_pos == 0:
            # close both legs, compute pnl
            # long spread = long s1, short s2; short spread = short s1, long s2
            if position == 1:
                # long s1, short s2
                pnl = (p1 - entry_p1) * shares1 + (entry_p2 - p2) * shares2
            else:
                pnl = (entry_p1 - p1) * shares1 + (p2 - entry_p2) * shares2
            # costs: brokerage+slippage both legs entry+exit, STT on sells
            cost = notional * (BROKERAGE + SLIPPAGE) * 2  # entry+exit approx
            # add STT on sell side notional
            cost += notional * STT
            pnl -= cost
            # return cash
            cash += pnl
            equity = cash
            trades.append({"pair": pair, "entry_date": entry_date, "exit_date": d, "position": position,
                           "entry_z": entry_z, "exit_z": float(zi), "reason": reason, "pnl": float(pnl),
                           "beta": float(bi)})
            position = 0
            shares1 = shares2 = 0

        # entry
        if position == 0 and new_pos != 0:
            # dollar-neutral: notional per leg equal
            # shares long = notional / price_long, short = notional / price_short
            # need to hold margin for short — simplified: reserve notional
            if cash < notional:  # insufficient
                eq_curve.append({"date": d, "equity": equity})
                continue
            # compute shares
            # for either direction, we allocate notional per leg
            shares1 = int(notional // p1) if p1 > 0 else 0
            shares2 = int(notional // p2) if p2 > 0 else 0
            if shares1 == 0 or shares2 == 0:
                eq_curve.append({"date": d, "equity": equity})
                continue
            position = new_pos
            entry_z = float(zi)
            entry_date = d
            entry_p1, entry_p2 = p1, p2
            # lock notional (margin) — equity unchanged until exit, but we track unrealized
            # for simplicity equity stays cash + unrealized
        # unrealized
        if position != 0:
            if position == 1:
                unreal = (p1 - entry_p1) * shares1 + (entry_p2 - p2) * shares2
            else:
                unreal = (entry_p1 - p1) * shares1 + (p2 - entry_p2) * shares2
            equity = cash + unreal
        eq_curve.append({"date": d, "equity": float(equity)})

    eq_df = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    metrics = compute_metrics(trades, eq_df, capital)
    return trades, eq_df, metrics


def backtest(data: dict[str, pd.DataFrame], capital: float = 1_000_000, pair: tuple[str, str] | None = None,
             entry: float = 2.0, exit: float = 0.3, stop: float = 3.5,
             beta_window: int = 60, z_window: int = 60, notional_pct: float = 0.1) -> tuple[list, pd.DataFrame]:
    """Strategy-library contract: pair backtest. If no pair given, picks first cointegrated pair."""
    from .pairs import find_cointegrated
    if pair is None:
        pairs = find_cointegrated(data)
        if not pairs:
            return [], pd.DataFrame(columns=["equity"])
        # find_cointegrated returns list of dicts with t1, t2 keys
        first = pairs[0]
        pair = (first["t1"], first["t2"])
    trades, eq, _ = run_pair(data, pair, capital=capital, entry=entry, exit=exit, stop=stop,
                              beta_window=beta_window, z_window=z_window, notional_pct=notional_pct)
    return trades, eq


META = {
    "name": "Pairs Trading (Cointegration)",
    "family": "Stat-arb",
    "params": {"capital": 1_000_000, "entry": 2.0, "exit": 0.3, "stop": 3.5, "beta_window": 60, "z_window": 60, "notional_pct": 0.1},
    "description": "Market-neutral pair trade: Engle-Granger cointegration, rolling z-score, dollar-neutral sizing, Indian costs.",
}
