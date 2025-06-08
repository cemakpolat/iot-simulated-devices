# # dashboard/app.py

# import eventlet
# eventlet.monkey_patch()  # Patch standard library for cooperative multitasking

# from flask import Flask, render_template, jsonify, request
# from flask_socketio import SocketIO, emit
# import json
# import time
# import random
# import aiohttp
# import asyncio
# import threading
# import websockets

# app = Flask(__name__, template_folder='templates', static_folder='static')
# app.config['SECRET_KEY'] = 'thermostat-dashboard-secret-key-12345'

# # Use eventlet async mode
# socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# # --- Dashboard Service Logic ---
# class DashboardService:
#     def __init__(self):
#         self.connected_clients_browser = set()
#         self.latest_data = {}
#         self.historical_data = self._generate_initial_historical_data()
#         self.ai_controller_ws_url = "ws://ai-controller:8092"
#         self.active_alerts = []
#         self.websocket_to_ai_controller_task_started = False

#     def _generate_initial_historical_data(self):
#         historical = []
#         now = time.time()
#         for i in range(48):
#             historical.append({
#                 "timestamp": now - (i * 3600),
#                 "temperature": round(22 + random.uniform(-2, 2), 1),
#                 "humidity": round(45 + random.uniform(-5, 5), 1),
#                 "energy": round(random.uniform(1, 3), 2)
#             })
#         return historical[::-1]

#     def start_data_stream_from_ai_controller(self):
#         if not self.websocket_to_ai_controller_task_started:
#             print(f"Dashboard attempting to connect to AI Controller WS at {self.ai_controller_ws_url} via SocketIO background task...")
#             socketio.start_background_task(self._connect_to_ai_controller_ws_sync)
#             self.websocket_to_ai_controller_task_started = True

#     def _connect_to_ai_controller_ws_sync(self):
#         # Run asyncio loop in a background thread safely under eventlet
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         loop.run_until_complete(self._connect_to_ai_controller_ws())

#     async def _connect_to_ai_controller_ws(self):
#         while True:
#             try:
#                 async with websockets.connect(self.ai_controller_ws_url) as ws:
#                     print(f"Successfully connected to AI Controller WebSocket at {self.ai_controller_ws_url}")
#                     while True:
#                         try:
#                             message_raw = await asyncio.wait_for(ws.recv(), timeout=60.0)
#                             message_parsed = json.loads(message_raw)

#                             if message_parsed.get("type") == "sensor_update":
#                                 self.latest_data = message_parsed.get("data", {})
#                                 self.latest_data["predictions"] = message_parsed.get("predictions", [])
#                                 socketio.emit('sensor_data', self.latest_data)

#                             elif message_parsed.get("type") == "alert":
#                                 alert = message_parsed.get("alert")
#                                 if alert:
#                                     self.active_alerts.insert(0, alert)
#                                     self.active_alerts = self.active_alerts[:10]
#                                     socketio.emit('alert', alert)
#                                     print(f"Received and broadcasted alert: {alert.get('message')}")

#                             else:
#                                 print(f"Received unknown message type from AI Controller: {message_parsed.get('type')} - {message_parsed}")

#                         except asyncio.TimeoutError:
#                             print("Dashboard WS: No message from AI Controller for 60 seconds.")
#                         await asyncio.sleep(0.1)

#             except websockets.exceptions.ConnectionClosedOK:
#                 print("Connection to AI Controller WebSocket closed cleanly. Reconnecting in 5s...")
#             except Exception as e:
#                 print(f"Error connecting/receiving from AI Controller WebSocket: {e}. Reconnecting in 5s...")
#             await asyncio.sleep(5)

# dashboard_service = DashboardService()

# # --- Flask Routes ---
# @app.route('/')
# def dashboard_page():
#     return render_template('index.html')

# @app.route('/api/current-data')
# def get_current_data_api():
#     return jsonify(dashboard_service.latest_data)

# @app.route('/api/historical-data')
# def get_historical_data_api():
#     return jsonify(dashboard_service.historical_data)

# @app.route('/api/alerts')
# def get_alerts_api():
#     return jsonify(dashboard_service.active_alerts)

