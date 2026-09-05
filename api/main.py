"""FastAPI backend exposing all stock-1 strategies."""
from __future__ import annotations
import os
import requests
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

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
from src.upstox import UpstoxClient

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


# Day-level cache: OOS-Sharpe weights are stable intraday; recompute once per day.
# Key: (date, tickers-key). First hit warms in parallel (8 workers); later hits are instant.
_WEIGHTS_CACHE: dict[tuple, dict[str, float]] = {}


def _strategy_weight(strategy_id: str, tickers: list[str], data: dict | None = None) -> float:
    from src.validation import run_walk_forward
    try:
        r = run_walk_forward(strategy_id, tickers, period="1y", chunk=63, data=data)
        if r is None or r.empty:
            return 0.0
        return max(float(r.iloc[0].get("mean_oos_sharpe", 0)), 0)
    except Exception:
        return 0.0


def _oos_weights(strategy_ids: list[str], tickers: list[str], data: dict | None = None) -> dict[str, float]:
    import datetime
    from concurrent.futures import ThreadPoolExecutor
    key = (datetime.date.today().isoformat(), tuple(sorted(tickers)))
    if key in _WEIGHTS_CACHE:
        return _WEIGHTS_CACHE[key]
    weights: dict[str, float] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for sid, w in zip(strategy_ids, pool.map(lambda s: _strategy_weight(s, tickers, data), strategy_ids)):
            weights[sid] = w
    _WEIGHTS_CACHE.clear()  # ponytail: keep one day only, no unbounded growth
    _WEIGHTS_CACHE[key] = weights
    return weights


@app.post("/api/decisions")
def decisions(req: DecisionsRequest) -> dict:
    """Per-ticker consensus: BUY / SELL / HOLD + entry/SL/target/timeframe/insight."""
    if not req.tickers:
        raise HTTPException(400, "tickers required")
    if len(req.tickers) > 25:
        raise HTTPException(400, "max 25 tickers")
    from src.signals import compute_signals_for_tickers
    from src.data import fetch_many, fetch, live_price
    from src.trade_plan import build_plan

    items = list_strategies()
    families = {s["id"]: s["family"] for s in items}
    names = {s["id"]: s["name"] for s in items}
    # ONE shared 1y fetch: feeds levels AND all 89 weight runs (no per-strategy refetch,
    # no rate-limit hammering, identical bars everywhere).
    ohlc = fetch_many(req.tickers, period="1y")
    for t in req.tickers:  # retry loners once with fresh download (no cache)
        if t not in ohlc:
            try:
                ohlc[t] = fetch(t, period="1y", use_cache=False)
            except Exception:
                pass
    weights = _oos_weights([s["id"] for s in items], req.tickers, data=ohlc)

    # Current signals (3mo window is fast)
    sig_map = compute_signals_for_tickers(req.tickers, period=req.period)
    # Live entries (1m bars; falls back to daily close; never raises)
    live = {t: live_price(t) for t in req.tickers}

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
        df = ohlc.get(ticker)
        if df is not None and not df.empty:
            try:
                lp, lp_label, lp_live = live.get(ticker, (None, "", False))
                plan = build_plan(ticker, df, decision, confidence,
                                  long_strats, short_strats, families, names,
                                  entry=lp, entry_label=lp_label if lp_live else "")
            except Exception:
                plan = None
        else:
            plan = None
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
            "plan": plan,
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
    capital: float = 1_000_000


@app.post("/api/backtest")
def backtest(req: BacktestRequest) -> dict:
    if not req.tickers:
        raise HTTPException(400, "tickers required")
    if len(req.tickers) > 50:
        raise HTTPException(400, "max 50 tickers")
    if req.capital <= 0:
        raise HTTPException(400, "capital must be > 0")
    try:
        result = run_backtest(req.strategy_id, req.tickers, req.params, req.period, capital=req.capital)
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


# ---------------------------------------------------------------------------
# FEAT-XXX — Upstox OAuth token + portfolio + analytics endpoints
# ---------------------------------------------------------------------------

