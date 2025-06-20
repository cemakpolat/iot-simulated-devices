# app/api/v1/router.py
from fastapi import APIRouter
from . import auth, devices, predictions, maintenance, notifications, monitoring

api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(auth.router, tags=["authentication"])
api_router.include_router(devices.router, tags=["devices"])
api_router.include_router(predictions.router, tags=["predictions"])
api_router.include_router(maintenance.router, tags=["maintenance"])
api_router.include_router(notifications.router, tags=["notifications"])
api_router.include_router(monitoring.router, tags=["monitoring"])

