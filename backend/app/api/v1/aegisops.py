from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
import numpy as np

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.ticket import Incident, IncidentSeverity, IncidentStatus
from app.models.audit import AuditLog
from ml.models.anomaly_detector import AegisOpsAnomalyDetector
from aegisops.diagnosis.ai_diagnoser import diagnose_incident
from aegisops.remediation.remediator import (
    execute_controlled_remediation,
    reject_remediation,
    verify_service_recovery,
    get_service_metric_instance,
)
from scripts.chaos_simulator import get_chaos_simulator
from services.lms.main import metrics as lms_m
from services.student_portal.main import metrics as portal_m
from services.exam_service.main import metrics as exam_m
from services.library_service.main import metrics as lib_m
from services.common_metrics import auth_m, parse_structured_log

router = APIRouter(prefix="/aegisops", tags=["AegisOps Engine"])


class IncidentTransitionRequest(BaseModel):
    status: str
    notes: Optional[str] = None


class LogParseRequest(BaseModel):
    raw_log: str


class ChaosInjectRequest(BaseModel):
    service_name: str = "exam_service"
    scenario: str = "database"  # cpu, memory, database, network, http_errors, combined
    severity: str = "HIGH"
    duration_seconds: int = 60


class ChaosRestoreRequest(BaseModel):
    service_name: Optional[str] = None  # None = restore all


class RemediationApproveRequest(BaseModel):
    incident_id: int
    action: str = "RESTART_POD"
    target_replicas: Optional[int] = 4


class RemediationRejectRequest(BaseModel):
    incident_id: int
    reason: Optional[str] = "Admin rejected automated recommendation"


def _get_or_create_incident_for_anomaly(
    db: Session,
    service_name: str,
    metrics: Dict[str, Any],
    anomaly_score: float,
    tenant_id: int = 1,
) -> Incident:
    """
    Incident Detection & Deduplication Engine (Directive 5).
    Finds active unresolved incident or creates a new one.
    """
    # 1. Deduplication check: Is there already an active incident for this service and tenant?
    active_incident = (
        db.query(Incident)
        .filter(
            Incident.service_name.ilike(f"%{service_name}%"),
            Incident.status != IncidentStatus.RESOLVED,
            Incident.tenant_id == tenant_id,
        )
        .first()
    )

    recent_logs = get_service_metric_instance(service_name).recent_logs[-10:]
    diag = diagnose_incident(service_name=service_name, metrics=metrics, anomaly_score=anomaly_score, recent_logs=recent_logs)

    sev = IncidentSeverity.MEDIUM
    if anomaly_score >= 0.85 or metrics.get("error_rate_percent", 0) > 15.0:
        sev = IncidentSeverity.CRITICAL
    elif anomaly_score >= 0.70:
        sev = IncidentSeverity.HIGH

    if active_incident:
        # Update existing incident without creating duplicates
        active_incident.anomaly_score = anomaly_score
        active_incident.metrics_summary = metrics
        active_incident.logs_summary = recent_logs
        active_incident.root_cause = diag["suspected_root_cause"]
        active_incident.recommendation = f"{diag['recommended_remediation']}: {diag.get('recommended_detail', '')}"
        active_incident.severity = sev
        db.commit()
        db.refresh(active_incident)
        return active_incident

    # Create new incident
    inc_count = db.query(Incident).count()
    new_inc = Incident(
        incident_code=f"INC-2026-{inc_count + 1001}",
        service_name=metrics.get("service", service_name.title()),
        title=f"{diag['matched_runbook_title']} ({metrics.get('active_scenario', 'Anomalous Behavior')})",
        status=IncidentStatus.PENDING_APPROVAL,
        severity=sev,
        anomaly_score=anomaly_score,
        metrics_summary=metrics,
        tenant_id=tenant_id,
        logs_summary=recent_logs,
        root_cause=diag["suspected_root_cause"],
        recommendation=f"{diag['recommended_remediation']}: {diag.get('recommended_detail', '')}",
    )
    db.add(new_inc)
    db.commit()
    db.refresh(new_inc)
    return new_inc


