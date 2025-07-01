# server/app/api/routes/monitoring.py
"""Enhanced monitoring with your database health checks"""
import logging
from fastapi import APIRouter, Response, Depends
from prometheus_client import generate_latest

from ..dependencies import get_influxdb_client, get_postgres_client, get_redis_client
from ...database.influxdb_client import InfluxDBClient
from ...database.postgres_client import PostgreSQLClient
from ...database.redis_client import RedisClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/metrics")
async def get_prometheus_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")


@router.get("/health")
async def basic_health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "smart-thermostat-api",
        "version": "2.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check(
    influx_client: InfluxDBClient = Depends(get_influxdb_client),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
    redis_client: RedisClient = Depends(get_redis_client)
):
    """Detailed health check for all components"""
    from datetime import datetime
    
    health_status = {
        "service": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Check InfluxDB
    try:
        if influx_client.client:
            health_status["components"]["influxdb"] = "healthy"
        else:
            health_status["components"]["influxdb"] = "unhealthy: client not initialized"
    except Exception as e:
        health_status["components"]["influxdb"] = f"unhealthy: {str(e)}"
    
    # Check PostgreSQL
    try:
        postgres_healthy = await postgres_client.health_check()
        health_status["components"]["postgres"] = "healthy" if postgres_healthy else "unhealthy"
    except Exception as e:
        health_status["components"]["postgres"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        redis_healthy = await redis_client.ping()
        health_status["components"]["redis"] = "healthy" if redis_healthy else "unhealthy"
    except Exception as e:
        health_status["components"]["redis"] = f"unhealthy: {str(e)}"
    
    # Determine overall health
    all_healthy = all(
        status == "healthy" 
        for status in health_status["components"].values()
    )
    
    if not all_healthy:
        health_status["service"] = "degraded"
    
    return health_status

router.add_api_route("/health", basic_health_check, methods=["GET"])
router.add_api_route("/health/detailed", detailed_health_check, methods=["GET"])
router.add_api_route("/metrics", get_prometheus_metrics, methods=["GET"])