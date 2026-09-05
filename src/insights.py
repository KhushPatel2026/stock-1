"""Pre-built insight generators — heuristics, no AI needed."""
from __future__ import annotations


def portfolio_concentration_risk(holdings: list[dict]) -> dict:
    """Compute Herfindahl index, top holdings weight."""
    if not holdings:
        return {"score": 0, "message": "No holdings."}
    total = sum(h.get("current_value") or 0 for h in holdings) or 1
    weights = [(h.get("current_value") or 0) / total for h in holdings]
    hhi = sum(w * w for w in weights)
    sorted_h = sorted(holdings, key=lambda h: -(h.get("current_value") or 0))
    top3_pct = sum((h.get("current_value") or 0) for h in sorted_h[:3]) / total * 100
    return {
        "score": round(hhi, 3),
        "concentration": "high" if hhi > 0.25 else "medium" if hhi > 0.15 else "low",
        "top3_pct": round(top3_pct, 1),
        "top_holdings": [
            {
                "ticker": h.get("ticker", ""),
                "weight_pct": round((h.get("current_value") or 0) / total * 100, 1),
            }
            for h in sorted_h[:5]
        ],
        "message": (
            f"HHI {hhi:.2f} ({'concentrated' if hhi > 0.25 else 'diversified'}). "
            f"Top 3 = {top3_pct:.0f}% of portfolio."
        ),
    }


def portfolio_pnl_attribution(holdings: list[dict]) -> dict:
    """Which positions contribute most to P&L?"""
    if not holdings:
        return {"winners": [], "losers": []}
    sorted_by_pnl = sorted(holdings, key=lambda h: -(h.get("pnl") or 0))
    return {
        "winners": sorted_by_pnl[:3],
        "losers": sorted_by_pnl[-3:][::-1],
        "total_pnl": sum(h.get("pnl") or 0 for h in holdings),
    }


def suggestions_for_holdings(holdings: list[dict]) -> list[str]:
    """Rule-based suggestions for the portfolio."""
    sugg: list[str] = []
    if not holdings:
        return ["Add some holdings to get insights."]

    total = sum(h.get("current_value") or 0 for h in holdings) or 1
    weights = [(h.get("current_value") or 0) / total for h in holdings]
    hhi = sum(w * w for w in weights)

    if hhi > 0.25:
        sugg.append("⚠️ Concentration risk: your top holdings are too large. Consider trimming the biggest position.")

    big_losers = [h for h in holdings if (h.get("pnl_pct") or 0) < -15]
    if big_losers:
        sugg.append(f"📉 {len(big_losers)} position(s) down >15%. Review if fundamentals changed before averaging down.")

    big_winners = [h for h in holdings if (h.get("pnl_pct") or 0) > 30]
    if big_winners:
        sugg.append(f"📈 {len(big_winners)} position(s) up >30%. Consider partial profit-taking.")

    if not sugg:
        sugg.append("✅ Portfolio looks balanced. Run 'What should I buy?' to find new ideas.")

    return sugg