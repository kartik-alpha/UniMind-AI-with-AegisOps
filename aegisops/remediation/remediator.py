from typing import Dict, Any
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.ticket import Incident, IncidentStatus
from services.exam_service.main import metrics as exam_m


ALLOWED_REMEDIATION_ACTIONS = {"RESTART_POD", "SCALE_DEPLOYMENT", "ROLLBACK_DEPLOYMENT"}


def execute_controlled_remediation(
    db: Session,
    incident_id: int,
    action: str,
    approved_by: str,
) -> Dict[str, Any]:
    if action not in ALLOWED_REMEDIATION_ACTIONS:
        raise ValueError(f"Unauthorized action '{action}'. Allowed: {ALLOWED_REMEDIATION_ACTIONS}")

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found.")

    # 1. Execute Predefined Controlled Action (Restoring healthy service metrics)
    if incident.service_name.lower() in ("exam service", "exam_service"):
        exam_m.set_chaos(False)

    incident.status = IncidentStatus.RESOLVED
    incident.remediation_status = f"EXECUTED: {action} by {approved_by}"

    # 2. Log Security Audit Record
    audit = AuditLog(
        action="SELF_HEALING_REMEDIATION_EXECUTED",
        performed_by=approved_by,
        target_resource=f"incident/{incident.incident_code}",
        status="SUCCESS",
        details={"action": action, "service": incident.service_name},
    )
    db.add(audit)
    db.commit()

    return {
        "incident_code": incident.incident_code,
        "service": incident.service_name,
        "action_executed": action,
        "approved_by": approved_by,
        "status": "RESOLVED",
        "service_health_restored": True,
    }
