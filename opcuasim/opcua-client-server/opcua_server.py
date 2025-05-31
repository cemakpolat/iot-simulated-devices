# opcua_server.py - Enhanced with environment variables
import os
import time
import random
from threading import Thread
from opcua import Server, ua

class IndustrialOPCServer:
    def __init__(self):
        # Get configuration from environment variables
        self.host = os.getenv('OPC_HOST', 'localhost')
        self.port = int(os.getenv('OPC_PORT', '4840'))
        self.endpoint_path = os.getenv('OPC_ENDPOINT_PATH', '/freeopcua/server/')
        self.server_name = os.getenv('OPC_SERVER_NAME', 'Industrial Simulation Server')
        self.update_interval = float(os.getenv('UPDATE_INTERVAL', '2.0'))
        
        # Temperature simulation parameters
        self.temp_base_1 = float(os.getenv('TEMP_BASE_1', '20.0'))
        self.temp_base_2 = float(os.getenv('TEMP_BASE_2', '25.0'))
        self.temp_base_3 = float(os.getenv('TEMP_BASE_3', '22.0'))
        self.temp_variation = float(os.getenv('TEMP_VARIATION', '3.0'))
        
        # Initialize the server
        self.server = Server()
        endpoint_url = f"opc.tcp://{self.host}:{self.port}{self.endpoint_path}"
        self.server.set_endpoint(endpoint_url)
        self.server.set_server_name(self.server_name)
        
        # Set up the address space
        self.setup_address_space()
        
        # Variables for simulation
        self.running = False
        self.simulation_thread = None
        
        print(f"OPC UA Server configured:")
        print(f"  Endpoint: {endpoint_url}")
        print(f"  Update Interval: {self.update_interval}s")
        print(f"  Temperature Bases: {self.temp_base_1}°C, {self.temp_base_2}°C, {self.temp_base_3}°C")
        
    def setup_address_space(self):
        # Get the root objects node
        objects = self.server.get_objects_node()
        
        # Create our main factory object
        self.factory = objects.add_object("ns=2;i=1", "Factory")
        
        # Create production line object
        self.production_line = self.factory.add_object("ns=2;i=2", "ProductionLine1")
        
        # Add temperature sensors
        self.temp_sensors = self.production_line.add_object("ns=2;i=3", "TemperatureSensors")
        
        # Create individual temperature sensor variables
        self.temp_sensor_1 = self.temp_sensors.add_variable("ns=2;i=10", "Sensor1_Temperature", self.temp_base_1)
        self.temp_sensor_2 = self.temp_sensors.add_variable("ns=2;i=11", "Sensor2_Temperature", self.temp_base_2)
        self.temp_sensor_3 = self.temp_sensors.add_variable("ns=2;i=12", "Sensor3_Temperature", self.temp_base_3)
        
        # Make temperature sensors writable
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
        
        # Make motor controls writable
        self.motor1_speed.set_writable()
        self.motor1_status.set_writable()
        self.motor2_speed.set_writable()
        self.motor2_status.set_writable()
        
        # Add system information
        self.system_info = self.factory.add_object("ns=2;i=5", "SystemInfo")
        self.uptime = self.system_info.add_variable("ns=2;i=30", "Uptime", 0)
        self.total_production = self.system_info.add_variable("ns=2;i=31", "TotalProduction", 0)
        
    def simulate_industrial_data(self):
        """Simulate realistic industrial data changes"""
        uptime_counter = 0
        production_counter = 0
        
        while self.running:
            try:
                # Simulate temperature fluctuations
                base_temp_1 = self.temp_base_1 + random.uniform(-self.temp_variation/2, self.temp_variation/2)
                base_temp_2 = self.temp_base_2 + random.uniform(-self.temp_variation/2, self.temp_variation/2)
                base_temp_3 = self.temp_base_3 + random.uniform(-self.temp_variation/2, self.temp_variation/2)
                
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
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                print(f"Simulation error: {e}")
                break
    
    def start(self):
        """Start the OPC UA server"""
        try:
            self.server.start()
            endpoint_url = f"opc.tcp://{self.host}:{self.port}{self.endpoint_path}"
            print(f"OPC UA Server started at {endpoint_url}")
            print("Server is running. Press Ctrl+C to stop.")
            
            # Start simulation thread
            self.running = True
            self.simulation_thread = Thread(target=self.simulate_industrial_data)
            self.simulation_thread.daemon = True
            self.simulation_thread.start()
            
        except Exception as e:
            print(f"Failed to start server: {e}")
    
    def stop(self):
        """Stop the OPC UA server"""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=5)
        self.server.stop()
        print("Server stopped.")

if __name__ == "__main__":
    server = IndustrialOPCServer()
    
    try:
        server.start()
        # Keep the server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()