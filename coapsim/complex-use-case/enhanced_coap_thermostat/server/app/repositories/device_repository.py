
# app/repositories/device_repository.py
"""Device data repository."""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from .base import BaseRepository
from ..models.database.device import Device
from ..core.exceptions import ValidationError


class DeviceRepository(BaseRepository[Device, dict, dict]):
    """Repository for device data operations."""
    
    def __init__(self, db: Session):
        super().__init__(Device, db)
    
    def get_by_device_id(self, device_id: str) -> Optional[Device]:
        """Get device by device_id."""
        return self.db.query(Device).filter(Device.device_id == device_id).first()
    
    def get_user_devices(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Device]:
        """Get all devices owned by a user."""
        return self.db.query(Device).filter(Device.owner_id == user_id).offset(skip).limit(limit).all()
    
    def get_online_devices(self) -> List[Device]:
        """Get all online devices."""
        return self.db.query(Device).filter(Device.is_online == True).all()
    
    def update_device_status(self, device_id: str, is_online: bool) -> bool:
        """Update device online status."""
        device = self.get_by_device_id(device_id)
        if device:
            device.is_online = is_online
            device.last_seen = datetime.now() if is_online else device.last_seen
            self.db.commit()
            return True
        return False
    
    def update_device_configuration(self, device_id: str, configuration: Dict[str, Any]) -> bool:
        """Update device configuration."""
        device = self.get_by_device_id(device_id)
        if device:
            device.configuration = configuration
            self.db.commit()
            return True
        return False
    
    def get_devices_by_type(self, device_type: str) -> List[Device]:
        """Get devices by type."""
        return self.db.query(Device).filter(Device.device_type == device_type).all()
    
    def search_devices(self, query: str, user_id: Optional[str] = None) -> List[Device]:
        """Search devices by name or device_id."""
        base_query = self.db.query(Device).filter(
            (Device.name.contains(query)) | (Device.device_id.contains(query))
        )
        
        if user_id:
            base_query = base_query.filter(Device.owner_id == user_id)
        
        return base_query.all()
    
    def verify_device_ownership(self, device_id: str, user_id: str) -> bool:
        """Verify that a user owns a specific device."""
        device = self.db.query(Device).filter(
            Device.device_id == device_id,
            Device.owner_id == user_id
        ).first()
        
    

