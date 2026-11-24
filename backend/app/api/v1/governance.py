"""
Enterprise Governance, Quotas, Rate Limiting & Tamper-Evident Audit Export API Router.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.api.tenant_deps import get_current_tenant, require_tenant_roles
from app.models.user import User, UserRole
from app.models.organization import Organization, TenantRole
from app.services.governance_service import GovernanceService
from app.adapters.factory import AdapterFactory

router = APIRouter(prefix="/governance", tags=["Enterprise Governance"])


class GovernanceControlsUpdate(BaseModel):
    storage_quota_bytes: Optional[int] = Field(None, description="Max storage in bytes", gt=0)
    rate_limit_per_min: Optional[int] = Field(None, description="Max API requests per minute", gt=0)
    monthly_token_budget: Optional[int] = Field(None, description="Monthly LLM token budget", gt=0)


@router.get("/status", summary="Get tenant governance status, quota usage, and token accounting")
def get_governance_status(
    current_tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GovernanceService.get_governance_summary(db, current_tenant.id)


@router.get("/tokens", summary="Get tenant monthly token usage and warning status")
def get_token_usage(
    month: Optional[str] = Query(None, description="Month in YYYY-MM format"),
    current_tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    cache_broker = AdapterFactory.get_cache()
    return cache_broker.get_token_usage(current_tenant.id, month_str=month)


@router.post(
    "/controls",
    summary="Update tenant governance quotas, rate limits, and token budgets (Admin only)",
    dependencies=[Depends(require_tenant_roles(UserRole.ADMIN, TenantRole.TENANT_ADMIN, TenantRole.PLATFORM_ADMIN))],
)
def update_governance_controls(
    payload: GovernanceControlsUpdate,
    current_tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GovernanceService.update_governance_controls(
        db=db,
        tenant_id=current_tenant.id,
        storage_quota_bytes=payload.storage_quota_bytes,
        rate_limit_per_min=payload.rate_limit_per_min,
        monthly_token_budget=payload.monthly_token_budget,
    )


@router.get("/audit/export", summary="Export tamper-evident, hash-chained audit logs (JSONL or CSV)")
def export_audit_logs(
    format: str = Query("jsonl", pattern="^(jsonl|csv)$"),
    start_date: Optional[str] = Query(None, description="ISO start date filter"),
    end_date: Optional[str] = Query(None, description="ISO end date filter"),
    current_tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content, mime_type, filename = GovernanceService.export_tamper_evident_audit_logs(
        db=db,
        tenant_id=current_tenant.id,
        export_format=format,
        start_date=start_date,
        end_date=end_date,
    )

    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit/verify-chain", summary="Cryptographically verify tamper-evident audit hash chain")
def verify_audit_chain(
    current_tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GovernanceService.verify_audit_chain(db=db, tenant_id=current_tenant.id)


@router.post(
    "/audit/backfill-chain",
    summary="Backfill cryptographic hash chain and HMAC signatures on audit records (Admin only)",
    dependencies=[Depends(require_tenant_roles(UserRole.ADMIN, TenantRole.TENANT_ADMIN, TenantRole.PLATFORM_ADMIN))],
)
def backfill_audit_chain(
    current_tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records_updated = GovernanceService.backfill_hash_chain(db=db, tenant_id=current_tenant.id)
    return {
        "status": "SUCCESS",
        "tenant_id": current_tenant.id,
        "records_backfilled": records_updated,
    }


@router.delete(
    "/tenants/{tenant_id}/purge",
    summary="Cryptographic shredding & complete cascading purge of all tenant data (Platform Admin only)",
    dependencies=[Depends(require_tenant_roles(UserRole.ADMIN, TenantRole.PLATFORM_ADMIN))],
)
def purge_tenant_data(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GovernanceService.purge_tenant_data(db=db, tenant_id=tenant_id)


@router.get(
    "/archive/export",
    summary="Export complete compliant tenant data archive (Admin only)",
    dependencies=[Depends(require_tenant_roles(UserRole.ADMIN, TenantRole.TENANT_ADMIN, TenantRole.PLATFORM_ADMIN))],
)
def export_tenant_data_archive(
    current_tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GovernanceService.export_tenant_complete_archive(db=db, tenant_id=current_tenant.id)


class TenantOnboardRequest(BaseModel):
    organization_name: str
    slug: str
    industry: Optional[str] = "EDUCATION"
    tier: Optional[str] = "PROFESSIONAL"
    admin_email: Optional[str] = None
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    admin_full_name: Optional[str] = None


@router.post(
    "/onboard",
    summary="Self-service tenant onboarding & resource provisioning",
    status_code=status.HTTP_201_CREATED,
)
def onboard_tenant(
    payload: TenantOnboardRequest,
    db: Session = Depends(get_db),
):
    return GovernanceService.onboard_tenant(
        db=db,
        org_name=payload.organization_name,
        slug=payload.slug,
        industry=payload.industry or "EDUCATION",
        tier=payload.tier or "PROFESSIONAL",
        admin_email=payload.admin_email or "",
        admin_username=payload.admin_username or "",
        admin_password=payload.admin_password or "",
        admin_full_name=payload.admin_full_name or "",
    )


class TenantLifecycleRequest(BaseModel):
    status: str


@router.post(
    "/tenants/{tenant_id}/lifecycle",
    summary="Transition tenant lifecycle state (ACTIVE, SUSPENDED, ARCHIVED)",
    dependencies=[Depends(require_tenant_roles(UserRole.ADMIN, TenantRole.PLATFORM_ADMIN, TenantRole.TENANT_ADMIN))],
)
def transition_tenant_lifecycle(
    tenant_id: int,
    payload: TenantLifecycleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GovernanceService.transition_tenant_lifecycle(
        db=db,
        tenant_id=tenant_id,
        new_status=payload.status,
        actor=current_user.username,
    )


@router.get(
    "/billing/usage",
    summary="Get commercial SaaS usage, tiered quotas, and billing breakdown",
)
def get_billing_usage(
    current_tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GovernanceService.get_billing_usage_summary(db=db, tenant_id=current_tenant.id)
