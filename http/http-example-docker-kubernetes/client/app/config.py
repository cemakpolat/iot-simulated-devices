import os
import logging
import socket
class Config:
    # The endpoint now posts to /data
    SERVER_URL = os.getenv("SERVER_URL", "http://server:5000/data") 
    # Device ID can be set via environment variable for running multiple clients
    DEVICE_ID = os.getenv("DEVICE_ID", "default-device-id")
    INTERVAL = int(os.getenv("SEND_INTERVAL", 2))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    @classmethod
    def setup_logging(cls):
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - [%(device_id)s] %(message)s'
        )
