# PostgreSQL MCP Cheatsheet for AI Agents

You are connected to a PostgreSQL database via an MCP server. When querying the database to discover schema information, **do not guess the SQL syntax.** Use the exact queries provided below.

### 🔌 Two MCP servers — both read-only

| MCP server | Target | When to use | Access gate |
|---|---|---|---|
| **`postgres-local`** | Local dev database | Default for all routine schema + data verification. | Always available. |
| **`postgres-prod`** | Production database (via SSH tunnel) | Only when the task explicitly needs **production** state (drift check, prod incident, prod-only data condition). | **SSH tunnel controlled by Tom.** Ask Tom to confirm the tunnel is up **before** your first `postgres-prod` query. A connection-failure error = tunnel is down → STOP and ask Tom; do not retry blindly. |

Both connections are **read-only** — verification only. Never INSERT/UPDATE/DELETE through either MCP; all data changes go through Alembic migrations, seed scripts, or application code. See the global rule [`.roo/rules/02-database-mcp-access.md`](../../.roo/rules/02-database-mcp-access.md). The query snippets below work identically against either server.

### 🛑 CRITICAL CONSTRAINTS
1. **Target Schemas:** This database utilizes two primary schemas: `public` (domain data) and `audit` (the `event` table). If you do not filter by these schemas, you will either get empty arrays or be overwhelmed by thousands of internal PostgreSQL system objects.
2. **Always Parameterize:** The queries below use `'your_table_name'`. Replace this with the actual table name you are investigating.
3. **No SQLite Syntax:** Do not use `PRAGMA` or `SHOW TABLES`. This is strictly PostgreSQL.
4. **`postgres-prod` requires Tom's tunnel:** Never assume the prod tunnel is up. Confirm with Tom first, and treat prod reads as sensitive (query only the columns you need — avoid dumping PII).

---

### 1. List All Tables (Across Public & Audit)
Use this to discover what tables exist in the database.
```sql
SELECT table_schema, table_name 
FROM information_schema.tables 
WHERE table_schema IN ('public', 'audit') 
  AND table_type = 'BASE TABLE'
ORDER BY table_schema, table_name;
```

### 2. Get All Columns for a Specific Table
Use this to see data types, default values, and nullability.
```sql
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_schema IN ('public', 'audit') 
  AND table_name = 'your_table_name'
ORDER BY ordinal_position;
```

### 3. Find the Primary Key of a Table
Use this to identify the unique identifier for a table.
```sql
SELECT kcu.column_name
FROM information_schema.table_constraints tco
JOIN information_schema.key_column_usage kcu 
  ON kcu.constraint_name = tco.constraint_name 
  AND kcu.constraint_schema = tco.constraint_schema
WHERE tco.constraint_type = 'PRIMARY KEY' 
  AND kcu.table_schema IN ('public', 'audit')
  AND kcu.table_name = 'your_table_name';
```

### 4. Find All Foreign Keys for a Table
Use this to understand how a table relates to other entities.
```sql
SELECT
    kcu.column_name AS local_column,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_schema IN ('public', 'audit')
  AND tc.table_name = 'your_table_name';
```

### 5. Find All Indexes for a Table
Use this to see B-Tree, GiST, or partial indexes (useful for identifying uniqueness constraints or query optimization targets).
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE schemaname IN ('public', 'audit') 
  AND tablename = 'your_table_name';
```

### 6. Get All Triggers on a Table
PostgreSQL's `information_schema` is notoriously bad for triggers. Use this `pg_trigger` query to get the exact `CREATE TRIGGER` definition.
```sql
SELECT tgname AS trigger_name, pg_get_triggerdef(oid) AS trigger_definition
FROM pg_trigger
WHERE tgrelid = 'public.your_table_name'::regclass 
  AND tgisinternal = false;
```
*(Note: Change `public.your_table_name` to `audit.your_table_name` if checking the audit table).*

### 7. List Custom Functions (Stored Procedures)
Use this to view the custom business logic (like audit logging or totals calculation) stored in the database.
```sql
SELECT p.proname AS function_name, pg_get_functiondef(p.oid) AS function_definition
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname IN ('public', 'audit')
ORDER BY p.proname;
```

### 8. Find Constraints (CHECK and EXCLUDE)
Use this to find business logic validation rules enforced at the database level.
```sql
SELECT conname AS constraint_name, pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'public.your_table_name'::regclass;
```

## Appendix A. Use Case Examples

**Before B11 (SMS/Telnyx) — verify TCPA opt-in/opt-out columns:**
```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'customer' AND column_name LIKE 'sms%'
ORDER BY column_name;
```
Expected if pre-existing: `sms_opted_out`, `sms_opt_out_at`, `sms_opt_in_consent`, `sms_opt_in_at`, `sms_opt_in_source`. If absent, add them in B11/A59 migration.

**Before B3 (Dispatch Board) — verify Receipt OCR and schedule history:**
```sql
-- Check for OCR-related Celery task routines
SELECT routine_name FROM information_schema.routines
WHERE routine_name LIKE '%receipt%' OR routine_name LIKE '%ocr%';

-- Check for existing customer preferred_contact_channel column (needed by A21)
SELECT column_name FROM information_schema.columns
WHERE table_name = 'customer' AND column_name = 'preferred_contact_channel';
```

**Before B5 (Reports) — verify dunning Celery task:**
```sql
-- Check task files from the OS (cannot use SQL for this — check backend/tasks/ directory listing)
-- SQL: verify any dunning-related cron stored procedures
SELECT routine_name FROM information_schema.routines
WHERE routine_name LIKE '%dun%' OR routine_name LIKE '%overdue%';
```

**Before any batch — confirm a table's exact column list:**
```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'YOUR_TABLE_NAME'
ORDER BY ordinal_position;
```

**Check existing indexes on a table (avoid duplicate index migrations):**
```sql
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename = 'YOUR_TABLE_NAME'
ORDER BY indexname;
```

**Check existing constraints (avoid duplicate constraint migrations):**
```sql
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'YOUR_TABLE_NAME';
```