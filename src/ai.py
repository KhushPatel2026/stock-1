"""Gemini AI integration — strategy explanations + portfolio insights."""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _REPO_ROOT / ".env"


def _load_dotenv_once() -> None:
    """Tiny .env loader — no new dependency. Env vars already set win."""
    if not _ENV_PATH.exists():
        return
    try:
        for line in _ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass


_load_dotenv_once()

_MODEL = "gemini-flash-lite-latest"
_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        from google import genai
        _CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    return _CLIENT


def is_available() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", ""))


def _generate(prompt: str) -> str:
    r = _client().models.generate_content(model=_MODEL, contents=prompt)
    return (r.text or "").strip()


def explain_strategy(strategy_id: str, name: str, family: str, metrics: dict, user_question: str = "") -> str:
    """Ask Gemini to explain a strategy's result in plain English for a trader."""
    if not is_available():
        return _fallback_explain(strategy_id, name, family, metrics)

    sharpe = metrics.get("sharpe", 0)
    total = metrics.get("total_return", 0) * 100
    cagr = metrics.get("cagr", 0) * 100
    max_dd = metrics.get("max_drawdown", 0) * 100
    n_bars = metrics.get("n_bars", 0)

    qline = f"\nThe user asked: {user_question}" if user_question else ""
    prompt = (
        f"You are a quant analyst explaining a strategy's backtest result to a retail trader.\n\n"
        f"Strategy: {name} ({strategy_id})\n"
        f"Family: {family}\n"
        f"Results: Sharpe {sharpe:.2f}, total return {total:.1f}%, CAGR {cagr:.1f}%, "
        f"max drawdown {max_dd:.1f}%, bars {n_bars}\n\n"
        f"Explain in 3-4 sentences:\n"
        f"1. What this strategy's result means (is the Sharpe good? Is the drawdown acceptable?)\n"
        f"2. What market conditions would help or hurt this strategy\n"
        f"3. One concrete suggestion for the trader"
        f"{qline}\n\n"
        f"Be direct, no fluff. No emojis. Plain text, no markdown headers."
    )

    try:
        return _generate(prompt)
    except Exception as e:
        log.warning("gemini explain_strategy failed: %s", e)
        return _fallback_explain(strategy_id, name, family, metrics)


def explain_portfolio(holdings: list[dict], summary: dict) -> str:
    """Explain user's actual holdings with actionable insights."""
    if not is_available() or not holdings:
        return _fallback_portfolio(holdings, summary)

    lines = []
    for h in holdings[:15]:
        cur = h.get("current_price") or 0
        lines.append(
            f"- {h['ticker']}: {h['quantity']} shares, "
            f"avg ₹{h['avg_price']:.0f}, current ₹{cur:.0f}, "
            f"P&L {h.get('pnl_pct', 0):.1f}%"
        )
    holdings_str = "\n".join(lines)
    prompt = (
        "You are a portfolio analyst. Look at this Indian retail portfolio and "
        "give a quick honest assessment.\n\n"
        f"Total invested: ₹{summary.get('total_invested', 0):,.0f}\n"
        f"Total current: ₹{summary.get('total_current', 0):,.0f}\n"
        f"Total P&L: ₹{summary.get('total_pnl', 0):,.0f} "
        f"({summary.get('total_pnl_pct', 0):.1f}%)\n\n"
        f"Holdings:\n{holdings_str}\n\n"
        "Give a 4-6 sentence assessment covering:\n"
        "1. Concentration risk (any single position >20%?)\n"
        "2. Sector diversification\n"
        "3. Top performers and losers\n"
        "4. One concrete suggestion to improve risk-adjusted return\n\n"
        "Be direct and specific. No emojis. No disclaimers."
    )

    try:
        return _generate(prompt)
    except Exception as e:
        log.warning("gemini explain_portfolio failed: %s", e)
        return _fallback_portfolio(holdings, summary)


def personalized_insight(user_stats: dict) -> str:
    """Based on what strategies user has run, suggest next actions."""
    if not is_available():
        return _fallback_insight(user_stats)

    prompt = (
        "You're a quant coach. Based on this user's stock-1 usage, "
        "suggest 3 specific next actions they should take.\n\n"
        f"Their stats:\n{json.dumps(user_stats, indent=2)}\n\n"
        "Be very specific — name strategies, timeframes, tickers they should try. "
        "No generic advice. No emojis. 3 short bullets."
    )

    try:
        return _generate(prompt)
    except Exception as e:
        log.warning("gemini personalized_insight failed: %s", e)
        return _fallback_insight(user_stats)


def _fallback_explain(strategy_id: str, name: str, family: str, metrics: dict) -> str:
    sharpe = metrics.get("sharpe", 0)
    if sharpe > 1:
        return (
            f"{name} shows a Sharpe of {sharpe:.2f} — solid risk-adjusted returns. "
            f"{family} strategies typically benefit from trending markets and suffer in chop."
        )
    if sharpe > 0:
        return (
            f"{name} has a modestly positive Sharpe of {sharpe:.2f}. "
            f"{family} works in specific regimes — try walk-forward to confirm out-of-sample."
        )
    return (
        f"{name} has a negative Sharpe of {sharpe:.2f} on this dataset. "
        "Either the period is unfavorable or the parameters need tuning. "
        "Try a different period or pick a different strategy."
    )


def _fallback_portfolio(holdings: list[dict], summary: dict) -> str:
    if not holdings:
        return "No holdings to analyze."
    n = len(holdings)
    pnl = summary.get("total_pnl_pct", 0)
    msg = f"Portfolio of {n} holdings with {pnl:+.1f}% P&L. "
    if pnl > 5:
        msg += "Currently in profit. Consider taking partial profits on winners."
    elif pnl < -10:
        msg += "Down significantly. Review whether fundamentals changed or it's just market drawdown."
    else:
        msg += "Roughly flat. Look at concentration — top positions drive most of the risk."
    return msg


def _fallback_insight(stats: dict) -> str:
    used = stats.get("most_used") or []
    if not used:
        return (
            "• Run a Smart picks preset to see what strategies actually work for your tickers\n"
            "• Try 'What should I buy?' for today's consensus\n"
            "• Connect Upstox for real portfolio insights"
        )
    names = ", ".join(used[:3])
    return (
        f"• You've been using {names} — try a strategy from a different family for diversification\n"
        "• Run 'All 56 ranked' to see which strategies actually work\n"
        "• Try short durations (1d, 1w) to see recent signals"
    )