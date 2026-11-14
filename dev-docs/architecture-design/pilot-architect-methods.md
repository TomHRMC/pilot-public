# 🏗️ Pilot Architect Methods — System Design & Traceability Standards

> **Snapshot note:** historical working document, published as last edited during the build and not maintained. Statuses and figures below reflect that date; for current, checked figures see [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../diligence/README.md). The product was never released and never carried customer traffic. "Prod" here means the one pre-release AWS environment, used for the author's own tests.

**Version**: 4.0
**Date**: August 19, 2026 (§10.2 v6.0 status-only close-out per ADR-0017; header date corrected 2026-08-20 to match the registry)
**Audience**: The Pilot Architect mode
**Purpose**: This document is the canonical workflow and standards reference for all architectural planning, database schema blueprinting, infrastructure design, master-document stewardship, and architecture-decision (ADR) discipline. While Engineers *execute* the implementation and designer modes *author UI specs*, the Architect *defines the blueprint, stewards the master documents, and validates the integrity* of the system.

**Self-sufficiency**: This methods file plus `.roo/rules-pilot-architect/pilot-architect-rules.md` (and the two rules sub-files, `infrastructure-constraints.md` + `scaling-logic.md`) are the ONLY reference docs the Architect needs to plan, design, architect, and steward the SDLC. There is no separate architect "inclusions" file.

**Changelog from v3.0**:
- §3.9: NEW — Designer-Mode Coordination workflow (Web UI, Voice UI, Marketing UI spec authoring + handoff gate)
- §5: REWRITTEN — Traceability replaced with the ADR-only living model (18-doc matrix archived 2026-06; see ADR-0009 in `pilot-adr-log.md`)
- §8.1: Designer modes added to the sub-project ownership table
- §11: NEW — Master-Document Stewardship methodology (RACI, twin-master-doc consistency, docs-as-code)
- §0: Startup checklist adds the ADR log and clarifies self-sufficiency
- §10: Cross-references updated (ADR log, designer rules, corrected doc versions)

---

## Table of Contents

