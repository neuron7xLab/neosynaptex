"""API safety smoke tests (fast, deterministic)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from mycelium_fractal_net.api import app


def test_health_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_validate_rejects_invalid_payload() -> None:
    client = TestClient(app)
    response = client.post("/validate", json={"seed": "not-an-int"})
    assert response.status_code == 422
    body = response.text
    assert "Traceback" not in body
    # ensure JSON is returned
    json.loads(body)
