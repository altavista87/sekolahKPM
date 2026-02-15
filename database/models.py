"""SQLAlchemy models for database."""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey,
    DECIMAL, BigInteger, func, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
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
    
    classes = relationship("Class", back_populates="school")


class Class(Base):
    """Class/Classroom model."""
    __tablename__ = "classes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    grade_level = Column(String(20))
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id"))
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    school = relationship("School", back_populates="classes")
    students = relationship("Student", back_populates="class_")


class User(Base):
    """User model (parents and teachers)."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True, index=True)
    phone_number = Column(String(20), unique=True)
    email = Column(String(255), unique=True)
    name = Column(String(255), nullable=False)
    role = Column(String(20), default="parent")  # parent, teacher, admin
    language = Column(String(10), default="en")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    students = relationship("Student", back_populates="parent")
    classes_taught = relationship("Class", back_populates="teacher")


class Student(Base):
    """Student model."""
    __tablename__ = "students"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    parent = relationship("User", back_populates="students")
    class_ = relationship("Class", back_populates="students")
    homework = relationship("Homework", back_populates="student")


class Homework(Base):
    """Homework assignment model."""
    __tablename__ = "homework"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    subject = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime(timezone=True))
    status = Column(String(20), default="pending")
    priority = Column(String(20), default="medium")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    student = relationship("Student", back_populates="homework")
    reminders = relationship("Reminder", back_populates="homework")


class Reminder(Base):
    """Reminder model."""
    __tablename__ = "reminders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    homework_id = Column(UUID(as_uuid=True), ForeignKey("homework.id"))
    reminder_time = Column(DateTime(timezone=True), nullable=False)
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    
    homework = relationship("Homework", back_populates="reminders")


class OCRResult(Base):
    """OCR processing result."""
    __tablename__ = "ocr_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    homework_id = Column(UUID(as_uuid=True), ForeignKey("homework.id"))
    image_path = Column(String(500))
    extracted_text = Column(Text)
    confidence_score = Column(DECIMAL(5, 4))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MessageLog(Base):
    """Message delivery log."""
    __tablename__ = "message_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    message_type = Column(String(50))  # telegram, whatsapp
    message_content = Column(Text)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered = Column(Boolean, default=False)


class UserConsent(Base):
    """User consent records for PDPA compliance."""
    __tablename__ = "user_consents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    consent_type = Column(String(50), nullable=False)
    granted = Column(Boolean, default=False)
    granted_at = Column(DateTime(timezone=True))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    __table_args__ = (UniqueConstraint('user_id', 'consent_type'),)
