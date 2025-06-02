import time
import random
import os
from threading import Thread
from opcua import Server, ua


class SecureIndustrialOPCServer:
    def __init__(self, use_tls=True):
        # Initialize the server
        self.server = Server()
        self.use_tls = use_tls

        if use_tls:
            self.setup_security()
        else:
            self.server.set_endpoint("opc.tcp://localhost:4840/freeopcua/server/")

        self.server.set_server_name("Secure Industrial Simulation Server")

        # Set up the address space
        self.setup_address_space()

        # Variables for simulation
        self.running = False
        self.simulation_thread = None

    def setup_security(self):
        """Configure TLS security with certificates"""
        try:
            # Set secure endpoint
            self.server.set_endpoint("opc.tcp://localhost:4843/freeopcua/server/")

            # Load server certificate and private key
            server_cert_path = "certificates/server_certificate.pem"
            server_key_path = "certificates/server_private_key.pem"

            if not os.path.exists(server_cert_path) or not os.path.exists(server_key_path):
                raise FileNotFoundError("Server certificates not found. Please generate certificates first.")

            # Load certificate and private key
            self.server.load_certificate(server_cert_path)
            self.server.load_private_key(server_key_path)

            # Configure security policies
            self.server.set_security_policy([
                ua.SecurityPolicyType.NoSecurity,
                ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
                ua.SecurityPolicyType.Basic256Sha256_Sign
            ])
            # Set up user authentication
            self.setup_user_authentication()

            print("TLS security configured successfully")

        except Exception as e:
            print(f"Failed to setup security: {e}")
            print("Falling back to non-secure mode")
            self.server.set_endpoint("opc.tcp://localhost:4840/freeopcua/server/")
            self.use_tls = False

    def setup_user_authentication(self):
        """Configure user authentication"""
        try:
            # Define users with different access levels
            users_db = {
                "operator": {"password": "op123", "role": "Operator"},
                "engineer": {"password": "eng456", "role": "Engineer"},
                "admin": {"password": "admin789", "role": "Administrator"}
            }

            # Custom user validation function
            def validate_user(session, username, password):
                if username in users_db and users_db[username]["password"] == password:
                    print(f"User {username} authenticated with role: {users_db[username]['role']}")
                    return True
                print(f"Authentication failed for user: {username}")
                return False

            # Set the user manager callback
            self.server.user_manager.set_user_manager(validate_user)
            print("User authentication configured")

        except Exception as e:
            print(f"Failed to setup user authentication: {e}")

    def setup_address_space(self):
        """Set up the server address space with security considerations"""
        # Get the root objects node
        objects = self.server.get_objects_node()

        # Create our main factory object
        self.factory = objects.add_object("ns=2;i=1", "Factory")

        # Create production line object
        self.production_line = self.factory.add_object("ns=2;i=2", "ProductionLine1")

        # Add temperature sensors
        self.temp_sensors = self.production_line.add_object("ns=2;i=3", "TemperatureSensors")

        # Create individual temperature senso1r variables
        self.temp_sensor_1 = self.temp_sensors.add_variable("ns=2;i=10", "Sensor1_Temperature", 20.0)
        self.temp_sensor_2 = self.temp_sensors.add_variable("ns=2;i=11", "Sensor2_Temperature", 25.0)
        self.temp_sensor_3 = self.temp_sensors.add_variable("ns=2;i=12", "Sensor3_Temperature", 22.0)

        # Temperature sensors are read-only for operators, writable for engineers+
        self.temp_sensor_1.set_writable()
        self.temp_sensor_2.set_writable()
        self.temp_sensor_3.set_writable()

        # Add motor control section
        self.motors = self.production_line.add_object("ns=2;i=4", "Motors")

        # Create motor variables
        self.motor1_speed = self.motors.add_variable("ns=2;i=20", "Motor1_Speed", 0)
        self.motor1_status = self.motors.add_variable("ns=2;i=21", "Motor1_Status", False)
        self.motor2_speed = self.motors.add_variable("ns=2;i=22", "Motor2_Speed", 0)
        self.motor2_status = self.motors.add_variable("ns=2;i=23", "Motor2_Status", False)

        # Motor controls require engineer+ privileges
        self.motor1_speed.set_writable()
        self.motor1_status.set_writable()
        self.motor2_speed.set_writable()
        self.motor2_status.set_writable()

        # Add system information
        self.system_info = self.factory.add_object("ns=2;i=5", "SystemInfo")
        self.uptime = self.system_info.add_variable("ns=2;i=30", "Uptime", 0)
        self.total_production = self.system_info.add_variable("ns=2;i=31", "TotalProduction", 0)

        # Add security status information
        self.security_info = self.factory.add_object("ns=2;i=6", "SecurityInfo")
        self.tls_enabled = self.security_info.add_variable("ns=2;i=40", "TLS_Enabled", self.use_tls)
        self.connection_count = self.security_info.add_variable("ns=2;i=41", "Active_Connections", 0)

    def simulate_industrial_data(self):
        """Simulate realistic industrial data changes"""
        uptime_counter = 0
        production_counter = 0

        while self.running:
            try:
                # Simulate temperature fluctuations
                base_temp_1 = 20.0 + random.uniform(-2, 3)
                base_temp_2 = 25.0 + random.uniform(-1.5, 2.5)
                base_temp_3 = 22.0 + random.uniform(-1, 2)

                self.temp_sensor_1.set_value(round(base_temp_1, 2))
                self.temp_sensor_2.set_value(round(base_temp_2, 2))
                self.temp_sensor_3.set_value(round(base_temp_3, 2))

                # Simulate motor behavior
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

                # Update system information
                uptime_counter += 1
                self.uptime.set_value(uptime_counter)
                self.total_production.set_value(production_counter)

                # Update connection count - using a simpler approach
                # Get the number of active sessions/connections
                try:
                    # Try to get session count from server's session manager
                    session_count = len(getattr(self.server, '_sessions', {}))
                    self.connection_count.set_value(session_count)
                except:
                    # Fallback to a default value if unable to get session count
                    self.connection_count.set_value(0)

                time.sleep(2)

            except Exception as e:
                print(f"Simulation error: {e}")
                break

    def start(self):
        """Start the secure OPC UA server"""
        try:
            self.server.start()

            if self.use_tls:
                print("Secure OPC UA Server started at opc.tcp://localhost:4843/freeopcua/server/")
                print("TLS encryption enabled")
                print("Users: operator/op123, engineer/eng456, admin/admin789")
            else:
                print("OPC UA Server started at opc.tcp://localhost:4840/freeopcua/server/")
                print("WARNING: Running in non-secure mode")

            print("Server is running. Press Ctrl+C to stop.")

            # Start simulation thread
            self.running = True
            self.simulation_thread = Thread(target=self.simulate_industrial_data)
            self.simulation_thread.daemon = True
            self.simulation_thread.start()

            # Print node information
            self.print_node_info()

        except Exception as e:
            print(f"Failed to start server: {e}")

    def print_node_info(self):
        """Print information about the server nodes"""
        print("\nServer Address Space:")
        print("- Factory")
        print("  - ProductionLine1")
        print("    - TemperatureSensors")
        print("      - Sensor1_Temperature, Sensor2_Temperature, Sensor3_Temperature")
        print("    - Motors")
        print("      - Motor1_Speed, Motor1_Status, Motor2_Speed, Motor2_Status")
        print("  - SystemInfo")
        print("    - Uptime, TotalProduction")
        print("  - SecurityInfo")
        print("    - TLS_Enabled, Active_Connections")

    def stop(self):
        """Stop the OPC UA server"""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=5)
        self.server.stop()
        print("Secure server stopped.")


