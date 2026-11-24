# Stage G0 — Interface Contracts & Adapter Specifications
**Platform:** UniMind AI + AegisOps Enterprise Platform  
**Target Milestone:** Stage G (Phase G0: Architecture & Interface Contracts Only)  
**Contract Version:** 1.0.0-draft  
**Design Phase Status:** **COMPLETE — ARCHITECTURE ONLY (ZERO SOURCE CODE MODIFIED)**

---

## 1. Common Exception Hierarchy

All adapters conform to a unified exception hierarchy to prevent leakage of backend-specific error types (e.g., `sqlite3.OperationalError`, `botocore.exceptions.ClientError`, `redis.exceptions.ConnectionError`) into core application services.

```python
class AdapterException(Exception):
    """Base exception for all Stage G adapter failures."""
    def __init__(self, message: str, tenant_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.tenant_id = tenant_id
        self.details = details or {}


class TenantIsolationViolationError(AdapterException):
    """Raised when an operation attempts to access, mutate, or leak another tenant's resources."""
    pass


class ResourceNotFoundError(AdapterException):
    """Raised when a requested file, collection, or cache key does not exist."""
    pass


class QuotaExceededError(AdapterException):
    """Raised when a tenant breaches their configured storage, rate, or token quota."""
    pass


class ConnectionTimeoutError(AdapterException):
    """Raised when connection to underlying storage, vector database, or broker times out."""
    pass


class AdapterConfigurationError(AdapterException):
    """Raised when adapter parameters, directories, or credentials are misconfigured."""
    pass
```

---

## 2. StorageAdapter Interface Specification

### 2.1 Responsibilities & Boundaries
- **Responsibility:** Persistent storage, retrieval, deletion, and metadata inspection of document payloads (PDFs, text files, exported logs).
- **Boundary:** Manages binary files and disk paths. Does **not** manage relational document metadata (title, author, chunk count), which remains the sole responsibility of SQLAlchemy `Document` models in `unimind.db`.
- **Tenant Isolation:** Every operation requires an explicit `tenant_id: int`. Files are strictly stored under tenant-segregated namespaces. Cross-tenant reads or path traversals raise `TenantIsolationViolationError`.

### 2.2 Python Interface Definition
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, BinaryIO
from pathlib import Path


