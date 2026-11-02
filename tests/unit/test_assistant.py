import io
import pytest
from app.models.user import User, UserRole
from app.core.security import create_access_token


def create_student_helper(db_session):
    student = User(
        email="astudent@univ.edu",
        username="astudent",
        full_name="Alice Student",
        hashed_password="hash",
        role=UserRole.STUDENT,
    )
    admin = User(
        email="aadmin@univ.edu",
        username="aadmin",
        full_name="Admin Doc",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add_all([student, admin])
    db_session.commit()
    db_session.refresh(student)
    db_session.refresh(admin)
    return student, admin


def test_assistant_grounded_answer(client, db_session):
    student, admin = create_student_helper(db_session)
    admin_headers = {"Authorization": f"Bearer {create_access_token(admin.username)}"}
    student_headers = {"Authorization": f"Bearer {create_access_token(student.username)}"}

    # Upload & ingest hostel rules document
    hostel_text = b"Hostel Policy 2026: Mandatory hostel curfew is 10:00 PM for all undergraduate resident students."
    file = ("hostel_rules.txt", io.BytesIO(hostel_text), "text/plain")

    up_resp = client.post(
        "/api/v1/documents/upload",
        data={"title": "Hostel Guidelines 2026", "category": "hostel"},
        files={"file": file},
        headers=admin_headers,
    )
    doc_id = up_resp.json()["id"]
    client.post(f"/api/v1/rag/ingest/{doc_id}", headers=admin_headers)

    # Ask student question about curfew
    chat_resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "What is the mandatory hostel curfew time?"},
        headers=student_headers,
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "10:00 PM" in chat_data["bot_answer"] or "curfew" in chat_data["bot_answer"].lower()
    assert len(chat_data["sources"]) >= 1


def test_assistant_fallback_ungrounded(client, db_session):
    student, _ = create_student_helper(db_session)
    student_headers = {"Authorization": f"Bearer {create_access_token(student.username)}"}

    # Ask ungrounded question not in vector store
    chat_resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "What is the secret recipe for quantum rocket fuel at university?"},
        headers=student_headers,
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert chat_data["bot_answer"] == "Information not found in the university knowledge base."
    assert len(chat_data["sources"]) == 0
