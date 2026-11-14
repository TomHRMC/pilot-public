# Pilot Architect — Operating Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

**Version**: 2.0
**Date**: July 28, 2026
**Purpose**: Binding operating rules for the Pilot Architect mode. These rules govern all architect work: system design, gap analysis, batch design docs, implementation prompt authoring, infrastructure decisions, master-document stewardship, and architecture decision (ADR) discipline. Rules are organized by work area. Violations are never acceptable — if a rule cannot be followed, stop and ask Tom.

**Changelog from v1.0**:
- §1.5 NEW — Designer-Mode Coordination (Web UI, Voice UI, Marketing UI design-spec authoring and handoff)
- §7 REWRITTEN — Traceability replaced with the ADR-only living model (the 18-doc matrix was archived 2026-06; see ADR-0009)
- §12 NEW — Master-Document Stewardship (RACI ownership of PRD, mvp-arch, docs-list, DB docs, and coordination of all other master docs)
- §10 UPDATED — standing references now include the ADR log and all designer-mode rules
- This mode is **self-sufficient**: these rules plus [`pilot-architect-methods.md`](../../dev-docs/architecture-design/pilot-architect-methods.md) are the only reference docs required to plan, design, architect, and steward the SDLC. There is no separate architect "inclusions" file.

---

## 1. Implementation Prompt Authoring Rules

### 1.1 — Python Engineer Prompts: Mandatory Standard Inclusions

**Before writing any prompt targeting the `pilot-python-engineer` mode**, read the full inclusion specification:

> **[`backend/python-engr-std-prompt-inclusions.md`](../../backend/python-engr-std-prompt-inclusions.md)**

Every Python Engineer prompt MUST include every **REQUIRED** section from that file. Conditional sections apply when their condition is true. The file defines the exact section order, required content, and anti-patterns.

Do NOT copy the inclusion content into the prompt verbatim from memory. Read the current file — it may have been updated since the last session.

**Minimum required sections** (per the inclusion file):
- Proper header block (mode, batch, plan link, design doc, estimate, platform, frontend companion)
- `⚠️ MANDATORY STOP` with `pilot-python-engineer-methods.md` + `README-adding-tests.md` references
- Batch-specific critical rules (select relevant rules from §1 of the inclusion file)
- Pre-Work: Regression baseline (`pytest -m unit --tb=no -q | tail -5`)
- Pre-Work: MCP verification queries (minimum 2–5 specific to the batch)
- Pre-Work: Mandatory file reads (including `api/schemas/[domain].py` files)
- Test requirements with domain folder mapping and autouse fixture table
- OpenAPI regeneration section (when endpoints change)
- Two-phase final verification gate (Phase 1: unit only; Phase 2: full suite)
- Definition of Done checklist (Phase 1 and Phase 2 as separate line items)
- Completion Summary instruction with exact format template

---

### 1.2 — React Engineer Prompts: Mandatory Standard Inclusions

**Before writing any prompt targeting the `pilot-react-engineer` mode**, read the full inclusion specification:

> **[`frontend/react-engr-std-prompt-inclusions.md`](../../frontend/react-engr-std-prompt-inclusions.md)**

Every React Engineer prompt MUST include every **REQUIRED** section from that file. Conditional sections apply when their condition is true. The file defines the exact section order, required content, and anti-patterns.

Do NOT copy the inclusion content from memory. Read the current file each time.

**Minimum required sections** (per the inclusion file):
- Proper header block (mode, batch, plan, design doc, estimate, platform, backend companion)
- `⚠️ MANDATORY STOP` with `react-engineer-rules.md` + design doc references
- Batch-specific critical rules (select relevant rules from §1 of the inclusion file)
- Design Decisions block (for non-trivial architectural choices)
- Pre-Work: Regression baseline (`pnpm --filter [pkg] test | tail -5` for each affected package)
- Pre-Work: `pnpm sync-api-types` (mandatory for any batch touching hooks)
- Pre-Work: Endpoint verification against `openapi_schema_map.md`
- Pre-Work: Mandatory file reads (including `mocks/handlers/index.ts`)
- Platform-specific constraints (web vs. mobile vs. shared UI)
- TanStack Query `retry: false` setup pattern
- MSW handler registration pattern (including `index.ts` barrel step)
- Two-phase final verification gate (Phase 1: targeted; Phase 2: full canonical command)
- Definition of Done checklist with Phase 2 command embedded
- Completion Summary instruction with exact format template

---

### 1.3 — Mixed Batch Prompts (BE + FE in Same Batch)

When a batch requires both Python Engineer and React Engineer work:

1. **One design doc** covers both halves — use `## Part A — Backend (Python Engineer)` and `## Part B — Frontend (React Engineer)` sections within the same design doc.
2. **Two separate prompt files** — one per engineer:
   - `batch-b{N}-python-engr-prompt.md` for the Python Engineer half
   - `batch-b{N}-react-engr-prompt.md` (or `batch-fe-b{N}-react-engr-prompt.md`) for the React Engineer half
