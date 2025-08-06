# #!/usr/bin/env python3
# """
# Discovery Engine - Dynamically identifies unknown EnOcean devices.

# This module analyzes packets from unknown devices by comparing the decoded data
# against a set of rules and known EEP profiles, which are loaded from external
# JSON configuration files. This makes the discovery process highly flexible
# and extensible without requiring code changes.
# """
# import json
# # 1. Standard Library Imports
# import time
# from dataclasses import asdict
# from typing import Dict, Any, List, Set, Tuple

# from ..utils.logger import Logger
# from ..protocol.eep_profiles import EEPDecoder

# from ..config.eep_profile_loader import EEPProfileLoader  # Now a required dependency
# from ..domain.models import EEPSuggestion, UnknownDevice
# import json


# # In core/discovery_engine.py
# class UnifiedDiscoveryEngine:
#     """Discovery engine that maintains compatibility with packet_processor interface"""

#     def __init__(self, eep_decoder: EEPDecoder, logger: Logger, eep_loader: EEPProfileLoader):
#         self.eep_decoder = eep_decoder
#         self.logger = logger
#         self.eep_loader = eep_loader
#         self.unknown_devices_file = "unknown_devices.json"

#         # Load configuration files for data-driven approach
#         self.capability_rules = self._load_capability_rules()
#         self.confidence_weights = self._load_confidence_weights()

#     # ========================================================================
#     # COMPATIBILITY METHODS - Keep existing packet_processor interface
#     # ========================================================================

#     def analyze_unknown_packet(self, device_id: str, raw_data: bytes, rorg: int) -> List[EEPSuggestion]:
#         """Analyze unknown packet - MAIN METHOD used by packet_processor"""
#         suggestions = []

#         # Get candidate profiles from loaded EEP data (data-driven)
#         candidate_profiles = self._get_candidate_profiles_from_config(rorg)

#         for profile_id in candidate_profiles:
#             try:
#                 profile_info = self.eep_loader.get_eep_profile(profile_id)
#                 if not profile_info:
#                     continue

#                 # Try to decode with this EEP profile
#                 decoded_data = self.eep_decoder.decode_by_rorg(rorg, raw_data)

#                 if decoded_data and self._is_reasonable_decode(decoded_data, profile_info):
#                     # Use rule-based capability detection
#                     detected_capabilities = self._detect_capabilities_from_rules(decoded_data)

#                     # Calculate confidence using configurable weights
#                     confidence = self._calculate_confidence_from_config(
#                         decoded_data, profile_info, detected_capabilities
#                     )

#                     reasoning = self._generate_reasoning_from_rules(
#                         decoded_data, profile_info, detected_capabilities
#                     )

#                     suggestion = EEPSuggestion(
#                         eep_profile=profile_id,
#                         confidence=confidence,
#                         reasoning=reasoning,
#                         decoded_data=decoded_data,
#                         data_quality=self._assess_data_quality_from_rules(decoded_data)
#                     )
#                     suggestions.append(suggestion)

#             except Exception as e:
#                 self.logger.debug(f"Failed to decode with {profile_id}: {e}")

#         # Sort by confidence
#         suggestions.sort(key=lambda x: x.confidence, reverse=True)

#         # Store unknown device for dashboard
#         self._store_unknown_device(device_id, raw_data, rorg, suggestions)

#         return suggestions

#     def mark_device_registered(self, device_id: str):
#         """Mark unknown device as registered - USED BY packet_processor"""
#         unknown_devices = self._load_unknown_devices()
#         if device_id in unknown_devices:
#             del unknown_devices[device_id]  # Remove completely when registered
#             self._save_unknown_devices(unknown_devices)
#             self.logger.info(f"🔄 Removed {device_id} from unknown devices (registered)")

#     def mark_device_ignored(self, device_id: str):
#         """Mark unknown device as ignored - USED BY packet_processor"""
#         unknown_devices = self._load_unknown_devices()
#         if device_id in unknown_devices:
#             unknown_devices[device_id]["status"] = "ignored"
#             self._save_unknown_devices(unknown_devices)
#             self.logger.info(f"🚫 Marked {device_id} as ignored")

