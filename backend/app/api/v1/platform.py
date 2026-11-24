import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.api.tenant_deps import require_platform_admin
from app.core.security import get_password_hash
from app.models.organization import (
    Organization,
    OrganizationMembership,
    TenantStatus,
    TenantIndustry,
    TenantRole,
)
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.ticket import Ticket, Incident
from app.schemas.platform import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantUsageStats,
    PlatformOverview,
)
from digital_twin.company_templates import (
    INDUSTRY_TEMPLATES,
    get_template_by_industry,
    list_available_templates,
)
from rag.retrieval.retriever import ingest_document_to_rag
from rag.vector_store.chroma_service import get_chroma_store

router = APIRouter(prefix="/platform", tags=["Platform Control Plane"])


@router.get("/templates")
def get_industry_templates(
    current_user: User = Depends(require_platform_admin),
):
    """
    List all predefined industry presets and operational templates.
    """
    return list_available_templates()


@router.get("/overview", response_model=PlatformOverview)
def get_platform_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Get multi-tenant platform fleet summary statistics.
    """
    total_tenants = db.query(Organization).count()
    active_tenants = db.query(Organization).filter(Organization.status == TenantStatus.ACTIVE).count()
    suspended_tenants = db.query(Organization).filter(Organization.status == TenantStatus.SUSPENDED).count()
    total_users = db.query(User).count()
    total_docs = db.query(Document).count()
    total_incidents = db.query(Incident).count()

    total_chunks = 0
    try:
        tenants = db.query(Organization).all()
        for t in tenants:
            cs = get_chroma_store(tenant_id=t.id)
            total_chunks += cs.collection.count()
    except Exception:
        pass

    return PlatformOverview(
        total_tenants=total_tenants,
        active_tenants=active_tenants,
        suspended_tenants=suspended_tenants,
        total_users=total_users,
        total_documents=total_docs,
        total_chunks=total_chunks,
        total_incidents=total_incidents,
    )


@router.get("/tenants", response_model=List[TenantResponse])
def list_tenants(
    industry: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    List all organizations across the platform with optional filters.
    """
    query = db.query(Organization)
    if industry:
        try:
            ind_enum = TenantIndustry[industry.upper()]
            query = query.filter(Organization.industry == ind_enum)
        except KeyError:
            pass
    if status_filter:
        try:
            stat_enum = TenantStatus[status_filter.upper()]
            query = query.filter(Organization.status == stat_enum)
        except KeyError:
            pass
    if search:
        query = query.filter(
            (Organization.name.ilike(f"%{search}%")) | (Organization.slug.ilike(f"%{search}%"))
        )

    return query.order_by(Organization.id.asc()).offset(skip).limit(limit).all()


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Provisions a new organization/company tenant with isolated storage, vector partition, and admin user.
    """
    # 1. Validate slug uniqueness
    existing_org = db.query(Organization).filter(Organization.slug == payload.slug).first()
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant slug '{payload.slug}' already exists. Please choose a unique slug.",
        )

    # 2. Check admin user collision
    existing_user = db.query(User).filter(
        (User.username == payload.admin_username) | (User.email == payload.admin_email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{payload.admin_username}' or email '{payload.admin_email}' already in use.",
        )

    # 3. Resolve template configuration
    ind_key = payload.industry.value if hasattr(payload.industry, "value") else str(payload.industry)
    template = get_template_by_industry(ind_key)
    base_config = dict(template.get("config", {}))
    if payload.config:
        base_config.update(payload.config)

    # 4. Create Organization
    new_org = Organization(
        name=payload.name,
        slug=payload.slug,
        industry=payload.industry,
        status=TenantStatus.ACTIVE,
        config=base_config,
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)

    # 5. Create Tenant Administrator User
    admin_user = User(
        email=payload.admin_email,
        username=payload.admin_username,
        full_name=f"{payload.name} Admin",
        hashed_password=get_password_hash(payload.admin_password),
        role=UserRole.ADMIN,
        tenant_id=new_org.id,
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    # 6. Create Organization Membership
    membership = OrganizationMembership(
        tenant_id=new_org.id,
        user_id=admin_user.id,
        role=TenantRole.TENANT_ADMIN,
        is_active=True,
    )
    db.add(membership)
    db.commit()

    # 7. Provision Sample Industry Documents & RAG Vector Space
    if payload.apply_industry_template and "sample_documents" in template:
        tenant_doc_dir = Path("data/tenants") / str(new_org.id) / "documents"
        for sample in template["sample_documents"]:
            cat_dir = tenant_doc_dir / sample["category"]
            cat_dir.mkdir(parents=True, exist_ok=True)
            file_path = cat_dir / sample["filename"]

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(sample["content"])

            file_size = os.path.getsize(file_path)
            doc_rec = Document(
                title=sample["title"],
                category=sample["category"],
                filename=sample["filename"],
                file_path=str(file_path),
                file_size=file_size,
                mime_type="text/plain",
                uploader_id=admin_user.id,
                tenant_id=new_org.id,
                chunk_count=0,
                meta_info={"source": sample["filename"], "industry": ind_key},
            )
            db.add(doc_rec)
            db.commit()
            db.refresh(doc_rec)

            try:
                ingest_document_to_rag(db=db, document_id=doc_rec.id, tenant_id=new_org.id)
            except Exception:
                pass

    return new_org


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Retrieve specific tenant details.
    """
    org = db.query(Organization).filter(Organization.id == tenant_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant ID {tenant_id} not found.",
        )
    return org


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: int,
    payload: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Update tenant name, operational status, or custom configuration.
    """
    org = db.query(Organization).filter(Organization.id == tenant_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant ID {tenant_id} not found.",
        )

    if payload.name:
        org.name = payload.name
    if payload.status:
        org.status = payload.status
    if payload.config:
        merged = dict(org.config or {})
        merged.update(payload.config)
        org.config = merged

    db.commit()
    db.refresh(org)
    return org


@router.post("/tenants/{tenant_id}/suspend", response_model=TenantResponse)
def suspend_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Immediately suspends a tenant. All user requests from this tenant receive HTTP 403 Forbidden.
    """
    org = db.query(Organization).filter(Organization.id == tenant_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {tenant_id} not found.")

    org.status = TenantStatus.SUSPENDED
    db.commit()
    db.refresh(org)
    return org


@router.post("/tenants/{tenant_id}/activate", response_model=TenantResponse)
def activate_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Reactivates a suspended tenant.
    """
    org = db.query(Organization).filter(Organization.id == tenant_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {tenant_id} not found.")

    org.status = TenantStatus.ACTIVE
    db.commit()
    db.refresh(org)
    return org


@router.get("/tenants/{tenant_id}/usage", response_model=TenantUsageStats)
def get_tenant_usage_stats(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Returns accurate resource consumption and multi-tenant utilization statistics.
    """
    org = db.query(Organization).filter(Organization.id == tenant_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {tenant_id} not found.")

    user_count = db.query(User).filter(User.tenant_id == tenant_id).count()
    documents = db.query(Document).filter(Document.tenant_id == tenant_id).all()
    storage_bytes = sum(d.file_size or 0 for d in documents)
    ticket_count = db.query(Ticket).filter(Ticket.tenant_id == tenant_id).count()
    incident_count = db.query(Incident).filter(Incident.tenant_id == tenant_id).count()

    # Chroma chunk count for this tenant
    vector_chunk_count = 0
    try:
        cs = get_chroma_store(tenant_id=tenant_id)
        vector_chunk_count = cs.collection.count()
    except Exception:
        pass

    categories = (org.config or {}).get("categories", [])

    return TenantUsageStats(
        tenant_id=org.id,
        name=org.name,
        slug=org.slug,
        status=org.status.value if hasattr(org.status, "value") else str(org.status),
        industry=org.industry.value if hasattr(org.industry, "value") else str(org.industry),
        user_count=user_count,
        document_count=len(documents),
        vector_chunk_count=vector_chunk_count,
        ticket_count=ticket_count,
        incident_count=incident_count,
        storage_bytes=storage_bytes,
        categories=categories,
    )

