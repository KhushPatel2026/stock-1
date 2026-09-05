"""Screener.in fundamentals — free, no key. Polite scraping with graceful fallback.

Chain position: `src/fundamentals` tries screener first (good .NS coverage where
yfinance .info is patchy), then yfinance .info fills gaps (debt/cash/EV absolutes).

Be nice: one shared session, browser UA, 1.5s between hits, 15s timeout.
Any failure -> {} so callers always fall back. Never raises.
"""
from __future__ import annotations
import re
import time
import threading
import requests

_SEARCH = "https://www.screener.in/api/company/search/"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_session: requests.Session | None = None
_lock = threading.Lock()
_last_hit = 0.0

# screener label -> our key, value kind
_LABELS = {
    "market cap": ("market_cap", "money_cr"),
    "current price": ("current_price", "money"),
    "high / low": (None, None),
    "stock p/e": ("pe_trailing", "num"),
    "book value": ("book_value", "money"),
    "dividend yield": ("dividend_yield", "pct"),
    "roce": ("roce", "pct"),
    "roce %": ("roce", "pct"),
    "roe": ("return_on_equity", "pct"),
    "roe %": ("return_on_equity", "pct"),
    "face value": (None, None),
    "eps ttm": ("eps_ttm", "money"),
    "debt to equity": ("debt_equity", "num"),
    "pledged percentage": ("pledged_pct", "pct"),
    "debtor days": (None, None),
    "ev": ("enterprise_value_cr", "money_cr"),
    "enterprise value": ("enterprise_value_cr", "money_cr"),
}


def _sess() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"})
        _session = s
    return _session


def _polite():
    global _last_hit
    with _lock:
        wait = 1.5 - (time.time() - _last_hit)
        if wait > 0:
            time.sleep(wait)
        _last_hit = time.time()


def _num(raw: str) -> float | None:
    raw = raw.replace(",", "").strip()
    m = re.match(r"([-+]?[0-9]*\.?[0-9]+)", raw)
    return float(m.group(1)) if m else None


def _convert(v: float | None, kind: str | None):
    if v is None or kind is None:
        return v
    if kind == "pct":
        return v / 100.0
    if kind == "money_cr":
        return v * 1e7
    return v


def search_url(query: str) -> str | None:
    """Best screener company URL for a query (usually the NSE symbol root)."""
    try:
        _polite()
        r = _sess().get(_SEARCH, params={"q": query}, timeout=15)
        if r.status_code != 200:
            return None
        hits = r.json()
        if not hits:
            return None
        url = hits[0].get("url", "")
        return f"https://www.screener.in{url}" if url else None
    except Exception:
        return None


def fetch_ratios(ticker: str) -> dict:
    """Top-ratios block for an NSE ticker. Returns {} on any failure."""
    query = ticker.split(".")[0].strip().upper()
    if not query:
        return {}
    url = search_url(query)
    if not url:
        return {}
    try:
        _polite()
        r = _sess().get(url, timeout=20)
        if r.status_code != 200 or "top-ratios" not in r.text:
            return {}
        html = r.text
        out: dict = {"source": "screener.in", "url": url}
        # <span class="name"> Label </span> ... <span class="number">VALUE</span>
        pairs = re.findall(
            r'<span class="name">\s*([^<]+?)\s*</span>.*?<span class="number">\s*([^<]+?)\s*</span>',
            html, re.DOTALL)
        for label, raw in pairs:
            key_kind = _LABELS.get(label.strip().lower())
            if not key_kind or key_kind[0] is None:
                continue
            key, kind = key_kind
            if key in out:
                continue
            out[key] = _convert(_num(raw), kind)
        # company name from <h1>
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
        if m:
            out["company_name"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()[:80]
        return out
    except Exception:
        return {}
