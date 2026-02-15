"""Database connection configuration for Railway PostgreSQL."""

import os
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Import Base from models (avoid circular import by doing it lazily)
Base = None
def get_base():
    global Base
    if Base is None:
        from database.models import Base as ModelsBase
        Base = ModelsBase
    return Base

# Global engine (initialized lazily)
_engine = None
_AsyncSessionLocal = None


def get_database_url() -> str:
    """Get database URL with proper format for asyncpg."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # Fallback for local development
        logger.warning("DATABASE_URL not set, using SQLite fallback")
        return "sqlite+aiosqlite:///./edusync.db"
    
    # Convert Railway's postgres:// to postgresql+asyncpg://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Add SSL mode for Railway PostgreSQL
    if "sslmode" not in database_url and "railway.app" in database_url:
        database_url += "?sslmode=require"
    
    return database_url


def get_engine():
    """Get or create engine (lazy initialization)."""
    global _engine
    if _engine is None:
        url = get_database_url()
        # SSL configuration for Railway PostgreSQL
        connect_args = {}
        if "railway.app" in url or "sslmode=require" in url:
            connect_args["ssl"] = "require"
        
        _engine = create_async_engine(
            url,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args=connect_args,
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
        async with engine.begin() as conn:
            # Import models to ensure they're registered
            try:
                from database.models import User, Student, Homework, Reminder, Class
                Base = get_base()
                await conn.run_sync(Base.metadata.create_all)
                logger.info("✅ Database initialized successfully")
            except ImportError as e:
                logger.warning(f"⚠️ Could not import models: {e}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
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
