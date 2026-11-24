import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class TenantStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ONBOARDING = "ONBOARDING"
    ARCHIVED = "ARCHIVED"


class SubscriptionTier(str, enum.Enum):
    STARTER = "STARTER"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


TIER_CONFIGS = {
    SubscriptionTier.STARTER: {
        "tier": "STARTER",
        "storage_quota_bytes": 1073741824,       # 1 GB
        "rate_limit_per_min": 60,                # 60 req/min
        "monthly_token_budget": 500000,          # 500k tokens
        "telemetry_retention_days": 7,           # 7 days
        "vector_isolation": "SHARED_LOGICAL_COLLECTION",
        "max_user_seats": 10,
        "base_monthly_price_usd": 299.0,
        "overage_per_1k_tokens_usd": 0.003,
        "hitl_remediation_enabled": False,
    },
    SubscriptionTier.PROFESSIONAL: {
        "tier": "PROFESSIONAL",
        "storage_quota_bytes": 10737418240,      # 10 GB
        "rate_limit_per_min": 300,               # 300 req/min
        "monthly_token_budget": 5000000,         # 5M tokens
        "telemetry_retention_days": 30,          # 30 days
        "vector_isolation": "DEDICATED_PARTITIONED_COLLECTION",
        "max_user_seats": 50,
        "base_monthly_price_usd": 999.0,
        "overage_per_1k_tokens_usd": 0.002,
        "hitl_remediation_enabled": True,
    },
    SubscriptionTier.ENTERPRISE: {
        "tier": "ENTERPRISE",
        "storage_quota_bytes": 107374182400,     # 100 GB
        "rate_limit_per_min": 2000,              # 2,000 req/min
        "monthly_token_budget": 50000000,        # 50M tokens
        "telemetry_retention_days": 365,         # 365 days
        "vector_isolation": "DEDICATED_ENCRYPTED_CLUSTER",
        "max_user_seats": 1000,
        "base_monthly_price_usd": 3999.0,
        "overage_per_1k_tokens_usd": 0.001,
        "hitl_remediation_enabled": True,
    },
}


class TenantIndustry(str, enum.Enum):
    EDUCATION = "EDUCATION"
    HEALTHCARE = "HEALTHCARE"
    FINANCE = "FINANCE"
    TECHNOLOGY = "TECHNOLOGY"
    MANUFACTURING = "MANUFACTURING"
    LOGISTICS = "LOGISTICS"
    ENTERPRISE = "ENTERPRISE"
    GOVERNMENT = "GOVERNMENT"
    RETAIL = "RETAIL"
    OTHER = "OTHER"


class TenantRole(str, enum.Enum):
    PLATFORM_ADMIN = "PLATFORM_ADMIN"  # Global operator
    TENANT_OWNER = "TENANT_OWNER"      # Company owner
    TENANT_ADMIN = "TENANT_ADMIN"      # Company SRE / IT admin
    TENANT_MEMBER = "TENANT_MEMBER"    # Standard employee / faculty / student
    TENANT_GUEST = "TENANT_GUEST"      # Read-only guest


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    industry = Column(Enum(TenantIndustry), default=TenantIndustry.EDUCATION, nullable=False)
    status = Column(Enum(TenantStatus), default=TenantStatus.ACTIVE, nullable=False)
    config = Column(JSON, default=dict)  # Branding, categories, prompt templates, SRE thresholds
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    memberships = relationship("OrganizationMembership", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization")
    documents = relationship("Document", back_populates="organization")
    conversations = relationship("Conversation", back_populates="organization")
    tickets = relationship("Ticket", back_populates="organization")
    incidents = relationship("Incident", back_populates="organization")


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(Enum(TenantRole), default=TenantRole.TENANT_MEMBER, nullable=False)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", back_populates="memberships")

