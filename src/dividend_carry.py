"""Dividend yield carry — long top quartile by yield, monthly rebalance.
ponytail: static yield map, refresh manually from NSE."""
import pandas as pd

YIELDS = {
    "RELIANCE.NS": 0.35, "TCS.NS": 1.30, "HDFCBANK.NS": 1.10, "INFY.NS": 2.20,
    "ICICIBANK.NS": 0.80, "HINDUNILVR.NS": 1.50, "SBIN.NS": 1.80, "ITC.NS": 3.00,
    "BHARTIARTL.NS": 0.50, "KOTAKBANK.NS": 0.10, "LT.NS": 0.85, "AXISBANK.NS": 0.40,
    "ASIANPAINT.NS": 1.10, "MARUTI.NS": 1.20, "BAJFINANCE.NS": 0.30, "WIPRO.NS": 2.10,
    "HCLTECH.NS": 3.50, "SUNPHARMA.NS": 1.00, "TITAN.NS": 0.30, "ULTRACEMCO.NS": 0.40,
    "NESTLEIND.NS": 0.80, "POWERGRID.NS": 4.50, "NTPC.NS": 3.50, "JSWSTEEL.NS": 1.50,
    "TATASTEEL.NS": 2.30, "TECHM.NS": 2.80, "INDUSINDBK.NS": 1.20, "ADANIENT.NS": 0.05,
    "ADANIPORTS.NS": 0.60, "BAJAJFINSV.NS": 0.05, "COALINDIA.NS": 7.00, "HDFCLIFE.NS": 0.30,
    "SBILIFE.NS": 0.20, "BRITANNIA.NS": 1.50, "EICHERMOT.NS": 1.00, "GRASIM.NS": 0.70,
    "HEROMOTOCO.NS": 2.50, "CIPLA.NS": 0.80, "DRREDDY.NS": 0.70, "BPCL.NS": 5.50,
    "APOLLOHOSP.NS": 0.25, "DIVISLAB.NS": 0.80, "BAJAJ-AUTO.NS": 2.50, "TATACONSUM.NS": 0.85,
    "TATAMOTORS.NS": 0.30, "ONGC.NS": 6.50, "HINDALCO.NS": 1.50, "LTIM.NS": 1.30,
    "M&M.NS": 0.85, "SHRIRAMFIN.NS": 0.10,
}

def backtest(data: dict, top_q=0.25, cost=0.001) -> tuple[list, pd.DataFrame]:
    elig = [t for t in data if YIELDS.get(t, 0) > 0]
    elig.sort(key=lambda t: -YIELDS[t])
    n = max(1, int(len(elig) * top_q))
    top = set(elig[:n])
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    months = pd.Series(all_dates).dt.to_period("M").unique()
    month_ends = []
    for p in months:
        ds = [d for d in all_dates if pd.Period(d, freq="M") == p]
        if ds:
            month_ends.append(max(ds))
    cash = 1_000_000
    holdings = {}
    trades = []
    eq_curve = []
    for d in all_dates:
        if d in month_ends:
            for t in list(holdings.keys()):
                if t not in top and d in data[t].index:
                    price = float(data[t].loc[d, "close"])
                    cash += holdings[t] * price * (1 - cost)
                    trades.append({"ticker": t, "date": d, "action": "sell", "price": price, "shares": holdings[t]})
                    del holdings[t]
            if top:
                cur_val = sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
                port = cur_val + cash
                slot = max(n, len(holdings) + len(top))
                notional = port / slot
                for t in top:
                    if t in holdings or d not in data[t].index:
                        continue
                    price = float(data[t].loc[d, "close"])
                    shares = int(notional // price)
                    if shares > 0:
                        cash -= shares * price * (1 + cost)
                        holdings[t] = shares
                        trades.append({"ticker": t, "date": d, "action": "buy", "price": price, "shares": shares})
        val = cash + sum(holdings[t] * float(data[t].loc[d, "close"]) for t in holdings if d in data[t].index)
        eq_curve.append({"date": d, "equity": float(val)})
    eq = pd.DataFrame(eq_curve).set_index("date") if eq_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "Dividend Yield Carry",
    "family": "Carry",
    "params": {"top_n": 5, "cost": 0.001},
    "description": "Top quartile by static yield, monthly rebalance.",
}
