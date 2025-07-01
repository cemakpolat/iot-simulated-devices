# server/app/api/routes/auth.py
# """Authentication endpoints"""
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ..dependencies import get_db, get_postgres_client, get_password_hasher
from ..models.requests import LoginRequest, RegisterRequest
from ..models.responses import AuthResponse, UserResponse, LoginResponse
from ...database.models import User
from ..auth.jqt_handler import create_access_token


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db),
    postgres_client = Depends(get_postgres_client),
    password_hasher= Depends(get_password_hasher)
):
    """Register a new user account"""
    try:
        logger.info(f"Registration attempt for username: {register_data.username}")
        
        # Check if username already exists
        existing_user = postgres_client.get_user_by_username(db, register_data.username)
        if existing_user:
            logger.warning(f"Registration failed - username already exists: {register_data.username}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email = postgres_client.get_user_by_email(db, register_data.email)
        if existing_email:
            logger.warning(f"Registration failed - email already exists: {register_data.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Hash password
        password_hash = password_hasher.hash_password(register_data.password)
        logger.debug(f"Password hashed for user: {register_data.username}")
        
        # Create user using SQLAlchemy
        new_user = postgres_client.create_user(
            db=db,
            username=register_data.username,
            email=register_data.email,
            password_hash=password_hash
        )
        
        if new_user is None:
            logger.error(f"Failed to create user in database: {register_data.username}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
            
        logger.info(f"Successfully registered user: {register_data.username} (ID: {new_user.id})")
        return {
            "message": "User registered successfully",
            "user_id": new_user.id,
            "username": new_user.username
        }
            
    except HTTPException:
        # Re-raise HTTP exceptions (like conflict errors)
        raise
    except Exception as e:
        logger.error(f"Unexpected registration error for {register_data.username}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration service error"
        )

@router.post("/login", response_model=LoginResponse)  # Use proper response model
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    postgres_client = Depends(get_postgres_client),
    password_hasher = Depends(get_password_hasher)
):
    """Login with username and password - Returns real JWT token"""
    try:
        logger.info(f"Login attempt for username: {login_data.username}")
        
        # Get user from database
        user = postgres_client.get_user_by_username(db, login_data.username)
        if not user:
            logger.warning(f"Login failed - user not found: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Verify password
        if not password_hasher.verify_password(login_data.password, user.password_hash):
            logger.warning(f"Login failed - invalid password: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Update last login timestamp
        postgres_client.update_user_last_login(db, user.id)
        
        # Generate real JWT token using your existing function
        try:
            access_token = create_access_token(
                user_id=user.id,
                username=user.username,
                email=user.email,
                roles=user.roles or ["user"]
            )
            
            logger.info(f"Successful login for user: {login_data.username} - JWT token generated")
            
            # Return properly structured response
            return LoginResponse(
                message="Login successful",
                user_id=user.id,
                username=user.username,
                email=user.email,
                roles=user.roles or ["user"],  # Keep as list
                access_token=access_token,
                token_type="bearer",
                expires_in=1800  # 30 minutes
            )
            
        except RuntimeError as e:
            logger.error(f"Failed to create JWT token for {login_data.username}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error - failed to generate token"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected login error for {login_data.username}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login service error"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    db: Session = Depends(get_db),
    # TODO: Add JWT token dependency here when you implement authentication
):
    """Get current user profile (placeholder for when you add JWT auth)"""
    # This is a placeholder - you'll implement proper JWT token validation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="JWT authentication not yet implemented"
    )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user by ID (admin endpoint)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        roles=user.roles,
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )


router.add_api_route("/register", register, methods=["POST"])
router.add_api_route("/login", login, methods=["POST"]) 

