from flask import Flask, jsonify, request
import logging
from server import get_register, set_register_value  # Access from server
import struct

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s")
log = logging.getLogger(__name__)

# Flask app for REST API
app = Flask(__name__)
FLASK_PORT = 15000
FLASK_IP = "0.0.0.0"


# Helper function to convert between data types
def convert_to_registers(value, data_type):
    """Converts a decimal value to a list of registers based on the specified data type."""
    try:
        if data_type == "UINT16":
            if not (0 <= value <= 65535):
                raise ValueError("Value out of range for UINT16")
            return [int(value)]  # Ensure integer
        elif data_type == "INT16":
            if not (-32768 <= value <= 32767):
                raise ValueError("Value out of range for INT16")
            return [int(value) & 0xFFFF]  # Ensure integer
        elif data_type == "UINT32":
            if not (0 <= value <= 4294967295):
                raise ValueError("Value out of range for UINT32")
            return list(struct.unpack(">HH", struct.pack(">I", int(value))))  # Split into two 16-bit registers

        elif data_type == "INT32":
            if not (-2147483648 <= value <= 2147483647):
                raise ValueError("Value out of range for INT32")

            return list(struct.unpack(">HH", struct.pack(">i", int(value))))  # Split into two 16-bit registers
        elif data_type == "FLOAT32":
            return list(struct.unpack(">HH", struct.pack(">f", float(value))))  # Split into two 16-bit registers
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
    except struct.error as e:
        log.error(f"Struct error during conversion: {e}", exc_info=True)
        raise  # Re-raise the exception
    except ValueError as e:
        log.error(f"Value error during conversion: {e}", exc_info=True)
        raise
    except Exception as e:
        log.error(f"Unexpected error during conversion: {e}", exc_info=True)
        raise


# REST API to interact with Modbus server
@app.route('/modbus/<string:register>/<int:address>', methods=['GET', 'PUT'])
def modbus_register(register, address):
    """
    Update register values.
    """
    try:
        register = register.lower()  # Standardize case

        if register not in ["coils", "discrete_inputs", "holding_registers", "input_registers"]:
            log.warning(f"Invalid register type requested: {register}")
            return jsonify({"error": "Invalid register type"}), 400

        store = get_register(register)
        if not store:
            log.error(f"Register {register} not found.")
            return jsonify({"error": "Invalid register type"}), 400

        if address < 0 or address >= len(store.values):
            log.warning(f"Invalid address {address} for register {register}")
            return jsonify({"error": "Invalid address"}), 400

        if request.method == 'GET':
            try:
                value = store.getValues(address, count=1)[0]
                return jsonify({"address": address, "value": value})
            except Exception as e:
                log.error(f"Error reading register {register} at address {address}: {e}", exc_info=True)
                return jsonify({"error": "Failed to read register"}), 500

        if request.method == 'PUT':
            data = request.get_json()  # Use get_json for safer parsing
            if not isinstance(data, dict) or "value" not in data or "data_type" not in data:
                log.warning("Invalid request body format.")
                return jsonify({"error": "Value and data_type are required"}), 400

            try:
                decimal_value = data["value"]
                data_type = str(data["data_type"]).upper()  # Ensure string type
                hex_values = convert_to_registers(decimal_value, data_type)

                # Update the Modbus register(s)
                set_register_value(register, address, hex_values)
                current_values = store.getValues(address, len(hex_values))

                log.info(f"Updated values at address {address}: {current_values}")
                return jsonify({
                    "address": address,
                    "value": decimal_value,
                    "hex_values": current_values,
                    "data_type": data_type
                })
            except ValueError as e:
                log.error(f"Invalid value provided: {e}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                log.error(f"Error updating register: {e}", exc_info=True)
                return jsonify({"error": "Failed to update register"}), 500

    except Exception as e:
        log.critical(f"Unhandled exception in modbus_register: {e}", exc_info=True)  # Catch all other exceptions
        return jsonify({"error": "Internal server error"}), 500


def start_flask_api():
    try:
        log.info("Starting Flask API...")
        app.run(host=FLASK_IP, port=FLASK_PORT, debug=False)
        log.info("Flask API started successfully.")
    except Exception as e:
        log.critical(f"Flask API failed to start: {e}", exc_info=True)
