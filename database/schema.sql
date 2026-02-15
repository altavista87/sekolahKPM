-- EduSync Database Schema
-- PostgreSQL 15+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE,
    whatsapp_phone VARCHAR(20),
    email VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('parent', 'teacher', 'admin')),
    preferred_language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'Asia/Singapore',
    notification_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Students table
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    class_id VARCHAR(50),
    parent_id UUID REFERENCES users(id) ON DELETE CASCADE,
    school_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Schools table
CREATE TABLE schools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Classes table
CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    school_id UUID REFERENCES schools(id),
    teacher_id UUID REFERENCES users(id),
    grade_level VARCHAR(20),
    academic_year INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Homework table
CREATE TABLE homework (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    teacher_id UUID REFERENCES users(id),
    subject VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    raw_text TEXT,
    due_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'overdue')),
    priority INTEGER DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    image_urls TEXT[],
    file_urls TEXT[],
    ai_enhanced BOOLEAN DEFAULT FALSE,
    ai_summary TEXT,
    ai_keywords TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Reminders table
CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    homework_id UUID REFERENCES homework(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    reminder_time TIMESTAMP WITH TIME ZONE NOT NULL,
    message TEXT,
    sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Message logs table
CREATE TABLE message_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('telegram', 'whatsapp')),
    message_type VARCHAR(50) NOT NULL,
    recipient VARCHAR(100) NOT NULL,
    content TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    external_id VARCHAR(100),
    cost_usd DECIMAL(10, 6),
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- OCR results table
CREATE TABLE ocr_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    homework_id UUID REFERENCES homework(id) ON DELETE CASCADE,
    image_path TEXT NOT NULL,
    extracted_text TEXT,
    confidence DECIMAL(5, 4),
    language VARCHAR(20),
    processing_time_ms INTEGER,
    engine VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit log table
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data JSONB,
    new_data JSONB,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_telegram ON users(telegram_id);
CREATE INDEX idx_users_whatsapp ON users(whatsapp_phone);
CREATE INDEX idx_homework_student ON homework(student_id);
CREATE INDEX idx_homework_status ON homework(status);
CREATE INDEX idx_homework_due_date ON homework(due_date);
CREATE INDEX idx_reminders_user ON reminders(user_id);
CREATE INDEX idx_reminders_time ON reminders(reminder_time) WHERE sent = FALSE;
CREATE INDEX idx_message_logs_user ON message_logs(user_id);
CREATE INDEX idx_audit_table_record ON audit_log(table_name, record_id);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_homework_updated_at BEFORE UPDATE ON homework
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
