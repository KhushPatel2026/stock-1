from src.market_context import tone_of_title, vix_label, get_context, macro_overlay


def _ctx(trend="uptrend", vix=12.0, breadth=65.0, sec_vs=3.0, sp=0.8, tones=None, month=4.0):
    return {
        "market": {"nifty_trend": trend, "nifty_month_pct": month, "vix": vix,
                   "vix_state": vix_label(vix), "breadth_pct": breadth},
        "global": {"S&P 500": {"day_pct": sp}},
        "sector": {"name": "Energy", "month_vs_nifty": sec_vs},
        "news": {"items": [{"tone": t} for t in (tones or [])]},
    }


def test_tone_keywords():
    assert tone_of_title("Reliance shares rally 3% on strong profit growth") == "positive"
    assert tone_of_title("Stock plunges on fraud probe fears, downgrade") == "negative"
    assert tone_of_title("Board meeting scheduled for next week") == "neutral"


def test_vix_buckets():
    assert vix_label(11.0) == "calm"
    assert vix_label(15.0) == "normal"
    assert vix_label(20.0) == "elevated"
    assert vix_label(30.0) == "fear"
    assert vix_label(None) == "unknown"


def test_context_shape_never_raises():
    ctx = get_context("RELIANCE.NS")
    for key in ("ticker", "market", "global", "sector", "commodity", "news", "cautions", "summary"):
        assert key in ctx
    assert isinstance(ctx["cautions"], list)
    assert isinstance(ctx["news"].get("items", []), list)
    for a in ctx["news"]["items"]:
        assert a["tone"] in ("positive", "negative", "neutral")
        assert a["title"]


def test_overlay_bull_market_positive():
    ov = macro_overlay("T.NS", _ctx(), atr_pct=1.5)
    assert ov["score"] > 0
    assert -30 <= ov["score"] <= 30
    assert any("Nifty above" in r for r in ov["reasons"])
    assert ov["sizing_pct"] == 1.0


def test_overlay_bear_market_negative_and_small_size():
    ov = macro_overlay("T.NS", _ctx(trend="downtrend", vix=21.0, breadth=30.0,
                                    sec_vs=-5.0, sp=-1.5,
                                    tones=["negative"] * 3 + ["neutral"] * 2, month=-6.0),
                       atr_pct=2.0)
    assert ov["score"] < 0
    assert ov["sizing_pct"] == 0.5
    assert "half size" in ov["sizing_note"]


def test_overlay_fear_quarter_size():
    ov = macro_overlay("T.NS", _ctx(vix=32.0), atr_pct=1.0)
    assert ov["sizing_pct"] == 0.25
    assert any("VIX" in r and "-12" in r for r in ov["reasons"])


def test_overlay_volatile_stock_halved():
    ov = macro_overlay("T.NS", _ctx(), atr_pct=4.5)
    assert ov["sizing_pct"] == 0.5


def test_overlay_empty_context_scores_zero():
    ov = macro_overlay("T.NS", {})
    assert ov["score"] == 0
    assert ov["sizing_pct"] == 1.0