# # --- Socket.IO Event Handlers ---
# @socketio.on('connect')
# def handle_connect(auth=None):
#     dashboard_service.connected_clients_browser.add(request.sid)
#     print(f"Browser client connected: {request.sid}. Total: {len(dashboard_service.connected_clients_browser)}")
#     emit('connected', {'status': 'Connected to Smart Thermostat Dashboard'})
#     if dashboard_service.latest_data:
#         emit('sensor_data', dashboard_service.latest_data, room=request.sid)
#     if dashboard_service.active_alerts:
#         for alert in dashboard_service.active_alerts:
#             emit('alert', alert, room=request.sid)

# @socketio.on('disconnect')
# def handle_disconnect():
#     dashboard_service.connected_clients_browser.discard(request.sid)
#     print(f"Browser client disconnected: {request.sid}. Total: {len(dashboard_service.connected_clients_browser)}")

# @socketio.on('send_command')
# def handle_command(data):
#     command = data.get('command', {})
#     print(f"Dashboard received command: {command}")

#     ai_controller_control_url = "http://ai-controller:8000/control/smart-thermostat-01"

#     async def send_command():
#         try:
#             async with aiohttp.ClientSession() as session:
#                 payload = {
#                     "action": command.get("action"),
#                     "target_temperature": command.get("target_temperature"),
#                     "mode": command.get("mode"),
#                     "fan_speed": command.get("fan_speed")
#                 }
#                 payload = {k: v for k, v in payload.items() if v is not None}

#                 async with session.post(ai_controller_control_url, json=payload, timeout=10) as resp:
#                     resp.raise_for_status()
#                     result = await resp.json()
#                     print(f"Command forwarded to AI Controller. Response: {result}")
#                     socketio.emit('command_result', {'status': 'success', 'command': command, 'message': 'Command sent to AI Controller.'})
#         except Exception as e:
#             print(f"Error sending command: {e}")
#             socketio.emit('command_result', {'status': 'error', 'command': command, 'message': f'Failed to send command: {e}'})

#     threading.Thread(target=lambda: asyncio.run(send_command())).start()

# # --- Main Entry ---
# if __name__ == '__main__':
#     dashboard_service.start_data_stream_from_ai_controller()
#     socketio.run(app, host='0.0.0.0', port=5000, debug=True)


# dashboard/app.py

import eventlet
eventlet.monkey_patch()  # Patch standard library for cooperative multitasking

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
import time
import random
import aiohttp
import asyncio
import threading # This can likely be removed after the fix
import websockets

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'thermostat-dashboard-secret-key-12345'

