# app/infrastructure/database/postgres.py
import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from ...core.config import get_settings
from ...models.database.base import Base

logger = logging.getLogger(__name__)
settings = get_settings()

class PostgreSQLClient:
    """PostgreSQL database client with connection pooling."""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connection."""
        try:
            self.engine = create_engine(
                settings.DATABASE_URL,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=settings.DEBUG
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            
            self._initialized = True
            logger.info("PostgreSQL client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL client: {e}")
            raise
    
    def get_db(self) -> Generator[Session, None, None]:
        """Get database session."""
        if not self._initialized:
            raise RuntimeError("PostgreSQL client not initialized")
        
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("PostgreSQL connections closed")
