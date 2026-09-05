"""Beta-hedged single-stock — long stock, short Nifty beta * notional."""
import pandas as pd
import numpy as np

def rolling_beta(stock_rets: pd.Series, nifty_rets: pd.Series, window: int = 60) -> pd.Series:
    out=pd.Series(np.nan, index=stock_rets.index, dtype=float)
    for i in range(window-1, len(stock_rets)):
        s=stock_rets.iloc[i-window+1:i+1]
        n=nifty_rets.iloc[i-window+1:i+1]
        c=np.cov(s, n)[0,1] if len(s)==window else np.nan
        v=np.var(n) if len(n)==window else np.nan
        out.iloc[i]= c/v if v and v!=0 else 1.0
    return out

def backtest(data: dict[str, pd.DataFrame], stock: str = None, nifty_proxy: pd.Series = None, lookback: int = 60) -> tuple[list[dict], pd.DataFrame, pd.Series]:
    tickers=list(data.keys())
    if not tickers:
        raise ValueError("no data")
    if stock is None:
        stock=tickers[0]
    if stock not in data:
        raise ValueError(f"stock {stock} not in data")
    all_dates=sorted(set().union(*(set(df.index) for df in data.values())))
    # nifty proxy: equal-weight avg close
    if nifty_proxy is None:
        df_all=pd.concat([data[t]["close"].rename(t) for t in tickers], axis=1).mean(axis=1)
        nifty_proxy=df_all
    else:
        nifty_proxy=nifty_proxy.reindex(all_dates).ffill()
    stock_rets=data[stock]["close"].pct_change()
    nifty_rets=nifty_proxy.pct_change()
    beta=rolling_beta(stock_rets.reindex(all_dates), nifty_rets.reindex(all_dates), lookback)
    trades=[]
    cash=1_000_000
    # hold stock long + short Nifty beta notional, rebalance daily beta
    shares_stock=0
    # init
    first=all_dates[lookback]
    price=float(data[stock].loc[first,"close"])
    notional=1_000_000*0.1
    shares_stock=int(notional//price)
    cash-=shares_stock*price
    trades.append({"ticker":stock,"date":first,"action":"buy","price":price,"shares":shares_stock})
    equity_curve=[]
    for d in all_dates[lookback:]:
        b=float(beta.loc[d]) if not pd.isna(beta.loc[d]) else 1.0
        # target hedge: short b* notional Nifty
        # pnl = stock leg + hedge leg (Nifty moves against)
        # we simulate hedge as synthetic short: pnl_hedge = -b * (nifty_ret) * notional
        # equity = cash + stock value + hedge cum pnl
        # simplify: track hedge pnl cum
        # we compute equity as cash + stock value + hedge_pnl cum
        # hedge_pnl cum via loop
        pass
    # simpler loop with hedge pnl
    hedge_pnl=0
    prev_nifty=float(nifty_proxy.loc[all_dates[lookback]])
    cash_after_entry=cash
    equity_curve=[]
    cum_hedge=0
    for d in all_dates[lookback:]:
        b=float(beta.loc[d]) if not pd.isna(beta.loc[d]) else 1.0
        cur_nifty=float(nifty_proxy.loc[d])
        prev=prev_nifty
        nifty_ret=(cur_nifty-prev)/prev if prev!=0 else 0
        # hedge notional = b * shares_stock*price_entry? use initial notional
        hedge_notional=shares_stock*float(data[stock].loc[all_dates[lookback],"close"])
        cum_hedge+= -b * hedge_notional * nifty_ret
        prev_nifty=cur_nifty
        stock_val=shares_stock*float(data[stock].loc[d,"close"]) if d in data[stock].index else 0
        equity=cash_after_entry + stock_val + cum_hedge
        equity_curve.append({"date":d,"equity":float(equity)})
    eq=pd.DataFrame(equity_curve).set_index("date") if equity_curve else pd.DataFrame(columns=["equity"])
    return trades, eq, beta


def backtest_returns_only(data: dict, stock: str = "RELIANCE.NS", **kwargs) -> tuple[list, pd.DataFrame]:
    """Strategy-library contract: drop the beta series from the tuple."""
    trades, eq, _ = backtest(data, stock=stock, **kwargs)
    return trades, eq


META = {
    "name": "Beta-Hedged Single Stock",
    "family": "Hedge",
    "params": {"stock": "RELIANCE.NS"},
    "description": "Long stock + short beta × Nifty (synthetic equal-weight proxy).",
}
