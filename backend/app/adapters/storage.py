"""
Storage Adapter Interface & Local Storage Implementation.
Enforces multi-tenant filesystem isolation, path traversal prevention, and storage accounting.
"""
import os
import shutil
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, BinaryIO

from app.adapters.exceptions import (
    AdapterException,
    TenantIsolationViolationError,
    ResourceNotFoundError,
    QuotaExceededError,
)


class StorageAdapter(ABC):
    """Abstract interface for multi-tenant document payload storage."""

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
        content_type: str = "application/pdf",
        max_bytes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Persist a document payload under the tenant's namespace."""
        pass

    @abstractmethod
    def read_file(self, tenant_id: int, storage_path: str) -> bytes:
        """Read the entire binary payload of a stored document."""
        pass

    @abstractmethod
    def stream_file(self, tenant_id: int, storage_path: str, chunk_size: int = 65536) -> BinaryIO:
        """Return a binary stream for file streaming."""
        pass

    @abstractmethod
    def delete_file(self, tenant_id: int, storage_path: str) -> bool:
        """Idempotently delete a stored file."""
        pass

    @abstractmethod
    def file_exists(self, tenant_id: int, storage_path: str) -> bool:
        """Check whether a file exists in the tenant's namespace."""
        pass

    @abstractmethod
    def get_tenant_storage_usage(self, tenant_id: int) -> Dict[str, Any]:
        """Calculate total storage consumption for a given tenant."""
        pass


