"""Distance-method pairs (Gatev-Goetzmann-Rouwenhorst) — no cointegration test.

Formation (252d): normalize prices, pick same-sector pair with min sum-of-squared-
deviations. Trading: spread z-score (60d) — enter at ±entry_z, exit at ±exit_z,
stop at ±stop_z. Dollar-neutral, Indian costs like src/pair_portfolio.py.
"""
import pandas as pd
import numpy as np
from .universe import same_sector_pairs

META = {
    "name": "distance_pairs",
    "family": "Stat-arb",
    "params": {"capital": 1_000_000, "formation": 252, "window": 60, "entry_z": 2.0, "exit_z": 0.5, "stop_z": 3.5, "cost": 0.001},
    "description": "Min-SSD same-sector pair, z-score traded, dollar-neutral.",
}


def _formation_ssd(a: pd.Series, b: pd.Series) -> float:
    an = a / a.iloc[0]
    bn = b / b.iloc[0]
    return float(((an - bn) ** 2).sum())


def backtest(data: dict, formation=252, window=60, entry_z=2.0, exit_z=0.5,
             stop_z=3.5, cost=0.001, capital=1_000_000) -> tuple[list, pd.DataFrame]:
    tickers = [t for t in data if len(data[t]) >= formation + window + 5]
    if len(tickers) < 2:
        return [], pd.DataFrame(columns=["equity"])
    all_dates = sorted(set().union(*(set(data[t].index) for t in tickers)))
    pairs = same_sector_pairs(tickers)
    if not pairs:
        pairs = [(tickers[i], tickers[i + 1]) for i in range(0, len(tickers) - 1, 2)]
    # formation on first `formation` common bars
    common = [d for d in all_dates if all(d in data[t].index for t in tickers)]
    fdates = common[:formation]
    closes = {t: data[t].loc[fdates, "close"] for t in tickers}
    best, best_ssd = pairs[0], np.inf
    for a, b in pairs:
        try:
            ssd = _formation_ssd(closes[a], closes[b])
        except Exception:
            continue
        if ssd < best_ssd:
            best, best_ssd = (a, b), ssd
    a, b = best
    # rolling hedge ratio + spread on the trade window
    tdates = [d for d in common[formation:] if d in data[a].index and d in data[b].index]
    if len(tdates) < window + 5:
        return [], pd.DataFrame(columns=["equity"])
    pa = data[a].loc[tdates, "close"].astype(float)
    pb = data[b].loc[tdates, "close"].astype(float)
    beta = (pa.rolling(window).cov(pb) / pb.rolling(window).var()).bfill()
    spread = pa - beta * pb
    z = (spread - spread.rolling(window).mean()) / spread.rolling(window).std()
    cash, pos, trades, eq_curve = capital, 0, [], []
    qty = 0
    for i, d in enumerate(tdates):
        zi = float(z.iloc[i]) if not pd.isna(z.iloc[i]) else 0.0
        pxa, pxb = float(pa.iloc[i]), float(pb.iloc[i])
        hedge = float(beta.iloc[i]) if not pd.isna(beta.iloc[i]) else 1.0
        if pos == 0 and abs(zi) >= entry_z:
            # long spread if z<0 (long a, short hedge*b), else flip
            direction = -np.sign(zi)
            na = int((capital * 0.5 / pxa // 1))
            nb = int((capital * 0.5 * abs(hedge) / pxb // 1))
            if na and nb:
                pos = direction
                qty = (na, nb)
                cash -= direction * na * pxa * (1 + cost)  # long leg pays, short leg receives
                cash += direction * nb * pxb * (1 - cost)
                trades.append({"ticker": f"{a}/{b}", "date": d, "action": "open", "shares": na, "price": pxa, "z": zi})
        elif pos != 0 and (abs(zi) <= exit_z or abs(zi) >= stop_z):
            na, nb = qty
            cash += pos * na * pxa * (1 - cost)
            cash -= pos * nb * pxb * (1 + cost)
            trades.append({"ticker": f"{a}/{b}", "date": d, "action": "close", "shares": na, "price": pxa, "z": zi})
            pos = 0
        mkt = pos * (qty[0] * pxa - qty[1] * pxb) if pos != 0 else 0.0
        eq_curve.append({"date": d, "equity": float(cash + mkt)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq
