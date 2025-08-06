
# utils/graceful_degradation.py
from typing import Dict, Any, Optional, Callable
from enum import Enum

from enocean_gateway.utils import Logger


class ServiceLevel(Enum):
    """Service degradation levels"""
    FULL = "full"  # All features available
    REDUCED = "reduced"  # Some features disabled
    MINIMAL = "minimal"  # Only core features
    EMERGENCY = "emergency"  # Critical functions only


class GracefulDegradation:
    """Manages graceful service degradation under stress"""

    def __init__(self, logger: Logger):
        self.logger = logger
        self._current_level = ServiceLevel.FULL
        self._feature_registry: Dict[str, Dict[ServiceLevel, Optional[Callable]]] = {}
        self._metrics = {
            "degradation_events": 0,
            "current_level": ServiceLevel.FULL.value,
            "disabled_features": []
        }

    def register_feature(self, name: str, implementations: Dict[ServiceLevel, Optional[Callable]]):
        """Register a feature with different implementation levels"""
        self._feature_registry[name] = implementations
        self.logger.debug(f"Registered feature '{name}' with {len(implementations)} levels")

    def get_implementation(self, feature_name: str) -> Optional[Callable]:
        """Get the appropriate implementation for current service level"""
        if feature_name not in self._feature_registry:
            self.logger.warning(f"Unknown feature requested: {feature_name}")
            return None

        implementations = self._feature_registry[feature_name]

        # Try current level first, then fall back to lower levels
        for level in [self._current_level, ServiceLevel.REDUCED, ServiceLevel.MINIMAL, ServiceLevel.EMERGENCY]:
            if level in implementations and implementations[level] is not None:
                return implementations[level]

        self.logger.warning(f"No implementation available for feature '{feature_name}' at any level")
        return None

    def degrade_to(self, level: ServiceLevel, reason: str = "Unknown"):
        """Degrade service to specified level"""
        if level != self._current_level:
            old_level = self._current_level
            self._current_level = level
            self._metrics["degradation_events"] += 1
            self._metrics["current_level"] = level.value

            # Update disabled features list
            disabled = []
            for feature_name, implementations in self._feature_registry.items():
                if level not in implementations or implementations[level] is None:
                    disabled.append(feature_name)

            self._metrics["disabled_features"] = disabled

            self.logger.warning(
                f"Service degraded from {old_level.value} to {level.value}. "
                f"Reason: {reason}. Disabled features: {disabled}"
            )

    def recover_to(self, level: ServiceLevel):
        """Attempt to recover service to higher level"""
        if level.value > self._current_level.value:  # Assuming enum values increase with capability
            old_level = self._current_level
            self._current_level = level
            self._metrics["current_level"] = level.value

            # Update disabled features list
            disabled = []
            for feature_name, implementations in self._feature_registry.items():
                if level not in implementations or implementations[level] is None:
                    disabled.append(feature_name)

            self._metrics["disabled_features"] = disabled

            self.logger.info(
                f"Service recovered from {old_level.value} to {level.value}. "
                f"Remaining disabled features: {disabled}"
            )

    @property
    def current_level(self) -> ServiceLevel:
        """Get current service level"""
        return self._current_level

    def get_metrics(self) -> Dict[str, Any]:
        """Get degradation metrics"""
        return self._metrics.copy()
