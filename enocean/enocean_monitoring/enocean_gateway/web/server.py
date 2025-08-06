#!/usr/bin/env python3
"""
Web Server - Enterprise-grade Flask application factory for EnOcean Gateway.

This module provides a robust, production-ready web server implementation that:
- Serves a modern React/Vue.js SPA dashboard with proper routing support
- Exposes comprehensive REST APIs for device management and monitoring
- Implements security best practices and error handling
- Supports real-time monitoring and metrics collection
- Follows Flask application factory pattern for scalability

Architecture:
    ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
    │   Web Client    │───▶│   Flask Server   │───▶│  EnOcean Core   │
    │  (Dashboard)    │    │  (This Module)   │    │    System       │
    └─────────────────┘    └──────────────────┘    └─────────────────┘
                                     │
                                     ▼
                           ┌──────────────────┐
                           │   API Routes     │
                           │ • Device Mgmt    │
                           │ • Monitoring     │
                           │ • Discovery      │
                           └──────────────────┘
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

from flask import Flask, send_from_directory, request, jsonify, g
from flask_cors import CORS
from werkzeug.exceptions import NotFound, InternalServerError
from werkzeug.middleware.proxy_fix import ProxyFix

from .api_routes import create_api_routes
from .monitoring_routes import create_monitoring_routes
from ..device_manager import DeviceManager
from ..config.eep_profile_loader import EEPProfileLoader
from ..core.synchronizer import StateSynchronizer
from ..core.gateway import UnifiedEnOceanSystem
from ..utils import Logger

# Application constants
BASE_DIR = Path(__file__).parent.resolve()
STATIC_DIR = BASE_DIR / "static"
DEFAULT_STATIC_FILES = {"index.html", "app.js", "style.css", "favicon.ico"}

# Initialize logger
logger = Logger()


class WebServerConfig:
    """Configuration class for web server settings."""
    
    # Security settings
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'enocean-gateway-dev-key-change-in-production')
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Static file caching (seconds)
    STATIC_CACHE_TIMEOUT = int(os.environ.get('STATIC_CACHE_TIMEOUT', '3600'))
    
    # Request limits
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
    
    # Debug mode
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'


def _configure_security(app: Flask) -> None:
    """Configure security headers and middleware."""
    
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Only add HSTS in production
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    # Trust proxy headers if behind reverse proxy
    if os.environ.get('BEHIND_PROXY', 'False').lower() == 'true':
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


def _configure_error_handlers(app: Flask) -> None:
    """Configure comprehensive error handling."""
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors - serve SPA for client-side routing."""
        # For API endpoints, return JSON error
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'API endpoint not found',
                'path': request.path
            }), 404
        
        # For other routes, serve the SPA (client-side routing)
        try:
            return send_from_directory(app.static_folder, "index.html")
        except Exception as e:
            logger.error(f"Error serving SPA for 404: {e}")
            return jsonify({
                'success': False,
                'error': 'Static files not found',
                'message': 'Please ensure the web dashboard is properly built and deployed'
            }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 errors with proper logging."""
        logger.error(f"Internal server error: {error}")
        
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please check the server logs.'
        }), 500
    
    @app.errorhandler(413)
    def handle_request_too_large(error):
        """Handle request payload too large."""
        return jsonify({
            'success': False,
            'error': 'Request payload too large',
            'max_size': f"{WebServerConfig.MAX_CONTENT_LENGTH // 1024 // 1024}MB"
        }), 413


def _configure_request_logging(app: Flask) -> None:
    """Configure request logging for monitoring and debugging."""
    
    @app.before_request
    def before_request():
        """Log request start and setup request context."""
        g.start_time = time.time()
        
        # Log API requests (but not static file requests)
        if request.path.startswith('/api/'):
            logger.debug(f"API Request: {request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        """Log request completion and performance metrics."""
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            
            # Log slow requests
            if duration > 1.0:  # Log requests taking more than 1 second
                logger.warning(f"Slow request: {request.method} {request.path} took {duration:.2f}s")
            
            # Log API responses
            if request.path.startswith('/api/'):
                logger.debug(f"API Response: {response.status_code} in {duration:.3f}s")
        
        return response


def _validate_static_directory(static_dir: Path) -> bool:
    """Validate that static directory exists and contains required files."""
    if not static_dir.exists():
        logger.warning(f"Static directory not found: {static_dir}")
        return False
    
    # Check for index.html (required for SPA)
    if not (static_dir / "index.html").exists():
        logger.warning("index.html not found in static directory")
        return False
    
    logger.info(f"✅ Static directory validated: {static_dir}")
    return True


def _setup_static_file_caching(app: Flask) -> None:
    """Configure static file caching for better performance."""
    
    @app.route('/static/<path:filename>')
    def custom_static(filename):
        """Custom static file handler with proper caching headers."""
        response = send_from_directory(app.static_folder, filename)
        
        # Set cache headers based on file type
        if filename.endswith(('.js', '.css')):
            # Cache JS/CSS for longer periods
            response.cache_control.max_age = WebServerConfig.STATIC_CACHE_TIMEOUT
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg')):
            # Cache images for very long periods
            response.cache_control.max_age = WebServerConfig.STATIC_CACHE_TIMEOUT * 24  # 24 hours
        else:
            # Cache other files for shorter periods
            response.cache_control.max_age = WebServerConfig.STATIC_CACHE_TIMEOUT // 4
        
        return response


def create_web_app(
    device_manager: DeviceManager,
    enocean_system: UnifiedEnOceanSystem,
    synchronizer: StateSynchronizer,
    eep_loader: EEPProfileLoader,
    config: Optional[Dict[str, Any]] = None
) -> Flask:
    """
    Create and configure a production-ready Flask web application.
    
    This factory function creates a fully configured Flask application with:
    - Modern SPA support with client-side routing
    - Comprehensive REST API for device management
    - Real-time monitoring and metrics endpoints
    - Security headers and error handling
    - Request logging and performance monitoring
    - Static file optimization and caching
    
    Args:
        device_manager: Device management service instance
        enocean_system: Core EnOcean communication system
        synchronizer: State synchronization service
        eep_loader: EEP profile configuration loader
        config: Optional additional configuration dictionary
        
    Returns:
        Fully configured Flask application ready for deployment
        
    Raises:
        RuntimeError: If critical configuration is missing or invalid
        
    Example:
        ```python
        app = create_web_app(
            device_manager=dm,
            enocean_system=system,
            synchronizer=sync,
            eep_loader=loader
        )
        app.run(host='0.0.0.0', port=5003)
        ```
    """
    
    # Validate static directory
    if not _validate_static_directory(STATIC_DIR):
        logger.warning("Static directory validation failed - web dashboard may not work properly")
    
    # Create Flask application
    app = Flask(
        __name__, 
        static_folder=str(STATIC_DIR),
        static_url_path='/static'
    )
    
    # Apply configuration
    app.config.from_object(WebServerConfig)
    if config:
        app.config.update(config)
    
    # Configure security
    _configure_security(app)
    
    # Configure CORS for API endpoints
    CORS(app, resources={
        r"/api/*": {
            "origins": WebServerConfig.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Configure error handlers
    _configure_error_handlers(app)
    
    # Configure request logging
    _configure_request_logging(app)
    
    # Setup static file caching
    _setup_static_file_caching(app)
    
    # Initialize and register API routes
    try:
        # Register API blueprint
        api_blueprint = create_api_routes(device_manager, enocean_system, synchronizer, logger)
        app.register_blueprint(api_blueprint)
        
        # Register monitoring blueprint
        monitoring_blueprint = create_monitoring_routes(enocean_system, logger)
        app.register_blueprint(monitoring_blueprint)
        
        logger.info("✅ All API and monitoring routes registered successfully")
        
    except Exception as e:
        logger.error(f"Failed to register routes: {e}")
        raise RuntimeError(f"Route registration failed: {e}")
    
    # --- SPA and Static File Routing ---
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        """
        Serve the Single Page Application with intelligent routing.
        
        This route handles:
        - Serving static assets (JS, CSS, images) when they exist
        - Falling back to index.html for client-side routing
        - Proper error handling for missing files
        
        Args:
            path: The requested path from the URL
            
        Returns:
            Flask response object with the requested file or SPA entry point
        """
        try:
            # If path is empty, serve the main SPA entry point
            if not path:
                return send_from_directory(app.static_folder, "index.html")
            
            # Check if the requested file exists in static folder
            static_file_path = Path(app.static_folder) / path
            
            if static_file_path.exists() and static_file_path.is_file():
                # Serve the actual static file
                response = send_from_directory(app.static_folder, path)
                
                # Add appropriate cache headers
                if path.endswith(('.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg')):
                    response.cache_control.max_age = WebServerConfig.STATIC_CACHE_TIMEOUT
                
                return response
            else:
                # Path doesn't exist as static file, serve SPA for client-side routing
                return send_from_directory(app.static_folder, "index.html")
                
        except Exception as e:
            logger.error(f"Error serving SPA route '{path}': {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to serve requested resource',
                'path': path
            }), 500
    
    # Health check endpoint (outside of API routes for load balancers)
    @app.route("/health")
    def health_check():
        """Simple health check endpoint for load balancers and monitoring."""
        try:
            # Basic system checks
            system_healthy = True
            health_info = {
                'status': 'healthy',
                'timestamp': time.time(),
                'service': 'enocean-gateway-web',
                'version': '2.0.0',
                'components': {}
            }

            # Check if core components are accessible
            try:
                if hasattr(enocean_system, 'running'):
                    health_info['components']['gateway'] = 'healthy' if enocean_system.running else 'stopped'
                    if not enocean_system.running:
                        system_healthy = False
                else:
                    health_info['components']['gateway'] = 'unknown'
            except:
                health_info['components']['gateway'] = 'error'
                system_healthy = False

            # Check device manager
            try:
                if hasattr(enocean_system, 'device_manager') and enocean_system.device_manager:
                    health_info['components']['device_manager'] = 'healthy'
                else:
                    health_info['components']['device_manager'] = 'missing'
            except:
                health_info['components']['device_manager'] = 'error'

            # Update overall status
            if not system_healthy:
                health_info['status'] = 'degraded'

            return jsonify(health_info)
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'timestamp': time.time(),
                'service': 'enocean-gateway-web',
                'error': str(e)
            }), 500
    
    # Add application context for debugging
    @app.context_processor
    def inject_debug_info():
        """Inject debug information into templates if needed."""
        return {
            'debug_mode': app.debug,
            'static_url': app.static_url_path
        }
    
    logger.info("🚀 Web application created successfully")
    logger.info(f"📁 Static files: {STATIC_DIR}")
    logger.info(f"🔧 Debug mode: {'ON' if app.debug else 'OFF'}")
    logger.info(f"🔒 CORS origins: {WebServerConfig.CORS_ORIGINS}")
    
    return app


def run_development_server(
    device_manager: DeviceManager,
    enocean_system: UnifiedEnOceanSystem,
    synchronizer: StateSynchronizer,
    eep_loader: EEPProfileLoader,
    host: str = "0.0.0.0",
    port: int = 5003,
    debug: bool = True
) -> None:
    """
    Run the web application in development mode.
    
    This is a convenience function for development and testing.
    For production deployment, use a proper WSGI server like Gunicorn.
    
    Args:
        device_manager: Device management service
        enocean_system: EnOcean communication system
        synchronizer: State synchronization service
        eep_loader: EEP profile loader
        host: Host to bind to (default: 0.0.0.0)
        port: Port to bind to (default: 5003)
        debug: Enable debug mode (default: True)
    """
    app = create_web_app(device_manager, enocean_system, synchronizer, eep_loader)
    
    logger.info(f"🌐 Starting development server on http://{host}:{port}")
    logger.warning("⚠️  This is a development server. Do not use in production!")
    
    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True,
            use_reloader=debug
        )
    except KeyboardInterrupt:
        logger.info("🛑 Development server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start development server: {e}")
        raise