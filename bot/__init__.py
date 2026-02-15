"""
EduSync Telegram Bot Module

Provides Telegram bot functionality for homework tracking and parent-teacher communication.
"""

__version__ = "1.0.0"
__author__ = "EduSync Team"

from .main import main, EduSyncBot
from .config import BotConfig
from .handlers import (
    BaseHandler,
    OnboardingHandler,
    HomeworkHandler,
    ParentHandler,
    TeacherHandler,
    ReminderHandler,
)
from .models import User, Homework, Reminder, UserRole, HomeworkStatus
from .ocr_engine import OCREngine
from .ai_processor import AIProcessor

__all__ = [
    "main",
    "EduSyncBot",
    "BotConfig",
    "BaseHandler",
    "OnboardingHandler",
    "HomeworkHandler",
    "ParentHandler",
    "TeacherHandler",
    "ReminderHandler",
    "User",
    "Homework",
    "Reminder",
    "UserRole",
    "HomeworkStatus",
    "OCREngine",
    "AIProcessor",
]
