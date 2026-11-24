"""
Hexagonal Architecture Adapters Package (Stage G & Stage H).
Provides pluggable adapters for Storage (Local / S3), Vector (Chroma / Qdrant),
Cache (In-Memory / Redis), and Relational Database (SQLite / PostgreSQL).
"""
from app.adapters.exceptions import (
    AdapterException,
    TenantIsolationViolationError,
    ResourceNotFoundError,
    QuotaExceededError,
    ConnectionTimeoutError,
    AdapterConfigurationError,
)
from app.adapters.storage import StorageAdapter, LocalStorageAdapter, S3StorageAdapter
from app.adapters.vector import VectorDatabaseAdapter, LocalChromaAdapter, QdrantVectorAdapter
from app.adapters.cache import CacheBrokerAdapter, LocalInMemoryCacheBroker, RedisCacheBrokerAdapter
from app.adapters.database import DatabaseAdapter, SQLiteDatabaseAdapter, PostgreSQLDatabaseAdapter
from app.adapters.factory import AdapterFactory

__all__ = [
    "AdapterException",
    "TenantIsolationViolationError",
    "ResourceNotFoundError",
    "QuotaExceededError",
    "ConnectionTimeoutError",
    "AdapterConfigurationError",
    "StorageAdapter",
    "LocalStorageAdapter",
    "S3StorageAdapter",
    "VectorDatabaseAdapter",
    "LocalChromaAdapter",
    "QdrantVectorAdapter",
    "CacheBrokerAdapter",
    "LocalInMemoryCacheBroker",
    "RedisCacheBrokerAdapter",
    "DatabaseAdapter",
    "SQLiteDatabaseAdapter",
    "PostgreSQLDatabaseAdapter",
    "AdapterFactory",
]
