import hashlib
import time
from pathlib import Path
import pytest
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.ticket import Incident, IncidentSeverity, IncidentStatus
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from services.common_metrics import ServiceMetrics, auth_m, parse_structured_log
from services.exam_service.main import metrics as exam_m
from services.lms.main import metrics as lms_m
from services.student_portal.main import metrics as portal_m
from services.library_service.main import metrics as lib_m
from ml.models.anomaly_detector import AegisOpsAnomalyDetector
from ml.inference.detector import evaluate_service_anomaly
from aegisops.diagnosis.ai_diagnoser import diagnose_incident, MICROSERVICE_TOPOLOGY
from aegisops.remediation.remediator import (
    execute_controlled_remediation,
    reject_remediation,
    verify_service_recovery,
    ALLOWED_REMEDIATION_ACTIONS,
)
from scripts.chaos_simulator import ChaosSimulator
from digital_twin.simulator import CampusActivitySimulator
from digital_twin.models import SimulationConfig, AcademicEvent, TrafficIntensity


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_phase_d1_telemetry_harvester_and_prometheus():
    """Test D1: Telemetry ingestion across core microservices and Prometheus export."""
    services = [exam_m, lms_m, portal_m, lib_m, auth_m]
    assert len(services) == 5

    for svc in services:
        m = svc.get_current_metrics()
        assert "cpu_usage_percent" in m
        assert "memory_usage_percent" in m
        assert "latency_ms" in m
        assert "latency_p95_ms" in m
        assert "latency_p99_ms" in m
        assert "db_pool_saturation_percent" in m
        assert "error_rate_percent" in m
        assert "request_rate_per_sec" in m
        assert "replicas" in m
        assert m["replicas"] >= 1
        assert m["latency_p95_ms"] >= m["latency_ms"]
        assert m["latency_p99_ms"] >= m["latency_p95_ms"]

        # Verify Prometheus format export
        prom = svc.to_prometheus_format()
        assert f'university_service_cpu_percent{{service="{svc.service_name}"' in prom
        assert f'university_service_latency_p95_ms{{service="{svc.service_name}"' in prom
        assert f'university_service_db_pool_saturation_percent{{service="{svc.service_name}"' in prom

    # Test structured log parser
    json_log = '{"time": "14:20:00", "severity": "ERROR", "app": "exam-service", "msg": "Database connection pool timeout", "traceId": "abc123"}'
    parsed_json = parse_structured_log(json_log)
    assert parsed_json["level"] == "ERROR"
    assert parsed_json["service"] == "exam-service"
    assert "Database connection pool timeout" in parsed_json["message"]

    raw_log = "[14:22:15] [WARN] [student-portal] High latency detected on RPC gateway"
    parsed_raw = parse_structured_log(raw_log)
    assert parsed_raw["level"] == "WARN"
    assert parsed_raw["service"] == "student-portal"
    assert "High latency detected" in parsed_raw["message"]


def test_phase_d2_isolation_forest_checksum_and_dampening():
    """Test D2: Isolation Forest model checksum invariant and dynamic baseline dampening."""
    # 1. Model Checksum Invariant
    model_path = Path("ml/models/isolation_forest.joblib")
    assert model_path.exists(), "Isolation forest model file missing"
    hasher = hashlib.sha256(model_path.read_bytes())
    model_sha256 = hasher.hexdigest().upper()
    assert model_sha256 == "C2715221415485B2C3956F71625D244D554281A44911F1D49FE8B0C170FF5B20"

    # 2. Normal baseline evaluation
    normal_metrics = {
        "service": "LMS",
        "cpu_usage_percent": 24.5,
        "memory_usage_percent": 38.0,
        "request_rate_per_sec": 320.0,
        "latency_ms": 115.0,
        "error_rate_percent": 0.05,
        "chaos_mode": False,
        "is_synthetic": False,
    }
    eval_res = evaluate_service_anomaly(normal_metrics)
    assert eval_res["is_anomaly"] is False
    assert eval_res["anomaly_score"] < 0.70
    assert eval_res["status_label"] == "NORMAL"

    # 3. Anomaly condition evaluation
    spike_metrics = {
        "service": "LMS",
        "cpu_usage_percent": 96.0,
        "memory_usage_percent": 88.0,
        "request_rate_per_sec": 850.0,
        "latency_ms": 2800.0,
        "error_rate_percent": 18.5,
        "chaos_mode": True,
        "is_synthetic": True,
    }
    eval_spike = evaluate_service_anomaly(spike_metrics)
    assert eval_spike["is_anomaly"] is True
    assert eval_spike["anomaly_score"] >= 0.70
    assert eval_spike["status_label"] == "HIGH ANOMALY"


