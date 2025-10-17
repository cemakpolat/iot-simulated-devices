import logging
from threading import Thread, Lock
from datetime import datetime
from models import ModelRegistry

logger = logging.getLogger(__name__)

class DataProcessor:
    # It now accepts the shared objects during initialization
    def __init__(self, data_queue, latest_readings):
        self.data_queue = data_queue
        self._latest_readings = latest_readings # This is now a shared Manager.dict
        self.model_registry = ModelRegistry()
        self._lock = Lock() # Locks are still useful for complex operations if needed

        self.worker = Thread(target=self._process_queue, daemon=True)
        self.worker.start()
        logger.info("Data processing worker thread started.")

    def submit_data(self, data):
        """Adds incoming data to the SHARED queue for processing."""
        if not isinstance(data, dict):
            raise ValueError("Payload must be a JSON object.")
        
        device_id = data.get('device_id')
        metrics = data.get('metrics')

        if not device_id or not isinstance(device_id, str):
            raise ValueError("Missing or invalid 'device_id'.")
        if not metrics or not isinstance(metrics, list):
            raise ValueError("Missing or invalid 'metrics' list.")
            
        self.data_queue.put(data)

    def _process_queue(self):
        """The main loop for the worker thread."""
        while True:
            data = self.data_queue.get()
            device_id = data['device_id']
            logger.debug(f"Processing data for device: {device_id}")
            
            processed_metrics = []
            for metric in data.get('metrics', []):
                metric_type = metric.get('type')
                value = metric.get('value')
                
                model = self.model_registry.get_model(metric_type)
                if model:
                    result, confidence = model.predict(value)
                    processed_metrics.append({
                        'type': metric_type,
                        'value': value,
                        'result': result,
                        'confidence': confidence
                    })
                else:
                    logger.warning(f"No model found for metric type: {metric_type}")

            # The Manager dict proxy handles its own locking
            self._latest_readings[device_id] = {
                'device_id': device_id,
                'metrics': processed_metrics,
                'timestamp': datetime.utcnow().isoformat() + "Z"
            }
            self.data_queue.task_done()

    def get_latest_readings(self):
        """Gets the latest processed data from the SHARED dictionary."""
        # Convert manager dict proxy to a regular list for JSON serialization
        return list(self._latest_readings.values())