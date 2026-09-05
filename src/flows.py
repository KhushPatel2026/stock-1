"""FII/DII daily flows — Moneycontrol, free, no key. 12h disk cache.

Moneycontrol's FII/DII activity page carries a daily table:
[date, FII buy, FII sell, FII net, DII buy, DII sell, DII net] in Rs Cr.
First triplet = FII, second = DII (page's long-standing layout; FIIs the marginal
price-setters, DIIs the cushion — reflected in how the overlay weights them).

Never raises: {} / [] on any failure so the overlay simply scores 0.
"""
from __future__ import annotations
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

CACHE = Path("data/cache/flows.json")
CACHE.parent.mkdir(parents=True, exist_ok=True)
TTL_HOURS = 12
URL = "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}


def _parse(html: str) -> list[dict]:
    tbodies = re.findall(r"<tbody>(.*?)</tbody>", html, re.DOTALL)
    rows = []
    for b in tbodies:
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", b, re.DOTALL):
            cells = [re.sub(r"<[^>]+>", "", c).strip().split("\n")[0].strip()
                     for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.DOTALL)]
            if len(cells) >= 7 and re.match(r"\d{2}-[A-Za-z]{3}-\d{4}", cells[0] or ""):
                try:
                    rows.append({
                        "date": cells[0],
                        "fii_net_cr": float(cells[3].replace(",", "")),
                        "dii_net_cr": float(cells[6].replace(",", "")),
                    })
                except ValueError:
                    continue
    # newest first, drop dupes
    seen, out = set(), []
    for r in rows:
        if r["date"] not in seen:
            seen.add(r["date"])
            out.append(r)
    return out


def fetch_flows(days: int = 10, *, use_cache: bool = True) -> list[dict]:
    if use_cache and CACHE.exists():
        try:
            cached = json.loads(CACHE.read_text())
            ts = datetime.fromisoformat(cached.get("fetched_at", "1970-01-01T00:00:00+00:00"))
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            if age_h < TTL_HOURS and cached.get("rows"):
                return cached["rows"][:days]
        except Exception:
            pass
    try:
        r = requests.get(URL, headers=UA, timeout=25)
        if r.status_code != 200:
            return []
        rows = _parse(r.text)[:days]
        if rows:
            try:
                CACHE.write_text(json.dumps({"rows": rows,
                                             "fetched_at": datetime.now(timezone.utc).isoformat()}))
            except Exception:
                pass
        return rows
    except Exception:
        return []


def five_day_sums(rows: list[dict] | None = None) -> dict:
    """{fii_5d_cr, dii_5d_cr} over the latest 5 sessions. {} when unavailable."""
    rows = rows if rows is not None else fetch_flows(5)
    if len(rows) < 3:
        return {}
    last5 = rows[:5]
    return {
        "fii_5d_cr": round(sum(r["fii_net_cr"] for r in last5), 1),
        "dii_5d_cr": round(sum(r["dii_net_cr"] for r in last5), 1),
        "as_of": last5[0]["date"],
    }
