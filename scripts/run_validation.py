"""CLI: run FEAT-007 walk-forward + regime validation across all strategies.

Usage:
    python3 scripts/run_validation.py [--tickers RELIANCE.NS,TCS.NS] [--period 5y] [--out reports] [--strategies bollinger,rsi2,...] [--workers 4]
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.registry import list_strategies
from src.validation import run_walk_forward, run_regime_tests


def main() -> None:
    p = argparse.ArgumentParser(description="Run walk-forward + regime validation.")
    p.add_argument("--tickers", default="RELIANCE.NS,TCS.NS,INFY.NS",
                   help="Comma-separated tickers (default: large-cap Nifty trio).")
    p.add_argument("--period", default="5y", help="yfinance period for walk-forward (default 5y).")
    p.add_argument("--out", default="reports", help="Output directory (default reports).")
    p.add_argument("--strategies", default="",
                   help="Comma-separated strategy IDs to run (default: all registered).")
    p.add_argument("--workers", type=int, default=4, help="Parallel workers (default 4).")
    p.add_argument("--skip-intraday", action="store_true", help="Skip intraday strategies (saves time).")
    args = p.parse_args()

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    all_strats = list_strategies()
    if args.strategies:
        sids = [s.strip() for s in args.strategies.split(",") if s.strip()]
    else:
        sids = [s["id"] for s in all_strats]
        if args.skip_intraday:
            sids = [s for s in sids if "intraday" not in s.lower() and "overnight" not in s.lower()]
    print(f"Validating {len(tickers)} tickers × {len(sids)} strategies ({args.workers} workers) → {args.out}/")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    def run_one(sid: str):
        try:
            wf = run_walk_forward(sid, tickers, period=args.period, chunk=63)
            rg = run_regime_tests(sid, tickers)
            return sid, wf, rg, ""
        except Exception as e:
            return sid, None, None, str(e)[:100]

    wf_rows = []
    rg_rows = []
    failed = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(run_one, sid): sid for sid in sids}
        for i, fut in enumerate(as_completed(futures), 1):
            sid, wf, rg, err = fut.result()
            if err:
                failed.append((sid, err))
                print(f"  [{i}/{len(sids)}] {sid}: FAILED ({err})", flush=True)
                continue
            if wf is not None and not wf.empty:
                wf_rows.append(wf.iloc[0].to_dict())
            if rg is not None and not rg.empty:
                for _, row in rg.iterrows():
                    rg_rows.append(row.to_dict())
            print(f"  [{i}/{len(sids)}] {sid}: OOS Sharpe={wf.iloc[0]['mean_oos_sharpe']:.3f}" if wf is not None and not wf.empty else f"  [{i}/{len(sids)}] {sid}: empty", flush=True)

    import pandas as pd
    wf_df = pd.DataFrame(wf_rows)
    rg_df = pd.DataFrame(rg_rows)
    wf_path = out_dir / "walk_forward.csv"
    rg_path = out_dir / "regime_tests.csv"
    rg_md_path = out_dir / "regime_tests.md"
    wf_df.to_csv(wf_path, index=False)
    rg_df.to_csv(rg_path, index=False)
    if not rg_df.empty:
        pivot = rg_df.pivot(index="strategy_id", columns="regime", values="sharpe").round(2).fillna("-")
        with open(rg_md_path, "w") as f:
            f.write("# Regime Tests — Sharpe per regime\n\n")
            f.write(f"Strategies: {len(pivot)}, regimes: {list(pivot.columns)}\n\n")
            f.write(_df_to_md(pivot))
            f.write("\n\n## Total return per regime\n\n")
            pivot_ret = rg_df.pivot(index="strategy_id", columns="regime", values="total_return").round(3).fillna("-")
            f.write(_df_to_md(pivot_ret))
            f.write("\n\n## Max drawdown per regime\n\n")
            pivot_dd = rg_df.pivot(index="strategy_id", columns="regime", values="max_dd").round(3).fillna("-")
            f.write(_df_to_md(pivot_dd))
            f.write("\n")


def _df_to_md(df) -> str:
    """Format DataFrame as markdown table (no tabulate dependency)."""
    cols = list(df.columns)
    header = "| " + " | ".join(["strategy_id"] + [str(c) for c in cols]) + " |"
    sep = "|" + "|".join(["---"] * (len(cols) + 1)) + "|"
    rows = []
    for idx, row in df.iterrows():
        cells = [str(idx)] + [str(row[c]) for c in cols]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep] + rows)
    print(f"\nwalk_forward rows: {len(wf_df)} → {wf_path}")
    print(f"regime_tests rows: {len(rg_df)} → {rg_path}")
    print(f"regime_tests.md → {rg_md_path}")
    if failed:
        print(f"failed: {len(failed)}")
        for sid, err in failed[:10]:
            print(f"  {sid}: {err}")


if __name__ == "__main__":
    main()
    print(f"  wrote {result['md_path']}")


if __name__ == "__main__":
    main()