import io
import time
import pytest
from app.adapters import (
    LocalStorageAdapter,
    LocalChromaAdapter,
    LocalInMemoryCacheBroker,
    AdapterFactory,
    TenantIsolationViolationError,
    ResourceNotFoundError,
    QuotaExceededError,
)


def test_local_storage_adapter_lifecycle_and_crud(tmp_path):
    adapter = LocalStorageAdapter(base_dir=str(tmp_path))
    adapter.connect()

    # Health check
    health = adapter.health_check()
    assert health["status"] == "healthy"
    assert health["adapter"] == "LocalStorageAdapter"

    # Save document
    payload = b"%PDF-1.4 Mock Institutional Syllabus Content"
    file_obj = io.BytesIO(payload)
    res = adapter.save_file(
        tenant_id=1,
        category="academics",
        filename="syllabus_2026.pdf",
        file_obj=file_obj,
    )

    assert res["filename"] == "syllabus_2026.pdf"
    assert res["size_bytes"] == len(payload)
    assert adapter.file_exists(1, res["storage_path"])

    # Read document
    read_data = adapter.read_file(1, res["storage_path"])
    assert read_data == payload

    # Tenant storage usage
    usage = adapter.get_tenant_storage_usage(1)
    assert usage["total_files"] == 1
    assert usage["total_bytes"] == len(payload)

    # Delete document
    deleted = adapter.delete_file(1, res["storage_path"])
    assert deleted is True
    assert not adapter.file_exists(1, res["storage_path"])


def test_local_storage_adapter_security_and_traversal_denial(tmp_path):
    adapter = LocalStorageAdapter(base_dir=str(tmp_path))
    adapter.connect()

    # Attempt saving traversal filename
    with pytest.raises(TenantIsolationViolationError):
        adapter.save_file(
            tenant_id=1,
            category="academics",
            filename="../../etc/passwd.pdf",
            file_obj=io.BytesIO(b"evil"),
        )

    # Attempt cross-tenant read
    saved = adapter.save_file(
        tenant_id=2,
        category="clinical",
        filename="patient_records.pdf",
        file_obj=io.BytesIO(b"confidential patient data"),
    )

    with pytest.raises(TenantIsolationViolationError):
        # Tenant 1 attempts to read Tenant 2 file
        adapter.read_file(tenant_id=1, storage_path=saved["storage_path"])


def test_local_cache_broker_rate_limiting_and_ttl():
    broker = LocalInMemoryCacheBroker(max_keys=100)
    broker.connect()

    # Rate limiting: allow 3 requests per 10 seconds
    res1 = broker.check_rate_limit(tenant_id=1, limit_key="api", max_requests=3, window_seconds=10)
    res2 = broker.check_rate_limit(tenant_id=1, limit_key="api", max_requests=3, window_seconds=10)
    res3 = broker.check_rate_limit(tenant_id=1, limit_key="api", max_requests=3, window_seconds=10)
    res4 = broker.check_rate_limit(tenant_id=1, limit_key="api", max_requests=3, window_seconds=10)

    assert res1["allowed"] is True
    assert res2["allowed"] is True
    assert res3["allowed"] is True
    assert res4["allowed"] is False
    assert res4["remaining"] == 0

    # Rate limit partitioning: Tenant 2 should not be blocked by Tenant 1
    t2_res = broker.check_rate_limit(tenant_id=2, limit_key="api", max_requests=3, window_seconds=10)
    assert t2_res["allowed"] is True

    # Cache TTL
    broker.set(tenant_id=1, key="test_key", value="hello", ttl_seconds=1)
    assert broker.get(tenant_id=1, key="test_key") == "hello"
    time.sleep(1.05)
    assert broker.get(tenant_id=1, key="test_key") is None


def test_local_cache_token_accounting():
    broker = LocalInMemoryCacheBroker()
    broker.set_token_budget(tenant_id=1, budget=1000)

    rec1 = broker.record_token_usage(tenant_id=1, prompt_tokens=400, completion_tokens=100, model_name="gpt-4o")
    assert rec1["total_tokens"] == 500
    assert rec1["is_warning"] is False
    assert rec1["is_exceeded"] is False

    rec2 = broker.record_token_usage(tenant_id=1, prompt_tokens=300, completion_tokens=50, model_name="gpt-4o")
    assert rec2["total_tokens"] == 850
    assert rec2["is_warning"] is True  # 85% > 80%
    assert rec2["is_exceeded"] is False

    rec3 = broker.record_token_usage(tenant_id=1, prompt_tokens=200, completion_tokens=0, model_name="gpt-4o")
    assert rec3["total_tokens"] == 1050
    assert rec3["is_exceeded"] is True

    # Retrieve usage summary
    summary = broker.get_token_usage(tenant_id=1)
    assert summary["total_tokens"] == 1050
    assert summary["request_count"] == 3


def test_adapter_factory():
    storage = AdapterFactory.get_storage()
    vector = AdapterFactory.get_vector()
    cache = AdapterFactory.get_cache()

    assert storage is not None
    assert vector is not None
    assert cache is not None

    health = AdapterFactory.health_check_all()
    assert health["storage"]["status"] in ("healthy", "degraded")
    assert health["vector"]["status"] in ("healthy", "degraded")
    assert health["cache"]["status"] == "healthy"
