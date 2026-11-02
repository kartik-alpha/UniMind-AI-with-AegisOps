import pytest
from app.models.user import User, UserRole
from app.models.ticket import Incident, IncidentSeverity
from app.core.security import create_access_token


def test_aegisops_endpoints(client, db_session):
    admin = User(
        email="aegisadmin@univ.edu",
        username="aegisadmin",
        full_name="Aegis Admin",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(admin.username)}"}

    # 1. Test Services API
    svc_resp = client.get("/api/v1/aegisops/services", headers=headers)
    assert svc_resp.status_code == 200
    assert len(svc_resp.json()) == 4

    # 2. Test Monitoring API
    mon_resp = client.get("/api/v1/aegisops/monitoring", headers=headers)
    assert mon_resp.status_code == 200
    assert "cpu_usage" in mon_resp.json()

    # 3. Test Metrics Table API
    met_resp = client.get("/api/v1/aegisops/metrics", headers=headers)
    assert met_resp.status_code == 200
    assert len(met_resp.json()) == 4

    # 4. Test Loki Logs API
    logs_resp = client.get("/api/v1/aegisops/logs", headers=headers)
    assert logs_resp.status_code == 200
    assert len(logs_resp.json()) >= 10

    # 5. Test AI Diagnosis API
    diag_resp = client.post("/api/v1/aegisops/diagnose/Exam Service", headers=headers)
    assert diag_resp.status_code == 200
    assert "suspected_root_cause" in diag_resp.json()

    # 6. Test Controlled Remediation API
    inc = Incident(
        incident_code="INC-2026-999",
        service_name="Exam Service",
        title="High Latency Degradation",
        severity=IncidentSeverity.HIGH,
    )
    db_session.add(inc)
    db_session.commit()

    rem_resp = client.post(
        f"/api/v1/aegisops/remediate?incident_id={inc.id}&action=RESTART_POD",
        headers=headers,
    )
    assert rem_resp.status_code == 200
    assert rem_resp.json()["status"] == "RESOLVED"
