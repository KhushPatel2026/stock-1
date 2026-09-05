"""Real-time data scrapers: news, sector indices, sentiment.

These complement the yfinance-based macro layer with sources that update faster
(yfinance quote for some symbols is delayed 15+ min) or that have no yfinance
equivalent (NSE sector indices, FII/DII flows, retail sentiment).

All scrapers are best-effort: 5 s timeout, swallow all exceptions, cache
successful results for 60 s in memory. They never raise.
"""
from __future__ import annotations

import html
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

from src.macro import news_for_ticker as _news_for_ticker


_session = requests.Session()
_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
})

_NSE_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 60.0


def _cached(key: str, fn):
    """Return cached value if fresh; else call fn() and cache result.

    On failure, fall back to the last good value (or None) so a transient
    network blip doesn't wipe a useful 60s-old result.
    """
    now = time.time()
    cached = _cache.get(key)
    if cached is not None:
        ts, val = cached
        if now - ts < _CACHE_TTL:
            return val
    try:
        val = fn()
    except Exception:
        return cached[1] if cached is not None else None
    _cache[key] = (now, val)
    return val


def _strip_tags(s: str) -> str:
    """Strip HTML tags and decode entities. Used on Google News titles
    which sometimes embed <ol>...</ol> markup from the publisher."""
    if not s:
        return ""
    no_tags = re.sub(r"<[^>]+>", "", s)
    return html.unescape(no_tags).strip()


# ---------------------------------------------------------------------------
# Google News RSS
# ---------------------------------------------------------------------------

def google_news(query: str, limit: int = 10) -> list[dict]:
    """Scrape Google News RSS. query can be ticker like 'RELIANCE.NS' or 'Nifty 50'."""
    return _cached(f"gn:{query}:{limit}", lambda: _google_news_raw(query, limit))


def _google_news_raw(query: str, limit: int) -> list[dict]:
    try:
        r = _session.get(
            "https://news.google.com/rss/search",
            params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
            timeout=5,
        )
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.text)
        items = []
        for item in root.findall(".//item")[:limit]:
            raw_title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            source = source_el.text if source_el is not None else ""
            try:
                pub_iso = parsedate_to_datetime(pub).isoformat() if pub else ""
            except Exception:
                pub_iso = pub
            items.append({
                "title": _strip_tags(raw_title),
                "link": link,
                "published": pub_iso,
                "source": (source or "").strip(),
                "origin": "Google News",
            })
        return items
    except Exception:
        return []


# ---------------------------------------------------------------------------
# MoneyControl news (best-effort HTML scrape of /news/tags/{tag}.html)
# ---------------------------------------------------------------------------

_MC_TAGS = {
    "RELIANCE": "reliance-industries-ltd",
    "TCS": "tata-consultancy-services-ltd",
    "HDFCBANK": "hdfc-bank-ltd",
    "INFY": "infosys-ltd",
    "ICICIBANK": "icici-bank-ltd",
    "SBIN": "state-bank-of-india",
    "BHARTIARTL": "bharti-airtel-ltd",
    "ITC": "itc-ltd",
    "KOTAKBANK": "kotak-mahindra-bank-ltd",
    "LT": "larsen-and-toubro-ltd",
    "HINDUNILVR": "hindustan-unilever-ltd",
    "AXISBANK": "axis-bank-ltd",
    "ASIANPAINT": "asian-paints-ltd",
    "MARUTI": "maruti-suzuki-india-ltd",
    "WIPRO": "wipro-ltd",
    "HCLTECH": "hcl-technologies-ltd",
    "SUNPHARMA": "sun-pharmaceutical-industries-ltd",
    "TATAMOTORS": "tata-motors-ltd",
    "TATASTEEL": "tata-steel-ltd",
    "ADANIENT": "adani-enterprises-ltd",
    "BAJFINANCE": "bajaj-finance-ltd",
    "BAJAJFINSV": "bajaj-finserv-ltd",
    "NTPC": "ntpc-ltd",
    "POWERGRID": "power-grid-corporation-of-india-ltd",
    "ONGC": "oil-and-natural-gas-corporation-ltd",
    "COALINDIA": "coal-india-ltd",
    "TECHM": "tech-mahindra-ltd",
    "INDUSINDBK": "indusind-bank-ltd",
    "ULTRACEMCO": "ultra-tech-cement-ltd",
    "M&M": "mahindra-and-mahindra-ltd",
    "NESTLEIND": "nestle-india-ltd",
    "TITAN": "titan-company-ltd",
    "JSWSTEEL": "jsw-steel-ltd",
    "HINDALCO": "hindalco-industries-ltd",
    "DRREDDY": "dr-reddys-laboratories-ltd",
    "CIPLA": "cipla-ltd",
    "GRASIM": "grasim-industries-ltd",
    "BPCL": "bharat-petroleum-corporation-ltd",
    "BRITANNIA": "britannia-industries-ltd",
    "EICHERMOT": "eicher-motors-ltd",
    "HEROMOTOCO": "hero-motocorp-ltd",
    "DIVISLAB": "divis-laboratories-ltd",
    "APOLLOHOSP": "apollo-hospitals-enterprises-ltd",
    "SBILIFE": "sbi-life-insurance-company-ltd",
    "HDFCLIFE": "hdfc-life-insurance-company-ltd",
    "TATACONSUM": "tata-consumer-products-ltd",
    "ADANIPORTS": "adani-ports-and-special-economic-zone-ltd",
    "BAJAJ-AUTO": "bajaj-auto-ltd",
    "LTIM": "ltimindtree-ltd",
    "SHRIRAMFIN": "shriram-finance-ltd",
    "TRENT": "trent-ltd",
}


