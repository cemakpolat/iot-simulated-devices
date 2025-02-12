import asyncio
import snmp_agent
import psutil
import random
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Function to get CPU usage percentage
def get_cpu_usage():
    return int(psutil.cpu_percent(interval=1))


# Function to get RAM usage percentage
def get_ram_usage():
    memory = psutil.virtual_memory()
    return int(memory.percent)


# Function to get network bytes sent (steady increase)
def get_network_in():
    net_io = psutil.net_io_counters()
    return int(net_io.bytes_recv)


# Function to get network bytes received (steady increase)
def get_network_out():
    net_io = psutil.net_io_counters()
    return int(net_io.bytes_sent)


# Function to simulate packet loss (random value for simulation)
def get_packet_loss():
    return random.randint(0, 100)  # Simulated packet loss percentage


# Function to simulate uptime in time ticks (increases steadily)
def get_uptime():
    return int(time.time())  # Simulated uptime in seconds


# Function to simulate fan speed (random value for simulation)
def get_fan_speed():
    return random.randint(1000, 5000)  # Simulated fan speed in RPM


# Function to simulate temperature (random value for simulation)
def get_temperature():
    return random.randint(30, 80)  # Simulated temperature in Celsius (e.g., CPU temperature)


# Function to simulate humidity (random value for simulation)
def get_humidity():
    return random.randint(20, 80)  # Simulated humidity percentage


# Function to simulate pressure (random value for simulation)
def get_pressure():
    return random.randint(980, 1050)  # Simulated pressure in hPa


# Handler for SNMP requests
async def handler(req: snmp_agent.SNMPRequest) -> snmp_agent.SNMPResponse:
    # Get dynamic values for OIDs
    cpu_usage = get_cpu_usage()
    ram_usage = get_ram_usage()
    network_in = get_network_in()
    network_out = get_network_out()
    packet_loss = get_packet_loss()
    uptime = get_uptime()
    fan_speed = get_fan_speed()
    temperature = get_temperature()
    humidity = get_humidity()
    pressure = get_pressure()

    vbs = [
        # System description OID
        snmp_agent.VariableBinding('1.3.6.1.2.1.1.1.0', snmp_agent.OctetString('Example SNMP Server')),

        # Uptime OID (sysUpTimeInstance)
        snmp_agent.VariableBinding('1.3.6.1.2.1.1.3.0', snmp_agent.Gauge32(uptime)),

        # CPU Usage OID
        snmp_agent.VariableBinding('1.3.6.1.2.1.25.3.3.1.2.1', snmp_agent.Gauge32(cpu_usage)),

        # RAM Usage OID
        snmp_agent.VariableBinding('1.3.6.1.2.1.25.2.3.1.6.1', snmp_agent.Gauge32(ram_usage)),

        # Network In OID (bytes received)
        snmp_agent.VariableBinding('1.3.6.1.2.1.2.2.1.10.1', snmp_agent.Counter32(network_in)),

        # Network Out OID (bytes sent)
        snmp_agent.VariableBinding('1.3.6.1.2.1.2.2.1.16.1', snmp_agent.Counter32(network_out)),

        # Packet Loss OID (simulated value)
        snmp_agent.VariableBinding('1.3.6.1.2.1.2.2.1.17.1', snmp_agent.Gauge32(packet_loss)),

        # Fan Speed OID (simulated RPM value)
        snmp_agent.VariableBinding('1.3.6.1.4.1.12345.1.1', snmp_agent.Gauge32(fan_speed)),

        # Temperature OID (simulated temperature in Celsius)
        snmp_agent.VariableBinding('1.3.6.1.4.1.12345.1.2', snmp_agent.Integer(temperature)),

        # Humidity OID (simulated humidity percentage)
        snmp_agent.VariableBinding('1.3.6.1.4.1.12345.1.3', snmp_agent.Integer(humidity)),

        # Pressure OID (simulated pressure in hPa)
        snmp_agent.VariableBinding('1.3.6.1.4.1.12345.1.4', snmp_agent.Integer(pressure)),

        # Network interface OID (example for 'fxp0')
        snmp_agent.VariableBinding('1.3.6.1.2.1.2.2.1.2.1', snmp_agent.OctetString('eth0')),

        # Network status OID (example value)
        snmp_agent.VariableBinding('1.3.6.1.2.1.2.2.1.5.1', snmp_agent.Gauge32(1))  # Interface is "up"
    ]

    # Process the request and create a response
    res_vbs = snmp_agent.utils.handle_request(req=req, vbs=vbs)
    res = req.create_response(res_vbs)
    return res


snmp_data = {
    '1.3.6.1.2.1.1.1.0': 'System',  # sysDescr (Description of the system)
    '1.3.6.1.2.1.2.2.1.10.1': 1000,  # ifInOctets (bytes received on interface)
}


# Main function to start the SNMP server
async def main():
    try:
        # Create and start the SNMP server
        sv = snmp_agent.Server(handler=handler, host='0.0.0.0', port=11611)
        await sv.start()
        while True:
            await asyncio.sleep(3600)  # Keep server running indefinitely
    except Exception as err:
        logging.error(f"Unexpected error occured {err}")


# Run the SNMP server
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
