import requests
import time
import logging
from datetime import datetime
from sensors import TempSensor, HumiditySensor # Import multiple sensors
from config import Config

class IoTDevice:
    def __init__(self):
        self.config = Config()
        # A device can now have multiple sensors
        self.sensors = {
            "temperature": TempSensor(),
            "humidity": HumiditySensor()
        }
        Config.setup_logging()
        # Create a logger adapter to include device_id in all logs
        self.logger = logging.LoggerAdapter(logging.getLogger(__name__), {'device_id': self.config.DEVICE_ID})


    def send_reading(self):
        # Build a list of metrics from all attached sensors
        metrics = []
        for sensor_type, sensor_instance in self.sensors.items():
            metrics.append({
                "type": sensor_type,
                "value": sensor_instance.read()
            })

        payload = {
            "device_id": self.config.DEVICE_ID,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": metrics
        }
        
        try:
            self.logger.info(f"Sending data: {payload['metrics']}")
            response = requests.post(self.config.SERVER_URL, json=payload, timeout=5)
            response.raise_for_status() # Raises an exception for 4xx/5xx status codes
            self.logger.info(f"Data accepted by server (Status: {response.status_code})")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send reading: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")

    def run(self):
        self.logger.info(f"Starting device...")
        try:
            while True:
                self.send_reading()
                time.sleep(self.config.INTERVAL)
        except KeyboardInterrupt:
            self.logger.info("Device stopped by user.")