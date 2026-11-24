import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure both backend and project root are in sys.path
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent
_project_root = _backend_dir.parent
for _p in [str(_backend_dir), str(_project_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.core.config import settings
from app.core.logging import logger
from app.api.v1.router import api_router
from app.db.seed_data import seed_initial_data
from app.adapters.factory import AdapterFactory
from app.middleware.rate_limit import TenantRateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist, demo data is seeded, and adapters initialized
    logger.info("Initializing UniMind AI & AegisOps database schema, adapters and seed data...")
    try:
        seed_initial_data()
        AdapterFactory.initialize_all()
        logger.info("Database schema, Stage G adapters and seed data successfully verified.")
    except Exception as e:
        logger.error(f"Error during startup initialization: {e}")
    yield
    # Shutdown
    logger.info("Shutting down UniMind AI & AegisOps API engine.")
    try:
        AdapterFactory.shutdown_all()
    except Exception:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="UniMind AI & AegisOps University Operations and Predictive AIOps Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Rate Limiting Middleware (Tenant-Scoped)
app.add_middleware(TenantRateLimitMiddleware)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


import os
from app.services.metrics_service import metrics_registry


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    req_id = f"req_{int(start_time*1000)}_{os.urandom(2).hex()}"
    request.state.request_id = req_id
    response = await call_next(request)
    process_time = time.time() - start_time

    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    response.headers["X-Request-ID"] = req_id

    # OWASP Top 10 Security Hardening Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

    # Record Prometheus metrics
    try:
        metrics_registry.inc_counter(
            "unimind_http_requests_total",
            labels={"method": request.method, "status": str(response.status_code)},
        )
        if response.status_code >= 400:
            metrics_registry.inc_counter(
                "unimind_http_errors_total",
                labels={"method": request.method, "status": str(response.status_code)},
            )
        metrics_registry.observe_histogram(
            "unimind_http_request_duration_seconds",
            process_time,
            labels={"method": request.method},
        )
    except Exception:
        pass

    logger.info(f"[{request.method}] {request.url.path} (ID: {req_id}) - Status: {response.status_code} - Time: {process_time:.4f}s")
    return response


import http

# Global Exception Handlers (Standardized RFC 7807 Problem Details Protocol)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = getattr(request.state, "request_id", None) or f"req_{int(time.time()*1000)}"
    status_phrase = (
        http.HTTPStatus(exc.status_code).phrase
        if exc.status_code in http.HTTPStatus._value2member_map_
        else "HTTP Error"
    )
    content = {
        # RFC 7807 Core Properties
        "type": f"https://unimind.ai/errors/HTTP_{exc.status_code}",
        "title": status_phrase,
        "status": exc.status_code,
        "detail": exc.detail,
        "instance": request.url.path,
        # Enterprise Audit Extensions
        "request_id": req_id,
        "timestamp": int(time.time()),
        # Backward-compatible Envelope
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
            "request_id": req_id,
        },
    }
    headers = getattr(exc, "headers", None) or {}
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=headers,
        media_type="application/problem+json",
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", None) or f"req_{int(time.time()*1000)}"
    logger.error(f"Unhandled server error on {request.method} {request.url.path} (ID: {req_id}): {exc}", exc_info=True)
    content = {
        # RFC 7807 Core Properties
        "type": "https://unimind.ai/errors/INTERNAL_SERVER_ERROR",
        "title": "Internal Server Error",
        "status": 500,
        "detail": str(exc) if settings.DEBUG else "An unexpected internal server error occurred.",
        "instance": request.url.path,
        # Enterprise Audit Extensions
        "request_id": req_id,
        "timestamp": int(time.time()),
        # Backward-compatible Envelope
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": str(exc) if settings.DEBUG else "An internal server error occurred.",
            "request_id": req_id,
        },
    }
    return JSONResponse(
        status_code=500,
        content=content,
        media_type="application/problem+json",
    )


# Include V1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)
# Root level health shortcut
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API Engine",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }
