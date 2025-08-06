# src/protocol/packet_decoder.py
"""
Enhanced EnOcean packet decoding with device registry support
"""

from typing import Dict, Any, Optional, List
from .packet_parser import EnOceanPacket
from .eep_profiles import EEPDecoder
from ..config.device_registry import DeviceRegistry, DeviceDiscovery
from ..utils.logger import Logger


class PacketDecoder:
    """Enhanced packet decoder that uses device registry for EEP profile mapping"""

    def __init__(self, logger: Logger, device_config_file: str = "devices.json"):
        self.logger = logger
        self.eep_decoder = EEPDecoder(logger)

        # Initialize device registry
        self.device_registry = DeviceRegistry(device_config_file, logger)
        self.device_discovery = DeviceDiscovery(self.device_registry, logger)

        # Statistics
        self.decode_stats = DecodingStatistics()

        # Auto-save timer
        self._last_save_time = 0
        self._save_interval = 300  # Save every 5 minutes

    def decode(self, packet: EnOceanPacket) -> Optional[Dict[str, Any]]:
        """Decode an EnOcean packet using device registry for EEP profile lookup"""
        if not packet or not packet.data:
            return None

        try:
            sender_id = packet.sender_id
            print(f"sender:{sender_id}")
            # Update device activity in registry
            self.device_registry.update_device_activity(sender_id, packet.timestamp)

            # Get device information from registry
            device_info = self.device_registry.get_device(sender_id)
            print(f"device info:{device_info}")
            eep_profile = None

            if device_info:
                eep_profile = device_info.eep_profile
                if self.logger:
                    self.logger.debug(f"Found device {sender_id} with profile {eep_profile}")
            else:
                # Try device discovery for unknown devices
                eep_profile = self.device_discovery.handle_unknown_device(
                    sender_id, packet.rorg, packet.data
                )
                print(f"unknown device {eep_profile}")
                if eep_profile:
                    device_info = self.device_registry.get_device(sender_id)

            # Base packet information
            result = {
                'device_id': sender_id,
                'timestamp': packet.timestamp,
                'rorg': f"0x{packet.rorg:02X}",
                'signal_quality': self._get_signal_quality(packet.status)
            }

            # Add device information if available
            if device_info:
                result.update({
                    'device_name': device_info.name,
                    'device_type': device_info.device_type,
                    'location': device_info.location,
                    'manufacturer': device_info.manufacturer,
                    'model': device_info.model,
                    'capabilities': device_info.capabilities
                })

            # Decode using specific EEP profile if known
            if eep_profile:
                eep_data = self._decode_with_specific_profile(packet, eep_profile)
                if eep_data:
                    result.update(eep_data)
                    self.decode_stats.record_decode(True, eep_data.get('type'), eep_profile)
                else:
                    # EEP decoder failed, try fallback
                    fallback_data = self._decode_with_fallback(packet)
                    if fallback_data:
                        result.update(fallback_data)
                        self.decode_stats.record_decode(True, fallback_data.get('type'), 'fallback')
                    else:
                        self.decode_stats.record_decode(False)
            else:
                # No EEP profile known, use generic decoder
                generic_data = self.eep_decoder.decode_by_rorg(packet.rorg, packet.data)
                if generic_data:
                    result.update(generic_data)
                    self.decode_stats.record_decode(True, generic_data.get('type'), 'generic')
                else:
                    # Complete fallback
                    result.update({
                        'type': 'unknown',
                        'raw_data': packet.data.hex().upper(),
                        'analysis': self._analyze_unknown_packet(packet.data)
                    })
                    self.decode_stats.record_unknown()

            # Auto-save registry if needed
            self._auto_save_registry()

            return result

        except Exception as e:
            self.logger.error(f"Packet decoding error: {e}")
            self.decode_stats.record_decode(False)
            return None

    def _decode_with_specific_profile(self, packet: EnOceanPacket, eep_profile: str) -> Optional[Dict[str, Any]]:
        """Decode packet using specific EEP profile"""
        try:
            # Get the appropriate decoder based on EEP profile
            rorg = packet.rorg

            # Map EEP profile to decoder method
            if eep_profile.startswith('A5-'):
                decoder = self.eep_decoder.decoders.get(0xA5)
            elif eep_profile.startswith('F6-'):
                decoder = self.eep_decoder.decoders.get(0xF6)
            elif eep_profile.startswith('D5-'):
                decoder = self.eep_decoder.decoders.get(0xD5)
            elif eep_profile.startswith('D2-'):
                decoder = self.eep_decoder.decoders.get(0xD2)
            elif eep_profile.startswith('D4-'):
                decoder = self.eep_decoder.decoders.get(0xD4)
            else:
                return None

            if decoder and decoder.can_decode(packet.data):
                result = decoder.decode(packet.data)
                if result:
                    result['eep_profile'] = eep_profile
                    return result

        except Exception as e:
            self.logger.debug(f"Specific EEP decoder failed for {eep_profile}: {e}")

        return None

    def _decode_with_fallback(self, packet: EnOceanPacket) -> Optional[Dict[str, Any]]:
        """Fallback decoding when specific EEP profile fails"""
        return self.eep_decoder.decode_by_rorg(packet.rorg, packet.data)

    def _get_signal_quality(self, status: int) -> Dict[str, Any]:
        """Extract signal quality from status byte"""
        rssi = status & 0x0F if isinstance(status, int) else 0
        quality_map = {
            range(13, 16): 'excellent',
            range(9, 13): 'good',
            range(5, 9): 'fair',
            range(0, 5): 'poor'
        }

        quality = 'unknown'
        for rssi_range, qual in quality_map.items():
            if rssi in rssi_range:
                quality = qual
                break

        return {'rssi': rssi, 'quality': quality}

    def _analyze_unknown_packet(self, data: bytes) -> Dict[str, Any]:
        """Provide analysis for unknown packet types"""
        if not data:
            return {}

        rorg = data[0]

        analysis = {
            'length': len(data),
            'rorg_byte': f"0x{rorg:02X}",
            'rorg_type': self._get_rorg_type_name(rorg),
            'hex_dump': data.hex(' ', 1).upper()
        }

        # Try to guess possible EEP profiles
        if len(data) >= 4:
            analysis['possible_eep'] = self._guess_eep_profile(data)

        return analysis

    def _get_rorg_type_name(self, rorg: int) -> str:
        """Get human-readable RORG type name"""
        rorg_types = {
            0xA5: "4BS (4-byte communication)",
            0xD2: "VLD (variable length data)",
            0xF6: "RPS (repeater)",
            0xD5: "1BS (1-byte communication)",
            0xA7: "Smart Ack",
            0x30: "Secure Device",
            0xD4: "UTE (universal teach-in)"
        }
        return rorg_types.get(rorg, f"Unknown RORG (0x{rorg:02X})")

    def _guess_eep_profile(self, data: bytes) -> str:
        """Attempt to guess EEP profile from data pattern"""
        if len(data) < 2:
            return "Unknown (data too short)"

        rorg = data[0]
        if rorg == 0xA5 and len(data) >= 5:
            return f"A5-{data[3]:02X}-{data[4]:02X}"
        elif rorg == 0xD2 and len(data) >= 4:
            return f"D2-{data[1]:02X}-{data[2]:02X}"
        elif rorg == 0xF6:
            return "F6-02-01/02 (Rocker switch)"
        elif rorg == 0xD5:
            return "D5-00-01 (Contact sensor)"

        return "Unknown (pattern not recognized)"

    def _auto_save_registry(self):
        """Auto-save device registry if enough time has passed"""
        import time
        current_time = time.time()
        if current_time - self._last_save_time > self._save_interval:
            self.device_registry.auto_save_if_modified()
            self._last_save_time = current_time

    # Device registry management methods
    def enable_device_discovery(self):
        """Enable automatic device discovery"""
        self.device_discovery.enable_discovery()

    def disable_device_discovery(self):
        """Disable automatic device discovery"""
        self.device_discovery.disable_discovery()

    def register_device_manually(self, sender_id: str, eep_profile: str, **kwargs):
        """Manually register a device"""
        return self.device_registry.register_device(sender_id, eep_profile, **kwargs)

    def get_device_info(self, sender_id: str):
        """Get device information"""
        return self.device_registry.get_device(sender_id)

    def get_all_devices(self):
        """Get all registered devices"""
        return self.device_registry.get_all_devices()

    def get_registry_statistics(self):
        """Get device registry statistics"""
        return self.device_registry.get_statistics()

    def get_decoding_statistics(self):
        """Get decoding statistics"""
        return self.decode_stats.get_stats()

    def save_device_registry(self):
        """Manually save device registry"""
        return self.device_registry.save_configuration()

    def reload_device_registry(self):
        """Reload device registry from file"""
        return self.device_registry.load_configuration()


