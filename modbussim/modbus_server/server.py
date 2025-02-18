import random
import logging
import time
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server.async_io import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.exceptions import ConnectionException

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s")
log = logging.getLogger(__name__)

# Constants
NUM_SENSORS = 10
BLOCK_SIZE = 100
MODBUS_PORT = 5026
MODBUS_HOST = "0.0.0.0"
RETRY_DELAY = 5  # seconds
MAX_RETRIES = 3

# Initialize baseline data
current_temperatures = [random.randint(20, 30) for _ in range(NUM_SENSORS)]  # Baseline temperatures
historical_averages = [random.randint(20, 30) for _ in range(NUM_SENSORS)]  # Historical averages

# Create initial data blocks
holding_registers_data = current_temperatures + [0] * (BLOCK_SIZE - NUM_SENSORS)
input_registers_data = historical_averages + [0] * (BLOCK_SIZE - NUM_SENSORS)
coils_data = [temp > 30 for temp in current_temperatures] + [False] * (BLOCK_SIZE - NUM_SENSORS)
discrete_inputs_data = [temp > 35 for temp in current_temperatures] + [False] * (BLOCK_SIZE - NUM_SENSORS)

# Create data blocks
holding_registers = ModbusSequentialDataBlock(0, holding_registers_data)
input_registers = ModbusSequentialDataBlock(0, input_registers_data)
coils = ModbusSequentialDataBlock(0, coils_data)
discrete_inputs = ModbusSequentialDataBlock(0, discrete_inputs_data)

# Define the Modbus slave context
slave_context = ModbusSlaveContext(
    di=discrete_inputs,
    co=coils,
    hr=holding_registers,
    ir=input_registers
)
context = ModbusServerContext(slaves=slave_context, single=True)


def simulate_temperature_data(current_temps, historical_avg):
    """
    Simulate realistic temperature changes and update cooling/alarm statuses.
    Also updates the historical averages using a moving average.
    """
    try:
        updated_temperatures = [round(temp + random.uniform(-1, 1)) for temp in current_temps]
        cooling_status = [temp > 30 for temp in updated_temperatures]
        alarm_statuses = [temp > 35 for temp in updated_temperatures]
        print(updated_temperatures, cooling_status, alarm_statuses)
        # Update historical averages with a moving average
        alpha = 0.1  # Smoothing factor (adjust as needed)
        updated_historical_avg = [
            round(alpha * new_temp + (1 - alpha) * avg)
            for new_temp, avg in zip(updated_temperatures, historical_avg)
        ]

        return updated_temperatures, updated_historical_avg, cooling_status, alarm_statuses

    except Exception as e:
        log.error(f"Error simulating temperature data: {e}", exc_info=True)  # Include traceback
        return current_temps, historical_avg, [False] * NUM_SENSORS, [False] * NUM_SENSORS  # Return default values


def update_registers():
    """
    Periodically update registers to simulate changing data.
    """
    log.info("Updating Modbus registers...")

    global current_temperatures, historical_averages

    try:
        current_temperatures, historical_averages, cooling_status, alarm_statuses = simulate_temperature_data(
            current_temperatures, historical_averages
        )
        # Update the data blocks
        holding_registers.setValues(0, current_temperatures)
        input_registers.setValues(0, historical_averages)
        coils.setValues(0, cooling_status)
        discrete_inputs.setValues(0, alarm_statuses)

        # Print the updated data for debugging
        log.debug(f"Updated Current Temperatures: {current_temperatures}")
        log.debug(f"Updated Cooling Status: {cooling_status}")
        log.debug(f"Updated Historical Status: {historical_averages}")
        log.debug(f"Updated Alarm Statuses: {alarm_statuses}")

    except Exception as e:
        log.error(f"Error updating Modbus registers: {e}", exc_info=True)  # Log traceback as well.

    # No need to sleep here.  The main loop handles the timing.


def start_modbus_server():
    """
    Start Modbus Server with retry mechanism.
    """
    identification = ModbusDeviceIdentification(
        info_name={
            "VendorName": "OOC",
            "ProductCode": "PMBUS",
            "VendorUrl": "http://caspace.com",
            "ProductName": "Python Modbus Server",
            "ModelName": "ModSim",
        }
    )

    retries = 0
    while retries < MAX_RETRIES:
        try:
            log.info(f"Starting Modbus server on {MODBUS_HOST}:{MODBUS_PORT}...")
            StartTcpServer(context=context, address=(MODBUS_HOST, MODBUS_PORT), identity=identification)
            log.info("Modbus server started successfully.")
            return  # Exit the loop if successful

        except ConnectionRefusedError as e:
            log.error(f"Connection refused error: {e}. Retrying in {RETRY_DELAY} seconds...")
            retries += 1
            time.sleep(RETRY_DELAY)
        except ConnectionException as e:
            log.error(f"Connection exception error: {e}. .")
        except Exception as e:
            log.error(f"Error starting Modbus server: {e}", exc_info=True)  # Log traceback
            retries += 1
            time.sleep(RETRY_DELAY)

    log.error("Max retries reached. Modbus server failed to start.")


def get_register(register_type):
    """
    Get the Modbus register by type.
    """
    registers = {
        "coils": coils,
        "discrete_inputs": discrete_inputs,
        "holding_registers": holding_registers,
        "input_registers": input_registers,
    }
    return registers.get(register_type)


def set_register_value(register_type, address, values):
    """
    Assign new values to registers.
    """
    register = get_register(register_type)
    if register:
        try:
            register.setValues(address, values)
        except Exception as e:
            log.error(f"Error setting register value for {register_type} at address {address}: {e}", exc_info=True)
            raise  # Re-raise the exception so the API can handle it.
    else:
        log.error(f"Invalid register type: {register_type}")
        raise ValueError(f"Invalid register type: {register_type}")  # Raise an exception
