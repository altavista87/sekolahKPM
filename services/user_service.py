"""User management service."""

import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Student

logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_user(
        self,
        name: str,
        role: str,
        telegram_id: Optional[int] = None,
        whatsapp_phone: Optional[str] = None,
        email: Optional[str] = None,
        language: str = "en",
    ) -> User:
        """Create new user."""
        user = User(
            name=name,
            role=role,
            telegram_id=telegram_id,
            whatsapp_phone=whatsapp_phone,
            email=email,
            preferred_language=language,
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        logger.info(f"Created user: {user.id}")
        return user
    
    async def get_user_by_telegram(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        query = select(User).where(User.telegram_id == telegram_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_by_whatsapp(self, phone: str) -> Optional[User]:
        """Get user by WhatsApp phone."""
        query = select(User).where(User.whatsapp_phone == phone)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def link_student_to_parent(
        self,
        parent_id: UUID,
        student_name: str,
        class_id: str,
    ) -> Student:
        """Link student to parent."""
        student = Student(
            name=student_name,
            class_id=class_id,
            parent_id=parent_id,
        )
        
        self.db.add(student)
        await self.db.commit()
        await self.db.refresh(student)
        
        logger.info(f"Linked student {student.id} to parent {parent_id}")
        return student
    
    async def get_parent_students(self, parent_id: UUID) -> List[Student]:
        """Get all students for parent."""
        query = select(Student).where(Student.parent_id == parent_id)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_preferences(
        self,
        user_id: UUID,
        language: Optional[str] = None,
        notifications: Optional[bool] = None,
    ) -> Optional[User]:
        """Update user preferences."""
        user = await self.db.get(User, user_id)
        
        if user:
            if language:
                user.preferred_language = language
            if notifications is not None:
                user.notification_enabled = notifications
            
            await self.db.commit()
            logger.info(f"Updated preferences for user: {user_id}")
        
        return user
    
    async def link_whatsapp(
        self,
        user_id: UUID,
        phone: str,
    ) -> Optional[User]:
        """Link WhatsApp phone to user."""
        # Check if phone already linked
        existing = await self.get_user_by_whatsapp(phone)
        if existing and existing.id != user_id:
            logger.warning(f"Phone {phone} already linked to user {existing.id}")
            return None
        
        user = await self.db.get(User, user_id)
        if user:
            user.whatsapp_phone = phone
            await self.db.commit()
            logger.info(f"Linked WhatsApp {phone} to user {user_id}")
        
        return user