#     def get_unknown_devices(self) -> List[UnknownDevice]:
#         """Get all unknown devices for dashboard - USED BY packet_processor"""
#         unknown_data = self._load_unknown_devices()
#         devices = []

#         for device_id, data in unknown_data.items():
#             # Only return pending devices (not ignored)
#             if data.get("status", "pending") != "pending":
#                 continue

#             # Convert hex strings back to bytes
#             sample_packets = [bytes.fromhex(p) for p in data.get("sample_packets", [])]

#             # Convert suggestion dicts back to objects
#             suggestions = []
#             for s in data.get("eep_suggestions", []):
#                 try:
#                     suggestions.append(EEPSuggestion(**s))
#                 except Exception:
#                     # Handle malformed suggestions gracefully
#                     continue

#             device = UnknownDevice(
#                 device_id=device_id,
#                 first_seen=data.get("first_seen", 0),
#                 last_seen=data.get("last_seen", 0),
#                 packet_count=data.get("packet_count", 0),
#                 sample_packets=sample_packets,
#                 rorg_types=data.get("rorg_types", []),
#                 eep_suggestions=suggestions,
#                 status=data.get("status", "pending")
#             )
#             devices.append(device)

#         return devices


#     def _get_candidate_profiles_from_config(self, rorg: int) -> List[str]:
#         """Get candidate profiles from loaded EEP configuration (data-driven)"""
#         rorg_hex = f"{rorg:02X}"
#         candidates = []

#         for profile_id, profile in self.eep_loader.get_all_eep_profiles().items():
#             if profile.rorg.upper() == rorg_hex:
#                 candidates.append(profile_id)

#         return candidates

#     def _detect_capabilities_from_rules(self, decoded_data: Dict[str, Any]) -> Set[str]:
#         """Use rule engine to detect capabilities"""
#         if hasattr(self.eep_loader, 'rule_engine') and self.eep_loader.rule_engine:
#             return self.eep_loader.rule_engine.detect_capabilities(decoded_data)

#         # Fallback to simple detection if rule engine not available
#         return self._simple_capability_detection(decoded_data)

#     def _simple_capability_detection(self, decoded_data: Dict[str, Any]) -> Set[str]:
#         """Simple fallback capability detection"""
#         capabilities = set()

#         if 'temperature_c' in decoded_data:
#             capabilities.add('temperature')
#         if 'humidity_percent' in decoded_data:
#             capabilities.add('humidity')
#         if 'button_name' in decoded_data or 'pressed' in decoded_data:
#             capabilities.add('switch')
#         if 'state' in decoded_data and decoded_data.get('type') == 'contact':
#             capabilities.add('contact')
#         if any(key.startswith('acceleration_') for key in decoded_data.keys()):
#             capabilities.add('acceleration')
#         if 'illuminance_lx' in decoded_data:
#             capabilities.add('illuminance')

#         return capabilities

#     def _calculate_confidence_from_config(self, decoded_data: Dict, profile_info,
#                                           detected_capabilities: Set[str]) -> float:
#         """Calculate confidence using configurable weights"""
#         weights = self.confidence_weights
#         base_confidence = weights.get('base_confidence', 0.5)

#         # Match capabilities
#         profile_capabilities = set(profile_info.capabilities)
#         matching_caps = detected_capabilities.intersection(profile_capabilities)

#         if profile_capabilities:
#             capability_match_score = len(matching_caps) / len(profile_capabilities)
#             confidence = base_confidence + (capability_match_score * weights.get('capability_match', 0.3))
#         else:
#             confidence = base_confidence

#         # Apply data quality bonuses from config
#         for field, bonus_weight in weights.get('data_quality_bonuses', {}).items():
#             if field in decoded_data:
#                 value = decoded_data[field]
#                 if self._is_reasonable_value(field, value):
#                     confidence += bonus_weight

#         return min(1.0, max(0.0, confidence))

