"""
Unit and Integration Test Suite for Stage H Distributed Infrastructure Adapters.
Validates Database (Postgres/SQLite), Vector (Qdrant), Cache (Redis), and Storage (S3/MinIO) adapters
under strict multi-tenant isolation, dimension checks, path traversal denial, and safe fallback.
"""
import io
import os
import pytest
from app.adapters.exceptions import (
    AdapterException,
    TenantIsolationViolationError,
    QuotaExceededError,
)
from app.adapters.database import SQLiteDatabaseAdapter, PostgreSQLDatabaseAdapter
from app.adapters.vector import QdrantVectorAdapter
from app.adapters.cache import RedisCacheBrokerAdapter
from app.adapters.storage import S3StorageAdapter
from app.adapters.factory import AdapterFactory


def test_stage_h_database_adapters():
    # 1. Test SQLite Database Adapter
    sqlite_adapter = SQLiteDatabaseAdapter()
    sqlite_adapter.connect()
    hc = sqlite_adapter.health_check()
    assert hc["status"] == "healthy"
    assert hc["dialect"] == "sqlite"

    tables = sqlite_adapter.get_table_names()
    assert len(tables) > 0
    assert "users" in tables

    raw_res = sqlite_adapter.execute_raw("SELECT count(*) as cnt FROM users;")
    assert len(raw_res) == 1
    assert raw_res[0]["cnt"] >= 1
    sqlite_adapter.disconnect()

    # 2. Test PostgreSQL Database Adapter contract & pool configuration
    pg_adapter = PostgreSQLDatabaseAdapter("postgresql://unimind_user:unimind_password@localhost:5432/unimind_db")
    assert pg_adapter.database_url.startswith("postgresql://")
    # Health check on offline PG container reports unhealthy cleanly without crashing
    hc_pg = pg_adapter.health_check()
    assert hc_pg["status"] == "unhealthy"
    assert hc_pg["dialect"] == "postgresql"
    assert "error" in hc_pg


def test_stage_h_qdrant_vector_adapter_isolation_and_crud():
    qdrant = QdrantVectorAdapter(embedding_dim=384)
    qdrant.connect()

    # 1. Health check
    hc = qdrant.health_check()
    assert hc["status"] == "healthy"
    assert "Qdrant" in hc["adapter"]

    # 2. Tenant isolation check: non-positive tenant ID rejected
    with pytest.raises(TenantIsolationViolationError):
        qdrant.upsert_chunks(tenant_id=0, chunks=[{"text": "invalid", "chunk_id": "0_1"}])

    with pytest.raises(TenantIsolationViolationError):
        qdrant.query_similar(tenant_id=-5, query_text="test")

    # 3. Vector dimension mismatch validation
    bad_chunks = [{"chunk_id": "t1_c1", "text": "policy", "embedding": [0.1, 0.2]}] # Only 2 dims
    with pytest.raises(AdapterException) as exc_info:
        qdrant.upsert_chunks(tenant_id=1, chunks=bad_chunks)
    assert "dimension mismatch" in str(exc_info.value).lower()

    # 4. Valid upsert for Tenant 1
    valid_chunks_t1 = [
        {"chunk_id": "t1_c1", "text": "Campus curfew is 10 PM on weekdays.", "doc_id": 101, "category": "hostel"},
        {"chunk_id": "t1_c2", "text": "Library open until midnight.", "doc_id": 102, "category": "library"},
    ]
    upserted_t1 = qdrant.upsert_chunks(tenant_id=1, chunks=valid_chunks_t1)
    assert upserted_t1 == 2

    # 5. Valid upsert for Tenant 2 (Healthcare)
    valid_chunks_t2 = [
        {"chunk_id": "t2_c1", "text": "ICU oxygen threshold is 92 percent.", "doc_id": 201, "category": "medical"},
    ]
    upserted_t2 = qdrant.upsert_chunks(tenant_id=2, chunks=valid_chunks_t2)
    assert upserted_t2 == 1

    # 6. Cross-Tenant Query Isolation: Tenant 1 cannot find Tenant 2 chunks
    t1_results = qdrant.query_similar(tenant_id=1, query_text="oxygen threshold")
    assert all("ICU" not in r["text"] for r in t1_results)

    t2_results = qdrant.query_similar(tenant_id=2, query_text="oxygen threshold")
    assert any("ICU" in r["text"] for r in t2_results)

    # 7. Delete document chunks
    del_count = qdrant.delete_document_chunks(tenant_id=1, doc_id=101)
    assert del_count >= 1

    # 8. Collection stats
    stats_t1 = qdrant.get_collection_stats(tenant_id=1)
    assert stats_t1["total_chunks"] == 1


