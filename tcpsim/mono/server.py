import socket
import threading
import struct
import logging


# TCP Server Class
class TCPServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = []
        self.shutdown_flag = threading.Event()

    def handle_client(self, conn, addr):
        logging.info(f"Connected to client {addr}")
        try:
            while not self.shutdown_flag.is_set():
                data = conn.recv(1024)
                if not data:
                    break
                temp, hum = struct.unpack("!HH", data)
                logging.info(f"Received telemetry data from {addr} -> temp={temp}, hum={hum}")
        except ConnectionResetError:
            logging.warning(f"Connection with {addr} lost.")
        finally:
            conn.close()
            logging.info(f"Connection with {addr} closed.")

    def start(self):
        logging.info(f"Starting TCP Server at {self.host}:{self.port}...")
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        logging.info("Server is listening for connections...")
        try:
            while not self.shutdown_flag.is_set():
                conn, addr = server_socket.accept()
                self.clients.append((conn, addr))
                client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                client_thread.start()
        except KeyboardInterrupt:
            logging.info("\nShutting down server...")
        finally:
            server_socket.close()
            self.shutdown_flag.set()
            logging.info("Server shutdown complete.")

    def stop(self):
        self.shutdown_flag.set()
