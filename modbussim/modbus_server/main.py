import threading
import time
import logging
from server import start_modbus_server, update_registers  # Correct import
from flask_api import start_flask_api  # Correct import

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s")
log = logging.getLogger(__name__)

MODBUS_DATA_UPDATE_FREQUENCY = 5  # Reduced for testing

if __name__ == '__main__':
    # Start the Flask API in a separate thread
    flask_thread = threading.Thread(target=start_flask_api, daemon=True)
    flask_thread.start()

    # Start the Modbus server in a separate thread
    modbus_thread = threading.Thread(target=start_modbus_server, daemon=True)
    modbus_thread.start()

    try:
        # Periodically update registers
        while True:
            update_registers()
            time.sleep(MODBUS_DATA_UPDATE_FREQUENCY)  # Control update frequency here

    except KeyboardInterrupt:
        print("Stopping server...")
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")