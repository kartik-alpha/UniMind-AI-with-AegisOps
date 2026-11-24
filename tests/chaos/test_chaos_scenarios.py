import numpy as np
import pytest

from services.common_metrics import ServiceMetrics
from scripts.chaos_simulator import get_chaos_simulator, SCENARIOS
from ml.models.anomaly_detector import AegisOpsAnomalyDetector


@pytest.fixture(autouse=True)
def clean_chaos_state():
    sim = get_chaos_simulator()
    sim.restore_all()
    yield
    sim.restore_all()


def test_normal_baseline_telemetry_and_ml_scoring():
    """
    Validates that a steady-state normal service exhibits low anomaly scores and no alert status.
    """
    sim = get_chaos_simulator()
    normal_data = sim.services["exam_service"].get_current_metrics()

    assert normal_data["status"] == "HEALTHY"
    assert normal_data["chaos_mode"] is False
    assert normal_data["cpu_usage_percent"] < 40.0
    assert normal_data["latency_ms"] < 200.0
    assert normal_data["error_rate_percent"] < 1.0

    # ML Inference
    detector = AegisOpsAnomalyDetector()
    f_vec = np.array([[
        normal_data["cpu_usage_percent"],
        normal_data["memory_usage_percent"],
        normal_data["request_rate_per_sec"],
        normal_data["latency_ms"],
        normal_data["error_rate_percent"],
    ]])
    score, is_anom = detector.predict_anomaly_score(f_vec)

    assert score < 0.55, f"False positive anomaly on normal baseline: {score}"
    assert is_anom is False


@pytest.mark.parametrize("scenario, expected_high_feature", [
    ("cpu", "cpu_usage_percent"),
    ("memory", "memory_usage_percent"),
    ("database", "latency_ms"),
    ("network", "latency_ms"),
    ("http_errors", "error_rate_percent"),
    ("combined", "cpu_usage_percent"),
])
def test_individual_chaos_scenarios_and_ml_detection(scenario, expected_high_feature):
    """
    Validates failure injection, telemetry reflection, and Isolation Forest scoring for all scenarios.
    """
    sim = get_chaos_simulator()
    injected = sim.inject_failure(
        service_name="exam_service",
        scenario=scenario,
        severity="HIGH",
        duration_seconds=30,
    )

    assert injected["status"] in ("CRITICAL", "DEGRADED")
    assert injected["is_synthetic"] is True
    assert injected[expected_high_feature] > 0

    # ML Anomaly Evaluation
    detector = AegisOpsAnomalyDetector()
    f_vec = np.array([[
        injected["cpu_usage_percent"],
        injected["memory_usage_percent"],
        injected["request_rate_per_sec"],
        injected["latency_ms"],
        injected["error_rate_percent"],
    ]])
    anomaly_score, is_anomaly = detector.predict_anomaly_score(f_vec)

    # Scenarios must trigger elevated anomaly score
    assert anomaly_score >= 0.65, f"Scenario {scenario} failed to elevate anomaly score: {anomaly_score}"

    # Verify Prometheus metric formatting has synthetic indicator
    prom_output = sim.services["exam_service"].to_prometheus_format()
    assert 'synthetic="true"' in prom_output
    assert 'university_service_cpu_percent' in prom_output

    # Verify correlated logs generated
    logs = sim.services["exam_service"].recent_logs
    assert len(logs) > 0
    assert any(l.get("is_synthetic") is True for l in logs)


def test_multivariate_combined_failure_scenario():
    """
    Validates Scenario F: Combined Infrastructure Failure across compute, memory, and database.
    """
    sim = get_chaos_simulator()
    res = sim.inject_failure(service_name="lms", scenario="combined", severity="CRITICAL", duration_seconds=45)

    assert res["service"] == "LMS"
    assert res["cpu_usage_percent"] >= 90.0
    assert res["memory_usage_percent"] >= 80.0
    assert res["latency_ms"] >= 1800.0
    assert res["error_rate_percent"] >= 12.0

    detector = AegisOpsAnomalyDetector()
    f_vec = np.array([[
        res["cpu_usage_percent"],
        res["memory_usage_percent"],
        res["request_rate_per_sec"],
        res["latency_ms"],
        res["error_rate_percent"],
    ]])
    score, is_anom = detector.predict_anomaly_score(f_vec)

    assert score >= 0.70
    assert is_anom is True


def test_chaos_duration_expiry_and_auto_recovery():
    """
    Validates that a time-bounded chaos scenario auto-recovers to healthy baseline after expiry.
    """
    sim = get_chaos_simulator()
    sim.inject_failure(service_name="student_portal", scenario="cpu", severity="MEDIUM", duration_seconds=1)

    assert sim.services["student_portal"].chaos_active is True

    # Simulate time progression beyond 1 second
    sim.services["student_portal"].started_at = 1.0  # Force elapsed time
    recovered = sim.services["student_portal"].get_current_metrics()

    assert recovered["status"] == "HEALTHY"
    assert recovered["chaos_mode"] is False
