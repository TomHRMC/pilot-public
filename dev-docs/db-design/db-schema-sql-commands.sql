-- View all functions
SELECT
    n.nspname AS schema_name,
    p.proname AS function_name,
    pg_get_function_result(p.oid) AS return_type,
    p.prosrc AS function_body
FROM pg_catalog.pg_proc p
JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
  -- 'f' filters for standard functions, excluding aggregates/window functions
  AND p.prokind = 'f' 
  AND pg_get_function_result(p.oid) = 'trigger'
ORDER BY schema_name, function_name;

-- View all triggers
SELECT 
    event_object_schema AS schema_name,
    event_object_table AS table_name,
    trigger_name, 
    action_timing AS timing,
    event_manipulation AS event, 
    action_statement AS execution_function
FROM information_schema.triggers
WHERE event_object_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY schema_name, table_name, trigger_name;

-- View all custom types (enums)
SELECT 
    n.nspname AS schema_name,
    t.typname AS enum_name,
    string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS allowed_values
FROM pg_catalog.pg_type t
JOIN pg_catalog.pg_enum e ON t.oid = e.enumtypid
JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
GROUP BY schema_name, enum_name
ORDER BY schema_name, enum_name;

-- View all installed extensions
SELECT 
    extname AS extension_name, 
    extversion AS version 
FROM pg_catalog.pg_extension
ORDER BY extension_name;
