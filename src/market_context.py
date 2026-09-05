"""Market context for the Trade Idea tab — regime, global, sector, commodity, news.

Everything here is FREE, no API keys:
- Prices/regime: yfinance (^NSEI, ^INDIAVIX, ^GSPC, ^IXIC, ^TNX, USDINR=X,
  BZ=F, GC=F, HG=F, SI=F) via the verified `src.data` layer.
- News: Google News India RSS first, yfinance Ticker.news fallback.
- Company name: screener.in (falls back to ticker root).

Never raises — every section degrades to None/[] with the reason kept.
"""
from __future__ import annotations
import re
import time
import html as _html
from datetime import datetime, timezone
import pandas as pd
import requests

from src.data import fetch_many, fetch

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}

INDICES = {"Nifty 50": "^NSEI", "India VIX": "^INDIAVIX"}
GLOBAL = {
    "S&P 500": "^GSPC", "Nasdaq": "^IXIC", "US 10Y": "^TNX",
    "USD-INR": "USDINR=X", "Brent Crude": "BZ=F", "Gold": "GC=F",
    "Copper": "HG=F", "Silver": "SI=F",
}
# sector -> the commodity that moves it most (shown as "linked" line)
SECTOR_COMMODITY = {"Energy": "Brent Crude"}
TICKER_COMMODITY = {
    "TATASTEEL.NS": "Copper", "JSWSTEEL.NS": "Copper", "HINDALCO.NS": "Copper",
    "COALINDIA.NS": "Brent Crude", "ONGC.NS": "Brent Crude", "BPCL.NS": "Brent Crude",
    "RELIANCE.NS": "Brent Crude", "ASIANPAINT.NS": "Brent Crude",
}

_POS_WORDS = ("rally", "rallies", "surge", "surges", "jumps", "soars", "upgrade",
              "upgrades", "record", "profit", "growth", "gains", "bull", "outperform",
              "beats", "bonus", "dividend", "buyback", "high")
_NEG_WORDS = ("fall", "falls", "drop", "drops", "plunge", "crash", "downgrade",
              "downgrades", "loss", "losses", "probe", "fraud", "warning", "decline",
              "bear", "misses", "cut", "selloff", "concern", "risk", "low")


def tone_of_title(title: str) -> str:
    """Keyword headline tone: positive / negative / neutral. Crude but transparent."""
    t = title.lower()
    pos = sum(1 for w in _POS_WORDS if w in t)
    neg = sum(1 for w in _NEG_WORDS if w in t)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def vix_label(vix: float | None) -> str:
    if vix is None:
        return "unknown"
    if vix < 13:
        return "calm"
    if vix < 18:
        return "normal"
    if vix < 25:
        return "elevated"
    return "fear"


def _day_change(df: pd.DataFrame) -> float | None:
    try:
        c = df["close"].astype(float)
        if len(c) < 2:
            return None
        return float(c.iloc[-1] / c.iloc[-2] - 1) * 100
    except Exception:
        return None


# Market-wide snapshot is identical for every ticker — cache 20 min so a
# 5-ticker scan doesn't refetch indices/global/breadth five times.
_MARKET_CACHE: dict[str, tuple[float, dict]] = {}
_MARKET_TTL_S = 20 * 60


def _market_snapshot() -> dict:
    import time as _time
    hit = _MARKET_CACHE.get("market")
    if hit and _time.time() - hit[0] < _MARKET_TTL_S:
        return hit[1]
    snap: dict = {"indices": {}, "regime": {}, "breadth": {}, "global": {}}
    try:
        snap["indices"] = _snapshot(INDICES)
        snap["regime"] = _nifty_regime()
        snap["breadth"] = _breadth()
        snap["global"] = _snapshot(GLOBAL)
    except Exception:
        pass
    _MARKET_CACHE["market"] = (_time.time(), snap)
    return snap


