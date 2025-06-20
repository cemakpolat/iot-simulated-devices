# app/models/database/user.py
from sqlalchemy import Column, String, Boolean, JSON, DateTime
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

