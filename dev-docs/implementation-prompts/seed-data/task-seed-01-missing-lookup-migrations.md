# Task: Seed Data Step 1 — Missing Lookup Data Alembic Migrations

**Mode**: Pilot Python Engineer
**Phase**: Pre-Workstream 3, Phase 0, Milestone Step 1
**Priority**: Critical — blocks all UI testing
**Authoritative plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §0.4 and §0.5

---

## Context

The dev DB has been audited (May 31, 2026) and 13 lookup tables that have `seed_rows` defined in the JSON schema (`dev-docs/db-design/pilot-db-schema-v2.6h.json`) currently have 0 rows in the live database and no Alembic migration to populate them. Additionally, 8 tables that are currently seeded only via `backend/migrations/seed_test_data.py` are genuinely core platform data and should be promoted to Alembic migrations so they reach production automatically on deploy.

This task writes three Alembic **data-only** migrations (no schema changes) to fix this gap. These are pure seed migrations — no `CREATE TABLE`, no `ALTER TABLE`, no ORM model changes.

---

## Reference Files

Read these before writing any code:

- **Authoritative plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` — §0.4 (audit table) and §0.5 (migration list with exact rows)
- **JSON schema seed_rows**: `dev-docs/db-design/pilot-db-schema-v2.6h.json` — each table's `seed_rows` array is the authoritative source for what values to insert
- **DB query guide**: `dev-docs/db-design/postgres-mcp-guide.md` — use postgres-local MCP to verify current row counts before and after
- **Migration standards**: `dev-docs/architecture-design/pilot-python-engineer-methods.md` §13 (Alembic standards) and §16.1 (regression baseline)
- **Existing seed migration pattern**: `backend/migrations/versions/2026_05_11_1915-9f8116bb6ad1_phase_fe_1_batch_b17_missing_lookup_.py` — this is the established pattern for data-only seed migrations; follow it exactly

---

## Pre-Work: Establish Regression Baseline

Before writing any migration file:

```bash
cd <repo>/backend
source .venv/bin/activate

# Unit test baseline
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

Record the pass/fail count. Do not proceed if any tests are failing.

Also verify current row counts using the postgres-local MCP tool:

```sql
SELECT
  (SELECT COUNT(*) FROM public.platform_role) AS platform_role,
  (SELECT COUNT(*) FROM public.subscription_status) AS subscription_status,
  (SELECT COUNT(*) FROM public.jwk_status) AS jwk_status,
  (SELECT COUNT(*) FROM public.sso_provider) AS sso_provider,
  (SELECT COUNT(*) FROM public.customer_lifecycle_status) AS customer_lifecycle_status,
  (SELECT COUNT(*) FROM public.site_lifecycle_status) AS site_lifecycle_status,
  (SELECT COUNT(*) FROM public.supplier_lifecycle_status) AS supplier_lifecycle_status,
  (SELECT COUNT(*) FROM public.job_expense_category) AS job_expense_category,
  (SELECT COUNT(*) FROM public.qpl_contact_action_type) AS qpl_contact_action_type,
  (SELECT COUNT(*) FROM public.webhook_event_type) AS webhook_event_type,
  (SELECT COUNT(*) FROM public.tenant_user_status) AS tenant_user_status,
  (SELECT COUNT(*) FROM public.address_type) AS address_type,
  (SELECT COUNT(*) FROM public.contact_type) AS contact_type,
  (SELECT COUNT(*) FROM public.taxability_code) AS taxability_code,
  (SELECT COUNT(*) FROM public.currency) AS currency,
  (SELECT COUNT(*) FROM public.job_status) AS job_status;
```

All should be 0 (or current count for `tenant_user_status` = 1, `address_type` = 4, `contact_type` = 4, `taxability_code` = 3, `currency` = 4, `job_status` = 5 if seeded by `seed_test_data.py`). Record counts before starting.

---

## Migration 1: Missing Lookup Tables — Independent Tables

**File naming convention** (follow §13 of methods doc):
```
alembic revision -m "seed_missing_lookup_tables_batch_1"
```

This migration seeds all tables that have no FK dependencies between them. Use the **exact pattern** from `batch_b17`:

```python
def upgrade() -> None:
    # Bypass immutability triggers for seed inserts — canonical migration pattern
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # All INSERTs use ON CONFLICT DO NOTHING for idempotency
    # Use gen_random_uuid() for UUID primary keys
    # Use now() for created_at / updated_at
    # tenant_id = NULL for all global (system-level) seed rows
```

### Tables and rows to seed (in this migration):

**`platform_role`** (3 rows — Pilot staff roles for managing tenants):
- `accountant`: read-only across tenants; no write; no impersonate
- `owner`: full write (tenants, users, suppliers, billing, jwks, plans, notifications); `impersonate_tenant=true`, `manage_jwks=true`
- `support`: limited write (tenants, users, billing, notifications); `impersonate_tenant=true`, `manage_jwks=false`

