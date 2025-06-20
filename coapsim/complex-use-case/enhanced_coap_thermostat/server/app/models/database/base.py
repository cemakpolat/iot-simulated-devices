# app/models/database/base.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import declared_attr

Base = declarative_base()

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class UUIDMixin:
    """Mixin for UUID primary key."""
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model class with UUID and timestamps."""
    
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

# app/models/database/user.py
from sqlalchemy import Column, String, Boolean, JSON
from .base import BaseModel

class User(BaseModel):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    roles = Column(JSON, default=list)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

# app/models/database/device.py
from sqlalchemy import Column, String, Boolean, JSON, ForeignKey
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