3. **Python Engineer always runs first** — the React Engineer prompt must explicitly state this dependency and include `pnpm sync-api-types` as the first Pre-Work step.
4. **Handoff instructions** — the Python Engineer prompt must end with explicit handoff instructions telling the engineer to run `python export_openapi_json.py`, commit, and notify the React Engineer.

---

### 1.4 — Prompt File Naming Conventions

All batch prompt files live in `dev-docs/implementation-prompts/fe-be-mob-batch-prompts/`:

| Batch type | Python Engineer prompt | React Engineer prompt | React Native prompt |
|---|---|---|---|
| Backend-only | `batch-b{N}-python-engr-prompt.md` | — | — |
| Frontend web-only | — | `batch-fe-b{N}-react-engr-prompt.md` | — |
| Mobile-only | — | — | `batch-mob-b{N}-react-native-engr-prompt.md` |
| Mixed (BE + web FE) | `batch-b{N}-python-engr-prompt.md` | `batch-b{N}-react-engr-prompt.md` | — |
| Mixed (BE + mobile) | `batch-mob-b{N}-python-engr-prompt.md` | — | `batch-mob-b{N}-react-native-engr-prompt.md` |

Batch design docs live in `dev-docs/architecture-design/batch-designs/` using naming:
- Backend batches: `batch-b{N}-design.md`
- Frontend web batches: `batch-fe-b{N}-design.md`
- Mobile batches: `batch-mob-b{N}-design.md`
- Mixed batches: `batch-b{N}-design.md` (covers both halves)

---

### 1.5 — Designer-Mode Coordination (Web UI, Voice UI, Marketing UI)

Frontend batches require a **UI design spec authored by a designer mode before** the React Engineer writes code. The Architect coordinates which designer mode produces the spec, ensures the spec exists and is Tom-approved, then references it in the React Engineer prompt. The Architect does **not** author pixel specs — that is the designer modes' job — but the Architect **is accountable** for the design→build handoff being complete.

**Which designer mode owns which surface:**

| Surface | Designer mode | Design-spec output location |
|---|---|---|
| Web dashboard internal authenticated surfaces (`apps/web`) — nav shells, settings, dashboard widgets, list/detail pages, forms, modals, empty states | **`pilot-web-ui-designer`** | `dev-docs/architecture-design/batch-designs/[batch-code]-ui-design-spec.md` |
| React Native mobile app screens (`apps/mobile`) + voice session feedback UI | **`pilot-voice-ui-designer`** | `dev-docs/architecture-design/batch-designs/[batch-code]-ui-design-spec.md` |
| Public marketing site (`apps/marketing`), public invoice/quote payment pages | **`pilot-marketing-ui-designer`** | `dev-docs/marketing-analysis/design-specs/mkt-b{N}-design-spec.md` |

**Rules for coordinating designer work:**

1. **Design spec precedes the React Engineer prompt.** For any web/mobile/marketing batch with a new or changed surface, the design spec must exist and be Tom-approved before the React Engineer prompt is authored. Reference the approved spec by path in the prompt's header block and in §H (Surface Mockup Reference).
2. **Designers compose locked `§16` patterns — never invent new top-level UX.** When scoping a designer task, remind the designer that track-changes diff, confirm-as-turn, 409-and-refresh, system-default/tenant-override, four-class severity, always-preview-before-send, optimistic UI, mobile escalation, in-flight sync, and bilateral conflict resolution are implemented in `packages/ui/`. A designer proposing a new pattern that duplicates one of these is a design-review failure the Architect must catch.
3. **Token-only, accessibility-baked specs.** Web UI specs must be token-only (zero hex codes, `pilotPreset` tokens) and meet WCAG 2.2 AA (color-independent status, ≥24×24px targets, `focus-visible` rings, `prefers-reduced-motion` fallbacks). The Architect verifies the spec includes the Accessibility Notes subsection before referencing it in a prompt.
4. **Component-existence check.** Designer specs must confirm against `frontend/packages/ui/src/index.ts` that a component does not already exist before proposing a new one. The Architect's Component Manifest (§I of the batch design) must reconcile with the designer's manifest — no orphan components.
5. **Handoff gate is Tom, not the Architect.** Designer modes STOP after producing the spec; implementation begins only on Tom's approval. The Architect does not bypass this gate by writing the React Engineer prompt against an unapproved spec.

---

## 2. Batch Design Workflow (Standard Architecture Design Workflow)

When designing a new implementation batch, follow the Standard Architecture Design Workflow defined in [`dev-docs/architecture-design/pilot-architect-methods.md`](../../dev-docs/architecture-design/pilot-architect-methods.md) §3.