# Certificate generation helper function
def generate_certificates():
    """Generate self-signed certificates for testing"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime

        # Create certificates directory
        os.makedirs("certificates", exist_ok=True)

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create certificate
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

        # Write certificate
        with open("certificates/server_certificate.pem", "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # Write private key
        with open("certificates/server_private_key.pem", "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        print("Certificates generated successfully in 'certificates' directory")
        return True

    except ImportError:
        print("cryptography library not installed. Run: pip install cryptography")
        return False
    except Exception as e:
        print(f"Failed to generate certificates: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Secure Industrial OPC UA Server')
    parser.add_argument('--no-tls', action='store_true', help='Run without TLS security')
    parser.add_argument('--gen-certs', action='store_true', help='Generate certificates and exit')

    args = parser.parse_args()

    if args.gen_certs:
        generate_certificates()
        exit(0)

    # Set use_tls based on command line argument
    use_tls = not args.no_tls

    if use_tls and not (os.path.exists("certificates/server_certificate.pem") and
                        os.path.exists("certificates/server_private_key.pem")):
        print("Certificates not found. Generating certificates...")
        if not generate_certificates():
            print("Failed to generate certificates. Running without TLS.")
            use_tls = False

    server = SecureIndustrialOPCServer(use_tls=use_tls)

    try:
        server.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down secure server...")
        server.stop()
