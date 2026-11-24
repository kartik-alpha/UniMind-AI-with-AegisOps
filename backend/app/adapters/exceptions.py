"""
Unified Adapter Exception Hierarchy for Stage G Hexagonal Architecture.
Prevents low-level driver exceptions from leaking into application domain services.
"""
from typing import Dict, Any, Optional


class AdapterException(Exception):
    """Base exception for all Stage G adapter failures."""
    def __init__(self, message: str, tenant_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.tenant_id = tenant_id
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "tenant_id": self.tenant_id,
            "details": self.details
        }


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
