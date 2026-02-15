"""Homework schemas."""

from typing import Optional, List
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class HomeworkBase(BaseModel):
    """Base homework schema."""
    subject: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: int = Field(default=3, ge=1, le=5)


class HomeworkCreate(HomeworkBase):
    """Homework creation schema."""
    student_id: UUID
    raw_text: Optional[str] = None
    image_urls: Optional[List[str]] = None
    file_urls: Optional[List[str]] = None


class HomeworkUpdate(BaseModel):
    """Homework update schema."""
    subject: Optional[str] = Field(None, min_length=1, max_length=100)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|cancelled)$")
    priority: Optional[int] = Field(None, ge=1, le=5)


class HomeworkComplete(BaseModel):
    """Homework completion schema."""
    completed_notes: Optional[str] = None


class HomeworkAIEnhancement(BaseModel):
    """AI enhancement schema."""
    ai_summary: Optional[str] = None
    ai_keywords: Optional[List[str]] = None
    ai_enhanced: bool = False


class HomeworkResponse(HomeworkBase):
    """Homework response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    student_id: UUID
    teacher_id: Optional[UUID] = None
    status: str = Field(default="pending")
    raw_text: Optional[str] = None
    image_urls: Optional[List[str]] = None
    file_urls: Optional[List[str]] = None
    ai_enhanced: bool = False
    ai_summary: Optional[str] = None
    ai_keywords: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class HomeworkListResponse(BaseModel):
    """Homework list response schema."""
    homework: List[HomeworkResponse]
    total: int
    page: int = 1
    per_page: int = 20


class HomeworkFilter(BaseModel):
    """Homework filter schema."""
    student_id: Optional[UUID] = None
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|cancelled)$")
    subject: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
