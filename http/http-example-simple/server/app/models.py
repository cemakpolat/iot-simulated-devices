import numpy as np
from sklearn.ensemble import IsolationForest
import logging

logger = logging.getLogger(__name__)

class TemperatureAnomalyModel:
    """AI model specifically for temperature anomalies."""
    def __init__(self):
        np.random.seed(42)
        # Train on a normal range of 20-25°C
        X_train = np.random.uniform(20, 25, size=(500, 1))
        self.model = IsolationForest(contamination=0.05, random_state=42)
        self.model.fit(X_train)
        logger.info("Temperature Anomaly Model trained and initialized.")

    def predict(self, value):
        is_anomaly = self.model.predict([[value]])[0] == -1
        score = self.model.score_samples([[value]])[0]
        confidence = 1 / (1 + np.exp(-score)) # Sigmoid for a 0-1 score
        result = 'anomaly' if is_anomaly else 'normal'
        return result, round(confidence, 3)

class HumidityAnomalyModel:
    """AI model specifically for humidity anomalies."""
    def __init__(self):
        np.random.seed(42)
        # Train on a normal range of 40-60%
        X_train = np.random.uniform(40, 60, size=(500, 1))
        self.model = IsolationForest(contamination=0.05, random_state=42)
        self.model.fit(X_train)
        logger.info("Humidity Anomaly Model trained and initialized.")
    
    def predict(self, value):
        is_anomaly = self.model.predict([[value]])[0] == -1
        score = self.model.score_samples([[value]])[0]
        confidence = 1 / (1 + np.exp(-score))
        result = 'anomaly' if is_anomaly else 'normal'
        return result, round(confidence, 3)


class ModelRegistry:
    """Holds a mapping from metric type to a trained model."""
    def __init__(self):
        self._models = {
            "temperature": TemperatureAnomalyModel(),
            "humidity": HumidityAnomalyModel(),
            # Add new models here, e.g., "pressure": PressureAnomalyModel()
        }
        logger.info(f"Model Registry loaded with models: {list(self._models.keys())}")

    def get_model(self, metric_type):
        return self._models.get(metric_type)