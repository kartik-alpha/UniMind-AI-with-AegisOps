import io
import pytest
from app.models.user import User, UserRole
from app.core.security import create_access_token


def create_user_helper(db_session, email, username, full_name, role):
    user = User(
        email=email,
        username=username,
        full_name=full_name,
        hashed_password="hash",
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_rag_ingest_and_query(client, db_session):
    admin = create_user_helper(db_session, "admin_rag@univ.edu", "admin_rag", "Admin RAG", UserRole.ADMIN)
    token = create_access_token(admin.username)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upload Document
    doc_content = b"Examinations Policy: End-semester exams account for 60% of total grade. Re-evaluation requests must be submitted within 7 days of result declaration."
    file = ("exam_policy.txt", io.BytesIO(doc_content), "text/plain")

    upload_resp = client.post(
        "/api/v1/documents/upload",
        data={"title": "Examination Policy 2026", "category": "examinations"},
        files={"file": file},
        headers=headers,
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # 2. Ingest Document into RAG Vector Store
    ingest_resp = client.post(f"/api/v1/rag/ingest/{doc_id}", headers=headers)
    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.json()
    assert ingest_data["chunks_indexed"] >= 1

    # 3. Perform RAG Semantic Query
    query_resp = client.post(
        "/api/v1/rag/query",
        json={"query": "What is the weightage of end-semester exams and re-evaluation timeline?", "top_k": 3},
        headers=headers,
    )
    assert query_resp.status_code == 200
    query_data = query_resp.json()
    assert query_data["total_found"] >= 1
    top_match = query_data["results"][0]
    assert "60%" in top_match["text"] or "re-evaluation" in top_match["text"].lower()
    assert top_match["metadata"]["category"] == "examinations"
