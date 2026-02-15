"""User routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user, get_db
from api.schemas.user import UserResponse, UserUpdate, UserPreferences
from database.models import User

router = APIRouter()


@router.get("/me", response_model=UserResponse)
@limiter.limit("100/minute")
async def get_current_user(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user profile.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
@limiter.limit("30/minute")
async def update_current_user(
    request: Request,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile.
    """
    # Update only provided fields
    update_data = user_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
@limiter.limit("100/minute")
async def get_user(
    request: Request,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID.
    
    Users can only view their own profile unless they are admin.
    """
    # Check permissions - users can only view their own profile
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    from sqlalchemy import select
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.patch("/{user_id}/preferences", response_model=UserResponse)
async def update_user_preferences(
    user_id: UUID,
    preferences: UserPreferences,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user preferences.
    """
    # Users can only update their own preferences
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    from sqlalchemy import select
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update preferences
    user.preferred_language = preferences.preferred_language
    user.timezone = preferences.timezone
    user.notification_enabled = preferences.notification_enabled
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user account.
    
    Only admins or the user themselves can delete accounts.
    """
    # Check permissions
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    from sqlalchemy import select
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await db.delete(user)
    await db.commit()
    
    return None
