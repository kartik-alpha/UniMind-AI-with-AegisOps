from datetime import datetime
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()

@router.get("", response_model=HealthResponse, summary="System Health Status")
def get_system_health():
    """
    Performs a system readiness and liveness check.
    Returns status of the core API service, version, and running environment.
    """
    return HealthResponse(
        status="healthy",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.utcnow(),
        services={
            "api_server": "online",
            "routing": "active",
            "core_engine": "ready"
        }
    )