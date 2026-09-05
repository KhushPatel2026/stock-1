"""CLI: python -m src.backtest [--tickers N] [--period 5y] [--capital 1000000]"""
import argparse
from .universe import NIFTY50, NIFTY15
from .data import fetch_many
from .indicators import add_all
from .portfolio import run

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", type=int, default=15, help="number of tickers from Nifty50 (15 or 50)")
    ap.add_argument("--period", default="5y")
    ap.add_argument("--capital", type=float, default=1_000_000)
    ap.add_argument("--max-pos", type=int, default=5)
    args = ap.parse_args()

    tickers = NIFTY50[:args.tickers] if args.tickers <= 50 else NIFTY15
    print(f"Fetching {len(tickers)} tickers period={args.period} ...")
    data = fetch_many(tickers, period=args.period)
    print(f"Fetched {len(data)}/{len(tickers)}")
    for t, df in list(data.items()):
        data[t] = add_all(df)
    trades, equity, metrics = run(data, capital=args.capital, max_positions=args.max_pos)
    print(f"\nTrades: {len(trades)}")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    if trades:
        print("\nLast 5 trades:")
        for t in trades[-5:]:
            print(t)
    if not equity.empty:
        print(f"\nEquity: {equity['equity'].iloc[0]:.0f} -> {equity['equity'].iloc[-1]:.0f} over {len(equity)} days")

if __name__ == "__main__":
    main()
