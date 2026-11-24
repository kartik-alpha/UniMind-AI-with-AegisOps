import re
from typing import Dict, Any, List, Optional
from incident_rag.documents.runbooks import RUNBOOKS_KNOWLEDGE

MICROSERVICE_TOPOLOGY: Dict[str, Dict[str, Any]] = {
    "exam_service": {
        "tier": "Tier-1 (Mission Critical)",
        "upstream_dependencies": ["database_cluster", "auth_service"],
        "downstream_dependents": ["student_portal"],
        "critical_path": True,
    },
    "lms": {
        "tier": "Tier-1 (Mission Critical)",
        "upstream_dependencies": ["database_cluster", "auth_service"],
        "downstream_dependents": ["student_portal"],
        "critical_path": True,
    },
    "student_portal": {
        "tier": "Tier-0 (Edge Gateway)",
        "upstream_dependencies": ["exam_service", "lms", "library_service", "auth_service"],
        "downstream_dependents": ["end_users"],
        "critical_path": True,
    },
    "library_service": {
        "tier": "Tier-2 (Internal Business)",
        "upstream_dependencies": ["database_cluster"],
        "downstream_dependents": ["student_portal"],
        "critical_path": False,
    },
    "auth_service": {
        "tier": "Tier-0 (Security / Identity)",
        "upstream_dependencies": ["database_cluster"],
        "downstream_dependents": ["exam_service", "lms", "student_portal"],
        "critical_path": True,
    },
}


