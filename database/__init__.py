"""Database module for EduSync."""

from database.models import (
    Base,
    User,
    Student,
    Homework,
    Class,
    School,
    Reminder,
    OCRResult,
    MessageLog,
    UserConsent,
)
from database.connection import (
    get_engine,
    get_session_maker,
    get_db,
    get_db_context,
    init_db,
    close_db,
)
# Note: database.session is async and requires asyncpg - not importing here

__all__ = [
    "Base",
    "User",
    "Student",
    "Homework",
    "Class",
    "School",
    "Reminder",
    "OCRResult",
    "MessageLog",
    "UserConsent",
    "get_engine",
    "get_session_maker",
    "get_db",
    "get_db_context",
    "init_db",
    "close_db",
]
