from flask import Flask
from routes import setup_routes
from config import Config
from processing import DataProcessor
import multiprocessing
import signal
import sys
import logging

logger = logging.getLogger(__name__)

# --- SHARED STATE INITIALIZATION ---
# This code runs ONCE in the Gunicorn master process
# before the application is forked into worker processes.
manager = multiprocessing.Manager()
shared_queue = manager.Queue()
shared_latest_readings = manager.dict()
# ------------------------------------

def create_app():
    app = Flask(__name__, template_folder='templates')
    
    # Instantiate the processor with the SHARED objects
    processor = DataProcessor(
        data_queue=shared_queue,
        latest_readings=shared_latest_readings
    )
    
    # Attach the processor to the app so routes can access it
    app.processor = processor
    
    setup_routes(app)
    return app

app = create_app()

def signal_handler(sig, frame):
    logger.info("Shutting down gracefully...")
    sys.exit(0)

if __name__ == "__main__":
    # This block is for local development (e.g., python main.py)
    # It will NOT be used by Gunicorn
    Config.setup_logging()
    config = Config()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info(f"Starting HTTP inference server on {config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, threaded=True)