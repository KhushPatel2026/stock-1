"""Macro context fetcher: Indian/global sector indices, commodities, FX, volatility.

Pulls a structured snapshot via yfinance in parallel, then derives a simple
regime summary (india/global bias, risk-on/off, strongest/weakest sectors)
that the rest of the strategy code can consume.
"""
from __future__ import annotations

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf


SECTORS = {
    "Nifty Bank": "^NSEBANK",
    "Nifty IT": "^CNXIT",
    "Nifty Auto": "^CNXAUTO",
    "Nifty Pharma": "^CNXPHARMA",
    "Nifty FMCG": "^CNXFMCG",
    "Nifty Metal": "^CNXMETAL",
    "Nifty Realty": "^CNXREALTY",
    "Nifty Energy": "^CNXENERGY",
    "Nifty Financial Services": "^CNXFINANCE",
    "Nifty PSU Bank": "^CNXPSUBANK",
}

GLOBAL_INDICES = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "FTSE 100": "^FTSE",
    "DAX": "^GDAXI",
    "Shanghai Composite": "^SSEC",
}

COMMODITIES = {
    "Crude Oil (WTI)": "CL=F",
    "Brent Crude": "BZ=F",
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Copper": "HG=F",
    "Natural Gas": "NG=F",
}

FX = {
    "USD/INR": "INR=X",
    "EUR/USD": "EURUSD=X",
    "USD/JPY": "JPY=X",
    "GBP/USD": "GBPUSD=X",
}

VOLATILITY = {
    "India VIX": "^INDIAVIX",
    "VIX (S&P)": "^VIX",
}

NIFTY50 = "^NSEI"

ALL_SYMBOLS = (
    list(SECTORS.values())
    + list(GLOBAL_INDICES.values())
    + list(COMMODITIES.values())
    + list(FX.values())
    + list(VOLATILITY.values())
    + [NIFTY50]
)


def _all_name_map() -> dict[str, str]:
    m: dict[str, str] = {}
    m.update(SECTORS)
    m.update(GLOBAL_INDICES)
    m.update(COMMODITIES)
    m.update(FX)
    m.update(VOLATILITY)
    m["Nifty 50"] = NIFTY50
    return m


