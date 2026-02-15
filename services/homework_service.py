"""Homework business logic service."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Homework, Student, Reminder

logger = logging.getLogger(__name__)


class HomeworkService:
    """Service for homework operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_homework(
        self,
        student_id: UUID,
        subject: str,
        title: str,
        description: str,
        due_date: Optional[datetime] = None,
        priority: int = 3,
        image_urls: Optional[List[str]] = None,
    ) -> Homework:
        """Create new homework."""
        homework = Homework(
            student_id=student_id,
            subject=subject,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            image_urls=image_urls or [],
        )
        
        self.db.add(homework)
        await self.db.commit()
        await self.db.refresh(homework)
        
        # Create default reminder
        if due_date:
            await self._create_default_reminder(homework)
        
        logger.info(f"Created homework: {homework.id}")
        return homework
    
    async def get_homework_by_student(
        self,
        student_id: UUID,
        status: Optional[str] = None,
    ) -> List[Homework]:
        """Get homework for student."""
        query = select(Homework).where(Homework.student_id == student_id)
        
        if status:
            query = query.where(Homework.status == status)
        
        query = query.order_by(Homework.due_date)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_overdue_homework(self) -> List[Homework]:
        """Get all overdue homework."""
        query = select(Homework).where(
            and_(
                Homework.due_date < datetime.utcnow(),
                Homework.status != "completed",
            )
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def complete_homework(self, homework_id: UUID) -> Optional[Homework]:
        """Mark homework as completed."""
        homework = await self.db.get(Homework, homework_id)
        
        if homework:
            homework.status = "completed"
            homework.completed_at = datetime.utcnow()
            await self.db.commit()
            logger.info(f"Completed homework: {homework_id}")
        
        return homework
    
    async def update_homework_status(self):
        """Update status of all homework (mark overdue)."""
        query = select(Homework).where(
            and_(
                Homework.due_date < datetime.utcnow(),
                Homework.status == "pending",
            )
        )
        
        result = await self.db.execute(query)
        overdue = result.scalars().all()
        
        for hw in overdue:
            hw.status = "overdue"
        
        await self.db.commit()
        logger.info(f"Updated {len(overdue)} homework to overdue")
    
    async def get_statistics(self, student_id: UUID) -> Dict[str, Any]:
        """Get homework statistics for student."""
        query = select(Homework).where(Homework.student_id == student_id)
        result = await self.db.execute(query)
        all_hw = result.scalars().all()
        
        total = len(all_hw)
        completed = sum(1 for h in all_hw if h.status == "completed")
        pending = sum(1 for h in all_hw if h.status == "pending")
        overdue = sum(1 for h in all_hw if h.status == "overdue")
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "overdue": overdue,
            "completion_rate": round(completion_rate, 1),
        }
    
    async def _create_default_reminder(self, homework: Homework):
        """Create default reminder for homework."""
        if not homework.due_date:
            return
        
        # Get parent user
        student = await self.db.get(Student, homework.student_id)
        if not student:
            return
        
        reminder_time = homework.due_date - timedelta(days=1)
        
        reminder = Reminder(
            homework_id=homework.id,
            user_id=student.parent_id,
            reminder_time=reminder_time,
            message=f"Reminder: {homework.title} is due tomorrow!",
        )
        
        self.db.add(reminder)
        await self.db.commit()
