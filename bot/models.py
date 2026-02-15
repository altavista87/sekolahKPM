"""Database models for Telegram Bot."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass, field
import uuid


class UserRole(Enum):
    """User roles."""
    PARENT = "parent"
    TEACHER = "teacher"
    ADMIN = "admin"


class HomeworkStatus(Enum):
    """Homework status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


@dataclass
class User:
    """User model."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    telegram_id: int = 0
    phone_number: Optional[str] = None
    name: str = ""
    email: Optional[str] = None
    role: UserRole = UserRole.PARENT
    preferred_language: str = "en"
    timezone: str = "Asia/Singapore"
    notification_enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Parent-specific
    children: List["Student"] = field(default_factory=list)
    
    # Teacher-specific
    school_id: Optional[str] = None
    subjects: List[str] = field(default_factory=list)


@dataclass
class Student:
    """Student model."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    class_id: str = ""
    parent_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Homework:
    """Homework model."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str = ""
    teacher_id: Optional[str] = None
    subject: str = ""
    title: str = ""
    description: str = ""
    raw_text: str = ""  # OCR extracted text
    due_date: Optional[datetime] = None
    status: HomeworkStatus = HomeworkStatus.PENDING
    priority: int = 1  # 1-5, 5 being highest
    
    # Media
    image_urls: List[str] = field(default_factory=list)
    file_urls: List[str] = field(default_factory=list)
    
    # AI Processing
    ai_enhanced: bool = False
    ai_summary: Optional[str] = None
    ai_keywords: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def is_overdue(self) -> bool:
        """Check if homework is overdue."""
        if self.due_date and self.status != HomeworkStatus.COMPLETED:
            return datetime.utcnow() > self.due_date
        return False


@dataclass
class Reminder:
    """Reminder model."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    homework_id: str = ""
    user_id: str = ""
    reminder_time: datetime = field(default_factory=datetime.utcnow)
    message: str = ""
    sent: bool = False
    sent_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConversationState:
    """User conversation state."""
    user_id: str = ""
    state: str = "idle"  # idle, awaiting_homework_photo, awaiting_due_date, etc.
    data: dict = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.utcnow)