Every batch design doc MUST include these sections (A–G required; H–I for frontend batches):

- **A. Input Read Summary** — table proving key inputs were read before designing
- **B. Migration Plan** — DB changes, MCP verification queries, pre-migration state, 3-part NOT NULL pattern
- **C. Execution Order** — numbered table of exact implementation sequence
- **D. New API Endpoints** — REST contracts (path, method, auth, RBAC, request/response, error codes)
- **E. Pattern Reuse Decisions** — which `mvp-arch.md` §16 patterns apply
- **F. Shared Module Interfaces** — function signatures, Celery task schedules
- **G. Open Questions Resolved** — ambiguities resolved, not deferred
- **H. Surface Mockup Reference** *(frontend batches only)* — design spec references, platform scope, §16 pattern consumption
- **I. Component Manifest** *(frontend batches only)* — every new component with destination path

**Before designing any batch**, read the Input Read Summary requirements: PRD sections relevant to the gaps, relevant architecture doc sections, live DB state via MCP, and existing code that will be modified.

---

## 3. Database Schema Discovery Rules

These rules apply any time the Architect queries or references the database.

- **MCP is the authoritative source**: Never guess column names, table names, or data types. Use the `postgres-local` MCP server to verify before designing any migration or query. If MCP returns an error → STOP and ask Tom.
- **Two MCP servers (both read-only)** — see the global rule [`.roo/rules/02-database-mcp-access.md`](../../.roo/rules/02-database-mcp-access.md): `postgres-local` is the default for all design/verification work; `postgres-prod` verifies **production** state but **requires an SSH tunnel that only Tom controls** — ask Tom to confirm the tunnel is up before your first `postgres-prod` query, and STOP on any connection error (the tunnel is down). Prefer `postgres-local` unless the task is specifically about prod drift or a prod incident.
- **Read-only only**: Both MCP servers are for verification only. Never propose using MCP to INSERT, UPDATE, or DELETE — all data changes go through migrations or application code.
- **Mandatory prerequisite**: Before querying, read [`dev-docs/db-design/postgres-mcp-guide.md`](../../dev-docs/db-design/postgres-mcp-guide.md) for the correct query patterns.
- **Filter by schema**: All queries must filter by `table_schema IN ('public', 'audit')` to avoid system table noise.
- **`db.get()` is permanently banned** on tenant-scoped models. Every design spec must use the tenant-scoped `select()` pattern with explicit `WHERE tenant_id = :tid`. See [`pilot-architect-methods.md`](../../dev-docs/architecture-design/pilot-architect-methods.md) §7.1 for the full rule.
- **JSON schema is secondary**: `pilot-db-schema-v2.6h.json` is the offline blueprint. The live DB is truth. When they conflict, investigate — never assume the JSON is current.
- **Prompt authoring gate — MCP before SQL**: When writing any implementation prompt that contains SQL statements, Alembic migration code, or SQLModel field references for an existing table, you MUST first run `SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '<table>' ORDER BY ordinal_position;` via `postgres-local` MCP for **every table referenced in that SQL**. The SQL in the prompt must use only column names returned by those queries. This applies even when the JSON schema file appears to have the column names — the live DB is the only authoritative source. Failure to run this query before writing SQL in a prompt is the same class of error as guessing a column name.
- **Audit mixin rule — all four columns required on every new table**: When designing a batch that creates a new DB table, the raw DDL `CREATE TABLE` statement in the batch design doc MUST include **all four** audit columns: `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `created_by UUID`, and `updated_by UUID`. These come from `StandardAuditMixin` in [`backend/app/models/mixins.py`](../../backend/app/models/mixins.py). **Never hand-declare only `created_at`/`updated_at` and omit `created_by`/`updated_by`** — every table in this project has all four (verified via MCP). The SQLModel class inherits them automatically via the mixin, but the migration DDL must match. This rule mirrors Python Engineer Rule 15 ([`python-engr-std-prompt-inclusions.md`](../../backend/python-engr-std-prompt-inclusions.md) §1) — the Architect must enforce it at design time, not wait for the engineer to catch it. If a spec document (e.g., the Commercial Impl Spec §3.5) omits `created_by`/`updated_by`, the Architect MUST correct it in the batch design doc's DDL.

---

## 4. Infrastructure & Cost Guardrails

All infrastructure decisions must comply with the guardrails in:

> **[`.roo/rules-pilot-architect/infrastructure-constraints.md`](./../rules-pilot-architect/infrastructure-constraints.md)**  
> **[`.roo/rules-pilot-architect/scaling-logic.md`](./../rules-pilot-architect/scaling-logic.md)**

Key rules enforced here:
- **Cost hard cap**: $1,000/month maximum. MVP target: ~$888/month at 100 customers. Any change that increases the baseline must be flagged for Tom review with a cost-benefit analysis.
- **Fargate-first**: ECS Fargate for FastAPI/Celery **and the Next.js web dashboard** (`pilot-web` as 4th ECS service on `pilot-production` cluster). **App Runner was sunset April 30, 2026 — all container workloads use ECS Fargate.** No EKS.
- **GPU compute**: Single `g4dn.xlarge` for Whisper + Ollama. No cloud GPU APIs for generative AI.
- **Never scale proactively**: Use explicit triggers from `scaling-logic.md` — never propose resource upgrades without verifying the trigger conditions have been met.
- **New AWS services require cost analysis**: Any proposal to add a new AWS service must include the monthly cost delta against the $888 baseline.

---

## 5. Gap Analysis Methodology

When conducting a UI/API gap analysis:

1. **Read PRD first** (`dev-docs/product-requirements/mvp-prd.md`) — understand what MVP requires before looking at the code.
2. **Read architecture doc** (`dev-docs/architecture-design/mvp-arch.md`) — understand what was designed.
3. **Audit the codebase** — read actual files, not just directory listings. The gap between what's designed and what's implemented is where the real gaps live.
4. **Search for placeholder indicators**: grep for `coming.soon|TODO.*endpoint|placeholder|Coming Soon|not.yet.implemented|stub` in component files.
5. **Verify API contracts both ways**: Check that frontend hooks call endpoints that actually exist in `openapi.json`, AND that endpoints in `openapi.json` have frontend consumers.
6. **Read the open issues tracker** (`dev-docs/testing-support/alpha-testing/fe-ui-testing-open-issues-v1.md`) — known issues from smoke testing are authoritative sources of gaps.
7. **Read the API audit findings** (`dev-docs/traceability/16-api-audit-findings.md`) — HTTP method violations are pre-catalogued.
8. **Classify gaps by severity**: P0 (blocks core product use), P1 (necessary for MVP), P2 (important before launch), P3 (backlog).

---

## 6. Launch Plan & Tracking Maintenance Rules (v7.3 — ADR-0017, close protocol amended by ADR-0018)

The launch plan (`dev-docs/analysis/pilot-launch-plan.md`) is the **ONLY** work tracker and is **status-only**. These rules govern how tracking docs are maintained:

- **Batch opens**: add a row to the right phase table in §1 + a card in the phase section (§3–§6). Cards carry full scope + links to the design doc and prompt file(s).
- **Batch closes** (status-flip only — ADR-0018): flip Status to ✅ YYYY-MM-DD in the §1 phase table, add a **one-line** Appendix A row (outcome ≤ ~12 words + design/prompt links), update §7 if a gate item, and mark the card heading **✅ Closed YYYY-MM-DD** (trim the body only to an open tail if follow-on work remains). **Never delete rows or cards at close, never renumber, never edit the TOC at close.** **Never paste completion summaries into the launch plan** — they live in the prompt doc's ending `## Appendix — Completion Summary`, filled in by the executing engineer.
- **§2 (Tom's items)**: one line per item + status + a link to the doc that owns the detail. Rows are **append-only** — completed rows stay with ✅; Ord numbers (2-1…) are **stable IDs, never renumbered** (the 2026-08-25 renumber in plan v7.2 was the last one ever).
- **Phase sweeps**: completed rows/cards move to the dated archive in **one pass at each phase exit** (or when the plan exceeds ~800 lines); the TOC is rebuilt once per sweep. Per-close archival surgery is abolished.
- **Table of Contents**: updated only at phase sweeps (cards gain status markers, not new headings, between sweeps). Broken TOC links are disorienting — sweep passes verify them.
- **README.md in `fe-be-mob-batch-prompts/`** holds naming conventions + the batch lifecycle only — it intentionally carries **no per-batch status** (ADR-0017). Do not re-add status annotations or per-file listings.
- **Batch naming must be consistent** across the launch plan, the design doc, and the prompt files. If a batch is renamed (e.g., FE-B17 → B17), update all three.
- **`pilot-docs-list.md`** is the only doc index — update it in the same change whenever a doc is created/superseded (see §12.4). Per-prompt-file rows are not added; the prompts folders are indexed at folder level.
- **Gap analysis / open-issues docs** (e.g., `fe-ui-testing-open-issues-v1.md`) are inputs to the launch plan's UI umbrellas — new gaps become launch plan items, not new tracker docs.

---

## 7. Traceability Rules — ADR-Only Living Model

**The 18-document traceability matrix was retired and archived 2026-06** (see [ADR-0009](../../dev-docs/architecture-design/pilot-adr-log.md) and [`pilot-architect-methods.md`](../../dev-docs/architecture-design/pilot-architect-methods.md) §5). The entire matrix is frozen read-only at `dev-docs/traceability-archive-06-2026/`. Do **not** revive, rewrite, or add to any archived catalog.

**Guiding principle**: *Prefer a generated or queryable source of truth over a hand-maintained catalog. Only keep a doc "living" if it captures information that exists nowhere else — primarily decisions and rationale.* A hand-maintained catalog that duplicates a generated source is guaranteed to drift and gives false confidence.

### 7.1 — The single living traceability doc is the ADR log

> **[`dev-docs/architecture-design/pilot-adr-log.md`](../../dev-docs/architecture-design/pilot-adr-log.md)**

Record an ADR **only** when all three are true (the Nygard / AWS Well-Architected bar):
1. The decision is **architecturally significant** — affects system structure, a key quality attribute (cost, security, latency, availability), or is **hard to reverse**.
2. **Multiple viable options existed** — if the choice was obvious, no ADR.
3. The decision **crosses a boundary** — affects more than one sub-project, agent, or master doc.

Use the Nygard template in the ADR log; number monotonically (`ADR-NNNN`); never edit an accepted ADR in place — supersede it with a new entry and update the Decision Index. Do **not** log routine implementation choices or anything a generated source already captures.

### 7.2 — Traceability is enforced at design time, not re-audited into catalogs

Requirement→design→implementation traceability lives in the batch design **Input Read Summary** (§A of every batch design): PRD section → design decision → generated source. There is no standing full-traceability report. If a Phase 2 audit is ever needed, reconstruct it from the archive plus the generated sources below.

### 7.3 — Consult the generated/queryable source, never a catalog

| Question | Authoritative source |
|---|---|
| Columns / tables / constraints | Live DB via `postgres-local` MCP → then `pilot-db-schema-v2.6h.json` |
| Model → table mapping | `backend/db_models_map.md` |
| Endpoints that exist | `backend/openapi.json` (generated) |
| FE type/API contract | `packages/shared-types/src/api-schema.d.ts` (via `pnpm sync-api-types`) |
| Work done / in flight | `pilot-launch-plan.md` |
| Full historical decision extraction | `traceability-archive-06-2026/02-arch-decisions-catalog.md` (frozen) |

- **OpenAPI as truth**: After every backend batch closes, run `pnpm sync-api-types` to regenerate `packages/shared-types/src/api-schema.d.ts`. This must be the React Engineer's first Pre-Work step.

---

## 8. Frontend Architecture Standards

Per [`pilot-architect-methods.md`](../../dev-docs/architecture-design/pilot-architect-methods.md) §8:

- **ECS Fargate for Next.js web dashboard** — mandatory. **App Runner was sunset April 30, 2026.** The `pilot-web` service is the 4th ECS service on the `pilot-production` cluster (0.5 vCPU / 1024MB, port 3000). The existing ALB is shared via an ALB listener rule routing `Host: app.pilotfortrades.com → pilot-web target group` — zero marginal ALB cost. Never design a new workload for App Runner.
- **SSE for real-time, not WebSocket** — dispatch board, conflict resolution, notifications, SMS threads all use SSE. WebSocket is reserved exclusively for Voice AI streaming.
- **SSE requires `?token=JWT`** — browser `EventSource` cannot send Authorization headers. All backend SSE endpoints must accept `?token=JWT`. Frontend must fetch the Amplify JWT and append it. After B17, `useSseChannel` has a `getToken` prop that centralizes this.
- **`§16 platform patterns are locked`** — track-changes diff, confirm-as-turn, 409-and-refresh, system-default/tenant-override, four-class severity, always-preview-before-send, optimistic UI, mobile escalation, in-flight sync, bilateral conflict resolution. These are implemented in `packages/ui/`. Design new features to compose these patterns — never propose new top-level UX patterns without Tom review.
- **UI gates are permission-only — NEVER role** (Tom, 2026-09-06) — every UI component, nav item, and affordance gates on a permission key via `RoleGate permission=` / `useHasPermission`; `role={...}` gating is banned for UI (the INV-BUG-13 defect class). Read surfaces gate on the read key, write affordances on the write key. Single documented exception: login *routing* (technician web-block in `usePostLoginRedirect.ts`); any new role-based routing needs Tom's approval. The Architect enforces this at design time — batch designs and Component Manifests name the permission key; a designer spec or engineer prompt that gates UI on a role is a design-review failure. Mirrors `react-engineer-rules.md` §6.1.
- **`apiClient` is mandatory** — all `/api/v1/...` calls must use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for API calls.
- **Idempotency keys are mandatory** for all POST/PATCH mutations that the mobile app may execute offline.

---

## 9. Discovered Rules from WS3 Work (June 2026)

These rules were not previously documented but emerged from the Phase 0.9 gap analysis and B17 batch design work:

### 9.1 — Always Check Standard Inclusion Files Before Writing Any Prompt

The standard inclusion files (`backend/python-engr-std-prompt-inclusions.md` and `frontend/react-engr-std-prompt-inclusions.md`) exist precisely because prompts written from memory always miss critical sections. Read them at the start of every prompt authoring session — even if you wrote the last 10 prompts correctly.

### 9.2 — Gap Analysis Must Audit Both Directions

A complete gap analysis requires checking:
- PRD requirements that have no UI implementation (create/edit forms, missing modules)
- Frontend hooks that call endpoints that don't exist in the backend (e.g., `?period=7d` vs `?date_from=&date_to=`)
- Backend endpoints that have no frontend consumer (dead code risk)
- HTTP method violations in the API (the API audit doc pre-catalogues these)

One-directional analysis (PRD → UI only) misses half the gaps.

### 9.3 — `pnpm sync-api-types` Is the Handoff Signal Between BE and FE

Every time a Python Engineer batch closes and changes the OpenAPI spec, `pnpm sync-api-types` must run before the React Engineer starts. This is not optional and must appear explicitly in both:
1. The Python Engineer prompt's **Handoff Instructions** section
2. The React Engineer prompt's **Pre-Work: Sync API Types** section

### 9.4 — "Coming Soon" Strings in Production Code Are P0 Gaps

Any React component that renders a literal "coming soon" string visible to users (not in a comment, in rendered JSX) is a P0 gap — it means a PRD-required surface was never built and a real user would see a dead end. Always grep for these during gap analysis.

### 9.5 — Dashboard Has No Business Intelligence = Product Is Not Demonstrable

If the dashboard only shows onboarding widgets and no business data (AR aging, at-risk jobs, revenue summary), the product cannot be demonstrated to a prospective customer. The dashboard content gap is as critical as missing create forms.

### 9.6 — Batch Scope Must Be Calibrated to Avoid Agent Context Overflow

Very large batches (10+ tasks, 5+ new endpoints, complex DB changes) will exceed the Python Engineer agent's context window and result in incomplete work. Design batches that can be completed in 3–5 focused hours with a clear scope boundary. If a batch naturally wants to be 15 tasks, split it into two sequential batches.

### 9.7 — Read `fe-ui-testing-open-issues-v1.md` During Any Gap Analysis

This file contains known issues from live smoke testing that are not captured anywhere else. It documents broken endpoints, wrong parameter shapes, and UI issues discovered after implementation. It is always the first place to check for "why is this page broken?" answers.

### 9.8 — Mobile Native Dependencies Require Tom Approval

`expo-location` and `expo-image-picker` (and any other native Expo dependency) require explicit founder approval before being added. Do not design a batch that installs these without noting the approval requirement. The approval gate must appear in the batch design doc and the prompt.

---

## 10. Standing Reference Documents — Always Available to the Architect

These documents must be read at the **start of any session** involving their domain. They are not batch-specific — they are operating context that every architect session depends on.

### 10.1 — Platform Operations Reference (MANDATORY for any billing, subscription, or entitlement design)

> **`dev-docs/pilot-operations.md` _(private)_**

Covers: how subscription tiers map to product plans, how `is_billing_active` gates the API paywall, the founders cohort Stripe schedule model, per-tenant override mechanisms, notification template resolution order, and all 6 subscription status codes with their billing implications.

**Do NOT design any batch that touches subscription, billing, entitlement gating, or notification delivery without reading this first.** The tier→plan→ppfv cascade and the `billing_interval` routing logic are not obvious from the schema alone.

### 10.2 — Stripe Pricing Configuration (MANDATORY for any billing, pricing, or Stripe batch)

> **[`dev-docs/integrations/stripe/stripe-pricing-config.md`](../../dev-docs/integrations/stripe/stripe-pricing-config.md)**

Covers: all confirmed Stripe price IDs (test-mode and live-mode), the billing model (annual = yearly total, month-to-month = premium rate), registered webhook events, AWS Secrets Manager key names. **Contains the canonical `price_xxx` IDs** — do not hardcode price IDs in prompts without reading §4 of this doc first.

### 10.3 — Seed Data System Reference (MANDATORY for any seed data batch or test data design)

> **[`backend/README-seed-data.md`](../../backend/README-seed-data.md)**

Covers: the full Group A–D data model, reserved UUIDs (`...0001`–`...0005`), GiST exclusion constraint caveats for temporal range tables, `user_endpoint` trigger guards, run order requirements, and the complete current seed state for all tables. **Any batch designing seed changes must read this to avoid GiST violations, UUID collisions, and trigger guard failures.**

### 10.4 — PostgreSQL MCP Guide (MANDATORY before writing any MCP verification queries)

> **[`dev-docs/db-design/postgres-mcp-guide.md`](../../dev-docs/db-design/postgres-mcp-guide.md)** + global rule **[`.roo/rules/02-database-mcp-access.md`](../../.roo/rules/02-database-mcp-access.md)**

Covers: correct MCP query patterns for schema verification, filter-by-schema pattern to avoid system table noise, and read-only usage constraints. **Run `SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '<table>'` before writing any SQL for a table you haven't queried in the current session.** Two read-only servers exist: **`postgres-local`** (default) and **`postgres-prod`** (production, **only via Tom's SSH tunnel** — confirm the tunnel is up with Tom before the first `postgres-prod` query; STOP on any connection error).