> ⚠️ `platform_role.permissions` is a JSONB column. Use this exact structure:
> ```json
> {"read_all": true, "write": ["tenants", "users"], "impersonate_tenant": true, "manage_jwks": false}
> ```
> Query the column type first: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'platform_role' ORDER BY ordinal_position;`

**`subscription_status`** (4 rows):
- `trial` (is_billing_active=true)
- `active` (is_billing_active=true)
- `past_due` (is_billing_active=true)
- `canceled` (is_billing_active=false)

**`jwk_status`** (3 rows — no `tenant_id` column on this table):
- `active` (is_default=true, is_signable=true)
- `retiring` (is_default=false, is_signable=false)
- `retired` (is_default=false, is_signable=false)

> ⚠️ `jwk_status` does NOT have a `tenant_id` column. Do NOT include it in the INSERT.

**`sso_provider`** (2 rows — code-keyed, no id/tenant_id):
- `google` (name="Google", is_active=true)
- `microsoft` (name="Microsoft", is_active=true)

> ⚠️ `sso_provider` uses `code` as the primary key (VARCHAR), not a UUID `id`. Do NOT generate a UUID for it.

**`customer_lifecycle_status`** (4 rows, tenant_id=NULL for global seeds):
- `prospect` (is_default=true)
- `active` (is_default=false)
- `dormant` (is_default=false)
- `churned` (is_default=false)

**`site_lifecycle_status`** (3 rows, tenant_id=NULL):
- `active` (is_default=true)
- `construction` (is_default=false)
- `closed` (is_default=false)

**`supplier_lifecycle_status`** (2 rows, tenant_id=NULL):
- `active` (is_default=true)
- `deprecated` (is_default=false)

**`supplier_item_category`** — Read the `seed_rows` from the JSON schema directly:
```bash
cd <repo>/backend
python schema_manager.py get --path tables.supplier_item_category.seed_rows
```
Use those exact rows (tenant_id=NULL for all).

**`supplier_item_uom`** — Read the `seed_rows` from the JSON schema directly:
```bash
python schema_manager.py get --path tables.supplier_item_uom.seed_rows
```

**`job_expense_category`** (3 rows, tenant_id=NULL for global seeds):
- `materials` (code="materials", name="Materials & Supplies", is_default=true)
- `equipment` (code="equipment", name="Equipment Rental", is_default=false)
- `permits` (code="permits", name="Permits & Fees", is_default=false)

**`qpl_contact_action_type`** (4 rows, tenant_id=NULL):
- `view` (is_default=true, is_active=true)
- `approve` (is_default=false, is_active=false — Phase 2, pre-register)
- `request_change` (is_default=false, is_active=false — Phase 2)
- `message` (is_default=false, is_active=false — Phase 2)

**`webhook_event_type`** — Read the `seed_rows` from the JSON schema directly:
```bash
python schema_manager.py get --path tables.webhook_event_type.seed_rows
```

> ⚠️ `webhook_event_type` uses `code` as the primary key (VARCHAR), not UUID.

**`tenant_user_status`** — Add 3 missing rows (the "active" row already exists; add only the missing ones using `ON CONFLICT DO NOTHING`):
- `invited` (is_default=false)
- `suspended` (is_default=false)
- `pending` (is_default=false)

**Promoted from `seed_test_data.py`** — These are core platform data that must travel to production. Read the seed values from `backend/migrations/seed_test_data.py` for the exact data:
- `address_type` (4 rows: billing, service_location, mailing, shipping)
- `contact_type` (4 rows: primary, billing, technical, decision_maker)
- `taxability_code` (3 rows: taxable, exempt, zero_rated) — note: the 3 test-specific `tax_rate_version` rows stay in `seed_test_data.py` only; only the `taxability_code` lookup moves here
- `currency` (4 rows: USD, CAD, EUR, GBP)
- `job_status` (5 rows: draft, scheduled, in_progress, completed, cancelled)
- `app_service_category` (QuickBooks category)
- `app_service_provider` (Intuit provider)
- `app_service` (QuickBooks Online app service — scoped to NULL tenant_id for global availability)

> ⚠️ For `app_service_category`, `app_service_provider`, `app_service`: query the column list before inserting — these tables have non-standard structures. Use: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name IN ('app_service_category', 'app_service_provider', 'app_service') ORDER BY table_name, ordinal_position;`

---

## Migration 2: System User Sentinel

**File naming convention**:
```
alembic revision -m "seed_system_user_sentinel"
```

This migration seeds the `user` system sentinel row. It must come **after** Migration 1 because it may reference `platform_role` (the column is nullable but should be set correctly if platform roles now exist).

