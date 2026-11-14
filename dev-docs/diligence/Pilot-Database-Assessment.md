# Pilot for Trades — Database Schema Assessment
*A grading of the schema from a database architect's seat (an AI-run review, directed and edited by me) — part of showing the engineering judgment behind this build. Companion to the Code-Quality Review.*

**Date:** 2026-10-13 · **Schema version:** v2.6h · **Engine:** PostgreSQL 17
**Sources:** `dev-docs/db-design/pilot-db-schema-v2.6h.json` (golden master) · ground-truth DDL dump

---

## Bottom line

**A strong relational foundation with three known gaps.** It is the kind of schema design that signals a senior data architect, not a feature-first app that grew a database by accident. The modeling discipline (transactional money in integer cents, 100% timezone-aware, heavy referential integrity, deep constraint coverage) is better than what most early-stage products carry.

What keeps it short of a hardened enterprise schema is a short, well-understood list — none of which is a redesign: **Postgres row-level security is not enabled** (tenant isolation is application/query-layer, and tested), optimistic concurrency is applied to only two tables, and the audit hash-chain columns exist but are not yet populated. I name all three plainly below.

> One-sentence version: *the data model is done carefully in the places that are expensive to change later; the remaining gaps are additive migrations, not foundations to rebuild.*

---

## Scale & shape

