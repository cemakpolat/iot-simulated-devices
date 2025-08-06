# src/connections/mqtt_connection.py
"""
Enhanced MQTT connection handler with comprehensive sensor definitions for Home Assistant discovery.
Supports all EnOcean EEP profiles and device types in the expanded configuration.
"""

import json
import time
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from ..utils.logger import Logger


@dataclass(frozen=True)
class SensorDefinition:
    """A structured definition for a Home Assistant discoverable sensor entity."""
    json_keys: List[str]
    name: str
    component: str
    value_template_gen: Callable[[str], str]
    ha_config: Dict[str, Any]
    is_multi_instance: bool = False


class MQTTConnection:
    """Enhanced MQTT connection with comprehensive Home Assistant auto-discovery for all sensor types."""

    # Comprehensive sensor definitions for all EnOcean device types

    def __init__(self, broker: str, port: int, client_id: str, topic_prefix: str, logger: Logger):
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.topic_prefix = topic_prefix
        self.logger = logger
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.base_topic = topic_prefix

    # Standard MQTT Connection Methods
    def connect(self) -> bool:
        """Establish MQTT connection"""
        try:
            self.client = mqtt.Client(client_id=self.client_id, callback_api_version=CallbackAPIVersion.VERSION2)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            time.sleep(0.5)
            return self.connected
        except Exception as e:
            self.logger.failure(f"MQTT connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.logger.info("MQTT connection closed")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            self.logger.success(f"MQTT connected to {self.broker}:{self.port}")
        else:
            self.logger.failure(f"MQTT connection failed with code {rc}")
    
    def is_connected(self):
        return self.connected

    def _on_disconnect(self, client, userdata, rc, properties=None, reasoncode=None):
        self.connected = False
        self.logger.info("MQTT disconnected")

    def _on_publish(self, client, userdata, mid, reason_code=None, properties=None):
        self.logger.debug(f"MQTT message {mid} published")

    def publish_sensor_data(self, data: Dict[str, Any]) -> bool:
        """Publish complete sensor data to the state topic."""
        if not self.connected or not self.client:
            return False
        try:
            device_id = data['device_id'].replace(':', '')
            topic = f"{self.base_topic}/{device_id}"
            message = json.dumps(data, default=str)
            result = self.client.publish(topic, message, qos=1)
            result.wait_for_publish(timeout=5)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"📤 Published state for {device_id}")
                return True
            self.logger.error(f"MQTT state publish failed: {mqtt.error_string(result.rc)}")
            return False
        except Exception as e:
            self.logger.error(f"MQTT state publish error: {e}", exc_info=True)
            return False

    def _handle_standard_sensor(self, configs, device_id, device_info, state_topic, config_key, definition, json_key):
        """Builds a config for a standard, single-instance sensor."""
        # Enhanced naming with device context
        device_name = device_info.get('name', f"EnOcean {device_id}")

        configs[config_key] = {
            "component": definition.component,
            "name": f"{device_name} {definition.name}",
            "unique_id": f"enocean_{device_id}_{config_key}",
            "state_topic": state_topic,
            "value_template": definition.value_template_gen(json_key),
            "device": device_info,
            **definition.ha_config
        }

        # Add availability if device supports it
        if 'last_seen' in device_info or 'status' in device_info:
            configs[config_key]["availability_topic"] = f"{state_topic}/availability"
            configs[config_key]["payload_available"] = "online"
            configs[config_key]["payload_not_available"] = "offline"

    def _handle_multi_instance_sensor(self, configs, device_id, device_info, state_topic, definition, sensor_data):
        """Builds configs for sensors with multiple instances."""
        device_name = device_info.get('name', f"EnOcean {device_id}")

        for key in definition.json_keys:
            if self._find_matching_key([key], sensor_data):
                # Extract the instance identifier
                if '_' in key:
                    instance_id = key.split('_')[1].replace('_g', '').replace('_pressed', '')
                else:
                    instance_id = key[-1]

                instance_key = f"{definition.name.lower().replace(' ', '_')}_{instance_id}"

                configs[instance_key] = {
                    "component": definition.component,
                    "name": f"{device_name} {definition.name} {instance_id.upper()}",
                    "unique_id": f"enocean_{device_id}_{instance_key}",
                    "state_topic": state_topic,
                    "value_template": definition.value_template_gen(key),
                    "device": device_info,
                    **definition.ha_config
                }

    def _add_device_type_specific_configs(self, configs, device_id, device_info, state_topic, sensor_data):
        """Add device type specific configurations not covered by standard definitions."""
        device_type = sensor_data.get('device_type', 'unknown')
        device_name = device_info.get('name', f"EnOcean {device_id}")

        # Special handling for switches with multiple states
        if device_type == 'rocker_switch' and 'button_combination' in sensor_data:
            configs['button_state'] = {
                "component": "sensor",
                "name": f"{device_name} Button State",
                "unique_id": f"enocean_{device_id}_button_state",
                "state_topic": state_topic,
                "value_template": "{{ value_json.button_combination }}",
                "icon": "mdi:gesture-tap-button",
                "device": device_info
            }

        # Special handling for teach-in devices
        if sensor_data.get('type') == 'teach_in':
            configs['teach_in_status'] = {
                "component": "binary_sensor",
                "name": f"{device_name} Teach-in",
                "unique_id": f"enocean_{device_id}_teach_in",
                "state_topic": state_topic,
                "value_template": "{{ 'ON' if value_json.type == 'teach_in' else 'OFF' }}",
                "device_class": "connectivity",
                "entity_category": "diagnostic",
                "device": device_info
            }

        # Special handling for multi-sensors with additional data
        if device_type in ['multi_sensor', 'multi_sensor_magnet']:
            # Add device status sensor
            configs['device_status'] = {
                "component": "sensor",
                "name": f"{device_name} Status",
                "unique_id": f"enocean_{device_id}_device_status",
                "state_topic": state_topic,
                "value_template": "{{ value_json.type }}",
                "icon": "mdi:information",
                "entity_category": "diagnostic",
                "device": device_info
            }

        # Add last seen timestamp for all devices
        configs['last_seen'] = {
            "component": "sensor",
            "name": f"{device_name} Last Seen",
            "unique_id": f"enocean_{device_id}_last_seen",
            "state_topic": state_topic,
            "value_template": "{{ value_json.timestamp | timestamp_local }}",
            "device_class": "timestamp",
            "entity_category": "diagnostic",
            "device": device_info
        }

        # Add packet count for statistics
        configs['packet_count'] = {
            "component": "sensor",
            "name": f"{device_name} Packet Count",
            "unique_id": f"enocean_{device_id}_packet_count",
            "state_topic": state_topic,
            "value_template": "{{ value_json.packet_count | default(0) }}",
            "state_class": "total_increasing",
            "entity_category": "diagnostic",
            "icon": "mdi:counter",
            "device": device_info
        }

    def _find_matching_key(self, possible_keys: List[str], sensor_data: Dict[str, Any]) -> Optional[str]:
        """Finds the first key from a list that exists in the data, supporting nested keys."""
        for key in possible_keys:
            path = key.split('.')
            value = sensor_data
            try:
                for p in path:
                    value = value[p]
                return key
            except (KeyError, TypeError):
                continue
        return None

    def publish_metrics(self, device_id: str, metrics: Dict[str, Any]) -> bool:
        """Publish individual metrics for time-series databases"""
        if not self.connected or not self.client:
            return False

        try:
            clean_device_id = device_id.replace(':', '')
            topic = f"{self.topic_prefix}/metrics/{clean_device_id}"
            message = json.dumps(metrics, default=str)
            result = self.client.publish(topic, message)
            return result.rc == mqtt.MQTT_ERR_SUCCESS

        except Exception as e:
            self.logger.error(f"Metrics publish error: {e}")
            return False

    def publish_availability(self, device_id: str, available: bool = True) -> bool:
        """Publish device availability status"""
        if not self.connected or not self.client:
            return False

        try:
            clean_device_id = device_id.replace(':', '')
            topic = f"{self.base_topic}/{clean_device_id}/availability"
            payload = "online" if available else "offline"
            result = self.client.publish(topic, payload, qos=1, retain=True)
            return result.rc == mqtt.MQTT_ERR_SUCCESS

        except Exception as e:
            self.logger.error(f"Availability publish error: {e}")
            return False

    def publish_device_info_update(self, device_id: str, device_info: Dict[str, Any]) -> bool:
        """Publish updated device information"""
        if not self.connected or not self.client:
            return False

        try:
            clean_device_id = device_id.replace(':', '')
            topic = f"{self.base_topic}/{clean_device_id}/info"
            message = json.dumps(device_info, default=str)
            result = self.client.publish(topic, message, qos=1, retain=True)
            return result.rc == mqtt.MQTT_ERR_SUCCESS

        except Exception as e:
            self.logger.error(f"Device info publish error: {e}")
            return False


