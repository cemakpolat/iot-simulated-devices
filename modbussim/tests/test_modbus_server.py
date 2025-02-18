# tests/test_modbus_server.py
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../modbus_server')))

import pytest

from ..modbus_server.server import (  # Import from server
    simulate_temperature_data,
    update_registers,
    get_register,
    set_register_value,
    NUM_SENSORS,
    holding_registers,
    input_registers,
    coils,
    discrete_inputs
)


def test_simulate_temperature_data():
    current_temps = [25] * NUM_SENSORS
    historical_avg = [23] * NUM_SENSORS
    updated_temps, _, cooling_status, alarm_statuses = simulate_temperature_data(current_temps, historical_avg)

    assert len(updated_temps) == NUM_SENSORS
    assert all(20 <= temp <= 30 for temp in updated_temps)  # Check if temps are within reasonable range
    assert all(isinstance(status, bool) for status in cooling_status)
    assert all(isinstance(status, bool) for status in alarm_statuses)


def test_update_registers():
    # Backup original values
    original_holding_registers = holding_registers.getValues(0, NUM_SENSORS)
    original_input_registers = input_registers.getValues(0, NUM_SENSORS)
    original_coils = coils.getValues(0, NUM_SENSORS)
    original_discrete_inputs = discrete_inputs.getValues(0, NUM_SENSORS)

    # Set initial values in holding registers to ensure discrete inputs change
    holding_registers.setValues(0, [60] * NUM_SENSORS)  # Force high values

    update_registers()

    # Verify that the values have changed
    new_holding_registers = holding_registers.getValues(0, NUM_SENSORS)
    new_input_registers = input_registers.getValues(0, NUM_SENSORS)
    new_coils = coils.getValues(0, NUM_SENSORS)
    new_discrete_inputs = discrete_inputs.getValues(0, NUM_SENSORS)

    assert new_holding_registers != original_holding_registers
    assert new_input_registers != original_input_registers
    #assert new_coils != original_coils
    #assert new_discrete_inputs != original_discrete_inputs


def test_get_register():
    assert get_register("holding_registers") == holding_registers
    assert get_register("input_registers") == input_registers
    assert get_register("coils") == coils
    assert get_register("discrete_inputs") == discrete_inputs
    assert get_register("invalid_register") is None


def test_set_register_value():
    # Backup original value
    original_value = holding_registers.getValues(0, 1)[0]

    # set a new value
    new_value = 50
    set_register_value("holding_registers", 0, [new_value])

    # Assert that the value has changed
    assert holding_registers.getValues(0, 1)[0] == new_value

    # Reset the value to original
    set_register_value("holding_registers", 0, [original_value])


def test_set_register_value_invalid_register():
    with pytest.raises(ValueError, match="Invalid register type: invalid_register"):
        set_register_value("invalid_register", 0, [10])
