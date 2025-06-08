import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential, load_model # <--- ADD load_model
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
        self.sequence_length = 24  # 24 hours of data (e.g., one day's hourly data)
        self.is_trained = False
        self.model_path = "models/lstm_temperature.h5" # Consistent path for model
        self.scaler_path = "models/temperature_scaler.pkl" # Consistent path for scaler
        logger.info("LSTMTemperaturePredictor initialized.")

    def prepare_data(self, data: pd.DataFrame):
        """
        Prepares time series data for LSTM training.
        Ensures required columns ('temperature', 'humidity', 'occupancy') are present.
        Adds 'hour' and 'day_of_week' features.
        Scales data using MinMaxScaler.
        """
        if data.empty or not all(col in data.columns for col in ['temperature', 'humidity', 'occupancy']):
            logger.warning("Insufficient or malformed data for LSTM data preparation. Skipping.")
            return np.array([]), np.array([])
        
        data_copy = data.copy() # Avoid SettingWithCopyWarning
        data_copy['hour'] = pd.to_datetime(data_copy['timestamp'], unit='s').dt.hour
        data_copy['day_of_week'] = pd.to_datetime(data_copy['timestamp'], unit='s').dt.dayofweek
        
        # Define features used by the model
        features = ['temperature', 'humidity', 'occupancy', 'hour', 'day_of_week']
        # Ensure all features exist in the dataframe before scaling
        actual_features = [f for f in features if f in data_copy.columns]
        if not actual_features:
            logger.warning("No valid features found in data for LSTM scaling. Cannot prepare data.")
            return np.array([]), np.array([])

        # Fit and transform the data using the scaler
        scaled_data = self.scaler.fit_transform(data_copy[actual_features])
        
        X, y = [], []
        # Create sequences of `self.sequence_length` for input (X) and next temperature for output (y)
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i])
            y.append(scaled_data[i, 0])  # Assuming temperature is the first feature to predict
            
        return np.array(X), np.array(y)
    
    def build_model(self, input_shape):
        """Builds the LSTM model architecture."""
        logger.info(f"Building LSTM model with input shape: {input_shape}")
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(25),
            Dense(1) # Output layer for single temperature prediction
        ])
        
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        return model
    
    def train(self, training_data: pd.DataFrame) -> bool:
        """Trains the LSTM model with provided training data."""
        logger.info(f"Starting LSTM model training with {len(training_data)} data points.")
        X, y = self.prepare_data(training_data)
        
        if len(X) == 0 or len(X) < 100: # Ensure enough samples for meaningful training
            logger.warning(f"Not enough prepared data ({len(X)} samples) for LSTM training. Skipping.")
            self.is_trained = False
            return False
            
        self.model = self.build_model((X.shape[1], X.shape[2]))
        
        try:
            # Train the model
            self.model.fit(X, y, epochs=50, batch_size=32, validation_split=0.2, verbose=0)
            self.is_trained = True
            logger.info("LSTM model trained successfully.")

            # Save the trained model and scaler to disk for persistence
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            self.model.save(self.model_path) # Saves model architecture, weights, and optimizer state
            joblib.dump(self.scaler, self.scaler_path)
            logger.info(f"LSTM model saved to {self.model_path} and scaler to {self.scaler_path}")
            return True
        except Exception as e:
            logger.error(f"Error during LSTM model training: {e}", exc_info=True)
            self.is_trained = False
            return False
    
    def predict(self, recent_data: pd.DataFrame, hours_ahead: int = 1) -> list | None:
        """
        Predicts temperature for the next `hours_ahead` using the trained LSTM model.
        :param recent_data: Pandas DataFrame containing the most recent sensor data
                            (at least `self.sequence_length` records).
        :param hours_ahead: Number of hours into the future to predict.
        :return: A list of predicted temperatures, or None if prediction fails.
        """
        if not self.is_trained or self.model is None or not hasattr(self.scaler, 'data_min_'):
            logger.warning("LSTM model not trained or scaler not fitted. Cannot make predictions.")
            return None
            
        if recent_data.empty or len(recent_data) < self.sequence_length:
            logger.warning(f"Insufficient recent data ({len(recent_data)} records) for LSTM prediction. Need {self.sequence_length}.")
            return None

        # Prepare input sequence for prediction
        features = ['temperature', 'humidity', 'occupancy', 'hour', 'day_of_week']
        # Create a copy to avoid modifying the original DataFrame and potential warnings
        recent_data_copy = recent_data.copy()
        recent_data_copy['hour'] = pd.to_datetime(recent_data_copy['timestamp'], unit='s').dt.hour
        recent_data_copy['day_of_week'] = pd.to_datetime(recent_data_copy['timestamp'], unit='s').dt.dayofweek
        
        # Filter features that are actually present in the data
        actual_features = [f for f in features if f in recent_data_copy.columns]
        if not actual_features:
            logger.error("No valid features found in recent data for scaling during prediction.")
            return None
            
        # Take the tail (most recent) data matching the sequence length
        # Transform it using the *fitted* scaler
        scaled_input_sequence = self.scaler.transform(recent_data_copy[actual_features].tail(self.sequence_length))
        # Reshape for LSTM input (batch_size, timesteps, features)
        X_input = scaled_input_sequence.reshape(1, self.sequence_length, len(actual_features))
        
        predictions = []
        for _ in range(hours_ahead):
            # Predict the next scaled temperature
            pred_scaled = self.model.predict(X_input, verbose=0)[0][0]
            
            # To inverse transform the prediction, we need to create a dummy array
            # with the same number of features that the scaler expects.
            # The prediction is placed in the first feature position (temperature).
            dummy_features_for_inverse = np.zeros((1, len(actual_features)))
            dummy_features_for_inverse[0, 0] = pred_scaled 
            
            # Inverse transform to get the temperature in its original scale
            pred_original_scale = self.scaler.inverse_transform(dummy_features_for_inverse)[0, 0]
            predictions.append(pred_original_scale)
            
            # Update the input sequence for the next prediction (autoregressive prediction)
            # Shift the window by one timestep, and append the new prediction (scaled)
            new_row_scaled_for_next_pred = scaled_input_sequence[-1:].copy() # Take the last row of the input sequence
            new_row_scaled_for_next_pred[0, 0] = pred_scaled # Update its temperature feature
            X_input = np.concatenate([X_input[0, 1:], new_row_scaled_for_next_pred]).reshape(1, self.sequence_length, len(actual_features))
            
        logger.info(f"Generated {len(predictions)} temperature predictions for next {hours_ahead} hours.")
        return [round(p, 2) for p in predictions] # Round for cleaner output