# Token held in memory for dev. Prod would use proper session-bound auth.
_upstox_token: str | None = os.getenv("UPSTOX_ACCESS_TOKEN")


class UpstoxTokenRequest(BaseModel):
    access_token: str


@app.post("/api/upstox/token")
def set_upstox_token(req: UpstoxTokenRequest) -> dict:
    """Store Upstox OAuth access_token in memory. Token lasts ~1 day; re-run OAuth when expired."""
    global _upstox_token
    if not req.access_token or len(req.access_token) < 10:
        raise HTTPException(400, "access_token looks invalid")
    _upstox_token = req.access_token
    return {"ok": True, "token_length": len(req.access_token)}


@app.get("/api/upstox/status")
def upstox_status() -> dict:
    client = UpstoxClient(_upstox_token)
    return {"authenticated": client.is_authenticated()}


@app.get("/api/portfolio")
def portfolio() -> dict:
    """Live Upstox holdings + positions enriched with current prices via yfinance."""
    from src.portfolio import fetch_portfolio
    return fetch_portfolio(_upstox_token)


@app.get("/api/upstox/profile")
def upstox_profile() -> dict:
    client = UpstoxClient(_upstox_token)
    if not client.is_authenticated():
        raise HTTPException(401, "no access token — POST /api/upstox/token first")
    try:
        return client.get_profile()
    except Exception as e:
        raise HTTPException(500, f"upstox profile failed: {e}")


@app.get("/api/upstox/quote/{exchange}/{symbol}")
def upstox_quote(exchange: str, symbol: str) -> dict:
    client = UpstoxClient(_upstox_token)
    try:
        return client.get_quote(symbol, exchange)
    except Exception as e:
        raise HTTPException(500, f"upstox quote failed: {e}")


@app.get("/api/upstox/option-chain")
def upstox_option_chain(symbol: str, expiry: str | None = None) -> dict:
    client = UpstoxClient(_upstox_token)
    try:
        return client.get_option_chain(symbol, expiry)
    except Exception as e:
        raise HTTPException(500, f"upstox option-chain failed: {e}")


@app.get("/api/upstox/india-vix")
def upstox_vix() -> dict:
    client = UpstoxClient(_upstox_token)
    try:
        return client.get_india_vix()
    except Exception as e:
        raise HTTPException(500, f"upstox india-vix failed: {e}")


@app.get("/api/upstox/pcr")
def upstox_pcr(symbol: str) -> dict:
    client = UpstoxClient(_upstox_token)
    try:
        return client.get_pcr(symbol)
    except Exception as e:
        raise HTTPException(500, f"upstox pcr failed: {e}")


@app.get("/api/upstox/server-info")
def upstox_server_info() -> dict:
    """Upstox calls are proxied via this backend, not the browser.
    If Upstox requires IP whitelisting, whitelist the server's public IP."""
    public_ip = None
    try:
        import requests
        public_ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception:
        pass
    return {
        "note": "Upstox API calls are made from this backend, not your browser. "
                "If Upstox requires IP-based access, whitelist the public_ip below.",
        "public_ip": public_ip,
    }


# ---------------------------------------------------------------------------
# Upstox OAuth — login flow → access token exchange
# ---------------------------------------------------------------------------

UPSTOX_AUTH_URL = "https://api.upstox.com/v2/login/authorization/dialog"
UPSTOX_TOKEN_URL = "https://api.upstox.com/v2/login/authorize"
DEFAULT_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:5173/callback")


@app.get("/api/upstox/auth-url")
def upstox_auth_url(redirect_uri: str | None = None) -> dict:
    """Build the Upstox OAuth login URL. Frontend opens this in a popup/redirect."""
    api_key = os.getenv("UPSTOX_API_KEY", "")
    redirect = redirect_uri or DEFAULT_REDIRECT_URI
    if not api_key:
        raise HTTPException(500, "UPSTOX_API_KEY not set in .env")
    params = {
        "client_id": api_key,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": "orders holdings portfolio",
    }
    qs = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return {"url": f"{UPSTOX_AUTH_URL}?{qs}", "redirect_uri": redirect}


