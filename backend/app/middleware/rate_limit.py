"""
Tenant-Scoped Token-Bucket Rate Limiting Middleware for Stage G Enterprise Governance.
"""
import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt

from app.core.config import settings
from app.core.security import decode_access_token
from app.adapters.factory import AdapterFactory

EXEMPT_PATHS = {
    "/",
    "/health",
    "/health/live",
    "/health/ready",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    f"{settings.API_V1_STR}/health",
    f"{settings.API_V1_STR}/auth/login",
}


class TenantRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Evaluates in-memory token-bucket rate limits per tenant.
    Returns HTTP 429 with Retry-After when threshold is breached.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Exempt health, metrics, documentation, and root endpoints
        if path in EXEMPT_PATHS or path.startswith("/docs") or path.startswith("/static"):
            return await call_next(request)

        # Extract tenant context from Header or Bearer Token
        tenant_id = 1
        header_tid = request.headers.get("x-tenant-id")
        if header_tid is not None and str(header_tid).strip():
            raw_tid = str(header_tid).strip()
            try:
                parsed_tid = int(raw_tid)
                if parsed_tid <= 0:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "type": "https://unimind.ai/errors/HTTP_400",
                            "title": "Bad Request",
                            "status": 400,
                            "detail": f"Invalid X-Tenant-ID header '{raw_tid}'. Must be a positive integer ID.",
                        },
                    )
                tenant_id = parsed_tid
            except (ValueError, TypeError):
                return JSONResponse(
                    status_code=400,
                    content={
                        "type": "https://unimind.ai/errors/HTTP_400",
                        "title": "Bad Request",
                        "status": 400,
                        "detail": f"Invalid X-Tenant-ID header '{raw_tid}'. Must be a positive integer ID.",
                    },
                )
        else:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
                try:
                    payload = decode_access_token(token)
                    # In our JWT payload, tenant_id is either direct or in sub
                    if "tenant_id" in payload and payload["tenant_id"]:
                        tenant_id = int(payload["tenant_id"])
                except Exception:
                    pass

        # In-memory sliding window check
        cache_broker = AdapterFactory.get_cache()
        # Default rate limit: 120 req/min
        res = cache_broker.check_rate_limit(
            tenant_id=tenant_id,
            limit_key="api_requests",
            max_requests=120,
            window_seconds=60,
        )

        if not res["allowed"]:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded for tenant {tenant_id}. Try again in {res['reset_seconds']}s.",
                    "tenant_id": tenant_id,
                    "limit": res["limit"],
                    "remaining": 0,
                    "reset_seconds": res["reset_seconds"],
                },
                headers={
                    "Retry-After": str(res["reset_seconds"]),
                    "X-RateLimit-Limit": str(res["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(res["reset_seconds"]),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(res["limit"])
        response.headers["X-RateLimit-Remaining"] = str(res["remaining"])
        response.headers["X-RateLimit-Reset"] = str(res["reset_seconds"])
        return response
