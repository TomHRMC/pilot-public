# 🔄 Schema Sync Tools

This document covers the **schema synchronization** toolset — a suite of Python scripts that extract database objects (functions and triggers) from the physical SQL dump and synchronize them into the master JSON blueprint ([`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json)).

Unlike the audit tools which are purely read-only, these scripts have two modes: **extraction-only (dry run)** and **write-back (live sync)**. Each script's behavior is documented clearly below.

> **Source of truth for all sync operations:**
> - Read from: [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) and `pilot-db-schema-dump-master.sql`
> - Written back to: [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) *(write-back scripts only)*

> **⚠️ File Naming Note:** All backup and export output files use the `sync_` prefix. Files previously named `design_*` are now `sync_design_*`; files previously named `physical_db_*` are now `sync_physical_db_*`.

---

## 🗂️ Sync Group 1 — PostgreSQL Functions

These four files handle the extraction, inspection, and write-back sync of PostgreSQL functions between the SQL dump and the JSON blueprint. The workflow is a three-step pipeline: **extract → review → merge**.

### [`sync_functions_to_json.py`](sync_functions_to_json.py) ← Run First

**Purpose:** Performs a **dry-run extraction** — reads existing functions from both the JSON blueprint and the SQL dump, saves each set to its respective output file, and **does not modify the master JSON**.

**How it works:**

**Step 1 — Extract from JSON blueprint:**
- Opens [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) and reads the top-level `functions` array
- Saves the existing JSON function definitions as-is to [`sync_design_functions_backup.json`](sync_design_functions_backup.json)

**Step 2 — Extract from SQL dump:**
- Opens `pilot-db-schema-dump-master.sql` and runs a regex pattern to locate all `CREATE [OR REPLACE] FUNCTION` blocks including their `$$` dollar-quoted bodies
- Extracts each function name and full DDL definition
- Saves results to [`sync_physical_db_functions_export.json`](sync_physical_db_functions_export.json)

**Why it exists:**
Before performing any live sync, you need to see exactly what functions exist in each source — and how many. This script lets you compare counts and definitions safely without risk of overwriting the master JSON. Run this first to inspect the delta before running the targeted sync.

> **🛑 Safe to run — does NOT modify [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json)**

**Usage:**
```bash
# Run from the dev-docs/db-design/ directory
python sync_functions_to_json.py
```

---

### [`sync_design_functions_backup.json`](sync_design_functions_backup.json)

**Purpose:** A snapshot of all PostgreSQL functions currently defined in the **JSON blueprint** at the time [`sync_functions_to_json.py`](sync_functions_to_json.py) was last run.

**What it contains:**
An array of function objects from the JSON `functions` key, each with:
```json
[
  {
    "schema": "audit",
    "name": "log_changes",
    "language": "plpgsql",
    "returns": "trigger",
    "definition": "CREATE FUNCTION audit.log_changes() ..."
  }
]
```

Functions captured include the full set of trigger functions: `audit.log_changes`, `audit.log_changes_code_pk`, `sync_user_email_from_endpoint_fn`, `guard_user_endpoint_primary_email_fn`, `recalc_quote_totals_fn`, and others defined in the design blueprint.

**How it is used:**
- Acts as a **safety backup** — if a write-back sync overwrites or corrupts function definitions in the master JSON, this file can be used to restore the prior state
- Also used to compare the design-time function list against the physical export to identify which functions exist only in the blueprint vs. only in the live database

---

### [`sync_physical_db_functions_export.json`](sync_physical_db_functions_export.json)

**Purpose:** A snapshot of all PostgreSQL functions extracted from the **physical SQL dump** (`pg_dump`) at the time [`sync_functions_to_json.py`](sync_functions_to_json.py) was last run.

**What it contains:**
An array of function objects, each with just `name` and `definition` (no schema metadata, as extracted directly from DDL):
```json
[
  {
    "name": "audit.log_changes",
    "definition": "CREATE FUNCTION audit.log_changes() RETURNS trigger ..."
  },
  {
    "name": "public.guard_created_fields_immutable",
    "definition": "CREATE FUNCTION public.guard_created_fields_immutable() ..."
  }
]
```

Functions captured include all trigger functions present in the live database: audit logging functions, guard functions (`guard_tenant_user_platform_isolation`, `guard_user_endpoint_primary_email_fn`, `guard_created_fields_immutable`), recalculation functions (`recalc_invoice_totals_fn`, `recalc_quote_totals_fn`, `recalc_change_order_totals_fn`), and others.

**How it is used:**
- Compared against [`sync_design_functions_backup.json`](sync_design_functions_backup.json) to identify functions present in the physical database but missing from the JSON blueprint
- The diff between these two files drives decisions about which functions need to be written back into the master JSON
- Consumed by [`schema_diff.py`](../schema_diff.py) as part of the full schema comparison pipeline
- Fed directly into [`sync_merge_functions_to_master.py`](sync_merge_functions_to_master.py) as the source of ground-truth definitions

---

### [`sync_merge_functions_to_master.py`](sync_merge_functions_to_master.py)

**Purpose:** A **write-back merge** script that performs a "smart merge" — it combines the rich structured metadata from the JSON design backup with the exact up-to-date DDL definitions from the physical export, then writes the result back into the master JSON blueprint.

**How it works:**
- Reads [`sync_design_functions_backup.json`](sync_design_functions_backup.json) as the **source of metadata** (schema, language, returns, plus any design-time annotations)
- Reads [`sync_physical_db_functions_export.json`](sync_physical_db_functions_export.json) as the **source of definitions** (the exact `CREATE FUNCTION` DDL as deployed)
- Builds a lookup dictionary of physical definitions keyed by function name
- For each function in the design backup, resolves the full name using `schema.name` format and replaces its `definition` with the physical version if one exists — preserving all other metadata fields unchanged
- Functions that exist in the design backup but have no matching physical entry keep their existing definition (no data loss)
- Writes the merged `functions` array back into [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json)

**Why it exists:**
The design backup and the physical export have complementary strengths:
- The **design backup** has rich metadata (`schema`, `language`, `returns`) but may have stale or hand-edited `definition` strings
- The **physical export** has exact DDL from the running database but has minimal metadata (just `name` + `definition`)

This script combines the best of both: structured metadata from the design + byte-accurate definitions from the physical database. It is the final step after running both [`sync_functions_to_json.py`](sync_functions_to_json.py) and [`sync_soft_delete_functions.py`](sync_soft_delete_functions.py).

> **⚠️ WRITE-BACK SCRIPT — overwrites the `functions` array in [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json)**
> Run [`sync_functions_to_json.py`](sync_functions_to_json.py) first to ensure both input files are current.

**Usage:**
```bash
# Run from the dev-docs/db-design/ directory
# Prerequisites: sync_functions_to_json.py must have been run first
python sync_merge_functions_to_master.py
# Then verify:
python schema_diff.py --group-by environment
```

---

## 🗂️ Sync Group 2 — Targeted Soft-Delete Function Sync

### [`sync_soft_delete_functions.py`](sync_soft_delete_functions.py)

**Purpose:** A **targeted, write-back sync** that finds all `cascade_soft_delete_to_*` functions in the SQL dump and adds any missing ones into the master JSON blueprint.

**How it works:**
- Loads both [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) and `pilot-db-schema-dump-master.sql`
- Applies a targeted regex: `CREATE FUNCTION public.(cascade_soft_delete_to_[a-zA-Z_]+)()` — matches only the family of soft-delete cascade functions
- Builds a set of existing function names from the JSON `functions` array to prevent duplicates
- For each new function found, appends a complete function object with `name`, `schema`, `language`, `returns`, and `definition`
- Writes the updated `schema_json` back to [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json)

**Why it exists:**
The soft-delete cascade functions (`cascade_soft_delete_to_job_assignments`, `cascade_soft_delete_to_invoice_lines`, etc.) are generated in bulk during migration phases and can fall out of sync with the JSON blueprint. This script is the targeted tool to close that specific gap without touching any other function definitions.

> **⚠️ WRITE-BACK SCRIPT — modifies [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) directly**
> Run [`sync_functions_to_json.py`](sync_functions_to_json.py) first to back up the current state.

**Usage:**
```bash
# Run from the dev-docs/db-design/ directory
# Recommended: run sync_functions_to_json.py first for a backup
python sync_soft_delete_functions.py
# Then verify the result:
python schema_diff.py --group-by environment
```

---

## 🗂️ Sync Group 3 — PostgreSQL Triggers

These three files handle the extraction and full injection of PostgreSQL triggers from the SQL dump into the JSON blueprint.

### [`sync_triggers_to_json.py`](sync_triggers_to_json.py)

**Purpose:** A **full write-back sync** that extracts all triggers from the physical SQL dump and overwrites the trigger definitions on every table in the master JSON blueprint with the ground-truth physical database state.

**How it works:**

**Step 1 — Backup existing JSON triggers:**
- Traverses all tables in both the `public` schema and any named schemas (e.g., `audit`) in [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json)
- Collects all tables that have non-empty `triggers` arrays via [`backup_triggers()`](sync_triggers_to_json.py)
- Saves the complete trigger map (keyed by `schema.table`) to [`sync_design_triggers_backup.json`](sync_design_triggers_backup.json)

**Step 2 — Extract physical triggers from SQL dump:**
- Reads `pilot-db-schema-dump-master.sql` and splits on `;`
- For each statement, applies a `CREATE TRIGGER` regex to capture: trigger name, schema, table, and full DDL definition
- Builds a `sql_triggers` map keyed by `schema.table`
- Saves the complete physical trigger map to [`sync_physical_db_triggers_export.json`](sync_physical_db_triggers_export.json)

**Step 3 — Inject triggers into JSON (overwrite):**
- Via [`inject_triggers()`](sync_triggers_to_json.py), iterates every table in the JSON blueprint
- For tables that have matching entries in the physical trigger map: **overwrites** the `triggers` array with the SQL ground-truth
- For tables with no physical triggers: **clears** the `triggers` array to `[]`
- Writes the fully updated `schema_json` back to [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json)

**Why it exists:**
Trigger definitions in the JSON blueprint can become stale when triggers are added, modified, or renamed in the database during migration phases. Rather than manually updating each table's `triggers` array, this script performs a single authoritative overwrite using the live database as the source of truth. This is how the JSON blueprint stays synchronized after trigger-heavy migration phases.

> **⚠️ WRITE-BACK SCRIPT — overwrites ALL trigger definitions in [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json)**
> A backup is automatically saved to [`sync_design_triggers_backup.json`](sync_design_triggers_backup.json) before any writes occur.

**Usage:**
```bash
# Run from the dev-docs/db-design/ directory
python sync_triggers_to_json.py
# Then verify the result:
python schema_diff.py --group-by environment
```

---

### [`sync_design_triggers_backup.json`](sync_design_triggers_backup.json)

**Purpose:** A snapshot of all trigger definitions as they existed in the **JSON blueprint** before [`sync_triggers_to_json.py`](sync_triggers_to_json.py) last ran. Serves as a rollback point.

**What it contains:**
A map keyed by `schema.table` with each table's trigger array as it was defined in the JSON blueprint (structured format with `name`, `timing`, `events`, `for_each`, `function`):
```json
{
  "public.user_endpoint": [
    {
      "name": "trg_user_endpoint_guard_biu",
      "timing": "BEFORE",
      "events": ["INSERT", "UPDATE"],
      "for_each": "ROW",
      "function": "guard_user_endpoint_primary_email_fn()"
    }
  ]
}
```

**How it is used:**
- **Recovery:** If a trigger sync produces an undesirable result, this file contains the pre-sync state to restore from
- **Comparison:** Diff this against [`sync_physical_db_triggers_export.json`](sync_physical_db_triggers_export.json) to understand what the sync will change before committing it

---

### [`sync_physical_db_triggers_export.json`](sync_physical_db_triggers_export.json)

**Purpose:** A snapshot of all trigger definitions extracted from the **physical SQL dump** at the time [`sync_triggers_to_json.py`](sync_triggers_to_json.py) last ran. Represents the ground-truth physical database trigger state.

**What it contains:**
A map keyed by `schema.table` with each table's triggers as raw DDL strings parsed from the `pg_dump` output:
```json
{
  "public.address": [
    {
      "name": "audit_address_changes",
      "definition": "CREATE TRIGGER audit_address_changes AFTER INSERT OR DELETE OR UPDATE ON public.address FOR EACH ROW EXECUTE FUNCTION audit.log_changes()"
    },
    {
      "name": "trg_address_guard_created_immutable",
      "definition": "CREATE TRIGGER trg_address_guard_created_immutable BEFORE UPDATE ON public.address FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()"
    }
  ]
}
```

Every table in the physical database has three standard triggers: an `audit_*_changes` AFTER trigger (→ `audit.log_changes()`), a `trg_*_guard_created_immutable` BEFORE UPDATE trigger (→ `guard_created_fields_immutable()`), and a `trg_*_set_updated_at` BEFORE UPDATE trigger (→ `set_updated_at()`).

**How it is used:**
- This is the source injected into the JSON blueprint by [`sync_triggers_to_json.py`](sync_triggers_to_json.py)
- Independently useful for reviewing trigger coverage across all tables without opening the 800 KB JSON file
- Consumed by [`schema_diff.py`](../schema_diff.py) when comparing trigger parity between JSON and SQL

---

## 🔗 Pipeline Overview

```
pilot-db-schema-v2.6h.json  ──┐
                                 ├──► sync_functions_to_json.py (DRY RUN / Step 1)
pilot-db-schema-dump-master.sql┘       │
                                         ├──► sync_design_functions_backup.json ──┐
                                         └──► sync_physical_db_functions_export.json ──┤
                                                                                        │
                                         sync_soft_delete_functions.py ──► [WRITES BACK] pilot-db-schema-v2.6h.json
                                         (cascade_soft_delete_to_* only / Step 2)      │
                                                                                        │
                                         sync_merge_functions_to_master.py ─────────────┘
                                         (smart merge: metadata + DDL / Step 3) ──► [WRITES BACK] pilot-db-schema-v2.6h.json

pilot-db-schema-v2.6h.json  ──┐
                                 ├──► sync_triggers_to_json.py ──► sync_design_triggers_backup.json
pilot-db-schema-dump-master.sql┘       │                     ──► sync_physical_db_triggers_export.json
                                         └──► [WRITES BACK] pilot-db-schema-v2.6h.json
                                              (all trigger arrays overwritten / Step 4)
```

---

## ⚙️ Prerequisites

- **Python 3.6+** — no third-party packages required; scripts use only the standard library (`json`, `re`)
- All scripts must be run from the [`dev-docs/db-design/`](.) directory (all file paths are relative)

## 🚀 Recommended Execution Order

```bash
# From dev-docs/db-design/

# Step 1: Extract & back up functions from both sources (safe, no writes)
python sync_functions_to_json.py

# Step 2: Sync soft-delete cascade functions into JSON (targeted write-back)
python sync_soft_delete_functions.py

# Step 3: Smart-merge all function metadata + definitions into master JSON (write-back)
python sync_merge_functions_to_master.py

# Step 4: Sync all triggers into JSON (full write-back, auto-backs up first)
python sync_triggers_to_json.py

# Step 5: Verify final state is clean
python schema_diff.py --group-by environment
```
