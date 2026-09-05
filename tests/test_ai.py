"""Tests for src.ai — fallback paths always run; live Gemini tests gated on key."""
from __future__ import annotations
import os
import pytest

from src.ai import (
    is_available,
    explain_strategy,
    explain_portfolio,
    personalized_insight,
    _fallback_explain,
    _fallback_portfolio,
    _fallback_insight,
)

LIVE = bool(os.getenv("GEMINI_API_KEY"))


# ---------------------------------------------------------------------------
# Fallback explain — Sharpe bucketing
# ---------------------------------------------------------------------------

def test_fallback_explain_positive_sharpe(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")  # force fallback
    text = _fallback_explain("x", "MyStrat", "Trend", {"sharpe": 1.5})
    assert "1.50" in text
    assert "solid" in text.lower() or "trending" in text.lower()


def test_fallback_explain_negative_sharpe(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    text = _fallback_explain("x", "MyStrat", "Mean Rev", {"sharpe": -0.4})
    assert "-0.40" in text
    assert "negative" in text.lower()


def test_fallback_explain_zero_sharpe(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    text = _fallback_explain("x", "MyStrat", "Mom", {"sharpe": 0.0})
    assert "modestly" in text.lower() or "0.00" in text


# ---------------------------------------------------------------------------
# Fallback portfolio
# ---------------------------------------------------------------------------

def test_fallback_portfolio_with_profit(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    holdings = [
        {"ticker": "A.NS", "current_value": 60000, "pnl_pct": 20},
        {"ticker": "B.NS", "current_value": 40000, "pnl_pct": 5},
    ]
    summary = {"total_pnl_pct": 8.0}
    text = _fallback_portfolio(holdings, summary)
    assert "2 holdings" in text
    assert "+8.0%" in text
    assert "profit" in text.lower()


def test_fallback_portfolio_empty():
    assert _fallback_portfolio([], {}) == "No holdings to analyze."


def test_fallback_portfolio_big_loss(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    holdings = [{"ticker": "X.NS", "current_value": 100, "pnl_pct": -20}]
    text = _fallback_portfolio(holdings, {"total_pnl_pct": -15.0})
    assert "Down significantly" in text


# ---------------------------------------------------------------------------
# Fallback personalized insight
# ---------------------------------------------------------------------------

def test_fallback_insight_no_usage(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    text = _fallback_insight({})
    assert "Smart picks" in text or "consensus" in text.lower()
    assert text.startswith("•")


def test_fallback_insight_with_usage(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    stats = {"most_used": ["bollinger", "rsi2", "macd"]}
    text = _fallback_insight(stats)
    assert "bollinger" in text
    assert "rsi2" in text


# ---------------------------------------------------------------------------
# Wrapper-level fallback (no key → falls through)
# ---------------------------------------------------------------------------

def test_explain_strategy_no_key_falls_back(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    text = explain_strategy("bollinger", "Bollinger", "Mean Reversion",
                            {"sharpe": 0.5, "total_return": 0.1})
    assert isinstance(text, str)
    assert len(text) > 20


def test_explain_portfolio_empty_returns_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    text = explain_portfolio([], {"total_pnl_pct": 0})
    assert text == "No holdings to analyze."


def test_personalized_insight_no_key_falls_back(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    text = personalized_insight({})
    assert text.startswith("•")


# ---------------------------------------------------------------------------
# is_available + ai_status
# ---------------------------------------------------------------------------

def test_ai_status(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    assert is_available() is False
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    assert is_available() is True
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert is_available() is False


# ---------------------------------------------------------------------------
# Live Gemini tests — skip unless key present in env
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not LIVE, reason="GEMINI_API_KEY not set")
def test_live_explain_strategy():
    text = explain_strategy(
        "bollinger",
        "Bollinger Bands",
        "Mean Reversion",
        {"sharpe": 1.2, "total_return": 0.18, "cagr": 0.10, "max_drawdown": -0.12, "n_bars": 500},
    )
    assert isinstance(text, str)
    assert len(text) > 30


@pytest.mark.skipif(not LIVE, reason="GEMINI_API_KEY not set")
def test_live_explain_portfolio():
    holdings = [
        {"ticker": "RELIANCE.NS", "quantity": 50, "avg_price": 2400,
         "current_price": 2700, "pnl_pct": 12.5},
        {"ticker": "TCS.NS", "quantity": 20, "avg_price": 3500,
         "current_price": 3200, "pnl_pct": -8.6},
    ]
    summary = {"total_invested": 190000, "total_current": 199000,
               "total_pnl": 9000, "total_pnl_pct": 4.7}
    text = explain_portfolio(holdings, summary)
    assert isinstance(text, str)
    assert len(text) > 50


@pytest.mark.skipif(not LIVE, reason="GEMINI_API_KEY not set")
def test_live_personalized_insight():
    stats = {
        "most_used": ["bollinger", "rsi2"],
        "recent_runs": [
            {"strategy_id": "bollinger", "sharpe": 0.9,
             "tickers": ["RELIANCE.NS"], "period": "1y"},
        ],
    }
    text = personalized_insight(stats)
    assert isinstance(text, str)
    assert len(text) > 20


@pytest.mark.skipif(not LIVE, reason="GEMINI_API_KEY not set")
def test_live_explain_strategy_with_user_question():
    text = explain_strategy(
        "macd",
        "MACD Crossover",
        "Trend",
        {"sharpe": 0.8, "total_return": 0.05, "cagr": 0.04,
         "max_drawdown": -0.08, "n_bars": 300},
        user_question="Is this safe for swing trading?",
    )
    assert isinstance(text, str)
    assert len(text) > 30