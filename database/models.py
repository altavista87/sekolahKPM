"""SQLAlchemy models for database."""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey,
    ARRAY, DECIMAL, BigInteger, JSON, Float, func, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class School(Base):
    """School model."""
    __tablename__ = "schools"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    contact_email = Column(String(255))
    contact_phone = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    classes = relationship("Class", back_populates="school")


class Class(Base):
    """Class/Classroom model."""
    __tablename__ = "classes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    grade_level = Column(String(20))
    academic_year = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    school = relationship("School", back_populates="classes")
    teacher = relationship("User", back_populates="classes")
    students = relationship("Student", back_populates="class_")


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True)
    whatsapp_phone = Column(String(20), unique=True)
    email = Column(String(255))
    name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    preferred_language = Column(String(10), default="en")
    timezone = Column(String(50), default="Asia/Singapore")
    notification_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    students = relationship("Student", back_populates="parent")
    homework = relationship("Homework", back_populates="teacher")
    classes = relationship("Class", back_populates="teacher")


class Student(Base):
    """Student model."""
    __tablename__ = "students"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    school_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    parent = relationship("User", back_populates="students")
    class_ = relationship("Class", back_populates="students")
    homework = relationship("Homework", back_populates="student")


class Homework(Base):
    """Homework model."""
    __tablename__ = "homework"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"))
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    subject = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    raw_text = Column(Text)
    due_date = Column(DateTime(timezone=True))
    status = Column(String(20), default="pending")
    priority = Column(Integer, default=3)
    image_urls = Column(ARRAY(Text))
    file_urls = Column(ARRAY(Text))
    ai_enhanced = Column(Boolean, default=False)
    ai_summary = Column(Text)
    ai_keywords = Column(ARRAY(Text))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    student = relationship("Student", back_populates="homework")
    teacher = relationship("User", back_populates="homework")
    reminders = relationship("Reminder", back_populates="homework")
    ocr_results = relationship("OCRResult", back_populates="homework")


class Reminder(Base):
    """Reminder model."""
    __tablename__ = "reminders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    homework_id = Column(UUID(as_uuid=True), ForeignKey("homework.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    reminder_time = Column(DateTime(timezone=True), nullable=False)
    message = Column(Text)
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    homework = relationship("Homework", back_populates="reminders")


class OCRResult(Base):
    """OCR processing result."""
    __tablename__ = "ocr_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    homework_id = Column(UUID(as_uuid=True), ForeignKey("homework.id", ondelete="CASCADE"))
    image_path = Column(String(500))
    extracted_text = Column(Text)
    confidence = Column(Float)
    language = Column(String(20))
    engine = Column(String(50))
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    homework = relationship("Homework", back_populates="ocr_results")


class MessageLog(Base):
    """Message log model."""
    __tablename__ = "message_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    channel = Column(String(20), nullable=False)
    message_type = Column(String(50), nullable=False)
    recipient = Column(String(100), nullable=False)
    content = Column(Text)
    status = Column(String(20), default="pending")
    external_id = Column(String(100))
    cost_usd = Column(DECIMAL(10, 6))
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Audit log model."""
    __tablename__ = "audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_name = Column(String(100), nullable=False)
    record_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(20), nullable=False)
    old_data = Column(JSONB)
    new_data = Column(JSONB)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserConsent(Base):
    """User consent records for PDPA compliance."""
    __tablename__ = "user_consents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    consent_type = Column(String(50), nullable=False)  # ai_processing, data_storage, etc.
    granted = Column(Boolean, default=False)
    granted_at = Column(DateTime(timezone=True))
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    
    __table_args__ = (UniqueConstraint('user_id', 'consent_type'),)
