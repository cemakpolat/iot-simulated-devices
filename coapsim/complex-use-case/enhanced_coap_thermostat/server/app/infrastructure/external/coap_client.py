# app/infrastructure/external/coap_client.py
"""Enhanced CoAP client for device communication."""

import asyncio
import aiocoap
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from aiocoap.message import Message
from aiocoap import Code, Context, GET, PUT, POST

from ...core.config import get_settings
from ...core.exceptions import DeviceError, DeviceOfflineError, ConfigurationError

logger = logging.getLogger(__name__)
settings = get_settings()


class EnhancedCoAPClient:
    """Enhanced CoAP client with better error handling and connection management."""
    
    def __init__(self):
        self.coap_context = None
        self.config = settings.coap_config
        self.device_url_base = self._build_device_url()
        self._initialized = False
        
        logger.info(f"EnhancedCoAPClient initialized. Target: {self.device_url_base}")
    
    def _build_device_url(self) -> str:
        """Build the base device URL based on configuration."""
        if self.config["enable_dtls"]:
            return f"coaps://{self.config['host']}:{self.config['secure_port']}"
        else:
            return f"coap://{self.config['host']}:{self.config['port']}"
    
    async def initialize(self):
        """Initialize the CoAP client."""
        try:
            await self._get_coap_context()
            self._initialized = True
            logger.info("CoAP client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize CoAP client: {e}")
            raise ConfigurationError(f"CoAP client initialization failed: {str(e)}")
    
    async def _get_coap_context(self):
        """Create or return the CoAP client context."""
        if self.coap_context is None:
            try:
                if self.config["enable_dtls"]:
                    identity = self.config["psk_identity"].encode('utf-8')
                    key = self.config["psk_key"].encode('utf-8')
                    
                    self.coap_context = await Context.create_client_context()
                    self.coap_context.client_credentials.load_from_dict({
                        f"coaps://{self.config['host']}/*": {
                            "dtls": {
                                "psk": key,
                                "client-identity": identity,
                            }
                        }
                    })
                    logger.info("CoAP client context created with DTLS security")
                else:
                    self.coap_context = await Context.create_client_context()
                    logger.info("CoAP client context created (no DTLS)")
            except Exception as e:
                logger.error(f"Failed to create CoAP context: {e}")
                raise
        
        return self.coap_context
    
    async def _send_request(self, method: Code, path: str, payload: bytes = b'', 
                           content_format: int = 0, timeout: float = 10.0) -> Optional[Message]:
        """Send a CoAP request with enhanced error handling."""
        if not self._initialized:
            raise DeviceError("CoAP client not initialized")
        
        context = await self._get_coap_context()
        request_url = f"{self.device_url_base}/{path}"
        
        request = Message(code=method, uri=request_url, payload=payload)
        if payload:
            request.content_format = content_format
        
        try:
            logger.debug(f"Sending CoAP {method.name} request to {request_url}")
            response = await asyncio.wait_for(
                context.request(request).response,
                timeout=timeout
            )
            logger.debug(f"Received CoAP response: {response.code}")
            return response
            
        except asyncio.TimeoutError:
            logger.warning(f"CoAP request to {request_url} timed out after {timeout}s")
            raise DeviceOfflineError(f"Device timeout after {timeout}s", {
                "url": request_url,
                "timeout": timeout
            })
        except Exception as e:
            logger.error(f"CoAP request to {request_url} failed: {e}")
            raise DeviceError(f"CoAP communication failed: {str(e)}", {
                "url": request_url,
                "method": method.name
            })
    
    async def get_all_sensor_data(self) -> Optional[Dict[str, Any]]:
        """Retrieve all sensor data from the device."""
        try:
            response = await self._send_request(GET, "sensor/data")
            if response and response.code.is_successful():
                data = json.loads(response.payload.decode('utf-8'))
                logger.debug(f"Retrieved sensor data: {data}")
                return data
            else:
                logger.warning(f"Failed to get sensor data. Response: {response.code.name if response else 'No response'}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode sensor data JSON: {e}")
            raise DeviceError("Invalid sensor data format received")
        except Exception as e:
            logger.error(f"Error getting sensor data: {e}")
            return None
    
    async def get_device_status(self) -> Optional[Dict[str, Any]]:
        """Retrieve device status information."""
        try:
            response = await self._send_request(GET, "device/status")
            if response and response.code.is_successful():
                data = json.loads(response.payload.decode('utf-8'))
                logger.debug(f"Retrieved device status: {data}")
                return data
            else:
                logger.warning(f"Failed to get device status. Response: {response.code.name if response else 'No response'}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode device status JSON: {e}")
            raise DeviceError("Invalid device status format received")
        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            return None
    
    async def send_control_command(self, command: Dict[str, Any]) -> bool:
        """Send a control command to the device."""
        try:
            payload = json.dumps(command).encode('utf-8')
            response = await self._send_request(POST, "control", payload, content_format=50)
            
            if response and response.code.is_successful():
                logger.info(f"Control command sent successfully: {command}")
                return True
            else:
                logger.error(f"Failed to send control command: {command}. Response: {response.code.name if response else 'No response'}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending control command {command}: {e}")
            raise DeviceError(f"Failed to send command: {str(e)}")
    
    async def get_configuration(self) -> Optional[Dict[str, Any]]:
        """Retrieve device configuration."""
        try:
            response = await self._send_request(GET, "config")
            if response and response.code.is_successful():
                return json.loads(response.payload.decode('utf-8'))
            return None
        except Exception as e:
            logger.error(f"Error getting device configuration: {e}")
            return None
    
    async def get_diagnostics(self) -> Optional[Dict[str, Any]]:
        """Retrieve device diagnostics."""
        try:
            response = await self._send_request(GET, "diagnostics")
            if response and response.code.is_successful():
                return json.loads(response.payload.decode('utf-8'))
            return None
        except Exception as e:
            logger.error(f"Error getting device diagnostics: {e}")
            return None
    
    async def ping_device(self) -> bool:
        """Ping the device to check connectivity."""
        try:
            response = await self._send_request(GET, "ping", timeout=5.0)
            return response is not None and response.code.is_successful()
        except Exception:
            return False
    
    async def close(self):
        """Close the CoAP client and cleanup resources."""
        if self.coap_context:
            try:
                await self.coap_context.shutdown()
                self.coap_context = None
                self._initialized = False
                logger.info("CoAP client closed successfully")
            except Exception as e:
                logger.error(f"Error closing CoAP client: {e}")


