-- ═══════════════════════════════════════════════════════════════════════════
-- audit_mcp_readonly_privs.sql
-- Purpose: Diagnose mcp_readonly role privileges on pilot_prod
-- Run as:  pilot_user via SSH tunnel (port 5433)
--   psql "host=127.0.0.1 port=5433 dbname=pilot_prod user=pilot_user" \
--     -f admin-tools/audit_mcp_readonly_privs.sql
-- Date:    2026-08-09
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. Role attributes + database-level grants ──────────────────────────────
SELECT r.rolname, r.rolcanlogin, r.rolconnlimit,
       has_database_privilege(r.rolname, 'pilot_prod', 'CONNECT') AS can_connect
FROM pg_roles r
WHERE r.rolname = 'mcp_readonly';

-- ── 2. Schema usage ─────────────────────────────────────────────────────────
SELECT n.nspname AS schema,
       has_schema_privilege('mcp_readonly', n.nspname, 'USAGE') AS has_usage
FROM pg_namespace n
WHERE n.nspname IN ('public', 'audit');

-- ── 3. Table SELECT coverage (granted vs. total) ────────────────────────────
SELECT n.nspname AS schema,
       count(*) FILTER (WHERE has_table_privilege('mcp_readonly', c.oid, 'SELECT')) AS select_ok,
       count(*) AS total_tables
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN ('public', 'audit') AND c.relkind IN ('r','p')
GROUP BY n.nspname;

-- ── 4. Tables mcp_readonly CANNOT select (should return 0 rows) ─────────────
SELECT n.nspname || '.' || c.relname AS missing_select
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN ('public', 'audit') AND c.relkind IN ('r','p')
  AND NOT has_table_privilege('mcp_readonly', c.oid, 'SELECT')
ORDER BY 1;

-- ── 5. Default privileges for FUTURE tables (post-migration gap check) ──────
-- Want: rows showing mcp_readonly=r (SELECT) for public + audit, grantor pilot_user
SELECT pg_get_userbyid(d.defaclrole) AS grantor,
       n.nspname AS schema,
       d.defaclobjtype AS obj_type,
       d.defaclacl::text AS acl
FROM pg_default_acl d
JOIN pg_namespace n ON n.oid = d.defaclnamespace
WHERE n.nspname IN ('public', 'audit');
