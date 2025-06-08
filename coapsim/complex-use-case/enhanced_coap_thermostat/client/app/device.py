# client/app/device.py
import asyncio
import aiocoap
import aiocoap.resource as resource
import logging
import time

from config import DeviceConfig
from security.auth import SecurityManager
from security.dtls_handler import DTLSSecurityHandler
from resources.sensor_data import SensorDataResource
from resources.device_status import DeviceStatusResource
from resources.control import EnhancedControlResource
# from .resources.configuration import ConfigurationResource # Will be added in Phase 3
# from .resources.diagnostics import DiagnosticsResource   # Will be added in Phase 3
from utils.logger import setup_logger

logger = setup_logger(__name__)

class CoAPDevice:
    """Represents the smart thermostat as a CoAP device."""
    def __init__(self, config: DeviceConfig):
        self.config = config
        self.coap_context = None
        self.device_start_time = time.time()
        
        # Initialize resources that hold state
        self.control_resource = EnhancedControlResource() 

        # Initialize security components
        self.security_manager = SecurityManager(self.config)
        self.dtls_handler = DTLSSecurityHandler(self.config, self.security_manager)

    async def start(self):
        """Starts the CoAP server for the device."""
        root = resource.Site()

        # Register core resources
       # root.add_resource(['.well-known', 'core'], resource.WkVsResource(root))
        root.add_resource(['sensor', 'data'], SensorDataResource(self.config.DEVICE_ID))
        root.add_resource(['device', 'status'], DeviceStatusResource(self.config.DEVICE_ID))
        root.add_resource(['control'], self.control_resource) 
        
        # Resources to be added in Phase 3
        # root.add_resource(['config'], ConfigurationResource(self.config))
        # root.add_resource(['diagnostics'], DiagnosticsResource(self.config.DEVICE_ID, self.device_start_time))
        self.config.ENABLE_DTLS = False
        if self.config.ENABLE_DTLS:
            logger.info(f"Starting CoAP server with DTLS on {self.config.HOST}:{self.config.SECURE_PORT}...")
            
            # Create server context without DTLS credentials first
            self.coap_context = await aiocoap.Context.create_server_context(
                root, 
                bind=(self.config.HOST, self.config.SECURE_PORT)
            )
            
            # Apply DTLS credentials to the context
            self.dtls_handler.apply_credentials_to_context(self.coap_context)
            
            logger.info(f"CoAP-DTLS server listening securely on {self.config.HOST}:{self.config.SECURE_PORT}")
        else:
            logger.info(f"Starting CoAP server WITHOUT DTLS on {self.config.HOST}:{self.config.PORT}...")
            self.coap_context = await aiocoap.Context.create_server_context(
                root, 
                bind=(self.config.HOST, self.config.PORT)
            )
            logger.info(f"CoAP server listening on {self.config.HOST}:{self.config.PORT}")

        logger.info(f"CoAP Device '{self.config.DEVICE_ID}' started successfully.")

        # Keep the server running indefinitely
        try:
            while True:
                await asyncio.sleep(3600) # Sleep for a long time to keep the event loop running
        except asyncio.CancelledError:
            logger.info("CoAP device main loop cancelled.")
        except Exception as e:
            logger.error(f"Error in CoAP device main loop: {e}", exc_info=True)
        finally:
            if self.coap_context:
                await self.coap_context.shutdown()
                logger.info("CoAP context shut down.")

    async def stop(self):
        """Stops the CoAP server gracefully."""
        if self.coap_context:
            await self.coap_context.shutdown()
            logger.info("CoAP device explicitly stopped.")