def has_internet(host: str = "query1.finance.yahoo.com", port: int = 443, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def fetch_one(symbol: str, period: str = "3mo") -> dict | None:
    try:
        t = yf.Ticker(symbol)
        df = t.history(period=period, auto_adjust=True)
        if df is None or df.empty or len(df) < 5:
            return None
        close = df["Close"]
        last = float(close.iloc[-1])
        prev = float(close.iloc[-2]) if len(close) >= 2 else last
        chg_1d = (last / prev - 1) * 100 if prev else 0
        chg_5d = (last / float(close.iloc[-6]) - 1) * 100 if len(close) >= 6 else 0
        chg_20d = (last / float(close.iloc[-21]) - 1) * 100 if len(close) >= 21 else 0
        if chg_20d > 2:
            trend = "up"
        elif chg_20d < -2:
            trend = "down"
        else:
            trend = "sideways"
        return {
            "symbol": symbol,
            "last": round(last, 2),
            "chg_1d_pct": round(chg_1d, 2),
            "chg_5d_pct": round(chg_5d, 2),
            "chg_20d_pct": round(chg_20d, 2),
            "trend": trend,
            "as_of": df.index[-1].strftime("%Y-%m-%d"),
        }
    except Exception:
        return None


def fetch_all() -> dict:
    sections = {
        "sectors": list(SECTORS.keys()),
        "global": list(GLOBAL_INDICES.keys()),
        "commodities": list(COMMODITIES.keys()),
        "fx": list(FX.keys()),
        "volatility": list(VOLATILITY.keys()),
    }
    name_map = _all_name_map()
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_one, sym): sym for sym in ALL_SYMBOLS}
        for fut in as_completed(futures, timeout=30):
            sym = futures[fut]
            try:
                r = fut.result(timeout=5)
            except Exception:
                r = None
            if r:
                results[sym] = r

    out = {"as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    for section, names in sections.items():
        out[section] = []
        for name in names:
            sym = name_map[name]
            d = results.get(sym)
            if d:
                d["name"] = name
                out[section].append(d)
    n = results.get(NIFTY50)
    if n:
        n["name"] = "Nifty 50"
        out["nifty50"] = n
    return out


def regime_summary(macro: dict) -> dict:
    nifty = macro.get("nifty50") or {}
    india_vix = next((x for x in macro.get("volatility", []) if "India" in x.get("name", "")), None)
    sp = next((x for x in macro.get("global", []) if "S&P" in x.get("name", "")), None)

    n_chg = nifty.get("chg_20d_pct", 0)
    vix = india_vix.get("last", 15) if india_vix else 15
    if n_chg > 2 and vix < 18:
        india_regime = "bullish"
    elif n_chg < -2 or vix > 22:
        india_regime = "bearish"
    else:
        india_regime = "neutral"

    sp_chg = sp.get("chg_20d_pct", 0) if sp else 0
    if sp_chg > 2:
        global_regime = "bullish"
    elif sp_chg < -2:
        global_regime = "bearish"
    else:
        global_regime = "neutral"

    crude = next((x for x in macro.get("commodities", []) if "Crude" in x.get("name", "")), None)
    gold = next((x for x in macro.get("commodities", []) if x.get("name") == "Gold"), None)
    crude_chg = crude.get("chg_20d_pct", 0) if crude else 0
    gold_chg = gold.get("chg_20d_pct", 0) if gold else 0
    if crude_chg > 2 and gold_chg < -1:
        commodities_bias = "risk-on"
    elif crude_chg < -2 and gold_chg > 1:
        commodities_bias = "risk-off"
    else:
        commodities_bias = "mixed"

    if vix > 20 or (gold_chg > 2 and sp_chg < -1):
        risk = "risk-off"
    elif vix < 16 and gold_chg < -1 and sp_chg > 1:
        risk = "risk-on"
    else:
        risk = "neutral"

    sectors = macro.get("sectors", [])
    sorted_sectors = sorted(sectors, key=lambda x: -x.get("chg_20d_pct", 0))
    strongest = sorted_sectors[:3] if sorted_sectors else []
    weakest = sorted_sectors[-3:] if sorted_sectors else []

    summary = (
        f"India {india_regime} ({n_chg:+.1f}% 20d, VIX {vix:.1f}), "
        f"Global {global_regime} (S&P {sp_chg:+.1f}% 20d), "
        f"{commodities_bias}, {risk}. "
        f"Strongest sectors: {', '.join(s.get('name', '?').replace('Nifty ', '') for s in strongest) or 'n/a'}. "
        f"Weakest: {', '.join(s.get('name', '?').replace('Nifty ', '') for s in weakest) or 'n/a'}."
    )

    return {
        "india_regime": india_regime,
        "global_regime": global_regime,
        "commodities_bias": commodities_bias,
        "risk_on_off": risk,
        "vix": vix,
        "nifty_20d": n_chg,
        "sp500_20d": sp_chg,
        "strongest_sectors": [s.get("name") for s in strongest],
        "weakest_sectors": [s.get("name") for s in weakest],
        "summary": summary,
    }


def news_for_ticker(ticker: str, limit: int = 5) -> list[dict]:
    """Fetch recent news for a ticker via yfinance. Returns [{title, publisher, link, published}]."""
    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        out = []
        for n in news[:limit]:
            # yfinance nests fields under "content" in newer versions
            content = n.get("content", {}) if isinstance(n.get("content"), dict) else {}
            title = content.get("title") or n.get("title", "")
            publisher = ""
            if content.get("provider"):
                publisher = content["provider"].get("displayName", "")
            elif n.get("publisher"):
                publisher = n["publisher"]
            link = (content.get("canonicalUrl") or {}).get("url") or n.get("link", "")
            pub_date = content.get("pubDate", "")
            summary = content.get("summary", "")
            out.append({
                "title": title,
                "publisher": publisher,
                "link": link,
                "published": pub_date,
                "summary": summary[:200] if summary else "",
            })
        return out
    except Exception:
        return []