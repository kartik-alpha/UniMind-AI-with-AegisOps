import io
import json
import hashlib
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from app.core.security import create_access_token
from app.adapters.factory import AdapterFactory

client = TestClient(app)


@pytest.fixture
def admin_headers():
    token = create_access_token(subject="1")
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": "1"}


@pytest.fixture
def tenant2_headers():
    token = create_access_token(subject="10")
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": "10"}


def test_governance_status_endpoint(admin_headers):
    resp = client.get("/api/v1/governance/status", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == 1
    assert "storage" in data
    assert "tokens" in data
    assert "rate_limit" in data
    assert data["storage"]["quota_bytes"] > 0


def test_governance_token_accounting_endpoint(admin_headers):
    resp = client.get("/api/v1/governance/tokens", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == 1
    assert "total_tokens" in data
    assert "budget" in data


def test_governance_controls_update(admin_headers):
    payload = {
        "storage_quota_bytes": 104857600,  # 100 MB
        "rate_limit_per_min": 150,
        "monthly_token_budget": 750000,
    }
    resp = client.post("/api/v1/governance/controls", json=payload, headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["storage"]["quota_bytes"] == 104857600
    assert data["rate_limit"]["requests_per_minute"] == 150


def test_tamper_evident_audit_export_hash_chain(admin_headers):
    # Test JSONL format
    resp = client.get("/api/v1/governance/audit/export?format=jsonl", headers=admin_headers)
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    lines = [l for l in resp.text.split("\n") if l.strip()]

    if lines:
        prev_hash = "0" * 64
        for line in lines:
            rec = json.loads(line)
            assert rec["tenant_id"] == 1
            assert rec["previous_hash"] == prev_hash

            # Verify chain hash computation
            ts_str = rec["timestamp"]
            details_str = json.dumps(rec["details"], sort_keys=True)
            expected_payload = f"{prev_hash}|{rec['id']}|{rec['tenant_id']}|{rec['action']}|{rec['performed_by']}|{rec['target_resource']}|{rec['status']}|{ts_str}|{details_str}"
            expected_hash = hashlib.sha256(expected_payload.encode("utf-8")).hexdigest()
            assert rec["chain_hash"] == expected_hash
            prev_hash = rec["chain_hash"]

    # Test CSV format
    csv_resp = client.get("/api/v1/governance/audit/export?format=csv", headers=admin_headers)
    assert csv_resp.status_code == 200
    assert "chain_hash" in csv_resp.text


def test_rate_limiting_enforcement():
    # Directly test rate limiter using low threshold
    cache = AdapterFactory.get_cache()
    # Fill quota of 5 requests for tenant 99
    for _ in range(5):
        res = cache.check_rate_limit(tenant_id=99, limit_key="test_rate", max_requests=5, window_seconds=60)
        assert res["allowed"] is True

    # 6th request must be rejected
    res_block = cache.check_rate_limit(tenant_id=99, limit_key="test_rate", max_requests=5, window_seconds=60)
    assert res_block["allowed"] is False
    assert res_block["remaining"] == 0
    assert res_block["reset_seconds"] > 0
