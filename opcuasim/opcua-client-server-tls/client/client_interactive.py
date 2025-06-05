import time
import os
from opcua import Client, ua
import threading
from datetime import datetime


class SecureIndustrialOPCClient:
    def __init__(self, server_url=None, use_tls=True, username=None, password=None):
        """
        Initialize the OPC UA client

        Args:
            server_url: Server endpoint URL
            use_tls: Whether to use TLS security
            username: Username for authentication
            password: Password for authentication
        """
        # Default server URLs
        if server_url is None:
            if use_tls:
                server_url = "opc.tcp://localhost:4843/freeopcua/server/"
            else:
                server_url = "opc.tcp://localhost:4840/freeopcua/server/"

        self.server_url = server_url
        self.use_tls = use_tls
        self.username = username
        self.password = password

        # Initialize client
        self.client = Client(server_url)

        # Node references (will be populated after connection)
        self.nodes = {}

        # Subscription variables
        self.subscription = None
        self.monitoring = False

    def setup_security(self):
        """Configure client security settings"""
        if not self.use_tls:
            return

        try:
            # Check if certificates exist
            client_cert_path = "certificates/client_certificate.pem"
            client_key_path = "certificates/client_private_key.pem"

            if os.path.exists(client_cert_path) and os.path.exists(client_key_path):
                # Set security policy with certificates
                policy = f"Basic256Sha256,SignAndEncrypt,{client_cert_path},{client_key_path}"
                self.client.set_security_string(policy)
                print("Client TLS security configured with certificates")
            else:
                print("Client certificates not found")
                # Try to connect with basic security policy but no certificates
                try:
                    self.client.set_security_string("Basic256Sha256,Sign")
                    print("Using TLS without client certificates")
                except:
                    print("TLS setup failed, falling back to no security")
                    self.use_tls = False

        except Exception as e:
            print(f"Security setup failed: {e}")
            print("Falling back to no security")
            self.use_tls = False

    def setup_authentication(self):
        """Configure user authentication"""
        if self.username and self.password:
            try:
                self.client.set_user(self.username)
                self.client.set_password(self.password)
                print(f"Authentication configured for user: {self.username}")
            except Exception as e:
                print(f"Authentication setup failed: {e}")

    def connect(self):
        """Connect to the OPC UA server"""
        try:
            # Setup security and authentication
            if self.use_tls:
                self.setup_security()
            self.setup_authentication()

            # Connect to server
            self.client.connect()
            print(f"Connected to server: {self.server_url}")

            # Get server info
            try:
                server_node = self.client.get_server_node()
                server_name = server_node.get_display_name()
                print(f"Server name: {server_name}")
            except:
                print("Server connected successfully")

            # Discover and cache node references
            self.discover_nodes()

            return True

        except Exception as e:
            print(f"Connection failed: {e}")
            # Try to provide more specific error information
            if "BadSecurityChecksFailed" in str(e):
                print("Security validation failed - check certificates or try without TLS")
            elif "BadUserAccessDenied" in str(e):
                print("Authentication failed - check username/password")
            elif "ConnectionRefusedError" in str(e):
                print("Server not running or wrong port")
            return False

    def discover_nodes(self):
        """Discover and cache important server nodes using exact NodeIDs"""
        try:
            # Use known NodeIDs instead of relying on browse names
            self.nodes['temp_sensor_1'] = self.client.get_node("ns=2;i=10")  # Sensor1_Temperature
            self.nodes['temp_sensor_2'] = self.client.get_node("ns=2;i=11")  # Sensor2_Temperature
            self.nodes['temp_sensor_3'] = self.client.get_node("ns=2;i=12")  # Sensor3_Temperature

            self.nodes['motor1_speed'] = self.client.get_node("ns=2;i=20")  # Motor1_Speed
            self.nodes['motor1_status'] = self.client.get_node("ns=2;i=21")  # Motor1_Status
            self.nodes['motor2_speed'] = self.client.get_node("ns=2;i=22")  # Motor2_Speed
            self.nodes['motor2_status'] = self.client.get_node("ns=2;i=23")  # Motor2_Status

            self.nodes['uptime'] = self.client.get_node("ns=2;i=30")  # Uptime
            self.nodes['total_production'] = self.client.get_node("ns=2;i=31")  # TotalProduction

            self.nodes['tls_enabled'] = self.client.get_node("ns=2;i=40")  # TLS_Enabled
            self.nodes['connection_count'] = self.client.get_node("ns=2;i=41")  # Active_Connections

            print("Node discovery completed successfully")
        except Exception as e:
            print(f"Node discovery failed: {e}")
            print("Make sure the server is running and the NodeIDs match.")

    def read_all_values(self):
        """Read all current values from the server"""
        print("\n" + "=" * 60)
        print(f"INDUSTRIAL SYSTEM STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        try:
            # Temperature readings
            print("\nTEMPERATURE SENSORS:")
            if 'temp_sensor_1' in self.nodes:
                temp1 = self.nodes['temp_sensor_1'].get_value()
                temp2 = self.nodes['temp_sensor_2'].get_value()
                temp3 = self.nodes['temp_sensor_3'].get_value()
                print(f"  Sensor 1: {temp1}°C")
                print(f"  Sensor 2: {temp2}°C")
                print(f"  Sensor 3: {temp3}°C")
            else:
                print("  Temperature sensors not available")

            # Motor status
            print("\nMOTOR STATUS:")
            if 'motor1_speed' in self.nodes:
                motor1_speed = self.nodes['motor1_speed'].get_value()
                motor1_status = self.nodes['motor1_status'].get_value()
                motor2_speed = self.nodes['motor2_speed'].get_value()
                motor2_status = self.nodes['motor2_status'].get_value()

                print(f"  Motor 1: {'RUNNING' if motor1_status else 'STOPPED'} - Speed: {motor1_speed} RPM")
                print(f"  Motor 2: {'RUNNING' if motor2_status else 'STOPPED'} - Speed: {motor2_speed} RPM")
            else:
                print("  Motor data not available")

            # System information
            print("\nSYSTEM INFORMATION:")
            if 'uptime' in self.nodes:
                uptime = self.nodes['uptime'].get_value()
                production = self.nodes['total_production'].get_value()
                tls_enabled = self.nodes['tls_enabled'].get_value()
                connections = self.nodes['connection_count'].get_value()

                print(f"  Uptime: {uptime} cycles")
                print(f"  Total Production: {production} units")
                print(f"  TLS Security: {'ENABLED' if tls_enabled else 'DISABLED'}")
                print(f"  Active Connections: {connections}")
            else:
                print("  System information not available")

        except Exception as e:
            print(f"Error reading values: {e}")

    def control_motor(self, motor_num, status, speed=None):
        """
        Control motor operation

        Args:
            motor_num: Motor number (1 or 2)
            status: True to start, False to stop
            speed: Motor speed (optional)
        """
        try:
            if motor_num == 1 and 'motor1_status' in self.nodes:
                self.nodes['motor1_status'].set_value(status)
                if speed is not None:
                    self.nodes['motor1_speed'].set_value(speed)
                print(f"Motor 1 {'started' if status else 'stopped'}")
                if speed:
                    print(f"Motor 1 speed set to {speed} RPM")

            elif motor_num == 2 and 'motor2_status' in self.nodes:
                self.nodes['motor2_status'].set_value(status)
                if speed is not None:
                    self.nodes['motor2_speed'].set_value(speed)
                print(f"Motor 2 {'started' if status else 'stopped'}")
                if speed:
                    print(f"Motor 2 speed set to {speed} RPM")
            else:
                print(f"Motor {motor_num} nodes not available")

        except Exception as e:
            print(f"Motor control failed: {e}")
            if "BadUserAccessDenied" in str(e):
                print("Access denied - Motor control requires engineer+ privileges")
            elif "BadNotWritable" in str(e):
                print("Node is not writable")

    def set_temperature_setpoint(self, sensor_num, temperature):
        """
        Set temperature setpoint (if writable)

        Args:
            sensor_num: Sensor number (1, 2, or 3)
            temperature: Target temperature
        """
        try:
            node_name = f'temp_sensor_{sensor_num}'
            if node_name in self.nodes:
                self.nodes[node_name].set_value(temperature)
                print(f"Temperature sensor {sensor_num} setpoint set to {temperature}°C")
            else:
                print(f"Temperature sensor {sensor_num} not available")
        except Exception as e:
            print(f"Temperature setpoint failed: {e}")
            if "BadUserAccessDenied" in str(e):
                print("Access denied - Temperature control requires engineer+ privileges")

    class DataChangeHandler:
        """Handler for subscription data changes"""

        def __init__(self, client_instance):
            self.client = client_instance

        def datachange_notification(self, node, val, data):
            """Handle data change notifications"""
            try:
                node_id = node.nodeid.Identifier
                timestamp = datetime.now().strftime('%H:%M:%S')

                # Map node IDs to readable names
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

                name = node_names.get(node_id, f"Node {node_id}")

                # Format the value based on type
                if isinstance(val, bool):
                    val_str = "ON" if val else "OFF"
                elif isinstance(val, float):
                    val_str = f"{val:.2f}"
                else:
                    val_str = str(val)

                print(f"[{timestamp}] {name}: {val_str}")

            except Exception as e:
                print(f"Error in data change handler: {e}")

    def start_monitoring(self):
        """Start monitoring data changes via subscription"""
        try:
            if not self.nodes:
                print("No nodes discovered - cannot start monitoring")
                return

            # Create subscription
            self.subscription = self.client.create_subscription(1000, self.DataChangeHandler(self))

            # Collect available nodes for subscription
            available_nodes = []

            # Temperature sensors
            for i in range(1, 4):
                node_name = f'temp_sensor_{i}'
                if node_name in self.nodes:
                    available_nodes.append(self.nodes[node_name])

            # Motor data
            motor_node_names = ['motor1_speed', 'motor1_status', 'motor2_speed', 'motor2_status']
            for node_name in motor_node_names:
                if node_name in self.nodes:
                    available_nodes.append(self.nodes[node_name])

            # System data
            system_node_names = ['uptime', 'total_production']
            for node_name in system_node_names:
                if node_name in self.nodes:
                    available_nodes.append(self.nodes[node_name])

            if available_nodes:
                # Subscribe to data changes
                handles = self.subscription.subscribe_data_change(available_nodes)
                self.monitoring = True
                print(f"Started monitoring {len(available_nodes)} nodes...")
                print("Monitoring data changes (Press Enter to return to menu)")
            else:
                print("No nodes available for monitoring")

        except Exception as e:
            print(f"Monitoring setup failed: {e}")

    def stop_monitoring(self):
        """Stop monitoring data changes"""
        try:
            if self.subscription:
                self.subscription.delete()
                self.subscription = None
            self.monitoring = False
            print("Stopped monitoring")
        except Exception as e:
            print(f"Error stopping monitoring: {e}")

    def disconnect(self):
        """Disconnect from the server"""
        try:
            if self.monitoring:
                self.stop_monitoring()
            self.client.disconnect()
            print("Disconnected from server")
        except Exception as e:
            print(f"Disconnect error: {e}")

    def interactive_menu(self):
        """Interactive menu for client operations"""
        while True:
            print("\n" + "=" * 50)
            print("INDUSTRIAL OPC UA CLIENT MENU")
            print("=" * 50)
            print("1. Read All Values")
            print("2. Start Motor 1")
            print("3. Stop Motor 1")
            print("4. Start Motor 2")
            print("5. Stop Motor 2")
            print("6. Set Motor Speed")
            print("7. Set Temperature Setpoint")
            print("8. Start Data Monitoring")
            print("9. Stop Data Monitoring")
            print("0. Exit")
            print("-" * 50)

            choice = input("Enter your choice: ").strip()

            if choice == '1':
                self.read_all_values()

            elif choice == '2':
                speed = input("Enter speed (or press Enter for default 100): ").strip()
                speed = int(speed) if speed else 100
                self.control_motor(1, True, speed)

            elif choice == '3':
                self.control_motor(1, False)

            elif choice == '4':
                speed = input("Enter speed (or press Enter for default 100): ").strip()
                speed = int(speed) if speed else 100
                self.control_motor(2, True, speed)

            elif choice == '5':
                self.control_motor(2, False)

            elif choice == '6':
                try:
                    motor = int(input("Enter motor number (1 or 2): "))
                    speed = int(input("Enter speed: "))
                    if motor in [1, 2]:
                        node_name = f'motor{motor}_speed'
                        if node_name in self.nodes:
                            self.nodes[node_name].set_value(speed)
                            print(f"Motor {motor} speed set to {speed}")
                        else:
                            print(f"Motor {motor} not available")
                except ValueError:
                    print("Invalid input")
                except Exception as e:
                    print(f"Error setting speed: {e}")

            elif choice == '7':
                try:
                    sensor = int(input("Enter sensor number (1, 2, or 3): "))
                    temp = float(input("Enter temperature: "))
                    if sensor in [1, 2, 3]:
                        self.set_temperature_setpoint(sensor, temp)
                except ValueError:
                    print("Invalid input")

            elif choice == '8':
                if not self.monitoring:
                    self.start_monitoring()
                    if self.monitoring:
                        input()  # Wait for user to press Enter
                else:
                    print("Already monitoring")

            elif choice == '9':
                self.stop_monitoring()

            elif choice == '0':
                break

            else:
                print("Invalid choice")


def test_connection(url, use_auth=False, username=None, password=None):
    """Test basic connectivity to server"""
    try:
        test_client = Client(url)
        if use_auth and username and password:
            test_client.set_user(username)
            test_client.set_password(password)

        test_client.connect()
        print(f"✓ Successfully connected to {url}")
        test_client.disconnect()
        return True
    except Exception as e:
        print(f"✗ Failed to connect to {url}: {e}")
        return False


def main():
    """Main function to run the client"""
    print("Industrial OPC UA Client")
    print("=" * 40)

    # Configuration
    secure_url = "opc.tcp://localhost:4843/freeopcua/server/"
    non_secure_url = "opc.tcp://localhost:4840/freeopcua/server/"

    print("\nTesting server connectivity...")

    # Test non-secure first (more likely to work)
    non_secure_available = test_connection(non_secure_url)
    secure_available = test_connection(secure_url)

    if not secure_available and not non_secure_available:
        print("\n❌ Cannot connect to server on either port!")
        print("Please check:")
        print("1. Is the OPC UA server running?")
        print("2. Run the server script first")
        print("3. Check firewall settings")
        return

    # Choose server based on availability
    if non_secure_available:
        print(f"\n✓ Non-secure server available at {non_secure_url}")
        use_tls = False
        server_url = non_secure_url
    elif secure_available:
        print(f"\n✓ Secure server available at {secure_url}")
        use_tls = True
        server_url = secure_url

    # Allow user to choose if both available
    if secure_available and non_secure_available:
        user_choice = input("Use TLS security? (y/n) [n]: ").strip().lower()
        if user_choice == 'y':
            use_tls = True
            server_url = secure_url

    # Get authentication details
    print("\nAuthentication options:")
    print("1. operator (op123) - Read access")
    print("2. engineer (eng456) - Read + Motor control")
    print("3. admin (admin789) - Full access")
    print("4. none - No authentication")

    auth_choice = input("Choose authentication [1]: ").strip()

    user_configs = {
        "1": ("operator", "op123"),
        "2": ("engineer", "eng456"),
        "3": ("admin", "admin789"),
        "4": (None, None)
    }

    username, password = user_configs.get(auth_choice, ("operator", "op123"))

    print(f"\nConnection Configuration:")
    print(f"URL: {server_url}")
    print(f"Security: {'TLS Enabled' if use_tls else 'No Security'}")
    print(f"User: {username if username else 'Anonymous'}")

    # Create and connect client
    client = SecureIndustrialOPCClient(
        server_url=server_url,
        use_tls=use_tls,
        username=username,
        password=password
    )

    if client.connect():
        try:
            # Show initial status
            client.read_all_values()

            # Start interactive menu
            client.interactive_menu()

        except KeyboardInterrupt:
            print("\nShutting down client...")
        finally:
            client.disconnect()
    else:
        print("\nConnection failed!")
        print("\nTroubleshooting steps:")
        print("1. Make sure the server is running first")
        print("2. Try running the server without TLS: python server.py --no-tls")
        print("3. Check server logs for error messages")
        print("4. Verify server is listening on the expected port")


if __name__ == "__main__":
    main()