def test_phase_d3_automated_ai_rca_and_topology():
    """Test D3: AI Root Cause Analysis with topological dependency mapping."""
    assert "exam_service" in MICROSERVICE_TOPOLOGY
    assert "student_portal" in MICROSERVICE_TOPOLOGY["exam_service"]["downstream_dependents"]

    db_exhaustion_metrics = {
        "service": "Exam Service",
        "active_scenario": ServiceMetrics.SCENARIO_DB_POOL,
        "cpu_usage_percent": 88.0,
        "memory_usage_percent": 75.0,
        "latency_ms": 2200.0,
        "error_rate_percent": 16.0,
        "replicas": 2,
        "is_synthetic": True,
    }
    logs = [
        {"level": "ERROR", "message": "Database connection pool exhausted after 5000ms timeout"},
        {"level": "ERROR", "message": "HTTP 503 upstream results_db saturated"},
    ]

    diag = diagnose_incident(
        service_name="Exam Service",
        metrics=db_exhaustion_metrics,
        anomaly_score=0.88,
        recent_logs=logs,
    )

    assert "Database connection pool exhaustion" in diag["suspected_root_cause"]
    assert diag["confidence_score"] >= 0.85
    assert diag["recommended_remediation"] == "RESTART_POD"
    assert diag["matched_runbook_id"] == "runbook-001"
    assert diag["requires_human_approval"] is True
    assert "topology" in diag
    assert "student_portal" in diag["topology"]["impacted_dependents"]


def test_phase_d4_incident_lifecycle_state_machine(db_session: Session):
    """Test D4: Enterprise incident lifecycle state transitions and audit logging."""
    code = f"INC-2026-D401-{int(time.time()*1000)}"
    inc = Incident(
        incident_code=code,
        service_name="Student Portal",
        title="High Latency Degradation",
        status=IncidentStatus.OPEN,
        severity=IncidentSeverity.HIGH,
        anomaly_score=0.76,
        tenant_id=1,
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)

    # 1. Transition: OPEN -> INVESTIGATING
    inc.status = IncidentStatus.INVESTIGATING
    audit1 = AuditLog(
        action="INCIDENT_STATUS_TRANSITION",
        performed_by="sre_engineer",
        target_resource=f"incident/{inc.incident_code}",
        status="SUCCESS",
        details={"old_status": "OPEN", "new_status": "INVESTIGATING"},
        tenant_id=1,
    )
    db_session.add(audit1)
    db_session.commit()

    # 2. Transition: INVESTIGATING -> PENDING_APPROVAL
    inc.status = IncidentStatus.PENDING_APPROVAL
    audit2 = AuditLog(
        action="INCIDENT_STATUS_TRANSITION",
        performed_by="sre_engineer",
        target_resource=f"incident/{inc.incident_code}",
        status="SUCCESS",
        details={"old_status": "INVESTIGATING", "new_status": "PENDING_APPROVAL"},
        tenant_id=1,
    )
    db_session.add(audit2)
    db_session.commit()

    # Verify audit logs in DB
    logs = (
        db_session.query(AuditLog)
        .filter(AuditLog.target_resource == f"incident/{inc.incident_code}")
        .all()
    )
    assert len(logs) >= 2


