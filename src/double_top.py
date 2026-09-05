"""Double Top / Bottom Breakout — detect two local maxima within 5% separated by ≥10 bars; long on breakout above higher peak."""
import pandas as pd
import numpy as np

META = {
    "name": "Double Top / Bottom Breakout",
    "family": "Pattern",
    "params": {"lookback": 60, "tol": 0.05, "min_sep": 10, "max_holdings": 5, "cost": 0.001, "capital": 1_000_000},
    "description": "Local maxima via (close>prev & close>next); two peaks within 5% separated by ≥10 bars; long on close > higher peak's high; exit below lower peak's low.",
}

def _local_max(close: pd.Series) -> pd.Series:
    prev = close.shift(1)
    nxt = close.shift(-1)
    return (close > prev) & (close > nxt)

def _double_top_breakout(close: pd.Series, high: pd.Series, i: int, lookback: int, tol: float, min_sep: int) -> tuple[bool, float]:
    start = max(0, i - lookback)
    win_close = close.iloc[start:i]
    win_high = high.iloc[start:i]
    if len(win_close) < min_sep + 2:
        return False, float("nan")
    is_peak = _local_max(win_close)
    peak_idx = np.where(is_peak.values)[0]
    if len(peak_idx) < 2:
        return False, float("nan")
    abs_idx = peak_idx + start
    peaks = list(zip(abs_idx, win_close.values[peak_idx]))
    for a in range(len(peaks)):
        for b in range(a + 1, len(peaks)):
            ia, pa = peaks[a]
            ib, pb = peaks[b]
            if abs(ib - ia) < min_sep:
                continue
            hi_p, lo_p = max(pa, pb), min(pa, pb)
            if abs(hi_p - lo_p) / hi_p > tol:
                continue
            hi_peak, lo_peak = (ia, pa) if pa >= pb else (ib, pb)
            lo_peak_idx = ia if pa < pb else ib
            if float(close.iloc[i]) > float(high.iloc[hi_peak]):
                return True, float(high.iloc[lo_peak_idx])
    return False, float("nan")

def backtest(data: dict, lookback=60, tol=0.05, min_sep=10, max_holdings=5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    cash = capital
    holdings = {}
    entry_bar_idx = {}
    stop_low = {}
    trades = []
    eq_curve = []
    bar_index_map = {t: {d: i for i, d in enumerate(df.index)} for t, df in data.items()}
    for d in all_dates:
        for t in list(holdings.keys()):
            if d in data[t].index:
                idx = bar_index_map[t][d]
                triggered = float(data[t].loc[d, "close"]) < stop_low[t]
                if triggered:
                    close = float(data[t].loc[d, "close"])
                    cash += holdings[t] * close * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": close, "shares": holdings[t]})
                    del holdings[t]
                    del entry_bar_idx[t]
                    del stop_low[t]
        if len(holdings) < max_holdings:
            for t, df in data.items():
                if t in holdings or d not in df.index:
                    continue
                idx = bar_index_map[t][d]
                if idx < lookback:
                    continue
                fired, stp = _double_top_breakout(df["close"], df["high"], idx, lookback, tol, min_sep)
                if not fired:
                    continue
                price = float(df.loc[d, "open"])
                slot_cash = cash / max(1, max_holdings - len(holdings))
                shares = int(slot_cash // price)
                if shares > 0 and shares * price * (1 + cost) <= cash:
                    cash -= shares * price * (1 + cost)
                    holdings[t] = shares
                    entry_bar_idx[t] = idx
                    stop_low[t] = stp
                    trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": shares})
                    if len(holdings) >= max_holdings:
                        break
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq