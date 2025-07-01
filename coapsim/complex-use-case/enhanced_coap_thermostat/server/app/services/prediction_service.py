# server/app/services/prediction_service.py
"""Your PredictionService - keep exactly as provided"""
import logging
from datetime import datetime, timedelta
import pandas as pd
import joblib 
import os
from typing import Optional, Dict, Any

from ..models.lstm_predictor import LSTMTemperaturePredictor
from ..models.anomaly_detector import AnomalyDetector 
from ..database.influxdb_client import InfluxDBClient

logger = logging.getLogger(__name__)

class PredictionService:
    """
    Manages the training, loading, and execution of ML models for predictions and anomaly detection.
    """
    def __init__(self, db_client: InfluxDBClient, lstm_predictor: LSTMTemperaturePredictor, anomaly_detector: AnomalyDetector):
        self.logger = logger
        self.lstm_predictor = lstm_predictor
        self.anomaly_detector = anomaly_detector
        self.db_client = db_client
        self.last_training: Optional[datetime] = None
        
        logger.info("PredictionService initialized.")
        self._load_models_on_startup()

    def _load_models_on_startup(self):
        """Load pre-trained models from disk"""
        self.logger.info("Attempting to load pre-trained prediction models...")
        try:
            # Load LSTM model
            if os.path.exists(self.lstm_predictor.model_path):
                try:
                    from tensorflow.keras.models import load_model
                    self.lstm_predictor.model = load_model(self.lstm_predictor.model_path)
                    self.lstm_predictor.is_trained = True
                    self.logger.info(f"LSTM model loaded from {self.lstm_predictor.model_path}")
                except Exception as e:
                    self.logger.error(f"Failed to load LSTM model: {e}")
                    self.lstm_predictor.is_trained = False

            # Load LSTM scaler
            if os.path.exists(self.lstm_predictor.scaler_path):
                self.lstm_predictor.scaler = joblib.load(self.lstm_predictor.scaler_path)
                self.logger.info(f"LSTM scaler loaded from {self.lstm_predictor.scaler_path}")
            else:
                self.logger.warning(f"LSTM scaler not found at {self.lstm_predictor.scaler_path}")
                self.lstm_predictor.is_trained = False

            # Load Anomaly Detector model
            self.anomaly_detector.load_model()

            if self.lstm_predictor.is_trained and self.anomaly_detector.is_trained:
                self.last_training = datetime.now()
                logger.info("All prediction models successfully loaded and active.")
            else:
                logger.warning("Not all prediction models could be loaded. Retraining will be required.")

        except Exception as e:
            logger.error(f"Overall error during model loading: {e}", exc_info=True)
            self.lstm_predictor.is_trained = False
            self.anomaly_detector.is_trained = False

    async def retrain_models(self) -> bool:
        """Retrain all ML models with recent data"""
        logger.info("Initiating prediction model retraining process...")
        try:
            # Get training data (last 30 days)
            training_data = await self.db_client.get_recent_data(hours=30*24)
            
            # Check for sufficient data for LSTM training
            if training_data.empty or len(training_data) < self.lstm_predictor.sequence_length * 2: 
                logger.warning(f"Insufficient data ({len(training_data)} records) for LSTM training")
                lstm_success = False
            else:
                lstm_success = self.lstm_predictor.train(training_data)
            
            # Train Anomaly Detector
            anomaly_features = ['temperature', 'humidity']
            available_anomaly_features = [f for f in anomaly_features if f in training_data.columns]
            
            anomaly_success = True
            if available_anomaly_features and not training_data.empty:
                anomaly_success = self.anomaly_detector.train(training_data, feature_columns=available_anomaly_features)
            else:
                logger.warning("No suitable features or data found for anomaly detector training")
                self.anomaly_detector.is_trained = False
                anomaly_success = False

            if lstm_success and anomaly_success:
                self.last_training = datetime.now()
                logger.info("All prediction models retrained successfully.")
                return True
            else:
                logger.warning(f"Model training incomplete. LSTM: {lstm_success}, Anomaly: {anomaly_success}")
                return False
            
        except Exception as e:
            logger.error(f"Error during prediction model retraining: {e}", exc_info=True)
            return False
    
    async def get_predictions(self, hours_ahead: int = 24) -> Optional[Dict[str, Any]]:
        """Get temperature predictions for upcoming hours"""
        if not self.lstm_predictor.is_trained:
            logger.warning("Prediction model not trained or loaded")
            return {
                "predictions": [],
                "hours_ahead": hours_ahead,
                "model_last_trained": self.last_training.isoformat() if self.last_training else "N/A",
                "confidence": 0.0,
                "message": "Prediction model not trained."
            }

        try:
            # Get recent data for prediction sequence
            recent_data = await self.db_client.get_recent_data(hours=self.lstm_predictor.sequence_length + 2)
            
            if recent_data.empty or len(recent_data) < self.lstm_predictor.sequence_length:
                logger.warning(f"Insufficient recent data for prediction")
                return {
                    "predictions": [],
                    "hours_ahead": hours_ahead,
                    "model_last_trained": self.last_training.isoformat() if self.last_training else "N/A",
                    "confidence": 0.1,
                    "message": "Insufficient recent data for prediction."
                }

            predictions = self.lstm_predictor.predict(recent_data, hours_ahead)
            
            if predictions:
                return {
                    "predictions": predictions,
                    "hours_ahead": hours_ahead,
                    "model_last_trained": self.last_training.isoformat() if self.last_training else "N/A",
                    "confidence": 0.8
                }
            else:
                logger.warning("LSTM predictor returned no predictions")
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
