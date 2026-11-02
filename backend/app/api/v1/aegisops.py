from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.ticket import Incident, IncidentSeverity, IncidentStatus
from aegisops.diagnosis.ai_diagnoser import diagnose_incident
from aegisops.remediation.remediator import execute_controlled_remediation
from services.lms.main import metrics as lms_m
from services.student_portal.main import metrics as portal_m
from services.exam_service.main import metrics as exam_m
from services.library_service.main import metrics as lib_m

router = APIRouter(prefix="/aegisops", tags=["AegisOps Engine"])


@router.get("/services")
def get_aegisops_services(current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """
    Get live metrics for all 4 demo university services matching screenshot 2.
    """
    return [
        {
            "name": "LMS",
            "status": lms_m.get_current_metrics()["status"],
            "cpu": f"{int(lms_m.get_current_metrics()['cpu_usage_percent'])}%",
            "memory": f"{int(lms_m.get_current_metrics()['memory_usage_percent'])}%",
            "latency": f"{int(lms_m.get_current_metrics()['latency_ms'])} ms",
            "uptime": "99.98%",
            "request_rate": f"{int(lms_m.get_current_metrics()['request_rate_per_sec'])}/s",
            "error_rate": f"{lms_m.get_current_metrics()['error_rate_percent']}%",
            "replicas": lms_m.replicas,
            "last_incident": "12 days ago",
        },
        {
            "name": "Student Portal",
            "status": portal_m.get_current_metrics()["status"],
            "cpu": f"{int(portal_m.get_current_metrics()['cpu_usage_percent'])}%",
            "memory": f"{int(portal_m.get_current_metrics()['memory_usage_percent'])}%",
            "latency": f"{int(portal_m.get_current_metrics()['latency_ms'])} ms",
            "uptime": "99.95%",
            "request_rate": f"{int(portal_m.get_current_metrics()['request_rate_per_sec'])}/s",
            "error_rate": f"{portal_m.get_current_metrics()['error_rate_percent']}%",
            "replicas": portal_m.replicas,
            "last_incident": "21 days ago",
        },
        {
            "name": "Exam Service",
            "status": exam_m.get_current_metrics()["status"],
            "cpu": f"{int(exam_m.get_current_metrics()['cpu_usage_percent'])}%",
            "memory": f"{int(exam_m.get_current_metrics()['memory_usage_percent'])}%",
            "latency": f"{int(exam_m.get_current_metrics()['latency_ms'])} ms",
            "uptime": "99.41%",
            "request_rate": f"{int(exam_m.get_current_metrics()['request_rate_per_sec'])}/s",
            "error_rate": f"{exam_m.get_current_metrics()['error_rate_percent']}%",
            "replicas": exam_m.replicas,
            "last_incident": "Active",
        },
        {
            "name": "Library Service",
            "status": lib_m.get_current_metrics()["status"],
            "cpu": f"{int(lib_m.get_current_metrics()['cpu_usage_percent'])}%",
            "memory": f"{int(lib_m.get_current_metrics()['memory_usage_percent'])}%",
            "latency": f"{int(lib_m.get_current_metrics()['latency_ms'])} ms",
            "uptime": "99.99%",
            "request_rate": f"{int(lib_m.get_current_metrics()['request_rate_per_sec'])}/s",
            "error_rate": f"{lib_m.get_current_metrics()['error_rate_percent']}%",
            "replicas": lib_m.replicas,
            "last_incident": "6 days ago",
        },
    ]


@router.get("/monitoring")
def get_monitoring_data(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get 15-min time-series monitoring metrics with anomaly marker points matching screenshot 3.
    """
    timestamps = ["12:12", "12:19", "12:26", "12:33", "12:40"]
    return {
        "time_range": "Last 1 hour",
        "cpu_usage": {"current": "93%", "series": [25, 28, 26, 60, 93], "anomaly_indices": [3, 4]},
        "memory_usage": {"current": "82.3%", "series": [40, 42, 40, 65, 82.3], "anomaly_indices": [3, 4]},
        "request_rate": {"current": "2945.1/s", "series": [750, 780, 720, 1500, 2945.1], "anomaly_indices": [3, 4]},
        "latency": {"current": "1695 ms", "series": [120, 115, 125, 850, 1695], "anomaly_indices": [3, 4]},
        "error_rate": {"current": "13.8%", "series": [0.1, 0.1, 0.2, 8.5, 13.8], "anomaly_indices": [3, 4]},
        "timestamps": timestamps,
    }


@router.get("/metrics")
def get_metrics_table(current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """
    Get Prometheus metrics summary table matching screenshot 4.
    """
    return [
        {
            "service": "LMS",
            "cpu": f"{int(lms_m.get_current_metrics()['cpu_usage_percent'])}%",
            "memory": f"{int(lms_m.get_current_metrics()['memory_usage_percent'])}%",
            "requests": f"{int(lms_m.get_current_metrics()['request_rate_per_sec'])}/s",
            "latency": f"{int(lms_m.get_current_metrics()['latency_ms'])} ms",
            "errors": f"{lms_m.get_current_metrics()['error_rate_percent']}%",
            "replicas": lms_m.replicas,
        },
        {
            "service": "Student Portal",
            "cpu": f"{int(portal_m.get_current_metrics()['cpu_usage_percent'])}%",
            "memory": f"{int(portal_m.get_current_metrics()['memory_usage_percent'])}%",
            "requests": f"{int(portal_m.get_current_metrics()['request_rate_per_sec'])}/s",
            "latency": f"{int(portal_m.get_current_metrics()['latency_ms'])} ms",
            "errors": f"{portal_m.get_current_metrics()['error_rate_percent']}%",
            "replicas": portal_m.replicas,
        },
        {
            "service": "Exam Service",
            "cpu": f"{int(exam_m.get_current_metrics()['cpu_usage_percent'])}%",
            "memory": f"{int(exam_m.get_current_metrics()['memory_usage_percent'])}%",
            "requests": f"{int(exam_m.get_current_metrics()['request_rate_per_sec'])}/s",
            "latency": f"{int(exam_m.get_current_metrics()['latency_ms'])} ms",
            "errors": f"{exam_m.get_current_metrics()['error_rate_percent']}%",
            "replicas": exam_m.replicas,
            "is_alert": True,
        },
        {
            "service": "Library Service",
            "cpu": f"{int(lib_m.get_current_metrics()['cpu_usage_percent'])}%",
            "memory": f"{int(lib_m.get_current_metrics()['memory_usage_percent'])}%",
            "requests": f"{int(lib_m.get_current_metrics()['request_rate_per_sec'])}/s",
            "latency": f"{int(lib_m.get_current_metrics()['latency_ms'])} ms",
            "errors": f"{lib_m.get_current_metrics()['error_rate_percent']}%",
            "replicas": lib_m.replicas,
        },
    ]


@router.get("/logs")
def get_loki_logs(
    service: Optional[str] = None,
    level: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    Get centralized Loki logs matching screenshot 5.
    """
    logs = [
        {"timestamp": "12:42:00", "service": "exam-service", "level": "ERROR", "message": "Database connection timeout after 5000ms (pool exhausted)", "trace_id": "a91f3c2e"},
        {"timestamp": "12:42:11", "service": "exam-service", "level": "WARN", "message": "Request latency exceeded threshold: 1834ms > 800ms", "trace_id": "a91f3c40"},
        {"timestamp": "12:42:15", "service": "exam-service", "level": "ERROR", "message": "Request failed with status 503 GET /api/results", "trace_id": "b20d7714"},
        {"timestamp": "12:42:16", "service": "exam-service", "level": "WARN", "message": "CPU throttling detected on pod exam-7d9f-x2k", "trace_id": "-"},
        {"timestamp": "12:42:19", "service": "lms", "level": "INFO", "message": "GET /courses/CS401 200 130ms", "trace_id": "c80e1s02"},
        {"timestamp": "12:42:21", "service": "student-portal", "level": "INFO", "message": "User session refreshed", "trace_id": "d01b4f9a"},
        {"timestamp": "12:42:24", "service": "exam-service", "level": "ERROR", "message": "Upstream timeout from results db", "trace_id": "b20d7790"},
        {"timestamp": "12:42:27", "service": "library", "level": "INFO", "message": "Catalogue search completed 92ms", "trace_id": "e47c2b11"},
        {"timestamp": "12:42:30", "service": "lms", "level": "DEBUG", "message": "Cache hit ratio 0.94", "trace_id": "-"},
        {"timestamp": "12:42:33", "service": "exam-service", "level": "WARN", "message": "Queue depth 1,240 requests", "trace_id": "-"},
    ]

    if service and service.lower() != "all services":
        logs = [l for l in logs if service.lower() in l["service"].lower()]
    if level and level.lower() != "all levels":
        logs = [l for l in logs if l["level"].lower() == level.lower()]

    return logs


@router.post("/diagnose/{service_name}")
def get_ai_diagnosis(service_name: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Run AI Root Cause Analysis for a degraded service.
    """
    m = exam_m.get_current_metrics() if "exam" in service_name.lower() else lms_m.get_current_metrics()
    return diagnose_incident(service_name=service_name, metrics=m, anomaly_score=0.91)


@router.post("/remediate")
def trigger_remediation(
    incident_id: int,
    action: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """
    Execute human-approved controlled self-healing remediation.
    Restricted to ADMIN role.
    """
    return execute_controlled_remediation(
        db=db, incident_id=incident_id, action=action, approved_by=current_user.username
    )


@router.get("/overview")
def get_aegisops_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get full AegisOps infrastructure overview statistics.
    """
    active_incidents = db.query(Incident).filter(Incident.status == IncidentStatus.ACTIVE).all()
    chaos_active = exam_m._chaos_active
    return {
        "cluster_name": "unimind-prod-us-east-1",
        "cluster_status": "Degraded" if (chaos_active or len(active_incidents) > 0) else "Healthy",
        "health_score": 75 if chaos_active else 100,
        "active_incidents": len(active_incidents),
        "total_services": 4,
        "degraded_services": 1 if chaos_active else 0,
        "mttd": "1.2m",
        "mttr": "3.4m",
        "chaos_active": chaos_active,
        "anomaly_score": 0.91 if chaos_active else 0.12,
        "active_incident_details": [
            {
                "id": inc.id,
                "incident_code": inc.incident_code,
                "service": inc.service_name,
                "title": inc.title,
                "severity": inc.severity.value if hasattr(inc.severity, "value") else str(inc.severity),
                "status": inc.status.value if hasattr(inc.status, "value") else str(inc.status),
                "created_at": inc.created_at.strftime("%H:%M:%S") if inc.created_at else "Just now",
            }
            for inc in active_incidents
        ],
    }


@router.post("/chaos/toggle")
def toggle_chaos(
    enable: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Toggle chaos engineering simulation on Exam Service.
    """
    if enable is None:
        new_state = not exam_m._chaos_active
    else:
        new_state = enable

    exam_m.set_chaos(new_state)
    return {
        "chaos_active": exam_m._chaos_active,
        "message": f"Chaos simulation {'ENABLED' if exam_m._chaos_active else 'DISABLED'}. Exam service is now {'degraded' if exam_m._chaos_active else 'healthy'}.",
    }


@router.get("/kubernetes/status")
def get_kubernetes_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get live Kubernetes deployment and pod status for the AegisOps cluster.
    """
    chaos = exam_m._chaos_active
    return {
        "namespace": "unimind-aegisops",
        "cluster_version": "v1.28.4-gke",
        "deployments": [
            {
                "name": "exam-service",
                "ready_replicas": exam_m.replicas,
                "total_replicas": exam_m.replicas,
                "status": "Degraded (Pool Exhausted)" if chaos else "Healthy",
                "image": "unimind/exam-service:latest",
                "cpu_limit": "500m",
                "mem_limit": "512Mi",
            },
            {
                "name": "lms-service",
                "ready_replicas": lms_m.replicas,
                "total_replicas": lms_m.replicas,
                "status": "Healthy",
                "image": "unimind/lms-service:latest",
                "cpu_limit": "1000m",
                "mem_limit": "1024Mi",
            },
            {
                "name": "student-portal",
                "ready_replicas": portal_m.replicas,
                "total_replicas": portal_m.replicas,
                "status": "Healthy",
                "image": "unimind/student-portal:latest",
                "cpu_limit": "500m",
                "mem_limit": "512Mi",
            },
            {
                "name": "library-service",
                "ready_replicas": lib_m.replicas,
                "total_replicas": lib_m.replicas,
                "status": "Healthy",
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
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Simulate pod restart for a service.
    """
    if "exam" in service_name.lower():
        exam_m.set_chaos(False)
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
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Scale deployment replicas for a service.
    """
    if "exam" in service_name.lower():
        exam_m.replicas = replicas
    elif "lms" in service_name.lower():
        lms_m.replicas = replicas
    elif "portal" in service_name.lower():
        portal_m.replicas = replicas
    elif "lib" in service_name.lower():
        lib_m.replicas = replicas

    return {
        "service": service_name,
        "action": "SCALE_DEPLOYMENT",
        "new_replicas": replicas,
        "status": "SUCCESS",
        "message": f"Scaled {service_name} to {replicas} replicas.",
    }

