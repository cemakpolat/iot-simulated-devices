# app/api/websocket/manager.py
"""WebSocket connection manager for real-time updates."""

import asyncio
import json
import logging
from typing import Set, Dict, Any, Optional, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from ...core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ConnectionManager:
    """Manages WebSocket connections for real-time data streaming."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        self.device_subscriptions: Dict[str, Set[WebSocket]] = {}
        self._background_task: Optional[asyncio.Task] = None
        
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)
        
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "message": "Connected to Smart Thermostat WebSocket",
            "timestamp": datetime.now().isoformat()
        }, websocket)
    
    async def disconnect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from device subscriptions
        for device_id, connections in self.device_subscriptions.items():
            connections.discard(websocket)
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to a specific connection."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            await self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = []
        
        for websocket in list(self.active_connections):
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def broadcast_to_user(self, message: Dict[str, Any], user_id: str):
        """Broadcast message to all connections for a specific user."""
        if user_id not in self.user_connections:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = []
        
        for websocket in list(self.user_connections[user_id]):
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            await self.disconnect(websocket, user_id)
    
    async def broadcast_to_device_subscribers(self, message: Dict[str, Any], device_id: str):
        """Broadcast message to all clients subscribed to a device."""
        if device_id not in self.device_subscriptions:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = []
        
        for websocket in list(self.device_subscriptions[device_id]):
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to device {device_id} subscribers: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.device_subscriptions[device_id].discard(websocket)
    
    async def subscribe_to_device(self, websocket: WebSocket, device_id: str):
        """Subscribe a connection to device updates."""
        if device_id not in self.device_subscriptions:
            self.device_subscriptions[device_id] = set()
        
        self.device_subscriptions[device_id].add(websocket)
        
        await self.send_personal_message({
            "type": "subscription",
            "message": f"Subscribed to device {device_id}",
            "device_id": device_id
        }, websocket)
    
    async def unsubscribe_from_device(self, websocket: WebSocket, device_id: str):
        """Unsubscribe a connection from device updates."""
        if device_id in self.device_subscriptions:
            self.device_subscriptions[device_id].discard(websocket)
        
        await self.send_personal_message({
            "type": "unsubscription",
            "message": f"Unsubscribed from device {device_id}",
            "device_id": device_id
        }, websocket)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about current connections."""
        return {
            "total_connections": len(self.active_connections),
            "user_connections": len(self.user_connections),
            "device_subscriptions": {
                device_id: len(connections) 
                for device_id, connections in self.device_subscriptions.items()
            },
            "timestamp": datetime.now().isoformat()
        }


# Global connection manager instance
connection_manager = ConnectionManager()
