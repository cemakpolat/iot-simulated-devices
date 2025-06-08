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
    It can be trained on historical data and then used to predict anomalies in new data.
    """
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        """
        Initializes the Isolation Forest model.
        :param contamination: The proportion of outliers in the data set. Used when fitting.
        :param random_state: Controls the randomness of the estimator.
        """
        self.model = IsolationForest(contamination=contamination, random_state=random_state)
        self.is_trained = False
        self.model_path = "models/anomaly_detector.joblib" # Consistent path for saving/loading
        logger.info("AnomalyDetector initialized.")

    def train(self, data: pd.DataFrame, feature_columns: list = None) -> bool:
        """
        Trains the anomaly detection model using the provided data.
        :param data: Pandas DataFrame containing the features for training.
        :param feature_columns: List of column names to use as features. If None, tries defaults.
        :return: True if training was successful, False otherwise.
        """
        if data.empty:
            logger.warning("No data provided for anomaly detector training.")
            self.is_trained = False
            return False

        if feature_columns is None:
            # Default to 'temperature' and 'humidity' if not specified, assuming their presence
            feature_columns = ['temperature', 'humidity'] 
            # Filter to ensure only existing columns are used
            feature_columns = [col for col in feature_columns if col in data.columns]
            if not feature_columns:
                logger.warning("No valid feature columns found in data for anomaly detector training.")
                self.is_trained = False
                return False

        # Prepare the feature matrix
        X = data[feature_columns].values
        
        try:
            # Fit the Isolation Forest model to the data
            self.model.fit(X)
            self.is_trained = True
            logger.info(f"Anomaly detector trained successfully on {len(X)} samples using features: {feature_columns}")
            
            # Save the trained model to disk for persistence
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            logger.info(f"Anomaly detector model saved to {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Error training anomaly detector: {e}", exc_info=True)
            self.is_trained = False
            return False

    def predict(self, data: pd.DataFrame, feature_columns: list = None) -> np.ndarray:
        """
        Predicts anomalies in new data.
        :param data: Pandas DataFrame containing the data to predict on.
        :param feature_columns: List of column names to use as features. Must match training features.
        :return: A NumPy array of predictions (-1 for anomaly, 1 for normal). 
                 Returns all 1s if model is not trained or an error occurs.
        """
        if not self.is_trained:
            # Attempt to load the model if it's not trained in the current session
            self.load_model() 
            if not self.is_trained:
                logger.warning("Anomaly detector is not trained or loaded. Skipping prediction and returning normal.")
                return np.ones(len(data)) # Assume all data is normal if no model is available

        if data.empty:
            logger.warning("No data provided for anomaly prediction. Returning empty array.")
            return np.array([])
            
        if feature_columns is None:
            # Use same default features as training
            feature_columns = ['temperature', 'humidity']
            feature_columns = [col for col in feature_columns if col in data.columns]
            if not feature_columns:
                logger.warning("No valid feature columns found in data for anomaly prediction. Returning all normal.")
                return np.ones(len(data))

        # Prepare the feature matrix for prediction
        X = data[feature_columns].values
        
        try:
            return self.model.predict(X)
        except Exception as e:
            logger.error(f"Error predicting anomalies: {e}", exc_info=True)
            return np.ones(len(X)) # Return normal for all in case of error

    def load_model(self):
        """Loads a pre-trained anomaly detection model from disk."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.is_trained = True
                logger.info(f"Anomaly detector model loaded successfully from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load anomaly detector model from {self.model_path}: {e}", exc_info=True)
                self.is_trained = False
        else:
            logger.info(f"Anomaly detector model file not found at {self.model_path}. Will need retraining.")
            self.is_trained = False