# Use eventlet async mode
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# --- Dashboard Service Logic ---
class DashboardService:
    def __init__(self):
        self.connected_clients_browser = set()
        self.latest_data = {}
        self.historical_data = self._generate_initial_historical_data()
        self.ai_controller_ws_url = "ws://ai-controller:8092"
        self.active_alerts = []
        self.websocket_to_ai_controller_task_started = False

    def _generate_initial_historical_data(self):
        historical = []
        now = time.time()
        for i in range(48):
            historical.append({
                "timestamp": now - (i * 3600),
                "temperature": round(22 + random.uniform(-2, 2), 1),
                "humidity": round(45 + random.uniform(-5, 5), 1),
                "energy": round(random.uniform(1, 3), 2)
            })
        return historical[::-1]

    def start_data_stream_from_ai_controller(self):
        if not self.websocket_to_ai_controller_task_started:
            print(f"Dashboard attempting to connect to AI Controller WS at {self.ai_controller_ws_url} via SocketIO background task...")
            socketio.start_background_task(self._connect_to_ai_controller_ws_sync)
            self.websocket_to_ai_controller_task_started = True

    def _connect_to_ai_controller_ws_sync(self):
        # Run asyncio loop in a background thread safely under eventlet
        # This part is still okay as it's for the WebSocket client which uses asyncio
        # and runs in a separate greenlet managed by eventlet.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._connect_to_ai_controller_ws())

    async def _connect_to_ai_controller_ws(self):
        while True:
            try:
                async with websockets.connect(self.ai_controller_ws_url) as ws:
                    print(f"Successfully connected to AI Controller WebSocket at {self.ai_controller_ws_url}")
                    while True:
                        try:
                            message_raw = await asyncio.wait_for(ws.recv(), timeout=60.0)
                            message_parsed = json.loads(message_raw)

                            if message_parsed.get("type") == "sensor_update":
                                self.latest_data = message_parsed.get("data", {})
                                self.latest_data["predictions"] = message_parsed.get("predictions", [])
                                socketio.emit('sensor_data', self.latest_data)

                            elif message_parsed.get("type") == "alert":
                                alert = message_parsed.get("alert")
                                if alert:
                                    self.active_alerts.insert(0, alert)
                                    self.active_alerts = self.active_alerts[:10]
                                    socketio.emit('alert', alert)
                                    print(f"Received and broadcasted alert: {alert.get('message')}")

                            else:
                                print(f"Received unknown message type from AI Controller: {message_parsed.get('type')} - {message_parsed}")

                        except asyncio.TimeoutError:
                            print("Dashboard WS: No message from AI Controller for 60 seconds.")
                        await asyncio.sleep(0.1)

            except websockets.exceptions.ConnectionClosedOK:
                print("Connection to AI Controller WebSocket closed cleanly. Reconnecting in 5s...")
            except Exception as e:
                print(f"Error connecting/receiving from AI Controller WebSocket: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

dashboard_service = DashboardService()

# --- Flask Routes ---
@app.route('/')
def dashboard_page():
    return render_template('index.html')

@app.route('/api/current-data')
def get_current_data_api():
    return jsonify(dashboard_service.latest_data)

@app.route('/api/historical-data')
def get_historical_data_api():
    return jsonify(dashboard_service.historical_data)

@app.route('/api/alerts')
def get_alerts_api():
    return jsonify(dashboard_service.active_alerts)

# --- Socket.IO Event Handlers ---
@socketio.on('connect')
def handle_connect(auth=None):
    dashboard_service.connected_clients_browser.add(request.sid)
    print(f"Browser client connected: {request.sid}. Total: {len(dashboard_service.connected_clients_browser)}")
    emit('connected', {'status': 'Connected to Smart Thermostat Dashboard'})
    if dashboard_service.latest_data:
        emit('sensor_data', dashboard_service.latest_data, room=request.sid)
    if dashboard_service.active_alerts:
        for alert in dashboard_service.active_alerts:
            emit('alert', alert, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    dashboard_service.connected_clients_browser.discard(request.sid)
    print(f"Browser client disconnected: {request.sid}. Total: {len(dashboard_service.connected_clients_browser)}")

@socketio.on('send_command')
def handle_command(data):
    command = data.get('command', {})
    print(f"Dashboard received command: {command}")

    ai_controller_control_url = "http://ai-controller:8000/control/smart-thermostat-01"

    # Define send_command as a regular function (or async if you want to use await inside it)
    # The crucial change is how it's called using eventlet.spawn_after
    async def send_command_async():
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "action": command.get("action"),
                    "target_temperature": command.get("target_temperature"),
                    "mode": command.get("mode"),
                    "fan_speed": command.get("fan_speed")
                }
                payload = {k: v for k, v in payload.items() if v is not None}

                async with session.post(ai_controller_control_url, json=payload, timeout=10) as resp:
                    resp.raise_for_status()
                    result = await resp.json()
                    print(f"Command forwarded to AI Controller. Response: {result}")
                    socketio.emit('command_result', {'status': 'success', 'command': command, 'message': 'Command sent to AI Controller.'})
        except Exception as e:
            print(f"Error sending command: {e}")
            socketio.emit('command_result', {'status': 'error', 'command': command, 'message': f'Failed to send command: {e}'})

    # Use socketio.start_background_task or eventlet.spawn to run the async function
    # within the eventlet loop. This avoids creating a new thread and a new asyncio loop.
    socketio.start_background_task(send_command_async)


# --- Main Entry ---
if __name__ == '__main__':
    dashboard_service.start_data_stream_from_ai_controller()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)