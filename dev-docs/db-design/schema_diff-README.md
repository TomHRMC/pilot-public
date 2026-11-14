# 🗄️ Pilot for Trades DB Design — Tool Ecosystem Overview

This folder contains the complete **database schema design, audit, synchronization, and diff toolset** for Pilot for Trades. All scripts operate on two master source files and are designed to keep the JSON blueprint and the physical PostgreSQL database in perfect agreement.

Because both source files are large (800 KB+) and structurally different (JSON vs. SQL DDL), all tooling uses programmatic parsing and set-theory comparison rather than visual diffing — guaranteeing no objects are skipped.

---

## 📁 Master Source Files

| File | Role |
|---|---|
| [`pilot-db-schema-v2.6h.json`](pilot-db-schema-v2.6h.json) | **Design-time blueprint** — the authoritative specification of what the database *should* look like. Contains tables, columns, indexes, FKs, triggers, functions, and design decisions in structured JSON. |
| `pilot-db-schema-dump-master.sql` _(private)_ | **Physical database state** — a `pg_dump --schema-only` export of the live PostgreSQL database. Represents what the database *actually* looks like in DDL. |

---

## 📚 Tool Groups & Their README Files

The toolset is organized into five functional groups, each with its own README:

### 1. 🔍 Inspection / Reconnaissance → [`inspect-README.md`](db-schema-sync-archive/inspect-README.md)

Lightweight probes that map the structural shape of both source files before running any diff or sync. Used to give an AI agent the context needed to reason about 800 KB+ files.

| File | Type | Description |
|---|---|---|
| [`inspect_json.py`](db-schema-sync-archive/inspect_json.py) | Script | Recursively maps the JSON blueprint's key hierarchy to a type-skeleton (up to 4 levels deep) |
| [`inspect_json_output.json`](db-schema-sync-archive/inspect_json_output.json) | Output | Structural blueprint of the JSON file — fed to AI agents for context |
| [`inspect_sql.py`](db-schema-sync-archive/inspect_sql.py) | Script | Extracts one sample `CREATE TABLE` and one `ALTER TABLE` from the SQL dump to surface its DDL dialect |
| [`inspect_sql_output.sql`](db-schema-sync-archive/inspect_sql_output.sql) | Output | Sample DDL from the physical dump — fed to AI agents to establish parsing conventions |

---

### 2. 🛡️ Schema Audits → [`audit-README.md`](db-schema-sync-archive/audit-README.md)

Read-only scripts that interrogate the JSON blueprint to surface structural risks, security gaps, and performance hazards.

| File | Type | Description |
|---|---|---|
| [`audit_tenant_ids.py`](db-schema-sync-archive/audit_tenant_ids.py) | Script | Identifies which tables have `tenant_id` and which don't — multi-tenancy isolation check |
| [`audit_tenant_ids.json`](db-schema-sync-archive/audit_tenant_ids.json) | Output | 67 tenant-scoped tables vs. 51 tables potentially lacking isolation |
| [`audit_fk_indexes.py`](db-schema-sync-archive/audit_fk_indexes.py) | Script | Stage 1: scans all 447 FKs for missing backing indexes |
| [`audit_fk_missing_indexes.json`](db-schema-sync-archive/audit_fk_missing_indexes.json) | Output | Raw result: 304 unindexed FKs (includes audit-column noise) |
| [`audit_fk_missing_indexes_filter.py`](db-schema-sync-archive/audit_fk_missing_indexes_filter.py) | Script | Stage 2: strips `created_by`/`updated_by` FKs, surfaces actionable structural gaps |
| [`audit_fk_missing_indexes_filter_output.json`](db-schema-sync-archive/audit_fk_missing_indexes_filter_output.json) | Output | Filtered result: **112 critical structural indexes** missing across 65 tables |
| [`audit_deletion_pathways.py`](db-schema-sync-archive/audit_deletion_pathways.py) | Script | Categorizes all FK `ON DELETE` rules; flags risky CASCADE on financial/audit tables |
| [`audit_deletion_pathways.json`](db-schema-sync-archive/audit_deletion_pathways.json) | Output | Full breakdown + **16 critical risky cascades** on invoice/quote/payment tables |

---

### 3. 🔄 Schema Sync → [`sync-README.md`](db-schema-sync-archive/sync-README.md)

Scripts that extract PostgreSQL functions and triggers from the physical SQL dump and synchronize them back into the JSON blueprint. Includes both dry-run inspection and write-back modes.

| File | Type | Description |
|---|---|---|
| [`sync_functions_to_json.py`](db-schema-sync-archive/sync_functions_to_json.py) | Script (dry run) | Extracts functions from both sources; saves snapshots; does NOT modify master JSON |
| [`sync_design_functions_backup.json`](db-schema-sync-archive/sync_design_functions_backup.json) | Output | Snapshot of functions as currently defined in the JSON blueprint |
| [`sync_physical_db_functions_export.json`](db-schema-sync-archive/sync_physical_db_functions_export.json) | Output | Snapshot of all functions extracted from the physical SQL dump |
| [`sync_soft_delete_functions.py`](db-schema-sync-archive/sync_soft_delete_functions.py) | Script (write-back) | Targeted sync: adds missing `cascade_soft_delete_to_*` functions into JSON |
| [`sync_merge_functions_to_master.py`](db-schema-sync-archive/sync_merge_functions_to_master.py) | Script (write-back) | Smart merge: preserves JSON metadata, replaces definitions with physical DDL |
| [`sync_triggers_to_json.py`](db-schema-sync-archive/sync_triggers_to_json.py) | Script (write-back) | Full overwrite: injects all physical triggers into JSON; auto-backs up first |
| [`sync_design_triggers_backup.json`](db-schema-sync-archive/sync_design_triggers_backup.json) | Output | Pre-sync backup of JSON blueprint trigger definitions |
| [`sync_physical_db_triggers_export.json`](db-schema-sync-archive/sync_physical_db_triggers_export.json) | Output | Ground-truth `CREATE TRIGGER` DDL for all tables from `pg_dump` |