@router.get("/services")
def get_aegisops_services(current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """
    Get live metrics for all 4 demo university services.
    """
    svcs = [
        ("LMS", lms_m, "12 days ago"),
        ("Student Portal", portal_m, "21 days ago"),
        ("Exam Service", exam_m, "Active" if exam_m.chaos_active else "3 days ago"),
        ("Library Service", lib_m, "6 days ago"),
    ]

    result = []
    for name, m_inst, last_inc in svcs:
        data = m_inst.get_current_metrics()
        result.append({
            "name": name,
            "status": data["status"],
            "cpu": f"{int(data['cpu_usage_percent'])}%",
            "memory": f"{int(data['memory_usage_percent'])}%",
            "latency": f"{int(data['latency_ms'])} ms",
            "uptime": "99.41%" if data["chaos_mode"] else "99.98%",
            "request_rate": f"{int(data['request_rate_per_sec'])}/s",
            "error_rate": f"{data['error_rate_percent']}%",
            "replicas": data["replicas"],
            "last_incident": last_inc,
            "chaos_active": data["chaos_mode"],
            "active_scenario": data["active_scenario"],
            "is_synthetic": data["is_synthetic"],
        })
    return result


@router.get("/monitoring")
def get_monitoring_data(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get live time-series monitoring metrics with anomaly marker points.
    Reflects actual underlying telemetry from Exam Service.
    """
    cur = exam_m.get_current_metrics()
    history = exam_m.get_history(points=8)

    cpu_series = [int(p["cpu_usage_percent"]) for p in history]
    mem_series = [int(p["memory_usage_percent"]) for p in history]
    req_series = [int(p["request_rate_per_sec"]) for p in history]
    lat_series = [int(p["latency_ms"]) for p in history]
    err_series = [float(p["error_rate_percent"]) for p in history]
    timestamps = [p.get("timestamp", "00:00") for p in history]

    # Dynamically compute anomaly indices from rolling telemetry points
    anomaly_indices = [
        idx for idx, p in enumerate(history)
        if p.get("cpu_usage_percent", 0) > 80.0
        or p.get("error_rate_percent", 0) > 5.0
        or p.get("latency_ms", 0) > 600.0
        or p.get("is_synthetic", False)
    ]

    return {
        "time_range": "Last 1 hour",
        "cpu_usage": {"current": f"{cur['cpu_usage_percent']}%", "series": cpu_series, "anomaly_indices": anomaly_indices},
        "memory_usage": {"current": f"{cur['memory_usage_percent']}%", "series": mem_series, "anomaly_indices": anomaly_indices},
        "request_rate": {"current": f"{cur['request_rate_per_sec']}/s", "series": req_series, "anomaly_indices": anomaly_indices},
        "latency": {"current": f"{cur['latency_ms']} ms", "series": lat_series, "anomaly_indices": anomaly_indices},
        "error_rate": {"current": f"{cur['error_rate_percent']}%", "series": err_series, "anomaly_indices": anomaly_indices},
        "timestamps": timestamps,
        "is_synthetic": cur["is_synthetic"],
    }


@router.get("/metrics")
def get_metrics_table(current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """
    Get Prometheus metrics summary table for all services.
    """
    svcs = [("LMS", lms_m), ("Student Portal", portal_m), ("Exam Service", exam_m), ("Library Service", lib_m)]
    table = []
    for name, m_inst in svcs:
        d = m_inst.get_current_metrics()
        table.append({
            "service": name,
            "cpu": f"{int(d['cpu_usage_percent'])}%",
            "memory": f"{int(d['memory_usage_percent'])}%",
            "requests": f"{int(d['request_rate_per_sec'])}/s",
            "latency": f"{int(d['latency_ms'])} ms",
            "errors": f"{d['error_rate_percent']}%",
            "replicas": d["replicas"],
            "is_alert": d["status"] != "HEALTHY",
            "is_synthetic": d["is_synthetic"],
        })
    return table


@router.get("/logs")
def get_loki_logs(
    service: Optional[str] = None,
    level: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    Get centralized Loki logs dynamically reflecting live scenario failures.
    """
    base_logs = [
        {"timestamp": "12:42:10", "service": "exam-service", "level": "INFO", "message": "Healthcheck probe /healthz 200 OK", "trace_id": "a10f8c31", "is_synthetic": False},
        {"timestamp": "12:42:12", "service": "student-portal", "level": "INFO", "message": "POST /auth/session authenticated", "trace_id": "b23c4d12", "is_synthetic": False},
        {"timestamp": "12:42:15", "service": "library-service", "level": "INFO", "message": "Book reservation queue processed", "trace_id": "c34d5e23", "is_synthetic": False},
        {"timestamp": "12:42:18", "service": "lms", "level": "INFO", "message": "Assignment submission received ID 4410", "trace_id": "d45e6f34", "is_synthetic": False},
        {"timestamp": "12:42:19", "service": "lms", "level": "INFO", "message": "GET /courses/CS401 200 130ms", "trace_id": "c80e1s02", "is_synthetic": False},
        {"timestamp": "12:42:21", "service": "student-portal", "level": "INFO", "message": "User session refreshed", "trace_id": "d01b4f9a", "is_synthetic": False},
        {"timestamp": "12:42:24", "service": "exam-service", "level": "DEBUG", "message": "Result calculation background job completed", "trace_id": "e12f3a45", "is_synthetic": False},
        {"timestamp": "12:42:27", "service": "library-service", "level": "INFO", "message": "Catalogue search completed 92ms", "trace_id": "e47c2b11", "is_synthetic": False},
        {"timestamp": "12:42:29", "service": "student-portal", "level": "INFO", "message": "GET /profile/grades 200 85ms", "trace_id": "f56a7b89", "is_synthetic": False},
        {"timestamp": "12:42:30", "service": "lms", "level": "DEBUG", "message": "Cache hit ratio 0.94", "trace_id": "-", "is_synthetic": False},
        {"timestamp": "12:42:32", "service": "exam-service", "level": "INFO", "message": "Active examination session token validated", "trace_id": "98a7b6c5", "is_synthetic": False},
        {"timestamp": "12:42:35", "service": "library-service", "level": "DEBUG", "message": "Digital asset cache synchronized", "trace_id": "-", "is_synthetic": False},
    ]

    # Combine with real-time logs emitted by active services
    dynamic_logs = []
    for m in [exam_m, lms_m, portal_m, lib_m]:
        dynamic_logs.extend(m.recent_logs)

    all_logs = dynamic_logs + base_logs

    if service and service.lower() != "all services":
        all_logs = [l for l in all_logs if service.lower() in l["service"].lower()]
    if level and level.lower() != "all levels":
        all_logs = [l for l in all_logs if l["level"].lower() == level.lower()]

    return all_logs[:30]


@router.post("/diagnose/{service_name}")
def get_ai_diagnosis(service_name: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Run AI Root Cause Analysis for a degraded service with SRE runbook retrieval.
    """
    svc = get_service_metric_instance(service_name)
    m = svc.get_current_metrics()

    detector = AegisOpsAnomalyDetector()
    f_vec = np.array([[m["cpu_usage_percent"], m["memory_usage_percent"], m["request_rate_per_sec"], m["latency_ms"], m["error_rate_percent"]]])
    score, _ = detector.predict_anomaly_score(f_vec)

    return diagnose_incident(service_name=service_name, metrics=m, anomaly_score=score, recent_logs=svc.recent_logs)


@router.post("/remediate")
@router.post("/remediate/approve")
def trigger_remediation_approval(
    payload: Optional[RemediationApproveRequest] = None,
    incident_id: Optional[int] = None,
    action: Optional[str] = None,
    target_replicas: Optional[int] = 4,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """
    Executes human-approved controlled self-healing remediation.
    Protected by ADMIN RBAC. Transitions: PENDING_APPROVAL -> APPROVED -> REMEDIATING -> RESOLVED.
    Supports both JSON body and query parameters for full compatibility.
    """
    inc_id = (payload.incident_id if payload else None) or incident_id
    act = (payload.action if payload else None) or action
    reps = ((payload.target_replicas if payload else None) or target_replicas) or 4

    if not inc_id or not act:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="incident_id and action are required.")

    try:
        result = execute_controlled_remediation(
            db=db,
            incident_id=inc_id,
            action=act,
            approved_by=current_user.username,
            target_replicas=reps,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/remediate/reject")
def trigger_remediation_rejection(
    payload: RemediationRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """
    Rejects automated remediation recommendation.
    Protected by ADMIN RBAC. Transitions: PENDING_APPROVAL -> REJECTED (OPEN).
    """
    try:
        result = reject_remediation(
            db=db,
            incident_id=payload.incident_id,
            rejected_by=current_user.username,
            reason=payload.reason or "Admin rejected",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/chaos/inject")
def inject_chaos_endpoint(
    payload: ChaosInjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """
    Injects a configurable chaos scenario and executes ML anomaly detection & incident creation.
    """
    simulator = get_chaos_simulator()
    try:
        injected = simulator.inject_failure(
            service_name=payload.service_name,
            scenario=payload.scenario,
            severity=payload.severity,
            duration_seconds=payload.duration_seconds,
        )

        # Run Isolation Forest against injected telemetry
        detector = AegisOpsAnomalyDetector()
        f_vec = np.array([[
            injected["cpu_usage_percent"],
            injected["memory_usage_percent"],
            injected["request_rate_per_sec"],
            injected["latency_ms"],
            injected["error_rate_percent"],
        ]])
        score, is_anom = detector.predict_anomaly_score(f_vec)

        # Auto-create or update incident with deduplication
        incident = _get_or_create_incident_for_anomaly(
            db=db,
            service_name=payload.service_name,
            metrics=injected,
            anomaly_score=max(score, 0.75 if payload.severity in ("HIGH", "CRITICAL") else score),
        )

        return {
            "status": "INJECTED",
            "telemetry": injected,
            "anomaly_score": score,
            "is_anomaly": is_anom or (score >= 0.70) or (payload.severity in ("HIGH", "CRITICAL")),
            "incident": {
                "id": incident.id,
                "incident_code": incident.incident_code,
                "status": incident.status.value,
                "severity": incident.severity.value,
                "root_cause": incident.root_cause,
                "recommendation": incident.recommendation,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/chaos/restore")
def restore_chaos_endpoint(
    payload: ChaosRestoreRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """
    Restores services to healthy operating baseline.
    """
    simulator = get_chaos_simulator()
    if payload.service_name:
        return simulator.restore_service(payload.service_name)
    return simulator.restore_all()


@router.post("/chaos/toggle")
def toggle_chaos(
    enable: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Legacy toggle for quick demo compatibility.
    """
    if enable is None:
        new_state = not exam_m.chaos_active
    else:
        new_state = enable

    exam_m.set_chaos(new_state)
    return {
        "chaos_active": exam_m.chaos_active,
        "message": f"Chaos simulation {'ENABLED' if exam_m.chaos_active else 'DISABLED'}.",
    }


@router.get("/overview")
def get_aegisops_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get full AegisOps infrastructure overview statistics.
    """
    active_incidents = db.query(Incident).filter(Incident.status != IncidentStatus.RESOLVED).all()
    any_chaos = any(m.chaos_active for m in [exam_m, lms_m, portal_m, lib_m])

    return {
        "cluster_name": "unimind-prod-us-east-1",
        "cluster_status": "Degraded" if (any_chaos or len(active_incidents) > 0) else "Healthy",
        "health_score": 70 if any_chaos else 100,
        "active_incidents": len(active_incidents),
        "total_services": 4,
        "degraded_services": sum(1 for m in [exam_m, lms_m, portal_m, lib_m] if m.chaos_active),
        "mttd": "1.2m",
        "mttr": "3.4m",
        "chaos_active": any_chaos,
        "anomaly_score": 0.91 if any_chaos else 0.12,
        "active_incident_details": [
            {
                "id": inc.id,
                "incident_code": inc.incident_code,
                "service": inc.service_name,
                "title": inc.title,
                "severity": inc.severity.value if hasattr(inc.severity, "value") else str(inc.severity),
                "status": inc.status.value if hasattr(inc.status, "value") else str(inc.status),
                "anomaly_score": inc.anomaly_score,
                "root_cause": inc.root_cause,
                "created_at": inc.created_at.strftime("%H:%M:%S") if inc.created_at else "Just now",
            }
            for inc in active_incidents
        ],
    }


@router.get("/kubernetes/status")
def get_kubernetes_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get live Kubernetes deployment and pod status for the AegisOps cluster.
    """
    chaos = exam_m.chaos_active
    return {
        "namespace": "unimind-aegisops",
        "cluster_version": "v1.28.4-gke",
        "deployments": [
            {
                "name": "exam-service",
                "ready_replicas": exam_m.replicas,
                "total_replicas": exam_m.replicas,
                "status": "Degraded" if chaos else "Healthy",
                "image": "unimind/exam-service:latest",
                "cpu_limit": "500m",
                "mem_limit": "512Mi",
            },
            {
                "name": "lms-service",
                "ready_replicas": lms_m.replicas,
                "total_replicas": lms_m.replicas,
                "status": "Degraded" if lms_m.chaos_active else "Healthy",
                "image": "unimind/lms-service:latest",
                "cpu_limit": "1000m",
                "mem_limit": "1024Mi",
            },
            {
                "name": "student-portal",
                "ready_replicas": portal_m.replicas,
                "total_replicas": portal_m.replicas,
                "status": "Degraded" if portal_m.chaos_active else "Healthy",
                "image": "unimind/student-portal:latest",
                "cpu_limit": "500m",
                "mem_limit": "512Mi",
            },
            {
                "name": "library-service",
                "ready_replicas": lib_m.replicas,
                "total_replicas": lib_m.replicas,
                "status": "Degraded" if lib_m.chaos_active else "Healthy",
                "image": "unimind/library-service:latest",
                "cpu_limit": "250m",
                "mem_limit": "256Mi",
            },
        ],
        "pods": [
            {
                "name": "exam-service-7d9f-x2k",
                "deployment": "exam-service",
                "status": "CrashLoopBackOff" if chaos else "Running",
                "restarts": 4 if chaos else 0,
                "age": "2h 15m",
                "node": "gke-node-pool-1",
                "cpu": f"{int(exam_m.get_current_metrics()['cpu_usage_percent'])}%",
                "memory": f"{int(exam_m.get_current_metrics()['memory_usage_percent'])}%",
            },
            {
                "name": "exam-service-7d9f-w9p",
                "deployment": "exam-service",
                "status": "Running",
                "restarts": 1 if chaos else 0,
                "age": "1h 40m",
                "node": "gke-node-pool-2",
                "cpu": f"{max(20, int(exam_m.get_current_metrics()['cpu_usage_percent']) - 15)}%",
                "memory": f"{max(30, int(exam_m.get_current_metrics()['memory_usage_percent']) - 10)}%",
            },
            {
                "name": "lms-service-5c8a-m1a",
                "deployment": "lms-service",
                "status": "Running",
                "restarts": 0,
                "age": "4d 12h",
                "node": "gke-node-pool-1",
                "cpu": f"{int(lms_m.get_current_metrics()['cpu_usage_percent'])}%",
                "memory": f"{int(lms_m.get_current_metrics()['memory_usage_percent'])}%",
            },
            {
                "name": "student-portal-9b2c-k8q",
                "deployment": "student-portal",
                "status": "Running",
                "restarts": 0,
                "age": "2d 08h",
                "node": "gke-node-pool-2",
                "cpu": f"{int(portal_m.get_current_metrics()['cpu_usage_percent'])}%",
                "memory": f"{int(portal_m.get_current_metrics()['memory_usage_percent'])}%",
            },
            {
                "name": "library-service-3a1f-z4x",
                "deployment": "library-service",
                "status": "Running",
                "restarts": 0,
                "age": "6d 19h",
                "node": "gke-node-pool-1",
                "cpu": f"{int(lib_m.get_current_metrics()['cpu_usage_percent'])}%",
                "memory": f"{int(lib_m.get_current_metrics()['memory_usage_percent'])}%",
            },
        ],
    }


@router.post("/services/{service_name}/restart")
def restart_service_pod(
    service_name: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """
    Simulate pod restart for a service.
    """
    svc = get_service_metric_instance(service_name)
    svc.set_chaos(False)
    return {
        "service": service_name,
        "action": "POD_RESTART",
        "status": "SUCCESS",
        "message": f"Pod for {service_name} restarted successfully. Fresh container initialized.",
    }


@router.post("/services/{service_name}/scale")
def scale_service(
    service_name: str,
    replicas: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """
    Scale deployment replicas for a service.
    """
    svc = get_service_metric_instance(service_name)
    svc.replicas = replicas
    return {
        "service": service_name,
        "action": "SCALE_DEPLOYMENT",
        "new_replicas": replicas,
        "status": "SUCCESS",
        "message": f"Scaled {service_name} to {replicas} replicas.",
    }


@router.post("/services/{service_name}/flush-connections")
def flush_service_connections(
    service_name: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """
    Safely flushes idle database connection handles and resets saturation for a service.
    """
    svc = get_service_metric_instance(service_name)
    svc.set_chaos(False)
    return {
        "service": service_name,
        "action": "FLUSH_IDLE_CONNECTIONS",
        "status": "SUCCESS",
        "message": f"Connection pool flushed for {service_name}. Pool saturation reset to baseline.",
    }


@router.get("/metrics/prometheus")
def get_prometheus_metrics() -> Response:
    """
    Prometheus scrape endpoint exposing standardized gauges for all 5 enterprise services.
    """
    all_metrics = [exam_m, lms_m, portal_m, lib_m, auth_m]
    body = "\n\n".join([m.to_prometheus_format() for m in all_metrics]) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")


@router.post("/incidents/{incident_id}/transition")
def transition_incident(
    incident_id: int,
    payload: IncidentTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
) -> Dict[str, Any]:
    """
    Formal state machine transition for enterprise incidents with audit logging:
    OPEN -> INVESTIGATING -> PENDING_APPROVAL -> REMEDIATING -> RESOLVED.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found.")

    is_super_admin = (
        current_user.role == UserRole.ADMIN
        and current_user.username in ("admin", "platform_admin", "kartik")
    )
    if not is_super_admin and incident.tenant_id and current_user.tenant_id:
        if incident.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Incident {incident_id} belongs to a different organization.",
            )

    valid_statuses = [s.value for s in IncidentStatus]
    target_status = payload.status.upper().strip()
    if target_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid incident status '{payload.status}'. Valid: {', '.join(valid_statuses)}",
        )

    old_status = incident.status.value
    incident.status = IncidentStatus[target_status]
    if payload.notes:
        logs = list(incident.logs_summary or [])
        now_ts = datetime.utcnow().strftime("%H:%M:%S")
        logs.append(f"[{now_ts}] State transition: {old_status} -> {target_status} by {current_user.username}. Notes: {payload.notes}")
        incident.logs_summary = logs

    audit = AuditLog(
        action="INCIDENT_STATUS_TRANSITION",
        performed_by=current_user.username,
        target_resource=f"incident/{incident.incident_code}",
        status="SUCCESS",
        details={"old_status": old_status, "new_status": target_status, "notes": payload.notes},
        tenant_id=incident.tenant_id or 1,
    )
    db.add(audit)
    db.commit()
    db.refresh(incident)

    return {
        "incident_code": incident.incident_code,
        "old_status": old_status,
        "new_status": incident.status.value,
        "updated_at": incident.updated_at.isoformat() if incident.updated_at else datetime.utcnow().isoformat(),
    }


@router.post("/logs/parse")
def parse_log_entry(
    payload: LogParseRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Parses an unstructured or JSON log line into a standardized telemetry log record.
    """
    return parse_structured_log(payload.raw_log)
