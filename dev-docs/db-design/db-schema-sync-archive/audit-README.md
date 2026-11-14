# 🛡️ Schema Audit Tools

This document covers the **schema integrity audit** toolset — a suite of Python scripts that interrogate [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) to surface structural risks, security gaps, and performance hazards across 118 tables before those issues reach the physical database.

All scripts in this group are **read-only auditors**: they parse the JSON blueprint and emit structured JSON reports. They do not modify any source files or the live database.

> **Source of truth for all audits:** [`pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json)

---

## 🗂️ Audit Group 1 — Multi-Tenancy Isolation

### [`audit_tenant_ids.py`](audit_tenant_ids.py)

**Purpose:** Scans every table in the `public` schema and flags which tables have a `tenant_id` column and which do not.

**How it works:**
- Iterates all entries in the `tables` map of the JSON blueprint
- For each table, checks whether `tenant_id` exists in the `columns` dictionary
- Splits results into two lists: `tables_with_tenant_id` and `tables_missing_tenant_id`
- Writes a structured summary JSON and prints counts to stdout

**Why it exists:**
AevoFab is a multi-tenant SaaS platform. Every table that stores business data must be scoped to a tenant via `tenant_id` to prevent data leakage between customers. This audit identifies tables that may be missing row-level tenant isolation — a critical security and compliance requirement.

**Output:** [`audit_tenant_ids.json`](audit_tenant_ids.json)

**Usage:**
```bash
# Run from the dev-docs/db-design/ directory
python audit_tenant_ids.py
```

---

### [`audit_tenant_ids.json`](audit_tenant_ids.json)

**Purpose:** Structured output of the multi-tenancy isolation audit.

**What it contains:**
```json
{
  "summary": {
    "has_tenant_id_count": 67,
    "missing_tenant_id_count": 51
  },
  "tables_with_tenant_id": [ ... ],      // 67 tenant-scoped tables
  "tables_missing_tenant_id": [ ... ]    // 51 tables potentially lacking isolation
}
```

**How it is used:**
- Reviewed by the Architect to verify that all domain-specific tables (jobs, invoices, quotes, customers) carry `tenant_id`
- Tables in `missing_tenant_id` require justification — they are either global lookup/reference tables (e.g., `platform_role`, `address_type`) or an isolation gap that needs remediation

---

## 🗂️ Audit Group 2 — Foreign Key Index Coverage (Two-Stage Pipeline)

These two scripts form a sequential pipeline. The first performs a broad scan; the second filters noise to surface only actionable findings.

### Stage 1: [`audit_fk_indexes.py`](audit_fk_indexes.py) → [`audit_fk_missing_indexes.json`](audit_fk_missing_indexes.json)

**Purpose:** Identifies every Foreign Key in the schema that lacks a backing index, which would cause full table scans on `JOIN` and `ON DELETE` operations in PostgreSQL.

**How it works:**
- For each table, collects all declared indexes via [`get_index_columns()`](audit_fk_indexes.py) (parses column names out of `CREATE INDEX` definition strings using regex)
- Also collects implicit indexes from `primary_key` and `unique` constraints
- For each Foreign Key, checks whether any available index **starts with** the exact FK column set in order (prefix-match rule)
- Unmatched FKs are recorded as missing; results written to JSON

**Why it exists:**
PostgreSQL does not automatically create indexes on FK columns (unlike some other databases). Unindexed FKs cause severe performance degradation at scale — every cascade delete, referential integrity check, and JOIN becomes an O(n) table scan. With 447 FKs across 116 tables, this audit is essential before deploying to production.

**Output:** [`audit_fk_missing_indexes.json`](audit_fk_missing_indexes.json)

**Usage:**
```bash
python audit_fk_indexes.py
```

---

### [`audit_fk_missing_indexes.json`](audit_fk_missing_indexes.json)

**Purpose:** Raw output of the FK index coverage audit — includes all unindexed FKs before noise filtering.

**What it contains:**
```json
{
  "summary": {
    "total_foreign_keys": 447,
    "indexed_foreign_keys": 143,
    "missing_indexes": 304,
    "tables_needing_indexes": 116
  },
  "tables": {
    "<table_name>": [
      {
        "fk_name": "...",
        "columns": [ "..." ],
        "references": "<ref_table>"
      }
    ]
  }
}
```

> **Note:** The raw count of 304 missing indexes includes `created_by` and `updated_by` audit-trail FKs present on virtually every table. These are intentionally unindexed (write-heavy, never JOIN targets). Stage 2 filters these out.

---

### Stage 2: [`audit_fk_missing_indexes_filter.py`](audit_fk_missing_indexes_filter.py) → [`audit_fk_missing_indexes_filter_output.json`](audit_fk_missing_indexes_filter_output.json)

**Purpose:** Post-processes [`audit_fk_missing_indexes.json`](audit_fk_missing_indexes.json) to remove known-acceptable audit-column FKs (`created_by`, `updated_by`) and produce a clean, actionable list of **structurally critical** missing indexes.

**How it works:**
- Reads the raw output from Stage 1
- For each unindexed FK, checks whether its column set is a subset of `{"created_by", "updated_by"}` (the `ignored_columns` set)
- Drops any FK that is purely composed of audit columns
- Recalculates summary stats: total ignored vs. critical structural gaps
- Writes a filtered report

**Why it exists:**
The 304 raw missing indexes are noisy — 192 are `created_by`/`updated_by` FKs that reference the `user` table for audit trail purposes and do not need indexes. The filtered output reduces the actionable deficit from 304 to **112 critical structural indexes** across 65 tables. This is the report used to generate migration plans.

**Output:** [`audit_fk_missing_indexes_filter_output.json`](audit_fk_missing_indexes_filter_output.json)

**Usage:**
```bash
# Must be run AFTER audit_fk_indexes.py has generated its output
python audit_fk_missing_indexes_filter.py
```

---

### [`audit_fk_missing_indexes_filter_output.json`](audit_fk_missing_indexes_filter_output.json)

**Purpose:** Final actionable output of the FK index coverage pipeline — noise-filtered list of structurally critical missing indexes.

**What it contains:**
```json
{
  "summary": {
    "total_foreign_keys_in_db": 447,
    "properly_indexed_fks": 143,
    "audit_fks_ignored": 192,
    "CRITICAL_missing_structural_indexes": 112,
    "tables_needing_indexes": 65
  },
  "tables": {
    "<table_name>": [
      {
        "fk_name": "...",
        "columns": [ "..." ],
        "references": "<ref_table>"
      }
    ]
  }
}
```

**How it is used:**
- Directly consumed by the Architect to generate `CREATE INDEX` migration statements
- The `CRITICAL_missing_structural_indexes` count (112) is the number tracked in schema sync phases
- The `tables` map is used to determine which migration batches to prioritize (high-traffic tables like `job`, `invoice`, `quote` are addressed first)

---

## 🗂️ Audit Group 3 — Deletion Pathway Safety

### [`audit_deletion_pathways.py`](audit_deletion_pathways.py)

**Purpose:** Performs a comprehensive audit of all 447 Foreign Key `ON DELETE` behaviors across the schema, identifies which tables support soft-delete, and flags potentially dangerous `CASCADE` rules on financial and audit tables.

**How it works:**
- Iterates all tables and checks for soft-delete indicators (`is_active` or `deleted_at` columns)
- For each FK, extracts the `on_delete` rule — checking both structured JSON fields (`on_delete`, `ondelete`) and raw `definition` strings via keyword search (`ON DELETE CASCADE`, `ON DELETE RESTRICT`, `ON DELETE SET NULL`)
- Categorizes all FKs into four buckets: `CASCADE`, `RESTRICT`, `SET_NULL`, `NO_ACTION_OR_DEFAULT`
- Applies a `financial_audit_keywords` filter (`invoice`, `payment`, `ledger`, `subscription`, `usage`, `audit`, `quote`) to identify `CASCADE` rules on sensitive tables — flagged as `CRITICAL_risky_financial_cascades`

**Why it exists:**
Deletion pathway design is a data integrity and financial compliance concern. A `CASCADE` delete on an `invoice` or `payment` record could silently destroy financial history. This audit surfaces every such risk so the Architect can intentionally decide: convert to `RESTRICT`, implement application-level soft-delete, or keep `CASCADE` with documented justification.

**Output:** [`audit_deletion_pathways.json`](audit_deletion_pathways.json)

**Usage:**
```bash
python audit_deletion_pathways.py
```

---

### [`audit_deletion_pathways.json`](audit_deletion_pathways.json)

**Purpose:** Structured output of the deletion pathway safety audit.

**What it contains:**
```json
{
  "summary": {
    "total_tables": 118,
    "tables_with_soft_delete": 60,
    "tables_without_soft_delete": 58,
    "total_fks_analyzed": 447,
    "fk_rules": {
      "CASCADE": 81,
      "RESTRICT": 149,
      "SET_NULL": 199,
      "NO_ACTION_OR_DEFAULT": 18
    },
    "CRITICAL_risky_financial_cascades": 16
  },
  "critical_risks": [ ... ],           // 16 FKs with CASCADE on financial/audit tables
  "soft_delete_tables": [ ... ],       // 60 tables with is_active or deleted_at
  "hard_delete_tables": [ ... ],       // 58 tables without soft-delete markers
  "detailed_fk_rules": { ... }         // Full breakdown by CASCADE / RESTRICT / SET_NULL / NO_ACTION
}
```

**How it is used:**
- The `critical_risks` list is reviewed by the Architect to determine whether each `CASCADE` on a financial table is intentional or a design error
- The `soft_delete_tables` list validates that all customer-facing entities (`job`, `quote`, `invoice`, `customer`) support soft-delete before go-live
- The `hard_delete_tables` list is cross-checked against lookup/reference tables to confirm they are appropriate candidates for hard deletion

---

## 🔗 Pipeline Overview

```
pilot-db-schema-v2.6h.json
        │
        ├──► audit_tenant_ids.py           ──► audit_tenant_ids.json
        │    (multi-tenancy isolation)
        │
        ├──► audit_fk_indexes.py           ──► audit_fk_missing_indexes.json
        │    (raw FK index coverage)               │
        │                                          └──► audit_fk_missing_indexes_filter.py
        │                                               ──► audit_fk_missing_indexes_filter_output.json
        │                                               (noise-filtered critical index gaps)
        │
        └──► audit_deletion_pathways.py    ──► audit_deletion_pathways.json
             (ON DELETE rule safety)
```

---

## ⚙️ Prerequisites

- **Python 3.6+** — no third-party packages required; scripts use only the standard library (`json`, `re`)
- All scripts must be run from the [`dev-docs/db-design/`](.) directory (all file paths are relative)
- [`audit_fk_missing_indexes_filter.py`](audit_fk_missing_indexes_filter.py) depends on [`audit_fk_missing_indexes.json`](audit_fk_missing_indexes.json) — run [`audit_fk_indexes.py`](audit_fk_indexes.py) first

## 🚀 Run All Audits

```bash
# From dev-docs/db-design/
python audit_tenant_ids.py
python audit_fk_indexes.py
python audit_fk_missing_indexes_filter.py
python audit_deletion_pathways.py
```
