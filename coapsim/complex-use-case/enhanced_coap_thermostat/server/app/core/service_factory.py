# server/app/core/service_factory.py
import logging
import asyncio

from ..config import ServerConfig
from ..database.influxdb_client import InfluxDBClient
from ..database.postgres_client import PostgreSQLClient
from ..database.redis_client import RedisClient
from ..coap.client import EnhancedCoAPClient
from ..services.notification_service import NotificationService
from ..services.thermostat_service import ThermostatControlService
from ..services.prediction_service import PredictionService
from ..services.maintenance_service import MaintenanceService
from ..models.lstm_predictor import LSTMTemperaturePredictor
from ..models.anomaly_detector import AnomalyDetector
from ..models.energy_optimizer import EnergyOptimizer
from ..models.ensemble_model import EnsemblePredictor
from ..api.websocket_handler import WebSocketManager

logger = logging.getLogger(__name__)

class ServiceFactory:
    """Factory class for creating and managing service instances."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self._initialized = False
        
        # Core clients
        self.influx_client = None
        self.postgres_client = None
        self.redis_client = None
        self.coap_client = None
        
        # ML Models
        self.lstm_predictor = None
        self.anomaly_detector = None
        self.energy_optimizer = None
        self.ensemble_predictor = None
        
        # Services
        self.notification_service = None
        self.prediction_service = None
        self.maintenance_service = None
        self.thermostat_service = None
        self.websocket_manager = None
    
    async def initialize(self) -> None:
        """Initialize all services and their dependencies."""
        if self._initialized:
            logger.warning("ServiceFactory already initialized")
            return
        
        logger.info("Initializing ServiceFactory...")
        
        # Initialize core clients
        await self._initialize_clients()
        
        # Initialize ML models
        self._initialize_ml_models()
        
        # Initialize services
        await self._initialize_services()
        
        self._initialized = True
        logger.info("ServiceFactory initialization completed")
    
    async def _initialize_clients(self) -> None:
        """Initialize database and communication clients."""
        logger.info("Initializing core clients...")
        
        self.influx_client = InfluxDBClient()
        
        self.postgres_client = PostgreSQLClient(self.config.DATABASE_URL)
        
        if self.postgres_client.engine is None or self.postgres_client.SessionLocal is None:
            logger.error("Failed to initialize PostgreSQL client")
            raise RuntimeError("PostgreSQL client initialization failed")
        else:
            logger.info("PostgreSQL client initialized successfully")
        
        
        self.redis_client = RedisClient(self.config.REDIS_URL)
        # Actually connect to Redis
        redis_connected = await self.redis_client.connect()
        if redis_connected:
            logger.info("Redis client connected successfully")
        else:
            logger.warning("Redis client failed to connect - caching will be disabled")
        
        
        self.coap_client = EnhancedCoAPClient(self.config)
        
        logger.info("Core clients initialized")
    
    def _initialize_ml_models(self) -> None:
        """Initialize ML models."""
        logger.info("Initializing ML models...")
        
        self.lstm_predictor = LSTMTemperaturePredictor()
        self.anomaly_detector = AnomalyDetector()
        self.energy_optimizer = EnergyOptimizer()
        
        # Ensemble model combines individual models
        self.ensemble_predictor = EnsemblePredictor(
            lstm_model=self.lstm_predictor,
            anomaly_detector=self.anomaly_detector,
            energy_optimizer=self.energy_optimizer
        )
        
        logger.info("ML models initialized")
    
    async def _initialize_services(self) -> None:
        """Initialize application services."""
        logger.info("Initializing application services...")
        
        # Notification service - now uses the refactored modular version
        # All notifiers (email, fcm, webhook, websocket) are initialized automatically
        self.notification_service = NotificationService(self.config)
        
        # Prediction service
        self.prediction_service = PredictionService(
            db_client=self.influx_client,
            lstm_predictor=self.lstm_predictor,
            anomaly_detector=self.anomaly_detector
        )
        
        # Maintenance service
        self.maintenance_service = MaintenanceService(
            db_client=self.influx_client,
            notification_service=self.notification_service
        )
        
        # Thermostat service (depends on other services)
        self.thermostat_service = ThermostatControlService(
            ensemble_model_instance=self.ensemble_predictor,
            db_client=self.influx_client,
            coap_client=self.coap_client,
            notification_service=self.notification_service,
            prediction_service=self.prediction_service,
            maintenance_service=self.maintenance_service,
            redis_client=self.redis_client
        )
        
        # WebSocket manager
        self.websocket_manager = WebSocketManager(self.thermostat_service, self.config)
        # Start WebSocket server
        asyncio.create_task(self.websocket_manager.start_server(host=self.config.WEBSOCKET_SERVER, port=self.config.WEBSOCKET_PORT))
        # Background task manager
        from ..core.background_tasks import BackgroundTaskManager
        self.background_task_manager = BackgroundTaskManager(
            config=self.config,
            thermostat_service=self.thermostat_service,
            prediction_service=self.prediction_service,
            maintenance_service=self.maintenance_service,
            websocket_manager=self.websocket_manager
        )
        
        # Set up cross-service dependencies
        # The refactored notification service can work with the WebSocket manager
        self.notification_service.set_websocket_manager(self.websocket_manager)
        
        logger.info("Application services initialized")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all services."""
        logger.info("Shutting down ServiceFactory...")
        
        if self.websocket_manager:
            await self.websocket_manager.stop()
        
        # Cleanup the notification service (new method in refactored version)
        if self.notification_service:
            await self.notification_service.cleanup()
        
        if self.coap_client:
            await self.coap_client.shutdown()
        
        if self.redis_client:
            await self.redis_client.close()

         # Close PostgreSQL connection (SQLAlchemy)
        if self.postgres_client:
            self.postgres_client.close()
            logger.info("PostgreSQL engine disposed")       
        
        if self.influx_client and hasattr(self.influx_client, 'client'):
            self.influx_client.client.close()
        
        logger.info("ServiceFactory shutdown completed")
    
    def get_all_services(self) -> dict:
        """Get all initialized services as a dictionary for app.state injection."""
        if not self._initialized:
            raise RuntimeError("ServiceFactory not initialized")
        
        return {
            'config': self.config,
            'influx_client': self.influx_client,
            'postgres_client': self.postgres_client,
            'redis_client': self.redis_client,
            'coap_client': self.coap_client,
            'notification_service': self.notification_service,
            'prediction_service': self.prediction_service,
            'maintenance_service': self.maintenance_service,
            'thermostat_service': self.thermostat_service,
            'websocket_manager': self.websocket_manager,
            'background_task_manager': self.background_task_manager,
        }