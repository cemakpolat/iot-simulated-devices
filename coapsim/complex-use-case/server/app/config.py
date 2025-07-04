# server/app/config.py
import os
from pydantic_settings import BaseSettings
from typing import Optional

class ServerConfig(BaseSettings):
    # CoAP Device Connectivity Settings (how the server connects to the thermostat)
    COAP_DEVICE_HOST: str = os.getenv("COAP_DEVICE_HOST", "coap-device") # Docker service name
    COAP_DEVICE_PORT: int = int(os.getenv("COAP_DEVICE_PORT", 5683))
    COAP_DEVICE_SECURE_PORT: int = int(os.getenv("COAP_DEVICE_SECURE_PORT", 5684))
    ENABLE_DTLS_SERVER_CLIENT: bool = os.getenv("ENABLE_DTLS_SERVER_CLIENT", "true").lower() == "true"
    COAP_PSK_IDENTITY: str = os.getenv("COAP_PSK_IDENTITY", "thermostat") # Must match client's PSK_IDENTITY
    COAP_PSK_KEY: str = os.getenv("COAP_PSK_KEY", "secretkey123")       # Must match client's PSK_KEY
    
    # InfluxDB Configuration (for time-series data storage)
    INFLUXDB_URL: str = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
    INFLUXDB_TOKEN: str = os.getenv("INFLUXDB_TOKEN", "admin-token") # Token for full access to org/bucket
    INFLUXDB_ORG: str = os.getenv("INFLUXDB_ORG", "thermostat-org")
    INFLUXDB_BUCKET: str = os.getenv("INFLUXDB_BUCKET", "thermostat-data")
    
    # Redis Configuration (for caching, session management - to be implemented later)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")

    # Postgresql configuration
    DATABASE_URL:str =  os.getenv("DATABASE_URL", "postgresql://thermostat:password@postgres:5432/thermostat")
    
    # WebSocket server 
    WEBSOCKET_SERVER: str = os.getenv("WEBSOCKET_SERVER", "0.0.0.0")
    WEBSOCKET_PORT: int = int(os.getenv("WEBSOCKET_PORT", 8092))
    
    # JWT and token expiration settings
    JWT_SECRET: Optional[str] = os.getenv("JWT_SECRET", None)
    JWT_ALGORITHM: str= os.getenv("JWT_SECRET", "HS256")
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)  # 30 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7)     # 7 days

    # API Configuration (for FastAPI REST API - to be implemented later)
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8000))

    # Control Loop & ML Settings
    POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", 3)) # Interval for the server to poll the device (seconds)
    ML_RETRAIN_INTERVAL_HOURS: int = int(os.getenv("ML_RETRAIN_INTERVAL_HOURS", 24)) # How often to retrain ML models
    
    # Notification Settings (for email/webhooks - to be fully implemented later)
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    EMAIL_USERNAME: str = os.getenv("EMAIL_USERNAME") # Your email username
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD") # Your email app password (for Gmail, etc.)
    FROM_EMAIL: str = os.getenv("FROM_EMAIL")         # The email address to send from
    ALERT_EMAIL: str = os.getenv("ALERT_EMAIL", "admin@example.com") # Recipient for critical alerts
    WEBHOOK_URLS: str = os.getenv("WEBHOOK_URLS", "") # Comma-separated list of webhook endpoints
    

    # FCM Configuration

    FCM_SERVICE_ACCOUNT_PATH: Optional[str] = os.getenv("FCM_SERVICE_ACCOUNT_PATH")
    # FCM_SERVER_PORT: int = int(os.getenv("FCM_SERVER_PORT", "5001"))
    
    # Logging Level
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO") # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    class Config:
        env_file = ".env" # Specifies that settings should be loaded from a .env file
        env_file_encoding = 'utf-8'