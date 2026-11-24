"""
Phase B Architecture & Platform Foundation Verification Test Suite.
Validates:
1. Real-time SSE Streaming (/assistant/chat/stream)
2. RFC 7807 Problem Details Error Protocol
3. Granular Multi-Tenant RBAC Permissions Engine
4. Pydantic v2 Settings Secret Masking & Production Guardrails
5. Hexagonal Adapter Pool Hooks & Health Status
"""
import json
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.permissions import (
    Permission,
    ROLE_PERMISSIONS,
    get_user_effective_permissions,
    has_permission,
)
from app.models.user import User, UserRole
from app.models.organization import Organization, OrganizationMembership, TenantRole, TenantStatus
from app.adapters.database import SQLiteDatabaseAdapter


def test_sse_chat_streaming(client: TestClient, db_session):
    """Test real-time Server-Sent Events token streaming endpoint."""
    response = client.post(
        "/api/v1/assistant/chat/stream",
        json={"message": "What is the attendance policy?", "mode": "hybrid"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    lines = response.text.strip().split("\n\n")
    assert len(lines) >= 2, f"Expected multi-event stream, got: {len(lines)} frames"

    events = []
    for line in lines:
        if line.startswith("data: "):
            payload = json.loads(line[6:])
            events.append(payload)

    # Verify token events
    token_events = [e for e in events if not e.get("done", False)]
    assert len(token_events) >= 1
    assert "token" in token_events[0]

    # Verify terminal event
    terminal = events[-1]
    assert terminal["done"] is True
    assert "bot_answer" in terminal
    assert "sources" in terminal
    assert "conversation_id" in terminal


def test_rfc7807_problem_details_error_handling(client: TestClient):
    """Test RFC 7807 Problem Details compliance on HTTP error responses."""
    # 404 Not Found
    res = client.get("/api/v1/documents/999999")
    assert res.status_code == 404
    assert "application/problem+json" in res.headers.get("content-type", "")

    data = res.json()
    # RFC 7807 Core Fields
    assert data["status"] == 404
    assert data["title"] == "Not Found"
    assert "type" in data
    assert "instance" in data
    assert "detail" in data
    # Enterprise Extensions & Backward-Compatibility
    assert "request_id" in data
    assert "error" in data
    assert data["error"]["code"] == "HTTP_404"


def test_granular_rbac_permissions(db_session):
    """Test unified granular RBAC permission resolution across UserRole and TenantRole."""
    # Create Student
    student = User(
        id=201,
        email="stud_rbac@univ.edu",
        username="stud_rbac",
        full_name="Student RBAC",
        hashed_password="hash",
        role=UserRole.STUDENT,
        tenant_id=1,
    )
    # Create Faculty
    faculty = User(
        id=202,
        email="fac_rbac@univ.edu",
        username="fac_rbac",
        full_name="Faculty RBAC",
        hashed_password="hash",
        role=UserRole.FACULTY,
        tenant_id=1,
    )
    # Create Admin
    admin = User(
        id=203,
        email="admin_rbac@univ.edu",
        username="admin_rbac",
        full_name="Admin RBAC",
        hashed_password="hash",
        role=UserRole.ADMIN,
        tenant_id=1,
    )
    db_session.add_all([student, faculty, admin])
    db_session.commit()

    # 1. Student permissions
    stud_perms = get_user_effective_permissions(student, tenant_id=1, db=db_session)
    assert Permission.DOCUMENTS_READ in stud_perms
    assert Permission.DOCUMENTS_DELETE not in stud_perms
    assert Permission.DOCUMENTS_UPLOAD not in stud_perms
    assert has_permission(student, Permission.DOCUMENTS_READ, tenant_id=1, db=db_session)
    assert not has_permission(student, Permission.DOCUMENTS_DELETE, tenant_id=1, db=db_session)

    # 2. Faculty permissions
    fac_perms = get_user_effective_permissions(faculty, tenant_id=1, db=db_session)
    assert Permission.DOCUMENTS_UPLOAD in fac_perms
    assert Permission.DOCUMENTS_DELETE not in fac_perms

    # 3. Admin permissions (Global or Tenant)
    assert has_permission(admin, Permission.DOCUMENTS_DELETE, tenant_id=1, db=db_session)
    assert has_permission(admin, Permission.TENANT_MANAGE, tenant_id=1, db=db_session)


def test_settings_secret_masking_and_validation():
    """Test Pydantic v2 Settings secret masking and production zero-trust rejection."""
    s = Settings(
        SECRET_KEY="super-secret-key-1234567890-test",
        OPENAI_API_KEY="sk-proj-1234567890abcdef",
        ENVIRONMENT="development",
    )
    masked = s.masked_dict()
    assert masked["SECRET_KEY"] != "super-secret-key-1234567890-test"
    assert "..." in masked["SECRET_KEY"]
    assert masked["OPENAI_API_KEY"].startswith("sk-")
    assert "..." in masked["OPENAI_API_KEY"]

    # Production Mode with Default Key Must Fail
    with pytest.raises(ValueError, match="CRITICAL SECURITY HAZARD"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="unimind-super-secret-key-change-in-production-2026",
        )


def test_sqlite_adapter_wal_hooks_and_health():
    """Test SQLite Database Adapter connection hooks, health check, and execution."""
    adapter = SQLiteDatabaseAdapter(database_url="sqlite:///:memory:")
    adapter.connect()
    try:
        health = adapter.health_check()
        assert health["status"] == "healthy"
        assert health["dialect"] == "sqlite"

        # Verify raw execution
        res = adapter.execute_raw("SELECT 42 as num;")
        assert res[0]["num"] == 42
    finally:
        adapter.disconnect()
