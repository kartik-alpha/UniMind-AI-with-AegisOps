import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_liveness_probe():
    resp = client.get("/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"
    assert "UniMind" in data["service"]
    assert "timestamp" in data


def test_readiness_probe():
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["database"] == "ready"
    assert data["checks"]["vector_store"] == "healthy"


def test_prometheus_metrics_exposition():
    # Make a few API calls to generate metrics
    client.get("/health/live")
    client.get("/health/live")

    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")

    body = resp.text
    # Verify standard Prometheus structure
    assert "# HELP unimind_http_requests_total" in body
    assert "# TYPE unimind_http_requests_total counter" in body
    assert "unimind_http_requests_total" in body
    assert "# HELP unimind_http_request_duration_seconds" in body
    assert "unimind_http_request_duration_seconds_bucket" in body
    assert "unimind_http_request_duration_seconds_sum" in body
    assert "unimind_http_request_duration_seconds_count" in body


def test_request_id_and_timing_headers():
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert resp.headers["X-Request-ID"].startswith("req_")
    assert "X-Process-Time" in resp.headers
    assert resp.headers["X-Process-Time"].endswith("s")
