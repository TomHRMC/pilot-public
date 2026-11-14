# Architect Design Sprint — Seed Data SD-05 through SD-10

**Mode**: pilot-architect  
**Type**: Design sprint — 6 design tasks, no code written here  
**Output**: 1 design doc + updates to 2 plan documents  
**Spec source**: `backend/migrations/scripts/README-seed-data.md` §10 (SD-05 through SD-10)  
**Date assigned**: 2026-07-06

---

## Context

SD-01 through SD-04 (implementation) are complete as of 2026-07-06. SD-05 through SD-10 are all **design tasks** — the Architect makes decisions, produces a design doc, and flags which tasks require a Python Engineer implementation batch. Some tasks require Tom's decision before implementation begins (specifically SD-07 and SD-08).

The goal of this sprint is to close the design gap so each of SD-05 through SD-10 has a clear decision, owner, and either an "approved for implementation" signal or a "Tom must decide first" blocker documented explicitly.

---

## Pre-Work: What to Read First

Read **all** of the following before writing a single design decision. Do not rely on memory of any prior session.

### Mandatory reads (in order):

1. **`backend/migrations/scripts/README-seed-data.md` §10** — The full spec for SD-05 through SD-10. Every task defines the problem, the design questions, and the implementation requirements. Your job is to answer the design questions.

2. **`dev-docs/analysis/pilot-launch-plan.md` §P1 Seed Data Batch** — Current state of SD tasks and the gate item `"P1: SD-05 through SD-10 design decisions made"` that this sprint must close.

3. **`dev-docs/marketing-analysis/gtm-feature-tier-matrix-v1.md`** — For SD-07: existing competitive analysis of feature tier decisions. Read before designing any product feature set changes.

4. **`dev-docs/traceability/17-cust-comms-templates.md`** — For SD-08: the authoritative spec for MVP customer communication templates. Cross-reference against the live DB before making any copy recommendations.

### MCP verification queries (run before SD-05, SD-06, SD-08, and SD-09 designs):

**SD-05 — Payment refund status:**
```sql
SELECT code, name FROM public.payment_status ORDER BY code;
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment' ORDER BY ordinal_position;
```

**SD-06 — Invoice status:**
```sql
SELECT code, name FROM public.invoice_status ORDER BY code;
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice' ORDER BY ordinal_position;
-- Check whether any invoice reminder Celery task exists:
```
Also search the codebase: `grep -r "invoice" backend/tasks/ --include="*.py" -l`

**SD-08 — Email + notification templates:**
```sql
SELECT template_code, subject, channel FROM public.email_template ORDER BY template_code;
SELECT template_code, channel, body_template FROM public.notification_template ORDER BY template_code;
SELECT code, label, is_active FROM public.customer_comm_template_type ORDER BY code;
```

**SD-09 — Empty functional tables:**
```sql
SELECT COUNT(*) as row_count, 'payment_method' as tbl FROM public.payment_method
UNION ALL SELECT COUNT(*), 'help_article' FROM public.help_article
UNION ALL SELECT COUNT(*), 'help_article_chunk' FROM public.help_article_chunk
UNION ALL SELECT COUNT(*), 'discount_version' FROM public.discount_version
UNION ALL SELECT COUNT(*), 'supplier' FROM public.supplier
UNION ALL SELECT COUNT(*), 'supplier_item' FROM public.supplier_item
UNION ALL SELECT COUNT(*), 'supplier_item_price' FROM public.supplier_item_price
UNION ALL SELECT COUNT(*), 'quote_template' FROM public.quote_template
ORDER BY tbl;

-- For quote_template origin check:
SELECT id, name, created_at FROM public.quote_template ORDER BY created_at;
```

---

## Output: Design Document

Create **one design doc** covering all 6 tasks:

**File path**: `dev-docs/architecture-design/batch-designs/batch-sd-design-sprint-design.md`

The doc must have one section per task (§SD-05 through §SD-10). Each section must answer all design questions posed in the README spec for that task, with a clear disposition:

- **`[APPROVED FOR IMPLEMENTATION]`** — Decision made; Python Engineer can proceed. Include exact schema changes, migration guidance, and which seed script(s) to update.
- **`[TOM MUST DECIDE — BLOCKED]`** — Design work done; specific question(s) for Tom documented before implementation can begin.
- **`[DEFERRED — NOT A LAUNCH BLOCKER]`** — Justified deferral with rationale. Not blocking beta.