class UpstoxCallbackRequest(BaseModel):
    code: str
    redirect_uri: str | None = None


@app.post("/api/upstox/callback")
def upstox_callback(req: UpstoxCallbackRequest) -> dict:
    """Exchange OAuth code for access token. Frontend calls this from /callback page."""
    global _upstox_token
    api_key = os.getenv("UPSTOX_API_KEY", "")
    api_secret = os.getenv("UPSTOX_API_SECRET", "")
    redirect = req.redirect_uri or DEFAULT_REDIRECT_URI
    if not api_key or not api_secret:
        raise HTTPException(500, "UPSTOX_API_KEY or UPSTOX_API_SECRET missing in .env")
    try:
        r = requests.post(
            UPSTOX_TOKEN_URL,
            data={
                "code": req.code,
                "client_id": api_key,
                "client_secret": api_secret,
                "redirect_uri": redirect,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
        if r.status_code != 200:
            raise HTTPException(r.status_code, f"upstox exchange failed: {r.text[:300]}")
        data = r.json()
        token = data.get("access_token")
        if not token:
            raise HTTPException(500, f"no access_token in response: {data}")
        _upstox_token = token
        return {"ok": True, "token_length": len(token)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"upstox callback failed: {e}")


# ---------------------------------------------------------------------------
# FEAT-XXX — Gemini AI explanations + portfolio insights
# ---------------------------------------------------------------------------

class AIExplainRequest(BaseModel):
    strategy_id: str
    metrics: dict
    user_question: str = ""


class AIPortfolioInsightRequest(BaseModel):
    holdings: list[dict]
    summary: dict


def _is_ai_available() -> bool:
    from src.ai import is_available
    return is_available()


@app.post("/api/ai/explain-strategy")
def ai_explain_strategy(req: AIExplainRequest) -> dict:
    """Explain a strategy result, contextualized with the user's tickers + holdings."""
    from src.ai import explain_strategy
    from src.registry import get_strategy
    from src.tracking import get_recent_runs
    from src.portfolio import fetch_portfolio
    s = get_strategy(req.strategy_id) or {}
    recent = get_recent_runs(5)
    watchlist: list[str] = []
    for r in recent:
        for t in (r.get("tickers") or []):
            if t not in watchlist:
                watchlist.append(t)
    holdings: list[dict] = []
    try:
        p = fetch_portfolio(_upstox_token)
        if p.get("authenticated"):
            holdings = p.get("holdings", []) or []
    except Exception:
        pass
    context = {
        "tickers": watchlist,
        "recent_runs": recent,
        "user_holdings": holdings,
    }
    text = explain_strategy(
        req.strategy_id,
        s.get("name", req.strategy_id),
        s.get("family", "?"),
        req.metrics,
        req.user_question,
        context=context,
    )
    return {"text": text, "ai_enabled": _is_ai_available()}


class AIAnalyzeRequest(BaseModel):
    tickers: list[str] = []
    holdings: list[dict] = []
    question: str = ""


@app.post("/api/ai/analyze")
def ai_analyze(req: AIAnalyzeRequest) -> dict:
    """User-driven AI: enter tickers OR portfolio → get contextual advice.
    This is the entry point the user actually wants.
    """
    from src.ai import _generate
    if not _is_ai_available():
        return {"text": "Gemini not configured. Add GEMINI_API_KEY to .env.", "ai_enabled": False}

    parts: list[str] = []
    if req.tickers:
        parts.append(f"Tickers to analyze: {', '.join(req.tickers[:15])}")
    if req.holdings:
        parts.append("Portfolio holdings (user-entered):")
        for h in req.holdings[:15]:
            parts.append(
                f"  - {h.get('ticker', '?')}: qty {h.get('quantity', '?')}, "
                f"avg {h.get('avg_price', '?')}, current {h.get('current_price', '?')}"
            )
    if not parts:
        return {"text": "Enter tickers or paste holdings to analyze.", "ai_enabled": False}

    user_q = req.question or "What should I do with these? Give me BUY/SELL/HOLD for each ticker with reasoning."
    prompt = (
        "You are a quant analyst for a retail Indian trader. "
        "Based on the user's input below, give concrete actionable advice.\n\n"
        + "\n".join(parts) + "\n\n"
        f"User question: {user_q}\n\n"
        "Format:\n"
        "- Per-ticker recommendation (BUY/SELL/HOLD) with one-line reasoning\n"
        "- Suggested position size (% of capital) for each\n"
        "- 1-2 risks to watch out for\n\n"
        "Be specific and direct. No emojis. No disclaimers. Plain text."
    )
    try:
        text = _generate(prompt)
    except Exception as e:
        text = f"AI error: {e}"
    return {"text": text, "ai_enabled": True}


@app.post("/api/ai/explain-portfolio")
def ai_explain_portfolio(req: AIPortfolioInsightRequest) -> dict:
    from src.ai import explain_portfolio
    text = explain_portfolio(req.holdings, req.summary)
    return {"text": text, "ai_enabled": _is_ai_available()}


@app.get("/api/ai/personalized")
def ai_personalized() -> dict:
    """Generate personalized insights from REAL user context:
    Upstox holdings + watchlist + recent backtest runs."""
    from src.tracking import get_most_used_strategies, get_recent_runs
    from src.ai import personalized_insight
    from src.portfolio import fetch_portfolio
    from src.data import fetch_many

    holdings = []
    portfolio_summary = {}
    try:
        p = fetch_portfolio(_upstox_token)
        if p.get("authenticated"):
            holdings = p.get("holdings", [])
            portfolio_summary = p.get("summary", {})
    except Exception:
        pass

    # watchlist = last tickers the user ran backtests on
    recent_runs = get_recent_runs(10)
    watchlist: list[str] = []
    for r in recent_runs:
        for t in (r.get("tickers") or []):
            if t not in watchlist:
                watchlist.append(t)

    stats = {
        "watchlist": watchlist[:15],
        "user_holdings": holdings[:10],
        "portfolio_summary": portfolio_summary,
        "most_used": [s["strategy_id"] for s in get_most_used_strategies()],
        "recent_runs": recent_runs,
    }
    text = personalized_insight(stats)
    return {"text": text, "ai_enabled": _is_ai_available(), "stats": stats}


@app.get("/api/ai/status")
def ai_status() -> dict:
    from src.ai import is_available
    return {"available": is_available()}


@app.get("/api/insights/portfolio")
def portfolio_insights() -> dict:
    """Pre-built (no AI) portfolio insights."""
    from src.portfolio import fetch_portfolio
    from src.insights import (
        portfolio_concentration_risk,
        portfolio_pnl_attribution,
        suggestions_for_holdings,
    )
    p = fetch_portfolio(_upstox_token)
    if not p.get("authenticated"):
        return {"authenticated": False}
    holdings = p.get("holdings", [])
    return {
        "authenticated": True,
        "concentration": portfolio_concentration_risk(holdings),
        "pnl_attribution": portfolio_pnl_attribution(holdings),
        "suggestions": suggestions_for_holdings(holdings),
        "summary": p.get("summary", {}),
    }


# ---------------------------------------------------------------------------
# Institutional Reports & Regime Validation Endpoints
# ---------------------------------------------------------------------------
import csv


@app.get("/api/reports/summary")
def reports_summary() -> dict:
    """Return executive summary KPIs and overview of validation reports."""
    wf_path = REPORTS_DIR / "walk_forward.csv"
    rg_path = REPORTS_DIR / "regime_tests.csv"

    wf_rows: list[dict[str, Any]] = []
    if wf_path.exists():
        with open(wf_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                wf_rows.append(r)

    rg_rows: list[dict[str, Any]] = []
    if rg_path.exists():
        with open(rg_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rg_rows.append(r)

    total_strats = len(wf_rows)
    sharpes = []
    positive_count = 0
    top_strat = None
    max_sharpe = -999.0

    for r in wf_rows:
        try:
            s = float(r.get("mean_oos_sharpe", 0))
            ret = float(r.get("total_oos_return", 0))
            dd = float(r.get("max_dd", 0))
            sharpes.append(s)
            if s > 0:
                positive_count += 1
            if s > max_sharpe:
                max_sharpe = s
                top_strat = {
                    "strategy_id": r.get("strategy_id"),
                    "sharpe": s,
                    "return": ret,
                    "max_dd": dd,
                    "n_windows": int(r.get("n_windows", 0)) if r.get("n_windows") else 0,
                }
        except (ValueError, TypeError):
            continue

    sharpes.sort()
    median_sharpe = sharpes[len(sharpes) // 2] if sharpes else 0.0
    positive_ratio = (positive_count / total_strats) if total_strats > 0 else 0.0

    return {
        "status": "ok",
        "walk_forward_count": total_strats,
        "regime_tests_count": len(rg_rows),
        "positive_alpha_ratio": round(positive_ratio, 4),
        "median_oos_sharpe": round(median_sharpe, 3),
        "top_strategy": top_strat,
        "available_reports": [
            {
                "id": "walk_forward",
                "name": "Walk-Forward OOS Engine",
                "path": "/reports/walk_forward.csv",
                "type": "csv",
                "rows": total_strats,
                "description": "Out-of-sample rolling window Sharpe, cumulative return, and max drawdown per strategy.",
            },
            {
                "id": "regime_tests",
                "name": "Regime Stress-Tests",
                "path": "/reports/regime_tests.csv",
                "type": "csv",
                "rows": len(rg_rows),
                "description": "Multi-regime resilience across 2018 NBFC crunch, 2020 COVID flash crash, and 2022 chop.",
            },
            {
                "id": "regime_md",
                "name": "Executive Summary",
                "path": "/reports/regime_tests.md",
                "type": "md",
                "rows": 0,
                "description": "Markdown report formatted for institutional investment committee review.",
            },
        ],
    }


@app.get("/api/reports/walk-forward")
def reports_walk_forward() -> list[dict[str, Any]]:
    """Return parsed walk-forward test results with typed numerical fields."""
    wf_path = REPORTS_DIR / "walk_forward.csv"
    if not wf_path.exists():
        return []
    results = []
    with open(wf_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                results.append({
                    "strategy_id": r.get("strategy_id", ""),
                    "n_windows": int(r.get("n_windows", 0)) if r.get("n_windows") else 0,
                    "mean_oos_sharpe": float(r.get("mean_oos_sharpe", 0)),
                    "total_oos_return": float(r.get("total_oos_return", 0)),
                    "max_dd": float(r.get("max_dd", 0)),
                })
            except (ValueError, TypeError):
                continue
    results.sort(key=lambda x: x["mean_oos_sharpe"], reverse=True)
    return results


@app.get("/api/reports/regimes")
def reports_regimes() -> dict[str, Any]:
    """Return parsed regime stress-tests with both raw rows and pivot matrix."""
    rg_path = REPORTS_DIR / "regime_tests.csv"
    if not rg_path.exists():
        return {"rows": [], "matrix": {}}
    rows = []
    matrix: dict[str, dict[str, Any]] = {}
    with open(rg_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                sid = r.get("strategy_id", "")
                reg = r.get("regime", "")
                item = {
                    "strategy_id": sid,
                    "regime": reg,
                    "sharpe": float(r.get("sharpe", 0)),
                    "total_return": float(r.get("total_return", 0)),
                    "max_dd": float(r.get("max_dd", 0)),
                    "n_bars": int(r.get("n_bars", 0)) if r.get("n_bars") else 0,
                }
                rows.append(item)
                if sid not in matrix:
                    matrix[sid] = {}
                matrix[sid][reg] = {
                    "sharpe": item["sharpe"],
                    "total_return": item["total_return"],
                    "max_dd": item["max_dd"],
                }
            except (ValueError, TypeError):
                continue
    return {"rows": rows, "matrix": matrix}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
