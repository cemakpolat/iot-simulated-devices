#!/usr/bin/env python3
"""
EEP Profile Loader - External Configuration Management
Loads device profiles, types, and locations from external JSON files
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from ..utils.logger import Logger

logger = Logger()

@dataclass
class EEPProfile:
    """EEP Profile with capabilities and metadata"""
    profile_id: str
    description: str
    data_length: int
    capabilities: List[str]
    rorg: str


@dataclass
class LocationInfo:
    """Location information"""
    name: str
    building: str
    floor: int
    zone: str


class CapabilityRuleEngine:
    """Loads and executes capability detection rules from a JSON file."""

    def __init__(self, rules_file: Path, logger):
        self.logger = logger
        self.rules = self._load_rules(rules_file)

        # This dispatcher maps rule 'type' from JSON to a handler function
        self.check_handlers = {
            "key_exists": self._handle_key_exists,
            "is_true": self._handle_is_true,
            "value_in": self._handle_value_in,
            "any_key_exists": self._handle_any_key_exists,
        }
        self.logger.info(f"⚙️ Capability Rule Engine initialized with {len(self.rules)} capabilities.")

    def _load_rules(self, rules_file: Path) -> Dict:
        """Loads the capability detection rules from the JSON file."""
        if not rules_file.exists():
            self.logger.error(f"Capability rules file not found at {rules_file}!")
            return {}
        try:
            with rules_file.open('r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            self.logger.error(f"Error loading capability rules: {e}")
            return {}

    def detect_capabilities(self, decoded_data: Dict[str, Any]) -> Set[str]:
        """
        Applies all loaded rules to the decoded data to determine which
        capabilities are present.
        """
        detected = set()
        for capability, definition in self.rules.items():
            rules_list = definition.get("rules", [])
            if not rules_list:
                continue

            # All rules for a capability must pass (AND logic)
            if all(self._execute_rule(rule, decoded_data) for rule in rules_list):
                detected.add(capability)

        return detected

    def _execute_rule(self, rule: Dict, data: Dict) -> bool:
        """Executes a single rule by calling the appropriate handler."""
        rule_type = rule.get("type")
        handler = self.check_handlers.get(rule_type)
        if not handler:
            self.logger.warning(f"Unknown rule type '{rule_type}' encountered.")
            return False

        try:
            return handler(rule, data)
        except KeyError as e:
            # A key required by the rule is missing from the data; this is a failure.
            return False

    # --- Rule Handler Implementations ---

    def _handle_key_exists(self, rule: Dict, data: Dict) -> bool:
        return rule["key"] in data

    def _handle_is_true(self, rule: Dict, data: Dict) -> bool:
        return data.get(rule["key"]) is True

    def _handle_value_in(self, rule: Dict, data: Dict) -> bool:
        return data.get(rule["key"]) in rule["values"]

    def _handle_any_key_exists(self, rule: Dict, data: Dict) -> bool:
        return any(key in data for key in rule["keys"])

class EEPProfileLoader:
    """
    Loads and manages EEP profiles and device configurations from external files
    Allows easy extension without code changes
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.eep_profiles: Dict[str, EEPProfile] = {}
        self.device_types: Dict[str, Dict[str, Any]] = {}
        self.locations: Dict[str, LocationInfo] = {}

        # Configuration file paths
        self.eep_profiles_file = self.config_dir / "eep_profiles.json"
        self.device_types_file = self.config_dir / "device_types.json"
        self.locations_file = self.config_dir / "locations.json"

        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)

        # Load all configurations
        self._load_all_configurations()

        self.capability_rules_file = self.config_dir / "capability_rules.json"

        # Create the engine instance here
        self.rule_engine = CapabilityRuleEngine(self.capability_rules_file,
                                                logger)  # You'll need to pass a logger

        print(f"✅ EEP Profile Loader initialized with {len(self.eep_profiles)} profiles")

    def _load_all_configurations(self):
        """Load all configuration files"""
        try:
            self._load_eep_profiles()
            self._load_device_types()
            self._load_locations()
        except Exception as e:
            print(f"⚠️ Error loading configurations: {e}")
            self._create_default_configs()

    def _load_eep_profiles(self):
        """Load EEP profiles from external JSON file"""
        if self.eep_profiles_file.exists():
            try:
                with open(self.eep_profiles_file, 'r') as f:
                    data = json.load(f)

                # Handle both your format and standalone format
                if "eep_profiles" in data:
                    profiles_data = data["eep_profiles"]
                else:
                    profiles_data = data

                for profile_id, profile_info in profiles_data.items():
                    self.eep_profiles[profile_id] = EEPProfile(
                        profile_id=profile_id,
                        description=profile_info["description"],
                        data_length=profile_info["data_length"],
                        capabilities=profile_info["capabilities"],
                        rorg=profile_info["rorg"]
                    )

                print(f"📋 Loaded {len(self.eep_profiles)} EEP profiles")

            except Exception as e:
                print(f"❌ Error loading EEP profiles: {e}")
                self._create_default_eep_profiles()
        else:
            print("📋 No EEP profiles file found, creating default")
            self._create_default_eep_profiles()

    def _load_device_types(self):
        """Load device type definitions"""
        if self.device_types_file.exists():
            try:
                with open(self.device_types_file, 'r') as f:
                    self.device_types = json.load(f)
                print(f"🏷️ Loaded {len(self.device_types)} device types")
            except Exception as e:
                print(f"❌ Error loading device types: {e}")
                self._create_default_device_types()
        else:
            self._create_default_device_types()

    def _load_locations(self):
        """Load location hierarchy"""
        if self.locations_file.exists():
            try:
                with open(self.locations_file, 'r') as f:
                    locations_data = json.load(f)

                # Handle both your format and standalone format
                if "locations" in locations_data:
                    locations_data = locations_data["locations"]

                for name, info in locations_data.items():
                    self.locations[name] = LocationInfo(
                        name=name,
                        building=info["building"],
                        floor=info["floor"],
                        zone=info["zone"]
                    )

                print(f"📍 Loaded {len(self.locations)} locations")

            except Exception as e:
                print(f"❌ Error loading locations: {e}")
                self._create_default_locations()
        else:
            self._create_default_locations()

    def _create_default_configs(self):
        """Create default configuration files"""
        self._create_default_eep_profiles()
        self._create_default_device_types()
        self._create_default_locations()

    def _create_default_eep_profiles(self):
        """Create default EEP profiles file"""
        default_profiles = {
            "A5-04-01": {
                "description": "Temperature and humidity sensor",
                "data_length": 4,
                "capabilities": ["temperature", "humidity"],
                "rorg": "A5"
            },
            "F6-02-01": {
                "description": "Rocker switch",
                "data_length": 1,
                "capabilities": ["switch"],
                "rorg": "F6"
            },
            "D5-00-01": {
                "description": "Contact sensor",
                "data_length": 1,
                "capabilities": ["contact"],
                "rorg": "D5"
            },
            "D2-14-41": {
                "description": "Multi-sensor with magnet contact",
                "data_length": 9,
                "capabilities": ["temperature", "humidity", "acceleration", "illumination", "magnet_contact"],
                "rorg": "D2"
            }
        }

        with open(self.eep_profiles_file, 'w') as f:
            json.dump(default_profiles, f, indent=2)

        # Reload after creation
        self._load_eep_profiles()

    def _create_default_device_types(self):
        """Create default device types file"""
        default_types = {
            "temperature_sensor": {
                "name": "Temperature Sensor",
                "icon": "🌡️",
                "expected_capabilities": ["temperature"],
                "typical_interval": 300
            },
            "temp_humidity_sensor": {
                "name": "Temperature & Humidity Sensor",
                "icon": "🌡️💧",
                "expected_capabilities": ["temperature", "humidity"],
                "typical_interval": 300
            },
            "rocker_switch": {
                "name": "Rocker Switch",
                "icon": "🔘",
                "expected_capabilities": ["switch"],
                "typical_interval": 0
            },
            "contact_sensor": {
                "name": "Contact Sensor",
                "icon": "🚪",
                "expected_capabilities": ["contact"],
                "typical_interval": 0
            },
            "multi_sensor_magnet": {
                "name": "Multi-sensor with Magnet",
                "icon": "📊🧲",
                "expected_capabilities": ["temperature", "humidity", "acceleration", "illumination", "magnet_contact"],
                "typical_interval": 600
            }
        }

        with open(self.device_types_file, 'w') as f:
            json.dump(default_types, f, indent=2)

        self.device_types = default_types

    def _create_default_locations(self):
        """Create default locations file"""
        default_locations = {
            "Kitchen": {
                "building": "Main",
                "floor": 1,
                "zone": "residential"
            },
            "Warehouse": {
                "building": "Storage",
                "floor": 1,
                "zone": "industrial"
            },
            "Workstation": {
                "building": "Main",
                "floor": 2,
                "zone": "work"
            },
            "Unknown": {
                "building": "Main",
                "floor": 1,
                "zone": "general"
            }
        }

        with open(self.locations_file, 'w') as f:
            json.dump(default_locations, f, indent=2)

        # Reload after creation
        self._load_locations()

    # ========================================================================
    # Public API Methods
    # ========================================================================

    def get_eep_profile(self, profile_id: str) -> Optional[EEPProfile]:
        """Get specific EEP profile"""
        return self.eep_profiles.get(profile_id)

    def get_all_eep_profiles(self) -> Dict[str, EEPProfile]:
        """Get all EEP profiles"""
        return self.eep_profiles.copy()

    def get_profiles_by_rorg(self, rorg: str) -> List[EEPProfile]:
        """Get EEP profiles filtered by RORG"""
        return [
            profile for profile in self.eep_profiles.values()
            if profile.rorg.upper() == rorg.upper()
        ]

    def get_profiles_by_capability(self, capability: str) -> List[EEPProfile]:
        """Get EEP profiles that have a specific capability"""
        return [
            profile for profile in self.eep_profiles.values()
            if capability in profile.capabilities
        ]

    def validate_eep_profile(self, profile_id: str) -> bool:
        """Check if EEP profile exists and is valid"""
        return profile_id in self.eep_profiles

    def get_device_type_info(self, device_type: str) -> Optional[Dict[str, Any]]:
        """Get device type information"""
        return self.device_types.get(device_type)

    def get_all_device_types(self) -> Dict[str, Dict[str, Any]]:
        """Get all device types"""
        return self.device_types.copy()

    def get_location_info(self, location_name: str) -> Optional[LocationInfo]:
        """Get location information"""
        return self.locations.get(location_name)

    def get_all_locations(self) -> Dict[str, LocationInfo]:
        """Get all locations"""
        return self.locations.copy()

    def get_locations_by_building(self, building: str) -> List[LocationInfo]:
        """Get locations filtered by building"""
        return [
            location for location in self.locations.values()
            if location.building == building
        ]

    def suggest_eep_profiles_for_rorg(self, rorg: int, decoded_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Suggest EEP profiles for a given RORG based on decoded data
        Used by discovery engine for intelligent suggestions
        """
        rorg_hex = f"{rorg:02X}"
        candidates = self.get_profiles_by_rorg(rorg_hex)

        suggestions = []
        for profile in candidates:
            confidence = 0.5  # Base confidence
            reasoning_parts = []

            # Increase confidence based on capability matching
            if decoded_data:
                matching_capabilities = []

                # Check for temperature data
                if "temperature_c" in decoded_data and "temperature" in profile.capabilities:
                    confidence += 0.2
                    matching_capabilities.append("temperature")

                # Check for humidity data
                if "humidity_percent" in decoded_data and "humidity" in profile.capabilities:
                    confidence += 0.2
                    matching_capabilities.append("humidity")

                # Check for switch/button data
                if "button_name" in decoded_data and "switch" in profile.capabilities:
                    confidence += 0.3
                    matching_capabilities.append("switch")

                # Check for contact data
                if "state" in decoded_data and "contact" in profile.capabilities:
                    confidence += 0.3
                    matching_capabilities.append("contact")

                if matching_capabilities:
                    reasoning_parts.append(f"Detected {', '.join(matching_capabilities)} data")

            # Add capability description
            if profile.capabilities:
                reasoning_parts.append(f"Can measure: {', '.join(profile.capabilities)}")

            suggestions.append({
                "eep_profile": profile.profile_id,
                "description": profile.description,
                "capabilities": profile.capabilities,
                "confidence": min(1.0, confidence),
                "reasoning": "; ".join(reasoning_parts) if reasoning_parts else "Standard profile match",
                "data_quality": 0.8  # Default quality
            })

        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions

    def reload_configurations(self):
        """Reload all configuration files (for runtime updates)"""
        print("🔄 Reloading configurations...")
        self.eep_profiles.clear()
        self.device_types.clear()
        self.locations.clear()
        self._load_all_configurations()
        print("✅ Configurations reloaded")

    def export_current_config_template(self, output_dir: str = "config_template"):
        """Export current configuration as template for easy customization"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Export EEP profiles
        eep_export = {profile.profile_id: {
            "description": profile.description,
            "data_length": profile.data_length,
            "capabilities": profile.capabilities,
            "rorg": profile.rorg
        } for profile in self.eep_profiles.values()}

        with open(output_path / "eep_profiles_template.json", 'w') as f:
            json.dump(eep_export, f, indent=2)

        # Export device types
        with open(output_path / "device_types_template.json", 'w') as f:
            json.dump(self.device_types, f, indent=2)

        # Export locations
        locations_export = {name: {
            "building": loc.building,
            "floor": loc.floor,
            "zone": loc.zone
        } for name, loc in self.locations.items()}

        with open(output_path / "locations_template.json", 'w') as f:
            json.dump(locations_export, f, indent=2)

        print(f"📤 Configuration templates exported to {output_path}")


print("✅ EEP Profile Loader ready for external configuration management")