Use the **Standard Architecture Design Workflow** sections A–G from `dev-docs/architecture-design/pilot-architect-methods.md` §3 where applicable. For this design sprint, at minimum include:

- **A. Input Read Summary** — table proving key inputs were read before designing each section
- **D. New API Endpoints** — only if any task introduces new endpoints (SD-06 likely does for the overdue derived property)
- **F. Shared Module Interfaces** — for SD-06: Celery task signature for the invoice reminder beat task
- **G. Open Questions Resolved** — document every design ambiguity and how it was resolved

---

## Task-by-Task Design Guidance

### SD-05 — Payment Refund Status Support

The key design question is: **new status codes vs. new columns on `payment`**.

Answer these before writing your decision:
- Stripe's `charge.refunded` webhook fires when a full or partial refund is issued. The payment `status` stays `succeeded` in Stripe's own model — refund state is tracked on a separate `Refund` object. Does our model need to match Stripe's approach?
- Is a partially refunded invoice still considered `paid`? Does the tenant need to see `$150 refunded` on a `$500` invoice that was paid?
- Does the UI (invoice detail page, AR aging) need to surface refund amounts today? Or is this a P2 item?

**Recommended direction to evaluate**: Add `refunded_amount_cents INTEGER DEFAULT 0` + `refunded_at TIMESTAMPTZ` columns to `payment` (tracking state on the row, not a new status). This avoids a new lookup code and keeps Stripe alignment. Evaluate and either confirm or counter with reasoning.

### SD-06 — Invoice Status Alignment + Automated Late Invoice Reminders

Two distinct sub-problems:

**Part A — Status alignment** is a documentation + audit task, not a schema change. The DB codes (`issued`, `writeoff`) are correct. The question is: does the frontend display them correctly? Answer:
- Search `frontend/apps/web/src/` for any hardcoded string `"sent"` or `"overdue"` used as an `invoice_status` filter or display label. Document findings.
- Define the "overdue" derived display rule: `due_at < TODAY AND status_code NOT IN ('paid', 'void', 'writeoff')`. Confirm this is not a DB column.

**Part B — Automated reminders** is a new feature. Answer:
- Does `backend/tasks/` already contain an invoice reminder task? (Check via MCP / codebase grep before designing.)
- If not: design a `send_overdue_invoice_reminders` Celery beat daily task. Which `notification_template` code fires? What reminder schedule (1d, 7d, 14d overdue)?
- Does `invoice` need new columns (`last_reminder_sent_at`, `reminder_count`)? Or track via `notification_log`?
- Should the reminder schedule be tenant-configurable via `platform_setting_catalog`? If yes, which keys?

### SD-07 — Product Feature / Usage Billing Competitive Review

This task requires Tom's decision before any implementation. Your job is to:
1. Read `dev-docs/marketing-analysis/gtm-feature-tier-matrix-v1.md` for the existing competitive analysis.
2. Assess the current 3 features (`voice_ai_minutes`, `qb_sync_operations`, `data_exports`) against what you know about FSM competitor pricing (Jobber, Housecall Pro, ServiceTitan, Workiz) — focus on what features they gate by tier and what usage thresholds trigger upgrades.
3. Produce a **proposed revised feature set** with specific limit values per tier (trial/starter/professional/enterprise). Present as a table.
4. Flag this section as **`[TOM MUST DECIDE — BLOCKED]`** with the specific question: "Do you approve the proposed feature set and limit values before implementation begins?"

Do NOT approve SD-07 implementation yourself. Tom decides.

### SD-08 — Email Template + Notification Template Review

This task requires Tom's copy approval before implementation. Your job is:
1. Query all 16 `email_template` rows and all 9 `notification_template` rows via MCP.
2. For each `email_template`: document `template_code`, `subject`, and whether `html_body` / `plain_text_body` is placeholder stub copy or complete copy. Flag any with `{{name}}` or `Hello, user` placeholder text.
3. For each `notification_template`: document `template_code`, `channel`, and `body_template`. Flag any with placeholder text.
4. Cross-reference against the 13 MVP active `customer_comm_template_type` codes from `dev-docs/traceability/17-cust-comms-templates.md` — identify any gaps.
5. Flag this section as **`[TOM MUST DECIDE — BLOCKED]`** with: "Review and approve the identified stub templates and proposed copy improvements below before implementation begins."

