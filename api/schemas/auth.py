"""Authentication schemas."""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


class Token(BaseModel):
    """JWT token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_id: UUID = Field(..., description="User ID")


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[str] = None
    telegram_id: Optional[int] = None
    whatsapp_phone: Optional[str] = None
    scopes: list[str] = []


class TokenRefresh(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")


class UserLogin(BaseModel):
    """User login request."""
    telegram_id: Optional[int] = Field(None, description="Telegram user ID")
    whatsapp_phone: Optional[str] = Field(None, description="WhatsApp phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    password: Optional[str] = Field(None, description="Password (if using email)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "telegram_id": 123456789,
            }
        }


class UserCreate(BaseModel):
    """User registration request."""
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    role: str = Field(..., pattern="^(teacher|parent|admin)$", description="User role")
    telegram_id: Optional[int] = Field(None, description="Telegram user ID")
    whatsapp_phone: Optional[str] = Field(None, max_length=20, description="WhatsApp phone")
    email: Optional[EmailStr] = Field(None, description="Email address")
    preferred_language: str = Field(default="en", max_length=10, description="Preferred language")
    timezone: str = Field(default="Asia/Singapore", max_length=50, description="User timezone")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "role": "parent",
                "telegram_id": 123456789,
                "preferred_language": "en"
            }
        }


class LogoutRequest(BaseModel):
    """Logout request."""
    refresh_token: Optional[str] = Field(None, description="Refresh token to revoke")
    all_devices: bool = Field(default=False, description="Logout from all devices")


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr = Field(..., description="Email address for password reset")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str = Field(..., description="Reset token from email")
    new_password: str = Field(..., min_length=8, description="New password")
