import os
from typing import List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "UniMind AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "unimind-super-secret-key-change-in-production-2026"
    OLD_SECRET_KEYS: List[str] = []
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Database
    DATABASE_BACKEND: str = "sqlite"
    DATABASE_URL: str = "sqlite:///./unimind.db"

    # Distributed Infrastructure Adapters (Stage H)
    VECTOR_BACKEND: str = "chroma"
    CACHE_BACKEND: str = "memory"
    STORAGE_BACKEND: str = "local"
    APP_ENV: str = "development"

    # Qdrant Vector Settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # S3 / MinIO Settings
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadminpassword"
    S3_BUCKET_NAME: str = "unimind-documents"
    S3_REGION_NAME: str = "us-east-1"

    # RAG & LLM Settings
    LLM_PROVIDER: str = "openai"  # "openai", "ollama", "claude", "mock"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"

    # Event Bus / Messaging
    EVENT_BUS_BACKEND: str = "memory"  # "memory", "redis"

    # Enterprise Governance & Zero-Trust Security
    AUTH_ENFORCE_STRICT: bool = False
    RATE_LIMIT_PER_MINUTE: int = 120

    # AegisOps ML Settings
    ANOMALY_THRESHOLD: float = 0.70
    ISOLATION_FOREST_CONTAMINATION: float = 0.05

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_security(self):
        env_lower = (self.ENVIRONMENT or "").lower()
        if env_lower in ("production", "staging"):
            if self.SECRET_KEY == "unimind-super-secret-key-change-in-production-2026":
                raise ValueError(
                    "CRITICAL SECURITY HAZARD: Default development SECRET_KEY detected in production/staging environment! "
                    "You must provide a secure cryptographic SECRET_KEY via environment variable."
                )
            if len(self.SECRET_KEY) < 32:
                raise ValueError("Production SECRET_KEY must be at least 32 characters long.")
            if self.DEBUG:
                self.DEBUG = False
            self.AUTH_ENFORCE_STRICT = True
        return self

    def masked_dict(self) -> dict:
        """Returns configuration dictionary with all secrets and credentials masked for secure logging."""
        raw = self.model_dump()
        sensitive_keys = {
            "SECRET_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
            "S3_SECRET_KEY", "S3_ACCESS_KEY", "QDRANT_API_KEY",
        }
        for k in sensitive_keys:
            if k in raw and raw[k]:
                val = str(raw[k])
                if len(val) > 8:
                    raw[k] = val[:3] + "..." + val[-3:]
                else:
                    raw[k] = "***"
        return raw

    def __repr__(self) -> str:
        masked = self.masked_dict()
        return f"Settings({', '.join(f'{k}={v}' for k, v in masked.items())})"


settings = Settings()