def moneycontrol_news(ticker: str, limit: int = 10) -> list[dict]:
    """Scrape MoneyControl news for an Indian ticker. Ticker should be like 'RELIANCE'."""
    sym = ticker.replace(".NS", "").replace(".BO", "").upper()
    return _cached(f"mc:{sym}:{limit}", lambda: _moneycontrol_news_raw(sym, limit))


def _moneycontrol_news_raw(sym: str, limit: int) -> list[dict]:
    tag = _MC_TAGS.get(sym)
    if not tag:
        # ponytail: unknown ticker — return empty rather than scraping a search
        # page that won't parse cleanly. Extend _MC_TAGS as needed.
        return []
    try:
        r = _session.get(
            f"https://www.moneycontrol.com/news/tags/{tag}.html",
            timeout=5,
        )
        if r.status_code != 200:
            return []
        # ponytail: brittle regex over MoneyControl's HTML — selectors change.
        # Returns empty rather than raising; the rest of the pipeline still works.
        pattern = re.compile(
            r'<a[^>]+href="(https://www\.moneycontrol\.com/news/[^"]+)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        seen = set()
        items: list[dict] = []
        for href, raw in pattern.findall(r.text):
            if href in seen:
                continue
            seen.add(href)
            title = _strip_tags(raw)
            if not title or len(title) < 10:
                continue
            items.append({
                "title": title,
                "link": html.unescape(href),
                "published": "",
                "source": "MoneyControl",
                "origin": "MoneyControl",
            })
            if len(items) >= limit:
                break
        return items
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Investing.com real-time quote (HTML scrape)
# ---------------------------------------------------------------------------

_INVESTING_PRICE_RE = re.compile(
    r'data-test="instrument-price-last"[^>]*>([\d,.\s]+)<',
    re.IGNORECASE,
)
_INVESTING_CHANGE_RE = re.compile(
    r'data-test="instrument-price-change"[^>]*>([+\-\d,.\s]+)<',
    re.IGNORECASE,
)
_INVESTING_PCT_RE = re.compile(
    r'data-test="instrument-price-change-percent"[^>]*>([+\-\d,.\s%]+)<',
    re.IGNORECASE,
)
_INVESTING_NAME_RE = re.compile(
    r'<h1[^>]*>(.*?)</h1>',
    re.IGNORECASE | re.DOTALL,
)


def investing_quote(symbol: str) -> dict | None:
    """Fetch real-time quote from Investing.com.
    symbol e.g. 'currencies/usd-inr', 'commodities/crude-oil'.
    """
    return _cached(f"inv:{symbol}", lambda: _investing_quote_raw(symbol))


def _investing_quote_raw(symbol: str) -> dict | None:
    try:
        r = _session.get(
            f"https://www.investing.com/{symbol}",
            timeout=5,
        )
        if r.status_code != 200:
            return None
        text = r.text

        price_match = _INVESTING_PRICE_RE.search(text)
        change_match = _INVESTING_CHANGE_RE.search(text)
        pct_match = _INVESTING_PCT_RE.search(text)
        name_match = _INVESTING_NAME_RE.search(text)

        if not price_match:
            return None

        def _to_float(s: str) -> float | None:
            s = s.strip().replace(",", "").replace("%", "")
            try:
                return float(s)
            except ValueError:
                return None

        price = _to_float(price_match.group(1))
        if price is None:
            return None

        name = _strip_tags(name_match.group(1)) if name_match else symbol

        return {
            "symbol": symbol,
            "name": name,
            "price": price,
            "change": _to_float(change_match.group(1)) if change_match else None,
            "pct_change": _to_float(pct_match.group(1)) if pct_match else None,
            "source": "Investing.com",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# NSE India official
# ---------------------------------------------------------------------------

def nse_sector_indices() -> list[dict]:
    """Fetch all NSE sector indices from official API."""
    return _cached("nse:all_indices", _nse_sector_indices_raw)


def _nse_sector_indices_raw() -> list[dict]:
    try:
        r = _session.get(
            "https://www.nseindia.com/api/allIndices",
            headers=_NSE_HEADERS,
            timeout=8,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        out = []
        for x in data.get("data", []):
            key = x.get("key") or ""
            if key not in ("BROAD MARKET", "SECTORAL INDICES"):
                continue
            out.append({
                "name": x.get("index", ""),
                "symbol": x.get("indexSymbol", ""),
                "last": x.get("last"),
                "change": x.get("change"),
                "pct_change": x.get("percentChange"),
                "open": x.get("open"),
                "high": x.get("high"),
                "low": x.get("low"),
                "prev_close": x.get("previousClose"),
                "category": key,
            })
        return out
    except Exception:
        return []


def nse_fii_dii() -> dict:
    """Fetch FII/DII daily activity from NSE."""
    return _cached("nse:fiidii", _nse_fii_dii_raw)


def _nse_fii_dii_raw() -> dict:
    try:
        r = _session.get(
            "https://www.nseindia.com/api/fiidiiTradeVol",
            headers=_NSE_HEADERS,
            timeout=8,
        )
        if r.status_code != 200:
            return {}
        rows = r.json() or []
        if not rows:
            return {}
        fii = dii = None
        for row in rows:
            cat = (row.get("category") or "").upper()
            if "FII" in cat and "FII" not in (row.get("subCategory") or "").upper():
                fii = row
            elif "DII" in cat:
                dii = row
        return {
            "date": rows[0].get("date"),
            "fii": _trade_row(fii),
            "dii": _trade_row(dii),
        }
    except Exception:
        return {}


def _trade_row(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {
        "buy": row.get("buyValue"),
        "sell": row.get("sellValue"),
        "net": row.get("netValue"),
    }


# ---------------------------------------------------------------------------
# StockTwits retail sentiment
# ---------------------------------------------------------------------------

def stocktwits_symbol_sentiment(ticker: str, limit: int = 20) -> dict:
    """Fetch recent StockTwits messages for a ticker.

    Returns: {messages: [...], sentiment: {bullish: int, bearish: int}, total: int}
    """
    sym = ticker.replace(".NS", "").replace(".BO", "").upper()
    candidates = [f"{sym}.NSE", f"{sym}.NYSE", f"{sym}.NASDAQ", sym]
    for symbol in candidates:
        out = _cached(f"st:{symbol}:{limit}", lambda s=symbol: _stocktwits_raw(s, limit))
        if out and out.get("messages"):
            return out
    return {"messages": [], "sentiment": {"bullish": 0, "bearish": 0}, "total": 0}


def _stocktwits_raw(symbol: str, limit: int) -> dict:
    try:
        r = _session.get(
            f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json",
            timeout=5,
        )
        if r.status_code != 200:
            return {"messages": [], "sentiment": {"bullish": 0, "bearish": 0}, "total": 0}
        data = r.json()
        msgs = (data.get("messages") or [])[:limit]
        bullish = sum(
            1 for m in msgs
            if (m.get("entities") or {}).get("sentiment", {}).get("basic") == "Bullish"
        )
        bearish = sum(
            1 for m in msgs
            if (m.get("entities") or {}).get("sentiment", {}).get("basic") == "Bearish"
        )
        return {
            "messages": [
                {
                    "user": (m.get("user") or {}).get("username", ""),
                    "body": m.get("body", ""),
                    "created": m.get("created_at", ""),
                    "sentiment": (m.get("entities") or {}).get("sentiment", {}).get("basic", ""),
                }
                for m in msgs
            ],
            "sentiment": {"bullish": bullish, "bearish": bearish},
            "total": len(msgs),
        }
    except Exception:
        return {"messages": [], "sentiment": {"bullish": 0, "bearish": 0}, "total": 0}


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def all_news_for_ticker(ticker: str, limit_per_source: int = 5) -> dict:
    """Aggregate news from all sources for a ticker."""
    return {
        "ticker": ticker,
        "yfinance": _news_for_ticker(ticker, limit_per_source),
        "google_news": google_news(f"{ticker} stock", limit_per_source),
        "moneycontrol": moneycontrol_news(ticker, limit_per_source),
        "stocktwits": stocktwits_symbol_sentiment(ticker, limit_per_source),
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }