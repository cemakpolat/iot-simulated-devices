# server/app/models/anomaly_detector.py
"""Your AnomalyDetector - keep exactly as provided"""
from sklearn.ensemble import IsolationForest
import numpy as np
import pandas as pd
import logging
import joblib
import os

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """
    Detects anomalies in sensor data using the Isolation Forest algorithm.
    """
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.model = IsolationForest(contamination=contamination, random_state=random_state)
        self.is_trained = False
        self.model_path = "models/anomaly_detector.joblib"
        logger.info("AnomalyDetector initialized.")

    def train(self, data: pd.DataFrame, feature_columns: list = None) -> bool:
        """Train the anomaly detection model"""
        if data.empty:
            logger.warning("No data provided for anomaly detector training.")
            self.is_trained = False
            return False

        if feature_columns is None:
            feature_columns = ['temperature', 'humidity'] 
            feature_columns = [col for col in feature_columns if col in data.columns]
            if not feature_columns:
                logger.warning("No valid feature columns found in data for anomaly detector training.")
                self.is_trained = False
                return False

        X = data[feature_columns].values
        
        try:
            self.model.fit(X)
            self.is_trained = True
            logger.info(f"Anomaly detector trained successfully on {len(X)} samples using features: {feature_columns}")
            
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            logger.info(f"Anomaly detector model saved to {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Error training anomaly detector: {e}", exc_info=True)
            self.is_trained = False
            return False

    def predict(self, data: pd.DataFrame, feature_columns: list = None) -> np.ndarray:
        """Predict anomalies in new data"""
        if not self.is_trained:
            self.load_model() 
            if not self.is_trained:
                logger.warning("Anomaly detector is not trained or loaded")
                return np.ones(len(data))

        if data.empty:
            logger.warning("No data provided for anomaly prediction")
            return np.array([])
            
        if feature_columns is None:
            feature_columns = ['temperature', 'humidity']
            feature_columns = [col for col in feature_columns if col in data.columns]
            if not feature_columns:
                logger.warning("No valid feature columns found in data for anomaly prediction")
                return np.ones(len(data))

        X = data[feature_columns].values
        
        try:
            return self.model.predict(X)
        except Exception as e:
            logger.error(f"Error predicting anomalies: {e}", exc_info=True)
            return np.ones(len(X))

    def load_model(self):
        """Load a pre-trained anomaly detection model from disk"""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.is_trained = True
                logger.info(f"Anomaly detector model loaded successfully from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load anomaly detector model: {e}", exc_info=True)
                self.is_trained = False
        else:
            logger.info(f"Anomaly detector model file not found at {self.model_path}")
            self.is_trained = False

