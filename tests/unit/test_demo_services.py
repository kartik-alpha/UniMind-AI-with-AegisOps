import pytest
from fastapi.testclient import TestClient

from services.lms.main import app as lms_app
from services.student_portal.main import app as portal_app
from services.exam_service.main import app as exam_app
from services.library_service.main import app as library_app


def test_lms_health_and_metrics():
    client = TestClient(lms_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "lms"

    m_resp = client.get("/metrics")
    assert m_resp.status_code == 200
    assert "university_service_cpu_percent" in m_resp.text


def test_student_portal_health():
    client = TestClient(portal_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "student_portal"


def test_exam_service_degradation_and_chaos():
    client = TestClient(exam_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "exam_service"

    # Disable chaos
    dis_resp = client.post("/chaos/disable")
    assert dis_resp.status_code == 200

    # Enable chaos
    en_resp = client.post("/chaos/enable")
    assert en_resp.status_code == 200


def test_library_service_health():
    client = TestClient(library_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "library_service"
