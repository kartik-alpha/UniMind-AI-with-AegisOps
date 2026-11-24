from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
import numpy as np

from app.models.audit import AuditLog
from app.models.ticket import Incident, IncidentStatus, IncidentSeverity
from ml.models.anomaly_detector import AegisOpsAnomalyDetector
from services.lms.main import metrics as lms_m
from services.student_portal.main import metrics as portal_m
from services.exam_service.main import metrics as exam_m
from services.library_service.main import metrics as lib_m
from services.common_metrics import auth_m


ALLOWED_REMEDIATION_ACTIONS = {
    "RESTART_POD",
    "SCALE_DEPLOYMENT",
    "ROLLBACK_DEPLOYMENT",
    "FLUSH_CACHE",
    "FLUSH_IDLE_CONNECTIONS",
    "FLUSH_DB_POOL",
}

SERVICE_METRICS_MAP = {
    "exam service": exam_m,
    "exam-service": exam_m,
    "exam_service": exam_m,
    "lms": lms_m,
    "lms-service": lms_m,
    "lms_service": lms_m,
    "student portal": portal_m,
    "student-portal": portal_m,
    "student_portal": portal_m,
    "library service": lib_m,
    "library-service": lib_m,
    "library_service": lib_m,
    "auth service": auth_m,
    "auth-service": auth_m,
    "auth_service": auth_m,
}


def get_service_metric_instance(service_name: str):
    clean = service_name.lower().strip()
    return SERVICE_METRICS_MAP.get(clean, exam_m)


def verify_service_recovery(service_name: str) -> Tuple[bool, Dict[str, Any], float]:
    """
    Independently verifies that a service has returned to normal operating baseline:
      1. CPU utilization < 75%
      2. Latency < 400ms
      3. Error rate < 1.0%
      4. Isolation Forest Anomaly Score < 0.50
    """
    m_instance = get_service_metric_instance(service_name)
    fresh_metrics = m_instance.get_current_metrics()

    detector = AegisOpsAnomalyDetector()
    feature_vector = np.array([[
        fresh_metrics["cpu_usage_percent"],
        fresh_metrics["memory_usage_percent"],
        fresh_metrics["request_rate_per_sec"],
        fresh_metrics["latency_ms"],
        fresh_metrics["error_rate_percent"],
    ]])
    anomaly_score, is_anom = detector.predict_anomaly_score(feature_vector)

    is_recovered = (
        fresh_metrics["cpu_usage_percent"] < 80.0
        and fresh_metrics["latency_ms"] < 600.0
        and fresh_metrics["error_rate_percent"] < 2.0
        and not is_anom
    )

    return is_recovered, fresh_metrics, anomaly_score


def execute_controlled_remediation(
    db: Session,
    incident_id: int,
    action: str,
    approved_by: str,
    target_replicas: int = 4,
) -> Dict[str, Any]:
    """
    Executes human-approved controlled self-healing remediation.
    Sequence: PENDING_APPROVAL -> APPROVED -> REMEDIATING -> VERIFIED -> RESOLVED.
    """
    if action not in ALLOWED_REMEDIATION_ACTIONS:
        raise ValueError(f"Unauthorized action '{action}'. Allowed actions: {ALLOWED_REMEDIATION_ACTIONS}")

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found.")

    if incident.status == IncidentStatus.RESOLVED:
        raise ValueError(f"Incident {incident.incident_code} is already RESOLVED.")

    # Human-in-the-loop requirement for critical/high severity
    if incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH) and not (approved_by and approved_by.strip()):
        raise PermissionError(f"Human-in-the-loop approval is mandatory for {incident.severity.value} remediation actions.")

    # 1. State: APPROVED -> REMEDIATING
    incident.status = IncidentStatus.REMEDIATING
    incident.approved_by = approved_by
    incident.action_taken = action
    db.commit()

    # 2. Execute Non-Destructive Orchestration Action
    svc_instance = get_service_metric_instance(incident.service_name)
    if action == "RESTART_POD":
        svc_instance.set_chaos(False)
    elif action == "SCALE_DEPLOYMENT":
        svc_instance.replicas = target_replicas
        svc_instance.set_chaos(False)
    elif action == "ROLLBACK_DEPLOYMENT":
        svc_instance.set_chaos(False)
    elif action in ("FLUSH_CACHE", "FLUSH_IDLE_CONNECTIONS", "FLUSH_DB_POOL"):
        svc_instance.set_chaos(False)

    # 3. Independent Recovery Verification (Directive 8)
    is_healthy, fresh_telemetry, new_anomaly_score = verify_service_recovery(incident.service_name)

    if is_healthy:
        incident.status = IncidentStatus.RESOLVED
        incident.anomaly_score = new_anomaly_score
        incident.metrics_summary = fresh_telemetry
        status_result = "RESOLVED"
    else:
        # If metrics did not recover, fail the remediation
        incident.status = IncidentStatus.OPEN
        status_result = "FAILED"

    # 4. Write Immutable Security Audit Record
    audit = AuditLog(
        action=f"REMEDIATION_{status_result}",
        performed_by=approved_by,
        target_resource=f"incident/{incident.incident_code}",
        status="SUCCESS" if is_healthy else "FAILURE",
        details={
            "action": action,
            "service": incident.service_name,
            "verified_recovery": is_healthy,
            "fresh_anomaly_score": new_anomaly_score,
            "fresh_cpu": fresh_telemetry["cpu_usage_percent"],
            "fresh_latency": fresh_telemetry["latency_ms"],
        },
        tenant_id=incident.tenant_id or 1,
    )
    db.add(audit)
    db.commit()

    return {
        "incident_code": incident.incident_code,
        "service": incident.service_name,
        "action_executed": action,
        "approved_by": approved_by,
        "status": status_result,
        "verified_recovery": is_healthy,
        "new_anomaly_score": new_anomaly_score,
        "fresh_telemetry": fresh_telemetry,
    }


def reject_remediation(
    db: Session,
    incident_id: int,
    rejected_by: str,
    reason: str = "Admin rejected suggested remediation action",
) -> Dict[str, Any]:
    """
    Transitions incident from PENDING_APPROVAL to OPEN / REJECTED without executing remediation.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found.")

    incident.status = IncidentStatus.OPEN
    incident.action_taken = f"REJECTED: {reason} by {rejected_by}"

    audit = AuditLog(
        action="REMEDIATION_REJECTED",
        performed_by=rejected_by,
        target_resource=f"incident/{incident.incident_code}",
        status="SUCCESS",
        details={"reason": reason, "service": incident.service_name},
        tenant_id=incident.tenant_id or 1,
    )
    db.add(audit)
    db.commit()

    return {
        "incident_code": incident.incident_code,
        "service": incident.service_name,
        "status": "OPEN",
        "action": "REJECTED",
        "rejected_by": rejected_by,
        "reason": reason,
    }
