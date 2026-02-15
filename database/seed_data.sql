-- EduSync Seed Data

-- Insert sample schools
INSERT INTO schools (id, name, address, contact_email, contact_phone) VALUES
('550e8400-e29b-41d4-a716-446655440000', 'Sample Primary School', '123 Education Street', 'admin@sample.edu', '+65-6123-4567'),
('550e8400-e29b-41d4-a716-446655440001', 'Example Secondary School', '456 Learning Avenue', 'contact@example.edu', '+65-6987-6543');

-- Insert sample users (parents)
INSERT INTO users (id, telegram_id, whatsapp_phone, email, name, role, preferred_language) VALUES
('660e8400-e29b-41d4-a716-446655440000', 123456789, '+6591234567', 'parent1@example.com', 'Sarah Tan', 'parent', 'en'),
('660e8400-e29b-41d4-a716-446655440001', 234567890, '+6592345678', 'parent2@example.com', 'John Lim', 'parent', 'zh'),
('660e8400-e29b-41d4-a716-446655440002', 345678901, '+6593456789', 'parent3@example.com', 'Ahmad bin Abdullah', 'parent', 'ms');

-- Insert sample users (teachers)
INSERT INTO users (id, telegram_id, email, name, role) VALUES
('770e8400-e29b-41d4-a716-446655440000', 456789012, 'teacher1@sample.edu', 'Ms. Lee', 'teacher'),
('770e8400-e29b-41d4-a716-446655440001', 567890123, 'teacher2@sample.edu', 'Mr. Kumar', 'teacher');

-- Insert sample students
INSERT INTO students (id, name, class_id, parent_id, school_id) VALUES
('880e8400-e29b-41d4-a716-446655440000', 'Emma Tan', '5A', '660e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('880e8400-e29b-41d4-a716-446655440001', 'Lucas Lim', '4B', '660e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000'),
('880e8400-e29b-41d4-a716-446655440002', 'Aisha binti Ahmad', '6C', '660e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000');

-- Insert sample homework (pending)
INSERT INTO homework (id, student_id, teacher_id, subject, title, description, due_date, status, priority, ai_enhanced) VALUES
('990e8400-e29b-41d4-a716-446655440000', '880e8400-e29b-41d4-a716-446655440000', '770e8400-e29b-41d4-a716-446655440000', 'Mathematics', 'Algebra Worksheet', 'Complete exercises 1-20 on page 45. Focus on solving linear equations.', NOW() + INTERVAL '3 days', 'pending', 4, TRUE),
('990e8400-e29b-41d4-a716-446655440001', '880e8400-e29b-41d4-a716-446655440000', '770e8400-e29b-41d4-a716-446655440001', 'English', 'Reading Comprehension', 'Read the passage and answer questions 1-5.', NOW() + INTERVAL '5 days', 'pending', 3, TRUE),
('990e8400-e29b-41d4-a716-446655440002', '880e8400-e29b-41d4-a716-446655440001', '770e8400-e29b-41d4-a716-446655440000', 'Science', 'Plant Life Cycle', 'Draw and label the stages of a plant life cycle.', NOW() + INTERVAL '2 days', 'pending', 4, FALSE);

-- Insert sample homework (completed)
INSERT INTO homework (id, student_id, teacher_id, subject, title, description, due_date, status, priority, completed_at) VALUES
('990e8400-e29b-41d4-a716-446655440003', '880e8400-e29b-41d4-a716-446655440000', '770e8400-e29b-41d4-a716-446655440000', 'Chinese', 'Character Writing', 'Practice writing characters on page 12.', NOW() - INTERVAL '2 days', 'completed', 2, NOW() - INTERVAL '1 day');

-- Insert sample reminders
INSERT INTO reminders (id, homework_id, user_id, reminder_time, message, sent) VALUES
('aa0e8400-e29b-41d4-a716-446655440000', '990e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440000', NOW() + INTERVAL '2 days', 'Mathematics homework due tomorrow!', FALSE),
('aa0e8400-e29b-41d4-a716-446655440001', '990e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440001', NOW() + INTERVAL '1 day', 'Science project due soon!', FALSE);
