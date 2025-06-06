import os

class Config:
    HOST = os.getenv("COAP_HOST", "0.0.0.0")
    PORT = int(os.getenv("COAP_PORT", 5683))
    DEVICE_ID = os.getenv("DEVICE_ID", "thermostat-01")