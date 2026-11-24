import pytest
from app.models.user import User, UserRole
from app.models.ticket import Incident, IncidentStatus
from app.models.audit import AuditLog
from app.core.security import create_access_token
from scripts.chaos_simulator import get_chaos_simulator


@pytest.fixture(autouse=True)
def reset_chaos_baseline():
    sim = get_chaos_simulator()
    sim.restore_all()
    yield
    sim.restore_all()


def create_user(db_session, username, role):
    user = User(
        email=f"{username}@unimind.edu",
        username=username,
        full_name=f"{username.title()} User",
        hashed_password="hashed_pw",
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_end_to_end_chaos_to_incident_and_remediation(client, db_session):
    admin = create_user(db_session, "sre_admin", UserRole.ADMIN)
    admin_headers = {"Authorization": f"Bearer {create_access_token(admin.username)}"}

    # 1. Inject Chaos Failure
    inject_resp = client.post(
        "/api/v1/aegisops/chaos/inject",
        json={
            "service_name": "exam_service",
            "scenario": "database",
            "severity": "CRITICAL",
            "duration_seconds": 60,
        },
        headers=admin_headers,
    )
    assert inject_resp.status_code == 200
    inject_data = inject_resp.json()
    assert inject_data["status"] == "INJECTED"
    assert inject_data["anomaly_score"] >= 0.70
    assert inject_data["is_anomaly"] is True
    assert inject_data["incident"] is not None

    incident_id = inject_data["incident"]["id"]
    incident_code = inject_data["incident"]["incident_code"]

    # 2. Verify Incident in Database
    db_inc = db_session.query(Incident).filter(Incident.id == incident_id).first()
    assert db_inc is not None
    assert db_inc.status == IncidentStatus.PENDING_APPROVAL
    assert "database" in db_inc.root_cause.lower()

    # 3. AI Root Cause Diagnosis
    diag_resp = client.post("/api/v1/aegisops/diagnose/exam_service", headers=admin_headers)
    assert diag_resp.status_code == 200
    diag_data = diag_resp.json()
    assert "Database connection pool exhaustion" in diag_data["suspected_root_cause"]
    assert "RESTART_POD" in diag_data["recommended_remediation"]
    assert diag_data["confidence_score"] >= 0.85
    assert "Runbook" in diag_data["matched_runbook_title"]

    # 4. Human-in-the-Loop Remediation Approval (Admin)
    rem_resp = client.post(
        "/api/v1/aegisops/remediate/approve",
        json={"incident_id": incident_id, "action": "RESTART_POD", "target_replicas": 4},
        headers=admin_headers,
    )
    assert rem_resp.status_code == 200
    rem_data = rem_resp.json()
    assert rem_data["status"] == "RESOLVED"
    assert rem_data["verified_recovery"] is True
    assert rem_data["approved_by"] == "sre_admin"

    # 5. Verify Recovery in Database and Telemetry
    db_session.refresh(db_inc)
    assert db_inc.status == IncidentStatus.RESOLVED

    # 6. Verify Security Audit Log Created
    audit = db_session.query(AuditLog).filter(
        AuditLog.target_resource == f"incident/{incident_code}",
        AuditLog.action == "REMEDIATION_RESOLVED",
    ).first()
    assert audit is not None
    assert audit.performed_by == "sre_admin"
    assert audit.details["verified_recovery"] is True


def test_incident_deduplication(client, db_session):
    admin = create_user(db_session, "dedup_admin", UserRole.ADMIN)
    headers = {"Authorization": f"Bearer {create_access_token(admin.username)}"}

    # Inject failure 1st time
    resp1 = client.post(
        "/api/v1/aegisops/chaos/inject",
        json={"service_name": "lms", "scenario": "memory", "severity": "HIGH", "duration_seconds": 60},
        headers=headers,
    )
    assert resp1.status_code == 200
    inc_id_1 = resp1.json()["incident"]["id"]

    # Inject failure 2nd time on same service while still unresolved
    resp2 = client.post(
        "/api/v1/aegisops/chaos/inject",
        json={"service_name": "lms", "scenario": "memory", "severity": "CRITICAL", "duration_seconds": 60},
        headers=headers,
    )
    assert resp2.status_code == 200
    inc_id_2 = resp2.json()["incident"]["id"]

    # Must update the existing incident, NOT create a second duplicate incident
    assert inc_id_1 == inc_id_2

    # Clean up LMS incident
    inc = db_session.query(Incident).filter(Incident.id == inc_id_1).first()
    inc.status = IncidentStatus.RESOLVED
    db_session.commit()


def test_remediation_rejection_flow(client, db_session):
    admin = create_user(db_session, "reject_admin", UserRole.ADMIN)
    headers = {"Authorization": f"Bearer {create_access_token(admin.username)}"}

    # Inject failure
    resp = client.post(
        "/api/v1/aegisops/chaos/inject",
        json={"service_name": "student_portal", "scenario": "network", "severity": "HIGH", "duration_seconds": 60},
        headers=headers,
    )
    inc_id = resp.json()["incident"]["id"]

    # Admin rejects suggested remediation
    rej_resp = client.post(
        "/api/v1/aegisops/remediate/reject",
        json={"incident_id": inc_id, "reason": "Awaiting maintenance window"},
        headers=headers,
    )
    assert rej_resp.status_code == 200
    rej_data = rej_resp.json()
    assert rej_data["action"] == "REJECTED"

    db_inc = db_session.query(Incident).filter(Incident.id == inc_id).first()
    assert db_inc.status == IncidentStatus.OPEN
    assert "Awaiting maintenance window" in db_inc.action_taken

    # Audit log check
    audit = db_session.query(AuditLog).filter(
        AuditLog.action == "REMEDIATION_REJECTED",
        AuditLog.performed_by == "reject_admin",
    ).first()
    assert audit is not None


def test_unauthorized_user_remediation_blocked(client, db_session):
    student = create_user(db_session, "unauthorized_student", UserRole.STUDENT)
    student_headers = {"Authorization": f"Bearer {create_access_token(student.username)}"}

    inc = Incident(
        incident_code="INC-2026-UNAUTH",
        service_name="Exam Service",
        title="Unauthorized Test",
        status=IncidentStatus.PENDING_APPROVAL,
    )
    db_session.add(inc)
    db_session.commit()

    # Student attempts to approve remediation -> Forbidden
    resp = client.post(
        "/api/v1/aegisops/remediate/approve",
        json={"incident_id": inc.id, "action": "RESTART_POD"},
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_prevent_duplicate_remediation_on_resolved_incident(client, db_session):
    admin = create_user(db_session, "resolved_admin", UserRole.ADMIN)
    headers = {"Authorization": f"Bearer {create_access_token(admin.username)}"}

    inc = Incident(
        incident_code="INC-2026-RESOLVED",
        service_name="Exam Service",
        title="Already Resolved Incident",
        status=IncidentStatus.RESOLVED,
    )
    db_session.add(inc)
    db_session.commit()

    # Re-executing remediation on resolved incident must fail
    resp = client.post(
        "/api/v1/aegisops/remediate/approve",
        json={"incident_id": inc.id, "action": "RESTART_POD"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "already RESOLVED" in resp.json()["detail"]
