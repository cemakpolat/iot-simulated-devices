# opcua_client.py - Enhanced with environment variables
import os
import time
from opcua import Client

class IndustrialOPCClient:
    def __init__(self):
        # Get configuration from environment variables
        self.server_host = os.getenv('OPC_SERVER_HOST', 'localhost')
        self.server_port = int(os.getenv('OPC_SERVER_PORT', '4840'))
        self.endpoint_path = os.getenv('OPC_ENDPOINT_PATH', '/freeopcua/server/')
        self.username = os.getenv('OPC_USERNAME', 'admin')
        self.password = os.getenv('OPC_PASSWORD', 'admin')
        self.monitor_interval = float(os.getenv('MONITOR_INTERVAL', '5.0'))
        self.monitor_duration = int(os.getenv('MONITOR_DURATION', '300'))  # 5 minutes default
        
        server_url = f"opc.tcp://{self.server_host}:{self.server_port}{self.endpoint_path}"
        print(f"Server URL: {server_url}")
        self.client = Client(server_url)
        
        # if self.username and self.password:
        #     self.client.set_user(self.username)
        #     self.client.set_password(self.password)
            
        print(f"OPC UA Client configured:")
        print(f"  Server: {server_url}")
        print(f"  Monitor Interval: {self.monitor_interval}s")
        print(f"  Monitor Duration: {self.monitor_duration}s")
        
    def connect(self):
        """Connect to the OPC UA server"""
        try:
            self.client.connect()
            print("Connected to OPC UA server")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the OPC UA server"""
        try:
            self.client.disconnect()
            print("Disconnected from server")
        except Exception as e:
            print(f"Error during disconnection: {e}")
    
    def read_factory_data(self):
        """Read all factory data and return as dictionary"""
        try:
            # Read temperature sensors
            temp1 = self.client.get_node("ns=2;i=10").get_value()
            temp2 = self.client.get_node("ns=2;i=11").get_value()
            temp3 = self.client.get_node("ns=2;i=12").get_value()
            
            # Read motor data
            motor1_speed = self.client.get_node("ns=2;i=20").get_value()
            motor1_status = self.client.get_node("ns=2;i=21").get_value()
            motor2_speed = self.client.get_node("ns=2;i=22").get_value()
            motor2_status = self.client.get_node("ns=2;i=23").get_value()
            
            # Read system info
            uptime = self.client.get_node("ns=2;i=30").get_value()
            production = self.client.get_node("ns=2;i=31").get_value()
            
            data = {
                'timestamp': time.time(),
                'temp_sensor_1': temp1,
                'temp_sensor_2': temp2,
                'temp_sensor_3': temp3,
                'motor1_speed': motor1_speed,
                'motor1_status': motor1_status,
                'motor2_speed': motor2_speed,
                'motor2_status': motor2_status,
                'uptime': uptime,
                'total_production': production
            }
            
            return data
            
        except Exception as e:
            print(f"Error reading data: {e}")
            return None
    
    def display_factory_data(self, data):
        """Display factory data in a formatted way"""
        if not data:
            return
            
        print("\n" + "="*50)
        print("FACTORY STATUS REPORT")
        print("="*50)
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['timestamp']))}")
        print(f"Temperature Sensors:")
        print(f"  Sensor 1: {data['temp_sensor_1']}°C")
        print(f"  Sensor 2: {data['temp_sensor_2']}°C")
        print(f"  Sensor 3: {data['temp_sensor_3']}°C")
        print(f"\nMotor Status:")
        print(f"  Motor 1: {'RUNNING' if data['motor1_status'] else 'STOPPED'} at {data['motor1_speed']} RPM")
        print(f"  Motor 2: {'RUNNING' if data['motor2_status'] else 'STOPPED'} at {data['motor2_speed']} RPM")
        print(f"\nSystem Information:")
        print(f"  Uptime: {data['uptime']} cycles")
        print(f"  Total Production: {data['total_production']} units")
        print("="*50)
    
    def monitor_continuous(self):
        """Monitor factory data continuously"""
        print(f"Starting continuous monitoring for {self.monitor_duration} seconds...")
        start_time = time.time()
        
        while time.time() - start_time < self.monitor_duration:
            data = self.read_factory_data()
            if data:
                self.display_factory_data(data)
            time.sleep(self.monitor_interval)
            
        print("Monitoring completed.")

def main():
    client = IndustrialOPCClient()
    
    if not client.connect():
        return
    
    try:
        client.monitor_continuous()
        
    except KeyboardInterrupt:
        print("\nClient stopped by user")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()