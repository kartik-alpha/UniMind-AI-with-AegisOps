import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from app.db.session import get_db, SessionLocal
from app.models.organization import Organization, OrganizationMembership, TenantStatus, TenantIndustry
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.ticket import Ticket, Incident
from app.core.security import create_access_token, get_password_hash


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="module")
def platform_admin_token(db_session: Session):
    admin = db_session.query(User).filter(User.username == "admin").first()
    db_session.rollback()
    return create_access_token(subject=admin.username)


@pytest.fixture(scope="module")
def student_token(db_session: Session):
    student = db_session.query(User).filter(User.username == "student").first()
    db_session.rollback()
    return create_access_token(subject=student.username)


def test_platform_admin_barrier(client: TestClient, student_token: str):
    """Verifies that non-platform users cannot access platform management endpoints."""
    res = client.get(
        "/api/v1/platform/tenants",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 403
    assert "Platform administration privileges required" in res.json()["detail"]


def test_tenant_provisioning_and_template_seeding(client: TestClient, db_session: Session, platform_admin_token: str):
    """Tests creating a new healthcare tenant with industry template presets."""
    # Ensure clean slate for idempotent testing
    existing_org = db_session.query(Organization).filter(Organization.slug == "apollo-health-test").first()
    if existing_org:
        db_session.query(Ticket).filter(Ticket.tenant_id == existing_org.id).delete()
        db_session.query(Incident).filter(Incident.tenant_id == existing_org.id).delete()
        db_session.query(Document).filter(Document.tenant_id == existing_org.id).delete()
        db_session.query(OrganizationMembership).filter(OrganizationMembership.tenant_id == existing_org.id).delete()
        db_session.query(User).filter(User.tenant_id == existing_org.id).delete()
        db_session.query(Organization).filter(Organization.id == existing_org.id).delete()
        db_session.commit()

    existing_user = db_session.query(User).filter(User.username == "apollo_admin").first()
    if existing_user:
        db_session.delete(existing_user)
        db_session.commit()
    db_session.commit()

    payload = {
        "name": "Apollo Metro Health",
        "slug": "apollo-health-test",
        "industry": "healthcare",
        "admin_email": "admin@apollohealth.org",
        "admin_username": "apollo_admin",
        "admin_password": "password123",
        "apply_industry_template": True,
    }
    res = client.post(
        "/api/v1/platform/tenants",
        json=payload,
        headers={"Authorization": f"Bearer {platform_admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Apollo Metro Health"
    assert data["slug"] == "apollo-health-test"
    assert data["industry"].upper() == "HEALTHCARE"
    assert data["status"].upper() == "ACTIVE"
    assert "clinical_protocols" in data["config"]["categories"]


def test_cross_tenant_document_and_query_isolation(client: TestClient, db_session: Session, platform_admin_token: str):
    """
    Validates strict cross-tenant isolation:
    - Documents from Tenant A cannot be listed or retrieved by Tenant B.
    - Vector search within Tenant A never retrieves content from Tenant B.
    """
    # 1. Fetch Tenant 1 (UniMind University) and Tenant 2 (Apollo Health)
    org_edu = db_session.query(Organization).filter(Organization.slug == "unimind-edu").first()
    org_health = db_session.query(Organization).filter(Organization.slug == "apollo-health-test").first()
    assert org_edu is not None
    assert org_health is not None

    apollo_admin = db_session.query(User).filter(User.username == "apollo_admin").first()
    assert apollo_admin is not None
    apollo_token = create_access_token(subject=apollo_admin.username)
    db_session.rollback()

    # 2. List documents as Tenant 1 (platform_admin belongs to unimind-edu)
    res_edu = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {platform_admin_token}"},
    )
    assert res_edu.status_code == 200
    edu_docs = res_edu.json()
    edu_titles = [d["title"] for d in edu_docs]

    # 3. List documents as Tenant 2 (apollo_admin)
    res_health = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {apollo_token}"},
    )
    assert res_health.status_code == 200
    health_docs = res_health.json()
    health_titles = [d["title"] for d in health_docs]

    # Cross-tenant boundary verification:
    for title in health_titles:
        assert title not in edu_titles, f"Tenant 2 document '{title}' leaked into Tenant 1!"

    # 4. Attempt to access Tenant 2 document using Tenant 1 credentials
    if health_docs:
        h_doc_id = health_docs[0]["id"]
        res_unauth = client.get(
            f"/api/v1/documents/{h_doc_id}",
            headers={"Authorization": f"Bearer {platform_admin_token}"},
        )
        assert res_unauth.status_code == 404, "Tenant 1 was able to access Tenant 2 document directly!"

    # 5. RAG Vector isolation check:
    # Querying Tenant 1 for healthcare protocols must return empty / no clinical chunks
    rag_query_edu = client.post(
        "/api/v1/rag/query",
        json={"query": "Emergency Severity Index Level 1 HIPAA", "top_k": 3},
        headers={"Authorization": f"Bearer {platform_admin_token}"},
    )
    assert rag_query_edu.status_code == 200
    edu_rag_results = rag_query_edu.json()["results"]
    for r in edu_rag_results:
        assert "Apollo" not in r["text"], "Apollo Health chunk leaked into UniMind University RAG!"


def test_cross_tenant_ticket_isolation(client: TestClient, db_session: Session, platform_admin_token: str):
    """Ensures support tickets are strictly isolated by tenant."""
    apollo_admin = db_session.query(User).filter(User.username == "apollo_admin").first()
    apollo_token = create_access_token(subject=apollo_admin.username)
    db_session.rollback()

    # Create ticket in Tenant 2 (Apollo Health)
    res_create = client.post(
        "/api/v1/tickets",
        json={
            "title": "EHR Gateway Connection Timeout",
            "description": "Port 9001 experiencing intermittent timeouts.",
            "category": "clinical_protocols",
            "priority": "high",
        },
        headers={"Authorization": f"Bearer {apollo_token}"},
    )
    assert res_create.status_code == 201
    apollo_ticket = res_create.json()

    # List tickets in Tenant 1 (UniMind University)
    res_edu = client.get(
        "/api/v1/tickets",
        headers={"Authorization": f"Bearer {platform_admin_token}"},
    )
    assert res_edu.status_code == 200
    edu_tickets = res_edu.json()
    edu_codes = [t["ticket_code"] for t in edu_tickets]

    assert apollo_ticket["ticket_code"] not in edu_codes, "Tenant 2 ticket leaked into Tenant 1 ticket queue!"


def test_tenant_suspension_lifecycle(client: TestClient, db_session: Session, platform_admin_token: str):
    """Validates that suspending a tenant blocks all authenticated access immediately with HTTP 403."""
    org_health = db_session.query(Organization).filter(Organization.slug == "apollo-health-test").first()
    assert org_health is not None
    apollo_admin = db_session.query(User).filter(User.username == "apollo_admin").first()
    apollo_token = create_access_token(subject=apollo_admin.username)
    db_session.rollback()

    # 1. Suspend Tenant
    res_suspend = client.post(
        f"/api/v1/platform/tenants/{org_health.id}/suspend",
        headers={"Authorization": f"Bearer {platform_admin_token}"},
    )
    assert res_suspend.status_code == 200
    assert res_suspend.json()["status"].upper() == "SUSPENDED"

    # 2. Verify all operations for this tenant now return HTTP 403 Forbidden
    res_blocked = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {apollo_token}"},
    )
    assert res_blocked.status_code == 403
    assert "currently suspended" in res_blocked.json()["detail"]

    # 3. Reactivate Tenant
    res_activate = client.post(
        f"/api/v1/platform/tenants/{org_health.id}/activate",
        headers={"Authorization": f"Bearer {platform_admin_token}"},
    )
    assert res_activate.status_code == 200
    assert res_activate.json()["status"].upper() == "ACTIVE"

    # 4. Verify operations work again
    res_restored = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {apollo_token}"},
    )
    assert res_restored.status_code == 200


def test_tenant_usage_stats(client: TestClient, db_session: Session, platform_admin_token: str):
    """Validates multi-tenant usage metering and storage calculation."""
    org_health = db_session.query(Organization).filter(Organization.slug == "apollo-health-test").first()
    assert org_health is not None
    db_session.rollback()

    res = client.get(
        f"/api/v1/platform/tenants/{org_health.id}/usage",
        headers={"Authorization": f"Bearer {platform_admin_token}"},
    )
    assert res.status_code == 200
    stats = res.json()
    assert stats["tenant_id"] == org_health.id
    assert stats["name"] == "Apollo Metro Health"
    assert stats["user_count"] >= 1
    assert stats["document_count"] >= 1
    assert stats["ticket_count"] >= 1
    assert stats["storage_bytes"] > 0