**`user`** (1 row — the Pilot internal system account):
- `id = '00000000-0000-0000-0000-000000000000'` (hardcoded sentinel UUID)
- `email = 'system@pilot.internal'`
- `first_name = 'Pilot'`
- `last_name = 'System'`
- `is_platform_user = false`
- `platform_role_code = NULL`
- `is_active = false`
- `email_verified_at = now()`
- `require_password_reset = false`
- `mfa_enforced = false`

> ⚠️ The `user` table has immutability triggers (`guard_created_fields_immutable`). Use `SET LOCAL session_replication_role = 'replica'` to bypass them during the seed insert.

> ⚠️ Use `WHERE NOT EXISTS` guard pattern (same as `task_1d1_quote_converted_status_seed.py`) to prevent duplicate inserts if migration is re-run in unusual circumstances:
> ```sql
> INSERT INTO "user" (...)
> SELECT ...
> WHERE NOT EXISTS (SELECT 1 FROM "user" WHERE id = '00000000-0000-0000-0000-000000000000');
> ```

---

## Migration 3: Communication Template Gap-Fill

**File naming convention**:
```
alembic revision -m "seed_communication_template_gap_fill"
```

`communication_template` currently has 7 rows seeded by `batch_b4` migration. `customer_comm_template_type` has 27 rows. The gap means 20 communication types have no template. This migration adds placeholder templates for the critical missing types.

Before writing this migration, query what currently exists:
```sql
SELECT template_code FROM public.communication_template ORDER BY template_code;
```

And query the full list of `customer_comm_template_type` codes:
```sql
SELECT code, name, is_active FROM public.customer_comm_template_type ORDER BY sort_order;
```

Add placeholder templates for these critical types at minimum (check which ones are NOT already in `communication_template`):
- `quote_sent` (SMS + email channels)
- `invoice_sent` (SMS + email channels)
- `appointment_reminder` (SMS + email channels)
- `payment_received` (SMS + email channels)

Template body content can be placeholder text for beta — e.g., `"Your quote is ready. Reply STOP to opt out."` — real copy will be authored before launch.

> ⚠️ `communication_template` has a `tenant_id` column (NULL = system-level). All new rows should use `tenant_id = NULL`.
> ⚠️ Use `ON CONFLICT DO NOTHING` keyed on the natural key — check what the unique constraint is first: `SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'public.communication_template'::regclass;`

---

## Migration Verification Loop (Required for ALL 3 Migrations)

After writing each migration, run the triple-verify loop per §13.2:

```bash
cd <repo>/backend
source .venv/bin/activate

alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

All three must succeed cleanly. A migration that doesn't cleanly downgrade is not accepted. The `downgrade()` function must `DELETE` the specific rows seeded by `upgrade()` (keyed on `code`, `id`, or `template_code` as appropriate — never a bulk `TRUNCATE` of the whole table).

---

## JSON Schema Sync (schema_manager.py)

The master JSON schema file (`dev-docs/db-design/pilot-db-schema-v2.6h.json`) is the **source** for most seed rows in this task — the `seed_rows` arrays in the JSON were read to produce the migration INSERTs. However, for any rows being inserted that are **not yet in the JSON `seed_rows`**, you must add them using `schema_manager.py` to keep the schema file as the single source of truth.

**Tables that need their JSON `seed_rows` updated:**

**1. `tenant_user_status`** — The 3 new rows (`invited`, `suspended`, `pending`) are not currently in the JSON. Add them:

```bash
cd <repo>/backend

cat << 'EOF' > /tmp/temp_payload.json
{"id": "uuid-gen", "code": "invited", "name": "Invited", "is_default": false, "is_active": true}
EOF
python schema_manager.py array-append --path tables.tenant_user_status.seed_rows --payload /tmp/temp_payload.json

cat << 'EOF' > /tmp/temp_payload.json
{"id": "uuid-gen", "code": "suspended", "name": "Suspended", "is_default": false, "is_active": true}
EOF
python schema_manager.py array-append --path tables.tenant_user_status.seed_rows --payload /tmp/temp_payload.json

cat << 'EOF' > /tmp/temp_payload.json
{"id": "uuid-gen", "code": "pending", "name": "Pending", "is_default": false, "is_active": true}
EOF
python schema_manager.py array-append --path tables.tenant_user_status.seed_rows --payload /tmp/temp_payload.json
rm /tmp/temp_payload.json
```

**2. `platform_role` owner permissions update** — The JSON schema's `owner` row has outdated permissions (missing `tenants`, `users`, `notifications` in the write array). Update it in-place:

```bash
cat << 'EOF' > /tmp/temp_payload.json
{
  "code": "owner",
  "name": "Platform Owner (Read/Write)",
  "description": "Full read, selected write incl. JWKS and plan management; can impersonate tenants.",
  "permissions": {
    "read_all": true,
    "write": ["tenants", "users", "suppliers", "billing", "jwks", "plans", "notifications"],
    "impersonate_tenant": true,
    "manage_jwks": true
  },
  "is_default": false,
  "is_active": true
}
EOF
python schema_manager.py array-update \
  --path tables.platform_role.seed_rows \
  --match-key code \
  --match-value owner \
  --payload /tmp/temp_payload.json
