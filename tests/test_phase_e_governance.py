"""
Phase E: Enterprise Security, Multi-Tenant Isolation & Zero-Trust Governance Test Suite.
Validates:
1. Cryptographic SHA-256 hash chaining on AuditLog records.
2. HMAC-SHA256 signature stamping and verification.
3. Cryptographic audit chain verification endpoint (GET /api/v1/governance/audit/verify-chain).
4. Tamper detection on modified log content, corrupted signatures, and broken links.
5. Zero-downtime secret key rotation for JWT authentication.
6. OWASP Top 10 API Security Headers enforcement.
7. Cross-tenant penetration attacks and BOLA/IDOR prevention.
8. Malicious header injection hardening (SQLi, path traversal, negative IDs).
"""
import json
import time
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, rotate_secret_key
from app.db.session import SessionLocal
from app.models.audit import AuditLog
from app.models.organization import Organization, TenantStatus, TenantIndustry
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.ticket import Ticket, TicketPriority, TicketStatus
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


@pytest.fixture
def tenant2_setup(db_session):
    # Ensure Tenant 2 exists
    org2 = db_session.query(Organization).filter(Organization.id == 2).first()
    if not org2:
        org2 = Organization(
            id=2,
            slug="tenant-2-corp",
            name="Tenant 2 Corp",
            industry=TenantIndustry.TECHNOLOGY,
            status=TenantStatus.ACTIVE,
            config={"storage_quota_bytes": 10485760},
        )
        db_session.add(org2)
        db_session.commit()

    # Ensure user for Tenant 2 exists
    user2 = db_session.query(User).filter(User.username == "user2_tenant2").first()
    if not user2:
        user2 = User(
            id=202,
            email="user2@tenant2.com",
            username="user2_tenant2",
            full_name="User Two",
            hashed_password="hashed_pw_test",
            role=UserRole.STUDENT,
            tenant_id=2,
            is_active=True,
        )
        db_session.add(user2)
        db_session.commit()

    token2 = create_access_token(subject="202")
    return {"org": org2, "user": user2, "token": token2, "headers": {"Authorization": f"Bearer {token2}", "X-Tenant-ID": "2"}}


# ---------------------------------------------------------------------------
# 1. Cryptographic Hash Chaining & HMAC Signatures
# ---------------------------------------------------------------------------

def test_phase_e_record_audit_event_hash_chain(db_session):
    """Verifies that record_audit_event computes SHA-256 chain and HMAC signature correctly."""
    # Record event 1
    action1 = f"PHASE_E_TEST_ACTION_1_{int(time.time()*1000)}"
    log1 = GovernanceService.record_audit_event(
        db=db_session,
        tenant_id=1,
        action=action1,
        performed_by="security-agent",
        target_resource="service/auth-gateway",
        status="SUCCESS",
        details={"ip": "10.0.0.1", "action_code": 101},
    )

    assert log1.id is not None
    assert log1.previous_hash is not None and len(log1.previous_hash) == 64
    assert log1.current_hash is not None and len(log1.current_hash) == 64
    assert log1.signature is not None and len(log1.signature) == 64

    # Verify log1 hash
    ts1 = log1.timestamp.isoformat()
    det1 = json.dumps(log1.details, sort_keys=True)
    expected_payload1 = f"{log1.previous_hash}|{log1.id}|{log1.tenant_id}|{log1.action}|{log1.performed_by}|{log1.target_resource}|{log1.status}|{ts1}|{det1}"
    expected_hash1 = hashlib.sha256(expected_payload1.encode("utf-8")).hexdigest()
    assert log1.current_hash == expected_hash1

    expected_sig1 = hmac.new(settings.SECRET_KEY.encode("utf-8"), expected_hash1.encode("utf-8"), hashlib.sha256).hexdigest()
    assert log1.signature == expected_sig1

    # Record event 2 for same tenant - must chain directly to log1.current_hash
    action2 = f"PHASE_E_TEST_ACTION_2_{int(time.time()*1000)}"
    log2 = GovernanceService.record_audit_event(
        db=db_session,
        tenant_id=1,
        action=action2,
        performed_by="security-agent",
        target_resource="service/auth-gateway",
        status="SUCCESS",
        details={"ip": "10.0.0.2", "action_code": 102},
    )

    assert log2.previous_hash == log1.current_hash
    ts2 = log2.timestamp.isoformat()
    det2 = json.dumps(log2.details, sort_keys=True)
    expected_payload2 = f"{log1.current_hash}|{log2.id}|{log2.tenant_id}|{log2.action}|{log2.performed_by}|{log2.target_resource}|{log2.status}|{ts2}|{det2}"
    expected_hash2 = hashlib.sha256(expected_payload2.encode("utf-8")).hexdigest()
    assert log2.current_hash == expected_hash2


