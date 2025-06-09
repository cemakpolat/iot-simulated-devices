import logging
from datetime import datetime, timedelta
import pandas as pd
import joblib 
import os
from typing import Optional, Dict, Any  # Add this import

from ..models.lstm_predictor import LSTMTemperaturePredictor
from ..models.anomaly_detector import AnomalyDetector 
from ..database.influxdb_client import InfluxDBClient

logger = logging.getLogger(__name__)

class PredictionService:
    """
    Manages the training, loading, and execution of ML models for predictions and anomaly detection.
    """
    def __init__(self, db_client: InfluxDBClient, lstm_predictor: LSTMTemperaturePredictor, anomaly_detector: AnomalyDetector):
        """
        Initializes the PredictionService with injected database client and ML model instances.
        """
        self.logger = logger
        self.lstm_predictor = lstm_predictor # Injected LSTM model instance
        self.anomaly_detector = anomaly_detector # Injected AnomalyDetector instance
        self.db_client = db_client # Injected InfluxDB client instance
        self.last_training: Optional[datetime] = None # Timestamp of the last successful model training
        
        logger.info("PredictionService initialized.")

        # Attempt to load pre-trained models on startup.
        # This ensures that if the server restarts, it can resume operations without immediate retraining.
        self._load_models_on_startup()

    def _load_models_on_startup(self):
        """
        Attempts to load pre-trained LSTM and AnomalyDetector models from disk.
        """
        self.logger.info("Attempting to load pre-trained prediction models...")
        try:
            # Load LSTM model
            if os.path.exists(self.lstm_predictor.model_path):
                # For Keras models saved with model.save(), load_model() works.
                # If only weights were saved, rebuild the model structure first.
                try:
                    # Assuming model.save() was used, load_model can load structure + weights.
                    from tensorflow.keras.models import load_model # Import here to avoid circular dependency issues at top
                    self.lstm_predictor.model = load_model(self.lstm_predictor.model_path)
                    self.lstm_predictor.is_trained = True # Mark as trained if model loaded
                    self.logger.info(f"LSTM model loaded from {self.lstm_predictor.model_path}")
                except Exception as e:
                    self.logger.error(f"Failed to load full LSTM model from {self.lstm_predictor.model_path}. Will need retraining. Error: {e}")
                    self.lstm_predictor.is_trained = False

            # Load LSTM scaler
            if os.path.exists(self.lstm_predictor.scaler_path):
                self.lstm_predictor.scaler = joblib.load(self.lstm_predictor.scaler_path)
                self.logger.info(f"LSTM scaler loaded from {self.lstm_predictor.scaler_path}")
            else:
                self.logger.warning(f"LSTM scaler not found at {self.lstm_predictor.scaler_path}. LSTM model might not be usable.")
                self.lstm_predictor.is_trained = False # Model might be loaded but scaler is missing

            # Load Anomaly Detector model
            self.anomaly_detector.load_model() # AnomalyDetector class has its own load_model method

            if self.lstm_predictor.is_trained and self.anomaly_detector.is_trained:
                self.last_training = datetime.now() # Assume current time for loaded models' "last trained"
                logger.info("All prediction models successfully loaded and active.")
            else:
                logger.warning("Not all prediction models could be loaded. Retraining will be required.")

        except Exception as e:
            logger.error(f"Overall error during model loading: {e}", exc_info=True)
            self.lstm_predictor.is_trained = False
            self.anomaly_detector.is_trained = False


    async def retrain_models(self) -> bool:
        """
        Retrains all ML models (LSTM and Anomaly Detector) with recent data from InfluxDB.
        :return: True if all models were successfully trained, False otherwise.
        """
        logger.info("Initiating prediction model retraining process...")
        try:
            # 1. Get training data (e.g., last 30 days of combined sensor data)
            training_data = await self.db_client.get_recent_data(hours=30*24)
            
            # Check for sufficient data for LSTM training
            if training_data.empty or len(training_data) < self.lstm_predictor.sequence_length * 2: 
                logger.warning(f"Insufficient data ({len(training_data)} records) for LSTM training. Need at least {self.lstm_predictor.sequence_length * 2} records. Skipping LSTM training.")
                lstm_success = False
            else:
                # 2. Train LSTM model
                lstm_success = self.lstm_predictor.train(training_data)
            
            # 3. Train Anomaly Detector
            anomaly_features = ['temperature', 'humidity'] # Features suitable for anomaly detection
            # Filter to ensure only existing features are passed
            available_anomaly_features = [f for f in anomaly_features if f in training_data.columns]
            
            anomaly_success = True
            if available_anomaly_features and not training_data.empty: # Only train if features and data are available
                anomaly_success = self.anomaly_detector.train(training_data, feature_columns=available_anomaly_features)
            else:
                logger.warning("No suitable features or data found for anomaly detector training. Skipping.")
                self.anomaly_detector.is_trained = False # Explicitly mark as not trained
                anomaly_success = False # Consider this a failure for overall retraining

            if lstm_success and anomaly_success:
                self.last_training = datetime.now() # Update last training timestamp
                logger.info("All prediction models retrained successfully.")
                return True
            else:
                logger.warning(f"One or more prediction models failed training. LSTM success: {lstm_success}, Anomaly success: {anomaly_success}.")
                return False
            
        except Exception as e:
            logger.error(f"Overall error during prediction model retraining: {e}", exc_info=True)
            return False
    
    async def get_predictions(self, hours_ahead: int = 24) -> Optional[Dict[str, Any]]:
        """
        Retrieves temperature predictions for upcoming hours using the trained LSTM model.
        :param hours_ahead: The number of hours into the future for which to predict.
        :return: A dictionary containing predictions and model metadata, or None if unavailable.
        """
        if not self.lstm_predictor.is_trained:
            logger.warning("Prediction model not trained or loaded. Cannot provide predictions.")
            return {
                "predictions": [],
                "hours_ahead": hours_ahead,
                "model_last_trained": self.last_training.isoformat() if self.last_training else "N/A",
                "confidence": 0.0,
                "message": "Prediction model not trained."
            }

        try:
            # Get enough recent data to form the initial prediction sequence for the LSTM
            recent_data = await self.db_client.get_recent_data(hours=self.lstm_predictor.sequence_length + 2) # Fetch a bit more than sequence length
            
            if recent_data.empty or len(recent_data) < self.lstm_predictor.sequence_length:
                logger.warning(f"Insufficient recent data ({len(recent_data)} records) for prediction. Need at least {self.lstm_predictor.sequence_length}. Returning empty predictions.")
                return {
                    "predictions": [],
                    "hours_ahead": hours_ahead,
                    "model_last_trained": self.last_training.isoformat() if self.last_training else "N/A",
                    "confidence": 0.1, # Low confidence due to data scarcity
                    "message": "Insufficient recent data for prediction."
                }

            predictions = self.lstm_predictor.predict(recent_data, hours_ahead)
            
            if predictions:
                return {
                    "predictions": predictions,
                    "hours_ahead": hours_ahead,
                    "model_last_trained": self.last_training.isoformat() if self.last_training else "N/A",
                    "confidence": 0.8 # Placeholder for prediction confidence, can be derived from model metrics
                }
            else:
                logger.warning("LSTM predictor returned no predictions.")
                return {
                    "predictions": [],
                    "hours_ahead": hours_ahead,
                    "model_last_trained": self.last_training.isoformat() if self.last_training else "N/A",
                    "confidence": 0.2,
                    "message": "Prediction failed internally in LSTM model."
                }
            
        except Exception as e:
            logger.error(f"Error getting predictions: {e}", exc_info=True)
            return {
                "predictions": [],
                "hours_ahead": hours_ahead,
                "model_last_trained": self.last_training.isoformat() if self.last_training else "N/A",
                "confidence": 0.0,
                "message": f"Prediction service error: {e}"
            }