# client/app/main.py
import asyncio
import logging
import os

from config import DeviceConfig
from device import CoAPDevice
from utils.logger import setup_logger

# Setup global logger for the main module
logger = setup_logger("client_main", level=logging.INFO)

async def main():
    """Main function to start the CoAP thermostat device."""
    # Load configuration
    config = DeviceConfig()
    
    logger.info(f"Starting Smart Thermostat Device: {config.DEVICE_ID}")
    logger.info(f"Device Type: {config.DEVICE_TYPE}, Firmware Version: {config.FIRMWARE_VERSION}")
    logger.info(f"DTLS Enabled: {config.ENABLE_DTLS}")
    
    device = CoAPDevice(config)
    
    try:
        await device.start()
    except KeyboardInterrupt:
        logger.info("Device shutdown initiated by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"An unhandled error occurred during device operation: {e}", exc_info=True)
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
        logger.warning("python-dotenv not installed. Environment variables must be set manually for DeviceConfig.")
    
    asyncio.run(main())