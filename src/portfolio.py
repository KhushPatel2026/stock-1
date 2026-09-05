"""Portfolio backtest loop — long-only, daily, max 5 positions."""
import pandas as pd
from .signals import is_entry
from .sizing import levels, position_size
from .metrics import compute_metrics

def run(data: dict[str, pd.DataFrame], capital: float = 1_000_000, max_positions: int = 5, risk_pct: float = 0.01) -> tuple[list[dict], pd.DataFrame, dict]:
    if not data:
        raise ValueError("no data")
    # union of all dates sorted
    all_dates = sorted(set().union(*(set(df.index) for df in data.values())))
    # map ticker -> date->row index for fast lookup
    # build date->idx per ticker
    ticker_idx = {}
    for t, df in data.items():
        m = {d: i for i, d in enumerate(df.index)}
        ticker_idx[t] = m

    positions: list[dict] = []  # open
    trades: list[dict] = []
    equity_curve = []
    cash = capital
    # track held tickers
    held = set()

    for d in all_dates:
        # 1. check exits
        for pos in positions[:]:
            t = pos["ticker"]
            df = data[t]
            idx = ticker_idx[t].get(d)
            if idx is None:
                continue
            row = df.iloc[idx]
            low, high = row["low"], row["high"]
            stop, tp = pos["stop"], pos["take_profit"]
            exit_price = None
            reason = None
            # SL has priority if both hit same bar (conservative)
            if low <= stop:
                exit_price, reason = stop, "SL"
            elif high >= tp:
                exit_price, reason = tp, "TP"
            if exit_price is not None:
                pnl = (exit_price - pos["entry_price"]) * pos["shares"]
                cash += exit_price * pos["shares"]
                trades.append({**pos, "exit_date": d, "exit_price": exit_price, "exit_reason": reason, "pnl": pnl, "return_pct": pnl / (pos["entry_price"]*pos["shares"])})
                positions.remove(pos)
                held.discard(t)

        # 2. entries
        if len(positions) < max_positions:
            for t, df in data.items():
                if t in held:
                    continue
                if len(positions) >= max_positions:
                    break
                idx = ticker_idx[t].get(d)
                if idx is None or idx == 0:
                    continue
                if not is_entry(df, idx):
                    continue
                row = df.iloc[idx]
                entry = float(row["close"])
                atr = float(row["atr"])
                if atr <= 0 or entry <= 0:
                    continue
                stop, tp = levels(entry, atr)
                shares = position_size(cash + sum(p["entry_price"]*p["shares"] for p in positions), entry, stop, risk_pct)  # use equity
                # actually use current equity approximation
                if shares <= 0:
                    continue
                cost = shares * entry
                # ensure we have enough equity (cash may be less than cost if many positions, but we use equity-based sizing so allow if cash insufficient? cap by cash)
                if cost > cash:
                    shares = int(cash // entry)
                    if shares == 0:
                        continue
                    cost = shares * entry
                cash -= cost
                pos = {"ticker": t, "entry_date": d, "entry_price": entry, "shares": shares, "stop": stop, "take_profit": tp, "atr": atr}
                positions.append(pos)
                held.add(t)

        # 3. equity
        # unrealized
        unreal = 0
        for pos in positions:
            df = data[pos["ticker"]]
            idx = ticker_idx[pos["ticker"]].get(d)
            if idx is not None:
                cur = float(df.iloc[idx]["close"])
                unreal += (cur - pos["entry_price"]) * pos["shares"]
        equity = cash + sum(p["entry_price"]*p["shares"] for p in positions) + unreal
        equity_curve.append({"date": d, "equity": equity})

    eq_df = pd.DataFrame(equity_curve).set_index("date") if equity_curve else pd.DataFrame(columns=["equity"])
    # close any open positions at last close (mark to market for metrics, but not as trades unless we want)
    metrics = compute_metrics(trades, eq_df, capital)
    # exposure approx
    if equity_curve and trades:
        metrics["exposure"] = len([e for e in equity_curve if e["equity"] != capital]) / len(equity_curve)
    return trades, eq_df, metrics
