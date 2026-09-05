"""ML overlay — GBM combining factors, walk-forward, no lookahead."""
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

def make_features(data: dict[str, pd.DataFrame], date) -> pd.DataFrame:
    rows=[]
    for t, df in data.items():
        if date not in df.index: continue
        idx=df.index.get_loc(date)
        if idx < 252: continue
        close=df["close"]
        mom=float(close.iloc[idx]/close.iloc[idx-252]-1)
        # value proxy
        sma200=close.rolling(200).mean().iloc[idx]
        val=float((sma200-close.iloc[idx])/close.iloc[idx]) if not pd.isna(sma200) else 0
        rets=close.pct_change().iloc[idx-60+1:idx+1]
        vol=float(rets.std()) if len(rets)==60 else 0
        lowvol=1/(vol+1e-6)
        # gap_z
        gap=df["open"].iloc[idx]-close.iloc[idx-1] if idx>0 else 0
        # label 5d forward
        label=None
        if idx+5 < len(df):
            label=1 if float(close.iloc[idx+5]/close.iloc[idx]-1) >0 else 0
        rows.append({"ticker":t,"momentum":mom,"value":val,"lowvol":lowvol,"gap":float(gap),"label":label})
    return pd.DataFrame(rows)

def train_predict(data: dict[str, pd.DataFrame], train: int = 252, test: int = 60) -> tuple[HistGradientBoostingClassifier, pd.DataFrame, pd.DataFrame]:
    all_dates=sorted(set().union(*(set(df.index) for df in data.values())))
    # build feature history for all dates where label exists
    # walk-forward: train 252d, test 60d rolling
    folds=[]
    i=train
    all_preds=[]
    while i+test < len(all_dates):
        train_dates=all_dates[i-train:i]
        test_dates=all_dates[i:i+test]
        # build train set
        X_train=[]; y_train=[]
        for d in train_dates:
            df=make_features(data, d)
            if df.empty or "label" not in df.columns: continue
            df=df.dropna(subset=["label"])
            if df.empty: continue
            X_train.append(df[["momentum","value","lowvol","gap"]].values)
            y_train.append(df["label"].values)
        if not X_train:
            i+=test; continue
        X_train=np.vstack(X_train); y_train=np.concatenate(y_train)
        # filter nan
        mask=~np.isnan(X_train).any(axis=1)
        X_train, y_train=X_train[mask], y_train[mask]
        if len(np.unique(y_train))<2:
            i+=test; continue
        clf=HistGradientBoostingClassifier(max_depth=3, max_iter=50, random_state=0)
        clf.fit(X_train, y_train)
        # predict test
        for d in test_dates:
            df=make_features(data, d)
            if df.empty: continue
            X=df[["momentum","value","lowvol","gap"]].values
            mask2=~np.isnan(X).any(axis=1)
            if not mask2.any(): continue
            probs=clf.predict_proba(X[mask2])[:,1]
            tickers=df.loc[mask2,"ticker"].values
            for t,p in zip(tickers, probs):
                all_preds.append({"date":d,"ticker":t,"prob":float(p)})
        i+=test
    preds=pd.DataFrame(all_preds) if all_preds else pd.DataFrame(columns=["date","ticker","prob"])
    # backtest preds: long top 3 prob per month-end
    if not preds.empty:
        preds["date"]=pd.to_datetime(preds["date"])
        # monthly backtest
        equity=[]
        cash=1_000_000; holdings={}
        months=preds["date"].dt.to_period("M").unique() if not preds.empty else []
        # map date->top tickers
        for p in months:
            ds=preds[preds["date"].dt.to_period("M")==p]
            if ds.empty: continue
            last=max(ds["date"])
            top=ds[ds["date"]==last].sort_values("prob", ascending=False).head(3)["ticker"].tolist()
            # close all, buy top
            # need prices at last date
            for t in list(holdings.keys()):
                if last in data[t].index:
                    price=float(data[t].loc[last,"close"])
                    cash+=holdings[t]*price*(1-0.001)
                del holdings[t]
            per=cash/ max(1,len(top)) if top else cash
            # need to recompute cash after sells is done, so use remaining cash
            # simplified: equal notional
            for t in top:
                if last not in data[t].index: continue
                price=float(data[t].loc[last,"close"])
                shares=int((per*0.2)//price) if price>0 else 0 # 20% per name
                if shares==0: continue
                cash-=shares*price*(1+0.001)
                holdings[t]=holdings.get(t,0)+shares
        # equity curve from preds dates
        all_dates2=sorted(preds["date"].unique()) if not preds.empty else []
        # build cash+holdings value over time (approx)
        eq=pd.DataFrame({"date":all_dates2,"equity":cash + sum(0 for _ in holdings)}) # placeholder
        # actual equity from holdings not tracked intraday; return preds
        eq=preds
    else:
        eq=pd.DataFrame()
    # return model of last fold, preds
    return clf if 'clf' in locals() else None, preds, preds

def backtest(data: dict[str, pd.DataFrame], top_n: int = 3, capital: float = 1_000_000) -> tuple[list[dict], pd.DataFrame]:
    _, preds, _ = train_predict(data)
    if preds.empty:
        return [], pd.DataFrame(columns=["equity"])
    # build equity from preds: monthly rebalance top_n probs
    all_dates=sorted(set().union(*(set(df.index) for df in data.values())))
    # group preds by month
    preds["date"]=pd.to_datetime(preds["date"])
    months=preds["date"].dt.to_period("M").unique()
    trades=[]; cash=capital; holdings={}
    equity_curve=[]
    # map month -> top
    month_tops={}
    for p in months:
        ds=preds[preds["date"].dt.to_period("M")==p]
        if ds.empty: continue
        last=max(ds["date"])
        top=ds[ds["date"]==last].sort_values("prob", ascending=False).head(top_n)["ticker"].tolist()
        month_tops[last]=top
    for d in all_dates:
        if d in month_tops:
            # close
            for t in list(holdings.keys()):
                if d in data[t].index:
                    price=float(data[t].loc[d,"close"])
                    cash+=holdings[t]*price*(1-0.001)
                    trades.append({"ticker":t,"date":d,"action":"sell","price":price})
                del holdings[t]
            for t in month_tops[d]:
                if d not in data[t].index: continue
                price=float(data[t].loc[d,"close"])
                shares=int((capital*0.2)//price) if price>0 else 0
                if shares==0 or shares*price>cash: continue
                cash-=shares*price*(1+0.001)
                holdings[t]=shares
                trades.append({"ticker":t,"date":d,"action":"buy","price":price})
        val=cash + sum(holdings[t]*float(data[t].loc[d,"close"]) for t in holdings if d in data[t].index)
        equity_curve.append({"date":d,"equity":float(val)})
    eq=pd.DataFrame(equity_curve).set_index("date") if equity_curve else pd.DataFrame(columns=["equity"])
    return trades, eq


META = {
    "name": "ML Overlay (HistGradientBoosting)",
    "family": "ML",
    "params": {"capital": 1_000_000, "top_n": 3},
    "description": "HistGradientBoosting on factors, walk-forward CV, long top-N probabilities.",
}
