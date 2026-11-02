import io
import pytest
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token


def create_user_helper(db_session, email, username, full_name, role):
    user = User(
        email=email,
        username=username,
        full_name=full_name,
        hashed_password=get_password_hash("Pass12345!"),
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def get_user_token(user):
    return create_access_token(user.username)


def test_document_upload_and_listing(client, db_session):
    admin = create_user_helper(db_session, "admin@univ.edu", "admin_doc", "Admin User", UserRole.ADMIN)
    student = create_user_helper(db_session, "student@univ.edu", "student_doc", "Student User", UserRole.STUDENT)

    admin_token = get_user_token(admin)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Upload test document
    file_content = b"Attendance Rule: Minimum 75% attendance is required to sit for end-semester exams."
    file = ("attendance_policy.txt", io.BytesIO(file_content), "text/plain")

    response = client.post(
        "/api/v1/documents/upload",
        data={"title": "Attendance Policy 2026", "category": "attendance"},
        files={"file": file},
        headers=headers,
    )

    assert response.status_code == 201
    doc_data = response.json()
    assert doc_data["title"] == "Attendance Policy 2026"
    assert doc_data["category"] == "attendance"
    assert doc_data["filename"] == "attendance_policy.txt"
    doc_id = doc_data["id"]

    # List documents as Student
    student_token = get_user_token(student)
    student_headers = {"Authorization": f"Bearer {student_token}"}

    list_resp = client.get("/api/v1/documents", headers=student_headers)
    assert list_resp.status_code == 200
    docs = list_resp.json()
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id

    # Filter by category
    filter_resp = client.get("/api/v1/documents?category=attendance", headers=student_headers)
    assert filter_resp.status_code == 200
    assert len(filter_resp.json()) == 1

    # Delete document as Admin
    del_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert del_resp.status_code == 200


def test_student_upload_forbidden(client, db_session):
    student = create_user_helper(db_session, "student2@univ.edu", "student2_doc", "Student 2", UserRole.STUDENT)
    student_token = get_user_token(student)
    headers = {"Authorization": f"Bearer {student_token}"}

    file_content = b"Some unauthorized content"
    file = ("unauth.txt", io.BytesIO(file_content), "text/plain")

    response = client.post(
        "/api/v1/documents/upload",
        data={"title": "Unauthorized Doc", "category": "hostel"},
        files={"file": file},
        headers=headers,
    )

    assert response.status_code == 403
