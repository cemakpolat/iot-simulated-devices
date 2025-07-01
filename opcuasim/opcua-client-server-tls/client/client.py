import time
import os
import sys
import random
import logging
import threading
import signal
from datetime import datetime
from opcua import Client, ua

# Configure security logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('opcua_security.log'),
        logging.StreamHandler()
    ]
)

class ClientCertificateManager:
    def __init__(self, cert_dir="/app/certificates"):
        self.cert_dir = cert_dir
        self.client_cert_path = os.path.join(self.cert_dir, "client_certificate.pem")
        self.client_key_path = os.path.join(self.cert_dir, "client_private_key.pem")

    def load_client_certificates(self, client: Client):
        """Load client certificate and private key into the OPC UA client."""
        if os.path.exists(self.client_cert_path) and os.path.exists(self.client_key_path):
            return self.client_cert_path, self.client_key_path
        else:
            logging.warning(f"Client certificates not found in {self.cert_dir}")
            return None, None


class ClientSecurityManager:
    def __init__(self, certificate_manager: ClientCertificateManager, use_tls_initial: bool, username: str = None, password: str = None):
        self.certificate_manager = certificate_manager
        self._use_tls = use_tls_initial # Store initial state
        self.username = username
        self.password = password

    @property
    def use_tls(self):
        """Read-only property for the current TLS status after configuration attempts."""
        return self._use_tls

    def configure_client_security(self, client: Client):
        """Configure client security settings including TLS and authentication."""
        if not self._use_tls:
            logging.info("TLS is disabled for the client as per configuration.")
            return True # No TLS to configure, so it's "successful" in that regard

        try:
            cert_path, key_path = self.certificate_manager.load_client_certificates(client)

            if cert_path and key_path:
                policy_string = f"Basic256Sha256,SignAndEncrypt,{cert_path},{key_path}"
                client.set_security_string(policy_string)
                logging.info("Client TLS security configured with certificates (SignAndEncrypt).")
                self._use_tls = True # Confirm TLS is enabled
            else:
                logging.warning("Client certificates not available. Attempting TLS with 'Sign' policy if server allows.")
                try:
                    client.set_security_string("Basic256Sha256,Sign")
                    logging.info("Using TLS with 'Sign' policy.")
                    self._use_tls = True # Confirm TLS is enabled (Sign only)
                except Exception as e:
                    logging.error(f"TLS 'Sign' policy setup failed: {e}. Falling back to no security.")
                    self._use_tls = False # Update internal state to reflect failure
                    return False # Indicate TLS setup failed

            if self.username and self.password:
                client.set_user(self.username)
                client.set_password(self.password)
                logging.info(f"Authentication configured for user: {self.username}")
            else:
                logging.info("No user credentials provided for authentication.")

            return True

        except Exception as e:
            logging.error(f"Security setup failed: {e}")
            logging.error("Falling back to no security (TLS disabled).")
            self._use_tls = False # Update internal state to reflect failure
            return False # Indicate failure


