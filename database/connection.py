"""Database connection configuration for Railway PostgreSQL."""

import os
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Base class for models
Base = declarative_base()

# Global engine (initialized lazily)
_engine = None
_AsyncSessionLocal = None


def get_database_url() -> str:
    """Get database URL with proper format for asyncpg."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        logger.warning("DATABASE_URL not set, using SQLite fallback")
        return "sqlite+aiosqlite:///./edusync.db"
    
    # Convert postgres:// to postgresql+asyncpg://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    # Add sslmode=require for Railway
    if "railway.app" in database_url and "sslmode" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url += f"{separator}sslmode=require"
        logger.info("Added sslmode=require to URL")
    
    logger.info(f"Database host: {database_url.split('@')[1].split(':')[0] if '@' in database_url else 'unknown'}")
    return database_url


def get_engine():
    """Get or create engine (lazy initialization)."""
    global _engine
    if _engine is None:
        url = get_database_url()
        
        _engine = create_async_engine(
            url,
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
        _AsyncSessionLocal = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _AsyncSessionLocal


async def init_db() -> None:
    """Initialize database tables."""
    try:
        engine = get_engine()
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            try:
                from database.models import User, Student, Homework, Reminder, Class
                # Use run_sync to create tables
                def create_tables(sync_conn):
                    Base.metadata.create_all(sync_conn)
                await conn.run_sync(create_tables)
                logger.info("✅ Database initialized successfully")
            except ImportError as e:
                logger.warning(f"⚠️ Could not import models: {e}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_context() -> AsyncSession:
    """Get database session as context manager."""
    session_maker = get_session_maker()
    return session_maker()


async def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"❌ Database connection check failed: {e}")
        return False


async def close_db() -> None:
    """Close database connections."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("Database connections closed")
