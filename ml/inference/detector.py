from typing import Dict, Any
from ml.features.feature_extractor import extract_features
from ml.models.anomaly_detector import AegisOpsAnomalyDetector

_detector_instance = None


def get_detector() -> AegisOpsAnomalyDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AegisOpsAnomalyDetector()
    return _detector_instance


def evaluate_service_anomaly(metrics_data: Dict[str, Any]) -> Dict[str, Any]:
    detector = get_detector()
    features = extract_features(metrics_data)
    score, is_anomaly = detector.predict_anomaly_score(features)

    service_name = metrics_data.get("service", "Unknown Service")
    if is_anomaly:
        alert_msg = f"{service_name}: current service behavior significantly differs from the learned normal operating pattern."
        status_label = "HIGH ANOMALY"
    else:
        alert_msg = f"{service_name}: operating within normal baseline limits."
        status_label = "NORMAL"

    return {
        "service": service_name,
        "anomaly_score": score,
        "is_anomaly": is_anomaly,
        "status_label": status_label,
        "alert_message": alert_msg,
        "features": {
            "cpu": metrics_data.get("cpu_usage_percent", 0.0),
            "memory": metrics_data.get("memory_usage_percent", 0.0),
            "request_rate": metrics_data.get("request_rate_per_sec", 0.0),
            "latency_ms": metrics_data.get("latency_ms", 0.0),
            "error_rate": metrics_data.get("error_rate_percent", 0.0),
        },
    }
