import os
import logging

class Config:
    HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    PORT = int(os.getenv("SERVER_PORT", 5000))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    ACTIVE_DEVICE_TIMEOUT_SECONDS = int(os.getenv("SERVER_PORT", 60))
    @classmethod
    def setup_logging(cls):
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )