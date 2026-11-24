from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.api.tenant_deps import get_current_tenant
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.ticket import Incident, IncidentStatus
from app.schemas.digital_twin import (
    SimulationRunRequest,
    CapacityPlanRequest,
    ScenarioCompareRequest,
    ProactiveRemediationApproveRequest,
    ProactiveRemediationRejectRequest,
    ProactiveRemediationCancelRequest,
    PredictiveEventRequest,
    AcademicEventDetail,
)
from digital_twin.models import (
    AcademicEvent,
    TrafficIntensity,
    SimulationConfig,
    CapacityForecastResult,
    ScenarioComparisonResult,
)
from digital_twin.simulator import CampusActivitySimulator
from digital_twin.capacity_planner import PredictiveCapacityPlanner
from digital_twin.aegisops_bridge import AegisOpsDigitalTwinBridge

router = APIRouter(prefix="/digital-twin", tags=["Digital Twin Campus Engine"])


@router.get("/events", response_model=List[AcademicEventDetail])
def list_academic_events(current_user: User = Depends(get_current_user)):
    """
    List modeled campus academic calendar events and their traffic impact profiles.
    """
    return [
        AcademicEventDetail(
            event_id=AcademicEvent.NORMAL_DAY.value,
            name="Normal Academic Day",
            description="Standard campus routine with balanced morning attendance check-ins, afternoon labs, and evening study.",
            primary_impact_service="Balanced across all services",
            concurrency_multiplier=1.0,
            typical_peak_window="10:00 - 11:00 & 20:00 - 21:00",
        ),
        AcademicEventDetail(
            event_id=AcademicEvent.EXAM_PERIOD.value,
            name="Mid-Term / Final Examination Period",
            description="Synchronous exam login rushes, stateful test submissions, and high query concurrency on Exam Service.",
            primary_impact_service="Exam Service",
            concurrency_multiplier=1.65,
            typical_peak_window="09:00 - 12:00 & 14:00 - 17:00",
        ),
        AcademicEventDetail(
            event_id=AcademicEvent.ASSIGNMENT_DEADLINE.value,
            name="Major Assignment Submission Deadline",
            description="Pre-midnight submission rush, large document uploads, and grading worker queue backlog on LMS.",
            primary_impact_service="LMS (Learning Management System)",
            concurrency_multiplier=1.75,
            typical_peak_window="21:00 - 23:59",
        ),
        AcademicEventDetail(
            event_id=AcademicEvent.ADMISSION_PERIOD.value,
            name="New Student Admissions & Enrollment",
            description="High public portal traffic, prospective applicant queries, and handbook document downloads.",
            primary_impact_service="Student Portal",
            concurrency_multiplier=1.35,
            typical_peak_window="10:00 - 16:00",
        ),
        AcademicEventDetail(
            event_id=AcademicEvent.RESULT_ANNOUNCEMENT.value,
            name="Semester Grade & Result Announcement",
            description="Instantaneous concurrency burst causing massive database connection pool saturation and read contention.",
            primary_impact_service="Student Portal & Exam Service",
            concurrency_multiplier=2.40,
            typical_peak_window="10:00 - 13:00 (Shock Spike)",
        ),
    ]