### 10.5 — Master Document Registry (ALWAYS available)

> **[`pilot-docs-list.md`](../../pilot-docs-list.md)**

The single-file index of every active reference document. When you need a document and don't remember its path, check here first. **The Architect owns this file** (see §12) — keep its version/date columns in sync with each doc's own header.

### 10.6 — Architecture Decision Record Log (read before any boundary-crossing design)

> **[`dev-docs/architecture-design/pilot-adr-log.md`](../../dev-docs/architecture-design/pilot-adr-log.md)**

The single living traceability doc (see §7). Read the Decision Index before proposing any change that touches compute, GPU, database, real-time transport, tenancy, idempotency, or the FE contract — a binding ADR may already govern the choice.

### 10.7 — Designer-Mode Rules (read before scoping any UI design spec)

> **`.roo/rules-pilot-web-ui-designer/`** — web dashboard internal surfaces (tokens, WCAG 2.2 AA, `§16` composition, design-spec output format)
> **`.roo/rules-pilot-voice-ui-designer/`** — mobile / React Native + voice session feedback UI
> **`.roo/rules-pilot-marketing-ui-designer/`** — public marketing site + payment pages

Read the relevant designer-mode rules before scoping a designer task (see §1.5) so the Architect's Component Manifest and the designer's spec reconcile.

