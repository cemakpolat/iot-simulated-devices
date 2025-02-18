from pymodbus.client import ModbusTcpClient
from pymodbus import ModbusException
import time
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s")

server_host = os.getenv("MODBUS_SERVER_IP", "localhost")  # Default to "server" (Docker service name)
server_port = int(os.getenv("MODBUS_SERVER_PORT", 5026))  # Default to 50001
update_frequency = int(os.getenv("UPDATE_FREQUENCY", 10))  # Default to 50001

logging.info(f"{server_host},{server_port}")


def run_modbus_client():
    client = None
    try:
        # Connect to the Modbus TCP server
        client = ModbusTcpClient(host=server_host, port=server_port)

        if not client.connect():
            print("Failed to connect to Modbus server")
            return

        while True:
            # Read holding registers (address 0, count 10) - Current temperatures
            response = client.read_holding_registers(address=0, count=9, slave=1)
            if response.isError():
                logging.info(f"Error reading holding registers: {response}")
            else:
                logging.info(f"Current Temperatures: {response.registers}")

            # Read input registers (address 0, count 10) - Historical averages
            response = client.read_input_registers(address=0, count=9, slave=1)
            if response.isError():
                logging.info(f"Error reading input registers: {response}")
            else:
                logging.info(f"Historical Average Temperatures: {response.registers}")

            # Read coils (address 0, count 10) - Cooling system status
            response = client.read_coils(address=0, count=9, slave=1)
            if response.isError():
                logging.info(f"Error reading coils: {response}")
            else:
                logging.info(f"Cooling System Status: {response.bits}")

            # Read discrete inputs (address 0, count 10) - Alarm statuses
            response = client.read_discrete_inputs(address=0, count=9, slave=1)
            if response.isError():
                logging.info(f"Error reading discrete inputs: {response}")
            else:
                logging.info(f"Alarm Statuses: {response.bits}")

            # Wait for 10 seconds before reading again
            time.sleep(update_frequency)
    except ModbusException as err:
        logging.error(f"Modbus exception is occurred {err}")
    except Exception as err:
        logging.error(f"An unknown error occurred {err}")

    finally:
        # Close the connection
        if client:
            client.close()


if __name__ == "__main__":
    run_modbus_client()
