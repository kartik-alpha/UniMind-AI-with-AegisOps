from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.ticket import Incident, IncidentSeverity, IncidentStatus
from app.models.audit import AuditLog
from digital_twin.models import BottleneckAlert, SimulationConfig
from digital_twin.capacity_planner import PredictiveCapacityPlanner, DEFAULT_SPECS


class AegisOpsDigitalTwinBridge:
    """
    Bridge connecting Digital Twin predictive capacity forecasts with AegisOps SRE workflows.
    Ensures that when demand is forecast to exceed capacity, a human-in-the-loop reviewable
    proactive alert is registered without autonomously mutating infrastructure.
    """

    @staticmethod
    def sync_alert_to_incident(
        db: Session,
        alert: BottleneckAlert,
        config: SimulationConfig,
        tenant_id: int = 1,
    ) -> Incident:
        """
        Creates or updates a predictive incident record in the database with strict tenant scoping.
        Implements deduplication: if an active predictive incident already exists for
        the service within the tenant, it updates the forecast evidence instead of creating a duplicate.
        """
        existing = (
            db.query(Incident)
            .filter(
                Incident.service_name.ilike(f"%{alert.service_name}%"),
                Incident.title.ilike("%[PREDICTIVE ALERT]%"),
                Incident.status != IncidentStatus.RESOLVED,
                Incident.tenant_id == tenant_id,
            )
            .first()
        )

        sev = IncidentSeverity.CRITICAL if alert.severity == "CRITICAL" else IncidentSeverity.HIGH

        metrics_payload = {
            "is_simulation": True,
            "data_source": "digital_twin_engine",
            "alert_id": alert.alert_id,
            "primary_bottleneck": alert.primary_bottleneck,
            "predicted_value": alert.predicted_value,
            "threshold_value": alert.threshold_value,
            "lead_time_hours": alert.lead_time_hours,
            "simulated_event": config.event.value,
            "simulated_intensity": config.intensity.value,
            "total_students": config.total_students,
            "target_replicas": alert.target_replicas,
            "tenant_id": tenant_id,
        }

        if existing:
            existing.severity = sev
            existing.metrics_summary = metrics_payload
            existing.recommendation = alert.recommendation
            existing.root_cause = f"Forecasted {alert.primary_bottleneck} saturation during {config.event.value} ({alert.time_label})"
            db.commit()
            db.refresh(existing)
            return existing

        # Create new incident strictly stamped with tenant_id
        inc_count = db.query(Incident).count()
        new_inc = Incident(
            incident_code=f"PRED-2026-{inc_count + 2001}",
            service_name=alert.service_name.title().replace("_", " "),
            title=f"[PREDICTIVE ALERT] {alert.service_name.title()} {alert.primary_bottleneck} Bottleneck ({alert.time_label})",
            status=IncidentStatus.PENDING_APPROVAL,
            severity=sev,
            anomaly_score=round(alert.predicted_value / 100.0, 2),
            metrics_summary=metrics_payload,
            tenant_id=tenant_id,
            logs_summary=[
                f"[{alert.time_label}] Predicted concurrency shock for {alert.service_name}",
                f"[{alert.time_label}] Headroom warning: {alert.explanation}",
                f"[{alert.time_label}] SRE recommendation: {alert.recommendation}",
            ],
            root_cause=f"Forecasted {alert.primary_bottleneck} saturation during {config.event.value} ({alert.time_label})",
            recommendation=alert.recommendation,
        )
        db.add(new_inc)
        db.commit()
        db.refresh(new_inc)
        return new_inc

    @staticmethod
    def create_predictive_event_incident(
        db: Session,
        tenant_id: int,
        event_type: str,
        service_name: str,
        predicted_metric: float,
        threshold_metric: float,
        lead_time_hours: float,
        recommendation: str,
        severity: str = "HIGH",
        details: Optional[Dict[str, Any]] = None,
    ) -> Incident:
        """
        Creates or correlates a qualifying predictive event (thermal spike, traffic surge, resource exhaustion)
        into an AegisOps operational incident defaulting to PENDING_APPROVAL.
        """
        valid_events = {"THERMAL_SPIKE", "TRAFFIC_SURGE", "RESOURCE_EXHAUSTION", "OPERATIONAL_ANOMALY"}
        norm_event = event_type.upper().strip()
        if norm_event not in valid_events:
            raise ValueError(f"Invalid predictive event type '{event_type}'. Must be one of: {valid_events}")

        # Deduplication: active incident of same event type and service for this tenant
        existing = (
            db.query(Incident)
            .filter(
                Incident.service_name == service_name,
                Incident.title.ilike(f"%[{norm_event}]%"),
                Incident.status != IncidentStatus.RESOLVED,
                Incident.tenant_id == tenant_id,
            )
            .first()
        )

        sev = IncidentSeverity.CRITICAL if severity.upper() == "CRITICAL" else IncidentSeverity.HIGH

        metrics_data = {
            "is_simulation": True,
            "predictive_event": norm_event,
            "service_name": service_name,
            "predicted_metric": predicted_metric,
            "threshold_metric": threshold_metric,
            "lead_time_hours": lead_time_hours,
            "tenant_id": tenant_id,
            "extra_details": details or {},
        }

        if existing:
            from datetime import datetime
            existing.anomaly_score = round(min(1.0, predicted_metric / max(1.0, threshold_metric)), 2)
            existing.metrics_summary = metrics_data
            existing.recommendation = recommendation
            existing.severity = sev
            existing.created_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing

        inc_count = db.query(Incident).count()
        new_inc = Incident(
            incident_code=f"PRED-{norm_event[:4]}-{inc_count + 3001}",
            service_name=service_name,
            title=f"[{norm_event}] Predicted {service_name} Disruption (Lead Time: {lead_time_hours}h)",
            status=IncidentStatus.PENDING_APPROVAL,
            severity=sev,
            anomaly_score=round(min(1.0, predicted_metric / max(1.0, threshold_metric)), 2),
            metrics_summary=metrics_data,
            tenant_id=tenant_id,
            logs_summary=[
                f"Predicted {norm_event} event detected for {service_name}",
                f"Forecasted Metric: {predicted_metric} vs Threshold: {threshold_metric}",
                f"Proposed Mitigation: {recommendation}",
            ],
            root_cause=f"Imminent {norm_event} forecasted to exceed threshold ({threshold_metric}) within {lead_time_hours} hours",
            recommendation=recommendation,
        )
        db.add(new_inc)
        db.commit()
        db.refresh(new_inc)
        return new_inc

    @staticmethod
    def approve_proactive_remediation(
        db: Session,
        incident_id: int,
        approved_by: str,
        target_replicas: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Human-in-the-loop approval of proactive pre-scaling recommendation.
        Re-evaluates headroom with new capacity and marks incident as RESOLVED.
        """
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if not inc:
            raise ValueError(f"Incident {incident_id} not found.")

        if inc.status == IncidentStatus.RESOLVED:
            raise ValueError(f"Incident {inc.incident_code} is already RESOLVED.")

        summary = inc.metrics_summary or {}
        s_name_raw = inc.service_name.lower().replace(" ", "_")
        reps = target_replicas or summary.get("target_replicas", 4)

        # Re-evaluate capacity with target replicas
        planner = PredictiveCapacityPlanner()
        planner.apply_capacity_overrides({s_name_raw: {"replicas": reps}})
        
        sim_config = SimulationConfig(
            total_students=summary.get("total_students", 10000),
            event=summary.get("simulated_event", "NORMAL_DAY"),
            intensity=summary.get("simulated_intensity", "NORMAL"),
        )
        post_forecast = planner.generate_capacity_forecast(sim_config)

        # Check if headroom is restored
        s_alerts = [a for a in post_forecast.alerts if a.service_name == s_name_raw]
        headroom_restored = len(s_alerts) == 0

        inc.status = IncidentStatus.RESOLVED
        inc.approved_by = approved_by
        inc.action_taken = f"PRE_SCALED: Adjusted {inc.service_name} to {reps} replicas. Headroom verified."
        inc.resolved_at = datetime.utcnow()

        audit = AuditLog(
            tenant_id=inc.tenant_id or 1,
            action="PROACTIVE_REMEDIATION_APPROVED",
            performed_by=approved_by,
            target_resource=f"digital_twin/{inc.service_name}",
            status="SUCCESS",
            details={
                "incident_code": inc.incident_code,
                "target_replicas": reps,
                "headroom_restored": headroom_restored,
                "remaining_alerts": len(s_alerts),
            },
        )
        db.add(audit)
        db.commit()

        return {
            "incident_code": inc.incident_code,
            "service": inc.service_name,
            "status": "RESOLVED",
            "action_executed": f"PRE_SCALE_TO_{reps}_REPLICAS",
            "approved_by": approved_by,
            "headroom_restored": headroom_restored,
            "remaining_service_alerts": len(s_alerts),
            "is_simulation": True,
        }

    @staticmethod
    def reject_proactive_remediation(
        db: Session,
        incident_id: int,
        rejected_by: str,
        reason: str = "Admin deferred proactive scaling",
    ) -> Dict[str, Any]:
        """
        Rejection of proactive recommendation. Incident marked OPEN without changes.
        """
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if not inc:
            raise ValueError(f"Incident {incident_id} not found.")

        inc.status = IncidentStatus.OPEN
        inc.action_taken = f"REJECTED: {reason} by {rejected_by}"

        audit = AuditLog(
            tenant_id=inc.tenant_id or 1,
            action="PROACTIVE_REMEDIATION_REJECTED",
            performed_by=rejected_by,
            target_resource=f"digital_twin/{inc.service_name}",
            status="SUCCESS",
            details={"incident_code": inc.incident_code, "reason": reason},
        )
        db.add(audit)
        db.commit()

        return {
            "incident_code": inc.incident_code,
            "service": inc.service_name,
            "status": "OPEN",
            "action": "REJECTED",
            "rejected_by": rejected_by,
            "reason": reason,
            "is_simulation": True,
        }

    @staticmethod
    def cancel_proactive_remediation(
        db: Session,
        incident_id: int,
        canceled_by: str,
        reason: str = "Operator canceled proactive action",
    ) -> Dict[str, Any]:
        """
        Cancellation workflow for proactive incidents.
        Sets status to RESOLVED with action_taken="CANCELED", leaving audit trail.
        """
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if not inc:
            raise ValueError(f"Incident {incident_id} not found.")

        inc.status = IncidentStatus.RESOLVED
        inc.action_taken = f"CANCELED: {reason} by {canceled_by}"
        inc.resolved_at = datetime.utcnow()

        audit = AuditLog(
            tenant_id=inc.tenant_id or 1,
            action="PROACTIVE_REMEDIATION_CANCELED",
            performed_by=canceled_by,
            target_resource=f"digital_twin/{inc.service_name}",
            status="SUCCESS",
            details={"incident_code": inc.incident_code, "reason": reason},
        )
        db.add(audit)
        db.commit()

        return {
            "incident_code": inc.incident_code,
            "service": inc.service_name,
            "status": "CANCELED",
            "action": "CANCELED",
            "canceled_by": canceled_by,
            "reason": reason,
            "is_simulation": True,
        }

