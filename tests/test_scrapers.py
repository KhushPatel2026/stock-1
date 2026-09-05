"""Tests for src.scrapers. HTTP calls are mocked via monkeypatch on _session.get."""
from __future__ import annotations

import json

import pytest
import requests

from src import scrapers


class _FakeResp:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Each test starts with a clean in-memory cache so TTL behavior is testable."""
    scrapers._cache.clear()
    yield
    scrapers._cache.clear()


# ---------------------------------------------------------------------------
# Google News
# ---------------------------------------------------------------------------

def test_google_news_parses(monkeypatch):
    xml = (
        "<?xml version='1.0'?>"
        "<rss><channel>"
        "<item><title>H1</title><link>http://x</link>"
        "<pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate><source>TestSrc</source></item>"
        "</channel></rss>"
    )
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(200, xml))
    out = scrapers.google_news("RELIANCE", limit=5)
    assert len(out) == 1
    assert out[0]["title"] == "H1"
    assert out[0]["source"] == "TestSrc"
    assert out[0]["origin"] == "Google News"
    assert out[0]["published"].startswith("2024-01-01")


def test_google_news_strips_html_entities(monkeypatch):
    xml = (
        "<?xml version='1.0'?><rss><channel>"
        "<item><title>AT&amp;T &lt;b&gt;buys&lt;/b&gt; Co</title>"
        "<link>http://x</link><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>"
        "<source>S</source></item>"
        "</channel></rss>"
    )
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(200, xml))
    out = scrapers.google_news("X", limit=5)
    assert out[0]["title"] == "AT&T buys Co"


def test_google_news_returns_empty_on_404(monkeypatch):
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(404, ""))
    assert scrapers.google_news("RELIANCE") == []


def test_google_news_returns_empty_on_malformed_xml(monkeypatch):
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(200, "<<not xml"))
    assert scrapers.google_news("RELIANCE") == []


# ---------------------------------------------------------------------------
# NSE sector indices
# ---------------------------------------------------------------------------

def test_nse_sector_indices_parses(monkeypatch):
    payload = {
        "data": [
            {
                "key": "SECTORAL INDICES",
                "index": "Nifty Bank",
                "indexSymbol": "NIFTY BANK",
                "last": 50000,
                "change": 100,
                "percentChange": 0.2,
                "open": 49900,
                "high": 50100,
                "low": 49800,
                "previousClose": 49900,
            },
            {"key": "MOVERS", "index": "should be skipped", "last": 1},
        ]
    }
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(200, json.dumps(payload)))
    out = scrapers.nse_sector_indices()
    assert len(out) == 1
    assert out[0]["name"] == "Nifty Bank"
    assert out[0]["last"] == 50000
    assert out[0]["pct_change"] == 0.2


def test_nse_sector_indices_empty_on_404(monkeypatch):
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(403, ""))
    assert scrapers.nse_sector_indices() == []


# ---------------------------------------------------------------------------
# NSE FII/DII
# ---------------------------------------------------------------------------

def test_nse_fii_dii_parses(monkeypatch):
    payload = [
        {"category": "FII/FPI*", "subCategory": "", "date": "01-Jan-2024",
         "buyValue": "1000", "sellValue": "800", "netValue": "200"},
        {"category": "DII**", "subCategory": "", "date": "01-Jan-2024",
         "buyValue": "500", "sellValue": "600", "netValue": "-100"},
    ]
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(200, json.dumps(payload)))
    out = scrapers.nse_fii_dii()
    assert out["date"] == "01-Jan-2024"
    assert out["fii"]["buy"] == "1000"
    assert out["fii"]["net"] == "200"
    assert out["dii"]["sell"] == "600"
    assert out["dii"]["net"] == "-100"


def test_nse_fii_dii_empty_on_404(monkeypatch):
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(404, ""))
    assert scrapers.nse_fii_dii() == {}


def test_nse_fii_dii_empty_rows(monkeypatch):
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(200, "[]"))
    assert scrapers.nse_fii_dii() == {}


# ---------------------------------------------------------------------------
# StockTwits
# ---------------------------------------------------------------------------

def test_stocktwits_parses(monkeypatch):
    payload = {
        "messages": [
            {"user": {"username": "u1"}, "body": "moon", "created_at": "2024-01-01",
             "entities": {"sentiment": {"basic": "Bullish"}}},
            {"user": {"username": "u2"}, "body": "dump", "created_at": "2024-01-01",
             "entities": {"sentiment": {"basic": "Bearish"}}},
            {"user": {"username": "u3"}, "body": "meh", "created_at": "2024-01-01",
             "entities": {"sentiment": {}}},
        ]
    }
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(200, json.dumps(payload)))
    out = scrapers.stocktwits_symbol_sentiment("AAPL", limit=5)
    assert out["sentiment"]["bullish"] == 1
    assert out["sentiment"]["bearish"] == 1
    assert len(out["messages"]) == 3
    assert out["messages"][0]["user"] == "u1"


def test_stocktwits_falls_through_symbol_candidates(monkeypatch):
    """If .NSE returns nothing, .NYSE is tried. Pick the first candidate that returns data."""
    payload = {"messages": [{"user": {"username": "u"}, "body": "x", "created_at": "",
                             "entities": {"sentiment": {}}}]}
    calls = []

    def fake_get(url, *a, **k):
        calls.append(url)
        if ".NSE" in url or ".NYSE" in url:
            return _FakeResp(200, json.dumps({"messages": []}))
        return _FakeResp(200, json.dumps(payload))

    monkeypatch.setattr(scrapers._session, "get", fake_get)
    out = scrapers.stocktwits_symbol_sentiment("RELIANCE", limit=5)
    assert len(out["messages"]) == 1
    # tried .NSE then .NYSE then .NASDAQ
    assert ".NSE" in calls[0]
    assert ".NYSE" in calls[1]
    assert ".NASDAQ" in calls[2]


def test_stocktwits_returns_empty_when_all_fail(monkeypatch):
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(404, ""))
    out = scrapers.stocktwits_symbol_sentiment("XYZ")
    assert out["messages"] == []
    assert out["sentiment"] == {"bullish": 0, "bearish": 0}
    assert out["total"] == 0


# ---------------------------------------------------------------------------
# MoneyControl
# ---------------------------------------------------------------------------

def test_moneycontrol_unknown_ticker_empty():
    assert scrapers.moneycontrol_news("UNKNOWN_TICKER_XYZ") == []


def test_moneycontrol_parses(monkeypatch):
    html_body = (
        '<html><body>'
        '<a href="https://www.moneycontrol.com/news/markets/reliance-q1.html">'
        '<h2>Reliance Q1 beats estimates</h2></a>'
        '<a href="https://www.moneycontrol.com/news/business/reliance-jio.html">'
        'Reliance Jio adds users</a>'
        '</body></html>'
    )
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(200, html_body))
    out = scrapers.moneycontrol_news("RELIANCE", limit=5)
    assert len(out) == 2
    assert out[0]["source"] == "MoneyControl"
    assert "Reliance Q1" in out[0]["title"]


# ---------------------------------------------------------------------------
# Investing.com
# ---------------------------------------------------------------------------

def test_investing_quote_parses(monkeypatch):
    html_body = (
        '<html><body>'
        '<h1>USD/INR</h1>'
        '<span data-test="instrument-price-last">83.25</span>'
        '<span data-test="instrument-price-change">0.12</span>'
        '<span data-test="instrument-price-change-percent">0.14%</span>'
        '</body></html>'
    )
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(200, html_body))
    out = scrapers.investing_quote("currencies/usd-inr")
    assert out is not None
    assert out["price"] == 83.25
    assert out["change"] == 0.12
    assert out["pct_change"] == 0.14
    assert out["name"] == "USD/INR"


def test_investing_quote_returns_none_on_missing_price(monkeypatch):
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(200, "<html></html>"))
    assert scrapers.investing_quote("currencies/usd-inr") is None


def test_investing_quote_returns_none_on_404(monkeypatch):
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(404, ""))
    assert scrapers.investing_quote("currencies/usd-inr") is None


# ---------------------------------------------------------------------------
# Resilience: never raise
# ---------------------------------------------------------------------------

def test_all_sources_fail_returns_empty(monkeypatch):
    def boom(*a, **k):
        raise requests.RequestException("network down")

    monkeypatch.setattr(scrapers._session, "get", boom)
    assert scrapers.google_news("X") == []
    assert scrapers.nse_sector_indices() == []
    assert scrapers.nse_fii_dii() == {}
    assert scrapers.moneycontrol_news("RELIANCE") == []
    assert scrapers.investing_quote("currencies/usd-inr") is None
    out = scrapers.stocktwits_symbol_sentiment("X")
    assert out["messages"] == []


# ---------------------------------------------------------------------------
# Cache: 2nd call within TTL doesn't hit network
# ---------------------------------------------------------------------------

def test_google_news_cache_hits(monkeypatch):
    xml = (
        "<?xml version='1.0'?><rss><channel>"
        "<item><title>H1</title><link>http://x</link>"
        "<pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate><source>S</source></item>"
        "</channel></rss>"
    )
    call_count = {"n": 0}

    def fake_get(*a, **k):
        call_count["n"] += 1
        return _FakeResp(200, xml)

    monkeypatch.setattr(scrapers._session, "get", fake_get)
    a = scrapers.google_news("RELIANCE", limit=5)
    b = scrapers.google_news("RELIANCE", limit=5)
    assert a == b
    assert call_count["n"] == 1


def test_nse_cache_hits(monkeypatch):
    payload = {"data": [{"key": "SECTORAL INDICES", "index": "Nifty Bank",
                          "indexSymbol": "NIFTY BANK", "last": 50000,
                          "change": 100, "percentChange": 0.2}]}
    call_count = {"n": 0}

    def fake_get(*a, **k):
        call_count["n"] += 1
        return _FakeResp(200, json.dumps(payload))

    monkeypatch.setattr(scrapers._session, "get", fake_get)
    scrapers.nse_sector_indices()
    scrapers.nse_sector_indices()
    assert call_count["n"] == 1


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def test_all_news_for_ticker_shape(monkeypatch):
    """Aggregator should return a dict with all 4 sources and a timestamp."""
    xml = (
        "<?xml version='1.0'?><rss><channel>"
        "<item><title>T</title><link>http://x</link>"
        "<pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate><source>S</source></item>"
        "</channel></rss>"
    )
    payload = {"data": [{"key": "SECTORAL INDICES", "index": "X",
                          "indexSymbol": "X", "last": 1, "change": 0,
                          "percentChange": 0}]}
    monkeypatch.setattr(scrapers._session, "get", lambda *a, **k: _FakeResp(200, xml))
    # yfinance path — leave alone; aggregator should still work even if it returns []
    out = scrapers.all_news_for_ticker("RELIANCE.NS", limit_per_source=3)
    assert out["ticker"] == "RELIANCE.NS"
    assert "google_news" in out
    assert "moneycontrol" in out
    assert "stocktwits" in out
    assert "yfinance" in out
    assert out["fetched_at"].endswith("Z")