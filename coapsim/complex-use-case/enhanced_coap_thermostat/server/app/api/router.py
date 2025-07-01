# # server/app/api/routes.py
# """
# Centralized route registration for the FastAPI application.
# This module imports all route modules and provides a single function
# to register all routes with the FastAPI app.
# """
# from fastapi import FastAPI

# from .routes import auth, devices, notifications, monitoring

# def register_routes(app: FastAPI) -> None:
#     """
#     Register all API routes with the FastAPI application.
    
#     Args:
#         app: The FastAPI application instance
#     """
#     # Authentication routes
#     app.include_router(auth.router)

#     app.include_router(devices.router)
#     app.include_router(monitoring.router)
#     app.include_router(notifications.router)
    
    

# def get_route_summary() -> dict:
#     """
#     Get a summary of all registered routes for debugging/documentation.
    
#     Returns:
#         dict: Summary of routes organized by prefix
#     """
#     return {
#         "auth": {
#             "prefix": "/auth",
#             "endpoints": [
#                 "POST /auth/login - Authenticate user and get JWT token",
#                 "POST /auth/register - Register new user account", 
#                 "GET /auth/me - Get current user information",
#                 "POST /auth/logout - Logout current user"
#             ]
#         },
#         "devices": {
#             "prefix": "/devices",
#             "endpoints": [
#                 "GET /devices/status/{device_id} - Get device status",
#                 "POST /devices/control/{device_id} - Send control command",
#                 "GET /devices/predictions/{device_id} - Get temperature predictions",
#                 "GET /devices/maintenance/{device_id} - Get maintenance status"
#             ]
#         },
       
#         "fcm": {
#             "prefix": "/fcm",
#             "endpoints": [
#                 "POST /fcm/register - Register FCM token",
#                 "POST /fcm/unregister - Unregister FCM token",
#                 "GET /fcm/health - FCM service health check",
#                 "POST /fcm/validate-tokens - Validate FCM tokens",
#                 "POST /fcm/test-notification - Send test notification",
#                 "GET /fcm/tokens - Get registered tokens",
#                 "POST /fcm/cleanup - Clean up old tokens"
#             ]
#         },
      
#     }

# server/app/api/router.py - Fixed router registration

"""
Centralized route registration for the FastAPI application.
"""
from fastapi import FastAPI

import logging

logger = logging.getLogger(__name__)

def register_routes(app: FastAPI) -> None:
    """
    Register all API routes with the FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """

    
    # Import and register auth routes
    try:
        from .routes.auth import router as auth_router
        app.include_router(auth_router)
        logger.info("✅ Auth routes registered successfully")
        
        # Log all registered auth routes
        for route in auth_router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                for method in route.methods:
                    logger.info(f"   {method} {auth_router.prefix}{route.path}")
                    
    except ImportError as e:
        logger.error(f"❌ Failed to import auth router: {e}")

    
    try:
        from .routes.devices import router as devices_router
        app.include_router(devices_router)
        logger.info("✅ Device routes registered")
    except ImportError:
        logger.warning("⚠️ Device routes not found - skipping")
    
    try:
        from .routes.monitoring import router as monitoring_router
        app.include_router(monitoring_router)
        logger.info("✅ Monitoring routes registered")
    except ImportError:
        logger.warning("⚠️ Monitoring routes not found - skipping")
    
    try:
        from .routes.notifications import router as notifications_router
        app.include_router(notifications_router)
        logger.info("✅ Notification routes registered")
    except ImportError:
        logger.warning("⚠️ Notification routes not found - skipping")

