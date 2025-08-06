#!/usr/bin/env python3
"""
Routes Export - Clean interface for importing API routes
"""

# Import the unified API routes function
from .api_routes import create_api_routes
from .monitoring_routes import create_monitoring_routes

# Export for easy importing
__all__ = ['create_api_routes','create_monitoring_routes']

