# app/services/ml_service.py
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

from .base import BaseService
from ..models.ml.ensemble_model import EnsemblePredictor
from ..models.ml.lstm_predictor import LSTMTemperaturePredictor
from ..models.ml.anomaly_detector import AnomalyDetector
from ..models.ml.energy_optimizer import EnergyOptimizer
from ..repositories.timeseries_repository import TimeseriesRepository
from ..core.exceptions import MLModelError

class MLService(BaseService):
    """Service for orchestrating machine learning operations."""
    
    def __init__(self, timeseries_repo: TimeseriesRepository):
        super().__init__()
        self.timeseries_repo = timeseries_repo
        
        # Initialize ML models
        self.lstm_predictor = LSTMTemperaturePredictor()
        self.anomaly_detector = AnomalyDetector()
        self.energy_optimizer = EnergyOptimizer()
        self.ensemble_model = EnsemblePredictor(
            lstm_model=self.lstm_predictor,
            anomaly_detector=self.anomaly_detector,
            energy_optimizer=self.energy_optimizer
        )
        
        self.last_training: Optional[datetime] = None
        self.retrain_interval_hours = 24
    
    async def initialize(self) -> bool:
        """Initialize ML service and attempt to load pre-trained models."""
        try:
            # Try to load existing models
            await self._load_models()
            
            self.logger.info("ML service initialized successfully")
            return await super().initialize()
        except Exception as e:
            self.logger.error(f"Failed to initialize ML service: {e}")
            return False
    
    async def _load_models(self):
        """Load pre-trained models from disk."""
        try:
            # Load models in parallel
            await asyncio.gather(
                self._load_lstm_model(),
                self._load_anomaly_model(),
                return_exceptions=True
            )
            
            if self.lstm_predictor.is_trained and self.anomaly_detector.is_trained:
                self.last_training = datetime.now()
                self.logger.info("All ML models loaded successfully")
            else:
                self.logger.warning("Some ML models could not be loaded")
                
        except Exception as e:
            self.logger.error(f"Error loading ML models: {e}")
    
    async def _load_lstm_model(self):
        """Load LSTM model asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.lstm_predictor.load_model)
    
    async def _load_anomaly_model(self):
        """Load anomaly detection model asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.anomaly_detector.load_model)
    
    async def make_decision(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make HVAC control decision using ensemble model."""
        self._validate_initialized()
        
        try:
            # Get historical data for ML models
            historical_data = await self.timeseries_repo.get_recent_data(hours=48)
            
            # Make decision using ensemble model
            decision = self.ensemble_model.make_decision(sensor_data, historical_data)
            
            self.logger.debug(f"ML decision made: {decision['action']} (confidence: {decision['confidence']:.2f})")
            return decision
            
        except Exception as e:
            self.logger.error(f"Error making ML decision: {e}")
            # Return safe fallback decision
            return {
                "action": "off",
                "target_temperature": 22.0,
                "mode": "auto",
                "fan_speed": "auto",
                "reasoning": [f"ML service error: {str(e)}"],
                "confidence": 0.0,
                "predictions": [],
                "energy_schedule": []
            }
    
    async def get_predictions(self, device_id: str, hours_ahead: int = 24) -> Dict[str, Any]:
        """Get temperature predictions."""
        self._validate_initialized()
        
        if not self.lstm_predictor.is_trained:
            return {
                "predictions": [],
                "hours_ahead": hours_ahead,
                "confidence": 0.0,
                "message": "LSTM model not trained"
            }
        
        try:
            # Get recent data for prediction
            recent_data = await self.timeseries_repo.get_recent_data(
                hours=self.lstm_predictor.sequence_length + 2
            )
            
            if recent_data.empty:
                return {
                    "predictions": [],
                    "hours_ahead": hours_ahead,
                    "confidence": 0.1,
                    "message": "Insufficient historical data"
                }
            
            # Make predictions
            predictions = self.lstm_predictor.predict(recent_data, hours_ahead)
            
            return {
                "predictions": predictions or [],
                "hours_ahead": hours_ahead,
                "model_last_trained": self.last_training.isoformat() if self.last_training else None,
                "confidence": 0.8 if predictions else 0.2
            }
            
        except Exception as e:
            self.logger.error(f"Error getting predictions: {e}")
            raise MLModelError(f"Prediction failed: {str(e)}")
    
    async def detect_anomalies(self, data: pd.DataFrame) -> List[bool]:
        """Detect anomalies in sensor data."""
        self._validate_initialized()
        
        if not self.anomaly_detector.is_trained:
            self.logger.warning("Anomaly detector not trained")
            return [False] * len(data)
        
        try:
            predictions = self.anomaly_detector.predict(data, ['temperature', 'humidity'])
            return [pred == -1 for pred in predictions]  # -1 indicates anomaly
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {e}")
            return [False] * len(data)
    
    async def should_retrain(self) -> bool:
        """Check if models should be retrained."""
        if not self.last_training:
            return True
        
        time_since_training = datetime.now() - self.last_training
        return time_since_training.total_seconds() / 3600 >= self.retrain_interval_hours
    
    async def retrain_models(self) -> bool:
        """Retrain all ML models with recent data."""
        self._validate_initialized()
        
        try:
            self.logger.info("Starting ML model retraining...")
            
            # Get training data (30 days)
            training_data = await self.timeseries_repo.get_recent_data(hours=30*24)
            
            if training_data.empty:
                self.logger.warning("No data available for model training")
                return False
            
            # Train models in parallel
            results = await asyncio.gather(
                self._train_lstm(training_data),
                self._train_anomaly_detector(training_data),
                return_exceptions=True
            )
            
            lstm_success = results[0] if not isinstance(results[0], Exception) else False
            anomaly_success = results[1] if not isinstance(results[1], Exception) else False
            
            if lstm_success and anomaly_success:
                self.last_training = datetime.now()
                self.logger.info("All ML models retrained successfully")
                return True
            else:
                self.logger.warning(f"Model training partial success: LSTM={lstm_success}, Anomaly={anomaly_success}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during model retraining: {e}")
            return False
    
    async def _train_lstm(self, data: pd.DataFrame) -> bool:
        """Train LSTM model asynchronously."""
        if len(data) < self.lstm_predictor.sequence_length * 2:
            self.logger.warning("Insufficient data for LSTM training")
            return False
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.lstm_predictor.train, data)
    
    async def _train_anomaly_detector(self, data: pd.DataFrame) -> bool:
        """Train anomaly detector asynchronously."""
        feature_columns = ['temperature', 'humidity']
        available_features = [col for col in feature_columns if col in data.columns]
        
        if not available_features:
            self.logger.warning("No suitable features for anomaly detection training")
            return False
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.anomaly_detector.train, data, available_features)