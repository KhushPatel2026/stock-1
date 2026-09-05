"""Real fundamentals via yfinance .info, cached to disk for 7 days."""
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
    """Pull yfinance .info for ticker, cache to JSON, return normalized dict.

    Cache TTL = 7 days. On miss/expired, refetches from yfinance.
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
    info = yf.Ticker(ticker).info or {}
    market_cap = _f(info, "marketCap")
    ev = _f(info, "enterpriseValue")
    ebitda = _f(info, "ebitda")
    ebit = _f(info, "ebit") if _f(info, "ebit") is not None else ebitda  # ponytail: use ebitda as proxy when ebit missing
    total_debt = _f(info, "totalDebt")
    total_cash = _f(info, "totalCash")
    roe = _f(info, "returnOnEquity")
    ey = (ebit / ev) if (ebit is not None and ev not in (None, 0)) else None
    out = {
        "ticker": ticker,
        "market_cap": market_cap,
        "enterprise_value": ev,
        "ebitda": ebitda,
        "ebit": ebit,
        "total_debt": total_debt,
        "total_cash": total_cash,
        "return_on_equity": roe,
        "earnings_yield": ey,
        "pe_trailing": _f(info, "trailingPE"),
        "pe_forward": _f(info, "forwardPE"),
        "price_to_book": _f(info, "priceToBook"),
        "dividend_yield": _f(info, "dividendYield"),
        "book_value": _f(info, "bookValue"),
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