Do NOT write final copy yourself unless it is a clearly non-customer-facing transactional template (e.g., `email_verification`). Flag customer-visible copy for Tom's review.

### SD-09 — Seed Data for Empty Functional Tables

Query the 8 tables via MCP (see pre-work). For each table, write a one-paragraph decision covering:
- What seed data is needed for the feature to be testable end-to-end
- Which script group owns it (Group B `seed_platform.py`, Group C `seed_test_tenant.py`, or Group D new scenario script)
- Any GiST, FK, or unique constraints that affect the insert approach
- Implementation difficulty: Low / Medium / High

Pay special attention to:
- `payment_method`: Spec §B15 says 1 system row needed. Confirm exact columns from live DB before designing.
- `help_article` + `help_article_chunk`: The embedding pipeline requirement is the blocker. Decide whether dev/QA can use pre-computed test vectors or must run the pipeline.
- `quote_template`: Run the MCP origin check query above. If `created_at` matches an Alembic migration timestamp → it belongs in `seed_core.py`. If manually created → decide whether to formalize.
- `discount_version`: Check whether this table uses GiST exclusion like `labor_rate_version`. If yes, same closed-range insertion rules apply.

Mark each table `[APPROVED FOR IMPLEMENTATION]` or `[DEFERRED — NOT A LAUNCH BLOCKER]`.

### SD-10 — Scenario Coverage Analysis + E2E Test Harness

This is the largest design task. Produce:

**Part A — Scenario Coverage Catalog**: For each workflow in the README §10 SD-10 table (16 workflows listed), document:
- Key runtime tables the workflow populates
- Whether an existing seed scenario covers it
- Gap classification: SD-02/03 covers it ✅, planned future script ☐, or no path yet ☐

**Part B — Test Harness Architecture Decision**: Answer the 5 questions from the README spec:
1. What type of harness? (FastAPI integration + Playwright + Maestro hybrid)
2. Seeding strategy for the harness
3. CI/CD integration — what runs on every PR vs. nightly
4. Expected outcome assertion pattern
5. Maintenance strategy

**Deliverable for Part B**: A recommendation (not a full harness design doc — that's a separate batch). The recommendation should fit in 1–2 pages within this design doc. Full harness implementation is a separate batch (Python + QA Engineer) that starts after Tom approves the recommendation.

---

## When Done: Update These Documents

After the design doc is written at `dev-docs/architecture-design/batch-designs/batch-sd-design-sprint-design.md`, update **both** of the following:

### 1. `backend/migrations/scripts/README-seed-data.md` §10

For each task SD-05 through SD-10, update the task header to reflect the design sprint disposition:
- If `[APPROVED FOR IMPLEMENTATION]` → change header to `☐ Approved — Awaiting Python Engineer implementation` and add a one-line "Design decision: [summary]" note below the header.
- If `[TOM MUST DECIDE — BLOCKED]` → change header to `⚠️ Design complete — Awaiting Tom decision` and add the specific decision question.
- If `[DEFERRED]` → change header to `☐ Deferred — [rationale in one sentence]`.

### 2. `dev-docs/analysis/pilot-launch-plan.md`

Update the Beta Launch Readiness Gate row:
```
| **P1**: SD-05 through SD-10 design decisions made (batches assigned or deferred) | Architect + Tom | ☐ |
```
→ Change to ✅ and add a note: `"Design doc: batch-sd-design-sprint-design.md. N tasks approved for implementation; N tasks awaiting Tom decision; N deferred."`

Also update the SD task table in §P1 Seed Data Batch — add rows or notes for SD-05 through SD-10 reflecting their dispositions from the design sprint.

---

## Definition of Done

- [ ] `dev-docs/architecture-design/batch-designs/batch-sd-design-sprint-design.md` created with sections for all 6 tasks
- [ ] Every task has an explicit disposition: `[APPROVED FOR IMPLEMENTATION]`, `[TOM MUST DECIDE — BLOCKED]`, or `[DEFERRED]`
- [ ] All MCP pre-work queries run; no column name or row value guessed from memory
- [ ] SD-07 and SD-08 explicitly flagged as Tom-decision gates with specific questions
- [ ] `README-seed-data.md` §10 SD-05 through SD-10 headers updated to reflect dispositions
- [ ] `pilot-launch-plan.md` Beta Gate row `"SD-05 through SD-10 design decisions made"` updated to ✅
