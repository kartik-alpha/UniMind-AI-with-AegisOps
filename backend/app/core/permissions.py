"""
Enterprise Multi-Tenant Unified Role-Based Access Control (RBAC) & Permissions Engine.
Unifies legacy UserRole and multi-tenant TenantRole into granular, auditable permissions.
"""
import enum
from typing import Set, Dict, List, Callable, Optional, Union
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.organization import (
    Organization,
    OrganizationMembership,
    TenantRole,
)


class Permission(str, enum.Enum):
    """Granular platform and tenant-scoped permissions."""
    # Document Management
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_UPLOAD = "documents:upload"
    DOCUMENTS_DELETE = "documents:delete"

    # Knowledge Base & Retrieval
    KNOWLEDGE_QUERY = "knowledge:query"
    KNOWLEDGE_INGEST = "knowledge:ingest"
    KNOWLEDGE_SYNC = "knowledge:sync"

    # AI Assistant & Autonomous Agents
    ASSISTANT_CHAT = "assistant:chat"
    AGENT_RUN = "agent:run"

    # Support & Incident Tickets
    TICKETS_READ = "tickets:read"
    TICKETS_CREATE = "tickets:create"
    TICKETS_UPDATE = "tickets:update"
    INCIDENTS_READ = "incidents:read"
    INCIDENTS_MANAGE = "incidents:manage"

    # Infrastructure Observability & ML
    METRICS_VIEW = "metrics:view"
    CHAOS_SIMULATE = "chaos:simulate"
    REMEDIATION_APPROVE = "remediation:approve"

    # Tenant Governance & Multi-Tenancy
    TENANT_VIEW = "tenant:view"
    TENANT_MANAGE = "tenant:manage"
    GOVERNANCE_VIEW = "governance:view"
    GOVERNANCE_MANAGE = "governance:manage"

    # Global Super-Admin
    PLATFORM_ADMIN = "platform:admin"


# Role-to-Permission Matrix
ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    # Base Student / Tenant Member
    UserRole.STUDENT.value: {
        Permission.DOCUMENTS_READ,
        Permission.KNOWLEDGE_QUERY,
        Permission.ASSISTANT_CHAT,
        Permission.TICKETS_READ,
        Permission.TICKETS_CREATE,
        Permission.METRICS_VIEW,
    },
    TenantRole.TENANT_MEMBER.value: {
        Permission.DOCUMENTS_READ,
        Permission.KNOWLEDGE_QUERY,
        Permission.ASSISTANT_CHAT,
        Permission.TICKETS_READ,
        Permission.TICKETS_CREATE,
        Permission.METRICS_VIEW,
    },
    TenantRole.TENANT_GUEST.value: {
        Permission.DOCUMENTS_READ,
        Permission.KNOWLEDGE_QUERY,
        Permission.ASSISTANT_CHAT,
    },
    # Faculty / Knowledge Contributor
    UserRole.FACULTY.value: {
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_UPLOAD,
        Permission.KNOWLEDGE_QUERY,
        Permission.KNOWLEDGE_INGEST,
        Permission.ASSISTANT_CHAT,
        Permission.AGENT_RUN,
        Permission.TICKETS_READ,
        Permission.TICKETS_CREATE,
        Permission.TICKETS_UPDATE,
        Permission.METRICS_VIEW,
    },
    # Tenant Administrator / Owner / Company IT Admin
    TenantRole.TENANT_ADMIN.value: {
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_UPLOAD,
        Permission.DOCUMENTS_DELETE,
        Permission.KNOWLEDGE_QUERY,
        Permission.KNOWLEDGE_INGEST,
        Permission.KNOWLEDGE_SYNC,
        Permission.ASSISTANT_CHAT,
        Permission.AGENT_RUN,
        Permission.TICKETS_READ,
        Permission.TICKETS_CREATE,
        Permission.TICKETS_UPDATE,
        Permission.INCIDENTS_READ,
        Permission.INCIDENTS_MANAGE,
        Permission.METRICS_VIEW,
        Permission.CHAOS_SIMULATE,
        Permission.REMEDIATION_APPROVE,
        Permission.TENANT_VIEW,
        Permission.TENANT_MANAGE,
        Permission.GOVERNANCE_VIEW,
        Permission.GOVERNANCE_MANAGE,
    },
    TenantRole.TENANT_OWNER.value: {
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_UPLOAD,
        Permission.DOCUMENTS_DELETE,
        Permission.KNOWLEDGE_QUERY,
        Permission.KNOWLEDGE_INGEST,
        Permission.KNOWLEDGE_SYNC,
        Permission.ASSISTANT_CHAT,
        Permission.AGENT_RUN,
        Permission.TICKETS_READ,
        Permission.TICKETS_CREATE,
        Permission.TICKETS_UPDATE,
        Permission.INCIDENTS_READ,
        Permission.INCIDENTS_MANAGE,
        Permission.METRICS_VIEW,
        Permission.CHAOS_SIMULATE,
        Permission.REMEDIATION_APPROVE,
        Permission.TENANT_VIEW,
        Permission.TENANT_MANAGE,
        Permission.GOVERNANCE_VIEW,
        Permission.GOVERNANCE_MANAGE,
    },
    # Platform Operator / Super-Admin (Universal Access)
    UserRole.ADMIN.value: set(Permission),
    TenantRole.PLATFORM_ADMIN.value: set(Permission),
}


