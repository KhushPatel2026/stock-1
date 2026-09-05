"""FastAPI backend exposing all stock-1 strategies."""
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any

from src.registry import list_strategies, run_backtest, get_strategy
from src.universe import NIFTY50
from src.paper import PaperBroker
from src.paper_engine import run_rebalance, daily_report, get_latest_prices
from src.signals import compute_signals

app = FastAPI(title="stock-1 API", version="1.0.0")

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")

_paper_broker = PaperBroker()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "n_strategies": len(list_strategies())}


@app.get("/api/strategies")
def strategies(family: str | None = None) -> list[dict]:
    items = list_strategies()
    if family:
        items = [s for s in items if s["family"].lower() == family.lower()]
    return items


@app.get("/api/strategies/{strategy_id}")
def strategy(strategy_id: str) -> dict:
    s = get_strategy(strategy_id)
    if not s:
        raise HTTPException(404, f"strategy not found: {strategy_id}")
    return s


@app.get("/api/tickers")
def tickers() -> list[str]:
    return NIFTY50


@app.get("/api/tickers/search")
def tickers_search(q: str = "", limit: int = 10) -> list[dict]:
    """Search any ticker via yfinance. Returns [{symbol, shortname, exchange}]."""
    if not q or len(q) < 1:
        return []
    try:
        import yfinance as yf
        s = yf.Search(q, max_results=limit)
        out = []
        for quote in (s.quotes or [])[:limit]:
            sym = quote.get("symbol", "")
            if not sym:
                continue
            out.append({
                "symbol": sym,
                "shortname": quote.get("shortname") or quote.get("longname") or sym,
                "exchange": quote.get("exchange", ""),
                "quoteType": quote.get("quoteType", ""),
            })
        return out
    except Exception as e:
        raise HTTPException(500, f"search failed: {e}")


class RecommendationsRequest(BaseModel):
    tickers: list[str]
    period: str = "1y"


@app.post("/api/recommendations")
def recommendations(req: RecommendationsRequest) -> dict:
    """Run all strategies on selected tickers for a recent window, return ranked by Sharpe."""
    if not req.tickers:
        raise HTTPException(400, "tickers required")
    from src.registry import list_strategies
    from src.validation import run_walk_forward
    items = list_strategies()
    ranked = []
    for s in items:
        sid = s["id"]
        try:
            r = run_walk_forward(sid, req.tickers, period=req.period, chunk=63)
            if r is None or r.empty:
                continue
            row = r.iloc[0]
            ranked.append({
                "strategy_id": sid,
                "name": s["name"],
                "family": s["family"],
                "oos_sharpe": float(row.get("mean_oos_sharpe", 0)),
                "total_return": float(row.get("total_oos_return", 0)),
                "max_dd": float(row.get("max_dd", 0)),
                "reason": s.get("reason", ""),
            })
        except Exception as e:
            ranked.append({"strategy_id": sid, "name": s["name"], "family": s["family"], "error": str(e)[:80]})
    ranked.sort(key=lambda x: x.get("oos_sharpe", -99), reverse=True)
    return {"as_of": req.period, "tickers": req.tickers, "ranked": ranked}


class DecisionsRequest(BaseModel):
    tickers: list[str]
    period: str = "3mo"


