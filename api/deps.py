"""API dependencies for authentication and authorization."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from database.models import User

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT"
)


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[str] = None
    telegram_id: Optional[int] = None
    whatsapp_phone: Optional[str] = None
    scopes: list[str] = []


async def get_db() -> AsyncSession:
    """Get database session."""
    from database.session import async_session_maker
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Validate JWT token and return current user.
    
    Args:
        token: JWT token from Authorization header
        db: Database session
        
    Returns:
        User object if token is valid
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    from sqlalchemy import select
    query = select(User).where(User.id == UUID(token_data.user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Check if current user is active.
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        User if active
        
    Raises:
        HTTPException: If user is inactive
    """
    # Add is_active field check if your User model has it
    # For now, we assume all users in DB are active
    return current_user


async def get_current_teacher(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Verify current user is a teacher.
    
    Args:
        current_user: User from get_current_active_user dependency
        
    Returns:
        User if teacher
        
    Raises:
        HTTPException: If user is not a teacher
    """
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Teacher role required.",
        )
    return current_user


async def get_current_parent(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Verify current user is a parent.
    
    Args:
        current_user: User from get_current_active_user dependency
        
    Returns:
        User if parent
        
    Raises:
        HTTPException: If user is not a parent
    """
    if current_user.role not in ["parent", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Parent role required.",
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Verify current user is an admin.
    
    Args:
        current_user: User from get_current_active_user dependency
        
    Returns:
        User if admin
        
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required.",
        )
    return current_user
