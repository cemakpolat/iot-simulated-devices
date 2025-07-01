# server/app/api/websocket_handler.py
import asyncio
import websockets
import json
import logging
from typing import Dict, Any, Set, Optional, List, Union
from datetime import datetime
from ..services.thermostat_service import ThermostatControlService
from ..config import ServerConfig

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Enhanced WebSocket manager for real-time data streaming and notifications.
    Integrates with the notification service for alert broadcasting.
    """
    
    def __init__(self, thermostat_service: ThermostatControlService, config: ServerConfig):
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.thermostat_service = thermostat_service
        self.config = config
        self._data_stream_task: Optional[asyncio.Task] = None
        self._server_task: Optional[asyncio.Task] = None
        self._websocket_server: Optional[websockets.WebSocketServer] = None
        
        # Client metadata for better connection management
        self.client_metadata: Dict[websockets.WebSocketServerProtocol, Dict[str, Any]] = {}
        
        logger.info("WebSocketManager initialized.")

    async def register_client(self, websocket: websockets.WebSocketServerProtocol, client_info: Dict[str, Any] = None):
        """Registers a new WebSocket client and sends initial data."""
        self.connected_clients.add(websocket)
        
        # Store client metadata
        self.client_metadata[websocket] = {
            "connected_at": datetime.now().isoformat(),
            "remote_address": str(websocket.remote_address) if websocket.remote_address else "unknown",
            "user_agent": client_info.get("user_agent") if client_info else None,
            "client_id": client_info.get("client_id") if client_info else None,
            "last_ping": datetime.now().isoformat()
        }
        
        logger.info(f"WebSocket client connected: {websocket.remote_address}. Total: {len(self.connected_clients)}")
        
        # Send initial data
        await self._send_initial_data(websocket)
        
        # Send connection confirmation
        await self._send_to_client_safe(websocket, {
            "type": "connection_status", 
            "status": "connected",
            "message": "Connected to Smart Thermostat WebSocket",
            "timestamp": datetime.now().isoformat(),
            "client_count": len(self.connected_clients)
        })

    async def _send_initial_data(self, websocket: websockets.WebSocketServerProtocol):
        """Send initial data to newly connected client"""
        try:
            latest_data = self.thermostat_service.get_last_processed_data()
            latest_predictions = self.thermostat_service.get_last_predictions()

            if latest_data:
                initial_payload = {
                    "type": "sensor_update",
                    "data": latest_data,
                    "predictions": latest_predictions,
                    "timestamp": datetime.now().isoformat()
                }
                await self._send_to_client_safe(websocket, initial_payload)
                logger.debug(f"Sent initial data to new client {websocket.remote_address}.")
            else:
                # Send empty state if no data available
                await self._send_to_client_safe(websocket, {
                    "type": "sensor_update",
                    "data": None,
                    "predictions": None,
                    "message": "No sensor data available yet",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error sending initial data to client {websocket.remote_address}: {e}")

    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregisters a WebSocket client."""
        self.connected_clients.discard(websocket)
        
        # Clean up client metadata
        if websocket in self.client_metadata:
            client_info = self.client_metadata.pop(websocket)
            logger.info(f"WebSocket client disconnected: {client_info.get('remote_address')}. Total: {len(self.connected_clients)}")
        else:
            logger.info(f"WebSocket client disconnected. Total: {len(self.connected_clients)}")

    async def broadcast(self, message: Dict[str, Any], message_type: str = None):
        """
        Broadcasts a message to all currently connected clients.
        Enhanced with message type filtering and better error handling.
        """
        if not self.connected_clients:
            logger.debug("No WebSocket clients connected to broadcast to.")
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        
        # Add message type if specified
        if message_type:
            message["type"] = message_type

        message_json = json.dumps(message, default=str)  # Handle datetime serialization
        
        # Broadcast to all clients concurrently
        tasks = [
            self._send_to_client_safe(client, message)
            for client in list(self.connected_clients)
        ]
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_sends = sum(1 for result in results if result is True)
            logger.debug(f"Broadcasted message to {successful_sends}/{len(self.connected_clients)} WebSocket clients.")

    async def _send_to_client_safe(self, client: websockets.WebSocketServerProtocol, message: Union[Dict[str, Any], str]) -> bool:
        """
        Safely send a message to a single client with proper error handling.
        Returns True if successful, False otherwise.
        """
        try:
            if isinstance(message, dict):
                message_json = json.dumps(message, default=str)
            else:
                message_json = message
                
            await client.send(message_json)
            
            # Update last ping time
            if client in self.client_metadata:
                self.client_metadata[client]["last_ping"] = datetime.now().isoformat()
                
            return True
            
        except websockets.exceptions.ConnectionClosedOK:
            logger.debug(f"Client {client.remote_address} closed connection normally.")
            await self.unregister_client(client)
            return False
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"Client {client.remote_address} connection closed with error: {e}")
            await self.unregister_client(client)
            return False
        except Exception as e:
            logger.error(f"Error sending to WebSocket client {client.remote_address}: {e}")
            await self.unregister_client(client)
            return False

    async def data_stream_producer(self):
        """
        Enhanced data stream producer with better error handling and health monitoring.
        """
        logger.info("WebSocket data stream producer started.")
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while True:
            try:
                latest_processed_data = self.thermostat_service.get_last_processed_data()
                latest_predictions = self.thermostat_service.get_last_predictions()
                
                if latest_processed_data:
                    payload_to_broadcast = {
                        "type": "sensor_update",
                        "data": latest_processed_data,
                        "predictions": latest_predictions,
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.broadcast(payload_to_broadcast)
                    consecutive_errors = 0  # Reset error counter on success
                
                await asyncio.sleep(self.config.POLL_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("WebSocket data stream producer cancelled.")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in WebSocket data stream producer (attempt {consecutive_errors}): {e}", exc_info=True)
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"Too many consecutive errors ({consecutive_errors}). Data stream producer pausing for extended period.")
                    await asyncio.sleep(self.config.POLL_INTERVAL * 10)
                    consecutive_errors = 0
                else:
                    await asyncio.sleep(self.config.POLL_INTERVAL * 2)

    async def start_server(self, host: str = "0.0.0.0", port: int = 8092):
        """Start the WebSocket server with improved lifecycle management"""
        try:
            # Start data stream producer
            self._data_stream_task = asyncio.create_task(self.data_stream_producer())
            
            # Start WebSocket server
            self._websocket_server = await websockets.serve(
                self.websocket_handler, 
                host, 
                port,
                ping_interval=30,  # Send ping every 30 seconds
                ping_timeout=10,   # Wait 10 seconds for pong
                close_timeout=10   # Wait 10 seconds for close
            )
            
            logger.info(f"WebSocket server listening on ws://{host}:{port}")
            
            # Keep server running
            if self._websocket_server:
                await self._websocket_server.wait_closed()
                
        except Exception as e:
            logger.error(f"Error starting WebSocket server: {e}", exc_info=True)
            raise

    async def websocket_handler(self, websocket: websockets.WebSocketServerProtocol, path: str = None):
        """
        Enhanced WebSocket connection handler with better message processing.
        """
        client_address = websocket.remote_address
        
        try:
            # Extract client info from headers if available
            client_info = {}
            if hasattr(websocket, 'request_headers'):
                client_info["user_agent"] = websocket.request_headers.get("User-Agent")
                client_info["client_id"] = websocket.request_headers.get("X-Client-ID")
            
            await self.register_client(websocket, client_info)
            
            # Handle incoming messages
            async for message in websocket:
                await self._process_websocket_message(websocket, message, path)
                
        except websockets.exceptions.ConnectionClosedOK:
            logger.debug(f"WebSocket connection closed cleanly by {client_address}")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"WebSocket connection closed with error by {client_address}: {e}")
        except Exception as e:
            logger.error(f"Unexpected WebSocket error with client {client_address}: {e}", exc_info=True)
        finally:
            await self.unregister_client(websocket)

    async def _process_websocket_message(self, websocket: websockets.WebSocketServerProtocol, message: str, path: str = None):
        """Process incoming WebSocket messages"""
        try:
            command_data = json.loads(message)
            message_type = command_data.get("type")
            
            logger.info(f"Received WS message from {websocket.remote_address} on path {path}: type={message_type}")
            
            if message_type == "control_command":
                await self._handle_control_command(websocket, command_data)
            elif message_type == "ping":
                await self._handle_ping(websocket, command_data)
            elif message_type == "subscribe":
                await self._handle_subscription(websocket, command_data)
            else:
                logger.warning(f"Unknown message type received: {message_type}")
                await self._send_to_client_safe(websocket, {
                    "type": "error", 
                    "message": f"Unknown message type: {message_type}"
                })
                
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON WebSocket message: {message}")
            await self._send_to_client_safe(websocket, {
                "type": "error", 
                "message": "Invalid JSON format."
            })
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
            await self._send_to_client_safe(websocket, {
                "type": "error", 
                "message": "Error processing message."
            })

    async def _handle_control_command(self, websocket: websockets.WebSocketServerProtocol, command_data: Dict[str, Any]):
        """Handle control commands from WebSocket clients"""
        command = command_data.get("command")
        logger.info(f"Received control command via WS: {command}")
        
        # Here you could integrate with your thermostat service for actual control
        # For now, just acknowledge
        await self._send_to_client_safe(websocket, {
            "type": "ack", 
            "message": f"Command '{command}' received by AI Controller (WS).",
            "command": command
        })

    async def _handle_ping(self, websocket: websockets.WebSocketServerProtocol, ping_data: Dict[str, Any]):
        """Handle ping messages from clients"""
        await self._send_to_client_safe(websocket, {
            "type": "pong",
            "timestamp": datetime.now().isoformat(),
            "client_timestamp": ping_data.get("timestamp")
        })

    async def _handle_subscription(self, websocket: websockets.WebSocketServerProtocol, sub_data: Dict[str, Any]):
        """Handle subscription requests (for future use)"""
        subscribe_to = sub_data.get("subscribe_to", [])
        logger.info(f"Client {websocket.remote_address} wants to subscribe to: {subscribe_to}")
        
        await self._send_to_client_safe(websocket, {
            "type": "subscription_ack",
            "subscribed_to": subscribe_to,
            "message": "Subscription preferences updated"
        })

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            "total_connections": len(self.connected_clients),
            "connected_clients": [
                {
                    "address": str(client.remote_address) if client.remote_address else "unknown",
                    "metadata": self.client_metadata.get(client, {})
                }
                for client in self.connected_clients
            ],
            "server_running": self._websocket_server is not None and not self._websocket_server.is_serving(),
            "data_stream_active": self._data_stream_task is not None and not self._data_stream_task.done()
        }

    async def stop(self):
        """Enhanced stop method with proper cleanup"""
        logger.info("Stopping WebSocketManager...")
        
        # Cancel data stream task
        if self._data_stream_task and not self._data_stream_task.done():
            self._data_stream_task.cancel()
            try:
                await self._data_stream_task
            except asyncio.CancelledError:
                logger.info("Data stream task cancelled successfully")

        # Close WebSocket server
        if self._websocket_server:
            self._websocket_server.close()
            await self._websocket_server.wait_closed()
            logger.info("WebSocket server closed")

        # Close all client connections
        if self.connected_clients:
            close_tasks = []
            for client in list(self.connected_clients):
                try:
                    close_tasks.append(client.close())
                except Exception as e:
                    logger.warning(f"Error initiating close for client: {e}")
            
            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Clear all data structures
        self.connected_clients.clear()
        self.client_metadata.clear()
        
        logger.info("WebSocketManager stopped and all resources cleaned up.")

    # Integration methods for notification service
    async def send_notification_to_websockets(self, notification: Dict[str, Any]) -> bool:
        """Send notification specifically to WebSocket clients"""
        if not self.connected_clients:
            return False
            
        notification_message = {
            "type": "notification",
            "notification": notification,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.broadcast(notification_message)
        return True