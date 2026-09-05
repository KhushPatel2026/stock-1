"""CLI for pairs: python -m src.pair_backtest --tickers 15 --period 2y"""
import argparse
from .universe import NIFTY50, NIFTY15
from .data import fetch_many
from .pairs import find_cointegrated
from .pair_portfolio import run_pair

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", type=int, default=15)
    ap.add_argument("--period", default="2y")
    ap.add_argument("--capital", type=float, default=1_000_000)
    ap.add_argument("--p-thresh", type=float, default=0.05)
    args = ap.parse_args()
    tickers = NIFTY50[:args.tickers] if args.tickers <= 50 else NIFTY15
    print(f"Fetching {len(tickers)} period={args.period} ...")
    data = fetch_many(tickers, period=args.period)
    print(f"Fetched {len(data)}/{len(tickers)}")
    pairs = find_cointegrated(data, p_thresh=args.p_thresh)
    print(f"Found {len(pairs)} cointegrated pairs (p<={args.p_thresh}):")
    for p in pairs[:5]:
        print(f"  {p['pair']} p={p['pvalue']:.4f} corr={p['corr']:.2f} beta={p['beta']:.2f}")
    if not pairs:
        print("No pairs — try --p-thresh 0.10 or larger universe")
        return
    top = pairs[0]["pair"]
    print(f"\nBacktesting top pair {top} ...")
    trades, eq, m = run_pair(data, top, capital=args.capital)
    print(f"Trades: {len(trades)}  Final: {eq['equity'].iloc[-1]:.0f} from {args.capital:.0f}")
    for k, v in m.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    if trades:
        print("\nLast 3 trades:", trades[-3:])

if __name__ == "__main__":
    main()
