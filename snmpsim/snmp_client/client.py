from pysnmp.hlapi.v3arch.asyncio import *
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

COMMUNITY_STRING = 'public'


def get_env_variable(name, default, cast_type):
    """Retrieve environment variable with validation."""
    value = os.getenv(name, str(default))
    try:
        return cast_type(value) if value.lower() != "none" else None
    except ValueError:
        logging.warning(f"Invalid {name} value: {value}, using default: {default}")
        return default


RUNS = get_env_variable("RUNS", 10, int)
REQUEST_INTERVAL = get_env_variable("REQUEST_INTERVAL", 3, int)
SNMP_AGENT_HOST = get_env_variable("SNMP_AGENT_HOST", "localhost", str)
SNMP_AGENT_PORT = get_env_variable("SNMP_AGENT_PORT", 11611, int)

if REQUEST_INTERVAL <= 0:
    logging.warning(f"REQUEST_INTERVAL must be a positive integer, using default: {3}")
    REQUEST_INTERVAL = 3

OID_CONFIG = {
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


async def snmp_get(oid: str):
    udp_transport = await UdpTransportTarget.create((SNMP_AGENT_HOST, SNMP_AGENT_PORT))

    iterator = get_cmd(
        SnmpEngine(),
        CommunityData(COMMUNITY_STRING, mpModel=0),
        udp_transport,
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )
    (error_indication, error_status, error_index, var_binds) = await iterator

    if error_indication:
        logging.error(f"SNMP GET error: {error_indication}")
        return None
    elif error_status:
        logging.error(f"SNMP GET error status: {error_status.prettyPrint()}")
        return None
    else:
        for var_bind in var_binds:
            return var_bind.prettyPrint().split(' = ')[1]


async def main():
    logging.info("Starting SNMP Client...")
    count = 0
    while RUNS is None or count < RUNS:
        tasks = [snmp_get(oid) for oid in OID_CONFIG.values()]
        results = await asyncio.gather(*tasks)

        for key, value in zip(OID_CONFIG.keys(), results):
            if value is not None:
                logging.info(f"{key}: {value}")

        count += 1
        logging.info(f"Run {count}/{RUNS if RUNS else '∞'} completed.")
        await asyncio.sleep(REQUEST_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