def _snapshot(symbols: dict[str, str], period: str = "5d") -> dict[str, dict]:
    out = {}
    try:
        data = fetch_many(list(symbols.values()), period=period)
    except Exception:
        data = {}
    inv = {v: k for k, v in symbols.items()}
    for sym, df in data.items():
        try:
            out[inv.get(sym, sym)] = {
                "price": round(float(df["close"].iloc[-1]), 2),
                "day_pct": round(_day_change(df) or 0, 2),
                "as_of": str(df.index[-1].date()),
            }
        except Exception:
            continue
    return out


def _nifty_regime() -> dict:
    out: dict = {"trend": None, "above_sma200": None, "month_pct": None}
    try:
        df = fetch("^NSEI", period="1y")
        c = df["close"].astype(float)
        out["above_sma200"] = bool(c.iloc[-1] > c.rolling(200).mean().iloc[-1])
        out["month_pct"] = round(float(c.iloc[-1] / c.iloc[-21] - 1) * 100, 2)
        out["trend"] = "uptrend" if out["above_sma200"] else "downtrend"
    except Exception as e:
        out["error"] = str(e)[:100]
    return out


def _breadth() -> dict:
    """% of Nifty50 stocks above their 50DMA. Slow first run, then disk-cached."""
    from src.universe import NIFTY50
    out: dict = {"above_50dma_pct": None, "n": 0}
    try:
        data = fetch_many(NIFTY50, period="4mo")
        hit = 0
        for df in data.values():
            try:
                c = df["close"].astype(float)
                if len(c) >= 50 and c.iloc[-1] > c.rolling(50).mean().iloc[-1]:
                    hit += 1
            except Exception:
                continue
        if data:
            out = {"above_50dma_pct": round(hit / len(data) * 100, 1), "n": len(data)}
    except Exception as e:
        out["error"] = str(e)[:100]
    return out


def _sector(ticker: str) -> dict:
    from src.universe import SECTORS
    out: dict = {"name": None, "day_pct": None, "month_vs_nifty": None}
    sector = next((s for s, m in SECTORS.items() if ticker in m), None)
    if not sector:
        return out
    out["name"] = sector
    try:
        members = [m for m in SECTORS[sector] if m != ticker][:6]
        data = fetch_many([ticker] + members, period="2mo")
        days, months = [], []
        for t, df in data.items():
            c = df["close"].astype(float)
            if len(c) >= 2:
                days.append(float(c.iloc[-1] / c.iloc[-2] - 1) * 100)
            if len(c) >= 21:
                months.append(float(c.iloc[-1] / c.iloc[-21] - 1) * 100)
        if days:
            out["day_pct"] = round(sum(days) / len(days), 2)
        if months:
            try:
                nifty = fetch("^NSEI", period="2mo")["close"].astype(float)
                nifty_m = float(nifty.iloc[-1] / nifty.iloc[-21] - 1) * 100
                out["month_vs_nifty"] = round(sum(months) / len(months) - nifty_m, 2)
            except Exception:
                pass
    except Exception as e:
        out["error"] = str(e)[:100]
    return out


def _company_name(ticker: str) -> str:
    try:
        from src.screener import fetch_ratios
        name = (fetch_ratios(ticker).get("company_name") or "").replace(" Ltd", "").strip()
        if name:
            return name
    except Exception:
        pass
    return ticker.split(".")[0]