@router.post("/simulate")
def simulate_student_activity(
    payload: SimulationRunRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Executes student activity simulation and returns hourly timeline with service RPS distribution.
    """
    cfg = SimulationConfig(
        total_students=payload.total_students,
        concurrency_ratio=payload.concurrency_ratio,
        duration_hours=payload.duration_hours,
        event=payload.event,
        intensity=payload.intensity,
        capacity_overrides=payload.capacity_overrides,
    )
    simulator = CampusActivitySimulator(cfg)
    timeline = simulator.simulate_timeline()

    return {
        "config": cfg.model_dump(),
        "total_hours": len(timeline),
        "peak_concurrent_students": max(t.concurrent_students for t in timeline) if timeline else 0,
        "peak_incoming_rps": max(t.total_incoming_rps for t in timeline) if timeline else 0.0,
        "timeline": [t.model_dump() for t in timeline],
        "is_simulation": True,
        "data_source": "digital_twin_engine",
    }


@router.post("/capacity-plan", response_model=CapacityForecastResult)
def run_predictive_capacity_plan(
    payload: CapacityPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Runs predictive capacity planner for the campus fleet.
    Forecasts CPU, Memory, Latency, and Database Pool usage.
    Optionally syncs predicted bottlenecks to AegisOps as early-warning incidents.
    """
    cfg = SimulationConfig(
        total_students=payload.total_students,
        concurrency_ratio=payload.concurrency_ratio,
        duration_hours=payload.duration_hours,
        event=payload.event,
        intensity=payload.intensity,
        capacity_overrides=payload.capacity_overrides,
    )
    planner = PredictiveCapacityPlanner()
    forecast = planner.generate_capacity_forecast(cfg)

    # Sync top alerts to AegisOps database as PENDING_APPROVAL incidents
    if payload.sync_to_aegisops and forecast.alerts:
        # Group by service to avoid duplicate alert flooding
        by_svc = {}
        for a in forecast.alerts:
            if a.service_name not in by_svc or a.severity == "CRITICAL":
                by_svc[a.service_name] = a

        tenant_id = 1
        if hasattr(current_user, "tenant_id") and current_user.tenant_id:
            tenant_id = current_user.tenant_id

        for s_alert in by_svc.values():
            AegisOpsDigitalTwinBridge.sync_alert_to_incident(
                db=db, alert=s_alert, config=cfg, tenant_id=tenant_id
            )

    return forecast


@router.post("/scenario-compare", response_model=ScenarioComparisonResult)
def compare_scenarios_endpoint(
    payload: ScenarioCompareRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Runs multi-scenario comparative analysis (Baseline Normal vs Peak Academic vs Extreme Shock).
    """
    cfg = SimulationConfig(
        total_students=payload.total_students,
        duration_hours=payload.duration_hours,
        event=payload.event,
    )
    planner = PredictiveCapacityPlanner()
    return planner.compare_scenarios(cfg)


@router.get("/predictive-alerts")
def get_predictive_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
) -> List[Dict[str, Any]]:
    """
    Retrieve active predictive early-warning incidents registered in AegisOps for the tenant.
    """
    incidents = (
        db.query(Incident)
        .filter(
            Incident.tenant_id == current_tenant.id,
            (Incident.title.ilike("%[PREDICTIVE ALERT]%") | Incident.title.ilike("%[THERMAL_SPIKE]%") |
             Incident.title.ilike("%[TRAFFIC_SURGE]%") | Incident.title.ilike("%[RESOURCE_EXHAUSTION]%") |
             Incident.title.ilike("%[OPERATIONAL_ANOMALY]%")),
        )
        .order_by(Incident.created_at.desc())
        .limit(100)
        .all()
    )

    result = []
    for inc in incidents:
        result.append({
            "id": inc.id,
            "incident_code": inc.incident_code,
            "service_name": inc.service_name,
            "title": inc.title,
            "status": inc.status.value if hasattr(inc.status, "value") else str(inc.status),
            "severity": inc.severity.value if hasattr(inc.severity, "value") else str(inc.severity),
            "anomaly_score": inc.anomaly_score,
            "metrics_summary": inc.metrics_summary,
            "root_cause": inc.root_cause,
            "recommendation": inc.recommendation,
            "approved_by": inc.approved_by,
            "action_taken": inc.action_taken,
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
            "is_simulation": True,
            "tenant_id": inc.tenant_id,
        })
    return result


@router.post("/events/predictive-alert")
def ingest_predictive_event_endpoint(
    payload: PredictiveEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Ingest a qualifying predictive alert from Digital Twin simulation into an AegisOps operational incident.
    Defaults to PENDING_APPROVAL.
    """
    try:
        inc = AegisOpsDigitalTwinBridge.create_predictive_event_incident(
            db=db,
            tenant_id=current_tenant.id,
            event_type=payload.event_type,
            service_name=payload.service_name,
            predicted_metric=payload.predicted_metric,
            threshold_metric=payload.threshold_metric,
            lead_time_hours=payload.lead_time_hours,
            recommendation=payload.recommendation,
            severity=payload.severity,
            details=payload.details,
        )
        return {
            "status": "INCIDENT_REGISTERED",
            "incident_id": inc.id,
            "incident_code": inc.incident_code,
            "title": inc.title,
            "approval_status": inc.status.value if hasattr(inc.status, "value") else str(inc.status),
            "tenant_id": inc.tenant_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/proactive-remediation/approve")
def approve_proactive_remediation_endpoint(
    payload: ProactiveRemediationApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    current_tenant: Organization = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Approve a proactive pre-scaling recommendation for a predicted bottleneck.
    Protected by ADMIN RBAC. Verifies restored headroom and updates incident to RESOLVED.
    """
    inc = db.query(Incident).filter(Incident.id == payload.incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {payload.incident_id} not found.")
    if inc.tenant_id and inc.tenant_id != current_tenant.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Cross-tenant incident approval denied.")

    try:
        res = AegisOpsDigitalTwinBridge.approve_proactive_remediation(
            db=db,
            incident_id=payload.incident_id,
            approved_by=current_user.username,
            target_replicas=payload.target_replicas,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/proactive-remediation/reject")
def reject_proactive_remediation_endpoint(
    payload: ProactiveRemediationRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    current_tenant: Organization = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Reject or defer a proactive pre-scaling recommendation.
    Protected by ADMIN RBAC. Updates incident to OPEN without executing changes.
    """
    inc = db.query(Incident).filter(Incident.id == payload.incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {payload.incident_id} not found.")
    if inc.tenant_id and inc.tenant_id != current_tenant.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Cross-tenant incident rejection denied.")

    try:
        res = AegisOpsDigitalTwinBridge.reject_proactive_remediation(
            db=db,
            incident_id=payload.incident_id,
            rejected_by=current_user.username,
            reason=payload.reason or "Admin deferred proactive pre-scaling",
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/proactive-remediation/cancel")
def cancel_proactive_remediation_endpoint(
    payload: ProactiveRemediationCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    current_tenant: Organization = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Cancel an active proactive mitigation workflow with audit trail.
    """
    inc = db.query(Incident).filter(Incident.id == payload.incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {payload.incident_id} not found.")
    if inc.tenant_id and inc.tenant_id != current_tenant.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Cross-tenant incident cancel denied.")

    try:
        res = AegisOpsDigitalTwinBridge.cancel_proactive_remediation(
            db=db,
            incident_id=payload.incident_id,
            canceled_by=current_user.username,
            reason=payload.reason or "Operator canceled proactive action",
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

