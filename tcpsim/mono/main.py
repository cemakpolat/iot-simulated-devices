import threading
import time
import logging

from tcpexample.mono.client import TCPClient
from tcpexample.mono.server import TCPServer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Main Functionality to Start Server and Clients
def main():
    # Server Configuration
    server = TCPServer(host="0.0.0.0", port=50001)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    # Client Configuration
    devices = [
        TCPClient(server_host="127.0.0.1", server_port=50001, device_name="DeviceTCP1"),
        TCPClient(server_host="127.0.0.1", server_port=50001, device_name="DeviceTCP2"),
        TCPClient(server_host="127.0.0.1", server_port=50001, device_name="DeviceTCP3"),
    ]

    # Start clients in separate threads
    client_threads = []
    for device in devices:
        client_thread = threading.Thread(target=device.send_data, daemon=True)
        client_threads.append(client_thread)
        client_thread.start()

    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("\nExiting program...")
        # Gracefully stop clients and server
        for device in devices:
            device.stop()
        server.stop()
        # Wait for threads to finish
        for client_thread in client_threads:
            client_thread.join(timeout=1)
        server_thread.join(timeout=1)


if __name__ == "__main__":
    main()
