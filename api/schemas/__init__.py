"""API Pydantic schemas."""

from api.schemas.auth import Token, TokenData, UserLogin, UserCreate, TokenRefresh
from api.schemas.user import UserResponse, UserUpdate, UserPreferences
from api.schemas.homework import (
    HomeworkCreate, 
    HomeworkUpdate, 
    HomeworkResponse,
    HomeworkListResponse
)
from api.schemas.student import StudentCreate, StudentResponse, StudentWithHomework

__all__ = [
    # Auth
    "Token",
    "TokenData", 
    "UserLogin",
    "UserCreate",
    "TokenRefresh",
    # User
    "UserResponse",
    "UserUpdate",
    "UserPreferences",
    # Homework
    "HomeworkCreate",
    "HomeworkUpdate",
    "HomeworkResponse",
    "HomeworkListResponse",
    # Student
    "StudentCreate",
    "StudentResponse",
    "StudentWithHomework",
]
