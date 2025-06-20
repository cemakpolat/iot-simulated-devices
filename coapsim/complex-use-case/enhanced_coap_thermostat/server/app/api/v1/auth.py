# app/api/v1/auth.py
"""Authentication endpoints."""

from typing import Annotated
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.dependencies import get_db, get_dependency_manager, get_current_user
from ...core.config import get_settings
from ...models.schemas.requests import LoginRequest, RegisterRequest
from ...models.schemas.responses import TokenResponse, UserResponse, SuccessResponse
from ...repositories.user_repository import UserRepository
from ...core.exceptions import AuthenticationError, ValidationError, create_http_exception

router = APIRouter(prefix="/auth")
settings = get_settings()


@router.post("/register", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Register a new user."""
    try:
        user_repo = UserRepository(db)
        
        # Check if username already exists
        if user_repo.get_by_username(user_data.username):
            raise ValidationError("Username already registered")
        
        # Check if email already exists
        if user_repo.get_by_email(user_data.email):
            raise ValidationError("Email already registered")
        
        # Create user
        dependency_manager = get_dependency_manager()
        security_service = dependency_manager.security_service
        
        # Hash password
        hashed_password = security_service.hash_password(user_data.password)
        
        # Create user data
        user_create_data = {
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": hashed_password,
            "is_active": True,
            "roles": ["user"]
        }
        
        user = user_repo.create(user_create_data)
        
        return SuccessResponse(
            message=f"User '{user_data.username}' registered successfully",
            data={"user_id": str(user.id)}
        )
        
    except (ValidationError, AuthenticationError) as e:
        raise create_http_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Authenticate user and return access token."""
    try:
        user_repo = UserRepository(db)
        dependency_manager = get_dependency_manager()
        security_service = dependency_manager.security_service
        
        # Get user
        user = user_repo.get_by_username(login_data.username)
        if not user:
            raise AuthenticationError("Invalid credentials")
        
        # Verify password
        if not security_service.verify_password(login_data.password, user.password_hash):
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
        
        access_token = security_service.create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        # Update last login
        user_repo.update_last_login(str(user.id))
        
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except (ValidationError, AuthenticationError) as e:
        raise create_http_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[dict, Depends(get_current_user)]
):
    """Get current user information."""
    return UserResponse.from_orm(current_user)
