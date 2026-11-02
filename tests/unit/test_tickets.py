import pytest
from app.models.user import User, UserRole
from app.models.ticket import Incident, IncidentSeverity
from app.core.security import create_access_token


def create_ticket_test_users(db_session):
    student = User(
        email="tstudent@univ.edu",
        username="tstudent",
        full_name="Ticket Student",
        hashed_password="hash",
        role=UserRole.STUDENT,
    )
    admin = User(
        email="tadmin@univ.edu",
        username="tadmin",
        full_name="Ticket Admin",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add_all([student, admin])
    db_session.commit()
    db_session.refresh(student)
    db_session.refresh(admin)
    return student, admin


def test_create_and_update_ticket(client, db_session):
    student, admin = create_ticket_test_users(db_session)
    student_headers = {"Authorization": f"Bearer {create_access_token(student.username)}"}
    admin_headers = {"Authorization": f"Bearer {create_access_token(admin.username)}"}

    # 1. Create ticket as student
    create_resp = client.post(
        "/api/v1/tickets",
        json={
            "title": "Library portal error 500",
            "description": "Unable to renew books online.",
            "category": "library",
            "priority": "HIGH",
        },
        headers=student_headers,
    )
    assert create_resp.status_code == 201
    t_data = create_resp.json()
    assert t_data["status"] == "OPEN"
    ticket_id = t_data["id"]

    # 2. Update status as Admin
    patch_resp = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "IN_PROGRESS", "assigned_to": "admin_team"},
        headers=admin_headers,
    )
    assert patch_resp.status_code == 200
    updated_data = patch_resp.json()
    assert updated_data["status"] == "IN_PROGRESS"
    assert updated_data["assigned_to"] == "admin_team"


def test_list_incidents(client, db_session):
    student, _ = create_ticket_test_users(db_session)
    student_headers = {"Authorization": f"Bearer {create_access_token(student.username)}"}

    incident = Incident(
        incident_code="INC-2026-888",
        service_name="exam_service",
        title="Database CPU spike",
        severity=IncidentSeverity.CRITICAL,
        anomaly_score=0.95,
    )
    db_session.add(incident)
    db_session.commit()

    inc_resp = client.get("/api/v1/incidents", headers=student_headers)
    assert inc_resp.status_code == 200
    inc_list = inc_resp.json()
    assert len(inc_list) >= 1
    assert inc_list[0]["incident_code"] == "INC-2026-888"
