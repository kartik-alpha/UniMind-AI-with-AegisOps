from typing import Dict, Any, List
import numpy as np


def extract_features(metrics_data: Dict[str, Any]) -> np.ndarray:
    """
    Extracts 5 numerical features for Isolation Forest anomaly detection:
    1. CPU Usage (%)
    2. Memory Usage (%)
    3. Request Rate (req/sec)
    4. Latency (ms)
    5. Error Rate (%)
    """
    cpu = float(metrics_data.get("cpu_usage_percent", 20.0))
    memory = float(metrics_data.get("memory_usage_percent", 35.0))
    req_rate = float(metrics_data.get("request_rate_per_sec", 100.0))
    latency = float(metrics_data.get("latency_ms", 100.0))
    errors = float(metrics_data.get("error_rate_percent", 0.0))

    return np.array([[cpu, memory, req_rate, latency, errors]], dtype=np.float32)