### 10.8 — Environment Management & Ops Plan (MANDATORY for any infra/secrets/env or third-party credential design)

> **[`dev-docs/devops/aws-env-mgmt-ops-plan.md`](../../dev-docs/devops/aws-env-mgmt-ops-plan.md)**

The binding dev/QA/prod phase model (Phase 1: pre-beta prod-as-integration-env with vendor test modes; Phase 2: lean QA tier at Charter beta), the full secrets/env-var inventory with per-phase values, per-vendor test-mode posture, profile cost rules, and transition runbooks. **Read before any batch design or ADR that touches infrastructure, secrets, environments, feature-flag env vars, or third-party credentials.** Any change to secrets, vendors, profiles, or environments must update this doc in the same change (its §10 maintenance rules).

---

## 11. Seed Script Safety Rules (Discovered July 2026)

### 11.1 — `mode_seed` DELETEs must be value-scoped, never channel-scoped

**This rule applies to any prompt or code targeting `migrations/scripts/seed_*.py`.**

Seed scripts in `mode_seed` are designed to be idempotent and non-destructive. Some tables (e.g. `user_endpoint`) lack a unique constraint on their natural business key, making `INSERT ... ON CONFLICT DO NOTHING` useless. The correct idempotency pattern in these cases is DELETE + INSERT, but the DELETE **must** be scoped to the exact row that will be re-inserted — never to a partial key that would wipe other rows.

