import time
from typing import Dict, Any, List
from collections import defaultdict
from ml.features.feature_extractor import extract_features
from ml.models.anomaly_detector import AegisOpsAnomalyDetector

_detector_instance = None
_score_history: Dict[str, List[float]] = defaultdict(list)


def get_detector() -> AegisOpsAnomalyDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AegisOpsAnomalyDetector()
    return _detector_instance


def evaluate_service_anomaly(metrics_data: Dict[str, Any], apply_dampening: bool = True) -> Dict[str, Any]:
    """
    Evaluates real-time microservice telemetry against the Isolation Forest model.
    Applies sliding window rolling smoothing and diurnal pattern dampening to prevent false alarms.
    Preserves strict >0.70 threshold invariant for confirmed anomalies.
    """
    detector = get_detector()
    features = extract_features(metrics_data)
    raw_score, raw_is_anomaly = detector.predict_anomaly_score(features)

    service_name = metrics_data.get("service", "Unknown Service")
    svc_key = service_name.lower().replace(" ", "_")

    cpu = metrics_data.get("cpu_usage_percent", 0.0)
    lat = metrics_data.get("latency_ms", 0.0)
    err = metrics_data.get("error_rate_percent", 0.0)
    is_chaos = metrics_data.get("chaos_mode") or metrics_data.get("is_synthetic")
    current_hour = time.localtime().tm_hour

    # 1. Sliding window rolling smoothing (5-sample window)
    history = _score_history[svc_key]
    history.append(raw_score)
    if len(history) > 10:
        history.pop(0)

    rolling_avg = sum(history[-5:]) / min(len(history), 5)
    # Blend current observation with rolling average to smooth short-term jitter
    smoothed_score = round(0.70 * raw_score + 0.30 * rolling_avg, 2)

    # Acute spike detection: If the raw anomaly score is high (>=0.70) accompanied by critical
    # metric thresholds (CPU > 80%, Error Rate > 5%, Latency > 800ms, or synthetic chaos),
    # do not suppress the immediate critical event via historical smoothing.
    if raw_score >= 0.70 and (cpu > 80.0 or err > 5.0 or lat > 800.0 or is_chaos):
        smoothed_score = raw_score

    # 2. Diurnal pattern dampening for normal daytime load
    # Normal daytime traffic (09:00-18:00) with healthy metrics shouldn't trip false anomalies
    dampened = False

    final_score = smoothed_score
    if apply_dampening and not is_chaos:
        # If metrics are well within safe operating envelopes during daytime, clamp spurious anomalies
        if (8 <= current_hour <= 22) and (cpu < 70.0) and (err < 1.0) and (lat < 400.0):
            if final_score >= 0.70:
                final_score = round(min(final_score, 0.45), 2)
                dampened = True

    # 3. Anomaly Decision Invariant (Threshold >= 0.70)
    is_anomaly = (final_score >= 0.70)

    if is_anomaly:
        alert_msg = f"{service_name}: current service behavior significantly differs from the learned normal operating pattern (Score: {final_score})."
        status_label = "HIGH ANOMALY"
    else:
        alert_msg = f"{service_name}: operating within normal baseline limits."
        status_label = "NORMAL"

    return {
        "service": service_name,
        "anomaly_score": final_score,
        "raw_score": raw_score,
        "smoothed_score": smoothed_score,
        "is_anomaly": is_anomaly,
        "status_label": status_label,
        "alert_message": alert_msg,
        "dampened": dampened,
        "rolling_history_size": len(history),
        "features": {
            "cpu": cpu,
            "memory": metrics_data.get("memory_usage_percent", 0.0),
            "request_rate": metrics_data.get("request_rate_per_sec", 0.0),
            "latency_ms": lat,
            "error_rate": err,
        },
    }
