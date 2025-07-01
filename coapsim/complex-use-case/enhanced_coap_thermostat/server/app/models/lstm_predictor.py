# server/app/models/lstm_predictor.py
"""Your LSTMTemperaturePredictor - keep exactly as provided"""
import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
import joblib
import os
import logging

logger = logging.getLogger(__name__)

class LSTMTemperaturePredictor:
    def __init__(self):
        self.model = None
        self.scaler = MinMaxScaler()
        self.sequence_length = 24
        self.is_trained = False
        self.model_path = "models/lstm_temperature.h5"
        self.scaler_path = "models/temperature_scaler.pkl"
        logger.info("LSTMTemperaturePredictor initialized.")

    def prepare_data(self, data: pd.DataFrame):
        """Prepare time series data for LSTM training"""
        if data.empty or not all(col in data.columns for col in ['temperature', 'humidity', 'occupancy']):
            logger.warning("Insufficient or malformed data for LSTM data preparation")
            return np.array([]), np.array([])
        
        data_copy = data.copy()
        data_copy['hour'] = pd.to_datetime(data_copy['timestamp'], unit='s').dt.hour
        data_copy['day_of_week'] = pd.to_datetime(data_copy['timestamp'], unit='s').dt.dayofweek
        
        features = ['temperature', 'humidity', 'occupancy', 'hour', 'day_of_week']
        actual_features = [f for f in features if f in data_copy.columns]
        if not actual_features:
            logger.warning("No valid features found in data for LSTM scaling")
            return np.array([]), np.array([])

        scaled_data = self.scaler.fit_transform(data_copy[actual_features])
        
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i])
            y.append(scaled_data[i, 0])  # Temperature is first feature
            
        return np.array(X), np.array(y)
    
    def build_model(self, input_shape):
        """Build the LSTM model architecture"""
        logger.info(f"Building LSTM model with input shape: {input_shape}")
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        return model
    
    def train(self, training_data: pd.DataFrame) -> bool:
        """Train the LSTM model with provided training data"""
        logger.info(f"Starting LSTM model training with {len(training_data)} data points")
        X, y = self.prepare_data(training_data)
        
        if len(X) == 0 or len(X) < 100:
            logger.warning(f"Not enough prepared data ({len(X)} samples) for LSTM training")
            self.is_trained = False
            return False
            
        self.model = self.build_model((X.shape[1], X.shape[2]))
        
        try:
            self.model.fit(X, y, epochs=50, batch_size=32, validation_split=0.2, verbose=0)
            self.is_trained = True
            logger.info("LSTM model trained successfully")

            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            self.model.save(self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info(f"LSTM model saved to {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Error during LSTM model training: {e}", exc_info=True)
            self.is_trained = False
            return False
    
    def predict(self, recent_data: pd.DataFrame, hours_ahead: int = 1):
        """Predict temperature for the next hours_ahead using trained LSTM model"""
        if not self.is_trained or self.model is None or not hasattr(self.scaler, 'data_min_'):
            logger.warning("LSTM model not trained or scaler not fitted")
            return None
            
        if recent_data.empty or len(recent_data) < self.sequence_length:
            logger.warning(f"Insufficient recent data ({len(recent_data)} records) for LSTM prediction")
            return None

        features = ['temperature', 'humidity', 'occupancy', 'hour', 'day_of_week']
        recent_data_copy = recent_data.copy()
        recent_data_copy['hour'] = pd.to_datetime(recent_data_copy['timestamp'], unit='s').dt.hour
        recent_data_copy['day_of_week'] = pd.to_datetime(recent_data_copy['timestamp'], unit='s').dt.dayofweek
        
        actual_features = [f for f in features if f in recent_data_copy.columns]
        if not actual_features:
            logger.error("No valid features found in recent data for scaling during prediction")
            return None
            
        scaled_input_sequence = self.scaler.transform(recent_data_copy[actual_features].tail(self.sequence_length))
        X_input = scaled_input_sequence.reshape(1, self.sequence_length, len(actual_features))
        
        predictions = []
        for _ in range(hours_ahead):
            pred_scaled = self.model.predict(X_input, verbose=0)[0][0]
            
            dummy_features_for_inverse = np.zeros((1, len(actual_features)))
            dummy_features_for_inverse[0, 0] = pred_scaled 
            
            pred_original_scale = self.scaler.inverse_transform(dummy_features_for_inverse)[0, 0]
            predictions.append(pred_original_scale)
            
            new_row_scaled_for_next_pred = scaled_input_sequence[-1:].copy()
            new_row_scaled_for_next_pred[0, 0] = pred_scaled
            X_input = np.concatenate([X_input[0, 1:], new_row_scaled_for_next_pred]).reshape(1, self.sequence_length, len(actual_features))
            
        logger.info(f"Generated {len(predictions)} temperature predictions for next {hours_ahead} hours")
        return [round(p, 2) for p in predictions]

