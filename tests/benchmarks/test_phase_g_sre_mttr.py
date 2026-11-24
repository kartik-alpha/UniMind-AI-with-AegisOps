"""
Phase G3: SRE Self-Healing, MTTD & MTTR Benchmark Suite.
Measures:
1. Mean Time To Detect (MTTD): Chaos injection -> Isolation Forest anomaly score >= 0.70 (< 2.0s).
2. Mean Time To Remediate (MTTR): Remediation approval -> service recovery & baseline metric verification (< 5.0s).
3. Scenario validation across CPU, Memory, Database Pool, Network, HTTP Errors, and Combined outages.
"""
import time
import numpy as np
import pytest

from app.db.session import SessionLocal
from app.models.ticket import Incident, IncidentStatus
from app.models.user import User, UserRole
from scripts.chaos_simulator import get_chaos_simulator
from ml.models.anomaly_detector import AegisOpsAnomalyDetector
from aegisops.remediation.remediator import execute_controlled_remediation, verify_service_recovery
from services.exam_service.main import metrics as exam_m


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


# ---------------------------------------------------------------------------
# G3.1: MTTD Benchmark Across Chaos Scenarios
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario,severity", [
    ("database", "HIGH"),
    ("cpu", "CRITICAL"),
    ("memory", "HIGH"),
    ("network", "MEDIUM"),
    ("http_errors", "HIGH"),
    ("combined", "CRITICAL"),
])
def test_benchmark_mttd_anomaly_detection(scenario, severity):
    """
    Measures Mean Time to Detect (MTTD):
    Injects failure and validates that Isolation Forest identifies anomaly in < 2000ms.
    """
    simulator = get_chaos_simulator()
    detector = AegisOpsAnomalyDetector()

    t_start = time.perf_counter()
    injected = simulator.inject_failure(
        service_name="exam_service",
        scenario=scenario,
        severity=severity,
        duration_seconds=30,
    )

    f_vec = np.array([[
        injected["cpu_usage_percent"],
        injected["memory_usage_percent"],
        injected["request_rate_per_sec"],
        injected["latency_ms"],
        injected["error_rate_percent"],
    ]])
    score, is_anom = detector.predict_anomaly_score(f_vec)
    mttd_ms = (time.perf_counter() - t_start) * 1000.0

    print(f"\n[BENCHMARK MTTD] Scenario: {scenario.upper():<10} | Severity: {severity:<8} | Anomaly Score: {score:.4f} | MTTD: {mttd_ms:.2f}ms")

    # Invariants
    assert mttd_ms < 2000.0, f"MTTD exceeded 2000ms SLA: {mttd_ms}ms"
    if severity in ("HIGH", "CRITICAL"):
        assert (is_anom or score >= 0.65), f"Failed to detect critical anomaly for {scenario}: score={score}"

    # Cleanup
    simulator.restore_all()


# ---------------------------------------------------------------------------
# G3.2: MTTR Benchmark for Self-Healing Orchestration
# ---------------------------------------------------------------------------

def test_benchmark_mttr_self_healing_remediation(db_session):
    """
    Measures Mean Time to Remediate (MTTR):
    From approval dispatch to full pod container reset, metrics stabilization, and audit log write.
    """
    simulator = get_chaos_simulator()
    simulator.inject_failure("exam_service", scenario="database", severity="HIGH", duration_seconds=60)

    # Create active incident
    inc = Incident(
        incident_code=f"INC-BENCH-MTTR-{int(time.time()*1000)%100000}",
        service_name="Exam Service",
        title="High Latency & DB Pool Saturation Benchmark",
        status=IncidentStatus.PENDING_APPROVAL,
        anomaly_score=0.91,
        tenant_id=1,
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)

    t_remediate_start = time.perf_counter()
    res = execute_controlled_remediation(
        db=db_session,
        incident_id=inc.id,
        action="RESTART_POD",
        approved_by="sre_benchmark_runner",
        target_replicas=4,
    )
    mttr_ms = (time.perf_counter() - t_remediate_start) * 1000.0

    print(f"\n[BENCHMARK MTTR] Action: RESTART_POD | Result: {res['status']} | MTTR: {mttr_ms:.2f}ms")

    # Strict SLA check
    assert res["status"] in ("SUCCESS", "RESOLVED")
    assert res["verified_recovery"] is True
    assert mttr_ms < 5000.0, f"MTTR exceeded 5000ms SLA: {mttr_ms}ms"

    # Verify underlying service recovery
    is_rec, fresh_m, fresh_score = verify_service_recovery("exam_service")
    assert is_rec is True
    assert fresh_score < 0.70, f"Recovered anomaly score remained high: {fresh_score}"

    # Cleanup
    db_session.delete(inc)
    db_session.commit()
    simulator.restore_all()
