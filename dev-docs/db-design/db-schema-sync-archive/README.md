# Schema Sync & Audit Toolchain (Archived)

A self-contained set of Python tools built during the Pilot for Trades database-design
phase to keep the design-time **JSON schema blueprint**
([`../pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json)) in lockstep with the
**physical PostgreSQL database**, and to audit that schema for multi-tenancy,
performance, and data-integrity risks *before* any change reached production.

> **Archived / frozen reference.** These scripts and their output files are preserved
> as-is from the build. They document the schema-governance workflow; they are not a
> maintained tool. They are read-only auditors or offline file-processors — they hold
> **no database credentials** and connect to **no live database**.

---

## Why this is kept in the public repo

It is evidence of how the schema was actually governed: a 118-table, multi-tenant schema
was not hand-waved into existence — it was continuously audited for tenant-isolation gaps,
missing foreign-key indexes, and dangerous `ON DELETE` cascades, and the design-time
blueprint was programmatically reconciled against the live database. The committed `*.json`
outputs are the real reports those audits produced.

## The toolsets

Each area has its own detailed README; start there.

| Area | What it does | Start here |
|---|---|---|
| **Audit** | Read-only integrity audits: multi-tenancy isolation, FK index coverage (two-stage pipeline), and deletion-pathway safety on financial/audit tables. | [`audit-README.md`](audit-README.md) |
| **Inspect** | Lightweight structural reconnaissance of the large (800 KB+) schema sources, so a human or AI reader can map their shape before a full diff. | [`inspect-README.md`](inspect-README.md) |
| **Sync** | Extract PostgreSQL functions and triggers from the physical dump and synchronize them into the JSON blueprint (dry-run and write-back modes). | [`sync-README.md`](sync-README.md) |
| **Extract** | Enumerate every business-logic column default in the blueprint to generate `ALTER COLUMN … SET DEFAULT` migrations. | [`extract-README.md`](extract-README.md) |

A standalone [`trigger-inventory.md`](trigger-inventory.md) summarizes the ~293 database
triggers (immutable guards, audit triggers, timestamp bumps, total recalculations).

## Inputs

- [`../pilot-db-schema-v2.6h.json`](../pilot-db-schema-v2.6h.json) — the design-time schema
  blueprint and source of truth for the audit/extract tools.
  *(Earlier revisions of the per-topic READMEs refer to this file by its AevoFab-era
  name — "AevoFab" was the product's former name before it was renamed to Pilot for
  Trades.)*
- A `pg_dump --schema-only` export of the live database (referenced as
  `…-db-schema-dump-master.sql`) — **not included in this public snapshot.** The sync and
  inspect scripts expect it to be present locally.

## Running (historical)

- Python 3.6+, standard library only (`json`, `re`) — no third-party packages.
- Paths in the per-topic READMEs are relative to the build-time working directory
  (`dev-docs/db-design/`); they are preserved for provenance, not as a run guide.
