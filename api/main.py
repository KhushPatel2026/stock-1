"""FastAPI backend exposing all stock-1 strategies."""
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

from src.registry import list_strategies, run_backtest, get_strategy
from src.universe import NIFTY50

app = FastAPI(title="stock-1 API", version="0.6.0")

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
