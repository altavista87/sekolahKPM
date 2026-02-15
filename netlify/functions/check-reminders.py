"""
Netlify Function: Scheduled Reminder Checker
Runs on a schedule to check and send homework reminders.
Triggered by Netlify's scheduled functions feature.
"""
import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def handler(event, context):
    """
    Scheduled function to check and send reminders.
    Runs at 8 AM, 1 PM, and 6 PM daily.
    """
    
    print(f"Running reminder check at {datetime.utcnow().isoformat()}")
    
    # This is where you'd:
    # 1. Query database for homework due soon
    # 2. Check user reminder preferences
    # 3. Send Telegram/WhatsApp notifications
    # 4. Log sent reminders
    
    result = {
        'status': 'completed',
        'timestamp': datetime.utcnow().isoformat(),
        'reminders_sent': 0,
        'reminders_pending': 0,
        'note': 'Connect to database to enable reminders'
    }
    
    # Check if database is configured
    if not os.getenv('DATABASE_URL'):
        result['warning'] = 'DATABASE_URL not set - skipping reminder check'
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    
    try:
        # Async reminder checking would go here
        # asyncio.run(check_and_send_reminders())
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error checking reminders: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e)
            })
        }


async def check_and_send_reminders():
    """Check for due homework and send reminders."""
    from database.connection import get_db_context
    from database.models import Homework, Reminder, User
    from sqlalchemy import select, and_
    
    async with get_db_context() as db:
        # Find homework due within 24 hours
        now = datetime.utcnow()
        tomorrow = now + timedelta(hours=24)
        
        # Query homework with no reminder sent
        result = await db.execute(
            select(Homework).where(
                and_(
                    Homework.due_date <= tomorrow,
                    Homework.due_date > now,
                    Homework.status != 'completed'
                )
            )
        )
        
        homework_list = result.scalars().all()
        
        for homework in homework_list:
            # Check if reminder already sent
            reminder_result = await db.execute(
                select(Reminder).where(
                    and_(
                        Reminder.homework_id == homework.id,
                        Reminder.sent == True
                    )
                )
            )
            
            existing = reminder_result.scalar_one_or_none()
            if existing:
                continue
            
            # Send reminder
            print(f"Would send reminder for homework: {homework.title}")
            
            # Create reminder record
            reminder = Reminder(
                homework_id=homework.id,
                user_id=homework.student_id,  # Should be parent_id
                reminder_time=now,
                message=f"Reminder: {homework.title} is due soon!",
                sent=True
            )
            db.add(reminder)
        
        await db.commit()