class DecodingStatistics:
    """Track decoding statistics and performance"""

    def __init__(self):
        self.total_decoded = 0
        self.successful_decodes = 0
        self.failed_decodes = 0
        self.decodes_by_type = {}
        self.decodes_by_eep = {}
        self.unknown_packets = 0
        self.decodes_by_device = {}

    def record_decode(self, success: bool, packet_type: str = None, eep_profile: str = None, device_id: str = None):
        """Record decoding statistics"""
        self.total_decoded += 1

        if success:
            self.successful_decodes += 1
            if packet_type:
                self.decodes_by_type[packet_type] = self.decodes_by_type.get(packet_type, 0) + 1
            if eep_profile:
                self.decodes_by_eep[eep_profile] = self.decodes_by_eep.get(eep_profile, 0) + 1
            if device_id:
                self.decodes_by_device[device_id] = self.decodes_by_device.get(device_id, 0) + 1
        else:
            self.failed_decodes += 1

    def record_unknown(self):
        """Record unknown packet"""
        self.unknown_packets += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get decoding statistics"""
        success_rate = (self.successful_decodes / self.total_decoded * 100) if self.total_decoded > 0 else 0

        return {
            'total_decoded': self.total_decoded,
            'successful_decodes': self.successful_decodes,
            'failed_decodes': self.failed_decodes,
            'unknown_packets': self.unknown_packets,
            'success_rate': round(success_rate, 2),
            'decodes_by_type': self.decodes_by_type,
            'decodes_by_eep': self.decodes_by_eep,
            'decodes_by_device': self.decodes_by_device,
            'supported_types': len(self.decodes_by_type),
            'supported_eep_profiles': len(self.decodes_by_eep),
            'active_devices': len(self.decodes_by_device)
        }

    def reset(self):
        """Reset all statistics"""
        self.total_decoded = 0
        self.successful_decodes = 0
        self.failed_decodes = 0
        self.decodes_by_type.clear()
        self.decodes_by_eep.clear()
        self.unknown_packets = 0
        self.decodes_by_device.clear()

    def get_device_activity(self) -> List[Dict[str, Any]]:
        """Get device activity summary"""
        return [
            {
                'device_id': device_id,
                'packet_count': count,
                'percentage': round((count / self.total_decoded * 100), 2) if self.total_decoded > 0 else 0
            }
            for device_id, count in sorted(self.decodes_by_device.items(), key=lambda x: x[1], reverse=True)
        ]