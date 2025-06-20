# app/services/base.py
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseService(ABC):
    """Base service class with common functionality."""
    
    def __init__(self, name: str = None):
        self.logger = logging.getLogger(name or self.__class__.__name__)
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the service. Override in subclasses."""
        self._initialized = True
        self.logger.info(f"{self.__class__.__name__} initialized")
        return True
    
    async def cleanup(self) -> None:
        """Cleanup resources. Override in subclasses."""
        self._initialized = False
        self.logger.info(f"{self.__class__.__name__} cleaned up")
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    def _validate_initialized(self):
        """Ensure service is initialized before operations."""
        if not self._initialized:
            raise RuntimeError(f"{self.__class__.__name__} not initialized")