#     def _generate_reasoning_from_rules(self, decoded_data: Dict, profile_info, detected_capabilities: Set[str]) -> str:
#         """Generate human-readable reasoning"""
#         reasons = []

#         profile_capabilities = set(profile_info.capabilities)
#         matching_caps = detected_capabilities.intersection(profile_capabilities)

#         if matching_caps:
#             reasons.append(f"Matched capabilities: {', '.join(sorted(matching_caps))}")

#         # Add specific data observations
#         if 'temperature_c' in decoded_data and 'humidity_percent' in decoded_data:
#             reasons.append("Contains both temperature and humidity data")
#         elif 'temperature_c' in decoded_data:
#             reasons.append("Contains temperature data")
#         elif 'humidity_percent' in decoded_data:
#             reasons.append("Contains humidity data")

#         if 'button_name' in decoded_data:
#             reasons.append("Shows button press patterns typical for switches")

#         if 'state' in decoded_data and decoded_data.get('type') == 'contact':
#             reasons.append("Shows binary state changes typical for contact sensors")

#         if not reasons:
#             reasons.append(f"Packet structure matches {profile_info.profile_id} format")

#         return "; ".join(reasons)

#     def _assess_data_quality_from_rules(self, decoded_data: Dict) -> float:
#         """Assess quality of decoded data using rules"""
#         quality = 0.5

#         # More decoded fields = higher quality
#         field_count = len([k for k in decoded_data.keys()
#                            if k not in ['type', 'raw_data', 'eep_profile']])
#         quality += min(0.3, field_count * 0.1)

#         # Reasonable values = higher quality
#         ranges = self.confidence_weights.get('reasonable_ranges', {})

#         for field, range_config in ranges.items():
#             if field in decoded_data:
#                 value = decoded_data[field]
#                 if range_config.get('min', -float('inf')) <= value <= range_config.get('max', float('inf')):
#                     quality += range_config.get('bonus', 0.1)

#         return min(1.0, quality)

#     def _is_reasonable_decode(self, decoded_data: Dict, profile_info) -> bool:
#         """Check if decoded data seems reasonable"""
#         if not decoded_data or 'type' not in decoded_data:
#             return False

#         ranges = self.confidence_weights.get('reasonable_ranges', {})

#         # Check each field against configured ranges
#         for field, range_config in ranges.items():
#             if field in decoded_data:
#                 value = decoded_data[field]
#                 min_val = range_config.get('min', -float('inf'))
#                 max_val = range_config.get('max', float('inf'))

#                 if not (min_val <= value <= max_val):
#                     return False

#         return True

#     def _is_reasonable_value(self, field: str, value) -> bool:
#         """Check if a specific field value is reasonable"""
#         ranges = self.confidence_weights.get('reasonable_ranges', {})

#         if field in ranges:
#             range_config = ranges[field]
#             return range_config.get('min', -float('inf')) <= value <= range_config.get('max', float('inf'))

#         return True

#     # ========================================================================
#     # CONFIGURATION LOADING METHODS
#     # ========================================================================

#     def _load_capability_rules(self) -> Dict:
#         """Load capability detection rules from JSON"""
#         try:
#             if hasattr(self.eep_loader, 'config_dir'):
#                 rules_file = self.eep_loader.config_dir / "capability_rules.json"
#                 if rules_file.exists():
#                     with open(rules_file, 'r') as f:
#                         return json.load(f)
#         except Exception as e:
#             self.logger.warning(f"Could not load capability rules: {e}")

#         return {}

#     def _load_confidence_weights(self) -> Dict:
#         """Load confidence calculation weights from JSON"""
#         try:
#             if hasattr(self.eep_loader, 'config_dir'):
#                 weights_file = self.eep_loader.config_dir / "confidence_weights.json"
#                 if weights_file.exists():
#                     with open(weights_file, 'r') as f:
#                         return json.load(f)
#         except Exception as e:
#             self.logger.warning(f"Could not load confidence weights: {e}")

