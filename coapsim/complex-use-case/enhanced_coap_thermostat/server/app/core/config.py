# app/core/config.py
import os
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, validator, Field
from functools import lru_cache

class Settings(BaseSettings):
    """Centralized application configuration with validation."""
    
    # Application
    APP_NAME: str = "Smart Thermostat AI API"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(default="development", regex="^(development|staging|production)$")
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Security & JWT
    JWT_SECRET: str = Field(default="your-secret-key", min_length=16)  # Your original default
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Database URLs
    DATABASE_URL: str = "postgresql://thermostat:password@postgres:5432/thermostat"
    
    # InfluxDB Configuration (for time-series data storage)
    INFLUXDB_URL: str = "http://influxdb:8086"
    INFLUXDB_TOKEN: str = "admin-token"
    INFLUXDB_ORG: str = "thermostat-org"
    INFLUXDB_BUCKET: str = "thermostat-data"
    
    # Redis Configuration (for caching, session management)
    REDIS_URL: str = "redis://redis:6379"
    
    # CoAP Device Connectivity Settings (how the server connects to the thermostat)
    COAP_DEVICE_HOST: str = "coap-device"  # Docker service name
    COAP_DEVICE_PORT: int = 5683
    COAP_DEVICE_SECURE_PORT: int = 5684
    ENABLE_DTLS_SERVER_CLIENT: bool = True  # Your original default
    COAP_PSK_IDENTITY: str = "thermostat"   # Must match client's PSK_IDENTITY
    COAP_PSK_KEY: str = "secretkey123"      # Must match client's PSK_KEY
    
    # Control Loop & ML Settings
    POLL_INTERVAL: int = 3  # Interval for the server to poll the device (seconds)
    ML_RETRAIN_INTERVAL_HOURS: int = 24  # How often to retrain ML models
    WEBSOCKET_PORT: int = 8092
    
    # Notification Settings (for email/webhooks)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_USERNAME: Optional[str] = None  # Your email username
    EMAIL_PASSWORD: Optional[str] = None  # Your email app password (for Gmail, etc.)
    FROM_EMAIL: Optional[str] = None      # The email address to send from
    ALERT_EMAIL: str = "admin@example.com"  # Recipient for critical alerts
    WEBHOOK_URLS: str = ""  # Comma-separated list of webhook endpoints
    
    # FCM Configuration
    FCM_PROJECT_ID: Optional[str] = None
    FCM_PRIVATE_KEY_ID: Optional[str] = None
    FCM_PRIVATE_KEY: Optional[str] = None
    FCM_CLIENT_EMAIL: Optional[str] = None
    FCM_CLIENT_ID: Optional[str] = None
    FCM_SERVICE_ACCOUNT_PATH: Optional[str] = None
    FCM_SERVER_PORT: int = 5001
    
    # Logging Level
    LOG_LEVEL: str = Field(default="INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # ML Model Paths
    MODEL_STORAGE_PATH: str = "models"
    
    @validator("JWT_SECRET")
    def validate_jwt_secret(cls, v):
        if len(v) < 16:  # More reasonable minimum for JWT secrets
            raise ValueError("JWT_SECRET must be at least 16 characters long")
        return v
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("WEBHOOK_URLS", pre=True)
    def parse_webhook_urls(cls, v):
        if isinstance(v, str) and v:
            return [url.strip() for url in v.split(",") if url.strip()]
        return []
    
    @validator("ENABLE_DTLS_SERVER_CLIENT", pre=True)
    def parse_dtls_setting(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)
    
    @property
    def database_config(self) -> Dict[str, Any]:
        """Database configuration for SQLAlchemy."""
        return {
            "url": self.DATABASE_URL,
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "echo": self.DEBUG
        }
    
    @property
    def influxdb_config(self) -> Dict[str, str]:
        """InfluxDB configuration."""
        return {
            "url": self.INFLUXDB_URL,
            "token": self.INFLUXDB_TOKEN,
            "org": self.INFLUXDB_ORG,
            "bucket": self.INFLUXDB_BUCKET
        }
    
    @property
    def redis_config(self) -> Dict[str, Any]:
        """Redis configuration."""
        return {
            "url": self.REDIS_URL,
            "decode_responses": True,
            "max_connections": 10
        }
    
    @property
    def coap_config(self) -> Dict[str, Any]:
        """CoAP device configuration."""
        return {
            "host": self.COAP_DEVICE_HOST,
            "port": self.COAP_DEVICE_PORT,
            "secure_port": self.COAP_DEVICE_SECURE_PORT,
            "enable_dtls": self.ENABLE_DTLS_SERVER_CLIENT,
            "psk_identity": self.COAP_PSK_IDENTITY,
            "psk_key": self.COAP_PSK_KEY
        }
    
    @property
    def email_config(self) -> Dict[str, Any]:
        """Email notification configuration."""
        return {
            "smtp_server": self.SMTP_SERVER,
            "smtp_port": self.SMTP_PORT,
            "username": self.EMAIL_USERNAME,
            "password": self.EMAIL_PASSWORD,
            "from_email": self.FROM_EMAIL,
            "alert_email": self.ALERT_EMAIL
        }
    
    @property
    def fcm_config(self) -> Dict[str, Any]:
        """FCM configuration."""
        return {
            "project_id": self.FCM_PROJECT_ID,
            "private_key_id": self.FCM_PRIVATE_KEY_ID,
            "private_key": self.FCM_PRIVATE_KEY,
            "client_email": self.FCM_CLIENT_EMAIL,
            "client_id": self.FCM_CLIENT_ID,
            "service_account_path": self.FCM_SERVICE_ACCOUNT_PATH,
            "server_port": self.FCM_SERVER_PORT
        }
    
    @property
    def is_email_configured(self) -> bool:
        """Check if email notifications are properly configured."""
        return all([
            self.EMAIL_USERNAME,
            self.EMAIL_PASSWORD,
            self.FROM_EMAIL
        ])
    
    @property
    def is_fcm_configured(self) -> bool:
        """Check if FCM is properly configured."""
        return bool(self.FCM_SERVICE_ACCOUNT_PATH) or all([
            self.FCM_PROJECT_ID,
            self.FCM_PRIVATE_KEY,
            self.FCM_CLIENT_EMAIL
        ])
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Global settings instance
settings = get_settings()

# Backward compatibility - create ServerConfig alias for existing code
class ServerConfig(Settings):
    """Backward compatibility alias for existing code."""
    pass

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Global settings instance
settings = get_settings()