# app/models/database/device.py
from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class Device(BaseModel):
    """Device model for thermostat devices."""
    
    __tablename__ = "devices"
    
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    device_type = Column(String(50), default="thermostat")
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    configuration = Column(JSON, default=dict)
    location = Column(String(200), nullable=True)
    firmware_version = Column(String(50), nullable=True)
    
    # Relationships
    owner = relationship("User", backref="devices")
    
    def __repr__(self):
        return f"<Device(device_id='{self.device_id}', name='{self.name}')>"