from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from .base import BaseRepository
from ..models.database.user import User
from ..models.schemas.requests import RegisterRequest

class UserRepository(BaseRepository[User, RegisterRequest, dict]):
    """Repository for user data operations."""
    
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        user = self.get(user_id)
        if user:
            user.last_login_at = datetime.now()
            self.db.commit()
            return True
        return False