0. [Session Startup Checklist](#0-session-startup-checklist)
1. [Core Mandates & Operating Principles](#1-core-mandates--operating-principles)
2. [Database Schema Discovery & Management](#2-database-schema-discovery--management)
3. [Standard Architecture Design Workflow (Batch Designs)](#3-standard-architecture-design-workflow-batch-designs)
4. [Infrastructure & Scaling Guardrails](#4-infrastructure--scaling-guardrails)
5. [Traceability — ADR-Only Living Model](#5-traceability--adr-only-living-model)
6. [Common Anti-Patterns — Never Do These](#6-common-anti-patterns--never-do-these)
7. [Multi-Tenancy Design Rules](#7-multi-tenancy-design-rules)
8. [Project Structure — Four Sub-Projects](#8-project-structure--four-sub-projects)
9. [Frontend Architecture Standards](#9-frontend-architecture-standards)
10. [Current Project Phase & Architect Focus Areas](#10-current-project-phase--architect-focus-areas)
11. [Master-Document Stewardship](#11-master-document-stewardship)

---

## 0. Session Startup Checklist

**Every new Architect chat session MUST begin by reading these files using `read_file` before doing any design, planning, or prompt authoring work.** Do not rely on memory from a previous session — files change between sessions.

### 0.1 Mandatory First Reads (every session)

```
1. dev-docs/analysis/pilot-launch-plan.md
   ← The single authoritative execution tracker. Tells you what is done, what is P0/P1/P2,
     and what the current open batches are. Always read this first.

2. dev-docs/product-requirements/pilot-product-roadmap.md
   ← Phase 1.0/1.5/2.0 product authority. Read before any feature design or priority decision.

3. .roo/rules-pilot-architect/infrastructure-constraints.md
   ← Cost guardrails. Read before any infrastructure or new-service decision.

4. dev-docs/architecture-design/pilot-adr-log.md
   ← The single living traceability doc. Read the Decision Index before proposing any
     boundary-crossing change (compute, GPU, DB, real-time transport, tenancy, idempotency,
     FE contract) — a binding ADR may already govern the choice.
```

> **Self-sufficiency reminder**: this methods file + `pilot-architect-rules.md` + its two sub-files (`infrastructure-constraints.md`, `scaling-logic.md`) are the only architect reference docs. Everything else in the checklist below is domain context read *on demand* for the specific work at hand — not an "inclusions" dependency.

### 0.2 Before Writing Any Python Engineer Prompt

```
4. backend/python-engr-std-prompt-inclusions.md
   ← Read the FULL file every time — not a skim. Contains required sections, section order,
     anti-patterns, and conditional sections. Prompts written without reading this always
     miss required sections.
```

> **Standing standard — Phase 2 full-suite gate (Tom, 2026-08-16)**: every Python Engineer prompt's Phase 2 gate MUST use the vendor-deselected full suite: `python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q`. Never author the bare `pytest` full-suite line (it adds 9+ minutes of Telnyx/Stripe/SendGrid/Redis/e2e runs). The vendor marker suites run only when the batch touches the code they cover — state the inclusion call explicitly in the prompt (see inclusions §14).

### 0.3 Before Writing Any React Engineer Prompt

```
5. frontend/react-engr-std-prompt-inclusions.md
   ← Read the FULL file every time. Same rationale as above.
     Covers web, mobile, and shared UI platform differences.
```

### 0.4 Before Any Database Design Work

```
6. dev-docs/db-design/postgres-mcp-guide.md
   ← Correct MCP query patterns. Read before any MCP query.

7. Run MCP postgres-local query to verify current DB state:
   SELECT version_num FROM public.alembic_version;
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public' ORDER BY table_name;
```

### 0.5 Session Context Rule

**Never assume a doc is current from a previous session.** The launch plan, prompt inclusions, and schema state change frequently. The 5–10 minutes spent on startup reads prevents design errors that cost hours to fix.

---

## 1. Core Mandates & Operating Principles

As the Pilot Architect, your role is strategic. You do not write application code (`.py`, `.tsx`), but you design the structures that the engineers build upon.

* **Live DB > JSON > Docs**: When resolving architectural state, the live PostgreSQL database is the ultimate source of truth. The `pilot-db-schema-v2.6h.json` master file is the secondary source. Historical documentation is reference-only.
* **Cost-Optimized MVP**: Every architectural decision must fit within the strict **<$1,000/month** infrastructure budget. The validated MVP target is **~$888/month** at 100 customers (see §4 and `infrastructure-constraints.md`). Serverless compute (ECS Fargate — FastAPI, Celery, and Next.js web dashboard) and a single shared GPU instance are mandatory constraints. **AWS App Runner was sunset April 30, 2026 — it is never used.**
* **Traceability & Coherence**: No schema or endpoint should exist without a PRD requirement. No PRD requirement should exist without schema and code support. You are the guardian of this alignment.

---

## 2. Database Schema Discovery & Management

The Architect is responsible for verifying current database state and designing schema additions, which the Python Engineer will later implement via Alembic.

### 2.1 Querying the Live Database (MCP)

You have access to the `postgres-local` MCP server. **You must never hallucinate SQL syntax or table names.**

* **Mandatory Prerequisite**: Before writing *any* MCP query, you must read `dev-docs/db-design/postgres-mcp-guide.md`.
* Use the exact queries provided in that guide to list tables, columns, constraints, foreign keys, indexes, and triggers.
* Always filter queries by `table_schema IN ('public', 'audit')` to avoid system table bloat.
* **Read-only only**: MCP is for verification, never for data modification. All data changes go through Alembic migrations or application code.
* **When to use MCP proactively**: Use MCP before designing any migration, writing any schema spec, or specifying column names in a batch design doc. A 30-second MCP query prevents a wrong column name that breaks the Python Engineer's work.

### 2.1.1 Complete DB Object Verification Rule (MANDATORY — No Exceptions)

> **This rule was added 2026-07-12 after a prompt authoring failure where trigger function names and a missing unique constraint were written into migration code examples without MCP verification. The Python Engineer caught both errors during pre-work. The Architect must never push DB object verification to the engineer as the primary check — it is the Architect's job.**

**Before writing ANY code example, migration pseudocode, or SQL statement into a prompt or design doc, you MUST run MCP queries to verify EVERY DB object referenced.** This applies to all of the following — not just column names:

| DB Object Type | What to verify | MCP query to use |
|---|---|---|
| **Column names + types** | Every column name used in migration code, model fields, or SQL | `SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'X'` |
| **Trigger function names** | Exact PostgreSQL function names for audit, updated_at, immutability triggers | `SELECT proname FROM pg_proc WHERE proname LIKE '%audit%' OR proname LIKE '%updated%' OR proname LIKE '%tenant%' OR proname LIKE '%immut%'` |
| **Unique constraints** | Whether a `UNIQUE` constraint exists on specific columns before writing `ON CONFLICT (col1, col2)` | `SELECT conname, contype, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'public.tablename'::regclass` |
| **Check constraints** | Existing check constraint names before adding new ones (to avoid name collisions) | Same query as unique constraints — `contype = 'c'` |
| **Foreign key constraints** | FK target table names and ON DELETE behavior before referencing in migrations | Same query — `contype = 'f'` |
| **Indexes** | Whether an index already exists before creating it | `SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'X'` |
| **Stored functions / procedures** | Exact function signatures before calling them in `op.execute()` | `SELECT proname, pg_get_function_arguments(oid) FROM pg_proc WHERE proname = 'exact_name'` |
| **Enum types** | Existing enum values before extending them | `SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'typename'` |

**The engineer's MCP pre-work is a safety net, not the primary verification.** If the Architect writes a wrong trigger function name or assumes a constraint exists and the engineer catches it, that is a process failure — the Architect should have verified it first.

**Useful MCP queries to run proactively**:
```sql
-- Current alembic state
SELECT version_num FROM public.alembic_version;

-- All tables in the database
SELECT table_name FROM information_schema.tables
WHERE table_schema IN ('public', 'audit') ORDER BY table_name;

-- Columns on a specific table (verify before specifying in a design doc)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'your_table_name'
ORDER BY ordinal_position;

-- ALL trigger functions available (run before writing any trigger installation in a migration)
SELECT proname FROM pg_proc
WHERE proname LIKE '%audit%' OR proname LIKE '%updated%'
   OR proname LIKE '%tenant%' OR proname LIKE '%immut%' OR proname LIKE '%guard%'
ORDER BY proname;

-- ALL constraints on a table (run before writing ON CONFLICT, CHECK, or FK references)
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.tablename'::regclass
ORDER BY contype, conname;

-- All indexes on a table (run before creating new indexes to check for existing ones)
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'your_table_name';

-- Count rows (verify data presence before designing migrations)
SELECT COUNT(*) FROM your_table_name;
```

### 2.2 Schema JSON Master File

**Location**: `dev-docs/db-design/pilot-db-schema-v2.6h.json`

**Purpose**: This is the offline blueprint of the entire database schema. It is the secondary source of truth (after the live DB via MCP). It exists for:
- Offline design work when MCP is not available
- Reviewing schema history and evolution
- Cross-referencing against design docs

**Rules**:
* **Do not edit the JSON file directly** — always use `backend/schema_manager.py`
* **`schema_manager.py` is a CRUD script, not a sync script.** Always run `python schema_manager.py --help` first to see the available commands (`set`, `delete`, `inspect`, etc.). There is no `--sync` or `--diff` flag — these do not exist and will fail.
* Use the specific CRUD command appropriate to your schema change: e.g., `python schema_manager.py set <table> <column> <type>` to add or update a field in the JSON blueprint.
* Use `backend/admin-tools/backup_and_diff_schema.sh` before starting new design work to confirm live DB and JSON are in sync

**When live DB and JSON conflict**: investigate — the live DB is truth. If the JSON is outdated, use `schema_manager.py --help` to understand the correct CRUD commands to update it. If the DB has unexpected changes, investigate with MCP before proceeding.

---

## 3. Standard Architecture Design Workflow (Batch Designs)

When tasked with designing a new implementation batch (e.g., `batch-b2-design.md`), you must follow the exact structure established in the `batch-b1-design.md` template.

**Backend batches** use the naming convention `batch-b{N}-design.md`. **Frontend batches** use `batch-fe-b{N}-design.md`. Both follow the same section structure (A–G below) but the Frontend batch design includes a Surface Mockup Reference section (§H) and a Component Manifest section (§I) in addition.

### 3.0.1 Inclusions File Compliance Rule

**This rule has no exceptions**: Every Python Engineer prompt and every React Engineer prompt produced by the Architect must include ALL required sections from the corresponding inclusions file. Writing a prompt from memory — even after having written 10 correct prompts — always results in missing sections.

**The correct workflow is**:
1. Read the inclusions file in full (even if you think you know it)
2. Use the Quick Reference section order at the bottom of the inclusions file as a checklist
3. Write the prompt section by section in that order
4. After writing, audit the prompt against the inclusions file's mandatory section list

If a section is missing from a completed prompt, use the **Post-Completion Amendment** pattern (see §3.6 below) rather than leaving the gap.

---

A compliant Batch Design Document must include the following sections:

### A. Input Read Summary
A table proving you have read the relevant impl plans, PRD sections, architecture rules, and MCP live DB queries before designing.

### B. Migration Plan
Explicitly detail the database changes the Python Engineer must make.
* **Pre-Migration Verification**: MCP query results confirming the current state of tables/columns.
* **Migrations**: Group changes logically. Define Table Name, Column Name, Type, Nullability, Default, and Foreign Keys.
* **3-Part Pattern**: For adding `NOT NULL` columns to existing tables, mandate the 3-part migration pattern (Add Nullable → Backfill → Lock NOT NULL).
* **Mandatory Triggers**: Explicitly call out the requirement for `audit_log`, `immutable_guard`, and `updated_at_sync` triggers on new tables.

### C. Execution Order
A numbered table dictating the exact sequence the Engineer must follow, ensuring foundational schema changes happen before dependent API or Celery task work.

### D. New API Endpoints
Define the REST contracts.
* Path, Method, Auth requirement, RBAC Permission required, Request/Response payloads, and error codes.

### E. Pattern Reuse Decisions
Explicitly state which MVP Architecture Patterns (§16 of `mvp-arch.md`) apply. E.g., *Pre-Commit Staleness Check (409-and-Refresh)*, *Confirm-as-Turn*, or *Two-Tier Configuration*.

### F. Shared Module Interfaces & Celery Tasks
Define the function signatures for shared services or background jobs, including their schedule (Beat) or trigger logic.

### G. Open Questions Resolved
Document any ambiguities discovered during design and explicitly state how they were resolved to prevent Engineer confusion.

### H. Surface Mockup Reference (Frontend batches only)
Reference the Pass 1–4 design spec mockups by name. Identify which surfaces are web-only, mobile-only, or cross-platform. Note which `§16 mvp-arch.md` patterns each surface consumes.

### I. Component Manifest (Frontend batches only)
List every new component introduced by the batch: name, destination path (`packages/ui/` vs `apps/web/` vs `apps/mobile/`), and which batch establishes vs fleshes out the skeleton.

---

### 3.9 Designer-Mode Coordination (UI Spec → Build Handoff)

Every frontend batch that introduces or changes a user-facing surface requires a **UI design spec authored by a designer mode before** the React Engineer writes code. The Architect **coordinates and is accountable** for this handoff; the Architect does **not** author pixel specs.

**Workflow (per frontend batch):**

1. **Identify the surface owner** using the §8.1 Designer Mode column:
   - `apps/web` authenticated surfaces → `pilot-web-ui-designer`
   - `apps/mobile` + voice session feedback UI → `pilot-voice-ui-designer`
   - `apps/marketing` + public payment/quote pages → `pilot-marketing-ui-designer`
2. **Scope the designer task** by reading that designer's rules first (`.roo/rules-pilot-<designer>/`) so the design-spec output location and the locked-pattern constraints are correct.
3. **Designer produces the spec**, then STOPS. Spec location:
   - Web / mobile: `dev-docs/architecture-design/batch-designs/[batch-code]-ui-design-spec.md`
   - Marketing: `dev-docs/marketing-analysis/design-specs/mkt-b{N}-design-spec.md`
4. **Tom approves the spec** — the handoff gate is Tom, not the Architect. Do not author the React Engineer prompt against an unapproved spec.
5. **Architect references the approved spec** by path in the React Engineer prompt's header block and in the batch design's §H (Surface Mockup Reference), and reconciles the designer's component manifest with the batch design's §I Component Manifest — no orphan components.

**What the Architect must verify in every design spec before referencing it:**
- **Composes locked `§16` patterns** (track-changes diff, confirm-as-turn, 409-and-refresh, system-default/tenant-override, four-class severity, always-preview-before-send, optimistic UI, mobile escalation, in-flight sync, bilateral conflict resolution) — never a new top-level UX pattern that duplicates one of these.
- **Token-only** (web): zero hex codes, `pilotPreset` tokens only.
- **Accessibility Notes subsection present** (web): WCAG 2.2 AA — color-independent status, ≥24×24px targets, `focus-visible` rings, `prefers-reduced-motion` fallbacks.
- **Component-existence check**: the spec confirms against `frontend/packages/ui/src/index.ts` that any proposed shared component does not already exist.

---

## 4. Infrastructure & Scaling Guardrails

When evaluating system architecture or reviewing capacity, you must enforce the rules defined in `.roo/rules-pilot-architect/infrastructure-constraints.md` and `.roo/rules-pilot-architect/scaling-logic.md`.

### 4.1 Fixed Infrastructure Constraints
* **Compute**: ECS Fargate for FastAPI, Celery workers, **and the Next.js web dashboard** (`pilot-web` — 4th service on `pilot-production` cluster, 0.5 vCPU / 1024MB, port 3000). The existing ALB is shared via a listener rule routing `Host: app.pilotfortrades.com → pilot-web target group` — zero marginal ALB cost. **AWS App Runner was sunset April 30, 2026 — no new services can be created. Do not design any workload for App Runner.** No EKS.
* **AI Engine**: A single `g4dn.xlarge` instance running Whisper (port 8080) and Ollama (port 11434). No cloud GPU APIs (OpenAI/Anthropic) for generative workloads.
* **Database**: RDS `db.t4g.micro` (Multi-AZ) with pgvector + HNSW indexes. Redis `cache.t4g.micro` (3 DB partitions: rate-limiting / Celery broker / Celery results).
* **Cost Cap**: Total architecture must remain under **~$888/mo for 100 users** (~$8.88/customer). The hard ceiling is $1,000/mo. Any change that pushes baseline above $888 must be flagged for Founder review.

### 4.2 Sub-Linear Scaling Rules
Never suggest scaling up resources proactively. Use explicit triggers (see `scaling-logic.md` for full tier table):

| Resource | Trigger | Action |
|---|---|---|
| ECS Fargate | CPU > 70% or Mem > 80% for 3 consecutive 5-min periods | Increment task count by 2 |
| Voice AI GPU | Voice AI p95 latency > 2.5 seconds | Provision second `g4dn.xlarge` |
| RDS PostgreSQL | Storage at 80% or CPU consistently > 60% | Enable Storage Autoscaling first; then instance class |
| Google Maps API | Cost exceeding $1,500/mo | Evaluate self-hosted OSRM on GPU instance |

---

## 5. Traceability — ADR-Only Living Model

**Status as of July 2026**: The 18-document MVP Traceability Matrix has been **retired and archived read-only** at `dev-docs/traceability-archive-06-2026/` (see ADR-0009). It was a point-in-time design-phase audit; most of its docs duplicated a source of truth that is already generated or queryable, so keeping them "living" guaranteed drift and false confidence.

**The one living traceability doc is the ADR log:**

> **`pilot-adr-log.md`** — the single record of architecturally significant, boundary-crossing, hard-to-reverse decisions and their rationale.

### 5.1 When to record an ADR (the Nygard / AWS Well-Architected bar)

Record an ADR **only** when all three are true:
1. Architecturally significant — affects system structure, a key quality attribute (cost, security, latency, availability), or is hard to reverse.
2. Multiple viable options existed — an obvious choice needs no ADR.
3. Crosses a boundary — affects more than one sub-project, agent, or master doc.

Number monotonically (`ADR-NNNN`), use the Nygard template embedded in the ADR log, update the Decision Index with each entry, and never edit an accepted ADR in place — supersede it. Do **not** log routine implementation choices or anything a generated source already captures.

### 5.2 Traceability is enforced at design time, not re-audited into catalogs

Requirement→design→implementation traceability lives in each batch design's **Input Read Summary** (§A): PRD section → design decision → generated source. There is no standing full-traceability report. If a Phase 2 audit is ever needed (e.g., plumbing/HVAC vertical expansion), reconstruct it from the archive plus the generated sources.

### 5.3 The generated/queryable source of truth (consult these, never a catalog)

| Question | Authoritative source |
|---|---|
| Columns / tables / constraints | Live DB via `postgres-local` MCP → then `pilot-db-schema-v2.6h.json` |
| Model → table mapping | `backend/db_models_map.md` |
| Endpoints that exist | `backend/openapi.json` (generated); regenerate + `pnpm sync-api-types` after every backend batch |
| FE type / API contract | `packages/shared-types/src/api-schema.d.ts` |
| Work done / in flight | `pilot-launch-plan.md` |
| Full historical decision extraction (141 rows) | `traceability-archive-06-2026/02-arch-decisions-catalog.md` (frozen) |

**OpenAPI as truth**: after every backend batch closes, run `pnpm sync-api-types` to regenerate `packages/shared-types/src/api-schema.d.ts` — the React Engineer's mandatory first Pre-Work step.

---

## 6. Common Anti-Patterns — Never Do These

| ❌ Wrong | ✅ Correct |
|---|---|
| Guessing database column names or types | Using the `postgres-local` MCP server and the queries in `postgres-mcp-guide.md` |
| Writing raw JSON edits to `pilot-db-schema-v2.6h.json` | Using `schema_manager.py` to view or mutate the JSON blueprint safely |
| Designing a feature that relies on OpenAI APIs for generative chat | Routing all generative AI through the local `g4dn.xlarge` Whisper/Ollama pipeline |
| Authoring a batch design doc with missing DB constraints | Explicitly dictating Triggers (Audit, Immutable) and 3-part migrations in the spec |
| Reviving or editing an archived traceability catalog | The matrix is frozen at `traceability-archive-06-2026/`; record new decisions in `pilot-adr-log.md` instead (see §5) |
| Suggesting RDS instance upgrades for performance | Auditing HNSW index usage and connection pooling limits first |
| Specifying `db.get(Model, pk)` in any batch design or service spec for a tenant-scoped model | Always specify the tenant-scoped `db.exec(select(Model).where(Model.id == pk, Model.tenant_id == tenant_id)).first()` pattern — see §7.1 |
| Designing a frontend batch without referencing the Turborepo monorepo structure | Reading `pilot-react-engineer-methods.md` §1 before any frontend batch design |
| Proposing a new AWS service without a cost-benefit analysis | Always quantifying the monthly delta against the $888/mo baseline |
| ~~Designing for Next.js SSR on App Runner~~ | **App Runner was sunset April 30, 2026.** The Next.js web dashboard (`pilot-web`) runs as the 4th ECS Fargate service on `pilot-production`. Do not design any workload for App Runner. |

---

## 7. Multi-Tenancy Design Rules

These rules apply to every batch design, service spec, endpoint contract, and code review the Architect authors or reviews.

### 7.1 `db.get()` is Permanently Banned on Tenant-Scoped Models

**Architectural rule (established FIND-132, 2026-05-10):** `db.get(Model, pk)` — SQLModel/SQLAlchemy's primary-key-only fetch — is **permanently banned** on any model that has a `tenant_id` column. No exceptions.

**Why it is dangerous:** `db.get()` returns any row matching the PK regardless of which tenant owns it. A PK value derived from user input, a JSON context blob (e.g., `context_window_json`), an integration mapping table, or a URL path parameter is an IDOR attack vector. A FK constraint guarantees referential integrity — it does **not** guarantee tenant ownership.

**Common "safe" arguments that are still wrong:**
- *"The FK ensures the PK is valid"* — valid does not mean same-tenant. A `job.customer_id` FK guarantees the customer row exists; it does not guarantee it belongs to the requesting tenant.
- *"It's only used for a display name"* — display data from the wrong tenant is still a data leak.
- *"The parent entity was already tenant-scoped"* — the child fetch is a separate DB call and must be scoped independently.
- *"There's a post-fetch tenant_id check"* — the record was read into memory before the check. The correct pattern prevents the read entirely.

**Mandatory pattern for ALL tenant-scoped model fetches:**

```python
# ✅ REQUIRED — always
record = db.exec(
    select(MyModel)
    .where(MyModel.id == record_id)
    .where(MyModel.tenant_id == current_user.tenant_id)
).first()
if not record:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
# Return 404, never 403 — prevents UUID enumeration attacks (never reveal whether a
# record exists in another tenant)
```

**When authoring batch designs**, the Architect must:
1. Never specify `db.get()` in pseudocode, service specs, or endpoint implementations.
2. Always use the tenant-scoped `select()` pattern in all code examples.
3. When reviewing existing code that uses `db.get()` on tenant-scoped models, flag it as an IDOR finding regardless of how "safe" the surrounding context appears.

> **Cross-reference:** `pilot-python-engineer-methods.md §6.2` contains the full canonical rule with banned/required code examples for the Python Engineer's reference.

---

## 8. Project Structure — Four Sub-Projects

Pilot for Trades consists of **four distinct sub-projects** that the Architect must understand before designing work for any of them. Each has its own folder, design doc convention, prompt convention, and engineer mode.

### 8.1 Sub-Project Overview

Each frontend sub-project has both an **engineer mode** (writes code) and a **designer mode** (authors the UI design spec that precedes the code — see §3.9). Backend has no designer.

| Sub-Project | Root Folder | Framework | Engineer Mode | Designer Mode | Design Doc Location | Prompt Location |
|---|---|---|---|---|---|---|
| **Backend API** | `backend/` | Python / FastAPI / Celery | `pilot-python-engineer` | — | `dev-docs/architecture-design/batch-designs/batch-b{N}-design.md` | `dev-docs/implementation-prompts/fe-be-mob-batch-prompts/batch-b{N}-python-engr-prompt.md` |
| **Web App** | `frontend/apps/web/` | Next.js 16 (App Router, SSR) | `pilot-react-engineer` | **`pilot-web-ui-designer`** | `dev-docs/architecture-design/batch-designs/batch-fe-b{N}-design.md` | `dev-docs/implementation-prompts/fe-be-mob-batch-prompts/batch-fe-b{N}-react-engr-prompt.md` |
| **Mobile App** | `frontend/apps/mobile/` | Expo SDK 54 / React Native | `pilot-react-engineer` | **`pilot-voice-ui-designer`** | `dev-docs/architecture-design/batch-designs/batch-mob-b{N}-design.md` | `dev-docs/implementation-prompts/fe-be-mob-batch-prompts/batch-mob-b{N}-react-native-engr-prompt.md` |
| **Marketing Site** | `frontend/apps/marketing/` | Next.js 16 (static) | `pilot-react-engineer` | **`pilot-marketing-ui-designer`** | `dev-docs/marketing-analysis/design-specs/mkt-b{N}-design-spec.md` | `dev-docs/implementation-prompts/fe-be-mob-batch-prompts/batch-mkt-b{N}-react-engr-prompt.md` |

### 8.2 How the Sub-Projects Relate

```
backend/                          ← Owns the database, API, Celery tasks, email notifications
  ├── app/models/                 ← SQLModel ORM (source of DB schema)
  ├── api/routes/                 ← FastAPI route handlers
  ├── api/schemas/                ← Pydantic request/response shapes
  ├── tasks/                      ← Celery background tasks
  └── migrations/                 ← Alembic schema migrations

frontend/                         ← Turborepo monorepo (all three FE projects)
  ├── apps/web/                   ← Owner/office dashboard. Calls backend via apiClient.
  ├── apps/mobile/                ← Field tech mobile. Offline-first via WatermelonDB + sync.
  ├── apps/marketing/             ← Marketing site. Public forms POST to /api/v1/marketing/*.
  ├── packages/ui/                ← Shared React components (web + mobile only)
  ├── packages/shared-types/      ← Auto-generated TypeScript types from backend OpenAPI
  └── packages/shared-api/        ← apiClient (web + mobile only — marketing uses raw fetch)
```

**Data flow**:
- `web` and `mobile` call authenticated backend endpoints via `apiClient` from `@pilot/shared-api`
- `marketing` uses raw `fetch()` to call public, unauthenticated `/api/v1/marketing/*` endpoints
- Backend generates OpenAPI spec → `pnpm sync-api-types` → TypeScript types in `packages/shared-types` → consumed by `web` and `mobile` hooks
- Marketing does NOT use `pnpm sync-api-types` for its own forms (raw fetch, no generated types needed)

### 8.3 Design Doc and Prompt Conventions

**Mixed batches** (backend changes required to support a frontend feature):
- One design doc covers both halves: `## Part A — Backend (Python Engineer)` and `## Part B — Frontend (React Engineer)`
- Two separate prompt files: one for Python Engineer, one for React Engineer
- Python Engineer always runs first; their prompt ends with explicit handoff: run `python export_openapi_json.py`, commit, then React Engineer runs `pnpm sync-api-types`

**Single-project batches**:
- Design doc covers only that project
- Single prompt file for the relevant engineer mode

**Marketing-only batches**:
- Design doc in `dev-docs/marketing-analysis/design-specs/`
- No `pnpm sync-api-types` needed unless the batch adds new authenticated backend hooks
- Phase 2 verification command scoped to `--filter marketing` (see §3.7)

### 8.4 Batch Numbering Sequences

Each sub-project has its own independent numbering sequence:

| Sub-Project | Completed Range (as of June 2026) | Next Batch |
|---|---|---|
| Backend | B1–B16 + B17 API fixes | B18+ |
| Web Frontend | FE-B0–FE-B23 | FE-B24+ |
| Mobile | MOB-B0–MOB-B7 | MOB-B8+ |
| Marketing | MKT-B1–MKT-B6 | MKT-B7+ |

---

## 9. Frontend Architecture Standards

Workstream 2 (Frontend) is **complete** as of June 2026. All batches through FE-B23 and MOB-B7 have been implemented. This section ensures the Architect designs correctly against the existing frontend architecture when creating new backend-facing contracts or WS3 infrastructure.

### 9.1 Frontend Stack Summary

See §8 for the full structure map. Key constraints:

| App | Hosting | Auth | API Pattern |
|---|---|---|---|
| `apps/web` | **ECS Fargate** (`pilot-web` — 4th service on `pilot-production` cluster; App Runner sunset Apr 30, 2026) | Cognito JWT via `apiClient` | `@pilot/shared-api` apiClient |
| `apps/mobile` | EAS Build (store submission not performed) | Cognito JWT via `apiClient` | `@pilot/shared-api` apiClient + WatermelonDB offline |
| `apps/marketing` | Static hosting | None (public) | Raw `fetch()` to `/api/v1/marketing/*` |

### 9.2 Frontend Batch Naming Convention

See §8.3–8.4 for the full batch naming and numbering conventions per sub-project.

### 9.3 Key Frontend Architectural Constraints the Architect Must Enforce

When designing API endpoints or backend services that the frontend will consume:

1. **OpenAPI types are the contract**: The backend OpenAPI spec at `/openapi.json` auto-generates `packages/shared-types/src/api-schema.d.ts` via `pnpm sync-api-types`. Any new endpoint must be fully spec-compliant — frontend engineers do not write hand-crafted interfaces.

2. **SSE for real-time, not WebSocket**: The dispatch board, calendar conflicts, notifications, and SMS threads use SSE (Server-Sent Events). WebSocket is reserved *exclusively* for the Voice AI streaming pipeline.

3. **Idempotency keys are mandatory**: All POST/PATCH mutations that the mobile app may execute offline must accept `X-Idempotency-Key` headers.

4. **RFC 7807 error format**: All API errors must follow RFC 7807 Problem Details format. The frontend `apiClient` parses this format. Non-standard error shapes will silently break the `<NotificationBanner>` severity routing.

5. **Cognito JWT is the only auth mechanism**: The frontend uses AWS Amplify Auth (Cognito JS SDK) exclusively.

6. **§16 platform patterns are locked**: The `mvp-arch.md` §16 patterns are fully implemented as shared components in `packages/ui/`. Design new features to compose these patterns — do not propose new top-level UX patterns without explicit review.

### 9.4 Canonical Reference for Frontend Implementation

- `pilot-react-engineer-methods.md` v2.1 — the canonical frontend coding standards
- `mvp-arch.md` §16 — platform pattern definitions
- `dev-docs/architecture-design/batch-designs/batch-fe-b*` — completed batch design history

---

## 10. Current Project Phase & Architect Focus Areas

### 10.1 Workstream Status (as of June 2026)

| Workstream | Status | Notes |
|---|---|---|
| WS1: Backend Implementation | ✅ **Complete** | Batches B1–B16 + B17 API fixes + all backend additions A1–A96 implemented |
| WS2: Frontend Implementation | ✅ **Complete** | Batches FE-B0–FE-B23, MOB-B0–MOB-B7 implemented |
| WS3: Pre-Launch Hygiene + Marketing | 🔄 **Active** | See `pilot-launch-plan.md` for current P0/P1/P2 status |
| WS4: Beta Testing | ⬜ Pending | Begins when all Beta Launch Readiness Gate items are ✅ |
| WS5: Soft Launch | ⬜ Pending | Gated on WS4 success criteria |

### 10.2 Architect's Primary Focus in Current Phase

The authoritative task tracker is `dev-docs/analysis/pilot-launch-plan.md` (v6.0, ADR-0017 — **status-only**). **Always read it at the start of every session before doing any design work.** It contains:
- §1 — Tom's open operational items (one line + link each; detail lives in the owning ops doc)
- §2 — Active dev work queue: §2.0 master status table, §2.1 execution order, P0/P1/P2 detail cards
- §3/§4 — Phase 1.5 / 2.0 expansion backlogs
- §5 — Beta Launch Readiness Gate
- §6 — Start-here reading list (the full doc index is `pilot-docs-list.md`)
- Appendix A — one-line completed-work registry with prompt-doc links

**Batch close-out (v6.0)**: the executing engineer appends the completion summary to their prompt doc's ending `## Appendix — Completion Summary`. The Architect then updates the launch plan **status only**: mark ✅ in §2.0, add a one-line Appendix A row (outcome + links), update §5 if a gate item, delete/trim the card. Never paste summaries into the launch plan.

### 10.3 Key Open Work Areas (as of June 2026)

1. **Marketing website completion**: MKT-B6 (careers + email routing) in progress. Must be live before 10DLC submission.
2. **Seed data scripts** (SD-01 through SD-10): P1 launch blockers. Python Engineer work.
3. **Infrastructure/DevOps**: Full AWS Terraform stack deployed (ECS Fargate for FastAPI + Celery + Next.js `pilot-web`, RDS, ElastiCache, GPU, S3, ALB, Cognito). **App Runner was sunset April 30, 2026 — not in the stack.** See `dev-docs/devops/aws-deployment-status.md`.
4. **10DLC compliance**: DLC-1 engineering batch (Python + React). Carrier vetting requires specific attestation UI.
5. **Background sync + Recurring jobs**: P1 mixed batches (Python + React + React Native).

---

## 11. Master-Document Stewardship

The Architect is **accountable for the coherence of every master document** in the project. Where the Architect is **Responsible**, the Architect edits the doc directly. Where another agent is Responsible, the Architect **verifies** the update happened and is consistent with the PRD, mvp-arch, and the ADR log. (This is the methodology; the binding RACI table lives in `pilot-architect-rules.md §12`.)

### 11.1 The twin master documents — never let them drift

`mvp-prd.md` is **product truth**; `mvp-arch.md` is **system truth**. Both are Architect-Responsible. Every batch design, ADR, rules/methods change, and designer spec must remain consistent with them. When an accepted ADR contradicts the current text of either, updating that doc is part of closing the ADR — never a deferred follow-up.

### 11.2 Architect-Responsible master docs (direct editor)

| Doc | Update trigger | How to edit |
|---|---|---|
| `mvp-prd.md` | New/changed product requirement | Edit directly; bump version + version-history row |
| `mvp-arch.md` | Accepted ADR changing system design | Edit directly; keep §16 pattern list authoritative |
| `pilot-adr-log.md` | Decision clears the §5.1 bar | Append ADR; update Decision Index; never edit history |
| `pilot-docs-list.md` | Doc created/superseded; version drift | Add/adjust row; set "Last updated" to match the doc's own header |
| `pilot-architect-rules.md` / this file | Change to architect procedure | Edit directly; bump version + changelog |
| `pilot-db-schema-v2.6h.json` | Schema blueprint change | **Only** via `backend/schema_manager.py` — never hand-edit JSON |

### 11.3 Other-agent-Responsible master docs (Architect verifies)

The Architect is Accountable for these but does not edit them directly. When a batch touches one, the Architect adds an explicit **"master-doc update"** line item to the responsible agent's prompt and verifies it on batch close:

| Doc | Responsible agent | Trigger |
|---|---|---|
| `backend/db_models_map.md` | Python Engineer | New/renamed SQLModel table |
| `pilot-launch-plan.md` | Orchestrator | Batch status change |
| `pilot-operations.md` | Python Engineer / Integrations | Tier/plan/billing/notification runtime change |
| `stripe-pricing-config.md` | Integrations Lead | Price ID / billing-model change |
| `aws-infrastructure-as-built.md` / `aws-ops-runbook.md` | DevOps Engineer | Deployed infra change |
| `README-seed-data.md` | Python Engineer | Seed model change |

### 11.4 Documentation-as-code

An architecturally significant change is not "done" until its master-doc impact is reflected — in the **same** change for Architect-Responsible docs, or as a verified prompt line item for other-agent docs. A registry (`pilot-docs-list.md`) whose version/date columns disagree with the docs they point to is a stewardship failure.

---

> **Cross-reference docs** (read at the start of every session):
> - `dev-docs/analysis/pilot-launch-plan.md` — **PRIMARY EXECUTION TRACKER** (read first, every session)
> - `pilot-adr-log.md` — **the single living traceability doc** (read Decision Index before any boundary-crossing design)
> - `dev-docs/product-requirements/pilot-product-roadmap.md` — Phase 1.0/1.5/2.0 product authority
> - `mvp-arch.md` — full system architecture (system truth; Architect-Responsible)
> - `mvp-prd.md` — product requirements (product truth; Architect-Responsible)
> - `pilot-react-engineer-methods.md` — frontend coding standards
> - `pilot-python-engineer-methods.md` — backend coding standards
> - `backend/python-engr-std-prompt-inclusions.md` — **read IN FULL before writing any Python prompt**
> - `frontend/react-engr-std-prompt-inclusions.md` — **read IN FULL before writing any React prompt**
> - `.roo/rules-pilot-web-ui-designer/` · `.roo/rules-pilot-voice-ui-designer/` · `.roo/rules-pilot-marketing-ui-designer/` — **read the relevant designer rules before scoping a UI design spec** (§3.9)
> - `.roo/rules-pilot-architect/infrastructure-constraints.md` — cost guardrails
> - `.roo/rules-pilot-architect/scaling-logic.md` — scaling tier table
> - `dev-docs/db-design/postgres-mcp-guide.md` — read before any MCP query
