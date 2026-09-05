"""Walk-forward optimization — rolling train/test, grid search OOS."""
import pandas as pd

def run(data: dict[str, pd.DataFrame], param_grid: list[dict], train: int = 504, test: int = 126, strategy_fn=None) -> list[dict]:
    """
    strategy_fn: (data_slice, params) -> equity Series
    data_slice is dict[ticker->df sliced to window]
    Returns folds: [{train_start, train_end, test_start, test_end, best_params, train_sharpe, oos_sharpe}]
    """
    if strategy_fn is None:
        raise ValueError("strategy_fn required")
    # union dates
    all_dates=sorted(set().union(*(set(df.index) for df in data.values())))
    folds=[]
    i=0
    while i + train + test <= len(all_dates):
        train_dates=all_dates[i:i+train]
        test_dates=all_dates[i+train:i+train+test]
        # slice data
        train_data={t: df.loc[train_dates[0]:train_dates[-1]] for t,df in data.items() if not df.loc[train_dates[0]:train_dates[-1]].empty}
        test_data={t: df.loc[test_dates[0]:test_dates[-1]] for t,df in data.items() if not df.loc[test_dates[0]:test_dates[-1]].empty}
        # grid search on train
        best=None; best_sharpe=-1e9
        for p in param_grid:
            try:
                eq=strategy_fn(train_data, p)
                rets=eq.pct_change().dropna()
                sharpe=float(rets.mean()/rets.std() * (252**0.5)) if rets.std()!=0 and len(rets)>1 else -1e9
            except Exception:
                sharpe=-1e9
            if sharpe > best_sharpe:
                best_sharpe=sharpe; best=p
        # OOS
        try:
            eq_test=strategy_fn(test_data, best) if best else pd.Series(dtype=float)
            rets=eq_test.pct_change().dropna()
            oos_sharpe=float(rets.mean()/rets.std() * (252**0.5)) if rets.std()!=0 and len(rets)>1 else 0
        except Exception:
            oos_sharpe=0; eq_test=pd.Series()
        folds.append({"train_start":train_dates[0],"train_end":train_dates[-1],"test_start":test_dates[0],"test_end":test_dates[-1],
                      "best_params":best,"train_sharpe":float(best_sharpe),"oos_sharpe":float(oos_sharpe),"test_len":len(test_dates)})
        i+=test
    return folds
