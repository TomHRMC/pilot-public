-- Set the target table name
SET my.target_schema = 'public';
SET my.target_table = 'voice_command_log';

-- View columns, types and defaults
SELECT 
    column_name, 
    data_type, 
    character_maximum_length AS max_len,
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_schema = current_setting('my.target_schema') 
  AND table_name = current_setting('my.target_table')
ORDER BY ordinal_position;

-- View indexes
SELECT 
    indexname AS index_name, 
    indexdef AS index_definition
FROM pg_indexes
WHERE schemaname = current_setting('my.target_schema') 
  AND tablename = current_setting('my.target_table');

-- View constraints (primary, foreign, unique, check)
SELECT 
    tc.constraint_name, 
    tc.constraint_type, 
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
  ON tc.constraint_name = kcu.constraint_name 
 AND tc.table_schema = kcu.table_schema
WHERE tc.table_schema = current_setting('my.target_schema')
  AND tc.table_name = current_setting('my.target_table')
ORDER BY tc.constraint_type, tc.constraint_name;

-- View triggers
SELECT 
    trigger_name, 
    action_timing, 
    event_manipulation AS trigger_event, 
    action_statement
FROM information_schema.triggers
WHERE event_object_schema = current_setting('my.target_schema')
  AND event_object_table = current_setting('my.target_table')
ORDER BY trigger_name;
