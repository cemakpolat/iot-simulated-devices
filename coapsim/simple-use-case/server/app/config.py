import os

class Config:
    DEVICE_HOST = os.getenv("COAP_DEVICE_HOST", "client")
    DEVICE_PORT = int(os.getenv("COAP_PORT", 5683))
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 3))