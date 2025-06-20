# app/services/auth_service.py
"""Authentication service."""

import logging
from typing import Dict, Any
from datetime import timedelta
from sqlalchemy.orm import Session

from .base import BaseService
from ..core.security import SecurityService
from ..core.config import get_settings
from ..core.exceptions import AuthenticationError, ValidationError
from ..models.schemas.requests import LoginRequest, RegisterRequest
from ..models.schemas.responses import TokenResponse
from ..repositories.user_repository import UserRepository
from ..utils.validators import UserValidator

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService(BaseService):
    """Service for handling authentication operations."""
    
    def __init__(self, security_service: SecurityService):
        super().__init__()
        self.security_service = security_service
        self.validator = UserValidator()
    
    async def register_user(self, db: Session, user_data: RegisterRequest) -> Dict[str, Any]:
        """Register a new user."""
        user_repo = UserRepository(db)
        
        # Validate input
        self.validator.validate_username(user_data.username)
        self.validator.validate_email(user_data.email)
        self.validator.validate_password(user_data.password)
        
        # Check if username already exists
        if user_repo.get_by_username(user_data.username):
            raise ValidationError("Username already registered")
        
        # Check if email already exists
        if user_repo.get_by_email(user_data.email):
            raise ValidationError("Email already registered")
        
        # Hash password
        hashed_password = self.security_service.hash_password(user_data.password)
        
        # Create user
        user_create_data = {
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": hashed_password,
            "is_active": True,
            "roles": ["user"]
        }
        
        user = user_repo.create(user_create_data)
        
        logger.info(f"User registered: {user_data.username}")
        return {"user_id": str(user.id), "username": user.username}
    
    async def authenticate_user(self, db: Session, login_data: LoginRequest) -> TokenResponse:
        """Authenticate user and return token."""
        user_repo = UserRepository(db)
        
        # Get user
        user = user_repo.get_by_username(login_data.username)
        if not user:
            raise AuthenticationError("Invalid credentials")
        
        # Verify password
        if not self.security_service.verify_password(login_data.password, user.password_hash):
            raise AuthenticationError("Invalid credentials")
        
        # Check if user is active
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
        
        # Create access token
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "roles": user.roles or []
        }
        
        access_token = self.security_service.create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        # Update last login
        user_repo.update_last_login(str(user.id))
        
        logger.info(f"User authenticated: {user.username}")
        
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def refresh_token(self, token: str) -> TokenResponse:
        """Refresh an access token."""
        try:
            payload = self.security_service.decode_token(token)
            
            # Create new token with same payload
            new_token = self.security_service.create_access_token(
                data={
                    "sub": payload["sub"],
                    "username": payload["username"],
                    "roles": payload.get("roles", [])
                },
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            return TokenResponse(
                access_token=new_token,
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            
        except Exception as e:
            raise AuthenticationError(f"Token refresh failed: {str(e)}")
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a token and return user info."""
        try:
            payload = self.security_service.decode_token(token)
            return {
                "valid": True,
                "user_id": payload["sub"],
                "username": payload["username"],
                "roles": payload.get("roles", [])
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }

