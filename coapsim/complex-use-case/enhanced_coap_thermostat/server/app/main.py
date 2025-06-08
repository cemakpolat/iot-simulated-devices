import asyncio
import logging
import os
from datetime import datetime, timedelta

# Setup basic logging for the server process (before importing other modules)
# This will log to console and potentially to a file defined by basicConfig.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import configuration from this server's app folder
from config import ServerConfig

# Import core components and services
from database.influxdb_client import InfluxDBClient
from coap.client import EnhancedCoAPClient

# Import ML Models (will be fully implemented in Phase 3/4)
from models.lstm_predictor import LSTMTemperaturePredictor
from models.anomaly_detector import AnomalyDetector
from models.energy_optimizer import EnergyOptimizer
from models.ensemble_model import EnsemblePredictor

# Import Services (will be fully implemented in Phase 3/4)
from services.thermostat_service import ThermostatControlService
from services.prediction_service import PredictionService
from services.maintenance_service import MaintenanceService
from services.notification_service import NotificationService 


# --- NEW: Import WebSocket Manager ---
from api.websocket_handler import WebSocketManager


# --- NEW: Import FastAPI app from rest_gateway ---
from api.rest_gateway import app as fastapi_app 

from dotenv import load_dotenv
load_dotenv()

# Load configuration
config = ServerConfig()
# Set global log level based on config
logging.getLogger().setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
logger.info(f"Server starting with log level: {config.LOG_LEVEL.upper()}")


# --- Initialize Core Dependencies (Singletons) ---
# These instances will be passed to other services as dependencies.
influx_client = InfluxDBClient()
coap_client = EnhancedCoAPClient(config)
notification_service = NotificationService(config) # Pass config for email/webhook settings


# --- Initialize ML Models ---
# Models are initialized first, then passed to services that use them.
lstm_predictor = LSTMTemperaturePredictor()
anomaly_detector = AnomalyDetector() 
energy_optimizer = EnergyOptimizer()
# Ensemble model combines the decisions of individual models
ensemble_predictor = EnsemblePredictor(
    lstm_model=lstm_predictor,
    anomaly_detector=anomaly_detector,
    energy_optimizer=energy_optimizer 
)


# --- Initialize Services ---
# Services take the core dependencies and other services as arguments.
# This pattern is called Dependency Injection.
prediction_service = PredictionService(
    db_client=influx_client, 
    lstm_predictor=lstm_predictor, 
    anomaly_detector=anomaly_detector
)
maintenance_service = MaintenanceService(
    db_client=influx_client, 
    notification_service=notification_service
)
thermostat_service = ThermostatControlService(
    ensemble_model_instance=ensemble_predictor,
    db_client=influx_client,
    coap_client=coap_client,
    notification_service=notification_service,
    prediction_service=prediction_service,  # Pass the prediction service instance
    maintenance_service=maintenance_service  # Pass the maintenance service instance
)

# --- NEW: Initialize WebSocket Manager ---
websocket_manager = WebSocketManager(thermostat_service, config)

notification_service.set_websocket_manager(websocket_manager)


# --- Main Control Loop for the AI Controller ---
async def control_loop():
    """
    This asynchronous loop continuously runs the core logic of the AI Controller:
    1. Fetches sensor data from the device.
    2. Stores data in the database.
    3. Triggers ML models for predictions and decisions.
    4. Sends control commands back to the device.
    5. Checks for maintenance needs and alerts.
    6. Periodically retrains ML models.
    """
    logger.info("Starting AI Controller background control loop...")
    
    # Attempt to pre-train models on startup.
    # This ensures models are ready if historical data exists.
    logger.info("Attempting initial ML model training...")
    await prediction_service.retrain_models()

    while True:
        try:
            # 1. Execute the main thermostat control cycle
            # This involves fetching data, making AI decisions, and sending commands.
            await thermostat_service.process_control_cycle()

            # 2. Check for predictive maintenance needs after processing current device status
            # The `process_control_cycle` within `thermostat_service` already fetches device status
            # and merges it into sensor_data. We can retrieve the last processed data.
            last_device_data = thermostat_service.get_last_processed_data()
            if last_device_data:
                await maintenance_service.check_maintenance_needs(last_device_data)
            else:
                logger.warning("No recent device data available for maintenance check.")

            # 3. Periodically retrain ML models
            # Check if retraining interval has passed since last training
            if (prediction_service.last_training is None or 
                (datetime.now() - prediction_service.last_training).total_seconds() / 3600 >= config.ML_RETRAIN_INTERVAL_HOURS):
                logger.info(f"Retraining interval reached ({config.ML_RETRAIN_INTERVAL_HOURS} hours). Initiating model retraining.")
                await prediction_service.retrain_models()

            # Wait for the next poll interval
            await asyncio.sleep(config.POLL_INTERVAL)
            
        except asyncio.CancelledError:
            logger.info("Control loop cancelled (e.g., due to shutdown signal).")
            break # Exit the loop cleanly
        except Exception as e:
            logger.error(f"An unexpected error occurred in the control loop: {e}", exc_info=True)
            # Log the error and wait for a longer period before retrying to prevent rapid error loops
            await asyncio.sleep(config.POLL_INTERVAL * 5) 

# --- FastAPI Lifespan Events ---
@fastapi_app.on_event("startup")
async def startup_event():
    """
    FastAPI startup event. This is where we start background tasks
    and inject instantiated services into the FastAPI app state.
    """
    logger.info("FastAPI startup event triggered. Initializing services and background tasks.")
    
    # Inject service instances into FastAPI app state
    fastapi_app.state.thermostat_service = thermostat_service
    fastapi_app.state.prediction_service = prediction_service
    fastapi_app.state.maintenance_service = maintenance_service
    fastapi_app.state.influx_client = influx_client
    fastapi_app.state.coap_client = coap_client
    fastapi_app.state.notification_service = notification_service # Also inject notification service

    # Start background tasks
    fastapi_app.state.control_loop_task = asyncio.create_task(control_loop_task_function())
    fastapi_app.state.websocket_server_task = asyncio.create_task(websocket_manager.start_server(host="0.0.0.0", port=8092))
    
    logger.info("Background control loop and WebSocket server tasks started.")

@fastapi_app.on_event("shutdown")
async def shutdown_event():
    """
    FastAPI shutdown event. This is where we gracefully stop background tasks
    and clean up resources.
    """
    logger.info("FastAPI shutdown event triggered. Initiating graceful shutdown.")
    
    # Cancel and await background tasks
    if hasattr(fastapi_app.state, 'control_loop_task') and fastapi_app.state.control_loop_task:
        fastapi_app.state.control_loop_task.cancel()
        try:
            await fastapi_app.state.control_loop_task
        except asyncio.CancelledError:
            pass
    if hasattr(fastapi_app.state, 'websocket_server_task') and fastapi_app.state.websocket_server_task:
        fastapi_app.state.websocket_server_task.cancel()
        try:
            await fastapi_app.state.websocket_server_task
        except asyncio.CancelledError:
            pass
    
    # Perform clean shutdown of services
    await websocket_manager.stop()
    await coap_client.shutdown()
    # If InfluxDB client needs explicit closing: influx_client.client.close()
    
    logger.info("AI Controller application shut down completely.")

# Expose the FastAPI app instance for Uvicorn to load.
app = fastapi_app 



async def main():
    """Main entry point function for the AI Controller application."""
    logger.info("Smart Thermostat AI Controller application is starting...")

    # Start the core control loop as a background asyncio task.
    control_loop_task = asyncio.create_task(control_loop())
    
    # --- NEW: Start the WebSocket server as a background asyncio task ---
    # The WebSocket server listens on a different port (8001) for dashboard connections.
    websocket_server_task = asyncio.create_task(websocket_manager.start_server(host="0.0.0.0", port=8092))

    # Keep the main event loop running indefinitely, awaiting all tasks.
    try:
        await asyncio.gather(control_loop_task, websocket_server_task)
    except asyncio.CancelledError:
        logger.info("AI Controller application main tasks cancelled.")
    except Exception as e:
        logger.critical(f"Unhandled error in AI Controller application main execution: {e}", exc_info=True)
    finally:
        logger.info("Initiating graceful shutdown of AI Controller components...")
        # Ensure all tasks are cancelled and awaited
        control_loop_task.cancel()
        websocket_server_task.cancel()
        try:
            await control_loop_task
            await websocket_server_task
        except asyncio.CancelledError:
            pass # Expected
        
        await websocket_manager.stop() # Stop WebSocket manager cleanly
        await coap_client.shutdown() # Shut down CoAP client connections
        influx_client.client.close() # If InfluxDB client needs explicit closing
        logger.info("AI Controller application shut down completely.")

# Standard Python entry point for running the asynchronous main function.
if __name__ == "__main__":
    # Load environment variables from .env file if `python-dotenv` is installed.
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        logger.info("Environment variables loaded from .env file.")
    except ImportError:
        logger.warning("python-dotenv not installed. Environment variables must be set manually for ServerConfig.")
    
    # Run the main asynchronous function
    asyncio.run(main())