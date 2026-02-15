"""Student schemas."""

from typing import Optional, List
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class StudentBase(BaseModel):
    """Base student schema."""
    name: str = Field(..., min_length=1, max_length=255)
    class_id: Optional[str] = Field(None, max_length=50)
    school_id: Optional[str] = Field(None, max_length=100)


class StudentCreate(StudentBase):
    """Student creation schema."""
    parent_id: UUID


class StudentUpdate(BaseModel):
    """Student update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    class_id: Optional[str] = Field(None, max_length=50)
    school_id: Optional[str] = Field(None, max_length=100)


class StudentResponse(StudentBase):
    """Student response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    parent_id: UUID
    created_at: datetime


class StudentWithHomework(StudentResponse):
    """Student with homework schema."""
    from api.schemas.homework import HomeworkResponse
    homework: List[HomeworkResponse] = []


class StudentStats(BaseModel):
    """Student homework statistics schema."""
    student_id: UUID
    total: int = 0
    completed: int = 0
    pending: int = 0
    in_progress: int = 0
    cancelled: int = 0
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    overdue: int = 0
