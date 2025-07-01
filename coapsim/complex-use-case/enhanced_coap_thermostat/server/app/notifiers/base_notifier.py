"""Base notification interface"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """Abstract base class for all notification types"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = True
        
    @abstractmethod
    async def send(self, alert_type: str, message: str, data: Dict[str, Any] = None) -> bool:
        """Send notification - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the notifier - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Cleanup resources - must be implemented by subclasses"""
        pass
    
    def disable(self):
        """Disable this notifier"""
        self.enabled = False
        logger.info(f"{self.__class__.__name__} disabled")
    
    def enable(self):
        """Enable this notifier"""
        self.enabled = True
        logger.info(f"{self.__class__.__name__} enabled")
    
    def is_enabled(self) -> bool:
        """Check if notifier is enabled"""
        return self.enabled
    
    def get_status(self) -> Dict[str, Any]:
        """Get notifier status information"""
        return {
            "name": self.__class__.__name__,
            "enabled": self.enabled,
            "config_keys": list(self.config.keys()) if self.config else []
        }