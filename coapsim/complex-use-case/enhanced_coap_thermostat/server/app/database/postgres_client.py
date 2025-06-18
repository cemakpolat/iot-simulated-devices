# server/app/database/postgres_client.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging
import os
from typing import Optional

from .models import Base, User # Import your models

logger = logging.getLogger(__name__)

class PostgreSQLClient:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._initialize_db()

    def _initialize_db(self):
        try:
            self.engine = create_engine(self.database_url, pool_pre_ping=True)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            # Create tables if they don't exist (for development/initial setup)
            Base.metadata.create_all(bind=self.engine)
            logger.info("PostgreSQL engine and session created.")
        except SQLAlchemyError as e:
            logger.critical(f"Failed to connect or initialize PostgreSQL: {e}", exc_info=True)
            self.engine = None
            self.SessionLocal = None

    def get_db(self):
        """Dependency for FastAPI to get a database session."""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def get_user_by_username(self, db, username: str) -> Optional[User]:
        """Fetches a user by username."""
        return db.query(User).filter(User.username == username).first()

    async def create_user(self, db, username: str, email: str, password_hash: str) -> User:
        """Creates a new user."""
        new_user = User(username=username, email=email, password_hash=password_hash)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"User {username} created in PostgreSQL.")
        return new_user

    # Add other CRUD operations for users, devices, schedules etc.