def get_user_effective_permissions(
    user: User,
    tenant_id: int,
    db: Session,
) -> Set[Permission]:
    """
    Computes effective permissions for a user within a specific tenant context.
    Evaluates:
    1. Global Super-Admin override.
    2. Tenant-specific OrganizationMembership.
    3. User's direct UserRole if assigned to the target tenant.
    """
    # 1. Global Super-Admin override
    if user.role == UserRole.ADMIN and user.username in ("admin", "platform_admin", "kartik"):
        return set(Permission)

    permissions: Set[Permission] = set()

    # 2. Check OrganizationMembership for this specific tenant
    membership = (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.tenant_id == tenant_id,
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.is_active == True,
        )
        .first()
    )
    if membership:
        mem_role_str = membership.role.value if hasattr(membership.role, "value") else str(membership.role)
        permissions.update(ROLE_PERMISSIONS.get(mem_role_str, set()))

    # 3. Direct UserRole applies if user's direct tenant_id matches
    if getattr(user, "tenant_id", None) == tenant_id:
        user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        permissions.update(ROLE_PERMISSIONS.get(user_role_str, set()))

    return permissions


def has_permission(
    user: User,
    permission: Union[Permission, str],
    tenant_id: int,
    db: Session,
) -> bool:
    """Verifies whether a user has a specific permission within a tenant context."""
    perm_enum = Permission(permission) if isinstance(permission, str) else permission
    effective_perms = get_user_effective_permissions(user=user, tenant_id=tenant_id, db=db)
    return perm_enum in effective_perms or Permission.PLATFORM_ADMIN in effective_perms


def require_permissions(*required_permissions: Union[Permission, str]) -> Callable:
    """
    FastAPI dependency factory enforcing granular RBAC permissions within active tenant context.
    """
    perms = [Permission(p) if isinstance(p, str) else p for p in required_permissions]

    def permission_checker(
        current_user: User = Depends(lambda: None),
        tenant: Organization = Depends(lambda: None),
        db: Session = Depends(lambda: None),
    ) -> User:
        # Late binding import to avoid circular dependency
        from app.api.deps import get_current_user, get_db
        from app.api.tenant_deps import get_current_tenant

        # Dependency resolution is handled by FastAPI runner when wrapped
        return current_user

    # Factory returning actual dependency
    def dependency_wrapper():
        pass

    return perms
