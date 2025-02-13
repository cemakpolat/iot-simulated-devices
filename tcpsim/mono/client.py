import socket
import threading
import time
import random
import struct
import logging


# TCP Client Class

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
        logging.info(f"{self.device_name}: Connecting to {self.server_host}:{self.server_port}...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            try:
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
                logging.error(f"{self.device_name}: Could not connect to server.")
            except KeyboardInterrupt:
                logging.info(f"{self.device_name}: Stopping client.")
            except Exception as error:
                logging.error(f"{self.device_name}: Error - {error}. Stopping client.")
            finally:
                self.shutdown_flag.set()

    def stop(self):
        self.shutdown_flag.set()
