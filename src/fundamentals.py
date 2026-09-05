"""Real fundamentals — screener.in first, yfinance .info fills gaps, 7-day disk cache."""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import yfinance as yf

CACHE_DIR = Path("data/cache/fundamentals")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
TTL = timedelta(days=7)

_NULL_KEYS = (None, "None", "", float("nan"))


def _clean(v):
    if v is None:
        return None
    if isinstance(v, float):
        try:
            if v != v:  # NaN
                return None
        except Exception:
            pass
        return float(v)
    if isinstance(v, (int,)):
        return float(v)
    return v


def _f(info: dict, *keys: str) -> float | None:
    for k in keys:
        if k in info and info[k] not in _NULL_KEYS:
            return _clean(info[k])
    return None


def fetch_fundamentals(ticker: str, *, use_cache: bool = True) -> dict:
    """Screener.in first (good .NS coverage), yfinance .info fills gaps.

    Cache TTL = 7 days. Returns normalized dict; always includes `source`.
    """
    safe = ticker.replace(".", "_").replace("/", "_")
    p = CACHE_DIR / f"{safe}.json"
    if use_cache and p.exists():
        try:
            cached = json.loads(p.read_text())
            ts = datetime.fromisoformat(cached.get("fetched_at", "1970-01-01T00:00:00+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - ts < TTL:
                return cached
        except Exception:
            pass
    try:
        from src.screener import fetch_ratios
        scr = fetch_ratios(ticker)
    except Exception:
        scr = {}
    info: dict = {}
    needs_info = any(scr.get(k) is None for k in
                     ("market_cap", "total_debt", "total_cash", "enterprise_value", "ebitda"))
    if needs_info or not scr:
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            info = {}
    market_cap = scr.get("market_cap") or _f(info, "marketCap")
    ev = _f(info, "enterpriseValue")
    ebitda = _f(info, "ebitda")
    ebit = _f(info, "ebit") if _f(info, "ebit") is not None else ebitda  # ponytail: use ebitda as proxy when ebit missing
    total_debt = _f(info, "totalDebt")
    total_cash = _f(info, "totalCash")
    roe = scr.get("return_on_equity") or _f(info, "returnOnEquity")
    ey = (ebit / ev) if (ebit is not None and ev not in (None, 0)) else None
    out = {
        "ticker": ticker,
        "source": "screener.in+yfinance" if scr and info else ("screener.in" if scr else "yfinance"),
        "market_cap": market_cap,
        "enterprise_value": ev,
        "ebitda": ebitda,
        "ebit": ebit,
        "total_debt": total_debt,
        "total_cash": total_cash,
        "return_on_equity": roe,
        "roce": scr.get("roce"),
        "eps_ttm": scr.get("eps_ttm"),
        "debt_equity": scr.get("debt_equity"),
        "earnings_yield": ey,
        "pe_trailing": scr.get("pe_trailing") or _f(info, "trailingPE"),
        "pe_forward": _f(info, "forwardPE"),
        "price_to_book": scr.get("price_to_book") or _f(info, "priceToBook"),
        "dividend_yield": scr.get("dividend_yield") if scr.get("dividend_yield") is not None else _f(info, "dividendYield"),
        "book_value": scr.get("book_value") or _f(info, "bookValue"),
        "company_name": scr.get("company_name"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        p.write_text(json.dumps(out, default=str))
    except Exception:
        pass
    return out


def fetch_many_fundamentals(tickers: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for t in tickers:
        try:
            out[t] = fetch_fundamentals(t)
        except Exception as e:
            out[t] = {"ticker": t, "error": str(e)}
    return out