---

### 4. 📋 Column Defaults Extraction → [`extract-README.md`](db-schema-sync-archive/extract-README.md)

Tools that identify every business-logic column default defined in the JSON blueprint and cross-check them against the physical database to drive `ALTER TABLE … SET DEFAULT` migrations.

| File | Type | Description |
|---|---|---|
| [`extract_defaults.py`](db-schema-sync-archive/extract_defaults.py) | Script | Scans JSON blueprint; prints markdown table of all columns with a `"default"` value |
| [`extract-required-defaults-columns-json.md`](db-schema-sync-archive/extract-required-defaults-columns-json.md) | Output | **200 business-logic defaults** expected by the JSON blueprint |
| [`extract-required-defaults-columns-db.json`](db-schema-sync-archive/extract-required-defaults-columns-db.json) | Output | Columns missing `column_default` in the live database (`information_schema` query result) |

---

### 5. 📊 Schema Diff (Core) → this file

The primary diff engine that compares the JSON blueprint against the physical SQL dump across all object types and generates a detailed HTML report.

| File | Type | Description |
|---|---|---|
| [`schema_diff.py`](schema_diff.py) | Script | Core diff engine — parses both sources into normalized Python dictionaries and compares them |
| `schema_diff_report.html` _(private)_ | Output | Interactive HTML dashboard showing all discrepancies grouped by environment or table |

---

## ⚙️ How `schema_diff.py` Works

The diff engine normalizes both files into Python dictionaries via set-theory comparison — guaranteeing mathematical precision with no objects skipped.

### JSON Parsing (`parse_json_schema()`)
- Traverses the `tables` root key (public schema) and any nested `schemas` (e.g., `audit`)
- Extracts per-table: `columns`, `primary_key`, `unique`, `indexes`, `foreign_keys`, `triggers`
- Extracts global `functions` with name normalization (handles `schema.name` vs. bare `name`)
- Normalizes index definitions via `normalize_index_def()` — strips `CREATE INDEX name ON table` prefix, `USING btree`, `ASC`, `NULLS LAST`, and whitespace for clean structural comparison

### SQL Parsing (`parse_sql_schema()`)
- Extracts `CREATE [OR REPLACE] FUNCTION` blocks **before** comment stripping (to preserve `$$` bodies)
- Splits on `;` for remaining statements; strips `--` comments
- Parses `CREATE TABLE` blocks for columns, inline PKs, unique constraints, and FKs
- Parses `ALTER TABLE … ADD CONSTRAINT` for additional PKs, unique constraints, and FKs
- Parses `CREATE INDEX` statements and maps them to their parent tables
- Parses `CREATE TRIGGER` statements and maps them to their parent tables
- Excludes `alembic_version` from comparison

### Comparison (Set Theory)
- **Missing in SQL** = JSON set − SQL set (requires database migration)
- **Missing in JSON** = SQL set − JSON set (requires JSON blueprint update)
- Applied independently to: tables, columns, PKs, unique constraints, FKs, indexes, triggers, functions

### Report Generation (`generate_html_report()`)
- **`--group-by environment`** (default): Two sections — "Missing in SQL" and "Missing in JSON" — each showing full object details
- **`--group-by table`**: One section per table showing both directions of discrepancy side-by-side
- Includes a top-level **Analysis Summary** table comparing object counts between JSON and SQL across all 8 categories

---

## 🚀 Running the Full Diff

```bash
# Run from the dev-docs/db-design/ directory

# Group by environment (recommended for migration planning)
python schema_diff.py --group-by environment

# Group by table (recommended for per-table review)
python schema_diff.py --group-by table
```

Open the generated `schema_diff_report.html` _(private)_ in a browser to review results.

---

## 🔗 Full Toolchain Execution Order

When performing a complete schema sync cycle, run tools in this order:

```bash
# ── STEP 1: INSPECT ──────────────────────────────────────────
python inspect_json.py          # Map JSON structure
python inspect_sql.py           # Probe SQL DDL format

# ── STEP 2: AUDIT ────────────────────────────────────────────
python audit_tenant_ids.py      # Check multi-tenancy coverage
python audit_fk_indexes.py      # Find unindexed FKs (raw)
python audit_fk_missing_indexes_filter.py  # Filter to actionable gaps
python audit_deletion_pathways.py          # Flag risky CASCADE rules

# ── STEP 3: SYNC FUNCTIONS ───────────────────────────────────
python sync_functions_to_json.py           # Extract + backup (safe)
python sync_soft_delete_functions.py       # Add soft-delete cascade functions
python sync_merge_functions_to_master.py   # Smart-merge definitions into JSON

# ── STEP 4: SYNC TRIGGERS ────────────────────────────────────
python sync_triggers_to_json.py            # Overwrite all triggers in JSON

# ── STEP 5: EXTRACT DEFAULTS ─────────────────────────────────
python extract_defaults.py                 # Review expected defaults

# ── STEP 6: DIFF & VERIFY ────────────────────────────────────
python schema_diff.py --group-by environment  # Final verification
```

---

## ⚙️ Prerequisites

- **Python 3.6+** — all scripts use only the standard library (`json`, `re`, `sys`, `pathlib`)
- No virtual environment or third-party packages required
- All scripts must be run from the [`dev-docs/db-design/`](.) directory (file paths are relative)
