from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Overall health status of the API")
    service: str = Field(default="UniMind AI API", description="Service name")
    environment: str = Field(default="development", description="Execution environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC Timestamp of health check")
    database: str = Field(default="unknown", description="Database connection status")
