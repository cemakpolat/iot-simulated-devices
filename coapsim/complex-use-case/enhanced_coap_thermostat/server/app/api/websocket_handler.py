# server/app/api/websocket_handler.py
import asyncio
import websockets
import json
import logging
from typing import Dict, Any, Set, Optional, List
from ..services.thermostat_service import ThermostatControlService
from ..config import ServerConfig
from fastapi import  Request # This  should be tested. 


logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages WebSocket connections for real-time data streaming from the AI Controller.
    It acts as a data broadcaster for dashboards and other clients.
    """
    def __init__(self, thermostat_service: ThermostatControlService, config: ServerConfig):
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.thermostat_service = thermostat_service
        self.config = config
        self._data_stream_task: Optional[asyncio.Task] = None # Task for the data producer loop
        
        logger.info("WebSocketManager initialized.")

    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Registers a new WebSocket client and sends initial data."""
        self.connected_clients.add(websocket)
        logger.info(f"WebSocket client connected: {websocket.remote_address}. Total: {len(self.connected_clients)}")
        
        latest_data = self.thermostat_service.get_last_processed_data()
        latest_predictions = self.thermostat_service.get_last_predictions()

        if latest_data:
            initial_payload = {
                "type": "sensor_update",
                "data": latest_data,
                "predictions": latest_predictions
            }
            try:
                await websocket.send(json.dumps(initial_payload))
                logger.debug(f"Sent initial data to new client {websocket.remote_address}.")
            except websockets.exceptions.ConnectionClosedOK:
                logger.info(f"Client {websocket.remote_address} disconnected before initial send.")
                await self.unregister_client(websocket)
            except Exception as e:
                logger.error(f"Error sending initial data to client {websocket.remote_address}: {e}")
                await self.unregister_client(websocket)

        await websocket.send(json.dumps({"type": "status", "message": "Connected to AI Controller WebSocket"}))

    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregisters a WebSocket client."""
        self.connected_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected: {websocket.remote_address}. Total: {len(self.connected_clients)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcasts a message to all currently connected clients."""
        if not self.connected_clients:
            logger.debug("No WebSocket clients connected to broadcast to.")
            return

        message_json = json.dumps(message)
        
        await asyncio.gather(*[
            self._send_to_client(client, message_json)
            for client in list(self.connected_clients)
        ])
        logger.debug(f"Broadcasted message to {len(self.connected_clients)} WebSocket clients.")

    async def _send_to_client(self, client: websockets.WebSocketServerProtocol, message_json: str):
        """Helper to send a message to a single client, handling potential disconnections."""
        try:
            await client.send(message_json)
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"Client {client.remote_address} closed connection. Unregistering.")
            await self.unregister_client(client)
        except Exception as e:
            logger.error(f"Error sending to WebSocket client {client.remote_address}: {e}", exc_info=True)
            await self.unregister_client(client)

    async def data_stream_producer(self):
        """
        Periodically fetches the latest sensor data and predictions from the
        ThermostatControlService and broadcasts it to all connected WebSocket clients.
        """
        logger.info("WebSocket data stream producer started.")
        while True:
            try:
                latest_processed_data = self.thermostat_service.get_last_processed_data()
                latest_predictions = self.thermostat_service.get_last_predictions()
                
                if latest_processed_data:
                    payload_to_broadcast = {
                        "type": "sensor_update",
                        "data": latest_processed_data,
                        "predictions": latest_predictions
                    }
                    await self.broadcast(payload_to_broadcast)
                
                await asyncio.sleep(self.config.POLL_INTERVAL)
            except asyncio.CancelledError:
                logger.info("WebSocket data stream producer cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket data stream producer: {e}", exc_info=True)
                await asyncio.sleep(self.config.POLL_INTERVAL * 2)
    async def start_server(self, host: str = "0.0.0.0", port: int = 8001):
        self._data_stream_task = asyncio.create_task(self.data_stream_producer())
        async with websockets.serve(self.websocket_handler, host, port):
            logger.info(f"WebSocket server listening on ws://{host}:{port}")
            await asyncio.Future()
        
    async def websocket_handler(self, websocket: websockets.WebSocketServerProtocol):
        
        """
        Handles incoming WebSocket connections and messages.
        """
        # try:
        #     request = websocket.handshake_request
        #     path = request.path
        # except Exception as e:
        #     logger.warning(f"Could not retrieve handshake request or path: {e}")
        #     path = None

        try:
            request = await websocket.recv_request()
            if not isinstance(request, Request):
                logger.warning("Unexpected frame received instead of HTTP request.")
                await websocket.close(4000, "Expected HTTP request")
                return
            path = request.path
        except Exception as e:
            logger.warning(f"Could not retrieve request or path: {e}")
            path = None

        await self.register_client(websocket)
        try:
            async for message in websocket:
                logger.info(f"Received WS message from {websocket.remote_address} on path {path}: {message}")
                try:
                    command_data = json.loads(message)
                    if command_data.get("type") == "control_command":
                        logger.info(f"Received control command via WS: {command_data['command']}")
                        await websocket.send(json.dumps({"type": "ack", "message": "Command received by AI Controller (WS)."}))
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON WebSocket message: {message}")
                    await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON format."}))

        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"WebSocket connection closed cleanly by {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Unexpected WebSocket error with client {websocket.remote_address}: {e}", exc_info=True)
        finally:
            await self.unregister_client(websocket)

    async def stop(self):
        if self._data_stream_task:
            self._data_stream_task.cancel()
            try:
                await self._data_stream_task
            except asyncio.CancelledError:
                pass
        
        for client in list(self.connected_clients):
            try:
                await client.close()
            except Exception as e:
                logger.warning(f"Error closing WS client connection: {e}")
        self.connected_clients.clear()
        logger.info("WebSocketManager stopped and all client connections closed.")