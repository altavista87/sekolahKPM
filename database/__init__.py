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
from database.session import (
    async_session_maker,
    get_db as get_db_session,
)

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
    "async_session_maker",
    "get_db",
    "get_db_context",
    "get_db_session",
    "init_db",
    "close_db",
]
