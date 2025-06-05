import time
import random
import os
import logging
from threading import Thread
from opcua import Server, ua
from dotenv import load_dotenv 

# Configure security logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('opcua_security.log'),
        logging.StreamHandler()
    ]
)

class CertificateManager:
    def __init__(self, cert_dir="/app/certificates"):
        self.cert_dir = cert_dir
        self.server_cert_path = os.path.join(self.cert_dir, "server_certificate.pem")
        self.server_key_path = os.path.join(self.cert_dir, "server_private_key.pem")
    # Implemented but not used 
    def generate_certificates(self):
        """Generate self-signed certificates for testing."""
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            import datetime

            os.makedirs(self.cert_dir, exist_ok=True)

            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test OPC UA Server"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ])

            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow()
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.IPAddress("127.0.0.1"),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())

            with open(self.server_cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))

            with open(self.server_key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            print(f"Certificates generated successfully in '{self.cert_dir}' directory")
            return True

        except ImportError:
            print("cryptography library not installed. Run: pip install cryptography")
            return False
        except Exception as e:
            print(f"Failed to generate certificates: {e}")
            return False

    def load_certificates(self, server: Server):
        """Load server certificate and private key into the OPC UA server."""
        if not os.path.exists(self.server_cert_path) or not os.path.exists(self.server_key_path):
            raise FileNotFoundError("Server certificates not found. Please generate certificates first.")

        server.load_certificate(self.server_cert_path)
        server.load_private_key(self.server_key_path)
        logging.info("Server certificates loaded successfully.")


class UserManager:
    def __init__(self, env_path=None): 
        self.users_db = {}
        self._load_users_from_env()

    def _load_users_from_env(self):
        """Loads user credentials from environment variables."""
        # The environment variables are already loaded by docker-compose
        # from the .env file and available via os.getenv() inside the container.

        # Load operator user
        op_user = os.getenv("OP_USER")
        op_pass = os.getenv("OP_PASS")
        if op_user and op_pass:
            self.users_db[op_user] = {"password": op_pass, "role": "Operator"}
        else:
            logging.warning("Warning: Operator user credentials (OP_USER, OP_PASS) not found in environment.")

        # Load engineer user
        eng_user = os.getenv("ENG_USER")
        eng_pass = os.getenv("ENG_PASS")
        if eng_user and eng_pass:
            self.users_db[eng_user] = {"password": eng_pass, "role": "Engineer"}
        else:
            logging.warning("Warning: Engineer user credentials (ENG_USER, ENG_PASS) not found in environment.")

        # Load telegraf user
        telegraf_user = os.getenv("TELEGRAF_USER")
        telegraf_pass = os.getenv("TELEGRAF_PASS")
        if telegraf_user and telegraf_pass:
            self.users_db[telegraf_user] = {"password": telegraf_pass, "role": "Telegraf"}
        else:
            logging.warning("Warning: Engineer user credentials (ENG_USER, ENG_PASS) not found in environment.")

        # Load admin user
        admin_user = os.getenv("ADMIN_USER")
        admin_pass = os.getenv("ADMIN_PASS")
        if admin_user and admin_pass:
            self.users_db[admin_user] = {"password": admin_pass, "role": "Administrator"}
        else:
            logging.warning("Warning: Admin user credentials (ADMIN_USER, ADMIN_PASS) not found in environment.")

        if not self.users_db:
            logging.info("No users loaded from environment variables. Server will not have specific user authentication.")


    def setup_user_manager(self, server: Server):
        """Configure user authentication for the OPC UA server."""
        try:
            if not self.users_db:
                print("No users defined in UserManager. User authentication will be skipped.")
                return

            # Custom user validation function
            def validate_user(session, username, password):
                if username in self.users_db and self.users_db[username]["password"] == password:
                    logging.info(f"User {username} authenticated with role: {self.users_db[username]['role']}")
                    return True
                logging.warning(f"Authentication failed for user: {username}")
                return False

            server.user_manager.set_user_manager(validate_user)
            logging.info("User authentication configured using environment variables.")

        except Exception as e:
            logging.error(f"Failed to setup user authentication: {e}")


class SecureIndustrialOPCServer:
    def __init__(self):
        # Read from environment variables
        # Default to True for TLS if not specified, but allow explicit 'false'
        self.use_tls = os.getenv('SERVER_USE_TLS', 'true').lower() == 'true'
        self.server_url_non_secure = os.getenv('SERVER_URL_NON_SECURE', 'opc.tcp://0.0.0.0:4840/freeopcua/server/')
        self.server_url_secure = os.getenv('SERVER_URL_SECURE', 'opc.tcp://0.0.0.0:4843/freeopcua/server/')
        self.server_name = os.getenv('SERVER_NAME', "Secure Industrial Simulation Server")

        self.server = Server()
        self.certificate_manager = CertificateManager()
        self.user_manager = UserManager() # UserManager now loads from env vars directly

        if self.use_tls:
            self.setup_security()
            # If TLS was attempted but failed, self.use_tls might be updated in setup_security
            # to reflect fallback to non-secure mode.
        else:
            self.server.set_endpoint(self.server_url_non_secure)
            logging.info(f"Server will start with NO TLS at: {self.server_url_non_secure}")


        self.server.set_server_name(self.server_name)
        self.setup_address_space()

        self.running = False
        self.simulation_thread = None

    def setup_security(self):
        """Configure TLS security with certificates and user authentication."""
        try:
            # Set secure endpoint, then attempt to load certs
            self.server.set_endpoint(self.server_url_secure)
            self.certificate_manager.load_certificates(self.server)

            self.server.set_security_policy([
                ua.SecurityPolicyType.NoSecurity,
                ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
                ua.SecurityPolicyType.Basic256Sha256_Sign
            ])
            self.user_manager.setup_user_manager(self.server)

            logging.info("TLS security configured successfully")

        except FileNotFoundError as e:
            logging.error(f"Failed to setup security: {e}")
            logging.error("Server certificates not found. Please ensure they are mounted or generated.")
            logging.error("Falling back to non-secure mode")
            self.server.set_endpoint(self.server_url_non_secure)
            self.use_tls = False # Update status to reflect actual running mode
        except Exception as e:
            logging.error(f"Failed to setup security: {e}")
            logging.error("Falling back to non-secure mode")
            self.server.set_endpoint(self.server_url_non_secure)
            self.use_tls = False # Update status to reflect actual running mode

    def setup_address_space(self):
        """Set up the server address space with security considerations"""
        objects = self.server.get_objects_node()

        self.factory = objects.add_object("ns=2;i=1", "Factory")
        self.production_line = self.factory.add_object("ns=2;i=2", "ProductionLine1")

        self.temp_sensors = self.production_line.add_object("ns=2;i=3", "TemperatureSensors")
        self.temp_sensor_1 = self.temp_sensors.add_variable("ns=2;i=10", "Sensor1_Temperature", 20.0)
        self.temp_sensor_2 = self.temp_sensors.add_variable("ns=2;i=11", "Sensor2_Temperature", 25.0)
        self.temp_sensor_3 = self.temp_sensors.add_variable("ns=2;i=12", "Sensor3_Temperature", 22.0)

        self.temp_sensor_1.set_writable()
        self.temp_sensor_2.set_writable()
        self.temp_sensor_3.set_writable()

        self.motors = self.production_line.add_object("ns=2;i=4", "Motors")
        self.motor1_speed = self.motors.add_variable("ns=2;i=20", "Motor1_Speed", 0)
        self.motor1_status = self.motors.add_variable("ns=2;i=21", "Motor1_Status", False)
        self.motor2_speed = self.motors.add_variable("ns=2;i=22", "Motor2_Speed", 0)
        self.motor2_status = self.motors.add_variable("ns=2;i=23", "Motor2_Status", False)

        self.motor1_speed.set_writable()
        self.motor1_status.set_writable()
        self.motor2_speed.set_writable()
        self.motor2_status.set_writable()

        self.system_info = self.factory.add_object("ns=2;i=5", "SystemInfo")
        self.uptime = self.system_info.add_variable("ns=2;i=30", "Uptime", 0)
        self.total_production = self.system_info.add_variable("ns=2;i=31", "TotalProduction", 0)

        self.security_info = self.factory.add_object("ns=2;i=6", "SecurityInfo")
        self.tls_enabled = self.security_info.add_variable("ns=2;i=40", "TLS_Enabled", self.use_tls)
        self.connection_count = self.security_info.add_variable("ns=2;i=41", "Active_Connections", 0)

    def simulate_industrial_data(self):
        """Simulate realistic industrial data changes."""
        uptime_counter = 0
        production_counter = 0

        while self.running:
            try:
                base_temp_1 = 20.0 + random.uniform(-2, 3)
                base_temp_2 = 25.0 + random.uniform(-1.5, 2.5)
                base_temp_3 = 22.0 + random.uniform(-1, 2)

                self.temp_sensor_1.set_value(round(base_temp_1, 2))
                self.temp_sensor_2.set_value(round(base_temp_2, 2))
                self.temp_sensor_3.set_value(round(base_temp_3, 2))

                if self.motor1_status.get_value():
                    current_speed = self.motor1_speed.get_value()
                    new_speed = max(0, current_speed + random.uniform(-5, 5))
                    self.motor1_speed.set_value(int(new_speed))
                    production_counter += random.randint(1, 3)

                if self.motor2_status.get_value():
                    current_speed = self.motor2_speed.get_value()
                    new_speed = max(0, current_speed + random.uniform(-3, 3))
                    self.motor2_speed.set_value(int(new_speed))
                    production_counter += random.randint(1, 2)

                uptime_counter += 1
                self.uptime.set_value(uptime_counter)
                self.total_production.set_value(production_counter)

                try:
                    session_count = len(getattr(self.server, '_sessions', {}))
                    self.connection_count.set_value(session_count)
                except:
                    self.connection_count.set_value(0)

                time.sleep(2)

            except Exception as e:
                logging.error(f"Simulation error: {e}")
                break

    def start(self):
        """Start the secure OPC UA server"""
        try:
            self.server.start()

            if self.use_tls:
                logging.info(f"Secure OPC UA Server started at {self.server_url_secure}")
                logging.info("TLS encryption enabled")
                logging.info("Users: operator/op123, engineer/eng456, admin/admin789 (from .env)")
            else:
                logging.info(f"OPC UA Server started at {self.server_url_non_secure}")
                logging.warning("WARNING: Running in non-secure mode")

            logging.info("Server is running. Press Ctrl+C to stop.")

            self.running = True
            self.simulation_thread = Thread(target=self.simulate_industrial_data)
            self.simulation_thread.daemon = True
            self.simulation_thread.start()

            self.print_node_info()

        except Exception as e:
            print(f"Failed to start server: {e}")

    def print_node_info(self):
        """Print information about the server nodes"""
        logging.info("\nServer Address Space:")
        logging.info("- Factory")
        logging.info("  - ProductionLine1")
        logging.info("    - TemperatureSensors")
        logging.info("      - Sensor1_Temperature, Sensor2_Temperature, Sensor3_Temperature")
        logging.info("    - Motors")
        logging.info("      - Motor1_Speed, Motor1_Status, Motor2_Speed, Motor2_2Status")
        logging.info("  - SystemInfo")
        logging.info("    - Uptime, TotalProduction")
        logging.info("  - SecurityInfo")
        logging.info("    - TLS_Enabled, Active_Connections")

    def stop(self):
        """Stop the OPC UA server"""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=5)
        self.server.stop()
        logging.info("Secure server stopped.")


if __name__ == "__main__":
    import argparse
    # Auto generation of certificates are not used.
    parser = argparse.ArgumentParser(description='Secure Industrial OPC UA Server')
    parser.add_argument('--gen-certs', action='store_true', help='Generate certificates and exit')

    args = parser.parse_args()

    if args.gen_certs:
        cert_manager_local = CertificateManager()
        cert_manager_local.generate_certificates()
        exit(0)

    if not os.getenv('SERVER_USE_TLS') and os.path.exists(".env"):
        logging.info("Loading environment variables from local .env for direct run...")
        load_dotenv() # Load from local .env if not running in Docker

    server = SecureIndustrialOPCServer() # No direct 'use_tls' argument needed anymore

    try:
        server.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("\nShutting down secure server...")
        server.stop()
        exit(0)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        server.stop()
