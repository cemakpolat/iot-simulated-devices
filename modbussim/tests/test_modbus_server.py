# tests/test_modbus_server.py

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../modbus_server')))

import pytest

from modbus_server.server import (  # Import from server
    simulate_temperature_data,
    update_registers,
    get_register,
    set_register_value,
    NUM_SENSORS,
    holding_registers,
    input_registers,
    coils,
    discrete_inputs,
    current_temperatures
)
from modbus_server.server import holding_registers_data, input_registers_data, coils_data, discrete_inputs_data

from unittest.mock import patch

def test_update_registers_with_mock():
    # Define mock return values for simulate_temperature_data
    mock_current_temperatures = [25] * NUM_SENSORS
    mock_historical_averages = [20] * NUM_SENSORS
    mock_cooling_status = [True] * NUM_SENSORS
    mock_alarm_statuses = [True] * NUM_SENSORS

    # Backup original values
    original_holding_registers = holding_registers.getValues(0, NUM_SENSORS)
    original_input_registers = input_registers.getValues(0, NUM_SENSORS)
    original_coils = coils.getValues(0, NUM_SENSORS)
    original_discrete_inputs = discrete_inputs.getValues(0, NUM_SENSORS)

    # Use pytest's patch to mock simulate_temperature_data
    with patch("modbus_server.server.simulate_temperature_data") as mock_simulate:
        # Configure the mock to return predefined values
        mock_simulate.return_value = (
            mock_current_temperatures,
            mock_historical_averages,
            mock_cooling_status,
            mock_alarm_statuses,
        )

        # Call the function under test
        update_registers()

        # Verify that the values have been updated as expected
        new_holding_registers = holding_registers.getValues(0, NUM_SENSORS)
        new_input_registers = input_registers.getValues(0, NUM_SENSORS)
        new_coils = coils.getValues(0, NUM_SENSORS)
        new_discrete_inputs = discrete_inputs.getValues(0, NUM_SENSORS)

        # Assert that the values match the mock return values
        assert new_holding_registers == mock_current_temperatures
        assert new_input_registers == mock_historical_averages
        assert new_coils == mock_cooling_status
        assert new_discrete_inputs == mock_alarm_statuses

        # Ensure the original values were different (to confirm updates happened)
        assert new_holding_registers != original_holding_registers
        assert new_input_registers != original_input_registers
        assert new_coils != original_coils
        assert new_discrete_inputs != original_discrete_inputs

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
    assert new_coils != original_coils
    assert new_discrete_inputs != original_discrete_inputs


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
