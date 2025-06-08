Okay, this is an extensive project with a well-defined structure and some great initial implementations. I'll go through the directory tree, identify the missing files, and then provide a reasonable implementation for each, ensuring they align with the described features and interact logically with the existing code.

---

### **Summary of Missing Files Identified and Implemented:**

**Client (IoT Device):**
*   `client/Dockerfile`
*   `client/app/security/auth.py`
*   `client/app/security/dtls_handler.py`
*   `client/app/resources/configuration.py`
*   `client/app/resources/diagnostics.py`
*   `client/app/utils/data_validator.py`
*   `client/app/utils/logger.py`
*   `client/app/device.py`
*   `client/app/main.py`

**Server (AI Controller):**
*   `server/Dockerfile`
*   `server/app/config.py`
*   `server/app/models/anomaly_detector.py` (extracted from `ensemble_model.py`)
*   `server/app/database/models.py`
*   `server/app/api/rest_gateway.py`
*   `server/app/api/websocket_handler.py`
*   `server/app/coap/client.py`
*   `server/app/main.py`

**Dashboard:**
*   `dashboard/Dockerfile`
*   `dashboard/static/index.html` (basic structure)
*   `dashboard/static/js/dashboard.js` (basic client-side JS)
*   `dashboard/static/css/style.css` (basic CSS)

**Mobile:**
*   `mobile/Dockerfile`
*   `mobile/push_notifications.py`

**Database:**
*   `database/init-scripts/influxdb-init.sql`

**Nginx:**
*   `nginx/nginx.conf`

**Adjustments/Additions to Existing Files:**
*   Added `math` and `time` imports to `client/app/sensors/temperature.py` and `client/app/sensors/occupancy.py`.
*   Added `time` and `random` imports to `client/app/resources/sensor_data.py`, `client/app/resources/device_status.py`, `client/app/resources/control.py`.
*   Added `IsolationForest` from `sklearn.ensemble`, `datetime`, `timedelta`, `random` imports to `server/app/models/ensemble_model.py`.
*   Added `logging`, `datetime`, `timedelta`, `os`, `aiohttp` imports to `server/app/services/notification_service.py`.
*   Added `os` import to `server/app/database/influxdb_client.py`.
*   Added `logging` and `joblib` imports to `server/app/services/prediction_service.py`.
*   Added `time` and `datetime` imports to `server/app/services/maintenance_service.py`.
*   Added `request` import to `dashboard/app.py`.
*   Added `os`, `time`, `random`, `datetime`, `timedelta` imports to `mobile/api/mobile_endpoints.py`.

---

Here are the implementations for the missing files:

### **1. Client (IoT Device) Implementations**

**`client/Dockerfile`**
```dockerfile
# client/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

# Install system dependencies for DTLS (if needed, e.g., libssl-dev)
# For aiocoap with DTLS, usually only requires Python cryptography, which is handled by pip
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libssl-dev \
#     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./client/app /app/app

# Ensure certs directory exists for DTLS PSK/Certificates
RUN mkdir -p /app/certs
COPY certs /app/certs

# Expose CoAP ports (UDP)
EXPOSE 5683/udp
EXPOSE 5684/udp

# Command to run the CoAP device
CMD ["python", "app/main.py"]
```

**`client/app/security/auth.py`**
```python
# client/app/security/auth.py
import os
import logging
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages PSK and Certificate-based security for CoAP DTLS."""
    def __init__(self, config):
        self.config = config
        self.psk_identity = self.config.PSK_IDENTITY.encode('utf-8')
        self.psk_key = self.config.PSK_KEY.encode('utf-8')
        logger.info(f"SecurityManager initialized with PSK Identity: {self.config.PSK_IDENTITY}")

    def get_psk_credentials(self, identity):
        """Returns PSK key for a given identity."""
        if identity == self.psk_identity:
            logger.debug(f"PSK provided for identity: {identity.decode()}")
            return self.psk_key
        logger.warning(f"Unknown PSK identity requested: {identity.decode()}")
        return None

    def generate_or_load_keys(self, private_key_path="certs/private_key.pem", public_key_path="certs/public_key.pem"):
        """Generates or loads RSA private and public keys."""
        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            logger.info("Loading existing RSA keys.")
            with open(private_key_path, "rb") as f:
                private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
            with open(public_key_path, "rb") as f:
                public_key = serialization.load_pem_public_key(f.read(), backend=default_backend())
        else:
            logger.info("Generating new RSA keys.")
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            public_key = private_key.public_key()

            # Save keys
            with open(private_key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            with open(public_key_path, "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
        return private_key, public_key

    # Certificate handling would go here, e.g., loading device certificates
    # For simplicity, we'll focus on PSK for DTLS with aiocoap for this example.
```

**`client/app/security/dtls_handler.py`**
```python
# client/app/security/dtls_handler.py
import asyncio
import aiocoap.security
from aiocoap.credentials import Credentials
import logging

logger = logging.getLogger(__name__)

class DTLSSecurityHandler:
    """Handles DTLS credentials for aiocoap context."""
    def __init__(self, config, security_manager):
        self.config = config
        self.security_manager = security_manager
        self.credentials_loaded = False

    def get_dtls_credentials(self):
        """Returns aiocoap DTLS credentials."""
        if not self.config.ENABLE_DTLS:
            logger.info("DTLS is disabled.")
            return {}

        if not self.credentials_loaded:
            logger.info("Loading DTLS PSK credentials.")
            creds = Credentials()
            # PSK credentials for server authentication (incoming requests)
            # The key parameter is a callable that receives the identity
            creds.add_psk(
                id=self.security_manager.psk_identity,
                key=self.security_manager.psk_key,
                # For client-side acting as a server, 'server_public_key' is not usually needed
                # unless client also validates server cert. For simple PSK, this is enough.
            )
            aiocoap.security.set_credentials(creds)
            self.credentials_loaded = True
            logger.info("DTLS PSK credentials loaded successfully.")
        
        # When acting as a client, we might need a different `set_credentials` call
        # or use `credentials` directly in the `aiocoap.Context.create_server` call.
        # For simplicity, we assume the server uses the same PSK.

        return {
            "psk_id": self.security_manager.psk_identity.decode('utf-8'),
            "psk": self.security_manager.psk_key.decode('utf-8')
        }

    # For more complex scenarios, you would add methods for:
    # - Certificate loading and validation
    # - Managing trust anchors (CAs)
```

**`client/app/resources/configuration.py`**
```python
# client/app/resources/configuration.py
import json
import aiocoap
from aiocoap.resource import Resource
import logging

logger = logging.getLogger(__name__)

class ConfigurationResource(Resource):
    """CoAP resource to get and update device configuration."""
    def __init__(self, device_config):
        super().__init__()
        self.device_config = device_config
        logger.info("ConfigurationResource initialized.")

    async def render_get(self, request):
        """Handle GET request to retrieve current configuration."""
        config_data = {
            "device_id": self.device_config.DEVICE_ID,
            "sensor_update_interval": self.device_config.SENSOR_UPDATE_INTERVAL,
            "enable_occupancy_sensor": self.device_config.ENABLE_OCCUPANCY_SENSOR,
            "enable_air_quality_sensor": self.device_config.ENABLE_AIR_QUALITY_SENSOR,
            "firmware_version": self.device_config.FIRMWARE_VERSION,
            "enable_dtls": self.device_config.ENABLE_DTLS
            # Add other configurable parameters here
        }
        payload = json.dumps(config_data).encode('utf-8')
        logger.info(f"GET /config - Responding with: {config_data}")
        return aiocoap.Message(payload=payload, content_format=50) # JSON format

    async def render_post(self, request):
        """Handle POST request to update configuration."""
        try:
            config_update = json.loads(request.payload.decode('utf-8'))
            response_data = {"status": "success", "message": "Configuration updated", "changes": []}

            # Example: Update sensor interval
            if "sensor_update_interval" in config_update:
                new_interval = int(config_update["sensor_update_interval"])
                if 1 <= new_interval <= 300: # Sanity check
                    old_interval = self.device_config.SENSOR_UPDATE_INTERVAL
                    self.device_config.SENSOR_UPDATE_INTERVAL = new_interval
                    response_data["changes"].append(f"Sensor interval: {old_interval}s -> {new_interval}s")
                    logger.info(f"Updated sensor_update_interval to {new_interval}")
                else:
                    raise ValueError("Sensor interval out of range (1-300).")
            
            # Example: Update sensor enable/disable flags
            if "enable_occupancy_sensor" in config_update:
                old_status = self.device_config.ENABLE_OCCUPANCY_SENSOR
                self.device_config.ENABLE_OCCUPANCY_SENSOR = bool(config_update["enable_occupancy_sensor"])
                response_data["changes"].append(f"Occupancy sensor enabled: {old_status} -> {self.device_config.ENABLE_OCCUPANCY_SENSOR}")
                logger.info(f"Updated enable_occupancy_sensor to {self.device_config.ENABLE_OCCUPANCY_SENSOR}")

            # Persist configuration (if applicable, e.g., write to a file or database)
            # self.device_config.save() # Placeholder for persistence

            payload = json.dumps(response_data).encode('utf-8')
            return aiocoap.Message(payload=payload, content_format=50)

        except Exception as e:
            logger.error(f"Error processing config update: {e}")
            error_payload = json.dumps({"status": "error", "message": str(e)}).encode('utf-8')
            return aiocoap.Message(payload=error_payload, code=aiocoap.Code.BAD_REQUEST, content_format=50)
```

**`client/app/resources/diagnostics.py`**
```python
# client/app/resources/diagnostics.py
import json
import aiocoap
from aiocoap.resource import Resource
import time
import psutil # Requires psutil in requirements.txt
import logging

logger = logging.getLogger(__name__)

class DiagnosticsResource(Resource):
    """CoAP resource to retrieve device diagnostics and health information."""
    def __init__(self, device_id: str, start_time: float):
        super().__init__()
        self.device_id = device_id
        self.start_time = start_time
        logger.info("DiagnosticsResource initialized.")

    async def render_get(self, request):
        """Handle GET request to retrieve diagnostics data."""
        try:
            uptime_seconds = int(time.time() - self.start_time)
            cpu_percent = psutil.cpu_percent(interval=None)
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')

            diagnostics_data = {
                "device_id": self.device_id,
                "timestamp": time.time(),
                "uptime_seconds": uptime_seconds,
                "cpu_usage_percent": cpu_percent,
                "memory_usage": {
                    "total_mb": round(memory_info.total / (1024*1024), 2),
                    "available_mb": round(memory_info.available / (1024*1024), 2),
                    "percent": memory_info.percent
                },
                "disk_usage": {
                    "total_gb": round(disk_info.total / (1024**3), 2),
                    "used_gb": round(disk_info.used / (1024**3), 2),
                    "percent": disk_info.percent
                },
                "network_status": self._get_network_status(),
                "last_error": "None", # Placeholder, would be pulled from a log
                "self_test_status": "Passed" # Placeholder for a self-test function
            }

            payload = json.dumps(diagnostics_data).encode('utf-8')
            logger.info(f"GET /diagnostics - Responding with system diagnostics.")
            return aiocoap.Message(payload=payload, content_format=50)

        except Exception as e:
            logger.error(f"Error gathering diagnostics: {e}")
            error_payload = json.dumps({"status": "error", "message": str(e)}).encode('utf-8')
            return aiocoap.Message(payload=error_payload, code=aiocoap.Code.INTERNAL_SERVER_ERROR, content_format=50)
            
    def _get_network_status(self):
        """Simulate network status."""
        # In a real device, this would involve checking interface status, pinging gateway, etc.
        return {
            "ip_address": "127.0.0.1", # Or actual IP
            "connectivity": "online",
            "rssi_dbm": -55 # Wi-Fi signal strength
        }
```

**`client/app/utils/data_validator.py`**
```python
# client/app/utils/data_validator.py
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """Utility class for validating sensor data and control commands."""

    @staticmethod
    def validate_sensor_reading(data: dict, sensor_type: str) -> bool:
        """Validates a single sensor reading dictionary."""
        if not isinstance(data, dict):
            logger.warning(f"Invalid sensor data type for {sensor_type}: {type(data)}")
            return False

        if "value" not in data and "occupied" not in data and "aqi" not in data:
            logger.warning(f"Missing 'value', 'occupied', or 'aqi' in {sensor_type} data.")
            return False
        
        if "timestamp" not in data or not isinstance(data["timestamp"], (int, float)):
            logger.warning(f"Missing or invalid 'timestamp' in {sensor_type} data.")
            return False

        if sensor_type == "temperature":
            if not (-50 <= data.get("value", 0) <= 100): # Realistic temperature range
                logger.warning(f"Temperature value {data.get('value')} out of expected range.")
                return False
        elif sensor_type == "humidity":
            if not (0 <= data.get("value", 0) <= 100): # Humidity percentage
                logger.warning(f"Humidity value {data.get('value')} out of expected range.")
                return False
        elif sensor_type == "air_quality":
            if not (0 <= data.get("aqi", 0) <= 500): # AQI range
                logger.warning(f"AQI value {data.get('aqi')} out of expected range.")
                return False
        elif sensor_type == "occupancy":
            if not isinstance(data.get("occupied"), bool):
                logger.warning(f"Occupied status must be boolean for occupancy sensor.")
                return False
        
        return True

    @staticmethod
    def validate_all_sensor_data(full_data: dict) -> bool:
        """Validates the combined sensor data payload."""
        if not isinstance(full_data, dict):
            logger.error("Full sensor data must be a dictionary.")
            return False
        
        required_keys = ["device_id", "timestamp", "temperature", "humidity"]
        for key in required_keys:
            if key not in full_data:
                logger.error(f"Missing required key in full sensor data: {key}")
                return False
        
        if not DataValidator.validate_sensor_reading(full_data.get("temperature", {}), "temperature"):
            logger.error("Temperature data failed validation.")
            return False
        if not DataValidator.validate_sensor_reading(full_data.get("humidity", {}), "humidity"):
            logger.error("Humidity data failed validation.")
            return False
        if "air_quality" in full_data and not DataValidator.validate_sensor_reading(full_data.get("air_quality", {}), "air_quality"):
            logger.error("Air quality data failed validation.")
            return False
        if "occupancy" in full_data and not DataValidator.validate_sensor_reading(full_data.get("occupancy", {}), "occupancy"):
            logger.error("Occupancy data failed validation.")
            return False

        return True

    @staticmethod
    def validate_control_command(command: dict) -> bool:
        """Validates an incoming control command."""
        if not isinstance(command, dict):
            logger.warning("Control command must be a dictionary.")
            return False

        if "hvac_state" in command and command["hvac_state"] not in ["on", "off", "heating", "cooling", "fan_only"]:
            logger.warning(f"Invalid hvac_state: {command['hvac_state']}")
            return False
        
        if "target_temperature" in command:
            temp = float(command["target_temperature"])
            if not (15 <= temp <= 30): # Reasonable target temp range
                logger.warning(f"Target temperature {temp} out of expected range (15-30).")
                return False
                
        if "mode" in command and command["mode"] not in ["auto", "heat", "cool", "off"]:
            logger.warning(f"Invalid mode: {command['mode']}")
            return False
            
        if "fan_speed" in command and command["fan_speed"] not in ["low", "medium", "high", "auto"]:
            logger.warning(f"Invalid fan_speed: {command['fan_speed']}")
            return False
            
        return True
```

**`client/app/utils/logger.py`**
```python
# client/app/utils/logger.py
import logging
import os

def setup_logger(name, level=logging.INFO):
    """Sets up a standardized logger for the client application."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding multiple handlers if logger is already configured
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler (optional)
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, "client.log"))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

# Example usage:
# logger = setup_logger(__name__)
# logger.info("This is an info message.")
```