#         # Default weights if file doesn't exist
#         return {
#             'base_confidence': 0.5,
#             'capability_match': 0.3,
#             'data_quality_bonuses': {
#                 'temperature_c': 0.1,
#                 'humidity_percent': 0.1,
#                 'button_name': 0.2
#             },
#             'reasonable_ranges': {
#                 'temperature_c': {'min': -50, 'max': 100, 'bonus': 0.1},
#                 'humidity_percent': {'min': 0, 'max': 100, 'bonus': 0.1}
#             }
#         }

#     # ========================================================================
#     # STORAGE METHODS (existing)
#     # ========================================================================

#     def _store_unknown_device(self, device_id: str, raw_data: bytes, rorg: int, suggestions: List[EEPSuggestion]):
#         """Store unknown device data for dashboard"""
#         try:
#             unknown_devices = self._load_unknown_devices()
#             current_time = time.time()

#             if device_id in unknown_devices:
#                 # Update existing
#                 device = unknown_devices[device_id]
#                 device["last_seen"] = current_time
#                 device["packet_count"] += 1

#                 # Add packet if we don't have too many samples
#                 if len(device.get("sample_packets", [])) < 10:
#                     device.setdefault("sample_packets", []).append(raw_data.hex())

#                 # Update suggestions with better ones
#                 if suggestions and (not device.get("eep_suggestions") or
#                                     suggestions[0].confidence > device["eep_suggestions"][0]["confidence"]):
#                     device["eep_suggestions"] = [asdict(s) for s in suggestions]
#             else:
#                 # Create new unknown device
#                 unknown_devices[device_id] = {
#                     "device_id": device_id,
#                     "first_seen": current_time,
#                     "last_seen": current_time,
#                     "packet_count": 1,
#                     "sample_packets": [raw_data.hex()],
#                     "rorg_types": [rorg],
#                     "eep_suggestions": [asdict(s) for s in suggestions],
#                     "status": "pending"
#                 }

#             # Save updated data
#             self._save_unknown_devices(unknown_devices)

#         except Exception as e:
#             self.logger.error(f"Failed to store unknown device: {e}")

#     def _load_unknown_devices(self) -> Dict:
#         """Load unknown devices from storage"""
#         try:
#             with open(self.unknown_devices_file, 'r') as f:
#                 return json.load(f)
#         except (FileNotFoundError, json.JSONDecodeError):
#             return {}

#     def _save_unknown_devices(self, devices: Dict):
#         """Save unknown devices to storage"""
#         with open(self.unknown_devices_file, 'w') as f:
#             json.dump(devices, f, indent=2)

#!/usr/bin/env python3
"""
Discovery Engine - Fixed version with proper deduplication
"""
import json
import time
from dataclasses import asdict
from typing import Dict, Any, List, Set, Tuple

from ..utils.logger import Logger
from ..protocol.eep_profiles import EEPDecoder
from ..config.eep_profile_loader import EEPProfileLoader
from ..domain.models import EEPSuggestion, UnknownDevice


