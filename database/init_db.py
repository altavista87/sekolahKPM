"""Database initialization script."""

import asyncio
import logging

from database.connection import init_db, close_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Initialize database tables."""
    try:
        logger.info("Initializing database tables...")
        await init_db()
        logger.info("Database tables created successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
