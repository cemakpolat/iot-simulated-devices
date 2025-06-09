# server/app/coap/client.py
# server/app/coap/client.py
import asyncio
import aiocoap
from aiocoap.message import Message
from aiocoap import Code, Context, GET, PUT, POST
import json
import logging
import time

from config import ServerConfig

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
        logger.info(f"EnhancedCoAPClient initialized. Target Device URL Base: {self.device_url_base}")

    async def _get_coap_context(self):
        """Lazily creates or returns the CoAP client context with DTLS if enabled."""
        if self.coap_context is None:
            # Create context with security if needed
            if self.config.ENABLE_DTLS_SERVER_CLIENT:
                identity = self.config.COAP_PSK_IDENTITY.encode('utf-8')
                key = self.config.COAP_PSK_KEY.encode('utf-8')
                
                # Create security context

                self.coap_context = await Context.create_client_context()
                self.coap_context.client_credentials.load_from_dict(
                    {
                        "coaps://%s/*" % self.config.COAP_DEVICE_HOST: {
                            "dtls": {
                                "psk": key,
                                "client-identity": identity,
                            }
                        }
                    }
                )

                logger.info("CoAP client context created with DTLS security")
            else:
                self.coap_context = await Context.create_client_context()
                logger.info("CoAP client context created (no DTLS)")
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
         #   response = await context.request(request).response
            response = await asyncio.wait_for(
                context.request(request).response,
                timeout=5.0
            )
            logger.debug(f"Received CoAP response from {request_url}: {response.code}")
            return response
        except asyncio.TimeoutError:
            logger.warning(f"CoAP request to {request_url} timed out")
            return None
        except Exception as e:
            logger.error(f"CoAP request to {request_url} failed: {e}", exc_info=True)
            return None


    async def get_all_sensor_data(self) -> dict:
        """Retrieves all sensor data from the thermostat device (`/sensor/data` resource)."""
        response = await self._send_request(GET, "sensor/data")
        if response and response.code.is_successful():
            try:
                data = json.loads(response.payload.decode('utf-8'))
                logger.debug(f"Successfully retrieved sensor data: {data}")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode sensor data JSON from response: {e}")
                return None
        logger.warning(f"Failed to get sensor data. CoAP Response: {response.code.name if response else 'No response'}")
        return None

    async def get_device_status(self) -> dict:
        """Retrieves device status information from the thermostat device (`/device/status` resource)."""
        response = await self._send_request(GET, "device/status")
        if response and response.code.is_successful():
            try:
                status_data = json.loads(response.payload.decode('utf-8'))
                logger.debug(f"Successfully retrieved device status: {status_data}")
                return status_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode device status JSON from response: {e}")
                return None
        logger.warning(f"Failed to get device status. CoAP Response: {response.code.name if response else 'No response'}")
        return None

    async def send_control_command(self, command: dict) -> bool:
        """Sends a control command to the thermostat device (`/control` resource)."""
        payload = json.dumps(command).encode('utf-8')
        response = await self._send_request(POST, "control", payload, content_format=50) # Content-Format 50 is application/json
        if response and response.code.is_successful():
            logger.info(f"Control command '{command}' sent successfully. Device response: {response.payload.decode()}")
            return True
        logger.error(f"Failed to send control command '{command}'. CoAP Response: {response.code.name if response else 'No response'}")
        return False
    
    # Other CoAP interactions (e.g., /config, /diagnostics) will be added in later phases

    async def shutdown(self):
        """Shuts down the CoAP client context gracefully."""
        if self.coap_context:
            await self.coap_context.shutdown()
            self.coap_context = None
            logger.info("CoAP client context shut down.")