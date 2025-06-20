# app/api/v1/devices.py
from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from ...core.dependencies import get_current_user, get_device_service
from ...models.schemas.requests import ThermostatCommand
from ...models.schemas.responses import DeviceStatusResponse, SensorDataResponse, SuccessResponse
from ...models.database.user import User
from ...services.device_service import DeviceService
from ...core.exceptions import ThermostatException, create_http_exception

router = APIRouter(prefix="/devices")

@router.get("/{device_id}/status", response_model=DeviceStatusResponse)
async def get_device_status(
    device_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    device_service: Annotated[DeviceService, Depends(get_device_service)]
):
    """Get current device status."""
    try:
        return await device_service.get_device_status(device_id)
    except ThermostatException as e:
        raise create_http_exception(e)

@router.post("/{device_id}/control", response_model=SuccessResponse)
async def send_control_command(
    device_id: str,
    command: ThermostatCommand,
    current_user: Annotated[User, Depends(get_current_user)],
    device_service: Annotated[DeviceService, Depends(get_device_service)]
):
    """Send control command to device."""
    try:
        result = await device_service.send_command(device_id, command)
        return SuccessResponse(
            message=f"Command sent to {device_id}",
            data=result
        )
    except ThermostatException as e:
        raise create_http_exception(e)

@router.get("/{device_id}/sensors", response_model=SensorDataResponse)
async def get_sensor_data(
    device_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    device_service: Annotated[DeviceService, Depends(get_device_service)]
):
    """Get current sensor data."""
    try:
        return await device_service.get_sensor_data(device_id)
    except ThermostatException as e:
        raise create_http_exception(e)

@router.get("/", response_model=list)
async def list_devices(
    current_user: Annotated[User, Depends(get_current_user)],
    device_service: Annotated[DeviceService, Depends(get_device_service)]
):
    """Get list of all devices."""
    try:
        return await device_service.get_all_devices()
    except ThermostatException as e:
        raise create_http_exception(e)

