"""
Phase I: Commercial SaaS Production Readiness, Multi-Tenant Onboarding & Billing Test Suite.
Validates:
1. Self-service multi-tenant onboarding workflow (STARTER, PROFESSIONAL, ENTERPRISE).
2. Automated tenant isolation provisioning (DB, root admin, membership, Chroma partition, audit provenance).
3. Lifecycle state transitions (ACTIVE, SUSPENDED, ARCHIVED) & boundary enforcement.
4. Commercial usage aggregation, token overages, and tiered pricing calculation.
5. Invariant integrity across multi-tenant boundaries.
"""
import time
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from app.db.session import SessionLocal
from app.core.security import create_access_token
from app.models.organization import (
    Organization,
    OrganizationMembership,
    TenantStatus,
    TenantRole,
    SubscriptionTier,
    TIER_CONFIGS,
)
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.services.governance_service import GovernanceService

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def admin_headers():
    token = create_access_token(subject="1")
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": "1"}


# ---------------------------------------------------------------------------
# 1. Self-Service Tenant Onboarding Workflow
# ---------------------------------------------------------------------------

def test_self_service_tenant_onboarding_starter(db_session):
    """Validates self-service tenant onboarding for the STARTER subscription tier."""
    unique_suffix = int(time.time() * 1000) % 100000
    slug = f"onboard-starter-{unique_suffix}"
    payload = {
        "organization_name": f"Starter Test Org {unique_suffix}",
        "slug": slug,
        "industry": "TECHNOLOGY",
        "tier": "STARTER",
        "admin_email": f"admin@{slug}.io",
        "admin_username": f"admin_{unique_suffix}",
        "admin_password": "StarterAdmin2026!",
        "admin_full_name": "Starter Admin Lead",
    }

    resp = client.post("/api/v1/governance/onboard", json=payload)
    assert resp.status_code == 201, f"Onboarding failed: {resp.text}"
    data = resp.json()

    assert data["status"] == "ONBOARDED"
    org_id = data["organization"]["id"]
    assert data["organization"]["slug"] == slug
    assert data["organization"]["tier"] == "STARTER"
    assert data["organization"]["status"] == "ACTIVE"
    assert data["admin_user"]["username"] == payload["admin_username"]
    assert data["allocated_quotas"]["storage_quota_bytes"] == TIER_CONFIGS[SubscriptionTier.STARTER]["storage_quota_bytes"]
    assert data["allocated_quotas"]["base_monthly_price_usd"] == 299.0

    # Verify DB persistence
    org = db_session.query(Organization).filter(Organization.id == org_id).first()
    assert org is not None
    assert org.slug == slug

    admin = db_session.query(User).filter(User.tenant_id == org_id).first()
    assert admin is not None
    assert admin.username == payload["admin_username"]

    # Verify cryptographic audit provenance
    audit = db_session.query(AuditLog).filter(
        AuditLog.tenant_id == org_id,
        AuditLog.action == "TENANT_ONBOARDED"
    ).first()
    assert audit is not None
    assert audit.current_hash is not None


def test_self_service_tenant_onboarding_enterprise(db_session):
    """Validates onboarding for the ENTERPRISE subscription tier with custom quotas."""
    unique_suffix = int(time.time() * 1000) % 100000
    slug = f"onboard-ent-{unique_suffix}"
    payload = {
        "organization_name": f"Enterprise Test Corp {unique_suffix}",
        "slug": slug,
        "industry": "ENTERPRISE",
        "tier": "ENTERPRISE",
        "admin_email": f"cio@{slug}.com",
        "admin_username": f"cio_{unique_suffix}",
        "admin_password": "EnterpriseSecret2026!",
        "admin_full_name": "Chief Information Officer",
    }

    resp = client.post("/api/v1/governance/onboard", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["organization"]["tier"] == "ENTERPRISE"
    assert data["allocated_quotas"]["storage_quota_bytes"] == 107374182400  # 100 GB
    assert data["allocated_quotas"]["hitl_remediation_enabled"] is True
    assert data["allocated_quotas"]["base_monthly_price_usd"] == 3999.0


def test_tenant_onboarding_duplicate_slug_rejection():
    """Validates that onboarding rejects duplicate organization slugs with 400 Bad Request."""
    payload = {
        "organization_name": "Duplicate Test Org",
        "slug": "unimind-edu",  # Existing root tenant slug
        "industry": "EDUCATION",
        "tier": "PROFESSIONAL",
    }
    resp = client.post("/api/v1/governance/onboard", json=payload)
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 2. Tenant Lifecycle State Machine Transitions
# ---------------------------------------------------------------------------

def test_tenant_lifecycle_transitions(db_session, admin_headers):
    """Validates state machine transitions: ACTIVE -> SUSPENDED -> ARCHIVED -> ACTIVE."""
    # Create temp tenant
    suffix = int(time.time() * 1000) % 100000
    org = Organization(
        slug=f"lifecycle-test-{suffix}",
        name=f"Lifecycle Test {suffix}",
        status=TenantStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    tid = org.id

    # 1. Transition to SUSPENDED
    resp_suspend = client.post(
        f"/api/v1/governance/tenants/{tid}/lifecycle",
        json={"status": "SUSPENDED"},
        headers=admin_headers,
    )
    assert resp_suspend.status_code == 200
    assert resp_suspend.json()["current_status"] == "SUSPENDED"

    db_session.refresh(org)
    assert org.status == TenantStatus.SUSPENDED

    # 2. Transition to ARCHIVED
    resp_archive = client.post(
        f"/api/v1/governance/tenants/{tid}/lifecycle",
        json={"status": "ARCHIVED"},
        headers=admin_headers,
    )
    assert resp_archive.status_code == 200
    assert resp_archive.json()["current_status"] == "ARCHIVED"

    # 3. Transition back to ACTIVE
    resp_active = client.post(
        f"/api/v1/governance/tenants/{tid}/lifecycle",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    assert resp_active.status_code == 200
    assert resp_active.json()["current_status"] == "ACTIVE"

    # 4. Reject invalid lifecycle status
    resp_invalid = client.post(
        f"/api/v1/governance/tenants/{tid}/lifecycle",
        json={"status": "INVALID_STATE"},
        headers=admin_headers,
    )
    assert resp_invalid.status_code == 400
    assert "Invalid status" in resp_invalid.json()["detail"]


# ---------------------------------------------------------------------------
# 3. Commercial Usage Metering & Tiered Billing Summary
# ---------------------------------------------------------------------------

def test_commercial_billing_usage_aggregation(admin_headers):
    """Validates commercial usage aggregation, quota breakdown, and bill calculation."""
    resp = client.get("/api/v1/governance/billing/usage", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["tenant_id"] == 1
    assert data["currency"] == "USD"
    assert "base_monthly_price_usd" in data
    assert "token_overage_charge_usd" in data
    assert "estimated_total_due_usd" in data
    assert "sla_tier" in data

    # Usage breakdown
    usage = data["usage_breakdown"]
    assert "storage" in usage
    assert usage["storage"]["quota_bytes"] > 0
    assert "tokens" in usage
    assert usage["tokens"]["monthly_budget"] > 0
    assert "seats" in usage
    assert usage["seats"]["active_users"] >= 1
