"""Unit tests for institutional report endpoints."""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_reports_summary():
    res = client.get("/api/reports/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "walk_forward_count" in data
    assert "positive_alpha_ratio" in data
    assert "top_strategy" in data
    assert "available_reports" in data
    assert len(data["available_reports"]) >= 2


def test_reports_walk_forward():
    res = client.get("/api/reports/walk-forward")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert "strategy_id" in first
        assert "mean_oos_sharpe" in first
        assert "total_oos_return" in first
        assert "max_dd" in first
        # Sorted descending by mean_oos_sharpe
        sharpes = [d["mean_oos_sharpe"] for d in data]
        assert sharpes == sorted(sharpes, reverse=True)


def test_reports_regimes():
    res = client.get("/api/reports/regimes")
    assert res.status_code == 200
    data = res.json()
    assert "rows" in data
    assert "matrix" in data
    if data["rows"]:
        first = data["rows"][0]
        assert "strategy_id" in first
        assert "regime" in first
        assert "sharpe" in first
