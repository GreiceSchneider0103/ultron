from __future__ import annotations

from fastapi.testclient import TestClient

from api.src.auth import require_auth_context
from api.src.main import app


class _DummyCtx:
    user_id = "00000000-0000-0000-0000-000000000111"
    workspace_id = "00000000-0000-0000-0000-000000000222"
    token = None
    claims = {}


def _override_auth():
    return _DummyCtx()


def test_health_smoke():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "monitor_scheduler_active" in body


def test_documents_analyze_smoke():
    app.dependency_overrides[require_auth_context] = _override_auth
    client = TestClient(app)
    response = client.post(
        "/api/documents/analyze",
        json={"text": "Dimensoes: 120 x 80 x 60 cm\nMaterial: Madeira\nPeso: 12 kg"},
    )
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert "structured_spec" in body
    assert body["structured_spec"]["attributes"]["largura_cm"] == 120.0


def test_expensive_call_trail_images_and_reports(monkeypatch):
    app.dependency_overrides[require_auth_context] = _override_auth
    captured: list[dict] = []

    from api.src.db import repository

    monkeypatch.setattr(repository, "create_job", lambda **kwargs: "job-1")

    def _capture_usage(**kwargs):
        captured.append(kwargs)
        return "usage-1"

    monkeypatch.setattr(repository, "create_usage_log", _capture_usage)

    client = TestClient(app)
    r1 = client.post(
        "/api/v2/images/analyze",
        json={"image_urls": ["https://cdn.exemplo.com/sofa_front_1200x1200.jpg"], "category": "sofa"},
        headers={"x-trace-id": "trace-images-1"},
    )
    r2 = client.post(
        "/api/reports/generate",
        json={"cost": 100, "target_price": 200, "findings": {}},
        headers={"x-trace-id": "trace-reports-1"},
    )
    app.dependency_overrides.clear()

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert len(captured) >= 2
    assert any(item["feature"] == "images_analyze" for item in captured)
    assert any(item["feature"] == "reports_generate" for item in captured)
    assert all(item["workspace_id"] == _DummyCtx.workspace_id for item in captured)
    assert all(item["user_id"] == _DummyCtx.user_id for item in captured)
