from typing import Dict, Any, List
from incident_rag.documents.runbooks import RUNBOOKS_KNOWLEDGE


def diagnose_incident(
    service_name: str,
    metrics: Dict[str, Any],
    anomaly_score: float,
    recent_logs: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    recent_logs = recent_logs or []

    # Find relevant runbook
    matched_runbook = next(
        (r for r in RUNBOOKS_KNOWLEDGE if r["service"].lower() in service_name.lower()),
        RUNBOOKS_KNOWLEDGE[0],
    )

    if service_name.lower() in ("exam service", "exam-service"):
        root_cause = "Database connection pool exhaustion and high query contention during peak exam submission load."
        evidence = f"CPU={metrics.get('cpu_usage_percent', 92.0)}%, Latency={metrics.get('latency_ms', 1800)}ms, Error Rate={metrics.get('error_rate_percent', 14.0)}%, Anomaly Score={anomaly_score}"
        recommended_action = "Scale Exam Service replicas to 4 & Restart degraded pod"
        confidence = 0.88
    else:
        root_cause = f"Unusual load spike detected on {service_name}."
        evidence = f"Anomaly Score={anomaly_score}"
        recommended_action = f"Restart pod deployment for {service_name}"
        confidence = 0.75

    return {
        "service": service_name,
        "suspected_root_cause": root_cause,
        "evidence": evidence,
        "confidence_score": confidence,
        "recommended_remediation": recommended_action,
        "matched_runbook_title": matched_runbook["title"],
        "runbook_summary": matched_runbook["content"].strip(),
    }