def _news_gnews(query: str, n: int = 5) -> list[dict]:
    try:
        r = requests.get(
            "https://news.google.com/rss/search",
            params={"q": f"{query} stock OR shares", "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
            headers=UA, timeout=20)
        if r.status_code != 200:
            return []
        items = re.findall(r"<item>(.*?)</item>", r.text, re.DOTALL)[:n]
        out = []
        for it in items:
            def tag(name: str) -> str:
                m = re.search(rf"<{name}>(.*?)</{name}>", it, re.DOTALL)
                return _html.unescape(m.group(1).strip()) if m else ""
            raw_title = tag("title")
            src = raw_title.split(" - ")[-1] if " - " in raw_title else ""
            title = re.sub(r" - [^-]+$", "", raw_title)
            link = tag("link")
            pub = tag("pubDate")[:16]
            if not title:
                continue
            out.append({"title": title[:160], "source": src[:40], "time": pub,
                        "link": link, "tone": tone_of_title(title)})
        return out
    except Exception:
        return []


def _news_yf(ticker: str, n: int = 5) -> list[dict]:
    try:
        import yfinance as yf
        items = (yf.Ticker(ticker).news or [])[:n]
        out = []
        for a in items:
            c = a.get("content", a) if isinstance(a, dict) else {}
            title = str(c.get("title", ""))[:160]
            if not title:
                continue
            out.append({"title": title, "source": str(c.get("provider", {}).get("displayName", ""))[:40],
                        "time": str(c.get("pubDate", ""))[:16], "link": str(c.get("canonicalUrl", "")),
                        "tone": tone_of_title(title)})
        return out
    except Exception:
        return []


def get_news(ticker: str, n: int = 5) -> dict:
    """Google News IN first, yfinance fallback. Returns {items, source}."""
    name = _company_name(ticker)
    items = _news_gnews(name, n)
    if items:
        return {"items": items, "source": "Google News IN"}
    items = _news_yf(ticker, n)
    return {"items": items, "source": "Yahoo Finance" if items else "none"}


def get_context(ticker: str) -> dict:
    """Full market-weather card for one ticker. Never raises."""
    ticker = (ticker or "").strip().upper()
    ctx: dict = {"ticker": ticker, "as_of": "", "market": {}, "global": {},
                 "sector": {}, "commodity": {}, "news": {}, "cautions": [], "summary": ""}
    try:
        snap = _market_snapshot()
        idx = snap.get("indices", {})
        nifty = idx.get("Nifty 50", {})
        vix = idx.get("India VIX", {})
        regime = snap.get("regime", {})
        breadth = snap.get("breadth", {})
        ctx["market"] = {
            "nifty": nifty.get("price"), "nifty_day_pct": nifty.get("day_pct"),
            "nifty_trend": regime.get("trend"), "nifty_month_pct": regime.get("month_pct"),
            "breadth_pct": breadth.get("above_50dma_pct"),
            "vix": vix.get("price"), "vix_state": vix_label(vix.get("price")),
            "as_of": nifty.get("as_of", ""),
        }
        ctx["as_of"] = nifty.get("as_of", "")
        ctx["global"] = snap.get("global", {})
        ctx["sector"] = _sector(ticker)
        comm_name = TICKER_COMMODITY.get(ticker)
        if not comm_name:
            from src.universe import SECTORS
            sector = next((s for s, m in SECTORS.items() if ticker in m), None)
            comm_name = SECTOR_COMMODITY.get(sector or "")
        if comm_name and comm_name in ctx["global"]:
            g = ctx["global"][comm_name]
            ctx["commodity"] = {"name": comm_name, **g}
        ctx["news"] = get_news(ticker)

        c: list[str] = []
        if ctx["market"].get("vix_state") in ("elevated", "fear"):
            c.append(f"India VIX {ctx['market'].get('vix')} ({ctx['market']['vix_state']}) — reduce size, expect gaps.")
        if ctx["market"].get("nifty_trend") == "downtrend":
            c.append("Nifty below 200DMA — market headwind; longs need stronger stock-level edge.")
        sp = ctx["global"].get("S&P 500", {}).get("day_pct")
        if sp is not None and sp <= -1.0:
            c.append(f"S&P 500 fell {sp}% overnight — expect a weak Nifty open.")
        tones = [a["tone"] for a in ctx["news"].get("items", [])]
        if len(tones) >= 3 and tones.count("negative") > tones.count("positive") + 1:
            c.append("Fresh headlines skew negative — check news before entering.")
        ctx["cautions"] = c
        m = ctx["market"]
        parts = []
        if m.get("nifty") is not None:
            parts.append(f"Nifty {m['nifty']:,.0f} ({m.get('nifty_day_pct', 0):+.1f}%, {m.get('nifty_trend', '?')})")
        if m.get("vix") is not None:
            parts.append(f"VIX {m['vix']} {m.get('vix_state', '')}")
        if sp is not None:
            parts.append(f"S&P 500 {sp:+.1f}% overnight")
        sec = ctx["sector"]
        if sec.get("name") and sec.get("day_pct") is not None:
            parts.append(f"{sec['name']} sector {sec['day_pct']:+.1f}% today")
        if ctx["market"].get("breadth_pct") is not None:
            parts.append(f"breadth {ctx['market']['breadth_pct']:.0f}% above 50DMA")
        ctx["summary"] = " · ".join(parts)
    except Exception as e:  # noqa: BLE001 — context must never break the verdict
        ctx["error"] = str(e)[:120]
    return ctx


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def macro_overlay(ticker: str, ctx: dict, atr_pct: float | None = None) -> dict:
    """Turn market weather into a vote adjustment + sizing. Pure function of ctx.

    Returns {score (-30..+30), reasons[], sizing_pct, sizing_note, capped}.
    Positive = tailwind for longs. Every point is explained in `reasons`.
    """
    m = ctx.get("market", {}) or {}
    g = ctx.get("global", {}) or {}
    sec = ctx.get("sector", {}) or {}
    tones = [a.get("tone") for a in (ctx.get("news", {}) or {}).get("items", [])]
    score = 0.0
    reasons: list[str] = []

    def add(pts: float, why: str):
        nonlocal score
        if pts:
            score += pts
            reasons.append(f"{why} ({pts:+.0f})")

    trend = m.get("nifty_trend")
    add(8 if trend == "uptrend" else (-8 if trend == "downtrend" else 0),
        "Nifty above 200DMA" if trend == "uptrend" else "Nifty below 200DMA" if trend == "downtrend" else "Nifty trend unknown")
    if m.get("nifty_month_pct") is not None:
        add(_clamp(round(m["nifty_month_pct"] / 2), -6, 6), f"Nifty {m['nifty_month_pct']:+.1f}% this month")
    vix_state = m.get("vix_state")
    add({"calm": 2, "normal": 0, "elevated": -6, "fear": -12}.get(vix_state or "", 0),
        f"VIX {m.get('vix')} {vix_state}" if m.get("vix") is not None else "VIX unknown")
    b = m.get("breadth_pct")
    if b is not None:
        add(4 if b >= 60 else (-4 if b <= 40 else 0), f"breadth {b:.0f}% above 50DMA")
    sv = sec.get("month_vs_nifty")
    if sv is not None:
        add(_clamp(round(sv / 2), -4, 4), f"{sec.get('name', 'sector')} {sv:+.1f}% vs Nifty (1M)")
    sp = (g.get("S&P 500") or {}).get("day_pct")
    if sp is not None:
        add(_clamp(round(sp * 2), -4, 4), f"US overnight {sp:+.1f}%")
    if len(tones) >= 3:
        net = tones.count("positive") - tones.count("negative")
        add(_clamp(net * 2, -4, 4), f"news tone net {net:+d}")

    score = _clamp(round(score), -30, 30)

    # sizing: start 1% risk, shrink with fear/volatility
    sizing, notes = 1.0, []
    if vix_state == "fear":
        sizing, notes = 0.25, ["VIX fear — quarter size or stay out"]
    elif vix_state == "elevated":
        sizing, notes = 0.5, ["VIX elevated — half size"]
    if atr_pct is not None and atr_pct > 3.0 and sizing > 0.25:
        sizing, notes = min(sizing, 0.5), notes + [f"ATR {atr_pct:.1f}% — volatile stock, half size"]
    sizing_note = "; ".join(notes) if notes else "normal size (1% risk)"
    return {
        "ticker": ticker,
        "score": score,
        "reasons": reasons,
        "sizing_pct": sizing,
        "sizing_note": sizing_note,
        "capped": False,
    }
