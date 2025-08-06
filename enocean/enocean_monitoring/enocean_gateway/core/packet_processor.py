# packet_processor.py 
from typing import Dict, Any, Optional, List, Tuple, Set

from ..config.eep_profile_loader import EEPProfileLoader
from ..utils.logger import Logger
from ..connections.mqtt_connection import MQTTConnection
from ..protocol.packet_parser import PacketParser, EnOceanPacket
from ..protocol.eep_profiles import EEPDecoder
from ..storage.repositories import DeviceRepository
from .discovery_engine import UnifiedDiscoveryEngine
from ..domain.models import ProcessedPacket, DeviceConfig, DeviceId, EEPProfile


class UnifiedPacketProcessor:
    """Main packet processor that handles both known and unknown devices"""

    def __init__(self, device_repository: DeviceRepository, eep_decoder: EEPDecoder,
                 mqtt_connection: MQTTConnection, logger: Logger, eep_loader: EEPProfileLoader):
        self.device_repository = device_repository
        self.eep_decoder = eep_decoder
        self.mqtt_connection = mqtt_connection
        self.logger = logger

        # Initialize discovery engine
        self.discovery_engine = UnifiedDiscoveryEngine(eep_decoder, logger, eep_loader)

        self.successful_decodes = 0
        self.unknown_devices_detected = 0

        # Reference to monitoring system (set by wrapper)
        self._metrics_collector = None

    def set_metrics_collector(self, metrics_collector):
        """Set the metrics collector reference"""
        self._metrics_collector = metrics_collector

    def process_packet(self, packet: EnOceanPacket) -> Optional[ProcessedPacket]:
        """Process incoming EnOcean packet"""

        try:
            device_id = DeviceId(packet.sender_id)
        except ValueError:
            self.logger.warning(f"Invalid device ID format: {packet.sender_id}")
            return None

        # Try to get device configuration
        device_config = self.device_repository.get_device(device_id)

        if device_config:
            # Known device - decode and publish
            return self._process_known_device(packet, device_config)
        else:
            # Unknown device - analyze for discovery
            return self._process_unknown_device(packet)

    def _process_known_device(self, packet: EnOceanPacket, device_config: DeviceConfig) -> Optional[ProcessedPacket]:
        """Process packet from known device"""
        try:
            # Decode using the configured EEP profile
            decoded_data = self.eep_decoder.decode_by_rorg(packet.rorg, packet.data)

            if decoded_data:
                # Update device activity
                device_config.update_activity(packet.timestamp)
                self.device_repository.save_device(device_config)

                # Create comprehensive MQTT payload
                mqtt_payload = {
                    "device_id": device_config.device_id.value,
                    "device_name": device_config.name,
                    "device_type": device_config.device_type,
                    "location": device_config.location,
                    "eep_profile": device_config.eep_profile.value,
                    "timestamp": packet.timestamp,
                    "packet_count": device_config.packet_count,
                    **decoded_data
                }

                # Publish to MQTT
                success = self.mqtt_connection.publish_sensor_data(mqtt_payload)

                if success:
                    self.successful_decodes += 1
                    self.logger.info(f"📦 {device_config.name}: {self._format_sensor_data(decoded_data)}")

                return ProcessedPacket(
                    device_id=device_config.device_id,
                    device_name=device_config.name,
                    eep_profile=device_config.eep_profile,
                    timestamp=packet.timestamp,
                    decoded_data=decoded_data,
                    success=success
                )
            else:
                self.logger.warning(f"Failed to decode packet from {device_config.name}")
                return None

        except Exception as e:
            self.logger.error(f"Error processing known device {device_config.name}: {e}")
            return None

    def _process_unknown_device(self, packet: EnOceanPacket) -> None:
        """Process packet from unknown device"""
        try:
            # Analyze packet for EEP suggestions
            suggestions = self.discovery_engine.analyze_unknown_packet(
                packet.sender_id, packet.data, packet.rorg
            )

            self.unknown_devices_detected += 1

            if suggestions:
                best_suggestion = suggestions[0]
                self.logger.info(
                    f"🔍 Unknown device {packet.sender_id}: "
                    f"Best EEP suggestion: {best_suggestion.eep_profile} "
                    f"({best_suggestion.confidence:.0%} confidence)"
                )
            else:
                self.logger.info(f"🔍 Unknown device {packet.sender_id}: No EEP suggestions")

            return None

        except Exception as e:
            self.logger.error(f"Error processing unknown device {packet.sender_id}: {e}")
            return None

    def _format_sensor_data(self, decoded_data: Dict[str, Any]) -> str:
        """Format sensor data for logging"""
        data_type = decoded_data.get('type', 'unknown')

        if 'temperature_c' in decoded_data:
            temp = decoded_data['temperature_c']
            humidity = decoded_data.get('humidity_percent', 'N/A')
            return f"🌡️ {temp}°C, 💧 {humidity}%"

        elif 'pressed' in decoded_data:
            action = "PRESSED" if decoded_data['pressed'] else "RELEASED"
            button = decoded_data.get('button_name', 'unknown')
            return f"🔘 {button} {action}"

        elif 'state' in decoded_data and data_type == 'contact':
            state = decoded_data['state'].upper()
            icon = "🔓" if state == 'OPEN' else "🔒"
            return f"{icon} {state}"

        else:
            return f"📊 {data_type}"

    def register_unknown_device(self, device_id: str, name: str, eep_profile: str,
                                device_type: str = "unknown", location: str = "",
                                manufacturer: str = "Unknown", model: str = "Unknown") -> bool:
        """Register an unknown device from discovery"""
        try:
            device_config = DeviceConfig(
                device_id=DeviceId(device_id),
                name=name,
                eep_profile=EEPProfile(eep_profile),
                device_type=device_type,
                location=location,
                manufacturer=manufacturer,
                model=model,
                description=f"Registered via discovery with EEP {eep_profile}"
            )

            success = self.device_repository.save_device(device_config)

            if success:
                # Mark as registered in discovery
                self.discovery_engine.mark_device_registered(device_id)
                self.logger.success(f"Registered device: {name} ({device_id}) -> {eep_profile}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to register device {device_id}: {e}")
            return False

    def ignore_unknown_device(self, device_id: str) -> bool:
        """Ignore an unknown device"""
        try:
            self.discovery_engine.mark_device_ignored(device_id)
            self.logger.info(f"Ignored unknown device: {device_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to ignore device {device_id}: {e}")
            return False

    def get_packet_count(self) -> int:
        """Get packet count from monitoring system if available, fallback to 0"""
        if self._metrics_collector:
            counter = self._metrics_collector.get_counter("enocean_packets_processed_total")
            if counter:
                return int(counter.get_value())
        return 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics using unified counting"""
        device_stats = self.device_repository.get_statistics()
        unknown_devices = self.discovery_engine.get_unknown_devices()

        # Use monitoring system as single source of truth
        total_packets = self.get_packet_count()

        return {
            **device_stats,
            "total_packets_processed": total_packets,  # ← Single source of truth
            "successful_decodes": self.successful_decodes,
            "decode_success_rate": (self.successful_decodes / max(1, total_packets)) * 100,
            "unknown_devices_detected": self.unknown_devices_detected,
            "pending_discovery": len([d for d in unknown_devices if d.status == "pending"]),
            "ignored_devices": len([d for d in unknown_devices if d.status == "ignored"])
        }
