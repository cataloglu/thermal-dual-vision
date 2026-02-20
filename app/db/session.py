"""
Database session management for Smart Motion Detector v2.

This module handles database connection, session creation, and initialization.
"""
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.utils.paths import DATA_DIR


logger = logging.getLogger(__name__)
_MIGRATION_STATUS: dict[str, dict[str, str | bool]] = {}


# Database configuration
DATABASE_DIR = DATA_DIR
DATABASE_FILE = DATABASE_DIR / "app.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    """Enable WAL mode and foreign key enforcement for every new connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

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


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context-managed DB session for worker/service code paths."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_add_rtsp_url_detection() -> None:
    """Add rtsp_url_detection (substream) column to cameras if missing."""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            row = conn.execute(text(
                "SELECT COUNT(*) FROM pragma_table_info('cameras') WHERE name='rtsp_url_detection'"
            )).scalar()
            if row == 0:
                conn.execute(text("ALTER TABLE cameras ADD COLUMN rtsp_url_detection VARCHAR(500)"))
                conn.commit()
                logger.info("Migration: added rtsp_url_detection to cameras")
            _MIGRATION_STATUS["rtsp_url_detection"] = {"ok": True, "error": ""}
        except Exception as e:
            logger.warning("Migration rtsp_url_detection: %s", e)
            _MIGRATION_STATUS["rtsp_url_detection"] = {"ok": False, "error": str(e)}


def _migrate_add_rejected_by_ai() -> None:
    """Add rejected_by_ai column to events if missing (SQLite)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            row = conn.execute(text(
                "SELECT COUNT(*) FROM pragma_table_info('events') WHERE name='rejected_by_ai'"
            )).scalar()
            if row == 0:
                conn.execute(text(
                    "ALTER TABLE events ADD COLUMN rejected_by_ai BOOLEAN DEFAULT 0 NOT NULL"
                ))
                conn.commit()
                logger.info("Migration: added rejected_by_ai to events")
            _MIGRATION_STATUS["rejected_by_ai"] = {"ok": True, "error": ""}
        except Exception as e:
            logger.warning("Migration rejected_by_ai: %s", e)
            _MIGRATION_STATUS["rejected_by_ai"] = {"ok": False, "error": str(e)}


def _migrate_add_person_count() -> None:
    """Add person_count column to events if missing (SQLite)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            row = conn.execute(text(
                "SELECT COUNT(*) FROM pragma_table_info('events') WHERE name='person_count'"
            )).scalar()
            if row == 0:
                conn.execute(text(
                    "ALTER TABLE events ADD COLUMN person_count INTEGER DEFAULT 1 NOT NULL"
                ))
                conn.commit()
                logger.info("Migration: added person_count to events")
            _MIGRATION_STATUS["person_count"] = {"ok": True, "error": ""}
        except Exception as e:
            logger.warning("Migration person_count: %s", e)
            _MIGRATION_STATUS["person_count"] = {"ok": False, "error": str(e)}


def get_migration_status() -> dict[str, dict[str, str | bool]]:
    return dict(_MIGRATION_STATUS)


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
    
    _migrate_add_rejected_by_ai()
    _migrate_add_person_count()
    _migrate_add_rtsp_url_detection()

    logger.info(f"Database initialized at {DATABASE_FILE}")


def drop_db() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data!
    Only use for testing or development.
    """
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped!")
