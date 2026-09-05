"""Upstox Analytics + Portfolio client."""
import os
import requests

BASE = "https://api.upstox.com"


class UpstoxError(Exception):
    pass


class UpstoxAuthError(UpstoxError):
    pass


class UpstoxNotFoundError(UpstoxError):
    pass


class UpstoxClient:
    def __init__(self, access_token: str | None = None):
        self.access_token = access_token or os.getenv("UPSTOX_ACCESS_TOKEN", "")
        self.api_key = os.getenv("UPSTOX_API_KEY", "")
        self._session = requests.Session()

    def _headers(self) -> dict:
        h = {"Accept": "application/json"}
        if self.access_token:
            h["Authorization"] = f"Bearer {self.access_token}"
        return h

    def is_authenticated(self) -> bool:
        return bool(self.access_token)

    def set_token(self, token: str) -> None:
        self.access_token = token

    def get_profile(self) -> dict:
        r = self._session.get(f"{BASE}/v2/user/profile", headers=self._headers(), timeout=10)
        return self._handle(r)

    def get_holdings(self) -> dict:
        r = self._session.get(f"{BASE}/v2/portfolio/long-term-holdings", headers=self._headers(), timeout=10)
        return self._handle(r)

    def get_positions(self) -> dict:
        r = self._session.get(f"{BASE}/v2/portfolio/short-term-positions", headers=self._headers(), timeout=10)
        return self._handle(r)

    def get_funds(self) -> dict:
        r = self._session.get(f"{BASE}/v2/user/get-funds-and-margin", headers=self._headers(), timeout=10)
        return self._handle(r)

    def get_quote(self, symbol: str, exchange: str = "NSE_EQ") -> dict:
        r = self._session.get(f"{BASE}/v2/quote/{exchange}/{symbol}", headers=self._headers(), timeout=10)
        return self._handle(r)

    def get_option_chain(self, symbol: str, expiry: str | None = None) -> dict:
        params = {"symbol": symbol}
        if expiry:
            params["expiry"] = expiry
        r = self._session.get(f"{BASE}/v2/option/chain", params=params, headers=self._headers(), timeout=15)
        return self._handle(r)

    def get_pcr(self, symbol: str) -> dict:
        r = self._session.get(f"{BASE}/v2/analytics/PCR", params={"symbol": symbol}, headers=self._headers(), timeout=10)
        return self._handle(r)

    def get_india_vix(self) -> dict:
        r = self._session.get(f"{BASE}/v2/analytics/India-VIX", headers=self._headers(), timeout=10)
        return self._handle(r)

    def get_market_oi(self) -> dict:
        r = self._session.get(f"{BASE}/v2/analytics/open-interest", headers=self._headers(), timeout=10)
        return self._handle(r)

    def _handle(self, r: requests.Response):
        if r.status_code == 401:
            raise UpstoxAuthError("token expired or invalid — re-authorize via Upstox OAuth")
        if r.status_code == 404:
            raise UpstoxNotFoundError(f"{r.url}: {r.text[:200]}")
        if r.status_code >= 400:
            raise UpstoxError(f"upstox {r.status_code}: {r.text[:200]}")
        try:
            return r.json()
        except Exception:
            return {"raw": r.text}


def to_upstox_symbol(ticker: str) -> tuple[str, str]:
    """Map yfinance ticker → Upstox (exchange, symbol)."""
    if ticker.endswith(".NS"):
        return ("NSE_EQ", ticker[:-3])
    if ticker.endswith(".BO"):
        return ("BSE_EQ", ticker[:-3])
    return ("NSE_EQ", ticker)
