"""Notification service for sending messages."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Homework, Reminder, MessageLog
from whatsapp.client import WhatsAppClient

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications."""
    
    def __init__(
        self,
        db: AsyncSession,
        whatsapp: Optional[WhatsAppClient] = None,
    ):
        self.db = db
        self.whatsapp = whatsapp
    
    async def send_reminder(self, reminder: Reminder) -> bool:
        """Send a reminder notification."""
        user = await self.db.get(User, reminder.user_id)
        if not user or not user.notification_enabled:
            return False
        
        success = False
        
        # Try WhatsApp first
        if self.whatsapp and user.whatsapp_phone:
            result = self.whatsapp.send_text_message(
                to=user.whatsapp_phone,
                text=reminder.message,
            )
            success = result.success
            
            # Log message
            await self._log_message(
                user_id=user.id,
                channel="whatsapp",
                message_type="reminder",
                recipient=user.whatsapp_phone,
                content=reminder.message,
                status="sent" if success else "failed",
                cost_usd=result.cost_usd,
            )
        
        # Update reminder status
        if success:
            reminder.sent = True
            reminder.sent_at = datetime.utcnow()
            await self.db.commit()
        
        return success
    
    async def send_homework_reminder(
        self,
        user_id: str,
        homework: Homework,
        days_until_due: int,
    ) -> bool:
        """Send homework-specific reminder."""
        user = await self.db.get(User, user_id)
        if not user:
            return False
        
        # Format message
        if days_until_due == 1:
            message = f"⏰ Tomorrow's deadline: {homework.title} ({homework.subject})"
        elif days_until_due <= 3:
            message = f"🔔 Due in {days_until_due} days: {homework.title} ({homework.subject})"
        else:
            message = f"📚 Reminder: {homework.title} due on {homework.due_date.strftime('%d %b')}"
        
        if self.whatsapp and user.whatsapp_phone:
            result = self.whatsapp.send_text_message(
                to=user.whatsapp_phone,
                text=message,
            )
            
            await self._log_message(
                user_id=user.id,
                channel="whatsapp",
                message_type="homework_reminder",
                recipient=user.whatsapp_phone,
                content=message,
                status="sent" if result.success else "failed",
                cost_usd=result.cost_usd,
            )
            
            return result.success
        
        return False
    
    async def process_pending_reminders(self) -> int:
        """Process all pending reminders."""
        from sqlalchemy import select
        
        query = select(Reminder).where(
            Reminder.sent == False,
            Reminder.reminder_time <= datetime.utcnow(),
        )
        
        result = await self.db.execute(query)
        pending = result.scalars().all()
        
        sent_count = 0
        for reminder in pending:
            if await self.send_reminder(reminder):
                sent_count += 1
        
        logger.info(f"Processed {len(pending)} reminders, sent {sent_count}")
        return sent_count
    
    async def get_user_notifications(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[MessageLog]:
        """Get notification history for user."""
        query = select(MessageLog).where(
            MessageLog.user_id == user_id,
        ).order_by(MessageLog.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _log_message(
        self,
        user_id: Optional[str],
        channel: str,
        message_type: str,
        recipient: str,
        content: str,
        status: str,
        cost_usd: float = 0.0,
    ):
        """Log message to database."""
        log = MessageLog(
            user_id=user_id,
            channel=channel,
            message_type=message_type,
            recipient=recipient,
            content=content[:1000],  # Truncate
            status=status,
            cost_usd=cost_usd,
        )
        
        self.db.add(log)
        await self.db.commit()