@app.post("/api/decisions")
def decisions(req: DecisionsRequest) -> dict:
    """Per-ticker consensus: BUY / SELL / HOLD based on signals + recent Sharpe weighting."""
    if not req.tickers:
        raise HTTPException(400, "tickers required")
    from src.signals import compute_signals_for_tickers
    from src.registry import list_strategies

    items = list_strategies()
    # Get recent OOS Sharpe per strategy for weighting
    from src.validation import run_walk_forward
    weights: dict[str, float] = {}
    for s in items:
        try:
            r = run_walk_forward(s["id"], req.tickers, period="1y", chunk=63)
            if r is None or r.empty:
                weights[s["id"]] = 0
            else:
                sharpe = float(r.iloc[0].get("mean_oos_sharpe", 0))
                weights[s["id"]] = max(sharpe, 0)  # only positive sharpe strategies vote
        except Exception:
            weights[s["id"]] = 0

    # Get current signals
    sig_map = compute_signals_for_tickers(req.tickers, period=req.period)

    out = []
    for ticker in req.tickers:
        n_long, n_short, n_flat = 0, 0, 0
        long_w, short_w, flat_w = 0.0, 0.0, 0.0
        long_strats, short_strats = [], []
        for sid, sig, strength in sig_map.get(ticker, []):
            w = max(weights.get(sid, 0.1), 0.1) * (strength or 0.3)
            if sig == "long":
                n_long += 1
                long_w += w
                long_strats.append((sid, w))
            elif sig == "short":
                n_short += 1
                short_w += w
                short_strats.append((sid, w))
            else:
                n_flat += 1
                flat_w += w
        total_w = long_w + short_w + flat_w + 1e-9
        long_pct = round(long_w / total_w * 100, 1)
        short_pct = round(short_w / total_w * 100, 1)

        # Decision: weighted score with strategy count support
        n_total = n_long + n_short + n_flat
        long_ratio = n_long / max(n_total, 1)
        short_ratio = n_short / max(n_total, 1)
        score = long_pct - short_pct

        # BUY: ≥25% strategies say long AND score ≥ 10
        if long_ratio >= 0.25 and score >= 10:
            decision = "BUY"
            confidence = min(long_ratio * 120 + score * 0.8, 99)
        # SELL: ≥15% say short AND score ≤ -5
        elif short_ratio >= 0.15 and score <= -5:
            decision = "SELL"
            confidence = min(short_ratio * 120 + (-score) * 0.8, 99)
        else:
            decision = "HOLD"
            confidence = round(100 - abs(score) * 2, 1)

        long_strats.sort(key=lambda x: -x[1])
        short_strats.sort(key=lambda x: -x[1])
        out.append({
            "ticker": ticker,
            "decision": decision,
            "confidence": round(confidence, 1),
            "long_pct": long_pct,
            "short_pct": short_pct,
            "score": round(score, 1),
            "long_strategies": [s for s, _ in long_strats[:5]],
            "short_strategies": [s for s, _ in short_strats[:5]],
            "n_long": n_long,
            "n_short": n_short,
            "n_flat": n_flat,
        })
    out.sort(key=lambda x: (x["decision"] != "BUY", -(x["score"])))
    return {"as_of": req.period, "tickers": req.tickers, "decisions": out}


@app.get("/api/families")
def families() -> list[dict]:
    items = list_strategies()
    fams = {}
    for s in items:
        fams.setdefault(s["family"], 0)
        fams[s["family"]] += 1
    return [{"name": k, "count": v} for k, v in sorted(fams.items())]


class BacktestRequest(BaseModel):
    strategy_id: str
    tickers: list[str]
    period: str = "2y"
    params: dict[str, Any] | None = None


@app.post("/api/backtest")
def backtest(req: BacktestRequest) -> dict:
    if not req.tickers:
        raise HTTPException(400, "tickers required")
    if len(req.tickers) > 50:
        raise HTTPException(400, "max 50 tickers")
    try:
        result = run_backtest(req.strategy_id, req.tickers, req.params, req.period)
    except Exception as e:
        raise HTTPException(500, f"backtest failed: {e}")
    return result


# FEAT-009 — paper trading endpoints

@app.get("/api/paper/state")
def paper_state() -> dict:
    prices = get_latest_prices(["RELIANCE.NS", "TCS.NS"])
    return _paper_broker.mark_to_market(prices)


@app.post("/api/paper/order")
def paper_order(ticker: str, side: str, qty: int, price: float | None = None) -> dict:
    if side not in ("buy", "sell"):
        raise HTTPException(400, "side must be 'buy' or 'sell'")
    if qty <= 0:
        raise HTTPException(400, "qty must be > 0")
    if price is None:
        prices = get_latest_prices([ticker])
        if ticker not in prices:
            raise HTTPException(400, f"no price for {ticker}")
        price = prices[ticker]
    try:
        return _paper_broker.place_order(ticker, side, int(qty), float(price))
    except Exception as e:
        raise HTTPException(500, f"order failed: {e}")


@app.post("/api/paper/rebalance")
def paper_rebalance(strategy_id: str = "bollinger", tickers: list[str] | None = None) -> dict:
    try:
        return run_rebalance(_paper_broker, strategy_id, tickers)
    except Exception as e:
        raise HTTPException(500, f"rebalance failed: {e}")


@app.get("/api/paper/report")
def paper_report() -> dict:
    return daily_report(_paper_broker)


@app.get("/api/signals")
def signals(tickers: list[str] | None = None) -> dict:
    return compute_signals(tickers)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
