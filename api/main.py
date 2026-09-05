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
