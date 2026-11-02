import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

MODEL_PATH = Path("ml/models/isolation_forest.joblib")


class AegisOpsAnomalyDetector:
    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        self.model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=42,
        )
        self.is_trained = False
        self._load_if_exists()

    def train_baseline(self, X_normal: np.ndarray):
        """
        Train Isolation Forest model on normal operating baseline data.
        """
        self.model.fit(X_normal)
        self.is_trained = True
        self.save_model()

    def save_model(self, path: Optional[Path] = None):
        target = path or MODEL_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, target)

    def _load_if_exists(self):
        if MODEL_PATH.exists():
            try:
                self.model = joblib.load(MODEL_PATH)
                self.is_trained = True
            except Exception:
                pass

    def predict_anomaly_score(self, feature_vector: np.ndarray) -> Tuple[float, bool]:
        """
        Returns (anomaly_score_normalized [0.0 - 1.0], is_anomaly [True/False]).
        Higher score (e.g. > 0.70) indicates high anomaly.
        """
        if not self.is_trained:
            # Self-train baseline if model not pre-loaded
            synthetic_normal = np.random.normal(loc=[30, 40, 300, 120, 0.1], scale=[5, 5, 50, 20, 0.1], size=(500, 5))
            synthetic_normal = np.clip(synthetic_normal, 0, None)
            self.train_baseline(synthetic_normal)

        # decision_function returns lower values for anomalies
        raw_score = self.model.decision_function(feature_vector)[0]
        # Normalize decision function score to [0.0, 1.0] range (0.0 = completely normal, 1.0 = extreme anomaly)
        normalized_score = round(float(np.clip(0.5 - raw_score, 0.0, 1.0)), 2)
        is_anomaly = normalized_score >= 0.70

        return normalized_score, is_anomaly