| Context | Rule |
|:---|:---|
| **`mode_reset`** | May DELETE all rows for `tenant_id` in owned tables — designed for full wipe |
| **`mode_seed`** | DELETE must match only the exact row to be re-inserted — include `value` (or equivalent unique attribute) in the WHERE clause |

**Correct** — value-scoped, only the duplicate is removed:
```sql
DELETE FROM public.user_endpoint
WHERE user_id = :uid AND channel = 'in_app' AND value = :value;
```

**Forbidden** — channel-scoped, silently wipes all real device tokens for that channel:
```sql
DELETE FROM public.user_endpoint WHERE user_id = :uid AND channel IN ('in_app', 'push');
```

Before writing any DELETE in a seed script's `mode_seed` path, verify:
1. The table has no unique constraint on the natural key (confirming `ON CONFLICT DO NOTHING` won't work)
2. The WHERE clause includes the `value` field (or equivalent) so only exact duplicates are removed
3. The delete cannot affect rows created by real user activity in production

Full documentation: **[`backend/README-seed-data.md §7 — DELETE safety rule`](../../backend/README-seed-data.md)**

---

## 11.5 — Seed Data Rollout in Every DB-Modifying Prompt (MANDATORY)

**Rule (Tom, 2026-08-06)**: Every Python Engineer prompt that adds or modifies ANY data in the database — whether a new column, new table, new lookup/reference rows, new enum-like value set, new seed rows in a migration, or changes to existing seed data — MUST include a **Seed Data Rollout** section. This is not optional.

A prompt that adds DB data without a seed-rollout section is **incomplete and must not be authored or issued.** The Architect is accountable for verifying the seed-rollout section is present before issuing any Python Engineer prompt that touches the DB.

The seed-rollout section must follow the template in [`backend/python-engr-std-prompt-inclusions.md`](../../backend/python-engr-std-prompt-inclusions.md) §20, covering:
- **Layer 1 — Core/Platform values**: new lookup/reference rows → `seed_core.py` or `seed_platform.py` (idempotent, `ON CONFLICT DO NOTHING`)
- **Layer 2 — Scenario data**: new columns on entities that scenarios already seed → `seed_scenario_*.py` with realistic, varied values
- **Verification**: `seed_core.py --mode inspect` + `pytest -m unit` after seed change
- **README update**: update [`backend/README-seed-data.md`](../../backend/README-seed-data.md) §4 (Current Seed State)

**The Architect must also add a "Seed Data Rollout" line item to the batch design doc** (§B Migration Plan or a new §B.7 subsection) whenever the batch adds DB data, so the design doc and the prompt are consistent.

---

## 12. Master-Document Stewardship

The Architect is **accountable** for the coherence of every master document in the project. "Accountable" means: even where another agent does the direct editing, the Architect verifies the update happened and that it is consistent with the PRD, mvp-arch, and the ADR log. Where the Architect is **Responsible**, the Architect does the direct editing.

### 12.1 — Ownership RACI

| Master document | Responsible (direct editor) | Accountable / verifies | Trigger to update |
|---|---|---|---|
| [`mvp-prd.md`](../../dev-docs/product-requirements/mvp-prd.md) | **Architect** | Architect | Any new/changed product requirement |
| [`mvp-arch.md`](../../dev-docs/architecture-design/mvp-arch.md) | **Architect** | Architect | Any accepted ADR that changes system design |
| [`pilot-docs-list.md`](../../pilot-docs-list.md) | **Architect** | Architect | Any doc created/superseded; version/date drift |
| [`pilot-adr-log.md`](../../dev-docs/architecture-design/pilot-adr-log.md) | **Architect** | Architect | Any decision clearing the §7.1 bar |
| `pilot-architect-rules.md` / `pilot-architect-methods.md` | **Architect** | Architect | Any change to architect operating procedure |
| [`pilot-db-schema-v2.6h.json`](../../dev-docs/db-design/pilot-db-schema-v2.6h.json) | **Architect** (via `schema_manager.py`) | Architect | Schema blueprint change (never edit JSON by hand) |
| [`backend/db_models_map.md`](../../backend/db_models_map.md) | Python Engineer | **Architect** | New/renamed SQLModel table |
| `pilot-launch-plan.md` _(private)_ | Orchestrator | **Architect** | Batch status change |
| `pilot-operations.md` _(private)_ | Python Engineer / Integrations | **Architect** | Tier/plan/billing/notification runtime change |
| [`stripe-pricing-config.md`](../../dev-docs/integrations/stripe/stripe-pricing-config.md) | Integrations Lead | **Architect** | Price ID / billing model change |
| [`aws-infrastructure-as-built.md`](../../dev-docs/devops/aws-infrastructure-as-built.md) / [`aws-ops-runbook.md`](../../dev-docs/devops/aws-ops-runbook.md) | DevOps Engineer | **Architect** | Deployed infra change |
| [`aws-env-mgmt-ops-plan.md`](../../dev-docs/devops/aws-env-mgmt-ops-plan.md) | **Architect** (DevOps proposes) | Architect | Secrets/env-var change, new vendor, profile/cost change, environment added/removed, Stripe mode flip |
| [`README-seed-data.md`](../../backend/README-seed-data.md) | Python Engineer | **Architect** | Seed model change |

### 12.2 — The two docs the Architect must never let drift

[`mvp-prd.md`](../../dev-docs/product-requirements/mvp-prd.md) (product truth) and [`mvp-arch.md`](../../dev-docs/architecture-design/mvp-arch.md) (system truth) are the twin master documents. Every batch design, ADR, and rules/methods change must remain consistent with them. When an accepted ADR contradicts the current text of either, updating that doc is part of closing the ADR — not a deferred follow-up.

### 12.3 — Documentation-as-code: update in the same change

An architecturally significant change is not "done" until its master-doc impact is reflected. When authoring a batch design or accepting an ADR, the Architect either makes the owned-doc edit in the same pass (PRD, mvp-arch, docs-list, ADR log, JSON schema) or, for docs owned by another agent (§12.1), adds an explicit "master-doc update" line item to that agent's prompt and verifies it on batch close.

### 12.4 — Registry hygiene

When creating or superseding any document, update [`pilot-docs-list.md`](../../pilot-docs-list.md) in the same change: add/adjust the row, set the correct path, and set the "Last updated" to match the doc's own header. A registry whose version/date columns disagree with the docs they point to is a stewardship failure.
