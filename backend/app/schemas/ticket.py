from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class TicketBase(BaseModel):
    title: str
    description: str
    category: str = "general"
    priority: str = "MEDIUM"


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None


class TicketResponse(TicketBase):
    id: int
    ticket_code: str
    user_id: int
    status: str
    assigned_to: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentResponse(BaseModel):
    id: int
    incident_code: str
    service_name: str
    title: str
    severity: str
    status: str
    anomaly_score: float
    metrics_summary: Optional[Dict[str, Any]] = None
    root_cause: Optional[str] = None
    recommendation: Optional[str] = None
    remediation_status: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
