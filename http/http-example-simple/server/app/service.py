from model import AnomalyModel
import logging

logger = logging.getLogger(__name__)

_latest_readings = {}

class InferenceService:
    def __init__(self):
        self.model = AnomalyModel()

    def infer(self, data):
        if not isinstance(data, dict):
            raise ValueError("Invalid payload: not a JSON object")

        device_id = data.get('device_id')
        temperature = data.get('temperature')

        if not device_id or not isinstance(device_id, str):
            raise ValueError("Missing or invalid 'device_id'")

        if temperature is None or not isinstance(temperature, (int, float)):
            raise ValueError("Missing or invalid 'temperature'")

        is_anomaly, confidence = self.model.predict_with_confidence(temperature)
        result = 'anomaly' if is_anomaly else 'normal'

        logger.info(f"Device {device_id}: {temperature}°C → {result} (confidence: {confidence})")

        result = {
            'device_id': device_id,
            'temperature': round(temperature, 2),
            'result': result,
            'confidence': confidence,
            'timestamp': self._get_timestamp()
        }
        
        _latest_readings[data['device_id']] = result
        return result

    def _get_timestamp(self):
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"

    def get_latest_readings(self):
        return list(_latest_readings.values())