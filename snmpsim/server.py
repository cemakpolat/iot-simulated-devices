import asyncio
import snmp_agent
import psutil
import random
import time
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configuration for OIDs and other settings
OID_CONFIG: Dict[str, Any] = {
    'system_description': '1.3.6.1.2.1.1.1.0',
    'uptime': '1.3.6.1.2.1.1.3.0',
    'cpu_usage': '1.3.6.1.2.1.25.3.3.1.2.1',
    'ram_usage': '1.3.6.1.2.1.25.2.3.1.6.1',
    'network_in': '1.3.6.1.2.1.2.2.1.10.1',
    'network_out': '1.3.6.1.2.1.2.2.1.16.1',
    'packet_loss': '1.3.6.1.2.1.2.2.1.17.1',
    'fan_speed': '1.3.6.1.4.1.12345.1.1',
    'temperature': '1.3.6.1.4.1.12345.1.2',
    'humidity': '1.3.6.1.4.1.12345.1.3',
    'pressure': '1.3.6.1.4.1.12345.1.4',
    'network_interface': '1.3.6.1.2.1.2.2.1.2.1',
    'network_status': '1.3.6.1.2.1.2.2.1.5.1',
}


def get_cpu_usage() -> int:
    return int(psutil.cpu_percent(interval=0.1))


def get_ram_usage() -> int:
    memory = psutil.virtual_memory()
    return int(memory.percent)


def get_network_in() -> int:
    net_io = psutil.net_io_counters()
    return int(net_io.bytes_recv)


def get_network_out() -> int:
    net_io = psutil.net_io_counters()
    return int(net_io.bytes_sent)


def get_packet_loss() -> int:
    return random.randint(0, 100)  # Simulated packet loss percentage


def get_uptime() -> int:
    return int(time.time())  # Simulated uptime in seconds


def get_fan_speed() -> int:
    return random.randint(1000, 5000)  # Simulated fan speed in RPM


def get_temperature() -> int:
    return random.randint(30, 80)  # Simulated temperature in Celsius


def get_humidity() -> int:
    return random.randint(20, 80)  # Simulated humidity percentage


def get_pressure() -> int:
    return random.randint(980, 1050)  # Simulated pressure in hPa


async def handler(req: snmp_agent.SNMPRequest) -> snmp_agent.SNMPResponse:
    try:
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
            snmp_agent.VariableBinding(OID_CONFIG['system_description'], snmp_agent.OctetString('Example SNMP Server')),
            snmp_agent.VariableBinding(OID_CONFIG['uptime'], snmp_agent.Gauge32(uptime)),
            snmp_agent.VariableBinding(OID_CONFIG['cpu_usage'], snmp_agent.Gauge32(cpu_usage)),
            snmp_agent.VariableBinding(OID_CONFIG['ram_usage'], snmp_agent.Gauge32(ram_usage)),
            snmp_agent.VariableBinding(OID_CONFIG['network_in'], snmp_agent.Counter32(network_in)),
            snmp_agent.VariableBinding(OID_CONFIG['network_out'], snmp_agent.Counter32(network_out)),
            snmp_agent.VariableBinding(OID_CONFIG['packet_loss'], snmp_agent.Gauge32(packet_loss)),
            snmp_agent.VariableBinding(OID_CONFIG['fan_speed'], snmp_agent.Gauge32(fan_speed)),
            snmp_agent.VariableBinding(OID_CONFIG['temperature'], snmp_agent.Integer(temperature)),
            snmp_agent.VariableBinding(OID_CONFIG['humidity'], snmp_agent.Integer(humidity)),
            snmp_agent.VariableBinding(OID_CONFIG['pressure'], snmp_agent.Integer(pressure)),
            snmp_agent.VariableBinding(OID_CONFIG['network_interface'], snmp_agent.OctetString('eth0')),
            snmp_agent.VariableBinding(OID_CONFIG['network_status'], snmp_agent.Gauge32(1)),  # Interface is "up"
        ]

        res_vbs = snmp_agent.utils.handle_request(req=req, vbs=vbs)
        res = req.create_response(res_vbs)
        return res
    except Exception as err:
        logging.error(f"Error handling SNMP request:{err}")
        return req.create_response(variable_bindings=[], error_status=5)  # status=5 corresponds to genErr


async def main():
    try:
        sv = snmp_agent.Server(handler=handler, host='0.0.0.0', port=11611)
        await sv.start()
        logging.info("SNMP server started on 0.0.0.0:11611")
        while True:
            await asyncio.sleep(3600)  # Keep server running indefinitely
    except Exception as err:
        logging.error(f"Unexpected error occurred: {err}")
    finally:
        logging.info("SNMP server stopped")


if __name__ == "__main__":
    asyncio.run(main())
