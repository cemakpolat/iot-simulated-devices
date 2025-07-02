# server/app/api/auth/jwt_handler.py


"""JWT token handling with enhanced functionality"""
import jwt
import logging
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ...config import ServerConfig
from ..models.responses import AuthenticatedUser

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Global JWT secret storage
_JWT_SECRET: Optional[str] = None
_JWT_ALGORITHM = "HS256"

# Token expiration settings
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7     # 7 da


def set_jwt_global_config(config: ServerConfig):
    global _JWT_SECRET
    _JWT_SECRET = config.JWT_SECRET
    global  _JWT_ALGORITHM
    _JWT_ALGORITHM = config.JWT_ALGORITHM
    global ACCESS_TOKEN_EXPIRE_MINUTES
    ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES 
    global REFRESH_TOKEN_EXPIRE_DAYS
    REFRESH_TOKEN_EXPIRE_DAYS = config.REFRESH_TOKEN_EXPIRE_DAYS


def set_jwt_secret(secret_key: str):
    """Set the JWT secret key globally"""
    global _JWT_SECRET
    _JWT_SECRET = secret_key
    logger.info("JWT secret key has been set")

def get_jwt_secret() -> str:
    """Get the JWT secret key"""
    if _JWT_SECRET is None:
        raise RuntimeError("JWT secret key not set. Call set_jwt_secret() first.")
    return _JWT_SECRET

def create_jwt_verifier(app_state):
    """Factory function to create JWT verifier with app state (backward compatibility)"""
    def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthenticatedUser:
        logger.debug(f"Verifying JWT token: {credentials.credentials[:20]}...")
        
        try:
            # Try to get secret from app_state first (existing pattern)
            if hasattr(app_state, 'config') and hasattr(app_state.config, 'JWT_SECRET'):
                secret = app_state.config.JWT_SECRET
            else:
                # Fallback to global secret
                secret = get_jwt_secret()
            
            payload = jwt.decode(
                credentials.credentials, 
                secret, 
                algorithms=[_JWT_ALGORITHM]
            )
            
            user_id = payload.get("sub")
            username = payload.get("username")
            user_roles = payload.get("roles", [])

            if not user_id or not username:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Invalid token payload"
                )

            if not isinstance(user_roles, list):
                user_roles = [str(user_roles)] if user_roles is not None else []

            return AuthenticatedUser(
                id=user_id,
                username=username,
                roles=user_roles
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except RuntimeError as e:
            logger.critical(f"JWT configuration error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    
    return verify_token

# Standalone JWT verifier (doesn't require app_state)
async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthenticatedUser:
    """Standalone JWT token verifier"""
    logger.debug(f"Verifying JWT token: {credentials.credentials[:20]}...")
    
    try:
        secret = get_jwt_secret()
        
        payload = jwt.decode(
            credentials.credentials, 
            secret, 
            algorithms=[_JWT_ALGORITHM]
        )
        
        user_id = payload.get("sub")
        username = payload.get("username")
        user_roles = payload.get("roles", [])
        email = payload.get("email")

        if not user_id or not username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Invalid token payload"
            )

        if not isinstance(user_roles, list):
            user_roles = [str(user_roles)] if user_roles is not None else []

        return AuthenticatedUser(
            id=user_id,
            username=username,
            email=email,
            roles=user_roles
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except RuntimeError as e:
        logger.critical(f"JWT configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )

def create_access_token(user_id: str, username: str, email: str = None, roles: List[str] = None) -> str:
    """
    Create a JWT access token with enhanced payload
    
    Args:
        user_id: Unique user identifier
        username: Username
        email: User email (optional)
        roles: List of user roles (defaults to ["user"])
    
    Returns:
        JWT token string
    """
    try:
        secret = get_jwt_secret()
        
        # Current time
        now = datetime.now(timezone.utc)
        
        # Token payload with all necessary claims
        payload = {
            "sub": user_id,          # Subject (user ID) - standard JWT claim
            "username": username,     # Custom claim
            "roles": roles or ["user"], # Custom claim for authorization
            "iat": now,              # Issued at - standard JWT claim
            "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),  # Expires - standard JWT claim
            "type": "access"         # Token type for validation
        }
        
        # Add email if provided
        if email:
            payload["email"] = email
        
        # Generate the token
        token = jwt.encode(payload, secret, algorithm=_JWT_ALGORITHM)
        
        logger.debug(f"Access token created for user: {username} (expires in {ACCESS_TOKEN_EXPIRE_MINUTES} minutes)")
        return token
        
    except Exception as e:
        logger.error(f"Error creating JWT token for user {username}: {e}")
        raise RuntimeError("Failed to create access token")

def create_refresh_token(user_id: str) -> str:
    """
    Create a JWT refresh token (longer lived, used to get new access tokens)
    
    Args:
        user_id: Unique user identifier
    
    Returns:
        JWT refresh token string
    """
    try:
        secret = get_jwt_secret()
        
        now = datetime.now(timezone.utc)
        
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            "type": "refresh"
        }
        
        token = jwt.encode(payload, secret, algorithm=_JWT_ALGORITHM)
        
        logger.debug(f"Refresh token created for user ID: {user_id} (expires in {REFRESH_TOKEN_EXPIRE_DAYS} days)")
        return token
        
    except Exception as e:
        logger.error(f"Error creating refresh token for user {user_id}: {e}")
        raise RuntimeError("Failed to create refresh token")
    
# Role-based access control
def require_roles(required_roles: List[str]):
    """Create a dependency that requires specific roles"""
    async def role_checker(current_user: AuthenticatedUser = Depends(verify_jwt_token)) -> AuthenticatedUser:
        user_roles = current_user.roles or []
        
        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        
        return current_user
    
    return role_checker

# Common role dependencies
async def require_admin(current_user: AuthenticatedUser = Depends(verify_jwt_token)) -> AuthenticatedUser:
    """Require admin role"""
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user

async def require_user(current_user: AuthenticatedUser = Depends(verify_jwt_token)) -> AuthenticatedUser:
    """Require basic user authentication"""
    if not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return current_user

# Token creation helper
def create_access_token(user_id: str, username: str, email: str = None, roles: List[str] = None) -> str:
    """Create a JWT access token"""
    try:
        secret = get_jwt_secret()
        
        payload = {
            "sub": user_id,
            "username": username,
            "roles": roles or ["user"]
        }
        
        if email:
            payload["email"] = email
        
        token = jwt.encode(payload, secret, algorithm=_JWT_ALGORITHM)
        return token
        
    except Exception as e:
        logger.error(f"Error creating JWT token: {e}")
        raise RuntimeError("Failed to create access token")

# Optional: Get current user info without requiring authentication
async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[AuthenticatedUser]:
    """Get current user if token is provided and valid, otherwise return None"""
    try:
        return await verify_jwt_token(credentials)
    except HTTPException:
        return None