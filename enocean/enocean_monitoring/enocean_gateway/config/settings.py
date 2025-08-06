# src/config/settings.py
"""
Configuration management for EnOcean Gateway
"""

import os
from dataclasses import dataclass

@dataclass
class Settings:
    """Configuration settings for the EnOcean Gateway"""

    # Serial configuration
    PORT: str
    BAUD_RATE: int

    # MQTT configuration
    MQTT_BROKER: str
    MQTT_PORT: int
    MQTT_TOPIC: str
    MQTT_CLIENT_ID: str

    # Application settings
    DEBUG: bool

    def __init__(self):
        """Initialize settings from environment variables"""
        self.PORT = os.getenv('ENOCEAN_DEVICE', '/dev/cu.usbserial-FT6U7YM1')
        self.BAUD_RATE = int(os.getenv('ENOCEAN_BAUD', '57600'))

        self.MQTT_BROKER = os.getenv('MQTT_BROKER', 'broker.emqx.io')
        #self.MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
        self.MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
        self.MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'enocean/sensors')
        self.MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'enocean_gateway')

         # Dead Letter Queue Settings
        self.DLQ_STORAGE_PATH: str = os.getenv('DLQ_STORAGE_PATH', 'data/dead_letter_queue.json')
        self.DLQ_MAX_SIZE: int = int(os.getenv('DLQ_MAX_SIZE', '1000'))
        
        # Enhanced Error Handling Settings
        self.DB_RETRY_ATTEMPTS: int = int(os.getenv('DB_RETRY_ATTEMPTS', '3'))
        self.SERIAL_FAILURE_THRESHOLD: int = int(os.getenv('SERIAL_FAILURE_THRESHOLD', '3'))
        self.SERIAL_TIMEOUT: int = int(os.getenv('SERIAL_TIMEOUT', '30'))
        self.DB_FAILURE_THRESHOLD: int = int(os.getenv('DB_FAILURE_THRESHOLD', '5'))
        self.DB_TIMEOUT: int = int(os.getenv('DB_TIMEOUT', '60'))
        self.PACKET_RETRY_ATTEMPTS: int = int(os.getenv('PACKET_RETRY_ATTEMPTS', '3'))

        self.DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'

    def validate(self) -> bool:
        """Validate configuration settings"""
        if not self.PORT:
            return False
        if not (1 <= self.BAUD_RATE <= 115200):
            return False
        if not self.MQTT_BROKER:
            return False
        if not (1 <= self.MQTT_PORT <= 65535):
            return False
        return True

    def to_dict(self) -> dict:
        """Convert settings to dictionary"""
        return {
            'port': self.PORT,
            'baud_rate': self.BAUD_RATE,
            'mqtt_broker': self.MQTT_BROKER,
            'mqtt_port': self.MQTT_PORT,
            'mqtt_topic': self.MQTT_TOPIC,
            'mqtt_client_id': self.MQTT_CLIENT_ID,
            'debug': self.DEBUG
        }