# class MQTTManager:
#     """Enhanced MQTT manager for multiple connections"""

#     def __init__(self, logger: Logger):
#         self.logger = logger
#         self.connections: Dict[str, MQTTConnection] = {}

#     def add_connection(self, name: str, broker: str, port: int, client_id: str, topic_prefix: str) -> bool:
#         """Add a new MQTT connection"""
#         connection = MQTTConnection(broker, port, client_id, topic_prefix, self.logger)
#         if connection.connect():
#             self.connections[name] = connection
#             return True
#         return False

#     def remove_connection(self, name: str):
#         """Remove an MQTT connection"""
#         if name in self.connections:
#             self.connections[name].disconnect()
#             del self.connections[name]

#     def get_connection(self, name: str) -> Optional[MQTTConnection]:
#         """Get an MQTT connection by name"""
#         return self.connections.get(name)

#     def disconnect_all(self):
#         """Disconnect all MQTT connections"""
#         for connection in self.connections.values():
#             connection.disconnect()
#         self.connections.clear()

#     def publish_to_all(self, data: Dict[str, Any]) -> Dict[str, bool]:
#         """Publish data to all connections"""
#         results = {}
#         for name, connection in self.connections.items():
#             results[name] = connection.publish_sensor_data(data)
#         return results

#     def get_connection_status(self) -> Dict[str, bool]:
#         """Get status of all connections"""
#         return {name: conn.connected for name, conn in self.connections.items()}