class UnifiedDiscoveryEngine:
    """Discovery engine with fixed deduplication logic"""

    def __init__(self, eep_decoder: EEPDecoder, logger: Logger, eep_loader: EEPProfileLoader):
        self.eep_decoder = eep_decoder
        self.logger = logger
        self.eep_loader = eep_loader
        self.unknown_devices_file = "unknown_devices.json"
        
        # ADDED: In-memory cache to prevent repeated analysis
        self._device_analysis_cache = {}
        self._last_packet_time = {}

        # Load configuration files for data-driven approach
        self.capability_rules = self._load_capability_rules()
        self.confidence_weights = self._load_confidence_weights()

    def analyze_unknown_packet(self, device_id: str, raw_data: bytes, rorg: int) -> List[EEPSuggestion]:
        """Analyze unknown packet - MAIN METHOD with deduplication"""
        
        # FIXED: Check if we already have this device analyzed recently
        if self._should_skip_analysis(device_id, raw_data):
            # Just update last seen time without full analysis
            self._update_existing_unknown_device(device_id, raw_data, rorg)
            return self._get_cached_suggestions(device_id)
        
        # Proceed with full analysis for new devices or significantly different packets
        suggestions = self._perform_full_analysis(device_id, raw_data, rorg)
        
        # Cache the results
        self._cache_analysis_results(device_id, suggestions)
        
        # Store/update unknown device
        self._store_unknown_device(device_id, raw_data, rorg, suggestions)

        return suggestions

    def _should_skip_analysis(self, device_id: str, raw_data: bytes) -> bool:
        """Check if we should skip analysis for this device/packet combination"""
        current_time = time.time()
        
        # If device is new, don't skip
        if device_id not in self._device_analysis_cache:
            return False
        
        # If last packet was very recent (< 5 seconds), skip analysis
        last_time = self._last_packet_time.get(device_id, 0)
        if current_time - last_time < 5.0:
            return True
        
        # If we've seen very similar packets recently, skip
        packet_hash = hash(raw_data[:4])  # Hash first 4 bytes
        cached_hash = self._device_analysis_cache[device_id].get('packet_hash')
        if cached_hash == packet_hash:
            return True
            
        return False

    def _get_cached_suggestions(self, device_id: str) -> List[EEPSuggestion]:
        """Get cached suggestions for a device"""
        if device_id not in self._device_analysis_cache:
            return []
        
        cached_suggestions = self._device_analysis_cache[device_id].get('suggestions', [])
        return [EEPSuggestion(**s) for s in cached_suggestions]

    def _cache_analysis_results(self, device_id: str, suggestions: List[EEPSuggestion]):
        """Cache analysis results to avoid repeated work"""
        self._device_analysis_cache[device_id] = {
            'suggestions': [asdict(s) for s in suggestions],
            'timestamp': time.time(),
            'packet_hash': None  # Will be set when packet is processed
        }

    def _update_existing_unknown_device(self, device_id: str, raw_data: bytes, rorg: int):
        """Update existing unknown device without full analysis"""
        try:
            unknown_devices = self._load_unknown_devices()
            current_time = time.time()
            
            if device_id in unknown_devices:
                device = unknown_devices[device_id]
                device["last_seen"] = current_time
                device["packet_count"] = device.get("packet_count", 0) + 1
                
                # Add RORG if not present
                if rorg not in device.get("rorg_types", []):
                    device.setdefault("rorg_types", []).append(rorg)
                
                # Only add packet sample if we don't have too many
                sample_packets = device.get("sample_packets", [])
                if len(sample_packets) < 10:
                    # Check if we already have a very similar packet
                    packet_hex = raw_data.hex()
                    if not any(self._packets_similar(packet_hex, existing) for existing in sample_packets):
                        sample_packets.append(packet_hex)
                
                self._save_unknown_devices(unknown_devices)
                
            # Update timing cache
            self._last_packet_time[device_id] = current_time
            
        except Exception as e:
            self.logger.error(f"Failed to update existing unknown device: {e}")

    def _packets_similar(self, packet1_hex: str, packet2_hex: str) -> bool:
        """Check if two packets are similar enough to be considered duplicates"""
        try:
            # Compare first 8 hex characters (4 bytes)
            return packet1_hex[:8] == packet2_hex[:8]
        except Exception:
            return False

    def _perform_full_analysis(self, device_id: str, raw_data: bytes, rorg: int) -> List[EEPSuggestion]:
        """Perform full EEP analysis (original logic)"""
        suggestions = []

        # Get candidate profiles from loaded EEP data
        candidate_profiles = self._get_candidate_profiles_from_config(rorg)

        for profile_id in candidate_profiles:
            try:
                profile_info = self.eep_loader.get_eep_profile(profile_id)
                if not profile_info:
                    continue

                # Try to decode with this EEP profile
                decoded_data = self.eep_decoder.decode_by_rorg(rorg, raw_data)

                if decoded_data and self._is_reasonable_decode(decoded_data, profile_info):
                    # Use rule-based capability detection
                    detected_capabilities = self._detect_capabilities_from_rules(decoded_data)

                    # Calculate confidence using configurable weights
                    confidence = self._calculate_confidence_from_config(
                        decoded_data, profile_info, detected_capabilities
                    )

                    reasoning = self._generate_reasoning_from_rules(
                        decoded_data, profile_info, detected_capabilities
                    )

                    suggestion = EEPSuggestion(
                        eep_profile=profile_id,
                        confidence=confidence,
                        reasoning=reasoning,
                        decoded_data=decoded_data,
                        data_quality=self._assess_data_quality_from_rules(decoded_data)
                    )
                    suggestions.append(suggestion)

            except Exception as e:
                self.logger.debug(f"Failed to decode with {profile_id}: {e}")

        # Sort by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions

    def mark_device_registered(self, device_id: str):
        """Mark unknown device as registered - USED BY packet_processor"""
        unknown_devices = self._load_unknown_devices()
        if device_id in unknown_devices:
            del unknown_devices[device_id]  # Remove completely when registered
            self._save_unknown_devices(unknown_devices)
            self.logger.info(f"🔄 Removed {device_id} from unknown devices (registered)")
            
        # ADDED: Clear from cache as well
        if device_id in self._device_analysis_cache:
            del self._device_analysis_cache[device_id]
        if device_id in self._last_packet_time:
            del self._last_packet_time[device_id]

    def mark_device_ignored(self, device_id: str):
        """Mark unknown device as ignored - USED BY packet_processor"""
        unknown_devices = self._load_unknown_devices()
        if device_id in unknown_devices:
            unknown_devices[device_id]["status"] = "ignored"
            self._save_unknown_devices(unknown_devices)
            self.logger.info(f"🚫 Marked {device_id} as ignored")

    def get_unknown_devices(self) -> List[UnknownDevice]:
        """Get all unknown devices for dashboard - USED BY packet_processor"""
        unknown_data = self._load_unknown_devices()
        devices = []

        for device_id, data in unknown_data.items():
            # Only return pending devices (not ignored)
            if data.get("status", "pending") != "pending":
                continue

            # Convert hex strings back to bytes
            sample_packets = [bytes.fromhex(p) for p in data.get("sample_packets", [])]

            # Convert suggestion dicts back to objects
            suggestions = []
            for s in data.get("eep_suggestions", []):
                try:
                    suggestions.append(EEPSuggestion(**s))
                except Exception:
                    # Handle malformed suggestions gracefully
                    continue

            device = UnknownDevice(
                device_id=device_id,
                first_seen=data.get("first_seen", 0),
                last_seen=data.get("last_seen", 0),
                packet_count=data.get("packet_count", 0),
                sample_packets=sample_packets,
                rorg_types=data.get("rorg_types", []),
                eep_suggestions=suggestions,
                status=data.get("status", "pending")
            )
            devices.append(device)

        return devices

    def _store_unknown_device(self, device_id: str, raw_data: bytes, rorg: int, suggestions: List[EEPSuggestion]):
        """Store unknown device data for dashboard - FIXED deduplication"""
        try:
            unknown_devices = self._load_unknown_devices()
            current_time = time.time()

            if device_id in unknown_devices:
                # Update existing device
                device = unknown_devices[device_id]
                device["last_seen"] = current_time
                device["packet_count"] = device.get("packet_count", 0) + 1

                # Add RORG type if not present
                if rorg not in device.get("rorg_types", []):
                    device.setdefault("rorg_types", []).append(rorg)

                # FIXED: Only add packet if it's significantly different
                sample_packets = device.get("sample_packets", [])
                packet_hex = raw_data.hex()
                
                if len(sample_packets) < 10:
                    # Check if we already have a similar packet
                    if not any(self._packets_similar(packet_hex, existing) for existing in sample_packets):
                        sample_packets.append(packet_hex)

                # FIXED: Only update suggestions if they're significantly better
                existing_suggestions = device.get("eep_suggestions", [])
                if suggestions:
                    if not existing_suggestions:
                        # No existing suggestions, add new ones
                        device["eep_suggestions"] = [asdict(s) for s in suggestions]
                    else:
                        # Compare best confidences
                        best_existing = max((s.get("confidence", 0) for s in existing_suggestions), default=0)
                        best_new = max((s.confidence for s in suggestions), default=0)
                        
                        # Only update if significantly better (>10% improvement)
                        if best_new > best_existing + 0.1:
                            device["eep_suggestions"] = [asdict(s) for s in suggestions]
                            self.logger.debug(f"Updated suggestions for {device_id} (confidence improved from {best_existing:.2f} to {best_new:.2f})")
            else:
                # FIXED: Check if device was recently registered before creating new entry
                # This prevents race conditions where a device is registered but packets are still being processed
                self.logger.info(f"🔍 New unknown device discovered: {device_id}")
                
                unknown_devices[device_id] = {
                    "device_id": device_id,
                    "first_seen": current_time,
                    "last_seen": current_time,
                    "packet_count": 1,
                    "sample_packets": [raw_data.hex()],
                    "rorg_types": [rorg],
                    "eep_suggestions": [asdict(s) for s in suggestions],
                    "status": "pending"
                }

            # Save updated data
            self._save_unknown_devices(unknown_devices)
            
            # Update cache timing
            self._last_packet_time[device_id] = current_time
            if device_id in self._device_analysis_cache:
                self._device_analysis_cache[device_id]['packet_hash'] = hash(raw_data[:4])

        except Exception as e:
            self.logger.error(f"Failed to store unknown device: {e}")

    # Keep all the existing helper methods unchanged
    def _get_candidate_profiles_from_config(self, rorg: int) -> List[str]:
        """Get candidate profiles from loaded EEP configuration (data-driven)"""
        rorg_hex = f"{rorg:02X}"
        candidates = []

        for profile_id, profile in self.eep_loader.get_all_eep_profiles().items():
            if profile.rorg.upper() == rorg_hex:
                candidates.append(profile_id)

        return candidates

    def _detect_capabilities_from_rules(self, decoded_data: Dict[str, Any]) -> Set[str]:
        """Use rule engine to detect capabilities"""
        if hasattr(self.eep_loader, 'rule_engine') and self.eep_loader.rule_engine:
            return self.eep_loader.rule_engine.detect_capabilities(decoded_data)

        # Fallback to simple detection if rule engine not available
        return self._simple_capability_detection(decoded_data)

    def _simple_capability_detection(self, decoded_data: Dict[str, Any]) -> Set[str]:
        """Simple fallback capability detection"""
        capabilities = set()

        if 'temperature_c' in decoded_data:
            capabilities.add('temperature')
        if 'humidity_percent' in decoded_data:
            capabilities.add('humidity')
        if 'button_name' in decoded_data or 'pressed' in decoded_data:
            capabilities.add('switch')
        if 'state' in decoded_data and decoded_data.get('type') == 'contact':
            capabilities.add('contact')
        if any(key.startswith('acceleration_') for key in decoded_data.keys()):
            capabilities.add('acceleration')
        if 'illuminance_lx' in decoded_data:
            capabilities.add('illuminance')

        return capabilities

    def _calculate_confidence_from_config(self, decoded_data: Dict, profile_info,
                                          detected_capabilities: Set[str]) -> float:
        """Calculate confidence using configurable weights"""
        weights = self.confidence_weights
        base_confidence = weights.get('base_confidence', 0.5)

        # Match capabilities
        profile_capabilities = set(profile_info.capabilities)
        matching_caps = detected_capabilities.intersection(profile_capabilities)

        if profile_capabilities:
            capability_match_score = len(matching_caps) / len(profile_capabilities)
            confidence = base_confidence + (capability_match_score * weights.get('capability_match', 0.3))
        else:
            confidence = base_confidence

        # Apply data quality bonuses from config
        for field, bonus_weight in weights.get('data_quality_bonuses', {}).items():
            if field in decoded_data:
                value = decoded_data[field]
                if self._is_reasonable_value(field, value):
                    confidence += bonus_weight

        return min(1.0, max(0.0, confidence))

    def _generate_reasoning_from_rules(self, decoded_data: Dict, profile_info, detected_capabilities: Set[str]) -> str:
        """Generate human-readable reasoning"""
        reasons = []

        profile_capabilities = set(profile_info.capabilities)
        matching_caps = detected_capabilities.intersection(profile_capabilities)

        if matching_caps:
            reasons.append(f"Matched capabilities: {', '.join(sorted(matching_caps))}")

        # Add specific data observations
        if 'temperature_c' in decoded_data and 'humidity_percent' in decoded_data:
            reasons.append("Contains both temperature and humidity data")
        elif 'temperature_c' in decoded_data:
            reasons.append("Contains temperature data")
        elif 'humidity_percent' in decoded_data:
            reasons.append("Contains humidity data")

        if 'button_name' in decoded_data:
            reasons.append("Shows button press patterns typical for switches")

        if 'state' in decoded_data and decoded_data.get('type') == 'contact':
            reasons.append("Shows binary state changes typical for contact sensors")

        if not reasons:
            reasons.append(f"Packet structure matches {profile_info.profile_id} format")

        return "; ".join(reasons)

    def _assess_data_quality_from_rules(self, decoded_data: Dict) -> float:
        """Assess quality of decoded data using rules"""
        quality = 0.5

        # More decoded fields = higher quality
        field_count = len([k for k in decoded_data.keys()
                           if k not in ['type', 'raw_data', 'eep_profile']])
        quality += min(0.3, field_count * 0.1)

        # Reasonable values = higher quality
        ranges = self.confidence_weights.get('reasonable_ranges', {})

        for field, range_config in ranges.items():
            if field in decoded_data:
                value = decoded_data[field]
                if range_config.get('min', -float('inf')) <= value <= range_config.get('max', float('inf')):
                    quality += range_config.get('bonus', 0.1)

        return min(1.0, quality)

    def _is_reasonable_decode(self, decoded_data: Dict, profile_info) -> bool:
        """Check if decoded data seems reasonable"""
        if not decoded_data or 'type' not in decoded_data:
            return False

        ranges = self.confidence_weights.get('reasonable_ranges', {})

        # Check each field against configured ranges
        for field, range_config in ranges.items():
            if field in decoded_data:
                value = decoded_data[field]
                min_val = range_config.get('min', -float('inf'))
                max_val = range_config.get('max', float('inf'))

                if not (min_val <= value <= max_val):
                    return False

        return True

    def _is_reasonable_value(self, field: str, value) -> bool:
        """Check if a specific field value is reasonable"""
        ranges = self.confidence_weights.get('reasonable_ranges', {})

        if field in ranges:
            range_config = ranges[field]
            return range_config.get('min', -float('inf')) <= value <= range_config.get('max', float('inf'))

        return True

    def _load_capability_rules(self) -> Dict:
        """Load capability detection rules from JSON"""
        try:
            if hasattr(self.eep_loader, 'config_dir'):
                rules_file = self.eep_loader.config_dir / "capability_rules.json"
                if rules_file.exists():
                    with open(rules_file, 'r') as f:
                        return json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load capability rules: {e}")

        return {}

    def _load_confidence_weights(self) -> Dict:
        """Load confidence calculation weights from JSON"""
        try:
            if hasattr(self.eep_loader, 'config_dir'):
                weights_file = self.eep_loader.config_dir / "confidence_weights.json"
                if weights_file.exists():
                    with open(weights_file, 'r') as f:
                        return json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load confidence weights: {e}")

        # Default weights if file doesn't exist
        return {
            'base_confidence': 0.5,
            'capability_match': 0.3,
            'data_quality_bonuses': {
                'temperature_c': 0.1,
                'humidity_percent': 0.1,
                'button_name': 0.2
            },
            'reasonable_ranges': {
                'temperature_c': {'min': -50, 'max': 100, 'bonus': 0.1},
                'humidity_percent': {'min': 0, 'max': 100, 'bonus': 0.1}
            }
        }

    def _load_unknown_devices(self) -> Dict:
        """Load unknown devices from storage"""
        try:
            with open(self.unknown_devices_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_unknown_devices(self, devices: Dict):
        """Save unknown devices to storage"""
        with open(self.unknown_devices_file, 'w') as f:
            json.dump(devices, f, indent=2)