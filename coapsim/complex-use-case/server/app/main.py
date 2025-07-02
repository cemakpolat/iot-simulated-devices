# server/app/main.py
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from fastapi import Response

from .config import ServerConfig
from .core.service_factory import ServiceFactory
from .core.background_tasks import BackgroundTaskManager
from .api.auth.jqt_handler import set_jwt_global_config
from .api.router import register_routes


# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Smart Thermostat AI API", version="2.0.0")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific domains
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Register all API routes
    register_routes(app)
    
    return app

# Create FastAPI app
app = create_app()

# Global variables
service_factory: ServiceFactory = None
background_task_manager: BackgroundTaskManager = None

@app.get("/")
async def root():
    """Root endpoint with API information."""
    from .api.router import get_route_summary
    return {
        "message": "Smart Thermostat AI API",
        "version": "2.0.0",
        "status": "running",
        "documentation": "/docs",
        "routes": get_route_summary()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

@app.get("/metrics")
async def metrics():
    """Endpoint for Prometheus to scrape metrics."""
    return Response(generate_latest(), media_type="text/plain")

class ApplicationManager:
    """Manages the complete application lifecycle for both modes."""
    
    def __init__(self, config: ServerConfig = None):
        self.config = config or ServerConfig()
        self.service_factory: ServiceFactory = None
        self.background_task_manager: BackgroundTaskManager = None
    
    async def initialize(self, setup_fastapi_state: bool = False) -> None:
        """Initialize all services and dependencies."""
        logger.info("Initializing Smart Thermostat AI application...")
        
        # Set logging level
        logging.getLogger().setLevel(getattr(logging, self.config.LOG_LEVEL.upper(), logging.INFO))
        logger.info(f"Application starting with log level: {self.config.LOG_LEVEL.upper()}")
        
        # Initialize service factory (includes refactored notification service)
        self.service_factory = ServiceFactory(self.config)
        await self.service_factory.initialize()
        
        # Get background task manager from service factory
        self.background_task_manager = self.service_factory.background_task_manager
        
        # Setup FastAPI state if needed (for web API mode)
        if setup_fastapi_state:
            services = self.service_factory.get_all_services()
            for key, value in services.items():
                setattr(app.state, key, value)
            
            # Set JWT secret for API authentication
            set_jwt_global_config(self.config)
            
            logger.info("FastAPI state setup completed")
        
        logger.info("Application initialization completed successfully")
    
    async def start_background_tasks(self) -> None:
        """Start all background tasks."""
        if self.background_task_manager:
            await self.background_task_manager.start_all_tasks()
            logger.info("Background tasks started")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the application."""
        logger.info("Initiating application shutdown...")
        
        # Stop background tasks
        if self.background_task_manager:
            await self.background_task_manager.stop_all_tasks()
            logger.info("Background tasks stopped")
        
        # Shutdown services (includes notification service cleanup)
        if self.service_factory:
            await self.service_factory.shutdown()
            logger.info("Services shutdown completed")
        
        logger.info("Application shutdown completed")

# Global application manager
app_manager: ApplicationManager = None

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup event handler.
    
    Use this mode when you want:
    - Web API + Background tasks
    - Development with hot reload
    - Production web service
    """
    global app_manager
    
    logger.info("🌐 Starting FastAPI mode (Web API + Background Tasks)")
    
    try:
        # Initialize application with FastAPI state setup
        app_manager = ApplicationManager()
        await app_manager.initialize(setup_fastapi_state=True)
        
        # Start background tasks
        await app_manager.start_background_tasks()
        
        logger.info("🚀 FastAPI application ready - API and background tasks running")
        
    except Exception as e:
        logger.error(f"Failed to start FastAPI application: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI shutdown event handler."""
    global app_manager
    
    logger.info("🛑 FastAPI shutdown initiated")
    
    if app_manager:
        await app_manager.shutdown()
    
    logger.info("✅ FastAPI shutdown completed")

async def main():
    """
    Standalone mode entry point.
    
    Use this mode when you want:
    - Background tasks only (no web API)
    Run with: python -m app.main
    """
    logger.info("⚙️  Starting Standalone mode (Background Tasks Only)")
    
    app_manager = None
    
    try:
        # Initialize application without FastAPI state
        app_manager = ApplicationManager()
        await app_manager.initialize(setup_fastapi_state=False)
        
        # Start background tasks
        await app_manager.start_background_tasks()
        
        logger.info("🔄 Standalone application running - Background tasks active")
        logger.info("Press Ctrl+C to stop...")
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️  Shutdown signal received")
    except Exception as e:
        logger.critical(f"💥 Critical error in standalone mode: {e}", exc_info=True)
    finally:
        if app_manager:
            await app_manager.shutdown()
        logger.info("✅ Standalone mode shutdown completed")

if __name__ == "__main__":
    """
    Entry point for standalone execution.
    
    This allows you to run the application in different ways:
    1. uvicorn app.main:app           # FastAPI mode (recommended for production)
    2. python -m app.main             # Standalone mode (background tasks only)
    """
    try:
        logger.info("🎯 Starting Smart Thermostat AI in standalone mode")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Application interrupted by user")
    except Exception as e:
        logger.critical(f"💥 Failed to start application: {e}", exc_info=True)