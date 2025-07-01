"""WebSocket notifier for real-time browser notifications"""
import asyncio
import json
import logging
from typing import Dict, Any, Set
from datetime import datetime
from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)


class WebSocketNotifier(BaseNotifier):
    """WebSocket notifier for real-time web app notifications"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connections: Set[Any] = set()  # WebSocket connections
        self._websocket_manager = None
        
    async def initialize(self) -> bool:
        """Initialize WebSocket notifier"""
        logger.info("WebSocket notifier initialized")
        return True
    
    async def add_connection(self, websocket):
        """Add WebSocket connection"""
        self.connections.add(websocket)
        logger.info(f"WebSocket connection added. Total: {len(self.connections)}")
    
    async def remove_connection(self, websocket):
        """Remove WebSocket connection"""
        self.connections.discard(websocket)
        logger.info(f"WebSocket connection removed. Total: {len(self.connections)}")
    
    async def send(self, alert_type: str, message: str, data: Dict[str, Any] = None) -> bool:
        """Send WebSocket notification to all connected clients"""
        if not self.enabled:
            return False
        
        # If we have a websocket manager, prefer using that for broadcasting
        if self._websocket_manager and hasattr(self._websocket_manager, 'broadcast'):
            try:
                alert_payload = {
                    "type": "notification",
                    "alert_type": alert_type,
                    "message": message,
                    "data": data or {},
                    "timestamp": datetime.now().isoformat()
                }
                await self._websocket_manager.broadcast(alert_payload)
                logger.info("WebSocket notification sent via WebSocketManager")
                return True
            except Exception as e:
                logger.error(f"Failed to send via WebSocketManager: {e}")
        
        # Fallback to direct connection management
        if not self.connections:
            logger.debug("No WebSocket connections available")
            return False
        
        # Create WebSocket message
        ws_message = {
            "type": "notification",
            "alert_type": alert_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }
        
        message_json = json.dumps(ws_message)
        disconnected = set()
        success_count = 0
        
        # Send to all connections
        for connection in self.connections.copy():
            try:
                await connection.send_text(message_json)
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.connections.discard(conn)
        
        if success_count > 0:
            logger.info(f"WebSocket notification sent to {success_count} clients")
            
        return success_count > 0
    
    def set_websocket_manager(self, ws_manager):
        """Set the WebSocket manager for centralized broadcasting"""
        self._websocket_manager = ws_manager
        logger.info("WebSocket manager set for WebSocketNotifier")
    
    async def cleanup(self):
        """Cleanup WebSocket connections"""
        for connection in self.connections.copy():
            try:
                await connection.close()
            except Exception:
                pass
        self.connections.clear()
        logger.info("All WebSocket connections closed")