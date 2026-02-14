"""
Database session management for Smart Motion Detector v2.

This module handles database connection, session creation, and initialization.
"""
import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.utils.paths import DATA_DIR


logger = logging.getLogger(__name__)


# Database configuration
DATABASE_DIR = DATA_DIR
DATABASE_FILE = DATABASE_DIR / "app.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    connect_args={"check_same_thread": False},  # Needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_engine():
    """
    Get the database engine.
    
    Returns:
        Engine: SQLAlchemy engine instance
    """
    return engine


def get_session() -> Generator[Session, None, None]:
    """
    Get a database session.
    
    This is a generator function for use with FastAPI Depends.
    
    Yields:
        Session: SQLAlchemy session
        
    Example:
        @app.get("/items")
        def get_items(db: Session = Depends(get_session)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database.
    
    Creates all tables if they don't exist.
    Should be called on application startup.
    """
    # Ensure data directory exists
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    logger.info(f"Database initialized at {DATABASE_FILE}")


def drop_db() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data!
    Only use for testing or development.
    """
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped!")