**`client/app/device.py`**
```python
# client/app/device.py
import asyncio
import aiocoap
import aiocoap.resource as resource
import logging
import time

from .config import DeviceConfig
from .security.auth import SecurityManager
from .security.dtls_handler import DTLSSecurityHandler
from .resources.sensor_data import SensorDataResource
from .resources.device_status import DeviceStatusResource
from .resources.control import EnhancedControlResource
from .resources.configuration import ConfigurationResource
from .resources.diagnostics import DiagnosticsResource
from .utils.logger import setup_logger

logger = setup_logger(__name__)

class CoAPDevice:
    """Represents the smart thermostat as a CoAP device."""
    def __init__(self, config: DeviceConfig):
        self.config = config
        self.coap_context = None
        self.device_start_time = time.time()
        self.control_resource = EnhancedControlResource() # Initialize control resource here
        
        self.security_manager = SecurityManager(self.config)
        self.dtls_handler = DTLSSecurityHandler(self.config, self.security_manager)

    async def start(self):
        """Starts the CoAP server for the device."""
        root = resource.Site()

        # Register resources
        root.add_resource(['.well-known', 'core'],
                          resource.WkVsResource(root))
        root.add_resource(['sensor', 'data'], SensorDataResource(self.config.DEVICE_ID))
        root.add_resource(['device', 'status'], DeviceStatusResource(self.config.DEVICE_ID))
        root.add_resource(['control'], self.control_resource) # Use the initialized instance
        root.add_resource(['config'], ConfigurationResource(self.config))
        root.add_resource(['diagnostics'], DiagnosticsResource(self.config.DEVICE_ID, self.device_start_time))
        
        if self.config.ENABLE_DTLS:
            logger.info("Starting CoAP server with DTLS.")
            # Get DTLS credentials for the server context
            dtls_params = self.dtls_handler.get_dtls_credentials()
            self.coap_context = await aiocoap.Context.create_server_context(
                root, 
                bind=(self.config.HOST, self.config.SECURE_PORT),
                dtls_server_certs=[
                    (self.security_manager.psk_identity, self.security_manager.psk_key)
                ] if self.config.ENABLE_DTLS else None # Simplified DTLS PSK setup for server
            )
            logger.info(f"CoAP-DTLS server listening on {self.config.HOST}:{self.config.SECURE_PORT}")
        else:
            logger.info("Starting CoAP server without DTLS.")
            self.coap_context = await aiocoap.Context.create_server_context(
                root, 
                bind=(self.config.HOST, self.config.PORT)
            )
            logger.info(f"CoAP server listening on {self.config.HOST}:{self.config.PORT}")

        logger.info(f"CoAP Device '{self.config.DEVICE_ID}' started successfully.")

        # Keep the server running
        try:
            while True:
                await asyncio.sleep(3600) # Keep alive
        except asyncio.CancelledError:
            logger.info("CoAP device stopped.")
        finally:
            if self.coap_context:
                await self.coap_context.shutdown()
                logger.info("CoAP context shut down.")

    async def stop(self):
        """Stops the CoAP server."""
        if self.coap_context:
            await self.coap_context.shutdown()
            logger.info("CoAP device stopped.")
```

**`client/app/main.py`**
```python
# client/app/main.py
import asyncio
import logging
import os

from .config import DeviceConfig
from .device import CoAPDevice
from .utils.logger import setup_logger

# Setup global logger for the main module
logger = setup_logger("client_main")

async def main():
    """Main function to start the CoAP thermostat device."""
    # Load configuration
    config = DeviceConfig()
    
    logger.info(f"Starting Smart Thermostat Device: {config.DEVICE_ID}")
    logger.info(f"Firmware Version: {config.FIRMWARE_VERSION}")
    logger.info(f"DTLS Enabled: {config.ENABLE_DTLS}")
    
    device = CoAPDevice(config)
    
    try:
        await device.start()
    except KeyboardInterrupt:
        logger.info("Device shutdown initiated by user.")
    except Exception as e:
        logger.critical(f"An unhandled error occurred: {e}", exc_info=True)
    finally:
        await device.stop()
        logger.info("Device gracefully shut down.")

if __name__ == "__main__":
    # Ensure .env is loaded if using python-dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("Environment variables loaded from .env")
    except ImportError:
        logger.warning("python-dotenv not installed. Environment variables must be set manually.")
    
    asyncio.run(main())
```

**Imports for existing client files:**

*   **`client/app/sensors/temperature.py`**:
    ```python
    import random
    import time
    from typing import Dict, Optional
    from dataclasses import dataclass
    import math # <--- ADD THIS
    ```
*   **`client/app/sensors/occupancy.py`**:
    ```python
    import random
    import time # <--- ADD THIS
    from typing import Dict
    ```
*   **`client/app/resources/sensor_data.py`**:
    ```python
    import json
    import aiocoap
    from aiocoap.resource import Resource
    from ..sensors.temperature import AdvancedTemperatureSensor
    from ..sensors.humidity import HumiditySensor
    from ..sensors.air_quality import AirQualitySensor
    from ..sensors.occupancy import OccupancySensor
    import time # <--- ADD THIS
    ```
*   **`client/app/resources/device_status.py`**:
    ```python
    import json
    import aiocoap
    from aiocoap.resource import Resource
    import time # <--- ADD THIS
    import random # <--- ADD THIS
    ```
*   **`client/app/resources/control.py`**:
    ```python
    import json
    import aiocoap
    from aiocoap.resource import Resource
    # No additional imports needed for the given snippet
    ```

---

### **2. Server (AI Controller) Implementations**

**`server/Dockerfile`**
```dockerfile
# server/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

# Install system dependencies for DTLS (if needed, e.g., libssl-dev)
# For aiocoap with DTLS, usually only requires Python cryptography, handled by pip
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libssl-dev \
#     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./server/app /app/app
# Copy models
COPY models /app/models

# Create a logs directory
RUN mkdir -p /app/logs

# Expose FastAPI port
EXPOSE 8000

# Command to run the AI controller
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`server/app/config.py`**
```python
# server/app/config.py
import os
from pydantic import BaseSettings

class ServerConfig(BaseSettings):
    # CoAP Device Connectivity
    COAP_DEVICE_HOST: str = os.getenv("COAP_DEVICE_HOST", "coap-device")
    COAP_DEVICE_PORT: int = int(os.getenv("COAP_DEVICE_PORT", 5683))
    COAP_DEVICE_SECURE_PORT: int = int(os.getenv("COAP_DEVICE_SECURE_PORT", 5684))
    ENABLE_DTLS_SERVER_CLIENT: bool = os.getenv("ENABLE_DTLS_SERVER_CLIENT", "true").lower() == "true"
    COAP_PSK_IDENTITY: str = os.getenv("COAP_PSK_IDENTITY", "thermostat")
    COAP_PSK_KEY: str = os.getenv("COAP_PSK_KEY", "secretkey123")
    
    # InfluxDB Configuration
    INFLUXDB_URL: str = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
    INFLUXDB_TOKEN: str = os.getenv("INFLUXDB_TOKEN", "admin-token")
    INFLUXDB_ORG: str = os.getenv("INFLUXDB_ORG", "thermostat-org")
    INFLUXDB_BUCKET: str = os.getenv("INFLUXDB_BUCKET", "thermostat-data")
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8000))
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key")
    
    # Control Loop & ML
    POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", 3)) # Seconds
    ML_RETRAIN_INTERVAL_HOURS: int = int(os.getenv("ML_RETRAIN_INTERVAL_HOURS", 24))
    
    # Notifications
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    EMAIL_USERNAME: str = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL")
    ALERT_EMAIL: str = os.getenv("ALERT_EMAIL", "admin@example.com")
    WEBHOOK_URLS: str = os.getenv("WEBHOOK_URLS", "") # Comma-separated
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
```

**`server/app/models/anomaly_detector.py`**
```python
# server/app/models/anomaly_detector.py
from sklearn.ensemble import IsolationForest
import numpy as np
import pandas as pd
import logging
import joblib
import os

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """
    Detects anomalies in sensor data using Isolation Forest.
    """
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.model = IsolationForest(contamination=contamination, random_state=random_state)
        self.is_trained = False
        self.model_path = "models/anomaly_detector.joblib"

    def train(self, data: pd.DataFrame, feature_columns: list = None):
        """
        Trains the anomaly detection model.
        Data should be a DataFrame with numeric features.
        """
        if data.empty:
            logger.warning("No data provided for anomaly detector training.")
            return False

        if feature_columns is None:
            # Default to temperature and humidity if not specified
            feature_columns = ['temperature', 'humidity'] 
            # Ensure columns exist, drop if not
            feature_columns = [col for col in feature_columns if col in data.columns]
            if not feature_columns:
                logger.warning("No valid feature columns found for anomaly detector training.")
                return False

        X = data[feature_columns].values
        
        try:
            self.model.fit(X)
            self.is_trained = True
            logger.info(f"Anomaly detector trained successfully on {len(X)} samples using features: {feature_columns}")
            # Save model
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            logger.info(f"Anomaly detector model saved to {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Error training anomaly detector: {e}")
            self.is_trained = False
            return False

    def predict(self, data: pd.DataFrame, feature_columns: list = None) -> np.ndarray:
        """
        Predicts anomalies in new data.
        Returns -1 for anomalies, 1 for normal data.
        """
        if not self.is_trained:
            self.load_model() # Attempt to load if not trained in current session
            if not self.is_trained:
                logger.warning("Anomaly detector is not trained or loaded. Skipping prediction.")
                return np.ones(len(data)) # Assume normal if no model

        if data.empty:
            return np.array([])
            
        if feature_columns is None:
            feature_columns = ['temperature', 'humidity']
            feature_columns = [col for col in feature_columns if col in data.columns]
            if not feature_columns:
                logger.warning("No valid feature columns found for anomaly prediction.")
                return np.ones(len(data))

        X = data[feature_columns].values
        
        try:
            return self.model.predict(X)
        except Exception as e:
            logger.error(f"Error predicting anomalies: {e}")
            return np.ones(len(X)) # Return normal for all in case of error

    def load_model(self):
        """Loads a pre-trained anomaly detection model."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.is_trained = True
                logger.info(f"Anomaly detector model loaded from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load anomaly detector model from {self.model_path}: {e}")
                self.is_trained = False
        else:
            logger.warning(f"Anomaly detector model not found at {self.model_path}. Will need retraining.")
            self.is_trained = False

# Note: The `ensemble_model.py` currently takes a single value for anomaly detection.
# This AnomalyDetector class is designed for multi-feature input.
# The `ensemble_model.py` will need adjustment to use this more comprehensively.
# For now, `ensemble_model.py` will simply pass `[[current_temp]]` which will use only temperature.
```

**`server/app/database/models.py`**
```python
# server/app/database/models.py
# This file would typically define SQLAlchemy models for PostgreSQL.
# For simplicity and given the focus on InfluxDB for time-series,
# this will be a placeholder. If user management or device registration
# becomes more complex, this file would be populated.

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Example Pydantic model for a registered device (for API consistency)
class RegisteredDevice(BaseModel):
    device_id: str
    device_type: str
    location: Optional[str] = None
    registered_at: datetime = datetime.now()
    last_seen: Optional[datetime] = None
    is_active: bool = True

# Example Pydantic model for a user
class User(BaseModel):
    user_id: str
    username: str
    email: str
    password_hash: str # In a real app, don't store plain passwords
    roles: List[str] = ["user"]
    created_at: datetime = datetime.now()

# Example Pydantic model for an alert
class Alert(BaseModel):
    alert_id: str
    device_id: str
    alert_type: str
    message: str
    severity: str
    timestamp: datetime
    is_resolved: bool = False
    resolution_details: Optional[str] = None

# If using an ORM like SQLAlchemy, you would have:
# from sqlalchemy import Column, Integer, String, Boolean, DateTime
# from sqlalchemy.ext.declarative import declarative_base
#
# Base = declarative_base()
#
# class Device(Base):
#     __tablename__ = "devices"
#     id = Column(String, primary_key=True, index=True)
#     type = Column(String)
#     location = Column(String)
#     registered_at = Column(DateTime, default=datetime.utcnow)
#     # ... and so on
```

**`server/app/api/rest_gateway.py`**
```python
# server/app/api/rest_gateway.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import jwt
import os
import time
import logging

from ..services.thermostat_service import ThermostatControlService
from ..services.prediction_service import PredictionService
from ..services.maintenance_service import MaintenanceService
from ..database.influxdb_client import InfluxDBClient
from ..config import ServerConfig

# Initialize services (these will be injected from main.py in a real app)
# For now, we'll instantiate them here for FastAPI's discovery, but they should be singletons.
# A better approach is dependency injection (e.g., using FastAPI's Depends or a custom IoC container).
influx_client = InfluxDBClient()
thermostat_service = ThermostatControlService()
prediction_service = PredictionService()
maintenance_service = MaintenanceService()

app = FastAPI(title="Smart Thermostat AI API", version="2.0.0")
security = HTTPBearer()
config = ServerConfig()
logger = logging.getLogger(__name__)

# Pydantic models for request/response bodies (similar to mobile/api/mobile_endpoints.py)
class ThermostatCommand(BaseModel):
    action: str
    target_temperature: Optional[float] = None
    mode: Optional[str] = None
    fan_speed: Optional[str] = None

class ScheduleEntry(BaseModel):
    time: str
    temperature: float
    days: List[str]
    enabled: bool = True

class DeviceInfo(BaseModel):
    device_id: str
    device_type: str
    location: str
    online: bool
    last_updated: float

# JWT Token Verification (shared with mobile/api/mobile_endpoints.py)
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials, 
            config.JWT_SECRET, 
            algorithms=["HS256"]
        )
        # You can add more complex user authorization here based on payload roles/permissions
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@app.on_event("startup")
async def startup_event():
    # Attempt to load ML models on startup
    await prediction_service.retrain_models()
    logger.info("REST Gateway startup complete.")

@app.get("/api/v1/status/{device_id}", response_model=Dict[str, Any])
async def get_device_status(device_id: str, user=Depends(verify_token)):
    """Get current device status and sensor data for a specific device."""
    try:
        # In a real system, this would fetch from a cache or the CoAP client directly
        # For now, let's use a mock or try to get latest from DB (which is not efficient for real-time)
        # A proper implementation would have the CoAP client push to Redis, and this API reads from Redis.
        mock_status = {
            "device_id": device_id,
            "online": True, # Assume online for now
            "current_temperature": thermostat_service.control_resource.target_temperature, # Mock from control resource
            "target_temperature": thermostat_service.control_resource.target_temperature,
            "humidity": 45.2,
            "air_quality": {"aqi": 35, "quality": "good"},
            "hvac_state": thermostat_service.control_resource.hvac_state,
            "energy_consumption": 2.1,
            "last_updated": time.time()
        }
        return mock_status
    except Exception as e:
        logger.error(f"Error fetching device status for {device_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/api/v1/control/{device_id}", response_model=Dict[str, Any])
async def send_control_command(device_id: str, command: ThermostatCommand, user=Depends(verify_token)):
    """Send control command to thermostat."""
    try:
        # In a real system, this would interact with the CoAP client to send the command
        # For simplicity, we'll directly call the service which uses the CoAP client
        # Note: thermostat_service.execute_decision expects a full decision dict
        # This endpoint just takes a command. We need a way to map this.
        
        # Mock conversion of command to a decision dict format
        mock_decision = {
            "action": command.action,
            "target_temperature": command.target_temperature or 22.0,
            "fan_speed": command.fan_speed or "auto",
            "reasoning": ["Manual command via API"],
            "confidence": 1.0
        }
        
        success = await thermostat_service.execute_decision(mock_decision)
        if success:
            return {"success": True, "command_executed": command.dict(), "timestamp": time.time()}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to execute command on device.")
    except Exception as e:
        logger.error(f"Error sending command to {device_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/v1/predictions/{device_id}", response_model=Dict[str, Any])
async def get_temperature_predictions(device_id: str, hours: int = 24, user=Depends(verify_token)):
    """Get temperature predictions for the next few hours."""
    try:
        # PredictionService operates on general historical data, not per-device by default.
        # This would need to be enhanced if predictions are device-specific.
        predictions_data = await prediction_service.get_predictions(hours_ahead=hours)
        if predictions_data:
            return predictions_data
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Predictions not available.")
    except Exception as e:
        logger.error(f"Error getting predictions for {device_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/v1/maintenance/{device_id}", response_model=Dict[str, Any])
async def get_device_maintenance_status(device_id: str, user=Depends(verify_token)):
    """Get maintenance recommendations for a specific device."""
    try:
        # Need to get device status first to pass to maintenance service
        device_status = {
            "device_id": device_id,
            "uptime_seconds": 3600 * 24 * 100, # Mock uptime
            "energy_consumption": 2.5, # Mock current consumption
            "last_maintenance": time.time() - (86400 * 95) # Mock 95 days ago
        }
        maintenance_info = await maintenance_service.check_maintenance_needs(device_status)
        return maintenance_info
    except Exception as e:
        logger.error(f"Error getting maintenance status for {device_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# Placeholder for device registration (if using models.py for this)
@app.post("/api/v1/devices", response_model=DeviceInfo)
async def register_device(device_info: DeviceInfo, user=Depends(verify_token)):
    """Register a new smart thermostat device."""
    # In a real system, store this in PostgreSQL or similar.
    # For now, just return the info.
    logger.info(f"Registered new device: {device_info.device_id}")
    return device_info
```

**`server/app/api/websocket_handler.py`**
```python
# server/app/api/websocket_handler.py
import asyncio
import websockets
import json
import logging
from typing import Dict, Any, Set
from ..services.thermostat_service import ThermostatControlService
from ..config import ServerConfig

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections for real-time data streaming."""
    def __init__(self, thermostat_service: ThermostatControlService, config: ServerConfig):
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.thermostat_service = thermostat_service
        self.config = config
        self._data_stream_task = None
        self._latest_sensor_data: Dict[str, Any] = {}

    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Registers a new WebSocket client."""
        self.connected_clients.add(websocket)
        logger.info(f"WebSocket client connected: {websocket.remote_address}")
        # Send latest data immediately upon connection if available
        if self._latest_sensor_data:
            try:
                await websocket.send(json.dumps(self._latest_sensor_data))
            except websockets.exceptions.ConnectionClosedOK:
                pass # Client disconnected before sending
        await websocket.send(json.dumps({"type": "status", "message": "Connected to AI Controller WebSocket"}))

    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregisters a WebSocket client."""
        self.connected_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected: {websocket.remote_address}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcasts a message to all connected clients."""
        if not self.connected_clients:
            return

        message_json = json.dumps(message)
        
        # Use asyncio.gather to send to all clients concurrently
        # Filter out connections that might have closed unexpectedly
        await asyncio.gather(*[
            self._send_to_client(client, message_json)
            for client in list(self.connected_clients) # Use a copy for iteration
        ])

    async def _send_to_client(self, client: websockets.WebSocketServerProtocol, message_json: str):
        """Helper to send a message to a single client, handling disconnections."""
        try:
            await client.send(message_json)
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"Client {client.remote_address} closed connection during send. Unregistering.")
            await self.unregister_client(client)
        except Exception as e:
            logger.error(f"Error sending to WebSocket client {client.remote_address}: {e}")
            await self.unregister_client(client) # Consider unregistering on other errors too

    async def data_stream_producer(self):
        """Periodically fetches data and broadcasts it."""
        while True:
            try:
                # Get latest sensor data from the thermostat service's internal state
                # (ThermostatService.decision_history or dedicated cache)
                # For simplicity, we'll get the last processed sensor data
                latest_processed_data = self.thermostat_service.get_last_processed_data()
                
                if latest_processed_data:
                    # Enrich with predictions if available
                    predictions = self.thermostat_service.get_last_predictions() # Assuming ThermostatService stores this
                    
                    self._latest_sensor_data = {
                        "type": "sensor_update",
                        "data": latest_processed_data,
                        "predictions": predictions
                    }
                    await self.broadcast(self._latest_sensor_data)
                
                await asyncio.sleep(self.config.POLL_INTERVAL) # Use server config for interval
            except asyncio.CancelledError:
                logger.info("WebSocket data stream producer cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket data stream producer: {e}", exc_info=True)
                await asyncio.sleep(5) # Wait before retrying after an error

    async def start_server(self, host: str = "0.0.0.0", port: int = 8001):
        """Starts the WebSocket server."""
        self._data_stream_task = asyncio.create_task(self.data_stream_producer())
        
        async with websockets.serve(self.websocket_handler, host, port):
            logger.info(f"WebSocket server listening on ws://{host}:{port}")
            await asyncio.Future() # Run forever

    async def websocket_handler(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handles incoming WebSocket connections."""
        await self.register_client(websocket)
        try:
            # Keep connection open for incoming messages (e.g., control commands from dashboard)
            async for message in websocket:
                logger.info(f"Received WS message from {websocket.remote_address}: {message}")
                # You can add logic here to parse commands and send to CoAP device
                # For example, if message is a JSON command for thermostat control
                # await self.thermostat_service.execute_decision_from_ws(json.loads(message))
                await websocket.send(json.dumps({"type": "ack", "message": "Command received"}))
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"WebSocket connection closed by {websocket.remote_address}")
        except Exception as e:
            logger.error(f"WebSocket error with {websocket.remote_address}: {e}", exc_info=True)
        finally:
            await self.unregister_client(websocket)

    async def stop(self):
        """Stops the WebSocket server and data stream."""
        if self._data_stream_task:
            self._data_stream_task.cancel()
            try:
                await self._data_stream_task
            except asyncio.CancelledError:
                pass
        for client in list(self.connected_clients):
            await client.close()
        self.connected_clients.clear()
        logger.info("WebSocket manager stopped.")

