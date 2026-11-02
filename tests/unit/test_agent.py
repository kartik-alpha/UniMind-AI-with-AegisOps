import pytest
from app.models.user import User, UserRole
from app.models.ticket import Ticket
from app.models.audit import AuditLog
from app.core.security import create_access_token


def create_agent_test_user(db_session):
    student = User(
        email="agent_student@univ.edu",
        username="agent_student",
        full_name="Agent Student",
        hashed_password="hash",
        role=UserRole.STUDENT,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


def test_agent_create_ticket_tool(client, db_session):
    student = create_agent_test_user(db_session)
    headers = {"Authorization": f"Bearer {create_access_token(student.username)}"}

    response = client.post(
        "/api/v1/agent/run",
        json={"prompt": "Please create a ticket for WiFi issue in hostel block B"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tool_used"] == "create_support_ticket"
    assert "ticket_code" in data["tool_output"]
    assert "TICK-" in data["tool_output"]["ticket_code"]

    # Verify ticket in database
    t_code = data["tool_output"]["ticket_code"]
    db_ticket = db_session.query(Ticket).filter(Ticket.ticket_code == t_code).first()
    assert db_ticket is not None
    assert db_ticket.user_id == student.id

    # Verify audit log in database
    audit = db_session.query(AuditLog).filter(AuditLog.action == "AGENT_EXECUTION").first()
    assert audit is not None


def test_agent_check_service_status_tool(client, db_session):
    student = create_agent_test_user(db_session)
    headers = {"Authorization": f"Bearer {create_access_token(student.username)}"}

    response = client.post(
        "/api/v1/agent/run",
        json={"prompt": "Is the Exam Service down?"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tool_used"] == "check_service_status"
    assert data["tool_output"]["service"] == "Exam Service"
    assert data["tool_output"]["status"] == "DEGRADED"
