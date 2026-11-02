import pytest
from app.models.user import User, UserRole
from app.core.security import create_access_token


def test_ml_anomaly_detection_endpoint(client, db_session):
    student = User(
        email="mlstudent@univ.edu",
        username="mlstudent",
        full_name="ML Student",
        hashed_password="hash",
        role=UserRole.STUDENT,
    )
    db_session.add(student)
    db_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(student.username)}"}

    response = client.get("/api/v1/ml/anomaly-scores", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "model_info" in data
    assert data["model_info"]["name"] == "Isolation Forest"
    assert len(data["services"]) == 4

    # Exam service should be flagged as high anomaly matching default screenshot state
    exam_service = next(s for s in data["services"] if s["service"] == "Exam Service")
    assert exam_service["is_anomaly"] is True
    assert exam_service["anomaly_score"] >= 0.70