def diagnose_incident(
    service_name: str,
    metrics: Dict[str, Any],
    anomaly_score: float,
    recent_logs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    AI Root Cause Analysis (RCA) Engine.
    Correlates real-time telemetry metrics and Loki logs against codified SRE Runbooks.
    Performs topological dependency tracing and blast radius calculation.
    Separates verified empirical evidence from AI-generated hypotheses.
    """
    recent_logs = recent_logs or []
    clean_svc = service_name.lower().replace(" ", "_")
    scenario = metrics.get("active_scenario") or metrics.get("scenario")
    cpu = metrics.get("cpu_usage_percent", 25.0)
    mem = metrics.get("memory_usage_percent", 40.0)
    lat = metrics.get("latency_ms", 120.0)
    err = metrics.get("error_rate_percent", 0.1)

    # 1. Topological dependency analysis
    topo = MICROSERVICE_TOPOLOGY.get(clean_svc, {
        "tier": "Tier-2 (General)",
        "upstream_dependencies": ["database_cluster"],
        "downstream_dependents": ["student_portal"],
        "critical_path": False,
    })
    impacted_dependents = topo.get("downstream_dependents", [])
    upstream_deps = topo.get("upstream_dependencies", [])
    blast_radius = round(len(impacted_dependents) / 3.0, 2)

    # 2. Correlate runtime logs and stack traces
    stack_trace_found = False
    correlated_log_lines = []
    if recent_logs:
        for l in recent_logs:
            msg = l.get("message", "")
            if l.get("level") in ("ERROR", "CRITICAL", "WARN"):
                correlated_log_lines.append(f"[{l.get('level')}] {msg}")
            if any(term in msg.lower() for term in ["exception", "traceback", "timeout", "refused", "oom"]):
                stack_trace_found = True

    # 3. Match SRE Runbook based on active scenario, log patterns, or symptoms
    matched_runbook = None
    if scenario:
        matched_runbook = next((r for r in RUNBOOKS_KNOWLEDGE if r.get("scenario") == scenario), None)

    if not matched_runbook and recent_logs:
        # Check logs for specific failure signatures
        log_text = " ".join([l.get("message", "") for l in recent_logs]).lower()
        if "pool exhausted" in log_text or "connection timeout" in log_text or "503" in log_text:
            matched_runbook = next((r for r in RUNBOOKS_KNOWLEDGE if r["id"] == "runbook-001"), None)
        elif "oom" in log_text or "garbage collection" in log_text:
            matched_runbook = next((r for r in RUNBOOKS_KNOWLEDGE if r["id"] == "runbook-002"), None)
        elif "throttling" in log_text or "cfs quota" in log_text:
            matched_runbook = next((r for r in RUNBOOKS_KNOWLEDGE if r["id"] == "runbook-003"), None)
        elif "socket" in log_text or "latency degradation" in log_text:
            matched_runbook = next((r for r in RUNBOOKS_KNOWLEDGE if r["id"] == "runbook-004"), None)

    if not matched_runbook:
        if err > 15.0 and cpu > 80.0:
            matched_runbook = next(r for r in RUNBOOKS_KNOWLEDGE if r["id"] == "runbook-006")  # Combined
        elif err > 10.0:
            matched_runbook = next(r for r in RUNBOOKS_KNOWLEDGE if r["id"] == "runbook-001")  # DB Pool / 503
        elif mem > 80.0:
            matched_runbook = next(r for r in RUNBOOKS_KNOWLEDGE if r["id"] == "runbook-002")  # Memory
        elif lat > 1500.0:
            matched_runbook = next(r for r in RUNBOOKS_KNOWLEDGE if r["id"] == "runbook-004")  # Network
        elif cpu > 80.0:
            matched_runbook = next(r for r in RUNBOOKS_KNOWLEDGE if r["id"] == "runbook-003")  # CPU
        else:
            matched_runbook = RUNBOOKS_KNOWLEDGE[0]

    # 4. Formulate Root Cause, Confidence, and Remediation Actions
    runbook_id = matched_runbook.get("id")
    if runbook_id == "runbook-001":
        root_cause = "Database connection pool exhaustion and high query contention during peak concurrent requests."
        recommended_action = "RESTART_POD"
        remediation_detail = "Restart pod to release stale database pool handles & Scale replicas to 4"
        confidence = 0.94 if anomaly_score >= 0.70 else 0.80
    elif runbook_id == "runbook-002":
        root_cause = "In-memory cache buffer exhaustion and garbage collection pause stall (cgroup OOM risk)."
        recommended_action = "RESTART_POD"
        remediation_detail = "Restart pod deployment to flush memory buffers and recover memory headroom"
        confidence = 0.91 if anomaly_score >= 0.70 else 0.76
    elif runbook_id == "runbook-003":
        root_cause = "Compute saturation causing container CFS CPU quota throttling and request queue backlog."
        recommended_action = "SCALE_DEPLOYMENT"
        remediation_detail = "Scale deployment to 4 replicas and perform rolling restart of throttled container"
        confidence = 0.92 if anomaly_score >= 0.70 else 0.78
    elif runbook_id == "runbook-004":
        root_cause = "Cross-service network latency degradation and keep-alive socket exhaustion on RPC bridge."
        recommended_action = "RESTART_POD"
        remediation_detail = "Restart service pod to re-initialize TCP socket connection pools"
        confidence = 0.89 if anomaly_score >= 0.70 else 0.74
    elif runbook_id == "runbook-005":
        root_cause = "HTTP 5xx failure cascade triggered by downstream handler timeout."
        recommended_action = "RESTART_POD"
        remediation_detail = "Restart failing service pod and reset endpoint connection state"
        confidence = 0.90 if anomaly_score >= 0.70 else 0.75
    else:  # Combined
        root_cause = "Critical multivariate infrastructure cascade across compute, memory, and database layers."
        recommended_action = "RESTART_POD"
        remediation_detail = "Emergency rolling pod restart & Scale replicas to 4"
        confidence = 0.96 if anomaly_score >= 0.70 else 0.82

    # Boost confidence if log pattern corroborates metrics
    if stack_trace_found:
        confidence = min(0.99, confidence + 0.03)

    # 5. Verified Empirical Evidence String
    evidence_lines = [
        f"Verified Telemetry: CPU={cpu}%, Memory={mem}%, Latency={lat}ms, Error Rate={err}%, Replicas={metrics.get('replicas', 2)}",
        f"Isolation Forest Anomaly Score: {round(anomaly_score, 2)} (Threshold: 0.70)",
        f"Topological Tier: {topo.get('tier')} | Blast Radius: {blast_radius}",
    ]
    if metrics.get("is_synthetic"):
        evidence_lines.append(f"Source: Synthetic Chaos Injection ({scenario or 'Manual Failure'})")
    else:
        evidence_lines.append("Source: Live Microservice Telemetry Collector")

    if correlated_log_lines:
        evidence_lines.append(f"Correlated Logs ({len(correlated_log_lines)} entries): {'; '.join(correlated_log_lines[:2])}")

    requires_human_approval = (anomaly_score >= 0.70 or topo.get("critical_path", False))

    return {
        "service": service_name,
        "suspected_root_cause": root_cause,
        "evidence": " | ".join(evidence_lines),
        "confidence_score": round(confidence, 2),
        "recommended_remediation": recommended_action,
        "recommended_detail": remediation_detail,
        "matched_runbook_id": matched_runbook["id"],
        "matched_runbook_title": matched_runbook["title"],
        "runbook_summary": matched_runbook["content"].strip(),
        "is_synthetic": metrics.get("is_synthetic", False),
        "topology": {
            "tier": topo.get("tier"),
            "upstream_dependencies": upstream_deps,
            "impacted_dependents": impacted_dependents,
            "blast_radius_score": blast_radius,
            "critical_path": topo.get("critical_path", False),
        },
        "requires_human_approval": requires_human_approval,
    }