class LocalStorageAdapter(StorageAdapter):
    """
    Local filesystem storage adapter preserving Stage F compatibility.
    Target directory: data/tenants/{tenant_id}/documents/{category}/
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or "data").resolve()
        self._connected = False

    def connect(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def health_check(self) -> Dict[str, Any]:
        try:
            stat = shutil.disk_usage(self.base_dir)
            return {
                "status": "healthy" if self._connected else "degraded",
                "adapter": "LocalStorageAdapter",
                "base_dir": str(self.base_dir),
                "total_bytes": stat.total,
                "used_bytes": stat.used,
                "free_bytes": stat.free,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "adapter": "LocalStorageAdapter",
                "error": str(e),
            }

    def _get_tenant_root(self, tenant_id: int) -> Path:
        if tenant_id <= 0:
            raise TenantIsolationViolationError("Tenant ID must be a positive integer", tenant_id=tenant_id)
        return (self.base_dir / "tenants" / str(tenant_id) / "documents").resolve()

    def _sanitize_and_resolve(self, tenant_id: int, category: str, filename: str) -> Path:
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            raise TenantIsolationViolationError(
                "Illegal or traversal filename detected", tenant_id=tenant_id, details={"filename": filename}
            )

        clean_filename = Path(filename).name
        if not clean_filename or clean_filename in (".", ".."):
            raise TenantIsolationViolationError(
                "Illegal or traversal filename detected", tenant_id=tenant_id, details={"filename": filename}
            )

        clean_category = Path(category).name
        tenant_cat_dir = (self._get_tenant_root(tenant_id) / clean_category).resolve()
        tenant_root = self._get_tenant_root(tenant_id)

        # Enforce that directory resides strictly under tenant root
        if not str(tenant_cat_dir).startswith(str(tenant_root)):
            raise TenantIsolationViolationError(
                "Category path traversal detected", tenant_id=tenant_id, details={"category": category}
            )

        tenant_cat_dir.mkdir(parents=True, exist_ok=True)
        resolved_path = (tenant_cat_dir / clean_filename).resolve()

        if not str(resolved_path).startswith(str(tenant_root)):
            raise TenantIsolationViolationError(
                "Target file path escapes tenant jail", tenant_id=tenant_id, details={"path": str(resolved_path)}
            )

        return resolved_path

    def _validate_path_ownership(self, tenant_id: int, storage_path: str) -> Path:
        resolved = Path(storage_path).resolve()
        tenant_root = self._get_tenant_root(tenant_id)
        if not str(resolved).startswith(str(tenant_root)):
            raise TenantIsolationViolationError(
                "Access denied: path does not belong to tenant namespace",
                tenant_id=tenant_id,
                details={"requested_path": storage_path, "tenant_root": str(tenant_root)},
            )
        return resolved

    def save_file(
        self,
        tenant_id: int,
        category: str,
        filename: str,
        file_obj: BinaryIO,
        content_type: str = "application/pdf",
        max_bytes: Optional[int] = None,
    ) -> Dict[str, Any]:
        dest_path = self._sanitize_and_resolve(tenant_id, category, filename)
        temp_dest = dest_path.with_suffix(dest_path.suffix + ".part")

        hasher = hashlib.sha256()
        bytes_written = 0

        try:
            with open(temp_dest, "wb") as f_out:
                while True:
                    chunk = file_obj.read(65536)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if max_bytes is not None and bytes_written > max_bytes:
                        raise QuotaExceededError(
                            f"File upload exceeds tenant maximum size limit ({max_bytes} bytes)",
                            tenant_id=tenant_id,
                            details={"bytes_written": bytes_written, "max_bytes": max_bytes},
                        )
                    hasher.update(chunk)
                    f_out.write(chunk)

            # Atomic move from .part to destination
            shutil.move(str(temp_dest), str(dest_path))
        except Exception:
            if temp_dest.exists():
                try:
                    temp_dest.unlink()
                except Exception:
                    pass
            raise

        rel_path = str(dest_path).replace("\\", "/")

        return {
            "storage_path": rel_path,
            "filename": dest_path.name,
            "category": category,
            "size_bytes": bytes_written,
            "sha256_hash": hasher.hexdigest(),
            "content_type": content_type,
        }

    def read_file(self, tenant_id: int, storage_path: str) -> bytes:
        dest_path = self._validate_path_ownership(tenant_id, storage_path)
        if not dest_path.exists() or not dest_path.is_file():
            raise ResourceNotFoundError(
                f"File not found: {storage_path}", tenant_id=tenant_id, details={"path": storage_path}
            )
        with open(dest_path, "rb") as f:
            return f.read()

    def stream_file(self, tenant_id: int, storage_path: str, chunk_size: int = 65536) -> BinaryIO:
        dest_path = self._validate_path_ownership(tenant_id, storage_path)
        if not dest_path.exists() or not dest_path.is_file():
            raise ResourceNotFoundError(
                f"File not found: {storage_path}", tenant_id=tenant_id, details={"path": storage_path}
            )
        return open(dest_path, "rb")

    def delete_file(self, tenant_id: int, storage_path: str) -> bool:
        try:
            dest_path = self._validate_path_ownership(tenant_id, storage_path)
            if dest_path.exists() and dest_path.is_file():
                dest_path.unlink()
                return True
            return False
        except TenantIsolationViolationError:
            raise
        except Exception as e:
            raise AdapterException(f"Failed to delete file: {e}", tenant_id=tenant_id)

    def file_exists(self, tenant_id: int, storage_path: str) -> bool:
        try:
            dest_path = self._validate_path_ownership(tenant_id, storage_path)
            return dest_path.exists() and dest_path.is_file()
        except TenantIsolationViolationError:
            return False

    def get_tenant_storage_usage(self, tenant_id: int) -> Dict[str, Any]:
        tenant_root = self._get_tenant_root(tenant_id)
        if not tenant_root.exists():
            return {"tenant_id": tenant_id, "total_bytes": 0, "total_files": 0}

        total_bytes = 0
        total_files = 0
        for p in tenant_root.rglob("*"):
            if p.is_file():
                total_bytes += p.stat().st_size
                total_files += 1

        return {
            "tenant_id": tenant_id,
            "total_bytes": total_bytes,
            "total_files": total_files,
            "storage_root": str(tenant_root),
        }


class S3StorageAdapter(StorageAdapter):
    """
    Enterprise S3-Compatible Object Storage Adapter for Stage H (AWS S3 & MinIO).
    Enforces strict tenant prefixing: tenant_{tenant_id}/{category}/{filename}.
    Supports live S3 cluster connection with automatic local simulation fallback.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None,
    ):
        from app.core.config import settings
        self.endpoint_url = endpoint_url or getattr(settings, "S3_ENDPOINT_URL", "http://localhost:9000")
        self.access_key = access_key or getattr(settings, "S3_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or getattr(settings, "S3_SECRET_KEY", "minioadminpassword")
        self.bucket_name = bucket_name or getattr(settings, "S3_BUCKET_NAME", "unimind-documents")
        self.region_name = region_name or getattr(settings, "S3_REGION_NAME", "us-east-1")
        self._s3_client = None
        self._connected = False
        self._local_fallback = LocalStorageAdapter(base_dir="data/s3_storage_fallback")

    def connect(self) -> None:
        try:
            import boto3
            from botocore.client import Config
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region_name,
                config=Config(signature_version="s3v4", connect_timeout=2, read_timeout=3),
            )
            # Verify bucket existence
            self._s3_client.head_bucket(Bucket=self.bucket_name)
            self._connected = True
        except Exception:
            self._s3_client = None
            self._local_fallback.connect()
            self._connected = True

    def disconnect(self) -> None:
        self._connected = False
        self._s3_client = None
        self._local_fallback.disconnect()

    def health_check(self) -> Dict[str, Any]:
        if self._s3_client is not None:
            try:
                import time
                start = time.perf_counter()
                self._s3_client.head_bucket(Bucket=self.bucket_name)
                lat_ms = (time.perf_counter() - start) * 1000
                return {
                    "status": "healthy",
                    "adapter": "S3StorageAdapter",
                    "engine": "S3/MinIO-Distributed",
                    "mode": "live_cluster",
                    "bucket": self.bucket_name,
                    "endpoint": self.endpoint_url,
                    "latency_ms": round(lat_ms, 2),
                }
            except Exception as e:
                return {
                    "status": "degraded",
                    "adapter": "S3StorageAdapter",
                    "error": str(e),
                    "mode": "live_cluster_unreachable",
                }
        fb_health = self._local_fallback.health_check()
        return {
            "status": "healthy" if self._connected else "degraded",
            "adapter": "S3StorageAdapter",
            "engine": "S3-Simulated",
            "mode": "standalone_local",
            "fallback": fb_health,
        }

    def _get_s3_key(self, tenant_id: int, category: str, filename: str) -> str:
        if tenant_id <= 0:
            raise TenantIsolationViolationError("Tenant ID must be a positive integer", tenant_id=tenant_id)
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            raise TenantIsolationViolationError("Path traversal or invalid characters detected in object key", tenant_id=tenant_id)
        clean_cat = category.strip().lower()
        return f"tenant_{tenant_id}/{clean_cat}/{filename}"

    def save_file(
        self,
        tenant_id: int,
        category: str,
        filename: str,
        file_obj: BinaryIO,
        content_type: str = "application/pdf",
        max_bytes: Optional[int] = None,
    ) -> Dict[str, Any]:
        s3_key = self._get_s3_key(tenant_id, category, filename)
        content = file_obj.read()
        file_size = len(content)

        if max_bytes and file_size > max_bytes:
            raise QuotaExceededError(f"File size {file_size} exceeds max allowed {max_bytes}", tenant_id=tenant_id)

        sha256_hash = hashlib.sha256(content).hexdigest()

        if self._s3_client is not None:
            try:
                import io
                self._s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=content,
                    ContentType=content_type,
                    Metadata={
                        "tenant_id": str(tenant_id),
                        "category": category,
                        "sha256": sha256_hash,
                    },
                )
                return {
                    "storage_path": f"s3://{self.bucket_name}/{s3_key}",
                    "size_bytes": file_size,
                    "sha256": sha256_hash,
                    "tenant_id": tenant_id,
                    "category": category,
                    "filename": filename,
                }
            except Exception:
                pass

        import io
        fallback_res = self._local_fallback.save_file(
            tenant_id=tenant_id,
            category=category,
            filename=filename,
            file_obj=io.BytesIO(content),
            content_type=content_type,
            max_bytes=max_bytes,
        )
        fallback_res["sha256"] = fallback_res.get("sha256_hash", sha256_hash)
        return fallback_res

    def read_file(self, tenant_id: int, storage_path: str) -> bytes:
        if self._s3_client is not None and storage_path.startswith("s3://"):
            try:
                s3_key = storage_path.replace(f"s3://{self.bucket_name}/", "")
                if not s3_key.startswith(f"tenant_{tenant_id}/"):
                    raise TenantIsolationViolationError("Attempted cross-tenant S3 object access", tenant_id=tenant_id)
                obj = self._s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                return obj["Body"].read()
            except TenantIsolationViolationError:
                raise
            except Exception:
                pass
        return self._local_fallback.read_file(tenant_id, storage_path)

    def stream_file(self, tenant_id: int, storage_path: str, chunk_size: int = 65536) -> BinaryIO:
        import io
        content = self.read_file(tenant_id, storage_path)
        return io.BytesIO(content)

    def delete_file(self, tenant_id: int, storage_path: str) -> bool:
        if self._s3_client is not None and storage_path.startswith("s3://"):
            try:
                s3_key = storage_path.replace(f"s3://{self.bucket_name}/", "")
                if not s3_key.startswith(f"tenant_{tenant_id}/"):
                    raise TenantIsolationViolationError("Attempted cross-tenant S3 delete", tenant_id=tenant_id)
                self._s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                return True
            except TenantIsolationViolationError:
                raise
            except Exception:
                pass
        return self._local_fallback.delete_file(tenant_id, storage_path)

    def file_exists(self, tenant_id: int, storage_path: str) -> bool:
        if self._s3_client is not None and storage_path.startswith("s3://"):
            try:
                s3_key = storage_path.replace(f"s3://{self.bucket_name}/", "")
                if not s3_key.startswith(f"tenant_{tenant_id}/"):
                    return False
                self._s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                return True
            except Exception:
                return False
        return self._local_fallback.file_exists(tenant_id, storage_path)

    def get_tenant_storage_usage(self, tenant_id: int) -> Dict[str, Any]:
        if tenant_id <= 0:
            raise TenantIsolationViolationError("Tenant ID must be positive", tenant_id=tenant_id)
        if self._s3_client is not None:
            try:
                prefix = f"tenant_{tenant_id}/"
                paginator = self._s3_client.get_paginator("list_objects_v2")
                pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
                total_bytes = 0
                total_files = 0
                for page in pages:
                    for obj in page.get("Contents", []):
                        total_bytes += obj.get("Size", 0)
                        total_files += 1
                return {
                    "tenant_id": tenant_id,
                    "total_bytes": total_bytes,
                    "total_files": total_files,
                    "storage_root": f"s3://{self.bucket_name}/{prefix}",
                }
            except Exception:
                pass
        return self._local_fallback.get_tenant_storage_usage(tenant_id)
