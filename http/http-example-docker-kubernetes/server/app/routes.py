import logging
from flask import request, jsonify, render_template
from tasks import process_data_task
from database import get_latest_readings_from_db, register_or_get_device
from celery_app import celery

logger = logging.getLogger(__name__)

def setup_routes(app):
    @app.route('/')
    def dashboard():
        return render_template('index.html')

    @app.route('/data', methods=['POST'])
    def receive_data():
        """Endpoint to receive data, register the device, and queue for processing."""
        try:
            data = request.get_json()
            if data is None: return jsonify({"error": "No JSON payload"}), 400
            
            device_id = data.get('device_id')
            if not device_id:
                return jsonify({"error": "Missing device_id"}), 400

            # --- DEVICE REGISTRATION LOGIC ---
            # On first contact, this will create the device in the database.
            # On subsequent contacts, it will do nothing but return True.
            if not register_or_get_device(device_id):
                return jsonify({"error": f"Failed to register device {device_id}"}), 500
            # ---------------------------------

            # Asynchronously call the processing task
            celery.send_task('tasks.process_data_task', args=[data])

            
            return jsonify({"status": "Data accepted"}), 202
        except Exception as e:
            logger.error(f"Error in /data endpoint: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @app.route('/latest', methods=['GET'])
    def latest():
        """Returns the latest processed data from the database."""
        latest_data = get_latest_readings_from_db()
        return jsonify(latest_data)
    
    @app.route('/config', methods=['POST'])
    def update_config():
        data = request.get_json()
        if data is None:
            return jsonify({"error": "No JSON payload"}), 400

        timeout = data.get('active_device_timeout_seconds')
        if timeout is not None:
            try:
                # Update the config value in-memory
                Config.ACTIVE_DEVICE_TIMEOUT_SECONDS = int(timeout)
                logger.info(f"Updated ACTIVE_DEVICE_TIMEOUT_SECONDS to {Config.ACTIVE_DEVICE_TIMEOUT_SECONDS}")
                return jsonify({"status": "updated", "active_device_timeout_seconds": Config.ACTIVE_DEVICE_TIMEOUT_SECONDS}), 200
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid value for timeout"}), 400
        
        return jsonify({"error": "No valid configuration key provided"}), 400
    
        
    @app.route('/health', methods=['GET'])
    def health_check():
        """A simple health check endpoint for Kubernetes probes."""
        return jsonify({"status": "healthy"}), 200