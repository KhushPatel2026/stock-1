"""Tests for Upstox client + portfolio enrichment.

Live network tests are skipped unless UPSTOX_ACCESS_TOKEN is set in env.
"""
from __future__ import annotations
import os
import pytest

from src.upstox import (
    UpstoxClient,
    UpstoxError,
    UpstoxAuthError,
    UpstoxNotFoundError,
    to_upstox_symbol,
)
from src.portfolio import fetch_portfolio

LIVE = bool(os.getenv("UPSTOX_ACCESS_TOKEN"))


# ---------------------------------------------------------------------------
# Pure helpers — always run
# ---------------------------------------------------------------------------

def test_to_upstox_symbol_nse():
    assert to_upstox_symbol("RELIANCE.NS") == ("NSE_EQ", "RELIANCE")


def test_to_upstox_symbol_bse():
    assert to_upstox_symbol("TCS.BO") == ("BSE_EQ", "TCS")


def test_to_upstox_symbol_bare_defaults_to_nse():
    assert to_upstox_symbol("INFY") == ("NSE_EQ", "INFY")


def test_client_unauthenticated():
    """Client with no token reports not authenticated and raises UpstoxAuthError on calls."""
    c = UpstoxClient(access_token="")
    assert not c.is_authenticated()
    with pytest.raises(UpstoxAuthError):
        c.get_profile()


def test_set_token_late_binding():
    c = UpstoxClient(access_token="")
    assert not c.is_authenticated()
    c.set_token("abc123")
    assert c.is_authenticated()


def test_fetch_portfolio_without_token():
    """fetch_portfolio returns the unauthenticated envelope when no token."""
    res = fetch_portfolio(None)
    assert res["authenticated"] is False
    assert "message" in res


# ---------------------------------------------------------------------------
# Live network tests — skip if no token
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not LIVE, reason="UPSTOX_ACCESS_TOKEN not set")
def test_live_profile():
    c = UpstoxClient()
    p = c.get_profile()
    assert isinstance(p, dict)


@pytest.mark.skipif(not LIVE, reason="UPSTOX_ACCESS_TOKEN not set")
def test_live_holdings():
    c = UpstoxClient()
    h = c.get_holdings()
    # Upstox returns {"data": [...]} or just a list
    items = h.get("data", h) if isinstance(h, dict) else h
    assert isinstance(items, list)


@pytest.mark.skipif(not LIVE, reason="UPSTOX_ACCESS_TOKEN not set")
def test_live_quote():
    c = UpstoxClient()
    q = c.get_quote("NSE_EQ", "RELIANCE")
    assert isinstance(q, dict)


@pytest.mark.skipif(not LIVE, reason="UPSTOX_ACCESS_TOKEN not set")
def test_live_india_vix():
    c = UpstoxClient()
    v = c.get_india_vix()
    assert isinstance(v, dict)


# ---------------------------------------------------------------------------
# FastAPI endpoint tests — exercise the API surface w/o making live Upstox calls
# ---------------------------------------------------------------------------

@pytest.fixture
def client_app():
    """Spin up the FastAPI app with TestClient; ensure no token is set."""
    from fastapi.testclient import TestClient
    import api.main as api_main
    api_main._upstox_token = None
    return TestClient(api_main.app)


def test_upstox_status_unauthenticated(client_app):
    r = client_app.get("/api/upstox/status")
    assert r.status_code == 200
    assert r.json() == {"authenticated": False}


def test_portfolio_without_token(client_app):
    r = client_app.get("/api/portfolio")
    assert r.status_code == 200
    body = r.json()
    assert body["authenticated"] is False


def test_upstox_quote_without_token(client_app):
    """Quote endpoint will pass through and try to hit Upstox. We only verify
    that the request reaches the route (any 500 with auth error is acceptable
    when no token — the route doesn't pre-check). With a fake token, Upstox
    returns 401 → we surface that. Without a token, the request is unauthenticated
    but Upstox still responds."""
    r = client_app.get("/api/upstox/quote/NSE_EQ/RELIANCE")
    # Either Upstox returns 401 (we raise UpstoxAuthError → 500) or some other error.
    # We just verify the route exists and responds (not 404).
    assert r.status_code != 404


def test_set_token_rejects_short(client_app):
    r = client_app.post("/api/upstox/token", json={"access_token": "x"})
    assert r.status_code == 400


def test_set_token_accepts(client_app):
    r = client_app.post("/api/upstox/token", json={"access_token": "fake-token-for-test-12345"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["token_length"] == len("fake-token-for-test-12345")


def test_server_info_returns_shape(client_app):
    r = client_app.get("/api/upstox/server-info")
    assert r.status_code == 200
    body = r.json()
    assert "note" in body
    assert "public_ip" in body  # may be None if no internet


def test_profile_endpoint_requires_token(client_app):
    """Profile endpoint explicitly raises 401 when no token."""
    r = client_app.get("/api/upstox/profile")
    assert r.status_code == 401
