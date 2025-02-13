import random
import socket
import time
import struct
import logging
import os
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class TCPClient:
    def __init__(self, server_host, server_port, device_name):
        self.server_host = server_host
        self.server_port = server_port
        self.device_name = device_name
        self.shutdown_flag = threading.Event()

    def generate_telemetry(self):
        """
        Generate telemetry data as binary:
        - temp: Random temperature value (0-100), 2 bytes.
        - hum: Random humidity value (0-100), 2 bytes.
        """
        temp = random.randint(0, 100)
        hum = random.randint(1, 100)
        # Pack data into binary format (2 unsigned shorts, 2 bytes each)
        message = struct.pack("!HH", temp, hum)
        return message

    def send_data(self):
        while not self.shutdown_flag.is_set():
            try:
                logging.info(f"{self.device_name}: Connecting to {self.server_host}:{self.server_port}...")
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                    client_socket.connect((self.server_host, self.server_port))
                    logging.info(f"{self.device_name}: Connected to server.")
                    while not self.shutdown_flag.is_set():
                        telemetry_data = self.generate_telemetry()
                        client_socket.sendall(telemetry_data)

                        # Decode and log the sent data
                        temp, hum = struct.unpack("!HH", telemetry_data)
                        logging.info(f"{self.device_name}: Sent telemetry -> temp={temp}, hum={hum}")

                        time.sleep(2)  # Simulate periodic data sending
            except ConnectionRefusedError:
                logging.error(f"{self.device_name}: Could not connect to server. Retrying in 5 seconds...")
            except Exception as error:
                logging.error(f"{self.device_name}: Error - {error}. Retrying in 5 seconds...")
            finally:
                time.sleep(5)  # Wait before retrying

    def stop(self):
        self.shutdown_flag.set()


if __name__ == "__main__":
    # Read environment variables
    server_host = os.getenv("SERVER_HOST", "server")  # Default to "server" (Docker service name)
    server_port = int(os.getenv("SERVER_PORT", "50001"))  # Default to 50001
    device_name = os.getenv("DEVICE_NAME", f"device_{random.randint(1000, 9999)}")  # Generate unique device name

    client = TCPClient(server_host=server_host, server_port=server_port, device_name=device_name)
    client.send_data()