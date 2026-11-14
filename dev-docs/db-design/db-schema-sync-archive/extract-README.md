# 📋 Column Defaults Extraction Tools

This document covers the **column defaults extraction** toolset — a script and its two output files that identify every business-logic column default defined in the JSON blueprint and cross-check them against what is actually set in the physical PostgreSQL database.

These files are used together to generate the exact set of `ALTER TABLE … ALTER COLUMN … SET DEFAULT` migration statements needed to close the gap between the design specification and the live database.

> **Source of truth:** [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) (design-time defaults) and the live PostgreSQL `information_schema.columns` (physical defaults)

---

## 🗂️ Extract Group — Column Defaults Audit

### [`extract_defaults.py`](extract_defaults.py)

**Purpose:** Scans [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) and prints a markdown table of every column that has a `"default"` value defined in the blueprint — representing all business-logic defaults the physical database must enforce.

**How it works:**
- Opens and parses [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) via [`extract_schema_defaults()`](extract_defaults.py)
- Iterates the top-level `tables` dictionary
- For each table's `columns` map, checks whether each column definition includes a `"default"` key
- Intentionally **skips `created_at` and `updated_at`** — these are standard infrastructure timestamps handled by triggers, not business logic
- Prints a formatted markdown table with three columns: `Table Name`, `Column Name`, `Expected Default`
- Reports a total count at the end

**Why it exists:**
The JSON blueprint can declare hundreds of column defaults across 80+ tables (e.g. `is_active → true`, `currency → 'USD'`, `quantity → 1`, `status → 'pending'`, `billing_interval → 'monthly'`). Without this script, there is no reliable way to enumerate all 200 expected defaults programmatically — they would have to be hunted manually across the 800 KB JSON file. This script produces the authoritative checklist for database migration work.

> **🛑 Safe to run — read-only, prints to stdout only**

**Usage:**
```bash
# Run from the dev-docs/db-design/ directory
# Output is printed to stdout — redirect to capture it
python extract_defaults.py

# Capture to a file:
python extract_defaults.py > extract-required-defaults-columns-json.md
```

---

### [`extract-required-defaults-columns-json.md`](extract-required-defaults-columns-json.md)

**Purpose:** The captured stdout output of [`extract_defaults.py`](extract_defaults.py) — the complete markdown table of all **200 business-logic column defaults** declared in the JSON blueprint.

**What it contains:**
A markdown table listing every column that requires a physical `DEFAULT` constraint, organized by table across all domains:

| Domain | Representative Defaults |
|---|---|
| **Identity / Auth** | `user.is_active → true`, `user.failed_login_count → 0`, `user_endpoint.verification_status → 'pending'` |
| **Tenancy** | `tenant.is_active → true`, `tenant_settings.default_quote_validity_days → 30` |
| **Sales / Quoting** | `quote.subtotal_cents → 0`, `quote.currency → 'USD'`, `quote_line.quantity → 1` |
| **Field Operations** | `job.is_active → true`, `job_assignment.is_lead → false`, `job_expense.is_billable → true` |
| **Invoicing** | `invoice.balance_due_cents → 0`, `invoice.currency → 'USD'`, `invoice_line.quantity → 1` |
| **Subscriptions** | `subscription.quantity_seats → 1`, `subscription.billing_interval → 'monthly'`, `subscription.cancel_at_period_end → false` |
| **Notifications** | `notification_outbox.status → 'pending'`, `notification_outbox.attempt_count → 0`, `notification_outbox.priority → 5` |
| **Integrations** | `integration_credential.connection_status → 'pending'`, `integration_sync_mapping.sync_preference → 'aevofab_master'` |
| **Voice AI** | `conversation_session.status → 'active'`, `voice_command_log.is_successful → true` |

**Total: 200 business-logic fields requiring physical DB defaults**

**How it is used:**
- Compared against [`extract-required-defaults-columns-db.json`](extract-required-defaults-columns-db.json) to identify which defaults are missing from the physical database
- The delta between the two files drives the `ALTER TABLE … ALTER COLUMN … SET DEFAULT` migration statements in schema sync phases
- Provides a human-readable audit trail confirming the scope of defaults work

---

### [`extract-required-defaults-columns-db.json`](extract-required-defaults-columns-db.json)

**Purpose:** The output of a live PostgreSQL query against `information_schema.columns` — a list of every column in the physical database that is **missing a `column_default`** value for columns that the JSON blueprint says should have one.

**What it contains:**
A flat JSON array where each entry represents a column missing its physical default:
```json
[
  {
    "table_schema": "audit",
    "table_name": "event",
    "column_name": "action",
    "data_type": "character varying"
  },
  {
    "table_schema": "public",
    "table_name": "address",
    "column_name": "is_active",
    "data_type": "boolean"
  }
]
```

**How it was generated:**
This file is populated by running a SQL query directly against the live database — typically something like:
```sql
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE column_default IS NULL
  AND table_schema IN ('public', 'audit')
  AND is_nullable = 'NO'
ORDER BY table_schema, table_name, column_name;
```
The results are exported to JSON (e.g. via `psql` or a database client) and saved to this file.

**How it is used:**
- Cross-referenced against [`extract-required-defaults-columns-json.md`](extract-required-defaults-columns-json.md) to identify the exact gap: columns the JSON says need defaults but the physical database does not have set
- The intersection of "in JSON md table" AND "in this db JSON" = the actionable migration list
- Drives `ALTER TABLE` migration batches during schema sync phases

---

## 🔗 How the Two Outputs Work Together

```
pilot-db-schema-v2.6h.json
        │
        └──► extract_defaults.py ──► extract-required-defaults-columns-json.md
                                      (200 expected defaults from blueprint)
                                              │
                                              │  CROSS-CHECK
                                              │
live PostgreSQL database ──────────────────► extract-required-defaults-columns-db.json
(information_schema query)                    (columns missing defaults in physical DB)
                                              │
                                              ▼
                                     DELTA = migration target
                                     (ALTER TABLE … SET DEFAULT statements)
```

**The workflow:**
1. Run [`extract_defaults.py`](extract_defaults.py) → produces the **expected** list
2. Query the live database → produces the **actual** list (`extract-required-defaults-columns-db.json`)
3. Compare → identify which columns need `ALTER TABLE … ALTER COLUMN … SET DEFAULT …` migrations
4. Write and apply the migration SQL
5. Re-run both to verify the gap is closed

---

## ⚙️ Prerequisites

- **Python 3.6+** — no third-party packages required; [`extract_defaults.py`](extract_defaults.py) uses only the standard library (`json`, `sys`, `pathlib`)
- [`extract_defaults.py`](extract_defaults.py) must be run from the [`dev-docs/db-design/`](.) directory
- [`extract-required-defaults-columns-db.json`](extract-required-defaults-columns-db.json) is produced by a direct PostgreSQL query — requires live database access
