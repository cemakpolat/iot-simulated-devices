# server/app/database/models.py - Enhanced User model
"""SQLAlchemy models with improvements"""
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone 
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    roles = Column(JSON, default=lambda: ['user'])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
    
    def to_dict(self):
        """Convert user to dictionary (excluding password)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'roles': self.roles,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None
        }

# You can add more models here for devices, etc.
class Device(Base):
    __tablename__ = "devices"
    
    id = Column(String(50), primary_key=True)
    user_id = Column(String, nullable=False)  # References User.id
    name = Column(String(100), nullable=False)
    device_type = Column(String(50), nullable=False)
    location = Column(String(100))
    room = Column(String(50))
    configuration = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Device(id='{self.id}', name='{self.name}', user_id='{self.user_id}')>"