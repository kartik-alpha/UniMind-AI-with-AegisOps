"""
Adapter Factory & Dependency Injection Registry (Stage H Hybrid Architecture).
Resolves and manages lifecycle of concrete adapters based on application configuration.
Supports SQLite/Postgres, Chroma/Qdrant, In-Memory/Redis, and Local/S3 adapters.
"""
import os
from typing import Dict, Any, Optional

from app.core.config import settings
from app.adapters.storage import StorageAdapter, LocalStorageAdapter, S3StorageAdapter
from app.adapters.vector import VectorDatabaseAdapter, LocalChromaAdapter, QdrantVectorAdapter
from app.adapters.cache import CacheBrokerAdapter, LocalInMemoryCacheBroker, RedisCacheBrokerAdapter
from app.adapters.database import DatabaseAdapter, SQLiteDatabaseAdapter, PostgreSQLDatabaseAdapter


class AdapterFactory:
    """
    Central factory registry ensuring singletons and lifecycle management for Stage G & H adapters.
    """

    _storage_adapter: Optional[StorageAdapter] = None
    _vector_adapter: Optional[VectorDatabaseAdapter] = None
    _cache_broker: Optional[CacheBrokerAdapter] = None
    _database_adapter: Optional[DatabaseAdapter] = None

    @classmethod
    def get_storage(cls) -> StorageAdapter:
        if cls._storage_adapter is None:
            backend = os.getenv("STORAGE_BACKEND", getattr(settings, "STORAGE_BACKEND", "local")).lower()
            if backend in ("s3", "minio"):
                cls._storage_adapter = S3StorageAdapter()
            else:
                cls._storage_adapter = LocalStorageAdapter()
            cls._storage_adapter.connect()
        return cls._storage_adapter

    @classmethod
    def get_vector(cls) -> VectorDatabaseAdapter:
        if cls._vector_adapter is None:
            backend = os.getenv("VECTOR_BACKEND", getattr(settings, "VECTOR_BACKEND", "chroma")).lower()
            if backend == "qdrant":
                cls._vector_adapter = QdrantVectorAdapter()
            else:
                cls._vector_adapter = LocalChromaAdapter()
            cls._vector_adapter.connect()
        return cls._vector_adapter

    @classmethod
    def get_cache(cls) -> CacheBrokerAdapter:
        if cls._cache_broker is None:
            backend = os.getenv("CACHE_BACKEND", getattr(settings, "CACHE_BACKEND", "memory")).lower()
            if backend == "redis":
                cls._cache_broker = RedisCacheBrokerAdapter()
            else:
                cls._cache_broker = LocalInMemoryCacheBroker()
            cls._cache_broker.connect()
        return cls._cache_broker

    @classmethod
    def get_database(cls) -> DatabaseAdapter:
        if cls._database_adapter is None:
            backend = os.getenv("DATABASE_BACKEND", getattr(settings, "DATABASE_BACKEND", "sqlite")).lower()
            if backend in ("postgres", "postgresql"):
                cls._database_adapter = PostgreSQLDatabaseAdapter()
            else:
                cls._database_adapter = SQLiteDatabaseAdapter()
            cls._database_adapter.connect()
        return cls._database_adapter

    @classmethod
    def initialize_all(cls) -> Dict[str, Any]:
        """Eager initialization during application lifespan startup."""
        s = cls.get_storage()
        v = cls.get_vector()
        c = cls.get_cache()
        d = cls.get_database()
        return {
            "storage": s.health_check(),
            "vector": v.health_check(),
            "cache": c.health_check(),
            "database": d.health_check(),
        }

    @classmethod
    def shutdown_all(cls) -> None:
        """Graceful shutdown during application lifespan shutdown."""
        if cls._storage_adapter:
            cls._storage_adapter.disconnect()
            cls._storage_adapter = None
        if cls._vector_adapter:
            cls._vector_adapter.disconnect()
            cls._vector_adapter = None
        if cls._cache_broker:
            cls._cache_broker.disconnect()
            cls._cache_broker = None
        if cls._database_adapter:
            cls._database_adapter.disconnect()
            cls._database_adapter = None

    @classmethod
    def health_check_all(cls) -> Dict[str, Any]:
        return {
            "storage": cls.get_storage().health_check(),
            "vector": cls.get_vector().health_check(),
            "cache": cls.get_cache().health_check(),
            "database": cls.get_database().health_check(),
        }