def test_phase_d5_controlled_self_healing_and_approval(db_session: Session):
    """Test D5: Controlled remediation, human-in-the-loop requirement, and post-action verification."""
    # Ensure allowed actions
    assert "RESTART_POD" in ALLOWED_REMEDIATION_ACTIONS
    assert "SCALE_DEPLOYMENT" in ALLOWED_REMEDIATION_ACTIONS
    assert "FLUSH_IDLE_CONNECTIONS" in ALLOWED_REMEDIATION_ACTIONS

    inc = Incident(
        incident_code=f"INC-2026-D501-{int(time.time()*1000)}",
        service_name="Exam Service",
        title="Exam Service CPU CFS Throttling",
        status=IncidentStatus.PENDING_APPROVAL,
        severity=IncidentSeverity.CRITICAL,
        anomaly_score=0.91,
        tenant_id=1,
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)

    # Negative test: Attempt remediation without human approval on CRITICAL incident
    with pytest.raises(PermissionError):
        execute_controlled_remediation(
            db=db_session,
            incident_id=inc.id,
            action="RESTART_POD",
            approved_by="",  # Missing approval signature
        )

    # Positive test: Execute with authorized approval
    res = execute_controlled_remediation(
        db=db_session,
        incident_id=inc.id,
        action="RESTART_POD",
        approved_by="aegis_admin",
    )
    assert res["status"] == "RESOLVED"
    assert res["verified_recovery"] is True
    assert res["approved_by"] == "aegis_admin"

    db_session.refresh(inc)
    assert inc.status == IncidentStatus.RESOLVED


def test_phase_d6_closed_loop_chaos_and_digital_twin_diurnal(db_session: Session):
    """Test D6: Closed-loop cycle (Fault -> Telemetry -> Anomaly -> RCA -> Self-Healing -> Health) + Diurnal simulation."""
    sim = ChaosSimulator()

    # Step 1: Inject Failure
    chaos_res = sim.inject_failure(
        service_name="exam_service",
        scenario="database",
        severity="HIGH",
        duration_seconds=120,
    )
    assert chaos_res["is_synthetic"] is True
    assert exam_m.chaos_active is True

    # Step 2: Telemetry Spike
    fresh_metrics = exam_m.get_current_metrics()
    assert fresh_metrics["db_pool_saturation_percent"] > 80.0
    assert fresh_metrics["latency_ms"] > 500.0

    # Step 3: Isolation Forest Anomaly Detection (>0.70)
    anom_res = evaluate_service_anomaly(fresh_metrics)
    assert anom_res["is_anomaly"] is True
    assert anom_res["anomaly_score"] >= 0.70

    # Step 4: AI RCA Diagnosis
    diag = diagnose_incident(
        service_name="Exam Service",
        metrics=fresh_metrics,
        anomaly_score=anom_res["anomaly_score"],
        recent_logs=exam_m.recent_logs,
    )
    assert diag["recommended_remediation"] == "RESTART_POD"
    assert diag["confidence_score"] >= 0.85

    # Step 5: Incident Creation & Controlled Remediation
    inc = Incident(
        incident_code=f"INC-2026-CLOSED-{int(time.time()*1000)}",
        service_name="Exam Service",
        title="Automated Closed-Loop Test Incident",
        status=IncidentStatus.PENDING_APPROVAL,
        severity=IncidentSeverity.HIGH,
        anomaly_score=anom_res["anomaly_score"],
        tenant_id=1,
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)

    rem_res = execute_controlled_remediation(
        db=db_session,
        incident_id=inc.id,
        action="RESTART_POD",
        approved_by="sre_autonomous_operator",
    )
    assert rem_res["status"] == "RESOLVED"
    assert rem_res["verified_recovery"] is True
    assert exam_m.chaos_active is False

    # Step 6: Post-Recovery Health Verification
    recovered, verify_telemetry, new_score = verify_service_recovery("Exam Service")
    assert recovered is True
    assert new_score < 0.50
    assert verify_telemetry["status"] == "HEALTHY"

    # Step 7: Digital Twin 24-hour Diurnal Simulation
    dt_sim = CampusActivitySimulator()
    config = SimulationConfig(
        event=AcademicEvent.EXAM_PERIOD,
        intensity=TrafficIntensity.PEAK,
        total_students=5000,
        duration_hours=24,
    )
    timeline = dt_sim.simulate_timeline(config)
    assert len(timeline) == 24
    # Peak exam hours (09:00 - 12:00) should have high exam_service traffic
    exam_hour_10 = timeline[10]
    assert exam_hour_10.service_rps["exam_service"] > 0
    assert exam_hour_10.total_incoming_rps > 0
    assert exam_hour_10.concurrent_students > 100
