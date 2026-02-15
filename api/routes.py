"""FastAPI routes - DEPRECATED: Use api/main.py instead.

This file is kept for backward compatibility but will be removed in a future version.
Please migrate to using api/main.py which includes proper security controls.
"""

import warnings
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Homework, User, Student
from services.homework_service import HomeworkService
from services.user_service import UserService
from config.settings import get_settings

warnings.warn(
    "api/routes.py is deprecated. Use api/main.py for secure API endpoints.",
    DeprecationWarning,
    stacklevel=2
)

settings = get_settings()

app = FastAPI(title="EduSync API (Legacy)", version="1.0.0-deprecated")

# Security Fix: Restricted CORS - NOT allowing all origins
# This addresses CVSS 8.6 vulnerability
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://edusync.app",
        "https://www.edusync.app",
        "https://api.edusync.app",
        "https://t.me",
        # Local development (remove in production)
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    max_age=600,
)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0", "deprecated": True}

@app.get("/ready")
async def readiness_check():
    return {"ready": True}

@app.get("/metrics")
async def metrics():
    return {"requests_total": 0}

# Users - UNPROTECTED: These endpoints should not be used in production
# Use /api/v1/users/* endpoints from api/main.py instead
@app.get("/users/{user_id}")
async def get_user(user_id: UUID):
    """Get user by ID - DEPRECATED."""
    return {"id": user_id, "name": "Test User", "deprecated": True}

@app.post("/users")
async def create_user(user_data: dict):
    """Create new user - DEPRECATED."""
    return {"id": "new-user-id", "created": True, "deprecated": True}

# Homework - UNPROTECTED: These endpoints should not be used in production
@app.get("/homework")
async def list_homework(
    student_id: Optional[UUID] = None,
    status: Optional[str] = None,
):
    """List homework - DEPRECATED."""
    return {
        "homework": [],
        "total": 0,
        "deprecated": True
    }

@app.post("/homework")
async def create_homework(hw_data: dict):
    """Create new homework - DEPRECATED."""
    return {"id": "new-hw-id", "created": True, "deprecated": True}

@app.get("/homework/{homework_id}")
async def get_homework(homework_id: UUID):
    """Get homework by ID - DEPRECATED."""
    return {"id": homework_id, "title": "Sample Homework", "deprecated": True}

@app.patch("/homework/{homework_id}/complete")
async def complete_homework(homework_id: UUID):
    """Mark homework as completed - DEPRECATED."""
    return {"id": homework_id, "status": "completed", "deprecated": True}

# Students - UNPROTECTED: These endpoints should not be used in production
@app.get("/students/{student_id}/homework")
async def get_student_homework(student_id: UUID):
    """Get all homework for student - DEPRECATED."""
    return {"student_id": student_id, "homework": [], "deprecated": True}

@app.get("/students/{student_id}/stats")
async def get_student_stats(student_id: UUID):
    """Get homework statistics for student - DEPRECATED."""
    return {
        "student_id": student_id,
        "total": 0,
        "completed": 0,
        "completion_rate": 0,
        "deprecated": True
    }

# Webhooks - SECURITY WARNING: No signature validation
# Use /api/v1/webhooks/* endpoints from api/main.py instead
@app.post("/webhook/telegram")
async def telegram_webhook(update: dict):
    """Handle Telegram webhook - DEPRECATED, NO SIGNATURE VALIDATION."""
    return {"ok": True, "deprecated": True, "warning": "No signature validation"}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(payload: dict):
    """Handle WhatsApp webhook - DEPRECATED, NO SIGNATURE VALIDATION."""
    return {"ok": True, "deprecated": True, "warning": "No signature validation"}

# Upload
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload file for processing - DEPRECATED."""
    return {
        "filename": file.filename,
        "size": 0,
        "uploaded": True,
        "deprecated": True
    }