class AutomatedIndustrialOPCClient:
    def __init__(self):
        """
        Initialize the OPC UA client by reading configuration from environment variables.
        """
        self.server_url = os.getenv('OPC_SERVER_URL', 'opc.tcp://localhost:4840/freeopcua/server/')
        self.use_tls_config = os.getenv('OPC_USE_TLS', 'false').lower() == 'true' # Initial config from env
        self.username = os.getenv('OPC_USERNAME', 'operator')
        self.password = os.getenv('OPC_PASSWORD', 'op123')

        self.operation_interval = int(os.getenv('OPC_OPERATION_INTERVAL', '10'))
        self.monitoring_enabled = os.getenv('OPC_MONITORING_ENABLED', 'true').lower() == 'true'
        self.auto_control_enabled = os.getenv('OPC_AUTO_CONTROL_ENABLED', 'true').lower() == 'true'
        self.max_retries = int(os.getenv('OPC_MAX_RETRIES', '5'))
        self.retry_delay = int(os.getenv('OPC_RETRY_DELAY', '5'))

        self.client = Client(self.server_url)

        self.certificate_manager = ClientCertificateManager()
        # Pass the initial TLS config to the security manager
        self.security_manager = ClientSecurityManager(
            certificate_manager=self.certificate_manager,
            use_tls_initial=self.use_tls_config, # Pass the initial config
            username=self.username,
            password=self.password
        )

        self.nodes = {}
        self.subscription = None
        self.monitoring = False
        self.running = True
        self.automation_thread = None

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logging.info(f"\nReceived signal {signum}. Shutting down gracefully...")
        self.running = False

    def connect(self):
        """Connect to the OPC UA server with retries"""
        for attempt in range(self.max_retries):
            try:
                # Configure security and authentication using the manager
                # The security_manager updates its own internal _use_tls state
                self.security_manager.configure_client_security(self.client)

                self.client.connect()
                logging.info(f"Connected to server: {self.server_url}")

                try:
                    server_node = self.client.get_server_node()
                    server_name = server_node.get_display_name().to_string()
                    logging.info(f"Server name: {server_name}")
                except Exception as e:
                    logging.error(f"Could not retrieve server name: {e}")
                    logging.error("Server connected successfully")

                self.discover_nodes()
                return True

            except Exception as e:
                logging.error(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logging.error("Max retries reached. Connection failed.")

        return False

    def discover_nodes(self):
        """Discover and cache important server nodes using exact NodeIDs"""
        try:
            self.nodes['temp_sensor_1'] = self.client.get_node("ns=2;i=10")
            self.nodes['temp_sensor_2'] = self.client.get_node("ns=2;i=11")
            self.nodes['temp_sensor_3'] = self.client.get_node("ns=2;i=12")

            self.nodes['motor1_speed'] = self.client.get_node("ns=2;i=20")
            self.nodes['motor1_status'] = self.client.get_node("ns=2;i=21")
            self.nodes['motor2_speed'] = self.client.get_node("ns=2;i=22")
            self.nodes['motor2_status'] = self.client.get_node("ns=2;i=23")

            self.nodes['uptime'] = self.client.get_node("ns=2;i=30")
            self.nodes['total_production'] = self.client.get_node("ns=2;i=31")

            self.nodes['tls_enabled'] = self.client.get_node("ns=2;i=40")
            self.nodes['connection_count'] = self.client.get_node("ns=2;i=41")

            logging.info("Node discovery completed successfully")
        except Exception as e:
            logging.error(f"Node discovery failed: {e}")

    def read_all_values(self):
        """Read all current values from the server"""
        logging.info("\n" + "=" * 60)
        logging.info(f"AUTOMATED SYSTEM STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("=" * 60)

        try:
            print("\nTEMPERATURE SENSORS:")
            if 'temp_sensor_1' in self.nodes:
                temp1 = self.nodes['temp_sensor_1'].get_value()
                temp2 = self.nodes['temp_sensor_2'].get_value()
                temp3 = self.nodes['temp_sensor_3'].get_value()
                logging.info(f"  Sensor 1: {temp1}°C")
                logging.info(f"  Sensor 2: {temp2}°C")
                logging.info(f"  Sensor 3: {temp3}°C")

            print("\nMOTOR STATUS:")
            if 'motor1_speed' in self.nodes:
                motor1_speed = self.nodes['motor1_speed'].get_value()
                motor1_status = self.nodes['motor1_status'].get_value()
                motor2_speed = self.nodes['motor2_speed'].get_value()
                motor2_status = self.nodes['motor2_status'].get_value()

                logging.info(f"  Motor 1: {'RUNNING' if motor1_status else 'STOPPED'} - Speed: {motor1_speed} RPM")
                logging.info(f"  Motor 2: {'RUNNING' if motor2_status else 'STOPPED'} - Speed: {motor2_speed} RPM")

            print("\nSYSTEM INFORMATION:")
            if 'uptime' in self.nodes:
                uptime = self.nodes['uptime'].get_value()
                production = self.nodes['total_production'].get_value()
                # Use the security manager's current TLS status
                tls_enabled_status = self.security_manager.use_tls
                connections = self.nodes['connection_count'].get_value()

                logging.info(f"  Uptime: {uptime} cycles")
                logging.info(f"  Total Production: {production} units")
                logging.info(f"  TLS Security: {'ENABLED' if tls_enabled_status else 'DISABLED'}")
                logging.info(f"  Active Connections: {connections}")

        except Exception as e:
            logging.error(f"Error reading values: {e}")

    def control_motor(self, motor_num, status, speed=None):
        """Control motor operation"""
        try:
            if motor_num == 1 and 'motor1_status' in self.nodes:
                self.nodes['motor1_status'].set_value(status)
                if speed is not None:
                    self.nodes['motor1_speed'].set_value(speed)
                logging.info(f"[AUTO] Motor 1 {'started' if status else 'stopped'}")
                if speed:
                    logging.info(f"[AUTO] Motor 1 speed set to {speed} RPM")

            elif motor_num == 2 and 'motor2_status' in self.nodes:
                self.nodes['motor2_status'].set_value(status)
                if speed is not None:
                    self.nodes['motor2_speed'].set_value(speed)
                logging.info(f"[AUTO] Motor 2 {'started' if status else 'stopped'}")
                if speed:
                    logging.info(f"[AUTO] Motor 2 speed set to {speed} RPM")

        except Exception as e:
            logging.error(f"Motor control failed: {e}")

    def random_operation(self):
        """Perform random operations on the system"""
        if not self.auto_control_enabled:
            return

        operations = [
            self._random_motor_control,
            self._random_speed_adjustment,
            self._random_temperature_setpoint
        ]

        operation = random.choice(operations)
        try:
            operation()
        except Exception as e:
            logging.error(f"Random operation failed: {e}")

    def _random_motor_control(self):
        """Randomly start/stop motors"""
        motor = random.choice([1, 2])
        action = random.choice([True, False])
        speed = random.randint(50, 200) if action else None

        logging.error(f"[AUTO] Random motor operation: Motor {motor} {'START' if action else 'STOP'}")
        self.control_motor(motor, action, speed)

    def _random_speed_adjustment(self):
        """Randomly adjust motor speeds"""
        motor = random.choice([1, 2])
        speed = random.randint(50, 200)

        try:
            node_name = f'motor{motor}_speed'
            if node_name in self.nodes:
                self.nodes[node_name].set_value(speed)
                logging.info(f"[AUTO] Random speed adjustment: Motor {motor} speed set to {speed} RPM")
        except Exception as e:
            logging.error(f"Speed adjustment failed: {e}")

    def _random_temperature_setpoint(self):
        """Randomly adjust temperature setpoints (if writable)"""
        sensor = random.choice([1, 2, 3])
        temperature = round(random.uniform(20.0, 80.0), 1)

        try:
            node_name = f'temp_sensor_{sensor}'
            if node_name in self.nodes:
                self.nodes[node_name].set_value(temperature)
                logging.info(f"[AUTO] Random temperature setpoint: Sensor {sensor} set to {temperature}°C")
        except Exception as e:
            logging.error(f"Temperature setpoint failed: {e}")

    class DataChangeHandler:
        """Handler for subscription data changes"""

        def __init__(self, client_instance):
            self.client = client_instance

        def datachange_notification(self, node, val, data):
            """Handle data change notifications"""
            try:
                node_id_identifier = node.nodeid.Identifier
                if isinstance(node_id_identifier, ua.NodeId):
                    node_id_identifier = node_id_identifier.Identifier
                elif not isinstance(node_id_identifier, int):
                    try:
                        node_id_identifier = int(str(node_id_identifier).split(';')[-1])
                    except ValueError:
                        logging.error(f"Warning: Could not parse node ID for monitoring: {node_id_identifier}")
                        return

                timestamp = datetime.now().strftime('%H:%M:%S')

                node_names = {
                    10: "Temp Sensor 1",
                    11: "Temp Sensor 2",
                    12: "Temp Sensor 3",
                    20: "Motor 1 Speed",
                    21: "Motor 1 Status",
                    22: "Motor 2 Speed",
                    23: "Motor 2 Status",
                    30: "System Uptime",
                    31: "Total Production"
                }

                name = node_names.get(node_id_identifier, f"Node {node_id_identifier}")

                if isinstance(val, bool):
                    val_str = "ON" if val else "OFF"
                elif isinstance(val, float):
                    val_str = f"{val:.2f}"
                else:
                    val_str = str(val)

                logging.info(f"[MONITOR] [{timestamp}] {name}: {val_str}")

            except Exception as e:
                logging.error(f"Error in data change handler: {e}")

    def start_monitoring(self):
        """Start monitoring data changes via subscription"""
        if not self.monitoring_enabled:
            return

        try:
            if not self.nodes:
                logging.info("No nodes discovered - cannot start monitoring")
                return

            self.subscription = self.client.create_subscription(1000, self.DataChangeHandler(self))

            available_nodes = []
            for i in range(1, 4):
                node_name = f'temp_sensor_{i}'
                if node_name in self.nodes:
                    available_nodes.append(self.nodes[node_name])

            motor_node_names = ['motor1_speed', 'motor1_status', 'motor2_speed', 'motor2_status']
            for node_name in motor_node_names:
                if node_name in self.nodes:
                    available_nodes.append(self.nodes[node_name])

            system_node_names = ['uptime', 'total_production']
            for node_name in system_node_names:
                if node_name in self.nodes:
                    available_nodes.append(self.nodes[node_name])

            if available_nodes:
                handles = self.subscription.subscribe_data_change(available_nodes)
                self.monitoring = True
                logging.info(f"Started monitoring {len(available_nodes)} nodes...")
            else:
                logging.info("No nodes available for monitoring")

        except Exception as e:
            logging.error(f"Monitoring setup failed: {e}")

    def stop_monitoring(self):
        """Stop monitoring data changes"""
        try:
            if self.subscription:
                self.subscription.delete()
                self.subscription = None
            self.monitoring = False
            logging.info("Stopped monitoring")
        except Exception as e:
            logging.error(f"Error stopping monitoring: {e}")

    def automation_loop(self):
        """Main automation loop"""
        logging.info(f"Starting automation loop with {self.operation_interval}s intervals...")

        while self.running:
            try:
                self.read_all_values()
                self.random_operation()
                for _ in range(self.operation_interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except KeyboardInterrupt:
                logging.info("\nKeyboard interrupt detected...")
                break
            except Exception as e:
                logging.error(f"Error in automation loop: {e}")
                time.sleep(5)

    def run(self):
        """Main run method for automated operation"""
        logging.info("=" * 60)
        logging.info("AUTOMATED INDUSTRIAL OPC UA CLIENT")
        logging.info("=" * 60)
        logging.info(f"Server URL: {self.server_url}")
        # Use the security manager's actual TLS state
        logging.info(f"Security: {'TLS Enabled' if self.security_manager.use_tls else 'No Security'}")
        logging.info(f"User: {self.username}")
        logging.info(f"Operation Interval: {self.operation_interval}s")
        logging.info(f"Monitoring: {'Enabled' if self.monitoring_enabled else 'Disabled'}")
        logging.info(f"Auto Control: {'Enabled' if self.auto_control_enabled else 'Disabled'}")
        logging.info("=" * 60)

        if not self.connect():
            logging.info("Failed to connect to OPC UA server!")
            return False

        try:
            if self.monitoring_enabled:
                self.start_monitoring()

            self.automation_thread = threading.Thread(target=self.automation_loop)
            self.automation_thread.daemon = True
            self.automation_thread.start()

            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            logging.info("\nShutting down...")
        finally:
            self.shutdown()

        return True

    def disconnect(self):
        """Disconnect from the server"""
        try:
            if self.monitoring:
                self.stop_monitoring()
            self.client.disconnect()
            logging.info("Disconnected from server")
        except Exception as e:
            logging.error(f"Disconnect error: {e}")

    def shutdown(self):
        """Graceful shutdown"""
        logging.info("Initiating graceful shutdown...")
        self.running = False

        if self.automation_thread and self.automation_thread.is_alive():
            logging.info("Waiting for automation thread to finish...")
            self.automation_thread.join(timeout=5)

        self.disconnect()
        logging.info("Shutdown complete")


def main():
    """Main function to run the automated client"""
    logging.info("Starting Automated Industrial OPC UA Client...")

    client = AutomatedIndustrialOPCClient()

    try:
        success = client.run()
        if not success:
            sys.exit(1)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
    