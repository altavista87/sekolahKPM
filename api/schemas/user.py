"""User schemas."""

from typing import Optional, List
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserBase(BaseModel):
    """Base user schema."""
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., pattern="^(teacher|parent|admin)$")
    preferred_language: str = Field(default="en", max_length=10)
    timezone: str = Field(default="Asia/Singapore", max_length=50)
    notification_enabled: bool = Field(default=True)


class UserCreate(UserBase):
    """User creation schema."""
    telegram_id: Optional[int] = None
    whatsapp_phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None


class UserUpdate(BaseModel):
    """User update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    preferred_language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    notification_enabled: Optional[bool] = None


class UserPreferences(BaseModel):
    """User preferences schema."""
    preferred_language: str = Field(default="en", max_length=10)
    timezone: str = Field(default="Asia/Singapore", max_length=50)
    notification_enabled: bool = Field(default=True)


class UserResponse(UserBase):
    """User response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    telegram_id: Optional[int] = None
    whatsapp_phone: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserWithStudents(UserResponse):
    """User with students schema."""
    from api.schemas.student import StudentResponse
    students: List[StudentResponse] = []
