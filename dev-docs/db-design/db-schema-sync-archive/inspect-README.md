# 🔍 Schema Inspection & Reconnaissance Tools

This document covers the **pre-analysis / reconnaissance** toolset used to map the internal structure of the two master schema source files **before** running a full programmatic diff. These scripts exist because both source files are large (800 KB+) and structurally different — an LLM or human reader cannot reliably summarize their layout without a structural probe first.

---

## 🗂️ File Group: Schema Source Inputs

These are the two authoritative source files that all inspection and diff tooling operates on.

| File | Type | Description |
|---|---|---|
| [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) | JSON Blueprint | The master design-time schema. Defines all tables, columns, indexes, foreign keys, triggers, functions, and design decisions in structured JSON. This is the **source of truth for what the database _should_ look like**. |
| `pilot-db-schema-dump-master.sql` | SQL Dump | A `pg_dump --schema-only` export of the live PostgreSQL database. Represents the **current physical state** of the database as DDL (`CREATE TABLE`, `ALTER TABLE`, `CREATE INDEX`, `CREATE TRIGGER`, `CREATE FUNCTION`). |

---

## 🔬 File Group: Inspection Scripts & Their Outputs

These four files form the **reconnaissance layer** — lightweight probes that reveal the structural shape of each source file without performing a full comparison. Their outputs are fed to an AI agent to enable a more thorough, context-aware analysis during schema comparison tasks.

### 1. [`inspect_json.py`](inspect_json.py)

**Purpose:** Maps the internal key hierarchy of [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) into a structural blueprint.

**How it works:**
- Loads the JSON file and recursively walks the object tree up to 4 levels deep via [`get_structure()`](inspect_json.py)
- For each node, it records the **data type** of leaf values (`str`, `bool`, `int`) and the **shape of objects and arrays** (first item only, to show the pattern)
- Prints a condensed JSON skeleton showing all top-level keys and their nested shapes — without the actual data values

**Why it exists:**
The master JSON schema contains rich metadata beyond just table definitions: `version`, `generated_at_utc`, `dialect`, `extensions_required`, `design_questions`, `design_decisions`, `functions`, `notes`, and a deeply nested `tables` map. An AI agent cannot reliably parse an 800 KB file in one pass. This script produces a compact structural fingerprint that fits in a single context window.

**Usage:**
```bash
# Run from the dev-docs/db-design/ directory
python inspect_json.py
```

---

### 2. [`inspect_json_output.json`](inspect_json_output.json)

**Purpose:** The captured stdout output of [`inspect_json.py`](inspect_json.py). Represents the **full structural blueprint** of [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json).

**What it contains:**
- Top-level keys: `version`, `generated_at_utc`, `dialect`, `extensions_required`, `design_questions`, `design_decisions`, `functions`, `notes`, `tables`
- The `tables` map reveals each table's sub-keys: `comment`, `columns` (with per-column `type`, `nullable`, `default`, `description`), `primary_key`, `unique`, `indexes`, `foreign_keys`, `triggers`
- All leaf values are replaced with their Python type name (`"str"`, `"bool"`, `"int"`, `"..."` for truncated depth)

**How it is used:**
Provided to an AI agent alongside the source JSON so the agent understands the schema's full object model before being asked to perform comparison or gap-analysis tasks. Without this blueprint, the agent would have to guess or partially parse the 10,000+ line JSON file.

---

### 3. [`inspect_sql.py`](inspect_sql.py)

**Purpose:** Extracts and prints representative sample DDL statements from `pilot-db-schema-dump-master.sql` to reveal its structural patterns.

**How it works:**
- Opens the SQL dump and runs two targeted regex searches via [`re.search()`](inspect_sql.py):
  - Finds the **first `CREATE TABLE` block** (captures column definitions, constraints, and the closing `);`)
  - Finds the **first `ALTER TABLE` statement** (reveals how constraints and defaults are applied post-creation)
- Prints both samples to stdout so the reader can see exactly how the dump is formatted

**Why it exists:**
A `pg_dump` output is not uniform prose — it uses a specific formatting style for schema qualifiers (`public.`, `audit.`), quoted identifiers, constraint naming conventions, and multi-line `DO $$` function bodies. This script surfaces those patterns before the full diff parser is written and run, confirming assumptions about the file format.

**Usage:**
```bash
# Run from the dev-docs/db-design/ directory
# Update the sql_file variable on line 5 to point to the correct filename
python inspect_sql.py
```

> **Note:** The `sql_file` variable on [`line 5`](inspect_sql.py) defaults to `schema_dump_latest.sql`. Update it to `pilot-db-schema-dump-master.sql` before running.

---

### 4. [`inspect_sql_output.sql`](inspect_sql_output.sql)

**Purpose:** The captured stdout output of [`inspect_sql.py`](inspect_sql.py). Contains representative sample DDL from `pilot-db-schema-dump-master.sql`.

**What it contains:**
- A `--- SAMPLE CREATE TABLE STATEMENT ---` block showing how table columns, types, nullability, and `CHECK` constraints are formatted in the dump (example: `audit.event` table)
- A `--- SAMPLE ALTER TABLE STATEMENT ---` block showing how column defaults are applied via `ALTER TABLE ONLY … ALTER COLUMN … SET DEFAULT`

**How it is used:**
Provided to an AI agent to establish the exact DDL dialect and formatting conventions used by `pg_dump` before asking it to parse or reason about the full SQL file. This prevents the agent from making incorrect assumptions about schema qualifiers, identifier quoting, or constraint placement.

---

## 🔗 Downstream Consumers

The outputs from these inspection scripts directly enable the full diff pipeline:

```
pilot-db-schema-v2.6h.json   ──┐
                                  ├──► schema_diff.py ──► schema_diff_report.html
pilot-db-schema-dump-master.sql ┘

    ↑ Structural context provided by:
    inspect_json_output.json  (JSON shape map)
    inspect_sql_output.sql    (SQL format sample)
```

| File | Role |
|---|---|
| [`schema_diff.py`](../schema_diff.py) | Core diff engine — parses both source files into normalized Python dictionaries and compares them using set theory across tables, columns, PKs, unique constraints, FKs, indexes, triggers, and functions |
| `schema_diff_report.html` | Human-readable HTML dashboard output — shows what is missing in SQL (requires migration) and what is missing in JSON (requires schema file update), with full object-level detail |

For full documentation on running the diff, see [`README-schema-inspect.md`](inspect-README.md).

---

## ⚙️ Prerequisites

- **Python 3.6+** — no third-party packages required; scripts use only the standard library (`json`, `re`)
- Scripts must be run from the [`dev-docs/db-design/`](.) directory (all file paths are relative)
