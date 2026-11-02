from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from ml.inference.detector import evaluate_service_anomaly
from services.lms.main import metrics as lms_m
from services.student_portal.main import metrics as portal_m
from services.exam_service.main import metrics as exam_m
from services.library_service.main import metrics as lib_m

router = APIRouter(prefix="/ml", tags=["ML Anomaly Detection"])


@router.get("/anomaly-scores")
def get_service_anomaly_scores(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get live Isolation Forest ML anomaly scores for all 4 demo university services.
    Matches AegisOps ML Anomaly Detection Dashboard.
    """
    all_metrics = [
        exam_m.get_current_metrics(),
        lms_m.get_current_metrics(),
        portal_m.get_current_metrics(),
        lib_m.get_current_metrics(),
    ]

    evaluations = [evaluate_service_anomaly(m) for m in all_metrics]
    high_anomalies = [e for e in evaluations if e["is_anomaly"]]

    return {
        "model_info": {
            "name": "Isolation Forest",
            "status": "Active",
            "features": ["CPU", "Memory", "Requests", "Latency", "Errors"],
            "threshold": 0.70,
            "trained_on": "14 days of normal traffic",
        },
        "services": evaluations,
        "active_anomaly_count": len(high_anomalies),
    }
