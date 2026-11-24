import pytest
from app.models.user import User, UserRole
from app.core.security import create_access_token
from app.models.ticket import Incident, IncidentStatus
from app.models.audit import AuditLog
from digital_twin.models import (
    AcademicEvent,
    TrafficIntensity,
    SimulationConfig,
    BottleneckAlert,
)
from digital_twin.simulator import CampusActivitySimulator
from digital_twin.capacity_planner import PredictiveCapacityPlanner
from digital_twin.aegisops_bridge import AegisOpsDigitalTwinBridge


def create_user_helper(db_session, email, username, full_name, role):
    user = User(
        email=email,
        username=username,
        full_name=full_name,
        hashed_password="hash",
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_diurnal_student_activity_curve():
    """Verify that diurnal student activity curve models 24h campus rhythms accurately."""
    config = SimulationConfig(
        total_students=10000,
        concurrency_ratio=0.15,
        duration_hours=24,
        event=AcademicEvent.NORMAL_DAY,
        intensity=TrafficIntensity.NORMAL,
    )
    simulator = CampusActivitySimulator(config)
    timeline = simulator.simulate_timeline()

    assert len(timeline) == 24
    
    # Night hours (01:00 to 04:00) should have very low concurrency (<500 students)
    night_users = [t.concurrent_students for t in timeline if 1 <= t.hour <= 4]
    for u in night_users:
        assert u < 100, f"Night users {u} should be low"

    # Peak hours (e.g. 10:00 or 20:00) should have high concurrency (>800 students)
    peak_users = [t.concurrent_students for t in timeline if t.hour in (10, 20, 21)]
    for u in peak_users:
        assert u > 800, f"Peak users {u} should be high"

    # All timeline points must be tagged as simulation
    assert all(t.is_simulation is True for t in timeline)


def test_academic_events_traffic_shaping():
    """Verify that different academic events shape microservice traffic appropriately."""
    sim = CampusActivitySimulator()

    # Exam period: 10:00 should have high exam_service share (>= 50%)
    exam_dist = sim.get_service_traffic_distribution(10, AcademicEvent.EXAM_PERIOD)
    assert exam_dist["exam_service"] >= 0.50

    # Assignment deadline: 22:00 should have high LMS share (>= 60%)
    lms_dist = sim.get_service_traffic_distribution(22, AcademicEvent.ASSIGNMENT_DEADLINE)
    assert lms_dist["lms"] >= 0.60

    # Admission period: 12:00 should have high Student Portal share (>= 50%)
    portal_dist = sim.get_service_traffic_distribution(12, AcademicEvent.ADMISSION_PERIOD)
    assert portal_dist["student_portal"] >= 0.50

    # Sum of weights must equal 1.0
    for d in [exam_dist, lms_dist, portal_dist]:
        assert abs(sum(d.values()) - 1.0) < 0.01


def test_predictive_capacity_planner_bottleneck_detection():
    """Verify that capacity planner identifies saturation bottlenecks and formulates recommendations."""
    config = SimulationConfig(
        total_students=25000,
        concurrency_ratio=0.30,
        duration_hours=24,
        event=AcademicEvent.RESULT_ANNOUNCEMENT,
        intensity=TrafficIntensity.EXTREME,
    )
    planner = PredictiveCapacityPlanner()
    forecast = planner.generate_capacity_forecast(config)

    assert forecast.is_simulation is True
    assert forecast.peak_concurrent_users > 5000
    assert forecast.overall_status in ("WARNING", "CRITICAL")
    assert len(forecast.alerts) > 0

    # Check alert structure
    alert = forecast.alerts[0]
    assert alert.primary_bottleneck in ("CPU", "DB_POOL", "RPS_CAPACITY", "MEMORY")
    assert alert.target_replicas > 2
    assert "Pre-scale" in alert.recommendation or "Autoscale" in alert.recommendation


def test_scenario_comparison():
    """Verify multi-scenario comparison of normal, peak, and extreme scenarios."""
    config = SimulationConfig(total_students=12000, duration_hours=24)
    planner = PredictiveCapacityPlanner()
    comp = planner.compare_scenarios(config)

    assert comp.is_simulation is True
    assert "Baseline Normal" in comp.scenarios
    assert "Peak Academic" in comp.scenarios
    assert "Extreme Shock" in comp.scenarios
    assert len(comp.comparison_table) == 3
    assert len(comp.key_findings) == 3

    # Concurrency and RPS should scale monotonically from normal to extreme
    normal_rps = comp.comparison_table[0]["peak_rps"]
    extreme_rps = comp.comparison_table[2]["peak_rps"]
    assert extreme_rps > normal_rps


def test_proactive_aegisops_bridge_sync_and_deduplication(db_session):
    """Verify syncing predictive bottleneck alerts into AegisOps incidents with deduplication."""
    alert = BottleneckAlert(
        alert_id="ALT-TEST-001",
        service_name="exam_service",
        hour=10,
        time_label="10:00",
        severity="CRITICAL",
        primary_bottleneck="DB_POOL",
        predicted_value=94.5,
        threshold_value=85.0,
        lead_time_hours=2,
        explanation="Database Connection Pool Saturation predicted (94.5% of 50 conns)",
        recommendation="Pre-scale exam_service replicas and expand DB pool",
        target_replicas=5,
        is_simulation=True,
    )
    config = SimulationConfig(
        total_students=18000,
        event=AcademicEvent.EXAM_PERIOD,
        intensity=TrafficIntensity.PEAK,
    )

    # 1. First sync creates new predictive incident
    inc1 = AegisOpsDigitalTwinBridge.sync_alert_to_incident(db_session, alert, config)
    assert inc1.id is not None
    assert "[PREDICTIVE ALERT]" in inc1.title
    assert inc1.status == IncidentStatus.PENDING_APPROVAL
    assert inc1.metrics_summary["is_simulation"] is True

    # 2. Second sync updates existing incident without duplicate
    alert2 = alert.model_copy(update={"predicted_value": 98.0})
    inc2 = AegisOpsDigitalTwinBridge.sync_alert_to_incident(db_session, alert2, config)
    assert inc2.id == inc1.id
    assert inc2.metrics_summary["predicted_value"] == 98.0


def test_proactive_remediation_approval_workflow(db_session):
    """Verify human approval workflow and automated headroom verification."""
    admin = create_user_helper(db_session, "dt_admin@univ.edu", "dt_admin", "DT Admin", UserRole.ADMIN)

    alert = BottleneckAlert(
        alert_id="ALT-TEST-002",
        service_name="exam_service",
        hour=10,
        time_label="10:00",
        severity="CRITICAL",
        primary_bottleneck="CPU",
        predicted_value=91.0,
        threshold_value=85.0,
        lead_time_hours=1,
        explanation="CPU Saturation predicted (91.0% >= 85%)",
        recommendation="Pre-scale exam_service to 4 replicas",
        target_replicas=4,
        is_simulation=True,
    )
    config = SimulationConfig(total_students=12000, event=AcademicEvent.EXAM_PERIOD)
    inc = AegisOpsDigitalTwinBridge.sync_alert_to_incident(db_session, alert, config)

    # Admin approves
    res = AegisOpsDigitalTwinBridge.approve_proactive_remediation(
        db_session, incident_id=inc.id, approved_by=admin.username, target_replicas=4
    )
    assert res["status"] == "RESOLVED"
    assert res["approved_by"] == "dt_admin"

    # Verify incident state in DB
    db_session.refresh(inc)
    assert inc.status == IncidentStatus.RESOLVED
    assert inc.approved_by == "dt_admin"

    # Verify AuditLog generated
    audit = db_session.query(AuditLog).filter(AuditLog.action == "PROACTIVE_REMEDIATION_APPROVED").first()
    assert audit is not None
    assert audit.performed_by == "dt_admin"


def test_proactive_remediation_rejection_workflow(db_session):
    """Verify administrator rejection of proactive recommendation transitions to OPEN."""
    admin = create_user_helper(db_session, "dt_rej@univ.edu", "dt_rej", "DT Rej", UserRole.ADMIN)

    alert = BottleneckAlert(
        alert_id="ALT-TEST-003",
        service_name="lms",
        hour=22,
        time_label="22:00",
        severity="WARNING",
        primary_bottleneck="CPU",
        predicted_value=86.0,
        threshold_value=85.0,
        lead_time_hours=3,
        explanation="CPU Saturation predicted",
        recommendation="Pre-scale lms replicas",
        target_replicas=4,
        is_simulation=True,
    )
    config = SimulationConfig(total_students=10000, event=AcademicEvent.ASSIGNMENT_DEADLINE)
    inc = AegisOpsDigitalTwinBridge.sync_alert_to_incident(db_session, alert, config)

    res = AegisOpsDigitalTwinBridge.reject_proactive_remediation(
        db_session, incident_id=inc.id, rejected_by=admin.username, reason="Cluster nodes under maintenance"
    )
    assert res["status"] == "OPEN"
    assert res["action"] == "REJECTED"

    db_session.refresh(inc)
    assert inc.status == IncidentStatus.OPEN
    assert "REJECTED" in inc.action_taken


def test_digital_twin_api_endpoints(client, db_session):
    """Verify FastAPI API router endpoints for Digital Twin."""
    admin = create_user_helper(db_session, "api_dt_admin@univ.edu", "api_dt_admin", "API DT Admin", UserRole.ADMIN)
    token = create_access_token(admin.username)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /events
    resp = client.get("/api/v1/digital-twin/events", headers=headers)
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 5
    assert any(e["event_id"] == "EXAM_PERIOD" for e in events)

    # 2. POST /simulate
    resp = client.post(
        "/api/v1/digital-twin/simulate",
        json={"total_students": 10000, "event": "NORMAL_DAY", "intensity": "NORMAL"},
        headers=headers,
    )
    assert resp.status_code == 200
    sim_data = resp.json()
    assert sim_data["is_simulation"] is True
    assert len(sim_data["timeline"]) == 24

    # 3. POST /capacity-plan
    resp = client.post(
        "/api/v1/digital-twin/capacity-plan",
        json={"total_students": 15000, "event": "EXAM_PERIOD", "intensity": "PEAK", "sync_to_aegisops": True},
        headers=headers,
    )
    assert resp.status_code == 200
    plan_data = resp.json()
    assert plan_data["is_simulation"] is True
    assert "metrics_by_service" in plan_data

    # 4. GET /predictive-alerts
    resp = client.get("/api/v1/digital-twin/predictive-alerts", headers=headers)
    assert resp.status_code == 200
    alerts = resp.json()
    assert isinstance(alerts, list)

    # 5. POST /scenario-compare
    resp = client.post(
        "/api/v1/digital-twin/scenario-compare",
        json={"total_students": 12000, "event": "EXAM_PERIOD"},
        headers=headers,
    )
    assert resp.status_code == 200
    comp_data = resp.json()
    assert "Baseline Normal" in comp_data["scenarios"]

    # 6. RBAC Check: Student cannot approve proactive remediation
    student = create_user_helper(db_session, "stu_dt@univ.edu", "stu_dt", "Student DT", UserRole.STUDENT)
    stu_token = create_access_token(student.username)
    stu_headers = {"Authorization": f"Bearer {stu_token}"}

    resp = client.post(
        "/api/v1/digital-twin/proactive-remediation/approve",
        json={"incident_id": 1, "target_replicas": 4},
        headers=stu_headers,
    )
    assert resp.status_code == 403

