# server/app/api/routes/device.py
"""Updated device routes using your services"""
import json
import time
import logging
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any

from ..dependencies import (
    get_thermostat_service, get_coap_client, get_redis_client,
    get_prediction_service, get_maintenance_service, get_influxdb_client
)
from ..models.requests import ThermostatCommand
from ..models.responses import AuthenticatedUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/device", tags=["device"])


@router.get("/status/{device_id}")
async def get_device_status(
    device_id: str,
    coap_client=Depends(get_coap_client),
    redis_client=Depends(get_redis_client)
) -> Dict[str, Any]:
    """Get current device status using your Redis caching"""
    # Try your Redis cache first
    cached_data = await redis_client.get(f"latest_sensor_data:{device_id}")
    if cached_data:
        logger.info(f"Serving status for {device_id} from your Redis cache")
        return json.loads(cached_data)

    # Fetch from device using your CoAP client
    device_data = await coap_client.get_device_status()
    sensor_data = await coap_client.get_all_sensor_data()

    if not device_data or not sensor_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found or offline"
        )

    full_data = {**sensor_data, **device_data}
    await redis_client.set(f"latest_sensor_data:{device_id}", json.dumps(full_data), ex=30)
    return full_data


@router.post("/control/{device_id}")
async def send_control_command(
    device_id: str,
    command: ThermostatCommand,
    thermostat_service=Depends(get_thermostat_service)
) -> Dict[str, Any]:
    """Send control command using your ThermostatControlService"""
    logger.info(f"Sending command {command.dict()} to device {device_id}")
    
    try:
        # Create decision format expected by your service
        mock_decision = {
            "action": command.action,
            "target_temperature": command.target_temperature,
            "mode": command.mode or "manual",
            "fan_speed": command.fan_speed or "auto",
            "reasoning": [f"Manual control via API"],
            "confidence": 1.0
        }
        
        # Use your ThermostatControlService's execute_decision method
        success = await thermostat_service.execute_decision(mock_decision)
        
        if success:
            return {
                "status": "success",
                "command_executed": command.dict(),
                "device_id": device_id,
                "timestamp": time.time()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to execute command on device"
            )
    except Exception as e:
        logger.error(f"Error sending command to {device_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/predictions/{device_id}")
async def get_temperature_predictions(
    device_id: str,
    hours: int = 24,
    prediction_service=Depends(get_prediction_service)
) -> Dict[str, Any]:
    """Get temperature predictions using your PredictionService"""
    logger.info(f"Requesting {hours}-hour predictions for device {device_id}")
    
    try:
        # Use your PredictionService's get_predictions method
        predictions_data = await prediction_service.get_predictions(hours_ahead=hours)
        
        if predictions_data:
            predictions_data["device_id"] = device_id
            return predictions_data
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Predictions not available"
            )
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction service error: {str(e)}"
        )


@router.get("/maintenance/{device_id}")
async def get_device_maintenance_status(
    device_id: str,
    maintenance_service=Depends(get_maintenance_service),
    coap_client=Depends(get_coap_client)
) -> Dict[str, Any]:
    """Get device maintenance status using your MaintenanceService"""
    logger.info(f"Requesting maintenance status for device {device_id}")
    
    try:
        device_status_full = await coap_client.get_device_status()
        if not device_status_full:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} status not available for maintenance check"
            )
        
        # Use your MaintenanceService's check_maintenance_needs method
        maintenance_info = await maintenance_service.check_maintenance_needs(device_status_full)
        
        if maintenance_info:
            return maintenance_info
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Maintenance information not available for this device"
            )
    except Exception as e:
        logger.error(f"Error getting maintenance status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Maintenance service error: {str(e)}"
        )


@router.get("/energy/{device_id}")
async def get_energy_data(
    device_id: str,
    days: int = 7,
    influx_client=Depends(get_influxdb_client)
) -> Dict[str, Any]:
    """Get energy consumption data using your InfluxDBClient"""
    logger.info(f"Requesting {days}-day energy data for device {device_id}")
    
    try:
        # Use your InfluxDBClient's get_energy_data method
        energy_data_list = await influx_client.get_energy_data(device_id, days=days)

        if not energy_data_list:
            return {
                "daily_data": [],
                "total_consumption_kwh": 0.0,
                "average_daily_kwh": 0.0,
                "cost_projection_monthly_usd": 0.0,
                "device_id": device_id,
                "message": "No energy data available for this period"
            }
        
        # Process the data from your InfluxDB client
        processed_daily_data = []
        total_consumption_kwh = 0.0
        for entry in energy_data_list:
            processed_daily_data.append({
                "timestamp": entry['time'],
                "consumption_kwh": round(entry['value'], 2)
            })
            total_consumption_kwh += entry['value']

        average_daily_kwh = total_consumption_kwh / days if days > 0 else 0.0
        cost_projection_monthly_usd = average_daily_kwh * 30 * 0.15
        
        return {
            "daily_data": processed_daily_data,
            "total_consumption_kwh": round(total_consumption_kwh, 2),
            "average_daily_kwh": round(average_daily_kwh, 2),
            "cost_projection_monthly_usd": round(cost_projection_monthly_usd, 2),
            "device_id": device_id
        }
    except Exception as e:
        logger.error(f"Error getting energy data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Energy data service error: {str(e)}"
        )


router.add_api_route("/status/{device_id}", get_device_status, methods=["GET"])
router.add_api_route("/control/{device_id}", send_control_command, methods=["POST"])
router.add_api_route("/predictions/{device_id}", get_temperature_predictions, methods=["GET"])
router.add_api_route("/maintenance/{device_id}", get_device_maintenance_status, methods=["GET"])
router.add_api_route("/energy/{device_id}", get_energy_data, methods=["GET"])


