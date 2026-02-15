-- PDPA Compliance Check Queries

-- 1. Check for inactive users with personal data older than retention period
SELECT 
    id,
    name,
    email,
    created_at,
    NOW() - created_at as data_age
FROM users
WHERE notification_enabled = FALSE
    AND NOW() - created_at > INTERVAL '1 year'
ORDER BY created_at ASC;

-- 2. List all data access by user (audit trail)
SELECT 
    table_name,
    action,
    record_id,
    user_id,
    created_at
FROM audit_log
WHERE created_at > NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;

-- 3. Find users without consent records
SELECT 
    u.id,
    u.name,
    u.email,
    u.created_at
FROM users u
LEFT JOIN user_consent uc ON u.id = uc.user_id
WHERE uc.id IS NULL;

-- 4. Data export for specific user (right to data portability)
SELECT 
    'user_info' as data_type,
    jsonb_build_object(
        'name', name,
        'email', email,
        'phone', whatsapp_phone,
        'language', preferred_language
    ) as data
FROM users WHERE id = :user_id

UNION ALL

SELECT 
    'students' as data_type,
    jsonb_agg(
        jsonb_build_object('name', s.name, 'class', s.class_id)
    ) as data
FROM students s WHERE s.parent_id = :user_id

UNION ALL

SELECT 
    'homework' as data_type,
    jsonb_agg(
        jsonb_build_object(
            'subject', h.subject,
            'title', h.title,
            'status', h.status,
            'created_at', h.created_at
        )
    ) as data
FROM homework h
JOIN students s ON h.student_id = s.id
WHERE s.parent_id = :user_id;

-- 5. Anonymize user data (right to be forgotten)
-- WARNING: Run with caution!
/*
UPDATE users 
SET 
    name = 'DELETED_USER_' || LEFT(id::text, 8),
    email = NULL,
    whatsapp_phone = NULL,
    telegram_id = NULL,
    notification_enabled = FALSE
WHERE id = :user_id;

UPDATE students
SET name = 'ANONYMOUS_STUDENT'
WHERE parent_id = :user_id;
*/
