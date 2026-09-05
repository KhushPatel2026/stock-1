"""Tests for src.macro: regime logic is pure, fetch_* uses monkeypatched yfinance."""
from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src import macro as M


class _FakeTicker:
    def __init__(self, symbol, df=None, news=None, raise_exc=False):
        self.symbol = symbol
        self._df = df
        self._news = news
        self._raise = raise_exc

    def history(self, period="3mo", auto_adjust=True):
        if self._raise:
            raise RuntimeError("yfinance exploded")
        return self._df

    @property
    def news(self):
        if self._raise:
            raise RuntimeError("yfinance exploded")
        return self._news


def _patch_yfinance(monkeypatch, ticker_cls):
    monkeypatch.setattr(M.yf, "Ticker", ticker_cls)


def _rising_df(n: int = 60, start: float = 100.0, drift: float = 0.005) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    close = start * (1 + drift) ** np.arange(n)
    return pd.DataFrame({"Close": close}, index=idx)


def _falling_df(n: int = 60, start: float = 100.0, drift: float = -0.005) -> pd.DataFrame:
    return _rising_df(n=n, start=start, drift=drift)


def test_sectors_dict_complete():
    expected = {"Nifty Bank", "Nifty IT", "Nifty Auto", "Nifty Pharma", "Nifty FMCG",
                "Nifty Metal", "Nifty Realty", "Nifty Energy", "Nifty Financial Services",
                "Nifty PSU Bank"}
    assert set(M.SECTORS.keys()) == expected


def test_fetch_one_yfinance_failure(monkeypatch):
    _patch_yfinance(monkeypatch, lambda sym: _FakeTicker(sym, raise_exc=True))
    assert M.fetch_one("^BOGUS") is None


def test_fetch_one_empty_df(monkeypatch):
    _patch_yfinance(monkeypatch, lambda sym: _FakeTicker(sym, df=pd.DataFrame()))
    assert M.fetch_one("^EMPTY") is None


def test_fetch_one_short_df(monkeypatch):
    _patch_yfinance(monkeypatch, lambda sym: _FakeTicker(sym, df=_rising_df(n=3)))
    assert M.fetch_one("^SHORT") is None


def test_fetch_one_rising_series(monkeypatch):
    _patch_yfinance(monkeypatch, lambda sym: _FakeTicker(sym, df=_rising_df()))
    r = M.fetch_one("^NSEI")
    assert r is not None
    assert r["symbol"] == "^NSEI"
    assert r["last"] > 0
    assert r["chg_20d_pct"] > 0
    assert r["trend"] == "up"


def _base_macro(nifty_20d: float = 0.0, vix: float = 15.0, sp_20d: float = 0.0,
                crude_20d: float = 0.0, gold_20d: float = 0.0) -> dict:
    return {
        "as_of": "2024-06-01 12:00 UTC",
        "nifty50": {"name": "Nifty 50", "last": 22000.0, "chg_20d_pct": nifty_20d},
        "sectors": [
            {"name": "Nifty IT", "chg_20d_pct": 5.0},
            {"name": "Nifty Bank", "chg_20d_pct": 3.0},
            {"name": "Nifty FMCG", "chg_20d_pct": 1.0},
            {"name": "Nifty Auto", "chg_20d_pct": -1.0},
            {"name": "Nifty Metal", "chg_20d_pct": -3.0},
            {"name": "Nifty Realty", "chg_20d_pct": -5.0},
        ],
        "global": [
            {"name": "S&P 500", "chg_20d_pct": sp_20d},
            {"name": "NASDAQ", "chg_20d_pct": 1.0},
        ],
        "commodities": [
            {"name": "Crude Oil (WTI)", "chg_20d_pct": crude_20d},
            {"name": "Gold", "chg_20d_pct": gold_20d},
        ],
        "fx": [],
        "volatility": [
            {"name": "India VIX", "last": vix, "chg_20d_pct": 0.0},
        ],
    }


