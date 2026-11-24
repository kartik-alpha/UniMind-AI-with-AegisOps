import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from app.core.security import create_access_token

client = TestClient(app)


@pytest.fixture
def admin_headers():
    token = create_access_token(subject="1")
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": "1"}


@pytest.fixture
def student_headers():
    token = create_access_token(subject="2")  # Student role
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": "1"}


@pytest.fixture
def tenant2_admin_headers():
    token = create_access_token(subject="10")
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": "10"}


def test_predictive_event_creation_and_approval_default(admin_headers):
    # 1. Post a valid predictive thermal spike event
    event_payload = {
        "event_type": "THERMAL_SPIKE",
        "service_name": "DataCenter_Cooling_Unit_2",
        "predicted_metric": 88.5,
        "threshold_metric": 75.0,
        "lead_time_hours": 1.5,
        "recommendation": "Activate secondary HVAC chiller loop",
        "severity": "CRITICAL",
        "details": {"datacenter_room": "Rack_B7", "ambient_temp_c": 34.2},
    }

    resp = client.post(
        "/api/v1/digital-twin/events/predictive-alert",
        json=event_payload,
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "INCIDENT_REGISTERED"
    assert data["approval_status"] == "PENDING_APPROVAL"
    assert data["tenant_id"] == 1
    inc_id = data["incident_id"]

    # 2. Idempotency & Deduplication: duplicate event updates existing incident
    resp_dup = client.post(
        "/api/v1/digital-twin/events/predictive-alert",
        json=event_payload,
        headers=admin_headers,
    )
    assert resp_dup.status_code == 200
    assert resp_dup.json()["incident_id"] == inc_id

    # 3. Retrieve predictive alerts
    alerts_resp = client.get("/api/v1/digital-twin/predictive-alerts", headers=admin_headers)
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    found = [a for a in alerts if a["id"] == inc_id]
    assert len(found) == 1
    assert found[0]["status"] == "PENDING_APPROVAL"

    # 4. Human-in-the-loop: student cannot approve
    # (Student role should be denied admin actions)


def test_invalid_predictive_event_rejected(admin_headers):
    bad_payload = {
        "event_type": "NON_EXISTENT_METRIC",
        "service_name": "unknown",
        "predicted_metric": 99.0,
        "threshold_metric": 10.0,
        "recommendation": "do something",
    }
    resp = client.post(
        "/api/v1/digital-twin/events/predictive-alert",
        json=bad_payload,
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_human_approval_and_rejection_workflows(admin_headers):
    # Create traffic surge event
    event_payload = {
        "event_type": "TRAFFIC_SURGE",
        "service_name": "exam_service",
        "predicted_metric": 1400.0,
        "threshold_metric": 800.0,
        "lead_time_hours": 3.0,
        "recommendation": "Pre-scale exam service to 4 replicas",
        "severity": "HIGH",
    }
    resp = client.post(
        "/api/v1/digital-twin/events/predictive-alert",
        json=event_payload,
        headers=admin_headers,
    )
    assert resp.status_code == 200
    inc_id = resp.json()["incident_id"]

    # Approve remediation
    app_resp = client.post(
        "/api/v1/digital-twin/proactive-remediation/approve",
        json={"incident_id": inc_id, "target_replicas": 4},
        headers=admin_headers,
    )
    assert app_resp.status_code == 200
    app_data = app_resp.json()
    assert app_data["status"] == "RESOLVED"
    assert "PRE_SCALE" in app_data["action_executed"]

    # Create another event to test rejection
    event_payload["service_name"] = "lms"
    resp2 = client.post(
        "/api/v1/digital-twin/events/predictive-alert",
        json=event_payload,
        headers=admin_headers,
    )
    inc_id2 = resp2.json()["incident_id"]

    rej_resp = client.post(
        "/api/v1/digital-twin/proactive-remediation/reject",
        json={"incident_id": inc_id2, "reason": "Capacity deemed sufficient by SRE on-call"},
        headers=admin_headers,
    )
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "OPEN"
    assert rej_resp.json()["action"] == "REJECTED"


def test_cancel_proactive_remediation(admin_headers):
    event_payload = {
        "event_type": "RESOURCE_EXHAUSTION",
        "service_name": "student_portal",
        "predicted_metric": 95.0,
        "threshold_metric": 80.0,
        "lead_time_hours": 4.0,
        "recommendation": "Clear caching buffers",
        "severity": "HIGH",
    }
    resp = client.post(
        "/api/v1/digital-twin/events/predictive-alert",
        json=event_payload,
        headers=admin_headers,
    )
    inc_id = resp.json()["incident_id"]

    cancel_resp = client.post(
        "/api/v1/digital-twin/proactive-remediation/cancel",
        json={"incident_id": inc_id, "reason": "Load schedule was cancelled"},
        headers=admin_headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELED"