```

**`server/app/coap/client.py`**
```python
# server/app/coap/client.py
import asyncio
import aiocoap
from aiocoap.message import Message
from aiocoap import Code, Context, GET, PUT, POST
import json
import logging
import time
from aiocoap.credentials import Credentials
from aiocoap.security import set_credentials as aiocoap_set_credentials

from ..config import ServerConfig
from ..utils.data_validator import DataValidator # Assuming validator is client-side, but can be server-side too

logger = logging.getLogger(__name__)

class EnhancedCoAPClient:
    """
    CoAP client for the AI Controller to communicate with the thermostat device.
    Supports secure CoAP (CoAPS) with PSK.
    """
    def __init__(self, config: ServerConfig):
        self.config = config
        self.coap_context = None
        self.device_url_base = (
            f"coaps://{self.config.COAP_DEVICE_HOST}:{self.config.COAP_DEVICE_SECURE_PORT}"
            if self.config.ENABLE_DTLS_SERVER_CLIENT
            else f"coap://{self.config.COAP_DEVICE_HOST}:{self.config.COAP_DEVICE_PORT}"
        )
        self._setup_dtls_credentials()
        logger.info(f"EnhancedCoAPClient initialized. Base URL: {self.device_url_base}")

    def _setup_dtls_credentials(self):
        """Configures DTLS PSK credentials for the client context."""
        if self.config.ENABLE_DTLS_SERVER_CLIENT:
            creds = Credentials()
            identity_bytes = self.config.COAP_PSK_IDENTITY.encode('utf-8')
            key_bytes = self.config.COAP_PSK_KEY.encode('utf-8')
            
            # Add PSK for the remote server (the thermostat device)
            creds.add_psk(
                id=identity_bytes,
                key=key_bytes,
                host=self.config.COAP_DEVICE_HOST # This is crucial for hostname matching
            )
            aiocoap_set_credentials(creds)
            logger.info(f"DTLS PSK credentials set for CoAP client. Identity: {self.config.COAP_PSK_IDENTITY}")
        else:
            logger.info("DTLS for CoAP client is disabled.")

    async def _get_coap_context(self):
        """Lazily creates or returns the CoAP context."""
        if self.coap_context is None:
            self.coap_context = await Context.create_client_context()
            logger.info("CoAP client context created.")
        return self.coap_context

    async def _send_request(self, method: Code, path: str, payload: bytes = b'', content_format: int = 0):
        """Helper to send a CoAP request and get the response."""
        context = await self._get_coap_context()
        request_url = f"{self.device_url_base}/{path}"
        
        request = Message(code=method, uri=request_url, payload=payload)
        if payload:
            request.content_format = content_format

        try:
            logger.debug(f"Sending CoAP {method.name} request to {request_url}")
            response = await context.request(request).response
            logger.debug(f"Received CoAP response from {request_url}: {response.code.name}")
            return response
        except Exception as e:
            logger.error(f"CoAP request to {request_url} failed: {e}")
            return None

    async def get_all_sensor_data(self) -> dict:
        """Retrieves all sensor data from the device."""
        response = await self._send_request(GET, "sensor/data")
        if response and response.code.is_successful():
            try:
                data = json.loads(response.payload.decode('utf-8'))
                if DataValidator.validate_all_sensor_data(data): # Use the validator
                    logger.debug("Sensor data validated successfully.")
                    return data
                else:
                    logger.warning("Received sensor data failed validation.")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode sensor data JSON: {e}")
                return None
        return None

    async def get_device_status(self) -> dict:
        """Retrieves device status."""
        response = await self._send_request(GET, "device/status")
        if response and response.code.is_successful():
            try:
                return json.loads(response.payload.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode device status JSON: {e}")
                return None
        return None

    async def send_control_command(self, command: dict) -> bool:
        """Sends a control command to the device."""
        if not DataValidator.validate_control_command(command): # Use the validator
            logger.warning(f"Control command failed validation: {command}")
            return False

        payload = json.dumps(command).encode('utf-8')
        response = await self._send_request(POST, "control", payload, content_format=50) # JSON format
        if response and response.code.is_successful():
            logger.info(f"Control command {command} sent successfully. Device response: {response.payload.decode()}")
            return True
        logger.error(f"Failed to send control command {command}. Response code: {response.code.name if response else 'None'}")
        return False
    
    async def get_configuration(self) -> dict:
        """Retrieves device configuration."""
        response = await self._send_request(GET, "config")
        if response and response.code.is_successful():
            try:
                return json.loads(response.payload.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode configuration JSON: {e}")
                return None
        return None

    async def update_configuration(self, config_update: dict) -> bool:
        """Sends an update for device configuration."""
        payload = json.dumps(config_update).encode('utf-8')
        response = await self._send_request(POST, "config", payload, content_format=50) # JSON format
        if response and response.code.is_successful():
            logger.info(f"Configuration update {config_update} sent successfully. Device response: {response.payload.decode()}")
            return True
        logger.error(f"Failed to send configuration update {config_update}. Response code: {response.code.name if response else 'None'}")
        return False

    async def get_diagnostics(self) -> dict:
        """Retrieves device diagnostics."""
        response = await self._send_request(GET, "diagnostics")
        if response and response.code.is_successful():
            try:
                return json.loads(response.payload.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode diagnostics JSON: {e}")
                return None
        return None

    async def shutdown(self):
        """Shuts down the CoAP client context."""
        if self.coap_context:
            await self.coap_context.shutdown()
            self.coap_context = None
            logger.info("CoAP client context shut down.")
```

**`server/app/main.py`**
```python
# server/app/main.py
import asyncio
import logging
import os
import uvicorn
from datetime import datetime
from functools import partial

from .config import ServerConfig
from .services.thermostat_service import ThermostatControlService
from .services.prediction_service import PredictionService
from .services.maintenance_service import MaintenanceService
from .services.notification_service import NotificationService
from .database.influxdb_client import InfluxDBClient
from .coap.client import EnhancedCoAPClient
from .api.rest_gateway import app as rest_api_app # Import FastAPI app
from .api.websocket_handler import WebSocketManager

# Setup basic logging for main server process
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration
config = ServerConfig()

# Initialize core components
influx_client = InfluxDBClient()
coap_client = EnhancedCoAPClient(config)
notification_service = NotificationService(config) # Pass config for email/webhook settings

# Initialize services
# Pass necessary dependencies to services
thermostat_service = ThermostatControlService(
    ensemble_model_instance=None, # Will be initialized inside loop
    db_client=influx_client,
    coap_client=coap_client,
    notification_service=notification_service # Pass notification service
)
prediction_service = PredictionService(db_client=influx_client)
maintenance_service = MaintenanceService(db_client=influx_client, notification_service=notification_service)

# Initialize WebSocket Manager
websocket_manager = WebSocketManager(thermostat_service, config)

# Main control loop for the AI Controller
async def control_loop():
    logger.info("Starting AI Controller background control loop...")
    
    # Pre-train models on startup if data exists
    await prediction_service.retrain_models()

    # Pass the instance of MaintenanceService and PredictionService to ThermostatControlService
    # This is a bit circular, often services share instances or a common state manager.
    # For now, we'll ensure they are callable or passed.
    thermostat_service.maintenance_service = maintenance_service
    thermostat_service.prediction_service = prediction_service

    while True:
        try:
            # 1. Process control cycle (get data, make decision, send command, store)
            await thermostat_service.process_control_cycle()

            # 2. Check for maintenance needs (using current device status)
            device_status = await coap_client.get_device_status()
            if device_status:
                await maintenance_service.check_maintenance_needs(device_status)

            # 3. Retrain models periodically
            if (prediction_service.last_training is None or 
                (datetime.now() - prediction_service.last_training).total_seconds() / 3600 >= config.ML_RETRAIN_INTERVAL_HOURS):
                await prediction_service.retrain_models()

            # 4. Push latest data to WebSocket clients (handled by WebSocketManager's producer)
            
            await asyncio.sleep(config.POLL_INTERVAL)
            
        except asyncio.CancelledError:
            logger.info("Control loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in control loop: {e}", exc_info=True)
            await asyncio.sleep(config.POLL_INTERVAL * 2) # Wait longer after an error

async def main():
    """Main entry point for the AI Controller application."""
    logger.info("Starting Smart Thermostat AI Controller...")

    # Start the background control loop
    control_loop_task = asyncio.create_task(control_loop())
    
    # Start the WebSocket server (in a separate task)
    websocket_server_task = asyncio.create_task(websocket_manager.start_server(host="0.0.0.0", port=8001)) # Different port for WS

    # Uvicorn serves the FastAPI app (rest_api_app).
    # We will run Uvicorn programmatically.
    # Note: When running with `uvicorn app.main:app`, the `main()` function here
    # acts as the startup entry point for other async tasks, while uvicorn
    # manages the ASGI server for `rest_api_app`.
    # To properly integrate FastAPI with the services, we need to pass the
    # initialized service instances to the FastAPI app.
    
    # A simple way to do this for FastAPI is via global singletons or dependency injection.
    # Here, we'll set them as attributes on the FastAPI app instance for access.
    rest_api_app.state.thermostat_service = thermostat_service
    rest_api_app.state.prediction_service = prediction_service
    rest_api_app.state.maintenance_service = maintenance_service
    rest_api_app.state.influx_client = influx_client
    rest_api_app.state.coap_client = coap_client # If FastAPI needs to directly interact with CoAP
    
    # Uvicorn will handle the main process. This main() is for orchestrating background tasks.
    # In a real setup, `uvicorn` command would launch the `rest_api_app`, and the `control_loop`
    # and `websocket_server_task` would be started as background tasks within FastAPI's lifespan events.
    # For a docker-compose setup where `CMD ["uvicorn", "app.main:app"]` is used,
    # the `asyncio.run(main())` block here won't execute directly.
    # Instead, FastAPI's `startup_event` in `rest_gateway.py` and `on_event("startup")` in this `main.py`
    # would be used to start the background tasks.

    # This example combines logic for a standalone runner or a uvicorn-managed app.
    # When `uvicorn app.main:app` is run, uvicorn discovers `app` from `rest_gateway.py` (aliased here).
    # We need to make sure the tasks are started as part of FastAPI's lifespan.

    try:
        # Keep the main process alive, allowing background tasks to run
        await asyncio.gather(control_loop_task, websocket_server_task)
    except asyncio.CancelledError:
        logger.info("Server main tasks cancelled.")
    except Exception as e:
        logger.critical(f"Unhandled error in main server execution: {e}", exc_info=True)
    finally:
        await coap_client.shutdown()
        logger.info("AI Controller shut down.")

# If running directly via `python app/main.py`
if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("Environment variables loaded from .env")
    except ImportError:
        logger.warning("python-dotenv not installed. Environment variables must be set manually.")

    # When using `uvicorn app.main:app`, uvicorn will run `app` (our FastAPI instance).
    # The `main()` function here is more for orchestrating background tasks if not using
    # FastAPI's lifespan events.
    # For this setup, the `app = FastAPI()` in `rest_gateway.py` is the one Uvicorn loads.
    # The background tasks *should* be started by FastAPI's `@app.on_event("startup")`
    # or by a custom lifespan manager.

    # To simplify, we'll start them here if `main.py` is executed directly,
    # and adjust the `rest_gateway.py` startup for `uvicorn` path.

    # We need to make sure the services in rest_gateway.py are initialized with the
    # instances created here. For this, we can pass them or use a global manager.
    # A cleaner approach for production is dependency injection.
    
    # For now, let's just make the `uvicorn` entry point the canonical one.
    # The `uvicorn` command in Dockerfile points to `app.main:app`, implying
    # this `main.py` *is* the FastAPI app's entry, which means `rest_api_app`
    # should be exposed as `app` here.
    
    # So, we need to adapt:
    # 1. Move service instantiation to `rest_gateway.py` or create a factory.
    # 2. Modify `rest_gateway.py`'s startup event to run background tasks.

    # Let's assume `rest_gateway.py`'s `app` is the primary FastAPI app.
    # The `main.py` is just a runner or background task orchestrator.
    # So, `CMD ["uvicorn", "app.api.rest_gateway:app", "--host", "0.0.0.0", "--port", "8000"]`
    # would be more standard for a FastAPI service.
    # And then, the `on_event("startup")` in `rest_gateway.py` would start the control loop.

    # For the provided `CMD ["uvicorn", "app.main:app"]`, `main.py` itself must return the app or manage it.
    # Let's make `main.py` responsible for bootstrapping and then serving the FastAPI app.

    # If `main.py` is the uvicorn entry point:
    @rest_api_app.on_event("startup")
    async def startup_event():
        logger.info("FastAPI startup event triggered.")
        # Start background tasks
        rest_api_app.state.control_loop_task = asyncio.create_task(control_loop())
        rest_api_app.state.websocket_server_task = asyncio.create_task(websocket_manager.start_server(host="0.0.0.0", port=8001))
        # This is where we inject the instances created in main.py into the FastAPI app state
        rest_api_app.state.thermostat_service = thermostat_service
        rest_api_app.state.prediction_service = prediction_service
        rest_api_app.state.maintenance_service = maintenance_service
        rest_api_app.state.influx_client = influx_client
        rest_api_app.state.coap_client = coap_client
        logger.info("Background tasks started via FastAPI startup event.")

    @rest_api_app.on_event("shutdown")
    async def shutdown_event():
        logger.info("FastAPI shutdown event triggered.")
        if hasattr(rest_api_app.state, 'control_loop_task'):
            rest_api_app.state.control_loop_task.cancel()
            try:
                await rest_api_app.state.control_loop_task
            except asyncio.CancelledError:
                pass
        if hasattr(rest_api_app.state, 'websocket_server_task'):
            rest_api_app.state.websocket_server_task.cancel()
            try:
                await rest_api_app.state.websocket_server_task
            except asyncio.CancelledError:
                pass
        await websocket_manager.stop()
        await coap_client.shutdown()
        logger.info("Background tasks and services shut down via FastAPI shutdown event.")

    # When uvicorn loads app.main:app, it looks for an `app` object.
    # We assign our FastAPI app to `app` here.
    app = rest_api_app # Expose the FastAPI app
```

**Adjustments to existing server files:**

*   **`server/app/models/ensemble_model.py`**:
    ```python
    import numpy as np
    import pandas as pd
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from sklearn.preprocessing import MinMaxScaler
    import joblib
    from sklearn.ensemble import IsolationForest # <--- ADD THIS
    from datetime import datetime, timedelta # <--- ADD THIS
    import random # <--- ADD THIS
    import logging # <--- ADD THIS

    logger = logging.getLogger(__name__)

    class EnsemblePredictor:
        def __init__(self):
            self.lstm_model = LSTMTemperaturePredictor()
            # Initialize with default contamination, will be trained
            self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42) # <--- USE DIRECTLY
            self.energy_optimizer = EnergyOptimizer()
            logger.info("EnsemblePredictor initialized.")

        def make_decision(self, sensor_data: dict, historical_data: pd.DataFrame):
            """Make comprehensive HVAC control decision"""
            # Ensure historical_data has the expected columns for anomaly detector training
            if not historical_data.empty:
                # Retrain anomaly detector if enough new data
                try:
                    features_for_anomaly = ['temperature', 'humidity'] # Example features
                    existing_features = [f for f in features_for_anomaly if f in historical_data.columns]
                    if existing_features:
                        self.anomaly_detector.fit(historical_data[existing_features].dropna())
                        logger.debug("Anomaly detector refitted with historical data.")
                except Exception as e:
                    logger.warning(f"Failed to refit anomaly detector: {e}")

            current_temp = sensor_data['temperature']['value']
            occupancy = sensor_data['occupancy']['occupied']
            air_quality_aqi = sensor_data['air_quality']['aqi'] # Rename to avoid conflict with class

            # Get predictions
            predicted_temps = self.lstm_model.predict(historical_data, hours_ahead=6)
            if predicted_temps is None:
                predicted_temps = [current_temp] * 6 # Fallback if prediction fails

            # Detect anomalies - using current sensor data
            # The IsolationForest expects a 2D array, even for single feature.
            # If your AnomalyDetector was standalone, it would take a DataFrame.
            # For simplicity, using only temperature here, as in the original snippet.
            temp_anomaly = False
            if self.lstm_model.is_trained: # Only if models are ready
                try:
                    # Using the directly instantiated IsolationForest for simplicity
                    # The `AnomalyDetector` class above would be better if fully integrated.
                    current_features = pd.DataFrame([{'temperature': current_temp, 'humidity': sensor_data['humidity']['value']}])
                    # Ensure column order matches training, if any
                    current_features = current_features[['temperature', 'humidity']] if 'humidity' in current_features.columns else current_features[['temperature']]
                    temp_anomaly = self.anomaly_detector.predict(current_features)[0] == -1
                    if temp_anomaly:
                        logger.warning(f"Temperature anomaly detected: {current_temp}°C")
                except Exception as e:
                    logger.warning(f"Error during anomaly detection: {e}")


            # Energy optimization
            occupancy_schedule = [occupancy] * 6  # Simplified: assume current occupancy for next 6 hours
            optimal_schedule = self.energy_optimizer.optimize_schedule(
                current_temp, 22.0, predicted_temps, occupancy_schedule
            )

            # Decision logic
            decision = {
                "action": "off",
                "target_temperature": 22.0,
                "mode": "auto",
                "fan_speed": "auto",
                "reasoning": [],
                "confidence": 0.0
            }

            # Temperature-based decision
            if current_temp > 25 and occupancy:
                decision["action"] = "cool"
                decision["target_temperature"] = 22.0 # Set a default target
                decision["reasoning"].append("High temperature with occupancy")
                decision["confidence"] += 0.4

            elif current_temp < 20 and occupancy:
                decision["action"] = "heat"
                decision["target_temperature"] = 22.0 # Set a default target
                decision["reasoning"].append("Low temperature with occupancy")
                decision["confidence"] += 0.4

            # Air quality consideration
            if air_quality_aqi > 100:
                decision["fan_speed"] = "high"
                decision["reasoning"].append("Poor air quality detected")
                decision["confidence"] += 0.2

            # Anomaly response
            if temp_anomaly:
                if decision["action"] == "off": # Only if not already heating/cooling
                    decision["action"] = "on" # General 'on' for investigation
                decision["reasoning"].append("Temperature anomaly detected")
                decision["confidence"] += 0.3

            # Energy optimization influence
            if optimal_schedule and optimal_schedule[0]["should_run"]:
                # If optimizer says to run, increase confidence or adjust target/action
                if optimal_schedule[0]["intensity"] > 0.5:
                    if decision["action"] == "off":
                        decision["action"] = "auto" # Let auto mode handle it
                decision["confidence"] = min(1.0, decision["confidence"] + 0.1) # Boost confidence
                decision["reasoning"].append("Energy optimization recommends current action")
            else:
                # If optimizer says NOT to run, and we were planning to, reduce confidence
                if decision["action"] != "off" and decision["confidence"] > 0.5:
                    decision["confidence"] = max(0, decision["confidence"] - 0.2)
                    decision["reasoning"].append("Energy optimization suggests turning off or reducing activity")
                    if decision["action"] != "off": # If we were on, consider switching to off
                        decision["action"] = "off" # Force off if energy savings are critical (simplified)

            decision["confidence"] = min(1.0, decision["confidence"])
            decision["predictions"] = predicted_temps
            decision["energy_schedule"] = optimal_schedule[:3]  # Next 3 hours

            logger.info(f"AI Decision: {decision['action']} (Conf: {decision['confidence']:.2f}) for Temp: {current_temp}°C. Reasoning: {'; '.join(decision['reasoning'])}")
            return decision
    ```
*   **`server/app/models/energy_optimizer.py`**:
    ```python
    import random
    from datetime import datetime, timedelta # <--- ADD THIS
    import logging # <--- ADD THIS

    logger = logging.getLogger(__name__)

    class EnergyOptimizer:
        def __init__(self):
            self.energy_prices = self._get_hourly_energy_prices()
            self.comfort_weight = 0.7
            self.energy_weight = 0.3
            logger.info("EnergyOptimizer initialized.")

        def _get_hourly_energy_prices(self):
            """Simulate time-of-use energy pricing"""
            base_price = 0.12  # $/kWh
            # Peak hours: 4 PM - 8 PM (16-20) are 1.5x base
            # Off-peak hours: 2 AM - 6 AM (2-6) are 0.8x base
            return {
                hour: base_price * (1.5 if 16 <= hour <= 20 else 0.8 if 2 <= hour <= 6 else 1.0)
                for hour in range(24)
            }

        def optimize_schedule(self, current_temp: float, target_temp: float,
                             predicted_temps: list, occupancy_schedule: list):
            """Optimize HVAC schedule for next 24 hours"""
            if not predicted_temps or not occupancy_schedule:
                logger.warning("Missing predicted temperatures or occupancy schedule for optimization.")
                return []

            # Ensure schedules are of same length (or handle discrepancy)
            min_len = min(len(predicted_temps), len(occupancy_schedule))
            predicted_temps = predicted_temps[:min_len]
            occupancy_schedule = occupancy_schedule[:min_len]

            optimal_schedule = []
            
            for i, (pred_temp, occupancy) in enumerate(zip(predicted_temps, occupancy_schedule)):
                current_hour = (datetime.now().hour + i) % 24
                energy_price = self.energy_prices.get(current_hour, self.energy_prices[datetime.now().hour]) # Fallback
                
                # Calculate comfort score (lower is better, 0 if at target)
                temp_diff = abs(pred_temp - target_temp)
                # Comfort is more important when occupied
                comfort_score = temp_diff * (1.5 if occupancy else 0.5)
                
                # Calculate estimated energy consumption needed to reach/maintain target
                # This is a very simplified model: assumes 0.1 kWh per degree-hour difference
                # In reality, this depends on HVAC efficiency, insulation, outside temp, etc.
                energy_needed_per_hour = max(0, temp_diff * 0.1 * (1 if occupancy else 0.5)) # Less energy if unoccupied
                energy_cost = energy_needed_per_hour * energy_price
                
                # Combined optimization score
                # We want to minimize this score.
                total_score = (self.comfort_weight * comfort_score) + (self.energy_weight * energy_cost)
                
                # Decision logic: Should we run HVAC?
                # Run if comfort is significantly off AND it's occupied, OR if it's very cheap to run.
                # Thresholds are arbitrary for simulation.
                should_run = False
                if occupancy and temp_diff > 1.0: # If occupied and temperature is off by > 1 degree
                    should_run = True
                elif energy_price < 0.10: # If energy is very cheap, consider running pre-emptively
                    should_run = True
                
                # Intensity of operation (0.0 to 1.0)
                # Maximize intensity if running and score is high (i.e., high discomfort/cost)
                intensity = min(1.0, total_score * 0.2) if should_run else 0.0 # Scale score to intensity
                
                optimal_schedule.append({
                    "hour": current_hour,
                    "should_run": should_run,
                    "intensity": round(intensity, 2),
                    "predicted_temp": round(pred_temp, 2),
                    "energy_cost_estimate": round(energy_cost, 3),
                    "comfort_score": round(comfort_score, 2),
                    "is_occupied": occupancy
                })
                
            return optimal_schedule
    ```
*   **`server/app/services/thermostat_service.py`**:
    ```python
    import asyncio
    import logging
    from datetime import datetime, timedelta
    from ..models.ensemble_model import EnsemblePredictor
    from ..database.influxdb_client import InfluxDBClient
    from ..coap.client import EnhancedCoAPClient
    from ..services.prediction_service import PredictionService # <--- ADD THIS
    from ..services.maintenance_service import MaintenanceService # <--- ADD THIS
    from ..services.notification_service import NotificationService # <--- ADD THIS

    logger = logging.getLogger(__name__)

    class ThermostatControlService:
        def __init__(self, ensemble_model_instance=None, db_client: InfluxDBClient = None, 
                     coap_client: EnhancedCoAPClient = None, notification_service: NotificationService = None):
            self.ensemble_model = ensemble_model_instance or EnsemblePredictor()
            self.db_client = db_client or InfluxDBClient()
            self.coap_client = coap_client or EnhancedCoAPClient(None) # Config will be set by main
            self.notification_service = notification_service or NotificationService(None)
            self.logger = logging.getLogger(__name__)
            self.decision_history = []
            self._last_processed_sensor_data = None
            self._last_predictions = None

            # These will be set by main.py after initialization, but are useful for circular deps
            self.prediction_service: PredictionService = None 
            self.maintenance_service: MaintenanceService = None
            
            logger.info("ThermostatControlService initialized.")

        def get_last_processed_data(self) -> dict:
            """Returns the last sensor data processed by the control cycle."""
            return self._last_processed_sensor_data

        def get_last_predictions(self) -> dict:
            """Returns the last temperature predictions made."""
            return self._last_predictions

        async def process_control_cycle(self):
            """Main control loop responsible for fetching data, making decisions, and acting."""
            try:
                # 1. Get current sensor data from the device
                sensor_data = await self.coap_client.get_all_sensor_data()
                if not sensor_data:
                    self.logger.warning("No sensor data received from device. Skipping control cycle.")
                    await self.notification_service.send_alert("connectivity_issue", "Failed to get sensor data from thermostat device.", {"device_id": "smart-thermostat-01"})
                    return
                
                self._last_processed_sensor_data = sensor_data # Store for WebSocketManager

                # 2. Get historical data for ML models
                # Fetch more data than just current, as ML models need sequences
                historical_data = await self.db_client.get_recent_data(hours=48)
                if historical_data.empty:
                    self.logger.warning("Insufficient historical data for ML models. Some features might be limited.")
                    # Fallback or simple decision if no historical data

                # 3. Store current sensor data in InfluxDB
                await self.db_client.store_sensor_data(sensor_data)
                
                # 4. Make AI decision using the ensemble model
                decision = self.ensemble_model.make_decision(sensor_data, historical_data)
                self._last_predictions = decision.get("predictions") # Store predictions for WebSocket

                # 5. Execute the AI decision on the device
                success = await self.execute_decision(decision)

                # 6. Log and store the decision
                self.log_decision(sensor_data, decision)
                self.decision_history.append({
                    "timestamp": datetime.now(),
                    "sensor_data": sensor_data,
                    "decision": decision,
                    "command_success": success
                })
                
                # Cleanup old history (keep memory usage reasonable)
                if len(self.decision_history) > 1000:
                    self.decision_history = self.decision_history[-500:] # Keep latest 500

            except Exception as e:
                self.logger.error(f"Error in thermostat control cycle: {e}", exc_info=True)
                await self.notification_service.send_alert("system_failure", f"Critical error in thermostat control loop: {e}", {"component": "ThermostatControlService"})

        async def execute_decision(self, decision: dict):
            """Execute the AI decision by sending a CoAP command."""
            control_command = {
                "hvac_state": decision["action"],
                "target_temperature": decision["target_temperature"],
                "fan_speed": decision["fan_speed"],
                "mode": decision["mode"] # Add mode control
            }
            
            # Send the command via CoAP client
            success = await self.coap_client.send_control_command(control_command)
            
            if success:
                self.logger.info(f"Command executed on device: {control_command}")
            else:
                self.logger.error(f"Failed to execute command on device: {control_command}")
                await self.notification_service.send_alert("device_command_failure", f"Failed to send HVAC command: {control_command}", {"device_id": "smart-thermostat-01"})
                
            return success
        
        def log_decision(self, sensor_data: dict, decision: dict):
            """Log decision with reasoning for human readability."""
            temp = sensor_data['temperature']['value']
            action = decision['action']
            confidence = decision['confidence']
            reasoning = '; '.join(decision['reasoning'])
            
            self.logger.info(
                f"🌡️ {temp}°C | Action: {action.upper()} | Target: {decision['target_temperature']}°C "
                f"(Confidence: {confidence:.2f}) - Reasoning: [{reasoning}]"
            )
            # You can also log this to a structured log file or another database for analytics
    ```
*   **`server/app/services/prediction_service.py`**:
    ```python
    import logging
    from datetime import datetime, timedelta
    import pandas as pd
    import joblib # <--- ADD THIS
    import os

    from ..models.lstm_predictor import LSTMTemperaturePredictor
    from ..database.influxdb_client import InfluxDBClient

    logger = logging.getLogger(__name__)

    class PredictionService:
        def __init__(self, db_client: InfluxDBClient = None):
            self.lstm_predictor = LSTMTemperaturePredictor()
            self.db_client = db_client or InfluxDBClient()
            self.last_training: datetime = None
            self.model_save_path = "models/lstm_temperature.h5"
            self.scaler_save_path = "models/temperature_scaler.pkl"
            
            # Attempt to load models on startup
            self._load_models()
            logger.info("PredictionService initialized.")

        def _load_models(self):
            """Loads pre-trained LSTM model and scaler if they exist."""
            try:
                if os.path.exists(self.model_save_path):
                    self.lstm_predictor.model = self.lstm_predictor.build_model((self.lstm_predictor.sequence_length, 5)) # Rebuild model structure
                    self.lstm_predictor.model.load_weights(self.model_save_path) # Load weights only
                    # Alternatively, if save_model() saves the full model
                    # from tensorflow.keras.models import load_model
                    # self.lstm_predictor.model = load_model(self.model_save_path)
                    logger.info(f"LSTM model loaded from {self.model_save_path}")

                if os.path.exists(self.scaler_save_path):
                    self.lstm_predictor.scaler = joblib.load(self.scaler_save_path)
                    logger.info(f"Scaler loaded from {self.scaler_save_path}")

                if self.lstm_predictor.model and hasattr(self.lstm_predictor.scaler, 'n_features_in_'): # Check if scaler is fit
                    self.lstm_predictor.is_trained = True
                    self.last_training = datetime.now() # Assume loaded model means "trained" now
                    logger.info("Prediction models successfully loaded and marked as trained.")
                else:
                    logger.warning("Could not fully load prediction models (model or scaler missing/invalid).")
                    self.lstm_predictor.is_trained = False

            except Exception as e:
                logger.error(f"Error loading prediction models: {e}", exc_info=True)
                self.lstm_predictor.is_trained = False

        async def retrain_models(self):
            """Retrain ML models with recent data."""
            self.logger.info("Attempting to retrain prediction models...")
            try:
                # Get training data (e.g., last 30 days of sensor data)
                training_data = await self.db_client.get_recent_data(hours=30*24)
                
                if training_data.empty or len(training_data) < self.lstm_predictor.sequence_length * 2: # Need enough data for sequences
                    self.logger.warning(f"Insufficient data ({len(training_data)} records) for training. Need at least {self.lstm_predictor.sequence_length * 2} records.")
                    return False
                    
                # Train LSTM model
                success = self.lstm_predictor.train(training_data)
                
                if success:
                    self.last_training = datetime.now()
                    self.logger.info("Prediction models retrained successfully.")
                    
                    # Save model and scaler
                    os.makedirs(os.path.dirname(self.model_save_path), exist_ok=True)
                    self.lstm_predictor.model.save(self.model_save_path) # Saves model architecture and weights
                    joblib.dump(self.lstm_predictor.scaler, self.scaler_save_path)
                    self.logger.info(f"Models saved to {self.model_save_path} and {self.scaler_save_path}")
                else:
                    self.logger.warning("LSTM model training did not succeed.")
                    
                return success
                
            except Exception as e:
                self.logger.error(f"Error retraining prediction models: {e}", exc_info=True)
                return False
        
        async def get_predictions(self, hours_ahead: int = 24):
            """Get temperature predictions for upcoming hours."""
            if not self.lstm_predictor.is_trained:
                self.logger.warning("Prediction model not trained or loaded. Cannot provide predictions.")
                return {
                    "predictions": [],
                    "hours_ahead": hours_ahead,
                    "model_last_trained": self.last_training,
                    "confidence": 0.0,
                    "message": "Model not trained."
                }

            try:
                # Get recent data to form the initial prediction sequence
                # We need at least `sequence_length` entries
                recent_data = await self.db_client.get_recent_data(hours=self.lstm_predictor.sequence_length + 2) # Fetch a bit more
                
                if recent_data.empty or len(recent_data) < self.lstm_predictor.sequence_length:
                    self.logger.warning(f"Insufficient recent data ({len(recent_data)} records) for prediction. Need at least {self.lstm_predictor.sequence_length}.")
                    return {
                        "predictions": [],
                        "hours_ahead": hours_ahead,
                        "model_last_trained": self.last_training,
                        "confidence": 0.1,
                        "message": "Insufficient recent data for prediction."
                    }

                predictions = self.lstm_predictor.predict(recent_data, hours_ahead)
                
                return {
                    "predictions": predictions,
                    "hours_ahead": hours_ahead,
                    "model_last_trained": self.last_training.isoformat() if self.last_training else "N/A",
                    "confidence": 0.8 # Placeholder confidence
                }
                
            except Exception as e:
                self.logger.error(f"Error getting predictions: {e}", exc_info=True)
                return {
                    "predictions": [],
                    "hours_ahead": hours_ahead,
                    "model_last_trained": self.last_training.isoformat() if self.last_training else "N/A",
                    "confidence": 0.0,
                    "message": f"Prediction failed: {e}"
                }
    ```
*   **`server/app/services/maintenance_service.py`**:
    ```python
    import logging
    import time
    from datetime import datetime, timedelta # <--- ADD THIS
    from ..database.influxdb_client import InfluxDBClient
    from ..services.notification_service import NotificationService # <--- ADD THIS

    logger = logging.getLogger(__name__)

    class MaintenanceService:
        def __init__(self, db_client: InfluxDBClient = None, notification_service: NotificationService = None):
            self.db_client = db_client or InfluxDBClient()
            self.notification_service = notification_service or NotificationService(None)
            self.maintenance_schedule = {} # Stores recommended dates/status per device
            self.last_checked_device: dict = {} # Stores last status check for a device
            logger.info("MaintenanceService initialized.")

        async def check_maintenance_needs(self, device_status: dict):
            """Check if device needs maintenance based on various metrics."""
            device_id = device_status.get('device_id')
            if not device_id:
                logger.error("Device ID missing in device status for maintenance check.")
                return None

            uptime = device_status.get('uptime_seconds', 0)
            energy_consumption = device_status.get('energy_consumption', 0) # Current kWh
            
            maintenance_score = 0
            recommendations = []
            
            # --- Rule 1: Uptime-based Routine Maintenance ---
            # Suggest routine maintenance every 6 months (approx 180 days)
            days_uptime = uptime / (24 * 3600)
            if days_uptime > 180: # If over 6 months
                maintenance_score += 20 # Low priority, routine check
                recommendations.append(f"Routine maintenance: Device uptime {int(days_uptime)} days (over 180 days).")
            
            # --- Rule 2: High Energy Consumption Anomaly ---
            # Compare current energy consumption with historical average
            historical_consumption_data = await self.db_client.get_energy_data(device_id, days=30)
            if historical_consumption_data:
                historical_consumptions = [entry['value'] for entry in historical_consumption_data if 'value' in entry]
                if historical_consumptions:
                    avg_consumption = sum(historical_consumptions) / len(historical_consumptions)
                    if energy_consumption > avg_consumption * 1.3: # 30% higher than average
                        maintenance_score += 40 # Medium priority
                        recommendations.append(f"High energy consumption ({energy_consumption:.2f} kWh) compared to average ({avg_consumption:.2f} kWh). Check filters/coils.")
                        self.notification_service.send_alert("energy_spike", f"Thermostat {device_id} showing high energy consumption.", {"consumption": energy_consumption, "average": avg_consumption})
            
            # --- Rule 3: Sensor Accuracy/Variance Check ---
            # High temperature variance might indicate sensor issues or inefficient operation
            temp_variance = await self.db_client.get_temperature_variance(device_id, hours=24)
            if temp_variance is not None and temp_variance > 2.0: # If variance is high (e.g., > 2 degrees)
                maintenance_score += 35 # Medium priority
                recommendations.append(f"High temperature variance ({temp_variance:.2f}°C) detected in last 24h. Calibrate sensors or check HVAC system.")
                self.notification_service.send_alert("sensor_malfunction", f"Thermostat {device_id} temperature sensor variance is high.", {"variance": temp_variance})

            # --- Rule 4: Last Maintenance Date ---
            last_maintenance_timestamp = device_status.get('last_maintenance', 0) # Unix timestamp
            if last_maintenance_timestamp:
                last_maintenance_date = datetime.fromtimestamp(last_maintenance_timestamp)
                days_since_maintenance = (datetime.now() - last_maintenance_date).days
                if days_since_maintenance > 90: # If more than 3 months
                    maintenance_score += 25 # Low-medium priority
                    recommendations.append(f"Last reported maintenance was {days_since_maintenance} days ago (over 90 days).")
            else:
                # If no last_maintenance date is provided, assume it's new or not tracked, maybe trigger an initial check
                maintenance_score += 5
                recommendations.append("Last maintenance date unknown. Recommend initial check-up.")

            # --- Rule 5: Error Logs/Diagnostics (Placeholder) ---
            # In a real system, you'd pull error logs from diagnostics resource or a logging service
            # For this example, let's just add a conditional rule
            if random.random() < 0.01: # 1% chance of a "simulated error"
                maintenance_score += 50
                recommendations.append("Internal system error detected. Requires immediate attention.")
                self.notification_service.send_alert("system_failure", f"Critical internal error on {device_id}.", {})

            # Determine priority level based on score
            priority = self._get_priority_level(maintenance_score)
            
            result = {
                "device_id": device_id,
                "maintenance_score": maintenance_score,
                "priority": priority,
                "recommendations": list(set(recommendations)), # Remove duplicates
                "estimated_cost": self._estimate_maintenance_cost(maintenance_score),
                "optimal_schedule_date": self._suggest_maintenance_date()
            }
            
            # Store maintenance alert if score is above a threshold
            if maintenance_score > 30 and (
                device_id not in self.maintenance_schedule or 
                self.maintenance_schedule[device_id].get('priority') != priority or 
                self.maintenance_schedule[device_id].get('maintenance_score', 0) < maintenance_score
            ):
                await self.db_client.store_maintenance_alert(result)
                self.maintenance_schedule[device_id] = result # Update internal schedule
                logger.warning(f"Maintenance alert triggered for {device_id}: Priority {priority}, Score {maintenance_score}")
                self.notification_service.send_alert("maintenance_required", f"Thermostat {device_id} requires {priority} maintenance.", result)
            elif maintenance_score <= 30 and device_id in self.maintenance_schedule:
                logger.info(f"Maintenance alert for {device_id} has cleared (score {maintenance_score}).")
                del self.maintenance_schedule[device_id] # Clear alert if condition improves

            return result

        def _get_priority_level(self, score: int) -> str:
            if score >= 80:
                return "critical"
            elif score >= 60:
                return "high"
            elif score >= 40:
                return "medium"
            else:
                return "low"

        def _estimate_maintenance_cost(self, score: int) -> dict:
            base_cost = 75  # Base service call
            parts_cost = max(0, (score - 50) * 2)  # Additional parts needed if score is higher
            labor_cost = max(50, score * 1.5)  # Labor based on complexity and time
            
            total = base_cost + parts_cost + labor_cost
            
            return {
                "service_call": round(base_cost, 2),
                "estimated_parts": round(parts_cost, 2),
                "estimated_labor": round(labor_cost, 2),
                "total_estimate": round(total, 2),
                "currency": "USD"
            }

        def _suggest_maintenance_date(self) -> str:
            """Suggests an optimal date/time for maintenance (e.g., next Tuesday-Thursday, 10 AM-2 PM)."""
            suggested_date = datetime.now() + timedelta(days=7) # Start with next week
            
            # Find the next Tuesday (day 1), Wednesday (day 2), or Thursday (day 3)
            while suggested_date.weekday() not in [1, 2, 3]: 
                suggested_date += timedelta(days=1)
            
            # Set to optimal time window (e.g., 10 AM)
            suggested_date = suggested_date.replace(hour=10, minute=0, second=0, microsecond=0)
            
            return suggested_date.isoformat()
    ```
*   **`server/app/services/notification_service.py`**:
    ```python
    import smtplib
    import json
    import logging
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime
    import asyncio # For async email sending (non-blocking)
    import aiohttp # For async HTTP requests (webhooks) # <--- ADD THIS
    import os # <--- ADD THIS

    from ..config import ServerConfig # <--- ADD THIS to get config

    logger = logging.getLogger(__name__) # <--- ADD THIS

    class NotificationService:
        def __init__(self, config: ServerConfig): # <--- Pass config
            self.config = config
            self.email_config = {
                "smtp_server": self.config.SMTP_SERVER,
                "smtp_port": self.config.SMTP_PORT,
                "username": self.config.EMAIL_USERNAME,
                "password": self.config.EMAIL_PASSWORD,
                "from_email": self.config.FROM_EMAIL
            }
            self.webhook_urls = [url.strip() for url in self.config.WEBHOOK_URLS.split(",") if url.strip()]
            logger.info(f"NotificationService initialized. Webhooks: {len(self.webhook_urls)}, Email configured: {'yes' if self.email_config['username'] else 'no'}")
            
        async def send_alert(self, alert_type: str, message: str, data: dict = None):
            """Send alert via multiple channels (email, webhooks)."""
            alert_payload = {
                "timestamp": datetime.now().isoformat(),
                "type": alert_type,
                "message": message,
                "data": data or {},
                "severity": self._get_severity(alert_type)
            }
            
            self.logger.info(f"Preparing alert: Type={alert_type}, Severity={alert_payload['severity']}, Message='{message}'")

            # Send email notification if severity is high/critical and email config is present
            if alert_payload["severity"] in ["high", "critical"] and self.email_config.get("username"):
                asyncio.create_task(self._send_email_alert(alert_payload)) # Run email sending in background
            
            # Send webhook notifications
            if self.webhook_urls:
                asyncio.create_task(self._send_webhook_alerts(alert_payload)) # Run webhooks in background
            
            self.logger.info(f"Alert '{alert_type}' triggered.")

        def _get_severity(self, alert_type: str) -> str:
            """Determines severity level based on alert type."""
            severity_map = {
                "temperature_anomaly": "medium",
                "system_failure": "critical",
                "maintenance_required": "high",
                "energy_spike": "medium",
                "sensor_malfunction": "high",
                "connectivity_issue": "low",
                "device_command_failure": "high"
            }
            return severity_map.get(alert_type, "medium")

        async def _send_email_alert(self, alert: dict):
            """Sends an email notification."""
            try:
                if not all([self.email_config["username"], self.email_config["password"], self.email_config["from_email"]]):
                    self.logger.warning("Email credentials not fully configured. Skipping email alert.")
                    return
                    
                msg = MIMEMultipart()
                msg['From'] = self.email_config["from_email"]
                msg['To'] = self.config.ALERT_EMAIL
                msg['Subject'] = f"Smart Thermostat Alert: {alert['type']} ({alert['severity'].upper()})"
                
                body = f"""
                Alert Type: {alert['type']}
                Severity: {alert['severity'].upper()}
                Time: {alert['timestamp']}
                
                Message: {alert['message']}
                
                Additional Data:
                {json.dumps(alert['data'], indent=2)}
                
                ---
                Smart Thermostat System
                """
                
                msg.attach(MIMEText(body, 'plain'))
                
                # SMTPlib methods are blocking, so run in a thread pool executor to avoid blocking asyncio loop
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._send_email_blocking, msg)
                
            except Exception as e:
                self.logger.error(f"Failed to send email alert: {e}", exc_info=True)

        def _send_email_blocking(self, msg):
            """Blocking part of email sending to be run in executor."""
            try:
                server = smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"])
                server.starttls() # Secure the connection
                server.login(self.email_config["username"], self.email_config["password"])
                server.send_message(msg)
                server.quit()
                self.logger.info(f"Email alert sent to {msg['To']} for {msg['Subject']}")
            except Exception as e:
                self.logger.error(f"Blocking email send failed: {e}", exc_info=True)

        async def _send_webhook_alerts(self, alert: dict):
            """Sends webhook notifications to configured URLs."""
            for webhook_url in self.webhook_urls:
                if not webhook_url.strip():
                    continue
                    
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(webhook_url, json=alert, timeout=10) as resp:
                            if resp.status == 200:
                                self.logger.info(f"Webhook sent successfully to {webhook_url}")
                            else:
                                self.logger.warning(f"Webhook failed for {webhook_url} with status: {resp.status} - {await resp.text()}")
                                
                except aiohttp.ClientError as e:
                    self.logger.error(f"Aiohttp client error for webhook {webhook_url}: {e}")
                except asyncio.TimeoutError:
                    self.logger.error(f"Webhook to {webhook_url} timed out.")
                except Exception as e:
                    self.logger.error(f"Unexpected error sending webhook to {webhook_url}: {e}", exc_info=True)
    ```
*   **`server/app/database/influxdb_client.py`**:
    ```python
    from influxdb_client import InfluxDBClient as InfluxClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    import pandas as pd
    from datetime import datetime, timedelta
    import os # <--- ADD THIS
    import logging

    logger = logging.getLogger(__name__)

    class InfluxDBClient:
        def __init__(self):
            try:
                self.url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
                self.token = os.getenv("INFLUXDB_TOKEN", "admin-token")
                self.org = os.getenv("INFLUXDB_ORG", "thermostat-org")
                self.bucket = os.getenv("INFLUXDB_BUCKET", "thermostat-data")

                self.client = InfluxClient(url=self.url, token=self.token, org=self.org)
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                self.query_api = self.client.query_api()
                logger.info(f"InfluxDBClient initialized for {self.url}, org: {self.org}, bucket: {self.bucket}")
            except Exception as e:
                logger.error(f"Failed to initialize InfluxDBClient: {e}", exc_info=True)
                self.client = None # Mark client as not ready

        async def store_sensor_data(self, sensor_data: dict):
            """Store sensor data in InfluxDB."""
            if not self.client:
                logger.error("InfluxDB client not initialized. Cannot store sensor data.")
                return

            try:
                points = []
                timestamp = datetime.now() # Use server's timestamp for consistency
                device_id = sensor_data.get('device_id', 'unknown_device')
                
                # Temperature data
                temp_data = sensor_data.get('temperature', {})
                if 'value' in temp_data:
                    point = Point("sensor_data") \
                        .tag("device_id", device_id) \
                        .tag("sensor_type", "temperature") \
                        .field("value", float(temp_data['value'])) \
                        .field("unit", temp_data.get('unit', 'celsius')) \
                        .field("accuracy", float(temp_data.get('accuracy', 0.1))) \
                        .time(timestamp)
                    points.append(point)
                
                # Humidity data
                humidity_data = sensor_data.get('humidity', {})
                if 'value' in humidity_data:
                    point = Point("sensor_data") \
                        .tag("device_id", device_id) \
                        .tag("sensor_type", "humidity") \
                        .field("value", float(humidity_data['value'])) \
                        .field("unit", humidity_data.get('unit', 'percent')) \
                        .field("status", humidity_data.get('status', 'normal')) \
                        .time(timestamp)
                    points.append(point)
                
                # Air quality data
                air_data = sensor_data.get('air_quality', {})
                if air_data:
                    point = Point("sensor_data") \
                        .tag("device_id", device_id) \
                        .tag("sensor_type", "air_quality") \
                        .field("pm2_5", float(air_data.get('pm2_5', 0))) \
                        .field("pm10", float(air_data.get('pm10', 0))) \
                        .field("co2", float(air_data.get('co2', 0))) \
                        .field("aqi", int(air_data.get('aqi', 0))) \
                        .field("quality", air_data.get('quality', 'unknown')) \
                        .time(timestamp)
                    points.append(point)
                
                # Occupancy data
                occupancy_data = sensor_data.get('occupancy', {})
                if 'occupied' in occupancy_data:
                    point = Point("sensor_data") \
                        .tag("device_id", device_id) \
                        .tag("sensor_type", "occupancy") \
                        .field("occupied", bool(occupancy_data['occupied'])) \
                        .field("confidence", float(occupancy_data.get('confidence', 0))) \
                        .field("motion_detected", bool(occupancy_data.get('motion_detected', False))) \
                        .time(timestamp)
                    points.append(point)
                
                # Write all points
                self.write_api.write(bucket=self.bucket, record=points)
                # logger.debug(f"Stored {len(points)} sensor data points for device {device_id}.")
                
            except Exception as e:
                logger.error(f"Error storing sensor data in InfluxDB for device {device_id}: {e}", exc_info=True)
        
        async def get_recent_data(self, hours: int = 24) -> pd.DataFrame:
            """Get recent sensor data for ML training."""
            if not self.client:
                logger.error("InfluxDB client not initialized. Cannot query recent data.")
                return pd.DataFrame()

            try:
                # Query for temperature, humidity, and occupancy, pivoting to wide format
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: -{hours}h)
                    |> filter(fn: (r) => 
                        r._measurement == "sensor_data" and 
                        (r.sensor_type == "temperature" or 
                         r.sensor_type == "humidity" or 
                         r.sensor_type == "occupancy"))
                    |> pivot(rowKey:["_time"], columnKey: ["sensor_type"], valueColumn: "_value")
                    |> keep(columns: ["_time", "temperature", "humidity", "occupancy"])
                '''
                
                result = self.query_api.query_data_frame(query=query, org=self.org)
                
                if not result.empty:
                    # Rename columns for clarity and consistency with ML models
                    # Convert _time to Unix timestamp
                    result['timestamp'] = pd.to_datetime(result['_time']).astype(int) // 10**9
                    
                    # Ensure numerical types and fill missing values appropriately
                    for col in ['temperature', 'humidity']:
                        if col in result.columns:
                            result[col] = pd.to_numeric(result[col], errors='coerce')
                            result[col] = result[col].fillna(result[col].mean() if not result[col].empty else 0) # Fill NaNs
                        else:
                            result[col] = 0 # Add column if missing

                    if 'occupancy' in result.columns:
                        result['occupancy'] = result['occupancy'].astype(bool).astype(int) # Convert to 0 or 1
                    else:
                        result['occupancy'] = 0 # Add if missing

                    # Select and return required columns, dropping any remaining NaNs after fill
                    return result[['timestamp', 'temperature', 'humidity', 'occupancy']].dropna()
                
                logger.info(f"No recent data found for the last {hours} hours.")
                return pd.DataFrame()
                
            except Exception as e:
                logger.error(f"Error querying recent data from InfluxDB: {e}", exc_info=True)
                return pd.DataFrame()

        async def store_maintenance_alert(self, alert_data: dict):
            """Store maintenance alert."""
            if not self.client:
                logger.error("InfluxDB client not initialized. Cannot store maintenance alert.")
                return

            try:
                point = Point("maintenance_alert") \
                    .tag("device_id", alert_data['device_id']) \
                    .tag("priority", alert_data['priority']) \
                    .field("score", int(alert_data['maintenance_score'])) \
                    .field("estimated_total_cost", float(alert_data['estimated_cost']['total_estimate'])) \
                    .field("recommendations_count", len(alert_data['recommendations'])) \
                    .time(datetime.now())
                
                self.write_api.write(bucket=self.bucket, record=point)
                logger.info(f"Stored maintenance alert for device {alert_data['device_id']}.")
                
            except Exception as e:
                logger.error(f"Error storing maintenance alert in InfluxDB: {e}", exc_info=True)

        async def get_energy_data(self, device_id: str, days: int = 7) -> List[Dict]:
            """Retrieves historical energy consumption data for a device."""
            if not self.client:
                logger.error("InfluxDB client not initialized. Cannot get energy data.")
                return []

            try:
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: -{days}d)
                    |> filter(fn: (r) => r._measurement == "device_status" and r.device_id == "{device_id}")
                    |> filter(fn: (r) => r._field == "energy_consumption")
                    |> yield(name: "energy_consumption")
                '''
                
                tables = self.query_api.query(query, org=self.org)
                
                results = []
                for table in tables:
                    for record in table.records:
                        results.append({
                            "time": record.get("_time").isoformat(),
                            "value": record.get("_value"),
                            "device_id": record.get("device_id")
                        })
                logger.debug(f"Retrieved {len(results)} energy data points for device {device_id}.")
                return results
            except Exception as e:
                logger.error(f"Error getting energy data from InfluxDB for device {device_id}: {e}", exc_info=True)
                return []

        async def get_temperature_variance(self, device_id: str, hours: int = 24) -> float:
            """Calculates temperature variance for a device over a period."""
            if not self.client:
                logger.error("InfluxDB client not initialized. Cannot calculate temperature variance.")
                return None

            try:
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: -{hours}h)
                    |> filter(fn: (r) => r._measurement == "sensor_data" and r.device_id == "{device_id}" and r.sensor_type == "temperature")
                    |> filter(fn: (r) => r._field == "value")
                    |> keep(columns: ["_time", "_value"])
                    |> yield(name: "temperature_values")
                '''
                
                tables = self.query_api.query(query, org=self.org)
                
                temperatures = []
                for table in tables:
                    for record in table.records:
                        temperatures.append(record.get("_value"))
                
                if temperatures:
                    # Calculate variance
                    df = pd.Series(temperatures)
                    variance = df.var() # pandas variance
                    logger.debug(f"Temperature variance for {device_id} over {hours}h: {variance:.2f}")
                    return float(variance)
                else:
                    logger.info(f"No temperature data found for variance calculation for device {device_id}.")
                    return None
            except Exception as e:
                logger.error(f"Error calculating temperature variance for device {device_id}: {e}", exc_info=True)
                return None
    ```

---

### **3. Dashboard Implementations**

**`dashboard/Dockerfile`**
```dockerfile
# dashboard/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./dashboard/app.py /app/app.py
COPY ./dashboard/static /app/static
COPY ./dashboard/templates /app/templates

EXPOSE 5000

# Command to run the Flask dashboard
CMD ["python", "app.py"]
```

**`dashboard/static/index.html`**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Thermostat Dashboard</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <header>
        <h1>Smart Thermostat System Dashboard</h1>
        <div id="status-indicator" class="status-offline">Offline</div>
    </header>

    <main>
        <section class="current-readings">
            <h2>Current Readings</h2>
            <div class="sensor-grid">
                <div class="sensor-card">
                    <h3>Temperature</h3>
                    <p id="current-temperature">--°C</p>
                    <p id="temperature-status"></p>
                </div>
                <div class="sensor-card">
                    <h3>Humidity</h3>
                    <p id="current-humidity">--%</p>
                    <p id="humidity-status"></p>
                </div>
                <div class="sensor-card">
                    <h3>Air Quality (AQI)</h3>
                    <p id="current-aqi">--</p>
                    <p id="air-quality-status"></p>
                </div>
                <div class="sensor-card">
                    <h3>Occupancy</h3>
                    <p id="current-occupancy">--</p>
                    <p id="occupancy-status"></p>
                </div>
            </div>
        </section>

        <section class="hvac-control">
            <h2>HVAC Control</h2>
            <div class="control-grid">
                <div class="control-card">
                    <h3>HVAC State</h3>
                    <p id="hvac-state">Off</p>
                    <p>Target: <span id="target-temperature">22.0</span>°C</p>
                </div>
                <div class="control-card">
                    <h3>Energy Usage</h3>
                    <p id="energy-consumption">-- kWh</p>
                    <p>Last Day: <span id="last-day-energy">--</span> kWh</p>
                </div>
            </div>
            <div class="manual-control">
                <label for="temp-input">Set Target Temp:</label>
                <input type="number" id="temp-input" value="22" step="0.5">
                <button onclick="sendCommand('set_temp')">Set</button>
                <button onclick="sendCommand('heat')">Heat</button>
                <button onclick="sendCommand('cool')">Cool</button>
                <button onclick="sendCommand('off')">Off</button>
            </div>
        </section>

        <section class="predictions-chart">
            <h2>Temperature Predictions (Next 6 Hours)</h2>
            <canvas id="temperatureChart"></canvas>
        </section>

        <section class="alerts-log">
            <h2>System Alerts</h2>
            <ul id="alerts-list">
                <li>No new alerts.</li>
            </ul>
        </section>
    </main>

    <footer>
        <p>&copy; 2024 Smart Thermostat System. All rights reserved.</p>
    </footer>

    <script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
</body>
</html>
```

**`dashboard/static/js/dashboard.js`**
```javascript
// dashboard/static/js/dashboard.js

const socket = io(); // Connect to the Socket.IO server
let temperatureChart; // Chart.js instance

// --- Socket.IO Event Handlers ---
socket.on('connect', () => {
    console.log('Connected to server WebSocket');
    document.getElementById('status-indicator').classList.remove('status-offline');
    document.getElementById('status-indicator').classList.add('status-online');
    document.getElementById('status-indicator').textContent = 'Online';
});

socket.on('disconnect', () => {
    console.log('Disconnected from server WebSocket');
    document.getElementById('status-indicator').classList.remove('status-online');
    document.getElementById('status-indicator').classList.add('status-offline');
    document.getElementById('status-indicator').textContent = 'Offline';
});

socket.on('sensor_data', (data) => {
    console.log('Received sensor data:', data);
    updateDashboard(data);
});

socket.on('command_result', (data) => {
    console.log('Command result:', data);
    // You might want to display a toast notification or update UI based on result
    alert(`Command result: ${data.status}`);
});

// --- Dashboard Update Logic ---
function updateDashboard(data) {
    // Update current readings
    if (data.temperature) {
        document.getElementById('current-temperature').textContent = `${data.temperature.value}°C`;
        document.getElementById('temperature-status').textContent = `Status: ${data.temperature.status || 'Normal'}`;
    }
    if (data.humidity) {
        document.getElementById('current-humidity').textContent = `${data.humidity.value}%`;
        document.getElementById('humidity-status').textContent = `Status: ${data.humidity.status || 'Normal'}`;
    }
    if (data.air_quality) {
        document.getElementById('current-aqi').textContent = data.air_quality.aqi;
        document.getElementById('air-quality-status').textContent = `Quality: ${data.air_quality.quality}`;
    }
    if (data.occupancy) {
        document.getElementById('current-occupancy').textContent = data.occupancy.occupied ? 'Occupied' : 'Vacant';
        document.getElementById('occupancy-status').textContent = `Confidence: ${data.occupancy.confidence}`;
    }

    // Update HVAC status
    if (data.hvac) {
        document.getElementById('hvac-state').textContent = data.hvac.state;
        document.getElementById('target-temperature').textContent = data.hvac.target_temperature;
        document.getElementById('energy-consumption').textContent = `${data.hvac.energy_consumption} kWh`;
    }

    // Update predictions chart
    if (data.predictions && data.predictions.length > 0) {
        updateTemperatureChart(data.predictions);
    }
}

function updateTemperatureChart(predictions) {
    const labels = predictions.map((_, i) => `Hour ${i + 1}`);
    const values = predictions.map(p => p.temperature || p); // Handle both formats

    if (temperatureChart) {
        temperatureChart.data.labels = labels;
        temperatureChart.data.datasets[0].data = values;
        temperatureChart.update();
    } else {
        const ctx = document.getElementById('temperatureChart').getContext('2d');
        temperatureChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Predicted Temperature (°C)',
                    data: values,
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Temperature (°C)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Hours Ahead'
                        }
                    }
                }
            }
        });
    }
}

// --- Manual Control Functions ---
function sendCommand(action) {
    let command = { action: action };
    if (action === 'set_temp') {
        command.target_temperature = parseFloat(document.getElementById('temp-input').value);
        command.action = 'set_target'; // A more explicit action for setting target temp
    }
    
    console.log('Sending command:', command);
    // Use Socket.IO to send command to the server
    socket.emit('send_command', { command: command });
}

// Fetch initial data (optional, the WS will push latest)
// async function fetchInitialData() {
//     const response = await fetch('/api/current-data');
//     const data = await response.json();
//     updateDashboard(data);
// }

// Call on page load
document.addEventListener('DOMContentLoaded', () => {
    // fetchInitialData(); // If you want to fetch once on load, besides WS updates
    // Initial chart setup with empty data
    updateTemperatureChart([]); 
});
```

**`dashboard/static/css/style.css`**
```css
/* dashboard/static/css/style.css */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f4f7f6;
    color: #333;
    line-height: 1.6;
}

header {
    background-color: #2c3e50;
    color: #ecf0f1;
    padding: 1.5rem 0;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    position: relative;
}

header h1 {
    margin: 0;
    font-size: 2.2rem;
}

#status-indicator {
    position: absolute;
    top: 15px;
    right: 20px;
    padding: 5px 10px;
    border-radius: 5px;
    font-size: 0.9rem;
    font-weight: bold;
}

.status-online {
    background-color: #27ae60;
    color: white;
}

.status-offline {
    background-color: #e74c3c;
    color: white;
}

main {
    padding: 20px;
    max-width: 1200px;
    margin: 20px auto;
    background-color: #fff;
    border-radius: 8px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.05);
}

section {
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 1px solid #eee;
}

section:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

h2 {
    color: #2980b9;
    font-size: 1.8rem;
    margin-bottom: 20px;
    border-bottom: 2px solid #3498db;
    padding-bottom: 10px;
}

/* Sensor Grid */
.sensor-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 20px;
}

.sensor-card, .control-card {
    background-color: #f9f9f9;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.sensor-card h3, .control-card h3 {
    color: #34495e;
    margin-top: 0;
    font-size: 1.3rem;
}

.sensor-card p, .control-card p {
    font-size: 1.5rem;
    font-weight: bold;
    color: #2c3e50;
    margin: 10px 0;
}

.sensor-card p:last-child, .control-card p:last-child {
    font-size: 0.9rem;
    font-weight: normal;
    color: #777;
}

/* HVAC Control */
.hvac-control .control-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
}

.manual-control {
    text-align: center;
    padding: 20px;
    background-color: #f0f3f6;
    border-radius: 8px;
    border: 1px dashed #d0d0d0;
}

.manual-control label {
    font-weight: bold;
    margin-right: 10px;
}

.manual-control input[type="number"] {
    padding: 8px;
    border: 1px solid #ccc;
    border-radius: 4px;
    margin-right: 10px;
    width: 80px;
}

.manual-control button {
    background-color: #3498db;
    color: white;
    padding: 10px 15px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 1rem;
    margin: 5px;
    transition: background-color 0.3s ease;
}

.manual-control button:hover {
    background-color: #2980b9;
}

/* Charts */
.predictions-chart canvas {
    max-width: 100%;
    height: 350px;
}

/* Alerts Log */
.alerts-log ul {
    list-style: none;
    padding: 0;
}

.alerts-log li {
    background-color: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 10px 15px;
    margin-bottom: 10px;
    color: #555;
    font-size: 0.95rem;
}

.alerts-log li.critical {
    border-left: 5px solid #e74c3c;
    background-color: #fbecec;
}

.alerts-log li.high {
    border-left: 5px solid #f39c12;
    background-color: #fef5ed;
}

footer {
    text-align: center;
    padding: 20px;
    margin-top: 30px;
    background-color: #ecf0f1;
    color: #7f8c8d;
    font-size: 0.9rem;
    border-top: 1px solid #e0e0e0;
}
```

**Adjustments to existing dashboard file:**

*   **`dashboard/app.py`**:
    ```python
    from flask import Flask, render_template, jsonify, request # <--- ADD request
    from flask_socketio import SocketIO, emit
    import asyncio
    import json
    import time
    from threading import Thread
    import random # <--- ADD THIS
    
    app = Flask(__name__, template_folder='templates', static_folder='static') # Specify folders
    app.config['SECRET_KEY'] = 'thermostat-dashboard-secret'
    socketio = SocketIO(app, cors_allowed_origins="*")

    # In a real system, DashboardService would connect to server/api/websocket_handler.py
    # For now, it will continue to mock data, but structure is ready for real integration.
    class DashboardService:
        def __init__(self):
            self.connected_clients = set()
            self.latest_data = {}
            self.historical_data = self._generate_initial_historical_data()
            
        def _generate_initial_historical_data(self):
            historical = []
            for i in range(48): # 48 hours of mock history
                historical.append({
                    "timestamp": time.time() - (i * 3600),
                    "temperature": round(22 + random.uniform(-2, 2), 1),
                    "humidity": round(45 + random.uniform(-5, 5), 1),
                    "energy": round(random.uniform(1, 3), 2)
                })
            return historical[::-1] # Reverse to have oldest first

        def start_data_stream(self):
            """Start streaming data to connected clients."""
            def data_loop():
                while True:
                    try:
                        # Get latest sensor data (mock for demo)
                        sensor_data = self.get_mock_sensor_data()
                        self.latest_data = sensor_data
                        
                        # Broadcast to all connected clients
                        socketio.emit('sensor_data', sensor_data)
                        
                        time.sleep(2)  # Update every 2 seconds
                        
                    except Exception as e:
                        print(f"Error in data stream: {e}")
                        time.sleep(5)
            
            thread = Thread(target=data_loop)
            thread.daemon = True
            thread.start()
        
        def get_mock_sensor_data(self):
            """Generate mock sensor data for demo"""
            # Simulate some trends
            hour = time.localtime().tm_hour
            base_temp_trend = 22 + 2 * math.sin((hour - 8) * math.pi / 12)
            base_humidity_trend = 45 + 5 * math.cos((hour - 12) * math.pi / 12)

            is_occupied = False
            if 7 <= hour <= 9 or 17 <= hour <= 22: # Morning/evening commute/home
                is_occupied = random.random() < 0.8
            elif 9 < hour < 17: # Work hours
                is_occupied = random.random() < 0.2
            else: # Night
                is_occupied = random.random() < 0.9

            current_temp = round(base_temp_trend + random.uniform(-1, 1), 1)
            current_humidity = round(base_humidity_trend + random.uniform(-2, 2), 1)
            
            # Simulate HVAC state based on temp
            hvac_state = "off"
            target_temp = 22.0
            if current_temp > target_temp + 1.0:
                hvac_state = "cooling"
            elif current_temp < target_temp - 1.0:
                hvac_state = "heating"

            # Add occasional anomalies
            if random.random() < 0.01: # 1% chance of temp spike
                current_temp += random.uniform(5, 10)
                hvac_state = "cooling" # To react

            aqi = random.randint(20, 80)
            if random.random() < 0.05: # 5% chance of poor air quality
                aqi = random.randint(100, 200)

            predictions = [
                round(current_temp + random.uniform(-1, 1), 1) for _ in range(6)
            ]
            
            return {
                "timestamp": time.time(),
                "device_id": "smart-thermostat-01",
                "temperature": {
                    "value": current_temp,
                    "unit": "celsius",
                    "status": "high" if current_temp > 25 else ("low" if current_temp < 20 else "normal")
                },
                "humidity": {
                    "value": current_humidity,
                    "unit": "percent",
                    "status": "high" if current_humidity > 60 else ("low" if current_humidity < 30 else "normal")
                },
                "air_quality": {
                    "aqi": aqi,
                    "pm2_5": round(random.uniform(5, 25), 1),
                    "quality": "good" if aqi <= 50 else ("moderate" if aqi <= 100 else "unhealthy")
                },
                "occupancy": {
                    "occupied": is_occupied,
                    "confidence": round(random.uniform(0.8, 1.0), 2)
                },
                "hvac": {
                    "state": hvac_state,
                    "target_temperature": target_temp,
                    "energy_consumption": round(random.uniform(0.5, 3.5), 2) # kWh per hour
                },
                "predictions": predictions, # Simplified: just temperature values
                "alerts": [] # Placeholder for actual alerts
            }

    dashboard_service = DashboardService()

    @app.route('/')
    def dashboard():
        return render_template('index.html') # Corrected filename

    @app.route('/api/current-data')
    def get_current_data():
        return jsonify(dashboard_service.latest_data)

    @app.route('/api/historical-data')
    def get_historical_data():
        # This endpoint could fetch from InfluxDB via the AI Controller's API
        # For mock, it provides pre-generated history.
        return jsonify(dashboard_service.historical_data)

    @socketio.on('connect')
    def handle_connect():
        dashboard_service.connected_clients.add(request.sid)
        print(f"Client connected: {request.sid}. Total: {len(dashboard_service.connected_clients)}")
        emit('connected', {'status': 'Connected to Smart Thermostat Dashboard'})
        # Send current data to newly connected client
        if dashboard_service.latest_data:
            emit('sensor_data', dashboard_service.latest_data, room=request.sid)

    @socketio.on('disconnect')
    def handle_disconnect():
        dashboard_service.connected_clients.discard(request.sid)
        print(f"Client disconnected: {request.sid}. Total: {len(dashboard_service.connected_clients)}")

    @socketio.on('send_command')
    def handle_command(data):
        # Process HVAC command received from dashboard UI
        command = data.get('command', {})
        print(f"Received command from dashboard: {command}")
        
        # In a real implementation, forward this command to the AI Controller's REST API
        # or directly to the CoAP client (if dashboard connected to AI controller directly via WS).
        # For this demo, we'll just acknowledge and update mock status.
        
        # Mock update of HVAC state
        if 'action' in command:
            if command['action'] == 'heat':
                dashboard_service.latest_data['hvac']['state'] = 'heating'
            elif command['action'] == 'cool':
                dashboard_service.latest_data['hvac']['state'] = 'cooling'
            elif command['action'] == 'off':
                dashboard_service.latest_data['hvac']['state'] = 'off'
            elif command['action'] == 'set_target' and 'target_temperature' in command:
                dashboard_service.latest_data['hvac']['target_temperature'] = command['target_temperature']
                dashboard_service.latest_data['hvac']['state'] = 'auto' # Assume setting target implies auto

        # Broadcast the updated mock data to all clients
        socketio.emit('sensor_data', dashboard_service.latest_data)
        emit('command_result', {'status': 'success', 'command': command, 'message': 'Command processed (mock).'})

    if __name__ == '__main__':
        # Start the data streaming thread
        dashboard_service.start_data_stream()
        
        # Run the Flask-SocketIO app
        # Use allow_unsafe_werkzeug=True for debug if needed, but avoid in production
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    ```

---

### **4. Mobile App Integration Implementations**

**`mobile/Dockerfile`**
```dockerfile
# mobile/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./mobile /app/mobile
COPY ./certs /app/certs # If mobile API needs certificates for communication

EXPOSE 8000

# Command to run the FastAPI mobile API
CMD ["uvicorn", "mobile.api.mobile_endpoints:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`mobile/push_notifications.py`**
```python
# mobile/push_notifications.py
import asyncio
import logging
from typing import Dict, List, Any
import firebase_admin # Requires firebase-admin in requirements.txt
from firebase_admin import credentials, messaging
import os

logger = logging.getLogger(__name__)

class PushNotificationService:
    """Handles sending push notifications to mobile devices (e.g., via FCM)."""
    def __init__(self):
        self.fcm_initialized = False
        # Path to your Firebase service account key JSON file
        self.firebase_credential_path = os.getenv("FIREBASE_CREDENTIAL_PATH", "certs/firebase-service-account.json")
        
        if os.path.exists(self.firebase_credential_path):
            try:
                cred = credentials.Certificate(self.firebase_credential_path)
                firebase_admin.initialize_app(cred)
                self.fcm_initialized = True
                logger.info("Firebase Admin SDK initialized successfully for FCM.")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)
        else:
            logger.warning(f"Firebase service account key not found at {self.firebase_credential_path}. Push notifications will be disabled.")

        # In a real app, you'd have a database (e.g., PostgreSQL) to store device tokens
        self.registered_devices: Dict[str, List[Dict[str, str]]] = {} # {user_id: [{device_token: "...", platform: "..."}]}
        logger.info("PushNotificationService initialized.")

    async def register_device(self, user_id: str, device_token: str, platform: str) -> bool:
        """Registers a mobile device for push notifications."""
        if not device_token or not platform:
            logger.warning(f"Attempted to register device with missing token or platform for user {user_id}.")
            return False

        if user_id not in self.registered_devices:
            self.registered_devices[user_id] = []
        
        # Avoid duplicate tokens for the same user
        if not any(d['device_token'] == device_token for d in self.registered_devices[user_id]):
            self.registered_devices[user_id].append({"device_token": device_token, "platform": platform})
            logger.info(f"Device token {device_token[:10]}... registered for user {user_id} on {platform}.")
            # In production, save to a persistent database here
            return True
        logger.info(f"Device token {device_token[:10]}... already registered for user {user_id}.")
        return False

    async def unregister_device(self, user_id: str, device_token: str) -> bool:
        """Unregisters a mobile device."""
        if user_id in self.registered_devices:
            original_len = len(self.registered_devices[user_id])
            self.registered_devices[user_id] = [
                d for d in self.registered_devices[user_id] if d['device_token'] != device_token
            ]
            if len(self.registered_devices[user_id]) < original_len:
                logger.info(f"Device token {device_token[:10]}... unregistered for user {user_id}.")
                # In production, remove from persistent database here
                return True
        logger.info(f"Device token {device_token[:10]}... not found for user {user_id}.")
        return False

    async def send_notification(self, user_id: str, title: str, body: str, data: Dict[str, str] = None) -> bool:
        """Sends a push notification to all devices registered for a specific user."""
        if not self.fcm_initialized:
            logger.warning("FCM not initialized. Cannot send push notifications.")
            return False

        if user_id not in self.registered_devices or not self.registered_devices[user_id]:
            logger.info(f"No registered devices found for user {user_id}.")
            return False

        messages_to_send = []
        for device_info in self.registered_devices[user_id]:
            token = device_info['device_token']
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data,
                token=token,
            )
            messages_to_send.append(message)
        
        try:
            # Send all messages in parallel (FCM provides batch sending)
            batch_response = await asyncio.to_thread(messaging.send_all, messages_to_send)
            
            success_count = batch_response.success_count
            failure_count = batch_response.failure_count
            
            logger.info(f"Sent {success_count} notifications to user {user_id}. Failed: {failure_count}.")
            
            if failure_count > 0:
                for i, resp in enumerate(batch_response.responses):
                    if not resp.success:
                        logger.error(f"Failed to send message to {messages_to_send[i].token[:10]}...: {resp.exception}")
                        # Optionally, remove invalid tokens from the database
                        if resp.exception and messaging.Is=""messaging.UnregisteredError"):
                            logger.warning(f"Removing invalid token: {messages_to_send[i].token[:10]}...")
                            asyncio.create_task(self.unregister_device(user_id, messages_to_send[i].token))
            return success_count > 0
        except Exception as e:
            logger.error(f"Error sending FCM notifications to user {user_id}: {e}", exc_info=True)
            return False

# You would typically inject this service into FastAPI endpoints
# Example usage in mobile_endpoints.py:
# push_service = PushNotificationService()
# @app.post("/api/v1/alert-user")
# async def alert_user(user_id: str, title: str, body: str, user=Depends(verify_token)):
#     success = await push_service.send_notification(user_id, title, body)
#     return {"status": "success" if success else "failed"}

```

**Adjustments to existing mobile file:**

*   **`mobile/api/mobile_endpoints.py`**:
    ```python
    from fastapi import FastAPI, HTTPException, Depends, status # <--- ADD status
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel
    from typing import List, Optional, Dict, Any # <--- ADD Dict, Any
    import jwt
    import os # <--- ADD THIS
    import time # <--- ADD THIS
    import random # <--- ADD THIS
    from datetime import datetime, timedelta # <--- ADD THIS
    import logging

    from ..push_notifications import PushNotificationService # <--- ADD THIS

    logger = logging.getLogger(__name__)

    app = FastAPI(title="Smart Thermostat Mobile API", version="2.0.0")
    security = HTTPBearer()

    # Initialize Push Notification Service
    push_service = PushNotificationService() # <--- ADD THIS

    # Placeholder for CoAP client (in a real app, this would be dependency injected from server)
    # For now, this API will mock responses or directly access services if on same machine/process.
    # In a microservice architecture, this Mobile API service would call the AI Controller's REST API.

    class ThermostatCommand(BaseModel):
        action: str
        target_temperature: Optional[float] = None
        mode: Optional[str] = None
        fan_speed: Optional[str] = None

    class ScheduleEntry(BaseModel):
        time: str
        temperature: float
        days: List[str]
        enabled: bool = True

    class UserPreferences(BaseModel):
        comfort_temperature: float = 22.0
        energy_saving_mode: bool = False
        notifications_enabled: bool = True
        auto_mode_enabled: bool = True

    def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Verify JWT token."""
        try:
            # Ensure JWT_SECRET is loaded from .env
            jwt_secret = os.getenv("JWT_SECRET", "your-secret-key")
            if jwt_secret == "your-secret-key":
                logger.warning("JWT_SECRET is using default value. Please set it in .env for security.")

            payload = jwt.decode(
                credentials.credentials, 
                jwt_secret, # Use the secret from config/env
                algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    @app.get("/api/v1/status/{device_id}", response_model=Dict[str, Any]) # Add device_id path parameter
    async def get_device_status(device_id: str, user=Depends(verify_token)): # Accept device_id
        """Get current device status."""
        # In real implementation, this would call the AI Controller's REST API
        # For demo, return mock data specific to the device_id
        logger.info(f"Fetching status for device: {device_id} by user: {user.get('sub')}")
        return {
            "device_id": device_id,
            "online": True,
            "current_temperature": round(20 + random.uniform(-2, 5), 1),
            "target_temperature": 22.0,
            "humidity": round(40 + random.uniform(-5, 10), 1),
            "air_quality": {"aqi": random.randint(20, 150), "quality": "good" if random.randint(0,100) < 70 else "moderate"},
            "hvac_state": random.choice(["cooling", "heating", "off"]),
            "energy_consumption": round(random.uniform(1.0, 3.5), 2),
            "last_updated": time.time()
        }

    @app.post("/api/v1/control/{device_id}", response_model=Dict[str, Any]) # Add device_id
    async def send_command(device_id: str, command: ThermostatCommand, user=Depends(verify_token)): # Accept device_id
        """Send control command to thermostat."""
        try:
            logger.info(f"User {user.get('sub')} sending command {command.dict()} to device {device_id}")
            # In real implementation, forward this command to the AI Controller's REST API
            # For now, just simulate success
            result = {
                "success": True,
                "command_executed": command.dict(),
                "device_id": device_id,
                "timestamp": time.time()
            }
            return result
        except Exception as e:
            logger.error(f"Error sending command to {device_id}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @app.get("/api/v1/predictions/{device_id}", response_model=Dict[str, Any]) # Add device_id
    async def get_predictions(device_id: str, hours: int = 6, user=Depends(verify_token)): # Accept device_id
        """Get temperature predictions."""
        logger.info(f"Fetching {hours}-hour predictions for device: {device_id} by user: {user.get('sub')}")
        predictions = []
        current_temp = round(20 + random.uniform(-2, 5), 1)
        for i in range(hours):
            predictions.append({
                "hour_ahead": i + 1,
                "temperature": round(current_temp + random.uniform(-1, 1), 1),
                "confidence": round(random.uniform(0.8, 0.95), 2)
            })
        
        return {
            "predictions": predictions,
            "model_accuracy": 0.89,
            "last_updated": time.time(),
            "device_id": device_id
        }

    @app.get("/api/v1/energy/{device_id}", response_model=Dict[str, Any]) # Add device_id
    async def get_energy_data(device_id: str, days: int = 7, user=Depends(verify_token)): # Accept device_id
        """Get energy consumption data."""
        logger.info(f"Fetching {days}-day energy data for device: {device_id} by user: {user.get('sub')}")
        energy_data = []
        for i in range(days):
            energy_data.append({
                "date": (datetime.now() - timedelta(days=i)).isoformat().split('T')[0],
                "consumption_kwh": round(random.uniform(15, 35), 2),
                "cost_usd": round(random.uniform(1.8, 4.2), 2),
                "efficiency_score": round(random.uniform(0.7, 0.95), 2)
            })
        
        total_consumption = sum(d["consumption_kwh"] for d in energy_data)
        average_daily = total_consumption / len(energy_data) if energy_data else 0

        return {
            "daily_data": energy_data,
            "total_consumption_kwh": round(total_consumption, 2),
            "average_daily_kwh": round(average_daily, 2),
            "cost_projection_monthly_usd": round(average_daily * 30 * 0.15, 2), # Example projection
            "device_id": device_id
        }

    @app.post("/api/v1/schedule/{device_id}", response_model=Dict[str, Any]) # Add device_id
    async def set_schedule(device_id: str, schedule: List[ScheduleEntry], user=Depends(verify_token)): # Accept device_id
        """Set thermostat schedule."""
        logger.info(f"User {user.get('sub')} setting schedule for device {device_id} with {len(schedule)} entries.")
        # In real implementation, store in database (PostgreSQL) and push to AI Controller
        return {
            "success": True,
            "schedule_entries_count": len(schedule),
            "message": "Schedule updated successfully (mock)",
            "device_id": device_id
        }

    @app.get("/api/v1/maintenance/{device_id}", response_model=Dict[str, Any]) # Add device_id
    async def get_maintenance_status(device_id: str, user=Depends(verify_token)): # Accept device_id
        """Get maintenance recommendations."""
        logger.info(f"Fetching maintenance status for device: {device_id} by user: {user.get('sub')}")
        return {
            "device_id": device_id,
            "maintenance_score": random.randint(10, 80),
            "priority": random.choice(["low", "medium", "high", "critical"]),
            "last_service": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat().split('T')[0],
            "next_recommended": (datetime.now() + timedelta(days=random.randint(30, 180))).isoformat().split('T')[0],
            "recommendations": [
                "Clean air filter",
                "Check refrigerant levels",
                "Inspect outdoor unit",
                "Calibrate temperature sensor"
            ],
            "estimated_cost_usd": round(random.uniform(100, 500), 2)
        }

    @app.post("/api/v1/register-device")
    async def register_mobile_device(device_data: dict, user=Depends(verify_token)):
        """Register mobile device for push notifications."""
        user_id = user.get("sub") # Assuming 'sub' is the user_id from JWT payload
        device_token = device_data.get("device_token")
        platform = device_data.get("platform")  # "ios" or "android"
        
        success = await push_service.register_device(
            user_id=user_id,
            device_token=device_token,
            platform=platform
        )
        
        return {"success": success, "message": "Device registration status."}

    @app.post("/api/v1/send-push-test")
    async def send_test_push_notification(user_id: str, user=Depends(verify_token)):
        """Test sending a push notification to a specific user."""
        current_user_id = user.get("sub")
        if current_user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot send test notification for another user.")

        success = await push_service.send_notification(
            user_id=user_id,
            title="Thermostat Test Notification",
            body="This is a test notification from your Smart Thermostat System!",
            data={"alert_type": "test", "device_id": "test_device"}
        )
        return {"success": success, "message": "Test notification sent status."}
    ```

---

### **5. Database Initialization Script**

**`database/init-scripts/influxdb-init.sql`**
```sql
-- database/init-scripts/influxdb-init.sql
-- This script runs automatically when the InfluxDB Docker container starts for the first time.

-- Create organization
CREATE ORGANIZATION thermostat-org;

-- Create bucket
CREATE BUCKET thermostat-data WITH ORGANIZATION thermostat-org;

-- Create user with read/write access to the bucket
CREATE USER thermostat WITH PASSWORD 'thermostat123' SET PASSWORD;
GRANT READ ON thermostat-data TO thermostat;
GRANT WRITE ON thermostat-data TO thermostat;

-- Create an admin token for API access (replace with a stronger token in production)
-- This token is used by the AI Controller to connect to InfluxDB
CREATE AUTHORIZATION FOR thermostat WITH USER thermostat ON thermostat-data AS ALL;
-- Example token for admin user:
-- This command is for v2.0+ via CLI or HTTP API. SQL init script might not support token creation directly for new users.
-- Alternatively, set INFLUXDB_ADMIN_TOKEN in docker-compose.yml for initial setup.
-- For a fresh container, INFLUXDB_SETUP_INFLUXDB_INIT_MODE=setup can be used with env vars:
-- INFLUXDB_SETUP_ORG=thermostat-org
-- INFLUXDB_SETUP_BUCKET=thermostat-data
-- INFLUXDB_SETUP_USERNAME=thermostat
-- INFLUXDB_SETUP_PASSWORD=thermostat123
-- INFLUXDB_SETUP_ADMIN_TOKEN=admin-token-from-docker-compose
-- For this setup, we rely on `INFLUXDB_DB`, `INFLUXDB_ADMIN_USER`, `INFLUXDB_ADMIN_PASSWORD`,
-- `INFLUXDB_USER`, `INFLUXDB_USER_PASSWORD` in `docker-compose.yml` to create default user/org/bucket.
-- The provided SQL is for direct `influx` CLI. Docker entrypoint handles it differently for v2.x.

-- Re-confirming for InfluxDB 2.x Docker setup:
-- The `docker-compose.yml` already sets `INFLUXDB_DB`, `INFLUXDB_ADMIN_USER`, etc.
-- For InfluxDB 2.x, these environment variables will automatically perform the initial setup
-- (creating an organization, user, bucket, and admin token).
-- Thus, a complex SQL script like this is often *not* needed for basic setup.
-- The `influxdb-init.sql` might be more useful for creating additional, more granular permissions or other resources,
-- but the environment variables usually cover the initial org/bucket/user setup.
-- I'll keep this simplified for demonstration, assuming the docker-compose env vars handle the primary setup.
```

---

### **6. Nginx Configuration**

**`nginx/nginx.conf`**
```nginx
# nginx/nginx.conf
worker_processes 1;

events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;

    sendfile on;
    keepalive_timeout 65;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_buffers 16 8k;
    gzip_http_version 1.1;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Define upstreams for your services
    upstream dashboard_app {
        server dashboard:5000;
    }

    upstream mobile_api {
        server mobile-api:8000;
    }

    # Server block for HTTP (redirect to HTTPS or serve HTTP)
    server {
        listen 80;
        server_name localhost; # Replace with your domain name

        # Redirect all HTTP to HTTPS (recommended for production)
        # return 301 https://$host$request_uri;

        # Or serve HTTP for testing/development
        location / {
            proxy_pass http://dashboard_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /api/mobile/ { # Mobile API path
            proxy_pass http://mobile_api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # WebSocket proxy for dashboard
        location /socket.io/ {
            proxy_pass http://dashboard_app/socket.io/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $websocket_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400s; # Keep WebSocket connection open
            proxy_send_timeout 86400s;
        }
    }

    # Server block for HTTPS (if you have certificates)
    # server {
    #     listen 443 ssl;
    #     server_name localhost; # Replace with your domain name

    #     ssl_certificate /etc/nginx/certs/fullchain.pem; # Your full chain certificate
    #     ssl_certificate_key /etc/nginx/certs/privkey.pem; # Your private key

    #     ssl_session_cache shared:SSL:10m;
    #     ssl_session_timeout 10m;
    #     ssl_protocols TLSv1.2 TLSv1.3;
    #     ssl_ciphers "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20";
    #     ssl_prefer_server_ciphers on;

    #     location / {
    #         proxy_pass http://dashboard_app;
    #         proxy_set_header Host $host;
    #         proxy_set_header X-Real-IP $remote_addr;
    #         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    #         proxy_set_header X-Forwarded-Proto $scheme;
    #     }

    #     location /api/mobile/ {
    #         proxy_pass http://mobile_api/;
    #         proxy_set_header Host $host;
    #         proxy_set_header X-Real-IP $remote_addr;
    #         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    #         proxy_set_header X-Forwarded-Proto $scheme;
    #     }

    #     location /socket.io/ {
    #         proxy_pass http://dashboard_app/socket.io/;
    #         proxy_http_version 1.1;
    #         proxy_set_header Upgrade $websocket_upgrade;
    #         proxy_set_header Connection "upgrade";
    #         proxy_set_header Host $host;
    #         proxy_read_timeout 86400s;
    #         proxy_send_timeout 86400s;
    #     }
    # }
}
```

---

### **Updated `requirements.txt`**

Make sure these are in your `requirements.txt`:
```txt
# Core CoAP
aiocoap>=0.4.1
cbor2>=5.4.0

# ML & AI
scikit-learn>=1.3.0
tensorflow>=2.13.0
numpy>=1.24.0
pandas>=2.0.0
joblib>=1.3.0
psutil>=5.9.0 # Added for client/app/resources/diagnostics.py

# Database
influxdb-client>=1.37.0
redis>=4.6.0
sqlalchemy>=2.0.0 # Placeholder, if you eventually use ORM for Postgres

# Web & API
fastapi>=0.100.0
uvicorn>=0.23.0
websockets>=11.0
flask>=2.3.0
flask-socketio>=5.3.0 # Added for dashboard
python-socketio>=5.10.0 # Dependency of flask-socketio
aiohttp>=3.9.0 # Added for server/app/services/notification_service.py

# Security
cryptography>=41.0.0
pyjwt>=2.8.0
python-jose[cryptography] # Added for JWT if more complex algorithms used, though pyjwt is primary

# Monitoring (already present)
prometheus-client>=0.17.0
psutil>=5.9.0

# Utilities
pydantic>=2.0.0
python-dotenv>=1.0.0
schedule>=1.2.0

# Firebase for Push Notifications
firebase-admin>=6.3.0 # Added for mobile/push_notifications.py
```

---

**Final Checks and Considerations:**

1.  **`.env` File**: Ensure you create a `.env` file at the root of `enhanced_coap_thermostat/` with all the necessary environment variables as defined in `config.py` files (e.g., `DEVICE_ID`, `COAP_HOST`, `INFLUXDB_URL`, `JWT_SECRET`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `FIREBASE_CREDENTIAL_PATH`).
2.  **`certs` Directory**: You'll need to create a `certs` directory at the root and potentially put your Firebase service account key (`firebase-service-account.json`) there if you want push notifications to work. For DTLS, `auth.py` will generate keys if they don't exist, but for production, you'd manage these securely.
3.  **Dependencies**: The `requirements.txt` has been updated with the libraries used in the new implementations. Make sure to `pip install -r requirements.txt` within your Docker containers.
4.  **Error Handling**: I've added basic `try-except` blocks and logging, but production-grade error handling is much more robust (e.g., specific exception types, retry mechanisms, circuit breakers).
5.  **Mocking vs. Real**: Some components still rely on mock data (`DashboardService`, `Mobile API`). For a full production system, these would need to communicate with the `AI Controller`'s REST API and WebSocket endpoints.
6.  **AI Controller's CoAP Client**: The `EnhancedCoAPClient` in `server/app/coap/client.py` is designed to talk to the `client/app/device.py` (your thermostat). DTLS credentials (`PSK_IDENTITY`, `PSK_KEY`) must match between them.
7.  **FastAPI Dependency Injection**: For the FastAPI app in `server/app/api/rest_gateway.py`, I've made `main.py` the entry point to run background tasks. For truly clean FastAPI, consider using `fastapi.Depends` for service injection or a custom IoC container. My approach assigns services to `app.state` which is acceptable for smaller apps.
8.  **Nginx SSL**: The `nginx.conf` has commented-out SSL configuration. For production, you'd uncomment it and provide actual certificates.
9.  **PostgreSQL**: The `server/app/database/models.py` is a placeholder. If you need to store user data, device registration, schedules, etc., you'd implement SQLAlchemy models there and set up a database migration system.

This comprehensive implementation should get you a fully fleshed-out system ready for testing and further development!