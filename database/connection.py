"""Database connection configuration for Railway PostgreSQL."""

import os
import logging
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)

# Global engine (initialized lazily)
_engine = None
_AsyncSessionLocal = None
Base = None


def get_base():
    """Get or import Base class."""
    global Base
    if Base is None:
        from database.models import Base as ModelsBase
        Base = ModelsBase
    return Base


def get_database_url() -> str:
    """Get database URL with proper format."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        logger.warning("DATABASE_URL not set, using SQLite fallback")
        return "sqlite:///./edusync.db"
    
    # For Railway PostgreSQL with psycopg2
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # Add sslmode=require for Railway
    if "railway.app" in database_url and "sslmode" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url += f"{separator}sslmode=require"
        logger.info("Added sslmode=require for Railway")
    
    logger.info(f"Database configured for: {database_url.split('@')[1].split(':')[0] if '@' in database_url else 'unknown'}")
    return database_url


def get_engine():
    """Get or create engine (lazy initialization)."""
    global _engine
    if _engine is None:
        from sqlalchemy import create_engine
        
        _engine = create_engine(
            get_database_url(),
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _engine


def get_session_maker():
    """Get or create session maker (lazy initialization)."""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        from sqlalchemy.orm import sessionmaker
        _AsyncSessionLocal = sessionmaker(
            get_engine(),
            autocommit=False,
            autoflush=False,
        )
    return _AsyncSessionLocal


def init_db():
    """Initialize database tables."""
    try:
        engine = get_engine()
        with engine.begin() as conn:
            try:
                from database.models import User, Student, Homework, Reminder, Class
                Base = get_base()
                Base.metadata.create_all(conn)
                logger.info("✅ Database initialized successfully")
            except ImportError as e:
                logger.warning(f"⚠️ Could not import models: {e}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise


def get_db():
    """Get database session."""
    session_maker = get_session_maker()
    session = session_maker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"❌ Database connection check failed: {e}")
        return False


def close_db():
    """Close database connections."""
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None
        logger.info("Database connections closed")


# Async wrappers for compatibility
async def init_db_async():
    """Async wrapper for init_db."""
    init_db()


async def check_db_connection_async() -> bool:
    """Async wrapper for check_db_connection."""
    return check_db_connection()


async def get_db_async():
    """Async wrapper for get_db."""
    for session in get_db():
        yield session