rm /tmp/temp_payload.json
```

**3. Verify all other tables' JSON seed_rows match what was inserted.** Spot-check a few:

```bash
python schema_manager.py get --path tables.customer_lifecycle_status.seed_rows
python schema_manager.py get --path tables.subscription_status.seed_rows
python schema_manager.py get --path tables.address_type.seed_rows
```

If any JSON `seed_rows` are missing rows that were inserted, add them with `array-append`. If any have incorrect values, update with `array-update`.

**Do not proceed to post-migration verification until the JSON schema is confirmed consistent with what was seeded.**

> Note: Ask Tom to run `schema_diff.py` and review `schema_diff_report.html` after this step. Data-only migrations should produce zero structural discrepancies. If any structural diff appears, stop and investigate before proceeding.

---

## Post-Migration Verification

After all 3 migrations triple-verified, `alembic upgrade head` applied, and JSON schema synced — verify using postgres-local MCP:

```sql
SELECT
  (SELECT COUNT(*) FROM public.platform_role) AS platform_role,
  (SELECT COUNT(*) FROM public.subscription_status) AS subscription_status,
  (SELECT COUNT(*) FROM public.jwk_status) AS jwk_status,
  (SELECT COUNT(*) FROM public.sso_provider) AS sso_provider,
  (SELECT COUNT(*) FROM public.customer_lifecycle_status) AS customer_lifecycle_status,
  (SELECT COUNT(*) FROM public.site_lifecycle_status) AS site_lifecycle_status,
  (SELECT COUNT(*) FROM public.supplier_lifecycle_status) AS supplier_lifecycle_status,
  (SELECT COUNT(*) FROM public.job_expense_category) AS job_expense_category,
  (SELECT COUNT(*) FROM public.qpl_contact_action_type) AS qpl_contact_action_type,
  (SELECT COUNT(*) FROM public.tenant_user_status) AS tenant_user_status,
  (SELECT COUNT(*) FROM public.address_type) AS address_type,
  (SELECT COUNT(*) FROM public.contact_type) AS contact_type,
  (SELECT COUNT(*) FROM public.currency) AS currency,
  (SELECT COUNT(*) FROM public.job_status) AS job_status,
  (SELECT COUNT(*) FROM public."user" WHERE id = '00000000-0000-0000-0000-000000000000') AS system_user;
```

Expected results:
- `platform_role`: 3
- `subscription_status`: 4
- `jwk_status`: 3
- `sso_provider`: 2
- `customer_lifecycle_status`: 4
- `site_lifecycle_status`: 3
- `supplier_lifecycle_status`: 2
- `job_expense_category`: 3
- `qpl_contact_action_type`: 4
- `tenant_user_status`: 4 (1 existing "active" + 3 new)
- `address_type`: 4
- `contact_type`: 4
- `currency`: 4
- `job_status`: 5
- `system_user`: 1

---

## Final Regression Check

```bash
cd <repo>/backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

Pass count must match (or exceed) the baseline captured in Pre-Work. No new failures permitted.

---

## Definition of Done

- [ ] Migration 1 (`seed_missing_lookup_tables_batch_1`) triple-verified and applies cleanly
- [ ] Migration 2 (`seed_system_user_sentinel`) triple-verified and applies cleanly
- [ ] Migration 3 (`seed_communication_template_gap_fill`) triple-verified and applies cleanly
- [ ] All tables show expected row counts in post-migration verification query
- [ ] `downgrade()` implemented for each migration (deletes only the rows seeded by `upgrade()`)
- [ ] Full unit test regression passes with zero new failures
- [ ] **Ask Tom to confirm** before marking complete — show him the verification query results

---

## Important Constraints

- **No ORM model changes** in this task — these are data-only migrations
- **No `--autogenerate`** — generate blank migrations and write SQL manually (§13.1)
- **No `TRUNCATE`** in `downgrade()` — delete only the specific rows added by this migration
- **No schema changes** — if a table column is missing that prevents a seed INSERT, stop and report to Tom rather than adding the column
- **Use `SET LOCAL session_replication_role = 'replica'`** in every `upgrade()` function to bypass immutability triggers (established pattern from batch_b17)
- **Use `ON CONFLICT DO NOTHING`** on all INSERTs for idempotency
- The JSON schema file (`dev-docs/db-design/pilot-db-schema-v2.6h.json`) is the authoritative source for seed_rows values — do not invent values
