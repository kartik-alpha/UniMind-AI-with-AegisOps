import numpy as np
from ml.models.anomaly_detector import AegisOpsAnomalyDetector, MODEL_PATH


def generate_14_day_normal_traffic(samples: int = 5000) -> np.ndarray:
    """
    Simulates 14 days of normal university IT infrastructure traffic across 5 features:
    - CPU (15-45%)
    - Memory (25-55%)
    - Request Rate (100-500 req/s)
    - Latency (80-200 ms)
    - Error Rate (0.0-0.3%)
    """
    np.random.seed(42)
    cpu = np.random.normal(30, 5, samples)
    mem = np.random.normal(40, 6, samples)
    reqs = np.random.normal(300, 50, samples)
    lat = np.random.normal(130, 20, samples)
    err = np.random.exponential(0.1, samples)

    X = np.column_stack([cpu, mem, reqs, lat, err])
    return np.clip(X, 0, None)


def train_and_save():
    print("Generating 14 days of normal traffic baseline data...")
    X_train = generate_14_day_normal_traffic()

    print("Training AegisOps Isolation Forest Anomaly Detection Model...")
    detector = AegisOpsAnomalyDetector(contamination=0.05)
    detector.train_baseline(X_train)

    print(f"Model successfully saved to {MODEL_PATH}")


if __name__ == "__main__":
    train_and_save()
