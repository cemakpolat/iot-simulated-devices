import logging
from flask import request, jsonify, render_template, current_app

logger = logging.getLogger(__name__)

def setup_routes(app):
    @app.route('/')
    def dashboard():
        return render_template('index.html')

    @app.route('/data', methods=['POST'])
    def receive_data():
        """Endpoint for ingesting sensor data asynchronously."""
        # Access the processor from the application context
        processor = current_app.processor
        try:
            data = request.get_json()
            if data is None:
                return jsonify({"error": "No JSON payload provided"}), 400
            
            processor.submit_data(data)
            return jsonify({"status": "Data accepted for processing"}), 202

        except ValueError as ve:
            logger.warning(f"Validation error: {ve}")
            return jsonify({"error": str(ve)}), 400
        except Exception as e:
            logger.error(f"Unexpected error on data submission: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @app.route('/latest', methods=['GET'])
    def latest():
        """Returns the latest processed data for the dashboard."""
        processor = current_app.processor
        return jsonify(processor.get_latest_readings())

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "healthy"}), 200