# ---------------------------------------------------------------------------
# 2. Cryptographic Audit Chain Verification Endpoint
# ---------------------------------------------------------------------------

def test_phase_e_verify_audit_chain_endpoint(admin_headers, db_session):
    """Verifies that GET /api/v1/governance/audit/verify-chain confirms a valid chain."""
    GovernanceService.backfill_hash_chain(db_session, tenant_id=1)
    resp = client.get("/api/v1/governance/audit/verify-chain", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True, f"Failed verification: {data}"
    assert data["tenant_id"] == 1
    assert data["total_records"] > 0
    assert "chain_head_hash" in data
    assert len(data["chain_head_hash"]) == 64


# ---------------------------------------------------------------------------
# 3. Tamper Detection: Modified Content, Bad Signatures, Broken Links
# ---------------------------------------------------------------------------

def test_phase_e_audit_tamper_detection(db_session):
    """Verifies that tampering with log content, signature, or link is caught with exact record identification."""
    # Ensure logs exist
    GovernanceService.backfill_hash_chain(db_session, tenant_id=1)
    logs = db_session.query(AuditLog).filter(AuditLog.tenant_id == 1).order_by(AuditLog.id.asc()).all()
    assert len(logs) >= 2
    target_log = logs[-1]
    original_details = target_log.details.copy() if target_log.details else {}
    original_sig = target_log.signature
    original_prev_hash = target_log.previous_hash

    try:
        # 1. Content Tampering (simulate unauthorized SQL update of details)
        target_log.details = {"malicious_tamper": "unauthorized_change"}
        db_session.add(target_log)
        db_session.commit()

        res_tamper = GovernanceService.verify_audit_chain(db_session, tenant_id=1)
        assert res_tamper["is_valid"] is False
        assert res_tamper["tampered_record_id"] == target_log.id
        assert "Content tampering detected" in res_tamper["reason"]

        # Revert content tampering
        target_log.details = original_details
        db_session.add(target_log)
        db_session.commit()

        # 2. Signature Tampering (simulate forged HMAC signature)
        target_log.signature = "0" * 64
        db_session.add(target_log)
        db_session.commit()

        res_sig = GovernanceService.verify_audit_chain(db_session, tenant_id=1)
        assert res_sig["is_valid"] is False
        assert res_sig["tampered_record_id"] == target_log.id
        assert "Invalid cryptographic signature" in res_sig["reason"]

        # Revert signature
        target_log.signature = original_sig
        db_session.add(target_log)
        db_session.commit()

        # 3. Broken Chain Link (simulate rogue record insertion / deleted record)
        target_log.previous_hash = "deadbeef" * 8
        db_session.add(target_log)
        db_session.commit()

        res_link = GovernanceService.verify_audit_chain(db_session, tenant_id=1)
        assert res_link["is_valid"] is False
        assert res_link["tampered_record_id"] == target_log.id
        assert "Broken chain link" in res_link["reason"]

    finally:
        # Restore original state cleanly
        target_log.details = original_details
        target_log.signature = original_sig
        target_log.previous_hash = original_prev_hash
        db_session.add(target_log)
        db_session.commit()

    # Re-verify clean state
    clean_res = GovernanceService.verify_audit_chain(db_session, tenant_id=1)
    assert clean_res["is_valid"] is True


# ---------------------------------------------------------------------------
# 4. Zero-Downtime Secret Key Rotation
# ---------------------------------------------------------------------------

def test_phase_e_zero_downtime_secret_rotation():
    """Verifies that rotating secret keys retains support for previously issued active tokens."""
    orig_secret = settings.SECRET_KEY
    orig_old_keys = list(getattr(settings, "OLD_SECRET_KEYS", []))

    try:
        # Create token with original key
        token_v1 = create_access_token(subject="999")
        payload_v1 = decode_access_token(token_v1)
        assert payload_v1["sub"] == "999"

        # Rotate to new secret key
        new_secret = "new-cryptographic-secret-key-2026-unimind-enterprise-32b"
        rotate_secret_key(new_secret)
        assert settings.SECRET_KEY == new_secret
        assert orig_secret in settings.OLD_SECRET_KEYS

        # Verify token_v1 still decodes cleanly via OLD_SECRET_KEYS
        payload_v1_post_rotate = decode_access_token(token_v1)
        assert payload_v1_post_rotate["sub"] == "999"

        # Create token_v2 with new key
        token_v2 = create_access_token(subject="999")
        payload_v2 = decode_access_token(token_v2)
        assert payload_v2["sub"] == "999"

        # Foreign token signed with arbitrary key must fail
        fake_token = hmac.new(b"fake", b"fake", hashlib.sha256).hexdigest()
        with pytest.raises(Exception):
            decode_access_token(fake_token)

    finally:
        # Restore configuration
        settings.SECRET_KEY = orig_secret
        settings.OLD_SECRET_KEYS = orig_old_keys


# ---------------------------------------------------------------------------
# 5. OWASP Top 10 Security Headers
# ---------------------------------------------------------------------------

def test_phase_e_owasp_security_headers():
    """Verifies that all API responses include OWASP Top 10 security hardening headers."""
    resp = client.get("/")
    assert resp.status_code == 200
    headers = resp.headers

    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers.get("permissions-policy", "")


# ---------------------------------------------------------------------------
# 6. Cross-Tenant Penetration & IDOR Prevention
# ---------------------------------------------------------------------------

def test_phase_e_cross_tenant_idor_penetration(tenant2_setup, admin_headers):
    """Verifies that users cannot access resources or audit logs belonging to another tenant."""
    t2_headers = tenant2_setup["headers"]

    # Tenant 2 user attempting to access Tenant 1 governance status
    # When Tenant 2 user passes X-Tenant-ID: 1 -> Header spoofing protection must reject with 403 Forbidden
    spoofed_headers = {
        "Authorization": t2_headers["Authorization"],
        "X-Tenant-ID": "1",
    }
    resp_spoof = client.get("/api/v1/governance/status", headers=spoofed_headers)
    assert resp_spoof.status_code == 403

    # Tenant 2 user attempting to verify Tenant 1 audit chain
    resp_audit_spoof = client.get("/api/v1/governance/audit/verify-chain", headers=spoofed_headers)
    assert resp_audit_spoof.status_code == 403

    # Tenant 2 user accessing their own governance status -> 200 OK
    resp_t2 = client.get("/api/v1/governance/status", headers=t2_headers)
    assert resp_t2.status_code == 200
    assert resp_t2.json()["tenant_id"] == 2


# ---------------------------------------------------------------------------
# 7. Malicious Tenant Header Injection Hardening
# ---------------------------------------------------------------------------

def test_phase_e_tenant_header_injection_attacks(admin_headers):
    """Verifies rejection of malformed or malicious X-Tenant-ID payloads."""
    malicious_headers = [
        "1 OR 1=1 --",
        "../../etc/passwd",
        "<script>alert(1)</script>",
        "-5",
        "0",
        "abc_invalid",
    ]
    for bad_tid in malicious_headers:
        headers = {
            "Authorization": admin_headers["Authorization"],
            "X-Tenant-ID": bad_tid,
        }
        resp = client.get("/api/v1/governance/status", headers=headers)
        assert resp.status_code == 400, f"Expected 400 for malicious header '{bad_tid}', got {resp.status_code}"
