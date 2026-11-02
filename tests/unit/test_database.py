import pytest
from app.models import (
    User,
    UserRole,
    Incident,
    IncidentSeverity,
    AuditLog,
)


def test_db_create_user(db_session):
    user = User(
        email="student@university.edu",
        username="student1",
        full_name="Alex Student",
        hashed_password="hashed_pass_123",
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    db_session.flush()

    assert user.id is not None
    assert user.email == "student@university.edu"
    assert user.role == UserRole.STUDENT


def test_db_create_incident_and_audit(db_session):
    incident = Incident(
        incident_code="INC-2026-001",
        service_name="exam-service",
        title="Exam Service High Latency & Memory Pressure",
        severity=IncidentSeverity.HIGH,
        anomaly_score=0.91,
        metrics_summary={"cpu": 92.0, "latency": 1800, "errors": 0.14},
    )
    db_session.add(incident)

    audit = AuditLog(
        action="ANOMALY_DETECTED",
        performed_by="AegisOps-Engine",
        target_resource="service/exam-service",
        status="SUCCESS",
        details={"score": 0.91},
    )
    db_session.add(audit)
    db_session.flush()

    saved_inc = db_session.query(Incident).filter_by(incident_code="INC-2026-001").first()
    assert saved_inc is not None
    assert saved_inc.service_name == "exam-service"
    assert saved_inc.anomaly_score == 0.91

    saved_audit = db_session.query(AuditLog).filter_by(action="ANOMALY_DETECTED").first()
    assert saved_audit is not None
    assert saved_audit.performed_by == "AegisOps-Engine"
