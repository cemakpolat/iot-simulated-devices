# app/api/websocket/handlers.py
"""WebSocket event handlers."""

import json
import logging
import asyncio
from datetime import datetime   
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect, Depends

from ...core.dependencies import get_current_user_ws, get_device_service
from .manager import connection_manager

logger = logging.getLogger(__name__)


async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str = None,
    device_service = Depends(get_device_service)
):
    """Main WebSocket endpoint for real-time communication."""
    
    await connection_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, message, user_id, device_service)
            except json.JSONDecodeError:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, websocket)
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Internal server error"
                }, websocket)
    
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await connection_manager.disconnect(websocket, user_id)


async def handle_websocket_message(
    websocket: WebSocket, 
    message: Dict[str, Any], 
    user_id: str,
    device_service
):
    """Handle incoming WebSocket messages."""
    
    message_type = message.get("type")
    
    if message_type == "subscribe_device":
        device_id = message.get("device_id")
        if device_id:
            # Verify user has access to device
            try:
                await device_service.verify_device_access(device_id, user_id)
                await connection_manager.subscribe_to_device(websocket, device_id)
            except Exception as e:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": f"Cannot subscribe to device: {str(e)}"
                }, websocket)
    
    elif message_type == "unsubscribe_device":
        device_id = message.get("device_id")
        if device_id:
            await connection_manager.unsubscribe_from_device(websocket, device_id)
    
    elif message_type == "get_device_status":
        device_id = message.get("device_id")
        if device_id:
            try:
                await device_service.verify_device_access(device_id, user_id)
                status = await device_service.get_device_status(device_id)
                await connection_manager.send_personal_message({
                    "type": "device_status",
                    "device_id": device_id,
                    "data": status.dict()
                }, websocket)
            except Exception as e:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": f"Cannot get device status: {str(e)}"
                }, websocket)
    
    elif message_type == "send_command":
        device_id = message.get("device_id")
        command_data = message.get("command")
        if device_id and command_data:
            try:
                await device_service.verify_device_access(device_id, user_id)
                # Convert to ThermostatCommand and send
                from ...models.schemas.requests import ThermostatCommand
                command = ThermostatCommand(**command_data)
                result = await device_service.send_command(device_id, command)
                
                await connection_manager.send_personal_message({
                    "type": "command_result",
                    "device_id": device_id,
                    "success": True,
                    "data": result
                }, websocket)
            except Exception as e:
                await connection_manager.send_personal_message({
                    "type": "command_result",
                    "device_id": device_id,
                    "success": False,
                    "error": str(e)
                }, websocket)
    
    elif message_type == "ping":
        await connection_manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, websocket)
    
    else:
        await connection_manager.send_personal_message({
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        }, websocket)


async def broadcast_device_update(device_id: str, update_data: Dict[str, Any]):
    """Broadcast device update to all subscribed clients."""
    message = {
        "type": "device_update",
        "device_id": device_id,
        "data": update_data,
        "timestamp": datetime.now().isoformat()
    }
    
    await connection_manager.broadcast_to_device_subscribers(message, device_id)


async def broadcast_system_alert(alert_data: Dict[str, Any]):
    """Broadcast system alert to all connected clients."""
    message = {
        "type": "system_alert",
        "data": alert_data,
        "timestamp": datetime.now().isoformat()
    }
    
    await connection_manager.broadcast_to_all(message)


async def broadcast_maintenance_alert(device_id: str, maintenance_data: Dict[str, Any]):
    """Broadcast maintenance alert to device subscribers."""
    message = {
        "type": "maintenance_alert",
        "device_id": device_id,
        "data": maintenance_data,
        "timestamp": datetime.now().isoformat()
    }
    
    await connection_manager.broadcast_to_device_subscribers(message, device_id)