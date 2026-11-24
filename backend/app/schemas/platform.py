from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict, field_validator

try:
    import email_validator  # noqa: F401
    from pydantic import EmailStr
except (ImportError, Exception):
    EmailStr = str

from app.models.organization import TenantStatus, TenantIndustry


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Organization display name")
    slug: str = Field(..., min_length=2, max_length=60, pattern="^[a-z0-9-]+$", description="URL-safe unique identifier")
    industry: TenantIndustry = Field(default=TenantIndustry.EDUCATION)
    admin_email: EmailStr
    admin_username: str = Field(..., min_length=3, max_length=50)
    admin_password: str = Field(..., min_length=6)
    config: Optional[Dict[str, Any]] = None
    apply_industry_template: bool = Field(default=True, description="Seed industry default documents and service presets")

    @field_validator("industry", mode="before")
    @classmethod
    def normalize_industry(cls, v):
        if isinstance(v, str):
            upper_v = v.upper().strip()
            try:
                return TenantIndustry[upper_v]
            except KeyError:
                return TenantIndustry(upper_v)
        return v


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[TenantStatus] = None
    config: Optional[Dict[str, Any]] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        if isinstance(v, str):
            upper_v = v.upper().strip()
            try:
                return TenantStatus[upper_v]
            except KeyError:
                return TenantStatus(upper_v)
        return v


class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    industry: str
    status: str
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantUsageStats(BaseModel):
    tenant_id: int
    name: str
    slug: str
    status: str
    industry: str
    user_count: int
    document_count: int
    vector_chunk_count: int
    ticket_count: int
    incident_count: int
    storage_bytes: int
    categories: List[str]


class PlatformOverview(BaseModel):
    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    total_users: int
    total_documents: int
    total_chunks: int
    total_incidents: int
