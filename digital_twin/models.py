import enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class AcademicEvent(str, enum.Enum):
    NORMAL_DAY = "NORMAL_DAY"
    EXAM_PERIOD = "EXAM_PERIOD"
    ASSIGNMENT_DEADLINE = "ASSIGNMENT_DEADLINE"
    ADMISSION_PERIOD = "ADMISSION_PERIOD"
    RESULT_ANNOUNCEMENT = "RESULT_ANNOUNCEMENT"


class TrafficIntensity(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    PEAK = "PEAK"
    EXTREME = "EXTREME"


class ServiceCapacitySpec(BaseModel):
    service_name: str
    replicas: int = 2
    max_rps_per_replica: float = 500.0  # Max request capacity before queuing
    base_cpu_percent: float = 20.0
    base_memory_percent: float = 35.0
    db_connections_per_100_rps: float = 4.0
    max_db_connections: int = 50
    avg_query_latency_ms: float = 80.0


class SimulationConfig(BaseModel):
    total_students: int = Field(default=10000, ge=100, le=100000)
    concurrency_ratio: float = Field(default=0.15, ge=0.01, le=1.0)
    duration_hours: int = Field(default=24, ge=1, le=168)
    event: AcademicEvent = AcademicEvent.NORMAL_DAY
    intensity: TrafficIntensity = TrafficIntensity.NORMAL
    capacity_overrides: Optional[Dict[str, Dict[str, Any]]] = None


class HourlyActivityPoint(BaseModel):
    hour: int
    time_label: str
    concurrent_students: int
    active_percentage: float
    total_incoming_rps: float
    service_rps: Dict[str, float]
    event: AcademicEvent
    is_simulation: bool = True


class PredictedMetricPoint(BaseModel):
    hour: int
    time_label: str
    service_name: str
    predicted_rps: float
    capacity_rps: float
    utilization_percent: float
    predicted_cpu_percent: float
    predicted_memory_percent: float
    predicted_latency_ms: float
    predicted_db_connections: int
    db_pool_saturation_percent: float
    is_bottleneck: bool
    bottleneck_reasons: List[str]
    is_simulation: bool = True


class BottleneckAlert(BaseModel):
    alert_id: str
    service_name: str
    hour: int
    time_label: str
    severity: str  # WARNING, CRITICAL
    primary_bottleneck: str  # CPU, MEMORY, DB_POOL, RPS_CAPACITY
    predicted_value: float
    threshold_value: float
    lead_time_hours: int
    explanation: str
    recommendation: str
    target_replicas: int
    is_simulation: bool = True


class CapacityForecastResult(BaseModel):
    config: SimulationConfig
    total_students: int
    event: AcademicEvent
    intensity: TrafficIntensity
    peak_concurrent_users: int
    peak_hour: int
    peak_rps: float
    timeline: List[HourlyActivityPoint]
    metrics_by_service: Dict[str, List[PredictedMetricPoint]]
    alerts: List[BottleneckAlert]
    overall_status: str  # HEALTHY, WARNING, CRITICAL
    executive_summary: str
    is_simulation: bool = True


class ScenarioComparisonResult(BaseModel):
    scenarios: Dict[str, CapacityForecastResult]
    comparison_table: List[Dict[str, Any]]
    key_findings: List[str]
    is_simulation: bool = True

