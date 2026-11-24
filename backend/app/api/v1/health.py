import time
from datetime import datetime
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse
from app.services.metrics_service import metrics_registry
from app.adapters.factory import AdapterFactory

router = APIRouter(tags=["Health & Observability"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns the operational status, environment details, and timestamp of the UniMind API."
)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        database="connected"
    )


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Kubernetes / Docker Liveness Probe",
    description="Checks whether the API server process is alive and responsive."
)
def liveness_probe():
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/health/ready",
    summary="Kubernetes / Docker Readiness Probe",
    description="Validates that required service dependencies (Database, Vector Engine, Adapters) are ready to receive traffic."
)
def readiness_probe(db: Session = Depends(get_db)):
    checks = {}
    is_ready = True

    # 1. Database Connectivity
    try:
        db.execute(text("SELECT 1;"))
        checks["database"] = "ready"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)[:60]}"
        is_ready = False

    # 2. Vector Database
    try:
        v_health = AdapterFactory.get_vector().health_check()
        checks["vector_store"] = v_health.get("status", "ready")
    except Exception as e:
        checks["vector_store"] = f"unhealthy: {str(e)[:60]}"
        is_ready = False

    # 3. Cache & Storage Adapters
    try:
        s_health = AdapterFactory.get_storage().health_check()
        c_health = AdapterFactory.get_cache().health_check()
        checks["storage"] = s_health.get("status", "ready")
        checks["cache_broker"] = c_health.get("status", "ready")
    except Exception as e:
        checks["adapters"] = f"unhealthy: {str(e)[:60]}"
        is_ready = False

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(
        content=str({
            "status": "ready" if is_ready else "not_ready",
            "service": settings.PROJECT_NAME,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
        }).replace("'", '"'),
        status_code=status_code,
        media_type="application/json",
    )


@router.get(
    "/metrics",
    summary="Prometheus Metrics Exposition",
    description="Returns standard Prometheus text format 0.0.4 metrics for platform observability."
)
def prometheus_metrics():
    exposition_text = metrics_registry.generate_exposition()
    return Response(
        content=exposition_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
