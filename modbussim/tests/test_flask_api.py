# tests/test_flask_api.py

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../modbus_server')))

import pytest
import json
from modbus_server.flask_api import app  # Import Flask app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_get_register_value(client):
    # Test getting a register value
    response = client.get('/modbus/holding_registers/0')
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert 'address' in data
    assert 'value' in data
    assert data['address'] == 0


def test_put_register_value(client):
    # Test updating a register value
    payload = {
        "value": 12345,
        "data_type": "UINT16"
    }
    response = client.put('/modbus/holding_registers/0', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert 'address' in data
    assert 'value' in data
    assert 'hex_values' in data
    assert data['address'] == 0
    assert data["value"] == 12345

    # Reset to original value (optional, but good practice)
    payload = {
        "value": 25,
        "data_type": "UINT16"
    }
    response = client.put('/modbus/holding_registers/0', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 200


def test_put_register_invalid_register(client):
    # Test updating a register with invalid register name
    payload = {
        "value": 10,
        "data_type": "UINT16"
    }
    response = client.put('/modbus/invalid_register/0', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.get_data(as_text=True))
    assert 'error' in data


def test_put_register_invalid_address(client):
    # Test updating a register with invalid address
    payload = {
        "value": 10,
        "data_type": "UINT16"
    }
    response = client.put(f'/modbus/holding_registers/{10000}', data=json.dumps(payload),
                          content_type='application/json')  # Large Address
    assert response.status_code == 400
    data = json.loads(response.get_data(as_text=True))
    assert 'error' in data


def test_put_register_invalid_data_type(client):
    # Test updating a register with invalid data_type
    payload = {
        "value": 10,
        "data_type": "String"
    }
    response = client.put('/modbus/holding_registers/0', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400  # Changed from 500 to 400
    data = json.loads(response.get_data(as_text=True))
    assert 'error' in data


def test_put_register_value_out_of_range(client):
    # Test updating a register value out of range
    payload = {
        "value": 70000,
        "data_type": "UINT16"
    }
    response = client.put('/modbus/holding_registers/0', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.get_data(as_text=True))
    assert 'error' in data


def test_put_register_missing_value(client):
    # Test PUT request with missing data
    payload = {
        "data_type": "UINT16"
    }
    response = client.put('/modbus/holding_registers/0', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.get_data(as_text=True))
    assert 'error' in data