def test_stage_h_redis_cache_adapter_isolation_and_rate_limiting():
    redis_adapter = RedisCacheBrokerAdapter()
    redis_adapter.connect()

    # 1. Health check
    hc = redis_adapter.health_check()
    assert hc["status"] == "healthy"
    assert "Redis" in hc["adapter"]

    # 2. Tenant isolation in caching
    redis_adapter.set(tenant_id=1, key="user_pref", value={"theme": "dark"})
    redis_adapter.set(tenant_id=2, key="user_pref", value={"theme": "light"})

    val_t1 = redis_adapter.get(tenant_id=1, key="user_pref")
    val_t2 = redis_adapter.get(tenant_id=2, key="user_pref")
    assert val_t1["theme"] == "dark"
    assert val_t2["theme"] == "light"

    # Cross-tenant key isolation: non-positive tenant ID rejected
    with pytest.raises(TenantIsolationViolationError):
        redis_adapter.get(tenant_id=0, key="user_pref")

    # 3. Rate limiting check
    tid = 99
    # Consume 3 requests
    for _ in range(3):
        res = redis_adapter.check_rate_limit(tenant_id=tid, limit_key="api_limit", max_requests=3, window_seconds=60)
        assert res["allowed"] is True

    # 4th request must be blocked
    res_block = redis_adapter.check_rate_limit(tenant_id=tid, limit_key="api_limit", max_requests=3, window_seconds=60)
    assert res_block["allowed"] is False
    assert res_block["remaining"] == 0
    assert res_block["reset_seconds"] > 0

    # 4. Token accounting
    rec = redis_adapter.record_token_usage(tenant_id=1, prompt_tokens=150, completion_tokens=75, model_name="gpt-4o-mini")
    assert rec["total_tokens"] >= 225
    usage = redis_adapter.get_token_usage(tenant_id=1)
    assert usage["total_tokens"] >= 225

    # 5. Delete key
    redis_adapter.delete(tenant_id=1, key="user_pref")
    assert redis_adapter.get(tenant_id=1, key="user_pref") is None


def test_stage_h_s3_storage_adapter_security_and_traversal():
    s3 = S3StorageAdapter(bucket_name="unimind-test-bucket")
    s3.connect()

    # 1. Health check
    hc = s3.health_check()
    assert hc["status"] == "healthy"
    assert "S3" in hc["adapter"]

    # 2. Path traversal denial
    with pytest.raises(TenantIsolationViolationError):
        s3.save_file(
            tenant_id=1,
            category="general",
            filename="../../etc/passwd.txt",
            file_obj=io.BytesIO(b"malicious"),
        )

    # Non-positive tenant ID rejected
    with pytest.raises(TenantIsolationViolationError):
        s3.save_file(
            tenant_id=0,
            category="general",
            filename="valid.txt",
            file_obj=io.BytesIO(b"test"),
        )

    # 3. Save file for Tenant 1
    content_t1 = b"Official University Attendance Regulation 2026."
    save_res = s3.save_file(
        tenant_id=1,
        category="academics",
        filename="attendance_policy_2026.txt",
        file_obj=io.BytesIO(content_t1),
        content_type="text/plain",
    )
    assert save_res["size_bytes"] == len(content_t1)
    assert save_res["sha256"] is not None
    storage_path = save_res["storage_path"]

    # 4. Read file & integrity
    read_bytes = s3.read_file(tenant_id=1, storage_path=storage_path)
    assert read_bytes == content_t1

    # 5. Cross-tenant read denial
    with pytest.raises(TenantIsolationViolationError):
        s3.read_file(tenant_id=2, storage_path=storage_path)

    # 6. File exists and usage
    assert s3.file_exists(tenant_id=1, storage_path=storage_path) is True
    assert s3.file_exists(tenant_id=2, storage_path=storage_path) is False

    usage_t1 = s3.get_tenant_storage_usage(tenant_id=1)
    assert usage_t1["total_bytes"] >= len(content_t1)
    assert usage_t1["total_files"] >= 1

    # 7. Delete file
    deleted = s3.delete_file(tenant_id=1, storage_path=storage_path)
    assert deleted is True
    assert s3.file_exists(tenant_id=1, storage_path=storage_path) is False


def test_stage_h_adapter_factory_backend_switching(monkeypatch):
    # Test dynamic switching to Qdrant, Redis, S3, and Postgres
    monkeypatch.setenv("VECTOR_BACKEND", "qdrant")
    monkeypatch.setenv("CACHE_BACKEND", "redis")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")

    # Clear cached singletons to test factory instantiation
    AdapterFactory._vector_adapter = None
    AdapterFactory._cache_broker = None
    AdapterFactory._storage_adapter = None
    AdapterFactory._database_adapter = None

    v = AdapterFactory.get_vector()
    c = AdapterFactory.get_cache()
    s = AdapterFactory.get_storage()
    d = AdapterFactory.get_database()

    assert v.__class__.__name__ == "QdrantVectorAdapter"
    assert c.__class__.__name__ == "RedisCacheBrokerAdapter"
    assert s.__class__.__name__ == "S3StorageAdapter"
    assert d.__class__.__name__ == "PostgreSQLDatabaseAdapter"

    # Reset back to local monolith defaults
    monkeypatch.setenv("VECTOR_BACKEND", "chroma")
    monkeypatch.setenv("CACHE_BACKEND", "memory")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("DATABASE_BACKEND", "sqlite")

    AdapterFactory._vector_adapter = None
    AdapterFactory._cache_broker = None
    AdapterFactory._storage_adapter = None
    AdapterFactory._database_adapter = None

    v_default = AdapterFactory.get_vector()
    c_default = AdapterFactory.get_cache()
    s_default = AdapterFactory.get_storage()
    d_default = AdapterFactory.get_database()

    assert v_default.__class__.__name__ == "LocalChromaAdapter"
    assert c_default.__class__.__name__ == "LocalInMemoryCacheBroker"
    assert s_default.__class__.__name__ == "LocalStorageAdapter"
    assert d_default.__class__.__name__ == "SQLiteDatabaseAdapter"
