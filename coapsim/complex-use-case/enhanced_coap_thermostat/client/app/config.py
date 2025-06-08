# client/app/config.py
import os
from typing import Dict, Any
from pydantic_settings import BaseSettings

class DeviceConfig(BaseSettings):
    # Device Identity
    DEVICE_ID: str = os.getenv("DEVICE_ID", "smart-thermostat-01")
    DEVICE_TYPE: str = "thermostat"
    FIRMWARE_VERSION: str = "2.1.0"
    
    # Network Configuration
    HOST: str = os.getenv("COAP_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("COAP_PORT", 5683))
    SECURE_PORT: int = int(os.getenv("COAPS_PORT", 5684))
    
    # Security
    ENABLE_DTLS: bool = os.getenv("ENABLE_DTLS", "true").lower() == "true"
    PSK_IDENTITY: str = os.getenv("PSK_IDENTITY", "thermostat")
    PSK_KEY: str = os.getenv("PSK_KEY", "secretkey123")
    
    # Sensor Configuration
    SENSOR_UPDATE_INTERVAL: int = int(os.getenv("SENSOR_INTERVAL", 2))
    ENABLE_OCCUPANCY_SENSOR: bool = True
    ENABLE_AIR_QUALITY_SENSOR: bool = True
    
    # Performance
    MAX_PAYLOAD_SIZE: int = 1024
    COAP_TIMEOUT: int = 10
    
    class Config:
        env_file = ".env"