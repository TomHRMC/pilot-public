# Task: Seed Data Step 2 — Dev/QA Seed Scripts

**Mode**: Pilot Python Engineer
**Phase**: Pre-Workstream 3, Phase 0, Milestone Step 2
**Prerequisite**: Step 1 complete — `alembic upgrade head` is at the latest revision and all 13 previously-missing lookup tables now have rows
**Authoritative plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §0.3, §0.5, §0.6

---

## Table of Contents

- [Task: Seed Data Step 2 — Dev/QA Seed Scripts](#task-seed-data-step-2--devqa-seed-scripts)
  - [Table of Contents](#table-of-contents)
  - [Context](#context)
  - [Reference Files](#reference-files)
  - [Pre-Work: Regression Baseline](#pre-work-regression-baseline)
  - [The Three-Mode CLI Design](#the-three-mode-cli-design)
  - [Script 1 (Group A): `backend/migrations/scripts/seed_core.py`](#script-1-group-a-backendmigrationsscriptsseed_corepy)
  - [Script 2 (Group C): `backend/migrations/scripts/seed_test_tenant.py`](#script-2-group-c-backendmigrationsscriptsseed_test_tenantpy)
  - [Script 3 (Group B): `backend/migrations/scripts/seed_platform.py`](#script-3-group-b-backendmigrationsscriptsseed_platformpy)
  - [Script 4 (Group D): `backend/migrations/scripts/seed_scenario_quote_to_cash.py`](#script-4-group-d-backendmigrationsscriptsseed_scenario_quote_to_cashpy)
  - [Script 5 (Group D): `backend/migrations/scripts/seed_scenario_dispatch.py`](#script-5-group-d-backendmigrationsscriptsseed_scenario_dispatchpy)
  - [Script 6 (Group D): `backend/migrations/scripts/reset_dev_db.py`](#script-6-group-d-backendmigrationsscriptsreset_dev_dbpy)
  - [Script Organization and Shared Utilities](#script-organization-and-shared-utilities)
  - [Post-Script Verification](#post-script-verification)
  - [Final Regression Check](#final-regression-check)
  - [Definition of Done](#definition-of-done)
  - [Important Constraints](#important-constraints)


---

## Context

Step 1 (Alembic data migrations) is complete. The dev DB now has all core reference/lookup data. Step 2 creates the Python seed scripts that handle the **dev/QA environment setup layer** — data that should NEVER go to production but is required to run UI tests and unit tests locally.

These scripts are **not migrations**. They are standalone Python scripts that:
- Connect to the database using SQLAlchemy (same ORM models as the application)
- Insert idempotent seed data (safe to run multiple times)
- Support a **three-mode CLI**: `--mode seed` (default), `--mode inspect`, `--mode show`
- Live in `backend/migrations/scripts/`

---

## Reference Files

Read these before writing any code:

- **Authoritative plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` — read §0.3 (full seed data spec per group), §0.5 (script design constraints + CLI interface + example output), and §0.6 (reset procedure)
- **Existing seed script**: `backend/migrations/seed_test_data.py` — the existing dev seed script; use this as the pattern for DB session setup, idempotent inserts, and console output style
- **DB models map**: `backend/db_models_map.md` — find the correct model file for every table
- **Model import paths**: `backend/app_model_imports.md` — use correct import paths
- **Settings/config**: `backend/core/config.py` — use `settings.TEST_TENANT_ID` and `settings.TEST_USER_ID` constants; never hardcode UUID strings
- **DB query guide**: `dev-docs/db-design/postgres-mcp-guide.md` — use postgres-local MCP for pre/post verification queries

---

## Pre-Work: Regression Baseline

Before writing any script files:

```bash
cd <repo>/backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

Record the pass/fail count. These scripts do not modify application code or models, but the baseline must be captured. We have been experiencing one flaky test that will sometimes fail and at other times pass, so if only 1 fails, keep going.

---

## The Three-Mode CLI Design

**Every script in this task must implement all three modes.** This is the standard interface that allows Tom to manage seed data without asking an agent to run database queries.

```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Seed script description here")
    parser.add_argument(
        "--mode",
        choices=["seed", "inspect", "show"],
        default="seed",
        help="seed: run the INSERT process | inspect: show current DB state | show: show what would be seeded",
    )
    # Add script-specific flags below (e.g., --tenant-id, --reset)
    return parser.parse_args()
```

**Mode behavior:**
- `seed` (default): runs all INSERTs with `ON CONFLICT DO NOTHING`; prints ✅ for each seeded/already-present record
- `inspect`: queries the DB for every table this script manages; prints current rows in a readable format; does NOT modify the DB
- `show`: prints the seed data definitions (hardcoded rows the script would insert); does NOT touch the DB at all; useful without a live DB

**Output format** (follow existing `seed_test_data.py` style with emoji indicators):
```
=== seed_test_tenant: inspect mode ===
[tenant]  1 row(s)
  00000000-0000-0000-0000-000000000001  "Pilot Dev Tenant"  is_active=True

[user]  3 row(s)
  00000000-0000-0000-0000-000000000002  dev@pilot.local  role=owner
  <uuid>  tech@pilot.local  role=technician
  <uuid>  office@pilot.local  role=office_staff
...
```

---

## Script 1 (Group A): `backend/migrations/scripts/seed_core.py`

**Purpose**: Re-inserts all Alembic-managed reference data. Used when restoring from a schema-only pg_dump (after `alembic stamp head`, which skips `upgrade()` functions). On a fresh `alembic upgrade head` this script is a no-op (all `ON CONFLICT DO NOTHING`).

**What it seeds** (all `tenant_id = NULL`, all `ON CONFLICT DO NOTHING`):
- `address_type` (4 rows)
- `contact_type` (4 rows)
- `taxability_code` (3 rows)
- `currency` (4 rows)
- `job_status` (5 rows)
- `quote_status` (9 rows — read existing data from DB before inserting to avoid collision)
- `invoice_status` (5 rows)
- `payment_status` (4 rows)
- `payment_type` (6 rows)
- `qco_line_type` (4 rows)
- `quote_link_status` (4 rows)
- `product_feature` (3 rows)
- `subscription_tier` (4 rows — trial/starter/professional/enterprise)
- `notification_channel` (4 rows)
- `notification_type` (3 rows)
- `platform_role` (3 rows)
- `subscription_status` (4 rows)
- `jwk_status` (3 rows)
- `sso_provider` (2 rows)
- `customer_lifecycle_status` (4 rows)
- `site_lifecycle_status` (3 rows)
- `supplier_lifecycle_status` (2 rows)
- `supplier_item_category` (electrical rows)
- `supplier_item_uom` (UOM rows)
- `job_expense_category` (3 rows)
- `qpl_contact_action_type` (4 rows)
- `tenant_user_status` (4 rows: active, invited, suspended, pending)
- `entity_type` (6 rows)
- `notification_category` (8 rows)
- `notification_default_policy` (24 rows)
- `app_service_category`, `app_service_provider`, `app_service` (QuickBooks chain)

> ⚠️ For large tables like `notification_default_policy` (24 rows) and `notification_category_sub_trigger` (7 rows): read the existing rows from the live DB first using `inspect` mode before embedding them as hardcoded seed values. These were seeded by existing migrations and are most reliably read from the DB using postgres-local MCP rather than re-derived from scratch.

> ⚠️ Do NOT seed: `platform_setting_catalog`, `platform_setting`, `customer_comm_template_type`, `email_template`, `communication_template`, `sync_conflict_classification_matrix`, `tenant_user_role` — these have complex data or existing migrations that are authoritative. The `seed_core.py` script covers only the simpler lookup tables.

**CLI interface:**
```bash
python migrations/scripts/seed_core.py               # seed mode (default)
python migrations/scripts/seed_core.py --mode inspect  # show DB state
python migrations/scripts/seed_core.py --mode show     # show what would be seeded
```

---

## Script 2 (Group C): `backend/migrations/scripts/seed_test_tenant.py`

**Purpose**: Creates the canonical dev/test tenant infrastructure and all tenant-level configuration required for both unit test `/test` endpoints and UI testing.

**What it seeds:**

**Test Tenant** (use `settings.TEST_TENANT_ID`):
- `tenant`: id=`settings.TEST_TENANT_ID`, name="Pilot Dev Tenant", `is_active=True`
- Set `current_subscription_tier_id` → trial tier (query `subscription_tier` for `is_trial=True`)

**Users** (3 total):
- Owner: id=`settings.TEST_USER_ID`, `email=settings.TEST_USER_EMAIL` (add this constant to config or use `"dev@pilot.local"` if not set), `first_name="Dev"`, `last_name="Owner"`, `is_active=True`
- Technician: deterministic UUID (not random — use a fixed UUID so re-runs don't create duplicates; suggest `00000000-0000-0000-0000-000000000003`), `email="tech@pilot.local"`, `first_name="Dev"`, `last_name="Technician"`, `display_color="#3B82F6"` (blue — used by dispatch board)
- Office staff: deterministic UUID (`00000000-0000-0000-0000-000000000004`), `email="office@pilot.local"`, `first_name="Dev"`, `last_name="Office"`

> ⚠️ Use `ON CONFLICT DO NOTHING` keyed on the UUID primary key. Check the `user` table column list before inserting — some fields may be nullable that aren't obvious.

**TenantUser rows** (3 rows, one per user):
- Owner → `role_code="owner"`, `status_id` = active status UUID (query `tenant_user_status` for `code="active"`)
- Technician → `role_code="technician"`, same active status
- Office staff → `role_code="office_staff"`, same active status

**UserEndpoint rows** (email endpoint for each user, for JWT mock to work):
- One `user_endpoint` row per user with `channel="email"`, `value=<user_email>`, `is_primary=True`

> ⚠️ The existing `seed_test_data.py` script already creates the owner user and tenant. Look at that file to understand the exact pattern used for `UserEndpoint`. The new script must be idempotent alongside the old script — if the owner already exists from the old seed, the new script should just `ON CONFLICT DO NOTHING`.

**Tenant Configuration:**
- `password_policy`: 1 row for test tenant — min 8 chars, requires uppercase + number, `password_expiry_days=None` (no expiry)
- `tenant_email_branding`: 1 row for test tenant — `company_name="Pilot Dev Tenant"`, placeholder colors
- `tenant_onboarding_checklist`: 1 row for test tenant in "completed" state (prevents onboarding wizard from dominating the UI)

> ⚠️ Before inserting `password_policy`, `tenant_email_branding`, `tenant_onboarding_checklist` — query their column lists using postgres-local MCP to verify column names and required fields:
> ```sql
> SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name IN ('password_policy', 'tenant_email_branding', 'tenant_onboarding_checklist') ORDER BY table_name, ordinal_position;
> ```

**Pricing Engine (requires tenant to exist first):**
- `subscription`: 1 row for test tenant → `status_code="trial"`, linked to trial `subscription_tier`, `is_active=True`
- `labor_rate_version`: 3 rows — master ($120.00/hr), journeyman ($85.00/hr), apprentice ($55.00/hr). All `tenant_id=settings.TEST_TENANT_ID`, `is_active=True`, `effective_date=today`
- `tenant_markup_version`: 1 row — `markup_pct=20.0`, `tenant_id=settings.TEST_TENANT_ID`, `is_active=True`, `effective_date=today`

> ⚠️ For `labor_rate_version` and `tenant_markup_version`: use postgres-local MCP to check the exact column names and types before inserting — these were added in frontend batch migrations and may have non-obvious column names:
> ```sql
> SELECT column_name, data_type FROM information_schema.columns WHERE table_name IN ('labor_rate_version', 'tenant_markup_version') ORDER BY table_name, ordinal_position;
> ```

**CLI interface:**
```bash
python migrations/scripts/seed_test_tenant.py                          # seed mode, defaults to `settings.TEST_TENANT_ID`
python migrations/scripts/seed_test_tenant.py --mode inspect           # show current state
python migrations/scripts/seed_test_tenant.py --mode show              # show what would be seeded
python migrations/scripts/seed_test_tenant.py --tenant-id <UUID>       # target a different tenant
python migrations/scripts/seed_test_tenant.py --reset                  # wipe Group C data only, then exit (no auto-reseed)
```

> ⚠️ **`--reset` on this script is destructive beyond Group C.** Because all Group D scenario data is FK-linked to the test tenant, a Group C wipe will cascade to customers, sites, jobs, quotes, invoices, and pricebook items. The script must print a prominent warning banner before executing any DELETE:
> ```
> ⚠️  WARNING: --reset will DELETE the test tenant and ALL tenant-scoped data.
>     This includes Group D scenario data (customers, sites, jobs, quotes, invoices).
>     Group A (lookup tables) and Group B (platform config) are NOT affected.
>     Press Ctrl+C to abort. Proceeding in 3 seconds...
> ```
> After the wipe, the script exits cleanly. Run `python migrations/scripts/seed_test_tenant.py` (no flags) to re-seed.

---

## Script 3 (Group B): `backend/migrations/scripts/seed_platform.py`

**Purpose**: Seeds the platform-level entitlement configuration. Not required for unit tests (entitlements are mocked), but required for UI testing where the real entitlement system runs.

**What it seeds:**

**Product Plan Hierarchy** (3 plans — one per paid tier):

The relationship chain is: `product_plan` → `product_plan_version` → `product_plan_product_feature_version`

Before writing this, query the exact column structure:
```sql
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name IN ('product_plan', 'product_plan_version', 'product_plan_product_feature_version', 'product_feature')
ORDER BY table_name, ordinal_position;
```

Also check what the existing `product_feature` rows look like:
```sql
SELECT * FROM public.product_feature;
```

Create:
- 3 `product_plan` rows: `starter_plan`, `professional_plan`, `enterprise_plan`
- 3 `product_plan_version` rows (1 active version per plan, `effective_from=today`)
- Junction rows in `product_plan_product_feature_version` — maps all 3 `product_feature` codes to each plan version with appropriate `limit_quantity` values per tier

Also update the `subscription_tier` rows to set `product_plan_code` FK:
```sql
-- Example (values are illustrative — derive from the actual tier names)
UPDATE subscription_tier SET product_plan_code = 'starter_plan' WHERE tier_name = 'starter';
UPDATE subscription_tier SET product_plan_code = 'professional_plan' WHERE tier_name = 'professional';
UPDATE subscription_tier SET product_plan_code = 'enterprise_plan' WHERE tier_name = 'enterprise';
```

**Notification Templates** (minimum 1 per notification_category):

Before writing, query what exists:
```sql
SELECT nc.category_id, nc.display_label, nt.template_id 
FROM public.notification_category nc
LEFT JOIN public.notification_template nt ON nt.category_id = nc.category_id
ORDER BY nc.display_order;
```

For each category that has no template, insert a placeholder row. Query the `notification_template` column structure first:
```sql
SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'notification_template' ORDER BY ordinal_position;
```

**CLI interface:**
```bash
python migrations/scripts/seed_platform.py                 # seed mode
python migrations/scripts/seed_platform.py --mode inspect  # show current platform config
python migrations/scripts/seed_platform.py --mode show     # show what would be seeded
```

---

## Script 4 (Group D): `backend/migrations/scripts/seed_scenario_quote_to_cash.py`

**Purpose**: Seeds realistic scenario data for the full quote-to-cash UI test flow. This is Group D (ephemeral scenario data) — it is wiped by `reset_dev_db.py`.

**What it seeds** (all scoped to `settings.TEST_TENANT_ID`):

Before inserting any records, verify the lifecycle status UUIDs by querying:
```sql
SELECT id, code FROM public.customer_lifecycle_status WHERE tenant_id IS NULL;
SELECT id, code FROM public.site_lifecycle_status WHERE tenant_id IS NULL;
```

**Customers (5 records)**:
- `John Smith` — type=person, lifecycle=active, residential, `mobile_phone="+12125551001"`, `email="john.smith@example.com"`
- `Mary Johnson` — type=person, lifecycle=active, residential, `mobile_phone="+12125551002"`, `email="mary.j@example.com"`
- `Apex Commercial LLC` — type=company, `company_name="Apex Commercial LLC"`, lifecycle=active, commercial
- `Bob Davis` — type=person, lifecycle=prospect (no jobs, no sites yet)
- `Inactive Customer` — type=person, lifecycle=dormant

**Sites** (one per active customer, not for prospect/inactive):
Each site must have a real US address (use these exact values for Google Maps API compatibility):
- Smith site: `line1="123 Main St"`, `city="Brooklyn"`, `state="NY"`, `postal_code="11201"`, country="US"
- Johnson site: `line1="456 Oak Ave"`, `city="Austin"`, `state="TX"`, `postal_code="78701"`, country="US"
- Apex site: `line1="789 Commerce Blvd"`, `city="Chicago"`, `state="IL"`, `postal_code="60601"`, country="US"

> ⚠️ Use `entity_address` table (polymorphic address junction) to link addresses to customers/sites. Query the column structure: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'entity_address' ORDER BY ordinal_position;`

**Pricebook Items** (5 items with versions):
Each `pricebook_item` must have an active `pricebook_item_version`. Query column structure first:
```sql
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name IN ('pricebook_item', 'pricebook_item_version')
ORDER BY table_name, ordinal_position;
```

Items:
1. `Standard Outlet Installation` — labor, $150 unit_price, $60 cost, taxable
2. `200A Panel Upgrade` — labor, $1800 unit_price, $600 cost, taxable
3. `15A Circuit Breaker` — material, $18 unit_price, $8 cost, taxable
4. `EMT Conduit` — material, $3.50/ft unit_price, $1.20 cost, taxable
5. `Residential Permit Fee` — fee, $250 unit_price, $250 cost, exempt (use `taxability_code` values from live DB)

**Quote (1 record in draft status)**:
- Customer: John Smith, Site: Smith site
- Status: draft (query `quote_status` for `code="draft"`)
- Include 2–3 line items using pricebook items above

> ⚠️ Query `quote_status` UUID: `SELECT id, code FROM public.quote_status WHERE tenant_id IS NULL AND code = 'draft';`

**CLI interface:**
```bash
python migrations/scripts/seed_scenario_quote_to_cash.py                # seed, defaults to `settings.TEST_TENANT_ID`
python migrations/scripts/seed_scenario_quote_to_cash.py --mode inspect # show current state
python migrations/scripts/seed_scenario_quote_to_cash.py --mode show    # show definitions
python migrations/scripts/seed_scenario_quote_to_cash.py --reset        # wipe this scenario's data only, then exit
```

The `--reset` flag must DELETE only the records created by this script in child-first order, then **exit cleanly** — it does NOT auto-reseed. Use the ordered DELETE sequence from the plan (job_tech_assignment → job → site → contact → customer → quote lines → quotes → pricebook_item_version → pricebook_item). After the wipe, the script prints:
```
✅ Quote-to-Cash scenario data wiped.
   Run: python migrations/scripts/seed_scenario_quote_to_cash.py
   to re-seed.
```

---

## Script 5 (Group D): `backend/migrations/scripts/seed_scenario_dispatch.py`

**Purpose**: Seeds jobs with scheduling data and tech assignments for dispatch board testing. Depends on `seed_test_tenant.py` having run first (needs the technician user).

**What it seeds** (all `tenant_id=settings.TEST_TENANT_ID`):

Requires existing customers and sites from `seed_scenario_quote_to_cash.py`. If they don't exist, create 2 minimal customers with sites first.

**Jobs (5 records)**:
1. `Scheduled - Outlet Installation` — `status=scheduled`, scheduled for tomorrow 9am–1pm, assigned to tech user (`role=primary`)
2. `In Progress - Panel Upgrade` — `status=in_progress`, started today, assigned to tech user
3. `Completed - Circuit Job` — `status=completed`, completed yesterday, assigned to tech user
4. `Completed - Awaiting Invoice` — `status=completed`, completed 3 days ago, no invoice yet
5. `Draft - Estimate Only` — `status=draft`, no scheduling, no assignment

> ⚠️ Query job_status UUID values: `SELECT id, code FROM public.job_status WHERE tenant_id IS NULL;`
> ⚠️ Use the technician user UUID (`00000000-0000-0000-0000-000000000003`) for assignments — this user must exist from `seed_test_tenant.py`

**Job Assignments** (for jobs 1–3):
- Use `job_tech_assignment` table — `user_id=technician_uuid`, `role="primary"`, `ordinal=1`, `is_active=True`

**Tech Availability Block** (1 record):
- Technician has a PTO block next Friday 8am–5pm (for conflict detection testing)
- Use `tech_availability` table — `user_id=technician_uuid`, `availability_type="pto"`, `starts_at=<next_friday_8am>`, `ends_at=<next_friday_5pm>`

**CLI interface:**
```bash
python migrations/scripts/seed_scenario_dispatch.py                # seed, defaults to `settings.TEST_TENANT_ID`
python migrations/scripts/seed_scenario_dispatch.py --mode inspect # show current state
python migrations/scripts/seed_scenario_dispatch.py --mode show    # show definitions
python migrations/scripts/seed_scenario_dispatch.py --reset        # wipe this scenario's data only, then exit
```

The `--reset` flag deletes only records created by this script (job_tech_assignment → tech_availability → job) scoped to `settings.TEST_TENANT_ID`, then **exits cleanly** — no auto-reseed. After the wipe, the script prints:
```
✅ Dispatch scenario data wiped.
   Run: python migrations/scripts/seed_scenario_dispatch.py
   to re-seed.
```

---

## Script 6 (Group D): `backend/migrations/scripts/reset_dev_db.py`

**Purpose**: Central Group D control panel. Wipes Group D (scenario) data and offers interactive or CLI-driven re-seed selection. Does NOT touch Group A/B/C data (lookup tables, platform config, test tenant infrastructure).

### Scenario Registry

At the top of the script, define a `SCENARIOS` dict so new scenarios are added in one place with no structural changes required:

```python
# ── SCENARIO REGISTRY ──────────────────────────────────────────────────────
# Add new Group D scenarios here. Each entry maps a short key to the seed
# script module path. The interactive menu and --scenarios flag both use this.
SCENARIOS = {
    "quote_to_cash": "migrations.scripts.seed_scenario_quote_to_cash",
    "dispatch":      "migrations.scripts.seed_scenario_dispatch",
}
# ───────────────────────────────────────────────────────────────────────────
```

### Interactive Menu (no-arg invocation)

When run with no arguments (or with `--interactive`), the script launches a numbered menu using stdlib `input()` — no third-party deps:

```
=== Pilot Dev DB Reset Manager ===
Group A/B/C data (lookup tables, platform config, test tenant) is NEVER touched.

What would you like to do?
  1. Wipe ALL Group D data (all scenarios)
  2. Wipe individual scenario(s)
  3. Inspect current Group D state (row counts)
  4. Exit

Choice: _
```

If option **2** is selected, a sub-menu lists each registered scenario individually with a multi-select interface:

```
Select scenarios to wipe (comma-separated numbers, or 'a' for all):
  1. quote_to_cash
  2. dispatch

Choice: _
```

After any wipe operation completes, the script asks:

```
✅ Wipe complete. Re-seed now? (y/N): _
```

- `y` → runs the seed function of each wiped scenario script (imported via `SCENARIOS` registry) immediately
- `N` / Enter → exits cleanly with a reminder of the manual re-seed command(s)

### Non-Interactive CLI Flags

Non-interactive flags still work for scripted/CI use:

```bash
python migrations/scripts/reset_dev_db.py                              # launches interactive menu
python migrations/scripts/reset_dev_db.py --wipe-only                  # wipe ALL Group D, exit (no prompt)
python migrations/scripts/reset_dev_db.py --scenarios quote_to_cash    # wipe one scenario, then prompt to re-seed
python migrations/scripts/reset_dev_db.py --scenarios quote_to_cash,dispatch  # wipe both, then prompt to re-seed
python migrations/scripts/reset_dev_db.py --mode inspect               # show current Group D row counts, no changes
```

### Wipe Sequence

The full ordered DELETE sequence below covers all Group D tables. Must be executed in this order — all FKs are RESTRICT, not CASCADE:

```python
# Ordered DELETE — child tables first, all filtered to TEST_TENANT_ID
tables_to_clear = [
    "loto_confirmation",
    "calendar_sync_conflict",
    "job_tech_assignment",
    "job_time_entry",
    "job_expense",
    "job_notes",
    "job_attachment",
    "change_order_line",
    "change_order",
    "tech_availability",
    "quote_line",
    "quote_version",
    "quote",
    "invoice_line",
    "invoice",
    "job",
    "pricebook_item_version",
    "pricebook_item",
    "entity_address",
    "entity_contact",
    "contact",
    "site",
    "customer",
]
# Filter to test tenant only — do NOT wipe system-level rows
for table in tables_to_clear:
    if table has tenant_id column:
        db.execute(f"DELETE FROM {table} WHERE tenant_id = :tenant_id", {"tenant_id": TEST_TENANT_ID})
    else:
        # Tables without tenant_id (e.g., entity_address linked via entity_id):
        # delete via FK-safe subquery scoped to test tenant records
        pass
```

> ⚠️ Before writing the DELETE statements, query which of these tables have a `tenant_id` column:
> ```sql
> SELECT table_name FROM information_schema.columns
> WHERE table_schema = 'public' AND column_name = 'tenant_id'
> AND table_name IN ('loto_confirmation','job_tech_assignment','job_time_entry','job_expense','job_notes','job_attachment','change_order_line','change_order','tech_availability','quote_line','quote_version','quote','invoice_line','invoice','job','pricebook_item_version','pricebook_item','entity_address','entity_contact','contact','site','customer')
> ORDER BY table_name;
> ```

### `--mode inspect` Output

```
=== reset_dev_db: Current Group D State ===
[customer]         0 row(s)
[site]             0 row(s)
[job]              0 row(s)
[quote]            0 row(s)
[invoice]          0 row(s)
[pricebook_item]   0 row(s)
...
```

---

## Script Organization and Shared Utilities

### Shared DB Session Utility

Create a shared utility module `backend/migrations/scripts/_db_utils.py` to avoid duplicating the DB session setup across all scripts:

```python
# backend/migrations/scripts/_db_utils.py

from sqlmodel import Session, create_engine
from backend.core.config import settings

def get_db_session() -> Session:
    """Return a session connected to the dev database."""
    engine = create_engine(settings.DATABASE_URL)
    return Session(engine)
```

Each script imports this utility. No duplication of connection string logic.

### Seed Data Configuration Pattern

Scripts 2–5 must define all configurable seed values in a clearly demarcated `CONFIG` block at the **top of the file**, immediately after imports. Script 1 (`seed_core.py`) is exempt — its data comes exclusively from Alembic migration values and must not diverge.

The CONFIG block pattern:

```python
# ── SEED DATA CONFIG ────────────────────────────────────────────────────────
# Edit the values below to change what gets seeded. These are the only values
# you need to touch — the SQL/ORM logic below uses these variables throughout.

# Script 2 example (seed_test_tenant.py):
TENANT_NAME          = "Pilot Dev Tenant"
TECH_EMAIL           = "tech@pilot.local"
TECH_FIRST_NAME      = "Dev"
TECH_LAST_NAME       = "Technician"
TECH_DISPLAY_COLOR   = "#3B82F6"   # blue — used by dispatch board calendar
OFFICE_EMAIL         = "office@pilot.local"
OFFICE_FIRST_NAME    = "Dev"
OFFICE_LAST_NAME     = "Office"
LABOR_RATE_MASTER    = 120.00      # $/hr
LABOR_RATE_JOURNEYMAN = 85.00
LABOR_RATE_APPRENTICE = 55.00
MARKUP_PCT           = 20.0

# Script 4 example (seed_scenario_quote_to_cash.py):
CUSTOMERS = [
    {"first_name": "John",  "last_name": "Smith",    "type": "person",  "lifecycle": "active",   "phone": "+12125551001", "email": "john.smith@example.com"},
    {"first_name": "Mary",  "last_name": "Johnson",  "type": "person",  "lifecycle": "active",   "phone": "+12125551002", "email": "mary.j@example.com"},
    {"company_name": "Apex Commercial LLC",           "type": "company", "lifecycle": "active"},
    {"first_name": "Bob",   "last_name": "Davis",    "type": "person",  "lifecycle": "prospect"},
    {"first_name": "Inactive", "last_name": "Customer", "type": "person", "lifecycle": "dormant"},
]
PRICEBOOK_ITEMS = [
    {"name": "Standard Outlet Installation", "category": "labor",    "unit_price": 150.00,  "cost": 60.00,  "taxable": True},
    {"name": "200A Panel Upgrade",            "category": "labor",    "unit_price": 1800.00, "cost": 600.00, "taxable": True},
    {"name": "15A Circuit Breaker",           "category": "material", "unit_price": 18.00,   "cost": 8.00,   "taxable": True},
    {"name": "EMT Conduit",                   "category": "material", "unit_price": 3.50,    "cost": 1.20,   "taxable": True},
    {"name": "Residential Permit Fee",        "category": "fee",      "unit_price": 250.00,  "cost": 250.00, "taxable": False},
]
# ────────────────────────────────────────────────────────────────────────────
```

> The SQL and ORM insert logic below the CONFIG block must reference these variables exclusively — no inline literal values for names, prices, emails, or colors. This ensures you can update all seed data by editing only the CONFIG section at the top.

---

## Post-Script Verification

After all 6 scripts are written and pass a `--mode show` dry run, execute the following to verify everything works end-to-end:

```bash
cd <repo>/backend
source .venv/bin/activate

# Step 1: Verify lookup data (should all be non-zero from Step 1 migrations)
python migrations/scripts/seed_core.py --mode inspect

# Step 2: Seed test tenant
python migrations/scripts/seed_test_tenant.py
python migrations/scripts/seed_test_tenant.py --mode inspect  # verify

# Step 3: Seed platform config
python migrations/scripts/seed_platform.py
python migrations/scripts/seed_platform.py --mode inspect  # verify

# Step 4: Seed scenario data
python migrations/scripts/seed_scenario_quote_to_cash.py
python migrations/scripts/seed_scenario_dispatch.py
python migrations/scripts/reset_dev_db.py --mode inspect  # verify counts

# Step 5: Verify reset works
python migrations/scripts/reset_dev_db.py --wipe-only
python migrations/scripts/reset_dev_db.py --mode inspect  # all Group D should be 0
python migrations/scripts/reset_dev_db.py --scenarios quote_to_cash,dispatch  # re-seed
python migrations/scripts/reset_dev_db.py --mode inspect  # counts should be back
```

All steps must complete without errors. Report results to Tom after each step.

---

## Final Regression Check

```bash
cd <repo>/backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

Pass count must match the baseline. These scripts are standalone utilities that don't modify application code, models, or routes — if any test failures appear, investigate before marking complete.

---

## Definition of Done

- [ ] `seed_core.py` — all 3 modes working; seeds cleanly on empty DB; no-ops on populated DB
- [ ] `seed_test_tenant.py` — all 3 modes + `--reset` (wipe-only with warning banner); tenant, 3 users, pricing engine all present after seed
- [ ] `seed_platform.py` — all 3 modes; product_plan hierarchy and notification_templates present
- [ ] `seed_scenario_quote_to_cash.py` — all 3 modes + `--reset` (wipe-only, exits with re-seed reminder); 5 customers, sites, 5 pricebook items, 1 draft quote
- [ ] `seed_scenario_dispatch.py` — all 3 modes + `--reset` (wipe-only, exits with re-seed reminder); 5 jobs with assignments, tech availability block
- [ ] `reset_dev_db.py` — interactive menu (no-arg), `--wipe-only`, `--scenarios`, `--mode inspect` all working; post-wipe re-seed prompt functional; `SCENARIOS` registry drives both menu and CLI
- [ ] `_db_utils.py` shared utility created
- [ ] All Scripts 2–5 have a top-of-file `# ── SEED DATA CONFIG ──` block; all insert logic references CONFIG variables (no inline literals)
- [ ] End-to-end verification sequence above passes cleanly
- [ ] Full unit test regression passes with zero new failures
- [ ] **Ask Tom to confirm** — show him the `inspect` output from `seed_test_tenant.py` and `reset_dev_db.py` before marking complete

---

## Important Constraints

- **These scripts are NEVER run in production** — they create dev/test data only
- **No Alembic migrations** — these are standalone Python scripts, not migrations
- **No ORM model changes** — use existing models as-is
- **Always use `settings.TEST_TENANT_ID` and `settings.TEST_USER_ID`** — never hardcode UUID strings for the canonical test tenant/user
- **Use deterministic UUIDs** for the new technician and office_staff users (not `uuid4()`) so scripts are fully idempotent across multiple runs
- **Use `ON CONFLICT DO NOTHING`** via SQLAlchemy's merge or explicit conflict handling — never TRUNCATE inside seed scripts
- **Ordered DELETE** in `reset_dev_db.py` — the FK audit confirmed all constraints are RESTRICT; TRUNCATE CASCADE will not work
- **Query column structure before inserting** into any table you haven't worked with before — use postgres-local MCP
