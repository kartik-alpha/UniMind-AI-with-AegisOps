from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from digital_twin.models import AcademicEvent, TrafficIntensity


class SimulationRunRequest(BaseModel):
    total_students: int = Field(default=12000, ge=100, le=100000)
    concurrency_ratio: float = Field(default=0.15, ge=0.01, le=1.0)
    duration_hours: int = Field(default=24, ge=1, le=168)
    event: AcademicEvent = AcademicEvent.NORMAL_DAY
    intensity: TrafficIntensity = TrafficIntensity.NORMAL
    capacity_overrides: Optional[Dict[str, Dict[str, Any]]] = None


class CapacityPlanRequest(BaseModel):
    total_students: int = Field(default=15000, ge=100, le=100000)
    concurrency_ratio: float = Field(default=0.20, ge=0.01, le=1.0)
    duration_hours: int = Field(default=24, ge=1, le=168)
    event: AcademicEvent = AcademicEvent.EXAM_PERIOD
    intensity: TrafficIntensity = TrafficIntensity.PEAK
    capacity_overrides: Optional[Dict[str, Dict[str, Any]]] = None
    sync_to_aegisops: bool = Field(default=True)


class ScenarioCompareRequest(BaseModel):
    total_students: int = Field(default=15000, ge=100, le=100000)
    event: AcademicEvent = AcademicEvent.EXAM_PERIOD
    duration_hours: int = Field(default=24, ge=1, le=168)


class ProactiveRemediationApproveRequest(BaseModel):
    incident_id: int
    target_replicas: Optional[int] = 4


class ProactiveRemediationRejectRequest(BaseModel):
    incident_id: int
    reason: Optional[str] = "Admin deferred proactive pre-scaling"


class ProactiveRemediationCancelRequest(BaseModel):
    incident_id: int
    reason: Optional[str] = "Operator canceled proactive action"


class PredictiveEventRequest(BaseModel):
    event_type: str = Field(..., description="THERMAL_SPIKE, TRAFFIC_SURGE, RESOURCE_EXHAUSTION, OPERATIONAL_ANOMALY")
    service_name: str = Field(..., description="Target service or infrastructure component")
    predicted_metric: float = Field(..., description="Forecasted metric value")
    threshold_metric: float = Field(..., description="Threshold metric limit")
    lead_time_hours: float = Field(default=2.0, description="Hours before breach is predicted to manifest")
    recommendation: str = Field(..., description="Proposed proactive remediation action")
    severity: str = Field(default="HIGH", description="CRITICAL, HIGH, MEDIUM, LOW")
    details: Optional[Dict[str, Any]] = None


class AcademicEventDetail(BaseModel):
    event_id: str
    name: str
    description: str
    primary_impact_service: str
    concurrency_multiplier: float
    typical_peak_window: str

