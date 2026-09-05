"""NSE option chain — free, no key. Handshake (cookies) + graceful fallback.

NSE blocks some networks/IPs outright; every function returns {} / None on any
failure so callers always degrade (yfinance chain -> BS synthetic). Never raises.

Current use: ATM implied vol calibrates the Black-Scholes fallback in
`src/options_real` (real smile level instead of a flat 0.15 floor).
"""
from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

CACHE_DIR = Path("data/cache/nse")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
TTL_HOURS = 24

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": _UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
        "X-Requested-With": "XMLHttpRequest",
    })
    return s


def _get(s: requests.Session, url: str, timeout: int = 20):
    for _ in range(2):
        try:
            r = s.get(url, timeout=timeout)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                return r.json()
        except Exception:
            pass
        time.sleep(1.0)
    return {}


def fetch_chain(symbol: str, *, use_cache: bool = True) -> dict:
    """Full NSE equity chain for an NSE symbol (e.g. 'RELIANCE'). {} on failure."""
    sym = symbol.split(".")[0].upper()
    p = CACHE_DIR / f"{sym}.json"
    if use_cache and p.exists():
        try:
            cached = json.loads(p.read_text())
            ts = datetime.fromisoformat(cached.get("fetched_at", "1970-01-01T00:00:00+00:00"))
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            if age_h < TTL_HOURS and cached.get("strikes"):
                return cached
        except Exception:
            pass
    try:
        s = _session()
        s.get("https://www.nseindia.com/", timeout=20)  # cookie handshake
        time.sleep(1.0)
        data = _get(s, f"https://www.nseindia.com/api/option-chain-equities?symbol={sym}")
        recs = (data.get("records") or {})
        rows = recs.get("data") or []
        strikes = []
        for row in rows:
            ce, pe = row.get("CE") or {}, row.get("PE") or {}
            strikes.append({
                "strike": row.get("strikePrice"),
                "expiry": row.get("expiryDate"),
                "ce_bid": ce.get("bidprice"), "ce_ask": ce.get("askPrice"),
                "ce_ltp": ce.get("lastPrice"), "ce_iv": ce.get("impliedVolatility"),
                "ce_oi": ce.get("openInterest"),
                "pe_bid": pe.get("bidprice"), "pe_ask": pe.get("askPrice"),
                "pe_ltp": pe.get("lastPrice"), "pe_iv": pe.get("impliedVolatility"),
                "pe_oi": pe.get("openInterest"),
            })
        out = {
            "symbol": sym,
            "source": "nseindia.com",
            "underlying": (recs.get("underlyingValue")),
            "expiries": recs.get("expiryDates") or [],
            "strikes": strikes,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        if strikes:
            try:
                p.write_text(json.dumps(out, default=str))
            except Exception:
                pass
            return out
        return {}
    except Exception:
        return {}


def atm_iv(symbol: str, underlying: float | None = None) -> float | None:
    """ATM call IV (decimal, e.g. 0.18) from the nearest expiry. None on failure."""
    chain = fetch_chain(symbol)
    strikes = chain.get("strikes") or []
    if not strikes:
        return None
    spot = underlying or chain.get("underlying")
    if not spot:
        return None
    first_exp = (chain.get("expiries") or [None])[0]
    cands = [r for r in strikes if (first_exp is None or r.get("expiry") == first_exp)
             and r.get("ce_iv")]
    if not cands:
        cands = [r for r in strikes if r.get("ce_iv")]
    if not cands:
        return None
    best = min(cands, key=lambda r: abs((r.get("strike") or 0) - spot))
    try:
        return float(best["ce_iv"]) / 100.0
    except Exception:
        return None