def test_regime_summary_bullish():
    m = _base_macro(nifty_20d=5.0, vix=14.0, sp_20d=4.0, crude_20d=3.0, gold_20d=-2.0)
    r = M.regime_summary(m)
    assert r["india_regime"] == "bullish"
    assert r["global_regime"] == "bullish"
    assert r["commodities_bias"] == "risk-on"
    assert r["risk_on_off"] == "risk-on"
    assert "India bullish" in r["summary"]
    assert "IT" in r["summary"]


def test_regime_summary_bearish():
    m = _base_macro(nifty_20d=-6.0, vix=15.0, sp_20d=-5.0, crude_20d=-3.0, gold_20d=2.0)
    r = M.regime_summary(m)
    assert r["india_regime"] == "bearish"
    assert r["global_regime"] == "bearish"
    assert r["commodities_bias"] == "risk-off"
    assert "India bearish" in r["summary"]


def test_regime_summary_risk_off():
    m = _base_macro(nifty_20d=0.0, vix=24.0, sp_20d=-2.0, crude_20d=-3.0, gold_20d=3.0)
    r = M.regime_summary(m)
    assert r["india_regime"] == "bearish"
    assert r["risk_on_off"] == "risk-off"


def test_regime_summary_neutral_fallbacks():
    m = {"sectors": [], "global": [], "commodities": [], "volatility": []}
    r = M.regime_summary(m)
    assert r["india_regime"] == "neutral"
    assert r["global_regime"] == "neutral"
    assert r["risk_on_off"] == "neutral"
    assert r["commodities_bias"] == "mixed"
    assert r["strongest_sectors"] == []
    assert r["weakest_sectors"] == []


def test_regime_summary_sector_rotation():
    m = _base_macro()
    r = M.regime_summary(m)
    assert r["strongest_sectors"][0] == "Nifty IT"
    assert r["weakest_sectors"][-1] == "Nifty Realty"


def test_news_for_ticker_empty(monkeypatch):
    _patch_yfinance(monkeypatch, lambda sym: _FakeTicker(sym, news=None))
    assert M.news_for_ticker("BOGUS") == []


def test_news_for_ticker_exception(monkeypatch):
    _patch_yfinance(monkeypatch, lambda sym: _FakeTicker(sym, raise_exc=True))
    assert M.news_for_ticker("BOGUS") == []


def test_news_for_ticker_returns_normalized(monkeypatch):
    raw = [
        {"title": "H1", "publisher": "P1", "link": "https://x", "providerPublishTime": 1700000000},
        {"title": "H2", "publisher": "P2", "link": "https://y", "providerPublishTime": 1700000100},
    ]
    _patch_yfinance(monkeypatch, lambda sym: _FakeTicker(sym, news=raw))
    out = M.news_for_ticker("^NSEI", limit=5)
    assert len(out) == 2
    assert out[0]["title"] == "H1"
    assert out[0]["publisher"] == "P1"
    assert out[0]["link"] == "https://x"
    assert out[1]["title"] == "H2"


def test_fetch_all_aggregates(monkeypatch):
    def factory(sym):
        if sym == "^NSEI":
            return _FakeTicker(sym, df=_rising_df(n=30, drift=0.01))
        if sym.startswith("^BOGUS"):
            return _FakeTicker(sym, raise_exc=True)
        return _FakeTicker(sym, df=_rising_df(n=30, drift=0.005))

    _patch_yfinance(monkeypatch, factory)
    monkeypatch.setattr(M, "ALL_SYMBOLS", ["^NSEI", "^BOGUS1"] + list(M.SECTORS.values()))
    out = M.fetch_all()
    assert "as_of" in out
    assert out["nifty50"]["name"] == "Nifty 50"
    assert out["nifty50"]["trend"] == "up"
    assert len(out["sectors"]) == len(M.SECTORS)
    for sec in out["sectors"]:
        assert "name" in sec
        assert sec["chg_20d_pct"] >= 0


@pytest.mark.skipif(not M.has_internet(), reason="needs live yfinance")
def test_fetch_one_live():
    r = M.fetch_one("^NSEI")
    assert r is not None
    assert r["last"] > 0