# server/app/database/models.py
# (Existing imports and Pydantic models)

from sqlalchemy import Column, String, DateTime, Boolean, JSON # JSON for roles if flexible
from sqlalchemy.orm import declarative_base # or sessionmaker
from datetime import datetime, timezone 
import uuid

Base = declarative_base() # Base class for SQLAlchemy models

class User(Base):
    __tablename__ = "users" # Define table name

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())) # UUID for user ID
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False) # Store hashed passwords, NEVER plain
    roles = Column(JSON, default=['user']) # E.g., ['user', 'admin']
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc)) # Use timezone.utc for default

    last_login_at = Column(DateTime, nullable=True)

    # You might also have a Device model linked to users
    # class Device(Base):
    #     __tablename__ = "devices"
    #     id = Column(String, primary_key=True, index=True)
    #     user_id = Column(String, ForeignKey("users.id"))
    #     user = relationship("User", back_populates="devices")
    #     # ... other device details

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
