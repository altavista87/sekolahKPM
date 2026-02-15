"""Celery batch processing worker."""

import os
import logging
from typing import Dict, Any

from celery import Celery
from celery.schedules import crontab

# Configure Celery
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("edusync", broker=redis_url, backend=redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Singapore",
    enable_utc=True,
    beat_schedule={
        "process-reminders": {
            "task": "workers.batch_worker.process_reminders",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        "update-homework-status": {
            "task": "workers.batch_worker.update_homework_status",
            "schedule": crontab(hour="0", minute="0"),  # Daily at midnight
        },
    },
)

logger = logging.getLogger(__name__)


@celery_app.task
def process_homework_image(image_path: str, user_id: str) -> Dict[str, Any]:
    """Process homework image in background."""
    logger.info(f"Processing image: {image_path} for user: {user_id}")
    
    # This would call the pipeline
    return {
        "status": "completed",
        "image_path": image_path,
        "extracted_text": "",
    }


@celery_app.task
def process_reminders():
    """Process pending reminders."""
    logger.info("Processing pending reminders")
    # Would call notification service
    return {"processed": 0}


@celery_app.task
def update_homework_status():
    """Update homework status (mark overdue)."""
    logger.info("Updating homework status")
    # Would call homework service
    return {"updated": 0}


@celery_app.task
def send_batch_notifications(user_ids: list, message: str) -> Dict[str, Any]:
    """Send batch notifications."""
    logger.info(f"Sending batch notification to {len(user_ids)} users")
    return {"sent": 0, "failed": 0}
