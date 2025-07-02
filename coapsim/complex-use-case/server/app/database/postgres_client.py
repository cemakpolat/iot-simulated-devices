
import logging
from typing import Optional, Generator
from .models import Base, User

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError


logger = logging.getLogger(__name__)

class PostgreSQLClient:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize database engine and session factory"""
        try:
            self.engine = create_engine(
                self.database_url, 
                pool_pre_ping=True,
                echo=False  # Set to True for SQL debugging
            )
            self.SessionLocal = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=self.engine
            )
            
            # Create tables if they don't exist (for development/initial setup)
            Base.metadata.create_all(bind=self.engine)
            logger.info("PostgreSQL engine and session created successfully.")
            
        except SQLAlchemyError as e:
            logger.critical(f"Failed to connect or initialize PostgreSQL: {e}", exc_info=True)
            self.engine = None
            self.SessionLocal = None
            raise  # Re-raise to prevent silent failures
    
    def get_db(self) -> Generator[Session, None, None]:
        """Dependency for FastAPI to get a database session."""
        if self.SessionLocal is None:
            raise RuntimeError("PostgreSQL client not properly initialized")
        
        db = self.SessionLocal()
        try:
            yield db
        except Exception as e:
            logger.error(f"Database session error: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        """Fetches a user by username."""
        try:
            return db.query(User).filter(User.username == username, User.is_active == True).first()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user by username: {e}")
            return None
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """Fetches a user by email."""
        try:
            return db.query(User).filter(User.email == email, User.is_active == True).first()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user by email: {e}")
            return None
    
    def create_user(self, db: Session, username: str, email: str, password_hash: str) -> Optional[User]:
        """Creates a new user."""
        try:
            new_user = User(
                username=username, 
                email=email, 
                password_hash=password_hash
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            logger.info(f"User '{username}' created successfully with ID: {new_user.id}")
            return new_user
        except SQLAlchemyError as e:
            logger.error(f"Error creating user '{username}': {e}")
            db.rollback()
            return None
    
    def update_user_last_login(self, db: Session, user_id: str) -> bool:
        """Update user's last login timestamp."""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                from datetime import datetime, timezone
                user.last_login_at = datetime.now(timezone.utc)
                db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            db.rollback()
            return False
    
    def deactivate_user(self, db: Session, user_id: str) -> bool:
        """Deactivate a user account."""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_active = False
                db.commit()
                logger.info(f"User {user.username} deactivated")
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error deactivating user {user_id}: {e}")
            db.rollback()
            return False
    
    def close(self):
        """Close the database engine."""
        if self.engine:
            self.engine.dispose()
            logger.info("PostgreSQL engine disposed")