Counts from `backend/scripts/schema_dump_20260907_082031.sql` (the AWS environment's database at hibernation).

| Dimension | Count | Read |
|---|---|---|
| Tables | 193 across 2 schemas | Large, real domain model — not a toy |
| Foreign keys | 697 | ~3.5 FKs/table — relationships are enforced, not implied |
| Indexes | 460 | Deliberate access-path design, not just PK defaults |
| CHECK constraints | 145 | Business rules pushed into the data layer |
| GiST EXCLUDE constraints | 9 | Range/overlap integrity (e.g. no double-booking) — advanced |
| Triggers | 471 | Heavy server-side enforcement & derived-state maintenance |
| Money columns | Transactional money in integer cents; supplier unit prices in exact `NUMERIC(19,4)`; no floating-point money columns | The single most important correctness choice in a billing DB |
| Datetime columns | 100% timezone-aware (TIMESTAMPTZ) | No naive-datetime class of bug |

---

## Dimension grades

| Dimension | Grade | Why |
|---|---|---|
| Referential integrity | **A** | 697 FKs; relationships enforced at the DB, not left to the app |
| Data-type correctness | **A** | Integer-cents transactional money, no float money columns, TIMESTAMPTZ on every datetime — the two bugs that sink billing SaaS are designed out |
| Constraint depth | **A-** | 145 CHECKs + 9 GiST EXCLUDE; real invariants live in the schema |
| Indexing | **B+** | 460 indexes show intent; needs a load-driven review before scale (expected at this stage) |
| Tenant isolation | **B** | Correct and tested — but **application-layer**, not DB-enforced (no RLS). The honest gap. |
| Concurrency control | **B-** | Optimistic `version` column on only 2 tables; fine today, needs extending for multi-writer paths |
| Auditability | **B-** | Audit tables + hash-chain **columns** exist; chain is **not yet populated** |
| Schema governance | **A-** | Golden-master JSON + diff gate + migration discipline; the master, the models and the live dump all agree on 193 tables |

---

## What's genuinely strong

1. **Transactional money is integer cents, with no floating-point money columns.** Quotes, invoices and payments are stored in cents; supplier unit prices use exact `NUMERIC(19,4)` for sub-cent pricing. This is the tell that a real engineer designed the billing model. Float money is the single most common correctness defect in payment SaaS, and it's designed out here. (The integer-cents ceiling of ~$21.5M per value is a deliberate, documented trade-off, not an oversight.)
2. **100% timezone-aware storage (TIMESTAMPTZ) with naive datetimes rejected at the API boundary.** A whole class of scheduling/billing bugs cannot occur. Paired Python+DB "double-lock" standard.
3. **697 foreign keys + 145 CHECK constraints + GiST EXCLUDE.** Integrity is enforced by the database, not hoped for in the application. The EXCLUDE constraints in particular (overlap prevention) are something most early products never reach for.
4. **Schema is version-controlled against a golden master with a diff gate.** The database has the same governance rigor as the code — drift is detected, not discovered in production.

---

## What I'd flag myself (and how I think about it)

**1. Tenant isolation is application-layer; Postgres RLS is not enabled.**
Correct, and I state it plainly. Every tenant-owned table carries `tenant_id`, tenant-scoped routes filter on the caller's `tenant_id` (a final code read found a few route groups that don't — Known Limitations #27; public, webhook and signed-link routes are scoped by their own token or signature), and there's a dedicated isolation suite (`test_multi_tenancy_isolation.py`) plus tenant-scoping assertions across 16 test files, including cross-tenant IDOR tests. Enabling Postgres RLS is an **additive migration** (policies on the existing `tenant_id` columns) — a defense-in-depth hardening step, not a schema redesign. I chose to ship tested app-layer isolation (with the #27 exceptions disclosed) rather than claim a DB control I hadn't enabled.

**2. Optimistic concurrency (`version`) is on only two tables.**
True. Those two are the ones with genuine concurrent-write contention today. The pattern is in place and proven; extending it to other multi-writer paths is a per-table addition as those access patterns emerge under real load — not a structural change.

**3. The audit hash-chain columns are unpopulated.**
Honest and intentional. The tamper-evident audit design (hash-chain columns) is modeled into the schema so the migration cost is already paid; populating the chain is a write-path feature scoped for a compliance phase, not the build phase. I'd rather show the design is in place than claim an audit guarantee I'm not yet enforcing.

---

## The questions a sharp reviewer asks — and my answers

**Is this schema enterprise-grade?** Not fully — three known gaps remain. The expensive-to-change foundations — money type, timezone handling, referential integrity, constraint depth — are done to a standard most early products don't reach until an audit forces them to. The remaining items are a short, documented list, all additive.

**How is multi-tenant data isolated?** Application/query-layer: `tenant_id` on every tenant-owned table, applied in the query layer by convention (`db.get()` banned on tenant tables, ADR-0005); tenant-scoped routes filter on the caller's `tenant_id` (exceptions in Known Limitations #27), with a dedicated isolation test suite and cross-tenant IDOR tests. Postgres RLS is not enabled — enabling it is an additive defense-in-depth migration on columns that already exist.

**How do you prevent money/rounding errors?** Transactional money is stored as integer cents and supplier unit prices as exact `NUMERIC`; there are zero floating-point money columns in the schema. Rounding is explicit and tested.

**What about concurrent edits / lost updates?** Optimistic concurrency via a `version` column is in place on the two tables with real write contention today; the pattern extends per-table as new multi-writer paths appear.

**Can you prove the audit trail hasn't been tampered with?** The schema models a tamper-evident hash-chain — the columns are in place. Populating the chain is a scoped later feature; today the audit tables capture events without the cryptographic chain enforced. I disclose that rather than overstate it.

**How do you keep the schema from drifting?** It's version-controlled against a golden-master JSON with a diff gate in the workflow. Discrepancies are detected automatically; at hibernation the master, the models and the live database all agreed on 193 tables.

---

## What this demonstrates

The **irreversible decisions are right**: you cannot cheaply retrofit integer-cents money or timezone-aware storage into a mature billing system — those have to be right from the first migration, and they are. The remaining items are all **reversible and additive**: turn on RLS, extend optimistic locking, populate the audit chain. A data architect reading this sees a foundation they'd build on, not one they'd rip out. Designing the schema that way — and naming the gaps I know about — is the data-modeling judgment this project is meant to show.