class StorageAdapter(ABC):
    """
    Abstract interface for multi-tenant document payload storage.
    Implementations: LocalStorageAdapter (default), S3StorageAdapter (future).
    """

    @abstractmethod
    def connect(self) -> None:
        """Initialize connection, verify permissions, and ensure root namespaces exist."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Release open file handles or connection pools."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return adapter status, available disk space, and latency metrics."""
        pass

    @abstractmethod
    def save_file(
        self,
        tenant_id: int,
        category: str,
        filename: str,
        file_obj: BinaryIO,
        content_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """
        Persist a document payload under the tenant's namespace.
        
        Args:
            tenant_id: Authenticated organization ID (mandatory).
            category: Document classification (e.g., 'policies', 'examinations').
            filename: Raw original filename (must be sanitized by adapter).
            file_obj: Readable binary stream.
            content_type: MIME type.
            
        Returns:
            Dict containing:
                - storage_path: Canonical internal storage identifier.
                - size_bytes: File size in bytes.
                - sha256_hash: Cryptographic integrity hash.
                
        Raises:
            TenantIsolationViolationError: If tenant_id <= 0 or path traversal detected.
            QuotaExceededError: If tenant storage quota is exceeded.
            AdapterException: On I/O or filesystem failure.
        """
        pass

    @abstractmethod
    def read_file(self, tenant_id: int, storage_path: str) -> bytes:
        """
        Read the entire binary payload of a stored document.
        
        Raises:
            TenantIsolationViolationError: If storage_path belongs to another tenant.
            ResourceNotFoundError: If file does not exist.
        """
        pass

    @abstractmethod
    def stream_file(self, tenant_id: int, storage_path: str, chunk_size: int = 65536) -> BinaryIO:
        """
        Return a binary stream for large file streaming downloads.
        """
        pass

    @abstractmethod
    def delete_file(self, tenant_id: int, storage_path: str) -> bool:
        """
        Idempotently delete a stored file.
        
        Returns:
            True if deleted, False if file did not exist.
        """
        pass

    @abstractmethod
    def file_exists(self, tenant_id: int, storage_path: str) -> bool:
        """Check whether a file exists in the tenant's namespace."""
        pass

    @abstractmethod
    def get_tenant_storage_usage(self, tenant_id: int) -> Dict[str, Any]:
        """
        Calculate total storage consumption for a given tenant.
        
        Returns:
            Dict containing:
                - total_bytes: Total bytes consumed.
                - total_files: File count.
        """
        pass
```

### 2.3 Concrete Local Implementation Contract (`LocalStorageAdapter`)
- **Default Path:** `data/tenants/{tenant_id}/documents/{category}/`
- **Path Sanitization:** Enforces `Path(filename).name` and validates that the resolved absolute path starts with `BASE_DATA_DIR.resolve()`.
- **Compatibility:** Exact 100% replacement for functions in `backend/app/services/document_service.py`.

---

## 3. VectorDatabaseAdapter Interface Specification

### 3.1 Responsibilities & Boundaries
- **Responsibility:** Indexing, updating, deleting, and similarity searching of document chunk embeddings.
- **Boundary:** Operates strictly on dense embeddings and chunk metadata. Does **not** perform BM25 sparse indexing (managed separately in `rag/retrieval/bm25.py`) or text generation.
- **Tenant Isolation:** Every collection or query must be scoped by `tenant_id: int`. Collections are either physical partitions (`tenant_{id}_kb`) or logical partitions enforcing strict metadata filtering (`{"tenant_id": {"$eq": tid}}`).

### 3.2 Python Interface Definition
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class VectorDatabaseAdapter(ABC):
    """
    Abstract interface for multi-tenant vector similarity storage and retrieval.
    Implementations: LocalChromaAdapter (default), QdrantVectorAdapter (future), PgVectorAdapter (future).
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to vector database engine."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Flush in-memory indexes and close client connections."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Verify vector database connectivity and return total collection counts."""
        pass

    @abstractmethod
    def upsert_chunks(
        self,
        tenant_id: int,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> int:
        """
        Upsert a batch of document chunks and their dense embeddings.
        
        Args:
            tenant_id: Authenticated tenant ID.
            chunks: List of dicts with 'chunk_id', 'text', 'metadata', 'doc_id'.
            embeddings: Corresponding dense float vectors.
            
        Returns:
            Count of successfully upserted chunks.
            
        Raises:
            TenantIsolationViolationError: If chunks contain conflicting tenant_ids.
            AdapterException: On vector storage failure.
        """
        pass

    @abstractmethod
    def query_similar(
        self,
        tenant_id: int,
        query_embedding: List[float],
        top_k: int = 4,
        category_filter: Optional[str] = None,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform nearest-neighbor search strictly within the tenant's vector partition.
        
        Returns:
            List of retrieved chunks with:
                - chunk_id: str
                - text: str
                - metadata: dict (guaranteed tenant_id == requested tenant_id)
                - similarity_score: float (normalized 0.0 to 1.0)
                
        Raises:
            TenantIsolationViolationError: If cross-tenant query attempted.
        """
        pass

    @abstractmethod
    def delete_document_chunks(self, tenant_id: int, doc_id: int) -> int:
        """
        Delete all vector chunks associated with a specific document.
        
        Returns:
            Count of deleted chunks.
        """
        pass

    @abstractmethod
    def delete_tenant_collection(self, tenant_id: int) -> bool:
        """Purge an entire tenant's vector collection upon tenant de-provisioning."""
        pass

    @abstractmethod
    def get_collection_stats(self, tenant_id: int) -> Dict[str, Any]:
        """
        Return collection statistics for the tenant:
            - collection_name: str
            - total_chunks: int
            - vector_dimension: int (e.g. 384)
        """
        pass
```

### 3.3 Concrete Local Implementation Contract (`LocalChromaAdapter`)
- **Backend:** Embedded ChromaDB `PersistentClient` targeting `chroma_db/`.
- **Partitioning Strategy:**
  - `tenant_id == 1`: Uses collection name `"university_knowledge_base"` (preserving Stage F legacy).
  - `tenant_id > 1`: Uses collection name `f"tenant_{tenant_id}_kb"`.
- **Defense-in-Depth Filter:** Always appends `where={"tenant_id": {"$eq": tenant_id}}` to every query.

---

## 4. CacheBrokerAdapter Interface Specification

### 4.1 Responsibilities & Boundaries
- **Responsibility:** Ephemeral key-value caching, atomic token-bucket rate limiting, and in-process asynchronous task dispatch.
- **Boundary:** Transient data only. Does **not** store durable relational records or uncommitted audit logs.
- **Tenant Isolation:** Keys are automatically prefixed with `tenant:{tenant_id}:`. Cross-tenant key reads are strictly disallowed.

### 4.2 Python Interface Definition
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class CacheBrokerAdapter(ABC):
    """
    Abstract interface for tenant-isolated caching, rate limiting, and pub/sub task dispatch.
    Implementations: LocalInMemoryCacheBroker (default), RedisCacheBrokerAdapter (future).
    """

    @abstractmethod
    def connect(self) -> None:
        """Initialize cache store, memory pools, and background cleanup tasks."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Stop background tasks and clear in-memory buffers."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return cache health, item count, memory usage, and hit ratio."""
        pass

    @abstractmethod
    def get(self, tenant_id: int, key: str) -> Optional[Any]:
        """
        Retrieve a cached value for a tenant.
        Returns None if key has expired or does not exist.
        """
        pass

    @abstractmethod
    def set(
        self,
        tenant_id: int,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = 300
    ) -> bool:
        """
        Set a tenant-scoped cache value with time-to-live.
        """
        pass

    @abstractmethod
    def delete(self, tenant_id: int, key: str) -> bool:
        """Delete a tenant-scoped cache key."""
        pass

    @abstractmethod
    def check_rate_limit(
        self,
        tenant_id: int,
        limit_key: str,
        max_requests: int,
        window_seconds: int
    ) -> Dict[str, Any]:
        """
        Atomic token-bucket rate limiting check.
        
        Returns:
            Dict containing:
                - allowed: bool (True if request is permitted)
                - remaining: int (remaining tokens in current window)
                - reset_seconds: int (seconds until quota resets)
        """
        pass

    @abstractmethod
    def publish_event(self, tenant_id: int, topic: str, payload: Dict[str, Any]) -> int:
        """Publish an event to a tenant-scoped message channel."""
        pass

    @abstractmethod
    async def subscribe_event(self, tenant_id: int, topic: str):
        """Async generator yielding events on a tenant-scoped channel."""
        pass
```

### 4.3 Concrete Local Implementation Contract (`LocalInMemoryCacheBroker`)
- **Backend:** Pure Python thread-safe dictionary with `threading.Lock` and monotonic timestamps for TTL checks.
- **Memory Ceiling:** Hard limit of 10,000 keys and maximum memory cap of **25 MB**. Capped via LRU eviction policy.
- **Zero External Dependencies:** Implemented without requiring `redis-py` or external daemons.
