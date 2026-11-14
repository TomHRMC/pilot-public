# UI Fix Batch 1 — Decisions & Findings Tracker

**Status**: 🔍 Investigation in progress  
**Started**: 2026-07-16  
**Owner**: Tom + Pilot Architect  
**Purpose**: Running log of all UI/backend discrepancies discovered during hands-on UI debugging. Once investigation is complete this doc drives the formal batch design doc(s) and engineer prompts.

> **How to use**: As we walk through each screen/flow and discover gaps, decisions are logged here. Each item gets a severity, affected layer (FE / BE / both), and a decision on the fix approach. No code changes until investigation is complete and batches are scoped.

> ~~**React Engineer handling directly** (not batched here): FIX-002 — Field Issues queue shows "Unknown" for tech name.~~ **RESOLVED — 2026-07-16**: Tom confirmed the tech name (Dev Technician) and operation type are displaying correctly in the UI. The live DB data is clean (`originating_user_id = 00000000-0000-0000-0000-000000000003` = Dev Technician). No fix needed — the "Unknown" fallback in `useFieldIssues.ts` is a safe fallback that isn't triggering in practice.

> **Note — `pay.pilotfortrades.com` does not exist and is not needed**: FIX-003 below documents the seed data correction needed. The real invoice payment URL is `https://app.pilotfortrades.com/i/{signed_token}` — the `/i/[token]` Next.js route is already built and functional.

---

## Table of Contents

- [UI Fix Batch 1 — Decisions \& Findings Tracker](#ui-fix-batch-1--decisions--findings-tracker)
  - [Table of Contents](#table-of-contents)
  - [Severity Key](#severity-key)
  - [FIX-001 — Quote Workflow: `approved` Status Invisible and Unsendable](#fix-001--quote-workflow-approved-status-invisible-and-unsendable)
    - [Context](#context)
    - [Root Cause](#root-cause)
    - [Decision](#decision)
    - [Specific Code Changes Required](#specific-code-changes-required)
  - [FIX-003 — Seed Data: Fictional `pay.pilotfortrades.com` URL in Customer Comms SMS Body](#fix-003--seed-data-fictional-paypilotfortradescom-url-in-customer-comms-sms-body)
    - [Context](#context-1)
    - [Real Invoice Payment Flow (Already Built)](#real-invoice-payment-flow-already-built)
    - [Decision](#decision-1)
    - [Specific Change Required](#specific-change-required)
  - [FIX-004 — Payment Architecture: Stripe Implementation vs PRD Design + Payment Provider Roadmap](#fix-004--payment-architecture-stripe-implementation-vs-prd-design--payment-provider-roadmap)
    - [Current Implementation vs PRD Intent](#current-implementation-vs-prd-intent)
    - [What This Means Today](#what-this-means-today)
    - [Decision — **CONFIRMED 2026-07-16 by Tom**](#decision--confirmed-2026-07-16-by-tom)
    - ["What if a tenant hasn't set up Stripe?" — Confirmed Behavior](#what-if-a-tenant-hasnt-set-up-stripe--confirmed-behavior)
    - [Payment Provider Market Research (Trades Industry)](#payment-provider-market-research-trades-industry)
  - [FIX-005 — Seed Data: Scheduled Jobs Have No Tech Assignments (Dispatch Board Empty)](#fix-005--seed-data-scheduled-jobs-have-no-tech-assignments-dispatch-board-empty)
    - [Root Cause](#root-cause-1)
    - [Decision](#decision-2)
  - [FIX-006 — Seed Data: Jobs Missing All Operational Data (At-Risk, Time Entries, Expenses, Change Orders, Notes)](#fix-006--seed-data-jobs-missing-all-operational-data-at-risk-time-entries-expenses-change-orders-notes)
    - [Root Cause](#root-cause-2)
    - [Decision](#decision-3)
  - [FIX-007 — Seed Data: Insufficient Invoice AR Aging Variety](#fix-007--seed-data-insufficient-invoice-ar-aging-variety)
    - [Current State (Live DB)](#current-state-live-db)
    - [Decision](#decision-4)
  - [FIX-008 — Seed Data: Quote Titles Embed Status in the Title String](#fix-008--seed-data-quote-titles-embed-status-in-the-title-string)
    - [Root Cause](#root-cause-3)
    - [Decision](#decision-5)
    - [Specific Change Required](#specific-change-required-1)
  - [FIX-009 — Invoice Builder: Billable Items Empty (Seed Data Consequence of FIX-006)](#fix-009--invoice-builder-billable-items-empty-seed-data-consequence-of-fix-006)
    - [What's Actually Happening (The System Works)](#whats-actually-happening-the-system-works)
    - [Two "Create Invoice" Paths — Important Distinction](#two-create-invoice-paths--important-distinction)
    - [Decision](#decision-6)
  - [FIX-010 — AR Aging Widget + Invoice List: Clickable Buckets \& Aging Column](#fix-010--ar-aging-widget--invoice-list-clickable-buckets--aging-column)
    - [Current State](#current-state)
    - [Decision: Both Changes Confirmed](#decision-both-changes-confirmed)
    - [Scope Summary](#scope-summary)
  - [FIX-011 — Seed Data: Invoice Numbers Don't Follow `INV-9#####` Convention](#fix-011--seed-data-invoice-numbers-dont-follow-inv-9-convention)
    - [Current State](#current-state-1)
    - [Decision](#decision-7)
    - [Files Requiring Updates (Cross-References)](#files-requiring-updates-cross-references)
  - [FIX-012 — Seed Data: Update All Customer Email + Phone to Real Test Contacts](#fix-012--seed-data-update-all-customer-email--phone-to-real-test-contacts)
    - [Decision](#decision-8)
    - [Current State (Live DB)](#current-state-live-db-1)
    - [Files Requiring Updates](#files-requiring-updates)
  - [FIX-013 — Invoice Detail Page: Payment History Never Populated (UI Bug)](#fix-013--invoice-detail-page-payment-history-never-populated-ui-bug)
    - [Root Cause](#root-cause-4)
    - [Fix Options](#fix-options)
    - [Backend Verification (Done)](#backend-verification-done)
    - [Required Changes (Mixed BE + FE batch)](#required-changes-mixed-be--fe-batch)
  - [FIX-014 — All Data List Pages: Server-Side Search, Filtering, Pagination + Filter Bar UI](#fix-014--all-data-list-pages-server-side-search-filtering-pagination--filter-bar-ui)
    - [Problem Summary (From React Engineer Analysis)](#problem-summary-from-react-engineer-analysis)
    - [Decision: Server-Side Search + Filter + Pagination for All 5 Entities](#decision-server-side-search--filter--pagination-for-all-5-entities)
    - [Scope Summary](#scope-summary-1)
  - [Implementation Batches](#implementation-batches)
    - [Batch Overview](#batch-overview)
    - [UI-FIX-1A — Backend: Seed Data Repair + InvoiceResponse Payments (Python Engineer)](#ui-fix-1a--backend-seed-data-repair--invoiceresponse-payments-python-engineer)
    - [UI-FIX-1B — Frontend: Quote Approved Flow + AR Widget + Payment History (React Engineer)](#ui-fix-1b--frontend-quote-approved-flow--ar-widget--payment-history-react-engineer)
    - [UI-FIX-1C — Server-Side Pagination + Filter (FIX-014) — Separate Design Doc](#ui-fix-1c--server-side-pagination--filter-fix-014--separate-design-doc)
    - [UI-FIX-1C Part A — Server-Side Pagination Backend: Completion Summary](#ui-fix-1c-part-a--server-side-pagination-backend-completion-summary)
    - [UI-FIX-1C Part B — Server-Side Pagination Frontend: Completion Summary](#ui-fix-1c-part-b--server-side-pagination-frontend-completion-summary)
    - [UI-FIX-1A — Seed Data Repair + InvoiceResponse Payments: Completion Summary](#ui-fix-1a--seed-data-repair--invoiceresponse-payments-completion-summary)
    - [UI-FIX-1B — Quote Approved Flow + AR Widget Links + Payment History: Completion Summary](#ui-fix-1b--quote-approved-flow--ar-widget-links--payment-history-completion-summary)

---

## Severity Key

| Level | Meaning |
|---|---|
| **P0** | Blocks core product use — cannot complete a workflow |
| **P1** | Significant user-facing breakage; workaround is painful or nonexistent |
| **P2** | Degraded UX; user can work around it but shouldn't have to |
| **P3** | Polish / minor inconsistency |

---

## FIX-001 — Quote Workflow: `approved` Status Invisible and Unsendable

**Severity**: P1  
**Layer**: Frontend only  
**Discovered**: 2026-07-16 (Tom debugging quote flow)  
**Reference**: `dev-docs/pilot-operations.md §9.3`

### Context

When `require_approval_for_tech_quotes = true` (multi-user tenants — the default), a technician creates a quote in `draft`, then submits it for approval. The owner reviews it and approves it — transitioning it to `approved`. The next intended step is for the owner to send it to the customer (generating the public link and transitioning to `sent`). This step is completely blocked by the UI.

### Root Cause

Four specific defects across two frontend files:

| # | File | Line(s) | Defect |
|---|---|---|---|
| 1 | `QuotesPage.tsx` | 31–38 | `STATUS_FILTERS` array missing `{ label: "Approved", value: "approved" }` — no filter pill exists |
| 2 | `QuotesPage.tsx` | 193–216 | Actions column has no case for `approved` rows — no "Send to Customer" inline action |
| 3 | `QuoteActionBar.tsx` | 53 | Render guard `if (!isDraft && !(isSent && isAccepted)) return null` excludes `approved` — action bar invisible on the detail page |
| 4 | `QuoteDetailPage.tsx` | 274 | Parent mounts `QuoteActionBar` only for `isDraft \|\| isAccepted` — `approved` excluded |

### Decision

Fix all 4 defects. Backend needs no changes — `POST /quotes/{id}/versions/{versionId}/public-link` already accepts calls from any non-terminal status.

**Correct flow after fix**:
```
pending_approval → approved → [Quotes list "Approved" filter pill]
                               → [row action: "Send to Customer" link → /quotes/{id}]
                               → QuoteDetailPage loads
                               → QuoteActionBar renders "Send to Customer" button
                               → preview modal → confirm
                               → public-link created → quote transitions to `sent`
```

### Specific Code Changes Required

| File | Change |
|---|---|
| `QuotesPage.tsx` | Add `{ label: "Approved", value: "approved" }` to `STATUS_FILTERS` after `pending_approval` entry |
| `QuotesPage.tsx` | Add approved case in actions column: `{q.status_code === "approved" && <RoleGate permission="quotes.edit"><a href={/quotes/${q.id}}>Send to Customer</a></RoleGate>}` |
| `QuoteActionBar.tsx` | Add `const isApproved = status === "approved";` and update render guard to `if (!isDraft && !isApproved && !(isSent && isAccepted)) return null;` |
| `QuoteDetailPage.tsx` | Add `const isApproved = quote?.status === "approved";` and update bar mount condition to `(isDraft \|\| isApproved \|\| isAccepted)` |

**Test required**: Add a test case in `QuoteActionBar.test.tsx` for `status="approved"` renders "Send to Customer" button.

---

---

## FIX-003 — Seed Data: Fictional `pay.pilotfortrades.com` URL in Customer Comms SMS Body

**Severity**: P2 (demo/testing UX confusion — no broken functionality, real payment flow works)
**Layer**: Backend seed data only
**Discovered**: 2026-07-16 (Tom noticed SMS showed `pay.pilotfortrades.com/inv/abc123`)

### Context

The SMS message visible on the Customer Comms page reads:
> "Hi Linda! Your invoice #1042 for the outlet installation is ready. View and pay at: https://pay.pilotfortrades.com/inv/abc123. Reply STOP to opt out."

`pay.pilotfortrades.com` does not exist — no CNAME, no infra, no code behind it. The `abc123` token is also hardcoded fiction. This was demo copy written into `seed_scenario_customer_comms.py` and was never updated to reflect the real URL pattern.

### Real Invoice Payment Flow (Already Built)

The actual payment URL structure is `https://app.pilotfortrades.com/i/{signed_token}`. The full flow:

```
Owner: POST /api/v1/invoices/{id}/send
  → InvoicePublicLink created with HMAC-signed token (90-day expiry)
  → Backend returns signed_token
  → Frontend/email template builds URL: https://app.pilotfortrades.com/i/{signed_token}
  → Email/SMS delivers URL via {{invoice_url}} template variable
  → Customer clicks → Next.js /i/[token] page (no login required)
  → PublicInvoicePage renders invoice + Stripe payment form (customer's card)
  → Stripe processes → payment_intent.succeeded webhook
  → Payment recorded in Pilot → invoice balance_due updated
```

The payment page uses the **tenant's Stripe account** (not Pilot's) — per PRD §3.6, payments pass through the contractor's own Stripe account. Pilot facilitates but does not collect.

### Decision

Fix the seed data SMS body to use the correct URL pattern. The fictional URL should be replaced with `https://app.pilotfortrades.com/i/EXAMPLE_TOKEN`.

### Specific Change Required

| File | Change |
|---|---|
| `seed_scenario_customer_comms.py` | Update SMS body from `https://pay.pilotfortrades.com/inv/abc123` → `https://app.pilotfortrades.com/i/EXAMPLE_TOKEN_abc123` |

**Also update `pilot-operations.md`**: Document the invoice payment flow (§10 — done below) so this is clear for future reference.

---

---

## FIX-004 — Payment Architecture: Stripe Implementation vs PRD Design + Payment Provider Roadmap

**Severity**: P0 architectural decision (before any tenant onboards and takes a payment)
**Layer**: Backend architecture + future product roadmap
**Discovered**: 2026-07-16 (Tom asking "what happens when tenant hasn't set up Stripe?")

---

### Current Implementation vs PRD Intent

**PRD §3.6 states**: "payments pass through via tenant's own Stripe account"
**Actual implementation**: `create_payment_intent()` in `stripe_payment_intents.py` uses Pilot's **platform-level** `STRIPE_SECRET_KEY` — NOT a per-tenant Stripe connected account.

```python
# current code — Pilot's key, not tenant's
stripe_key = getattr(cfg, "STRIPE_SECRET_KEY", None)
stripe.api_key = stripe_key
pi = stripe.PaymentIntent.create(amount=amount_cents, ...)
```

The `tenant` table has `stripe_customer_id` (tenant as **customer of Pilot's billing**) — there is **no `stripe_connect_account_id`** column. The pass-through architecture from the PRD was never implemented.

### What This Means Today

| Scenario | Current behavior |
|---|---|
| Tenant has not set up Stripe | Payment still processes through Pilot's Stripe key |
| Tenant has set up Stripe (any account) | Still uses Pilot's key — tenant's account is never touched |
| No `STRIPE_SECRET_KEY` in env | Mock response returned — payment "succeeds" but nothing real happens |
| Production payment taken | Goes into Pilot's Stripe account, not the contractor's |

### Decision — **CONFIRMED 2026-07-16 by Tom**

**Stripe Connect per-tenant is REQUIRED BEFORE LAUNCH. Square added in Phase 1.5.**

Tenants must be able to connect their own Stripe account. The current Pilot-platform-key implementation must be replaced before any founders cohort tenant takes a real payment.

**Required work (pre-launch batch — must ship before beta):**
1. Add `stripe_connect_account_id TEXT NULL` to `tenant` table (Alembic migration)
2. Add `Settings > Billing > Payment Processing` page — tenant connects Stripe via OAuth (Stripe Connect onboarding URL)
3. Update `stripe_payment_intents.py` `create_payment_intent()` to pass `stripe_account=tenant.stripe_connect_account_id`
4. Public invoice page: if `stripe_connect_account_id IS NULL` → render manual payment instructions (phone, email, "pay by check/cash/Zelle") — no Stripe form rendered
5. Public invoice page: if `stripe_connect_account_id` set → render Stripe payment form (current UX, now correctly using tenant's account)

### "What if a tenant hasn't set up Stripe?" — Confirmed Behavior

Public invoice page renders a manual payment panel showing the tenant's phone, email, and a message like "Contact us to arrange payment by check, card, or Zelle." The `POST /api/v1/invoices/{id}/record-payment` endpoint (already built) handles manual payment recording — no changes needed there.

---

### Payment Provider Market Research (Trades Industry)

**Top payment processors used by electrical/plumbing/HVAC contractors (2025):**

| Provider | Market Fit | Notes |
|---|---|---|
| **Stripe** | Tech-forward, online-first | Best API, best for web/SMS pay links. Already integrated in Pilot. |
| **Square** | Dominant in field trades | Mobile card reader hardware, very popular with solo/small-crew electricians and plumbers. No monthly fee for basic. Field-first. |
| **PayPal** | Legacy, consumer-familiar | Some older small contractors still use it. Less common for new setups. |
| **Wisetack** | BNPL for large tickets | Purpose-built for home services trades. $500–$25k financing. Huge for HVAC ($5k–$15k installs). In PRD §3.11 roadmap — P1 post-launch. |
| **ACH/eCheck** | Commercial clients | Very common for commercial/property management accounts paying invoices. Stripe supports ACH natively. |
| **Zelle/Venmo** | Small solo contractors | Common but untrackable — manual recording in Pilot covers this. |

**Confirmed Payment Provider Roadmap (Tom, 2026-07-16)**

| Phase | Provider | Decision |
|---|---|---|
| **Pre-launch (required)** | **Stripe Connect (per-tenant)** | ✅ CONFIRMED — must ship before founders cohort launch |
| **Pre-launch (required)** | Manual payment fallback (cash/check/Zelle) | ✅ CONFIRMED — when no Stripe connected |
| **Phase 1.5** | **Square (per-tenant)** | ✅ CONFIRMED — post-founders-launch; many trades already have Square hardware |
| **Phase 1.5** | Wisetack BNPL financing | Huge for $5k–$15k HVAC/electrical panel jobs |
| **Phase 1.5** | ACH via Stripe | For commercial/property management clients |
| **Not planned** | PayPal | Low ROI for trades market |

**Note on Square**: Square has an invoicing API but it's NOT as cleanly separable as Stripe Connect. The tenant would need to connect their Square account and Pilot would make API calls on their behalf. Doable in Phase 2 but requires a separate payment method abstraction layer in the backend.

---

---

## FIX-005 — Seed Data: Scheduled Jobs Have No Tech Assignments (Dispatch Board Empty)

**Severity**: P2 (demo gap — dispatch board shows no assigned jobs)
**Layer**: Backend seed data only
**Discovered**: 2026-07-16 (Tom seeing no jobs on dispatch board schedule)

### Root Cause

The 3 `scheduled` status jobs in the DB have zero `job_assignment` rows:

| Job # | Status | Scheduled | Assignments |
|---|---|---|---|
| `JOB-000001` | scheduled | 2026-06-16 09:00 | **0** |
| `JOB-000010` | scheduled | 2026-07-07 09:00 | **0** |
| `DISP-001` | scheduled | 2026-07-16 09:00 | **0** |

The dispatch board backend (`scheduling.py`) correctly places unassigned jobs into the `unassigned` bucket — so they DO appear on the board, just in "Unassigned" column. The real gap is:
1. No tech is assigned, so the board shows no tech columns (just an unassigned pile)
2. `JOB-000001` (June 16) and `JOB-000010` (July 7) are in the past — only visible if the user navigates back to those dates
3. `DISP-001` (today) is the only one that would show on today's board — and it shows as unassigned

### Decision

Update seed scripts to add `job_assignment` rows for all `scheduled` and `in_progress` jobs, assigning them to `Dev Technician` (`00000000-0000-0000-0000-000000000003`). Also update `scheduled_start_at` to use relative dates (e.g., `NOW() + interval '1 day'`, `NOW() + interval '3 days'`) so the dispatch board shows current data on any run date, not fixed past dates.

**Also needed**: Seed at least 2–3 jobs with future `scheduled_start_at` dates (next 7 days) with tech assignments so the dispatch board shows a populated schedule by default.

---

## FIX-006 — Seed Data: Jobs Missing All Operational Data (At-Risk, Time Entries, Expenses, Change Orders, Notes)

**Severity**: P2 (dashboard BI, profitability, and job detail views all show empty data)
**Layer**: Backend seed data only
**Discovered**: 2026-07-16 (Tom: profitability, time entries, expenses, change orders, and notes are empty on all jobs)

### Root Cause

All jobs in the DB have:
- `actual_labor_cost_cents = 0`, `actual_material_cost_cents = 0`, `actual_profit_cents = 0`
- No `time_entry` rows (no labor clock-in/out records)
- No `expense` rows (no material receipts)
- No `change_order` rows (no scope additions)
- No `job_note` rows (no field notes)

This means: job detail pages show empty tabs for all operational data; profitability views show no actuals; at-risk detection never triggers; the dashboard BI widgets have nothing to display.

### Decision

For every `in_progress` and `scheduled` job in seed data, add:

**Time entries** (minimum 2 per job):
- Clock-in/clock-out pairs for Dev Technician with realistic hours (2–8h)
- ETC values at each clock-out (estimate remaining hours)

**Expenses** (minimum 1–2 per job):
- Material purchases with `cost_cents` in the $100–$2,000 range
- Linked to the correct `job_id` and `tenant_id`

**Change orders** (for at least 2 jobs):
- Scope additions with `total_cents` and linked to the job's quote version

**Job notes** (minimum 1 per job):
- Free-text field notes from the tech (e.g., "Customer requested outlet moved to east wall")

**At-risk scenario** (at least 1 job):
- A job where `actual_labor_cost_cents + actual_material_cost_cents` > 80% of the linked quote's `total_cents` — this triggers the at-risk threshold at the default 20% margin target
- A second job with a high ETC value pushing projected cost over budget

---

## FIX-007 — Seed Data: Insufficient Invoice AR Aging Variety

**Severity**: P2 (AR aging dashboard shows sparse data)
**Layer**: Backend seed data only
**Discovered**: 2026-07-16 (Tom checking outstanding invoices)

### Current State (Live DB)

Only 3 outstanding invoices:

| Invoice | Status | Balance | Days Overdue |
|---|---|---|---|
| `INV-SEED-G` | writeoff | $5,068.60 | 57 days |
| `INV-SEED-C` | issued | $1,156.30 | 40 days |
| `INV-SEED-E` | partial | $1,358.00 | 19 days |

No invoices in: current (0–29 days), 30-day bucket, 60-day bucket, or any current/not-yet-due state.

### Decision

Add seed invoices covering all AR aging buckets:
- 2 invoices **current** (due in future or 0–14 days overdue)
- 2 invoices **30-day** (15–44 days overdue, status=`issued`)
- 2 invoices **60-day** (45–74 days overdue, status=`issued`)
- 1 invoice **90-day** (75+ days overdue, status=`issued`)
- 1 invoice **partial payment** (partially paid, balance remaining)
- Keep existing `writeoff` for that status bucket

Use realistic totals in the $500–$8,000 range typical for electrical work. All should have valid `customer_id`, `job_id`, and correct `balance_due_cents`.

---

---

## FIX-008 — Seed Data: Quote Titles Embed Status in the Title String

**Severity**: P2 (looks unprofessional in demo; status is already shown separately via status pill)
**Layer**: Backend seed data only
**Discovered**: 2026-07-16 (Tom: quote list shows titles like "<<description>> — <<status action>>")

### Root Cause

The seed script (`seed_scenario_quote_to_cash.py`) wrote quote titles that embed the status action into the human-readable title:

| Quote # | Current Title | Status |
|---|---|---|
| `QUO-900001` | "Panel Upgrade — **Pending Internal Approval**" | `pending_approval` |
| `QUO-900002` | "Commercial Panel Assessment — **Pending Customer Review**" | `pending` |
| `QUO-900003` | "Outlet Installation — **Internally Approved**" | `approved` |
| `QUO-900004` | "Service Panel Inspection — **Sent to Customer**" | `expired` |
| `QUO-900005` | "Wiring Upgrade — **Customer Accepted**" | `accepted` |
| `QUO-900006` | "Electrical Inspection — **Converted to Job**" | `converted` |
| `QUO-900007` | "Solar Panel Wiring Estimate — **Rejected**" | `rejected` |
| `QUO-900008` | "Generator Install Estimate — **Expired**" | `expired` |
| `QUO-900009` | "EV Charger Install — **Voided**" | `void` |

The status is already displayed as a separate pill on the quote list page — embedding it in the title is redundant and makes it obvious these are demo placeholders.

Also: `QUO-000001` has `title = NULL` — no title at all. The quote list falls back to `quote_number` display but no description is shown.

### Decision

Update all seeded quote titles to be realistic job-description-style titles matching the work type. Format: `"[Scope] — [Location/Customer Context]"` — no status in the title.

**Proposed realistic replacements:**

| Quote # | New Title | Notes |
|---|---|---|
| `QUO-900001` | "200A Panel Upgrade — Johnson Residence" | Realistic scope |
| `QUO-900002` | "Commercial Panel Assessment — Metro Properties LLC" | Matches customer |
| `QUO-900003` | "GFCI Outlet Installation — Master Bath" | Specific scope |
| `QUO-900004` | "Electrical Service Inspection — Fairview Ave Property" | |
| `QUO-900005` | "Full Home Rewire — Smith Renovation" | |
| `QUO-900006` | "LED Lighting Upgrade — Office Suite 200" | |
| `QUO-900007` | "Solar Panel Tie-In Wiring — Rooftop Array" | |
| `QUO-900008` | "Standby Generator Installation — Backup System" | |
| `QUO-900009` | "EV Charger Rough-In — Garage 240V Circuit" | |
| `QUO-000001` | "Service Call — Outlet Troubleshooting" | Fill null title |
| `QTC-001` | "Electrical Service Call — Initial Estimate" | Already clean but fix "Draft Estimate" suffix |

### Specific Change Required

Update `title` values in the quote INSERT statements in `seed_scenario_quote_to_cash.py`. Also update the `QUOTE_SCENARIOS` dict definitions that drive these rows.

---

---

## FIX-009 — Invoice Builder: Billable Items Empty (Seed Data Consequence of FIX-006)

**Severity**: P2 (demo gap — invoice builder shows no items to invoice; not a code bug)
**Layer**: Seed data gap (consequence of FIX-006) + one genuine UI distinction
**Discovered**: 2026-07-16 (Tom: "Create Invoice from job shows nothing pre-populated")

### What's Actually Happening (The System Works)

The invoice builder **does** pre-populate when there is real data. The flow:

```
Job Detail page → "Convert to Invoice" button
  → navigates to /invoices/new?job_id={id}
  → InvoiceBuilderPage receives jobId param
  → useJob(jobId) fetches job → customer_id + site_id pre-filled ✅
  → useBillableItems(jobId) fetches GET /api/v1/jobs/{id}/billable-items
    → returns { time_entries: [], expenses: [] }   ← ALL EMPTY (seed data gap)
  → Builder shows "Link a job above to pre-fill billable items" message
  → User sees empty checklist with only custom line item form
```

Customer and site ARE pre-filled correctly. The billable items section is empty because seed data jobs have no `time_entry` or `expense` rows (see FIX-006).

### Two "Create Invoice" Paths — Important Distinction

| Entry point | Path | What it does |
|---|---|---|
| Job detail "Convert to Invoice" btn | `/invoices/new?job_id={id}` | **Full builder** — customer/site pre-filled, billable items checklist populated from time entries + expenses |
| Invoices list "+ New Invoice" btn | Modal (inline) | **Lightweight modal** — link to job/quote dropdowns only, no billable item pre-fill at all; creates a bare invoice record |

The lightweight modal is intentionally minimal — it creates an invoice skeleton that the user then edits in the invoice detail page. The **full pre-population experience** is only available via `/invoices/new?job_id=X`.

### Decision

**No code change needed.** The pre-population will work correctly once FIX-006 seed data is in place (time entries + expenses seeded to jobs). Confirm by running the seed after FIX-006 and clicking "Convert to Invoice" from a job detail page.

**Note for demo prep**: Until FIX-006 seed data is in place, use the InvoiceBuilderPage with a custom line item to demonstrate the invoice creation flow. The billable items section will be populated once real time/expense data exists.

---

---

## FIX-010 — AR Aging Widget + Invoice List: Clickable Buckets & Aging Column

**Severity**: P2 (UX improvement — data is there but not actionable)
**Layer**: Frontend (both changes) + small Backend addition (1 query param)
**Discovered**: 2026-07-17 (Tom: AR widget should link to filtered invoices; invoice list needs aging column)

### Current State

**Dashboard AR Widget** (`ArSummaryWidget.tsx`):
- 4 static bucket rows (Current, 30+, 60+, 90+) + Total Outstanding
- No links — numbers are display-only, no click-through

**Invoices Page** (`InvoicesPage.tsx`):
- Status filter pills: All, Draft, Sent, Paid, Void, Write-Off
- Separate "Overdue Only" toggle → sends `?overdue=true` to backend → returns ALL overdue invoices (correct)
- Columns: Invoice #, Customer, Status (with derived "Overdue" badge), Total, Issued, Due
- No "Aging" column
- The `isOverdue()` helper is client-side boolean — no bucket classification

**Backend invoices list** (`invoices.py`):
- `?overdue=true` — returns all invoices where `due_at < now` and `status NOT IN (paid, void, writeoff)`
- `?due_after=DATE` param exists
- **No `?due_before=DATE` param** — needed for per-bucket filtering

---

### Decision: Both Changes Confirmed

#### Change A — Dashboard Widget: Clickable Bucket Links (Frontend only + backend param)

Each bucket row becomes a `<Link>` to the invoices page filtered to that bucket:

| Bucket | Link target |
|---|---|
| **Current** | `/invoices` (no filter — current = not overdue) |
| **30+ days** | `/invoices?overdue=true&due_before=DATE_30_DAYS_AGO` |
| **60+ days** | `/invoices?overdue=true&due_before=DATE_60_DAYS_AGO` |
| **90+ days** | `/invoices?overdue=true&due_before=DATE_90_DAYS_AGO` |
| **Total Outstanding** | `/invoices?overdue=true` (all overdue) |

Each link also shows the dollar amount (already displayed) — no change to the amount display.

**Backend change required**: Add `due_before: datetime | None = Query(None)` param to the invoices list endpoint alongside the existing `due_after`. Filter: `Invoice.due_at < due_before`. This is a 3-line backend change.

**Frontend change**: Convert each bucket `<div>` in `ArSummaryWidget.tsx` to a Next.js `<Link>` with appropriate URL params.

#### Change B — Invoices Page: Add "Aging" Column (Frontend only — no backend change)

Add a computed "Aging" column derived from `due_at` (already in the response) at render time:

```tsx
function getAgingBucket(due_at: string | null, status_code: string): string {
  if (!isOverdue({ due_at, status_code })) return "Current";
  const daysOverdue = Math.floor((Date.now() - new Date(due_at!).getTime()) / 86_400_000);
  if (daysOverdue <= 60) return "30+";
  if (daysOverdue <= 90) return "60+";
  return "90+";
}
```

Column renders a colored badge:
- `Current` → green (`bg-margin-100 text-margin-700`)
- `30+` → amber (`bg-alert-100 text-alert-600`)
- `60+` → orange-amber (`bg-alert-100 text-alert-700`)
- `90+` → red (`bg-fault-100 text-fault-700`)

Place after the "Status" column. Only meaningful on non-paid invoices — show `—` for paid/void/writeoff.

#### "Overdue Only" Toggle — Confirmed Correct Behavior

The current toggle is correct: `?overdue=true` returns ALL overdue invoices (30+, 60+, 90+ combined). This is the right behavior for a bulk view. The aging column added in Change B lets the user see which bucket each invoice falls into without needing separate filter pills for each aging tier.

**Do NOT** add separate filter pills for "30+", "60+", "90+" — that would be redundant with the aging column. Keep the single "Overdue Only" toggle. If the user wants to sort by aging, the table sort on the new Aging column handles that.

---

### Scope Summary

| Change | Layer | Effort |
|---|---|---|
| A1: Add `due_before` query param to invoices list endpoint | Backend | ~1h — 1 new Query param + filter clause |
| A2: Make AR widget bucket rows clickable links | Frontend | ~1h — wrap divs in Next.js Link |
| B: Add computed "Aging" column to invoices list table | Frontend | ~1h — 1 new TanStack column + helper function |

**Total estimate**: ~3h — good candidate to bundle with other invoice UI improvements in a focused React Engineer batch.

---

---

## FIX-011 — Seed Data: Invoice Numbers Don't Follow `INV-9#####` Convention

**Severity**: P3 (demo polish — data looks obviously synthetic)
**Layer**: Backend seed data only
**Discovered**: 2026-07-17 (Tom: invoices show `INV-SEED-A` through `INV-SEED-G` instead of realistic numbers)

### Current State

| Invoice # | Source script |
|---|---|
| `INV-900001` | `seed_scenario_quote_to_cash.py` — correct format |
| `INV-SEED-A` through `INV-SEED-G` | `seed_scenario_reporting.py` — non-standard format |

Production invoice numbers auto-increment as `INV-000001`, `INV-000002`, etc. Seed data uses the `9XXXXX` prefix convention to distinguish seed records from user-created records.

### Decision

Rename all `INV-SEED-<letter>` invoices to `INV-9XXXXX` format, sequential from `INV-900002` (since `INV-900001` already exists):

| Old | New |
|---|---|
| `INV-SEED-A` | `INV-900002` |
| `INV-SEED-B` | `INV-900003` |
| `INV-SEED-C` | `INV-900004` |
| `INV-SEED-D` | `INV-900005` |
| `INV-SEED-E` | `INV-900006` |
| `INV-SEED-F` | `INV-900007` |
| `INV-SEED-G` | `INV-900008` |

### Files Requiring Updates (Cross-References)

**Critical**: The invoice numbers are hardcoded in multiple places — ALL must be updated together:

| File | References |
|---|---|
| `seed_scenario_reporting.py` | All `INV-SEED-<letter>` definitions (lines 76–1420) |
| `seed_scenario_notifications.py` | Line 55: `"INV-SEED-B"` in QB conflict notification body; line 63: `"INV-SEED-C"` in dunning notification body and deep link |

The `reset_dev_db.py` script doesn't hardcode invoice numbers — it clears by `tenant_id` — so no changes needed there.

---

---

## FIX-012 — Seed Data: Update All Customer Email + Phone to Real Test Contacts

**Severity**: P1 for testing (cannot test email/SMS delivery without real contact info)
**Layer**: Backend seed data only
**Decided**: 2026-07-17 by Tom

### Decision

Update `email` and `mobile_phone` on ALL seeded customers to:

```
email:        info@pilotfortrades.com
mobile_phone: +14105550123   (E.164 format for 410-555-0123)
```

This allows real email delivery and Telnyx SMS testing once the A2P 10DLC campaign is approved.

### Current State (Live DB)

| Customer | email | mobile_phone | Action |
|---|---|---|---|
| Apex Commercial LLC | NULL | NULL | Add both |
| Bob Davis | NULL | NULL | Add both |
| Carlos Rivera | carlos.rivera@example.com | +13125551010 | Update both |
| Inactive Customer | NULL | NULL | Add both |
| James Torres | james.torres@example.com | +13055551007 | Update both |
| Jane Doe | jane@doeelectric.example.com | 555-1234 | Update both (phone also wrong format) |
| John Smith | john.smith@example.com | +12125551001 | Update both |
| Linda Park | linda.park@example.com | +16175551020 | Update both |
| Mary Johnson | mary.j@example.com | +12125551002 | Update both |
| Metro Properties LLC | info@metro-properties.example.com | +12025551006 | Update both |
| Rachel Kim | rachel.kim@example.com | +14255551005 | Update both |
| Sunrise Electric LLC | contact@sunrise-electric.example.com | +14155551030 | Update both |

### Files Requiring Updates

The customer seed data comes from `seed_scenario_quote_to_cash.py` and `seed_test_tenant.py`. Both need the `email` and `mobile_phone` values updated on all customer INSERT/upsert rows.

**Phone format note**: Store as E.164 (`+14105550123`) — required for Telnyx SMS delivery. The existing `555-1234` on Jane Doe is also non-E.164 and should be corrected as part of this fix.

---

---

## FIX-013 — Invoice Detail Page: Payment History Never Populated (UI Bug)

**Severity**: P1 — payment history is always empty even when payments exist
**Layer**: Frontend
**Discovered**: 2026-07-17 (Tom: INV-SEED-E shows `partial` status but payment history section is empty)

### Root Cause

The payment IS in the DB — `$800.00` check payment recorded against INV-SEED-E (now INV-900006). The UI shows empty because `InvoiceDetailPage.tsx` mounts `InvoicePaymentHistory` with no props:

```tsx
// InvoiceDetailPage.tsx line 202 — bug: no payments passed
<InvoicePaymentHistory />
```

`InvoicePaymentHistory` accepts `payments?: PaymentEntry[]` defaulting to `[]`. The parent never fetches or passes the actual payment rows.

### Fix Options

**Option A (preferred)**: Add `payments` to the invoice detail API response. Check whether `GET /api/v1/invoices/{id}` already returns a `payments` array. If not, add it to the `InvoiceResponse` schema. Then pass `invoice.payments` to `<InvoicePaymentHistory payments={invoice.payments} />`.

**Option B**: Add a separate `useInvoicePayments(invoiceId)` hook that calls `GET /api/v1/invoices/{id}/payments` (if that endpoint exists) and passes the result to the component.

**Decision**: Use Option A — keeping payments in the main invoice response is more efficient (1 request). Need to verify whether the invoice detail endpoint already returns payments.

### Backend Verification (Done)

`InvoiceResponse` schema (`schemas.py`) confirmed — it has `lines: list[InvoiceLineResponse]` but **no `payments` field**. Payments are NOT returned by the invoice detail endpoint.

### Required Changes (Mixed BE + FE batch)

**Backend:**
1. Add `PaymentSummaryResponse` schema with: `id`, `amount_cents`, `paid_at`, `paid_via`, `psp_provider`, `customer_payment_comment`
2. Add `payments: list[PaymentSummaryResponse] = []` to `InvoiceResponse`
3. Update `GET /api/v1/invoices/{id}` handler to JOIN and return payments for the invoice

**Frontend:**
1. Update `useInvoice` hook's return type to include `payments: PaymentEntry[]`
2. Update `InvoiceDetailPage.tsx` to pass `payments={invoice.payments ?? []}` to `<InvoicePaymentHistory>`

**Effort**: ~2h — straightforward addition. Good to bundle with FIX-010 (AR widget + aging column) in the same mixed batch.

---

---

## FIX-014 — All Data List Pages: Server-Side Search, Filtering, Pagination + Filter Bar UI

**Severity**: P0 — client-side-only search is fundamentally broken above the page limit
**Layer**: Backend (all 5 entity list endpoints) + Frontend (all 5 list pages + shared pagination component)
**Decided**: 2026-07-17 by Tom

### Problem Summary (From React Engineer Analysis)

| Surface | Server search | Server filter | Returns `total` | Pagination params |
|---|---|---|---|---|
| Customers | ✅ `?search=` | ❌ none | ❌ no | `skip`, `limit` |
| Quotes | ❌ none | ❌ none | ❌ no | **no params at all** |
| Invoices | ❌ none | ❌ none | ✅ yes | `offset`, `limit` |
| Catalog | ❌ none | ❌ none | ❌ no | `skip`, `limit` |
| Jobs | ❌ none | ❌ none | ❌ no | `skip`, `limit` |

- All filtering/search today is **client-side only** — scans only the fetched page, not the full DB
- Sorting is **client-side only** — sorts the in-memory page, not the full dataset
- No entity except invoices returns a `total` count — pagination is impossible without it

---

### Decision: Server-Side Search + Filter + Pagination for All 5 Entities

#### Backend Changes Required (per entity)

**All endpoints must return a standardized paginated response wrapper:**
```python
class PaginatedResponse(BaseModel):
    items: list[...]
    total: int       # Total matching rows in DB (for pagination math)
    limit: int
    offset: int      # Standardize on offset (not skip)
```

**Standardized pagination params** (all endpoints, consistent naming):
```
?limit=25    (see shared PAGE_SIZE constant below)
?offset=0
```

**Per-entity server-side filter params (AND logic when multiple supplied):**

| Entity | Filter params |
|---|---|
| **Customers** | `?search=` (name, email, phone), `?status=active\|inactive` |
| **Quotes** | `?customer_search=`, `?title_search=`, `?status=`, `?date_from=`, `?date_to=` (on `created_at`) |
| **Invoices** | `?customer_search=`, `?status=`, `?date_from=`, `?date_to=` (on `issued_at`) — existing `?overdue=` kept |
| **Catalog (pricebook)** | `?search=` (name, description, sku), `?status=active\|inactive` |
| **Jobs** | `?customer_search=`, `?status=`, `?scheduled_from=`, `?scheduled_to=` (on `scheduled_start_at`) |

**All filters are AND logic**: `?customer_search=Smith&status=draft` returns drafts whose customer name matches "Smith".

**Sorting**: Defer server-side sorting to Phase 1.5. Column sort remains client-side (current page only) for this batch. Add a visible note in the UI: "Sorting applies to current page." Phase 1.5 adds `?sort_by=&sort_dir=asc|desc` to all endpoints.

---

#### Frontend Changes Required (all 5 list pages)

**1. Shared constant — single source of truth for page size:**
```ts
// packages/shared-api/src/constants.ts (or similar shared location)
export const LIST_PAGE_SIZE = 25;
```
All `PAGE_SIZE` hardcodes in individual page components (`QuotesPage`, `InvoicesPage`, `JobsPage`, `CustomersPage`, `CatalogPage`) replaced with this import.

**2. Filter Bar component (per page, NOT a shared generic component — keep it entity-specific for clarity):**

Each list page gets a filter bar above the table:
- **Text inputs** for each searchable text field (customer name, title, SKU, etc.)
- **Status dropdown** (NOT pills — dropdown `<select>` defaulting to `""` meaning "All") populated with the entity's status codes
- **Date range pickers** (`date_from` / `date_to`) where applicable — two `<input type="date">` fields with "From" / "To" labels
- **"Search" button** — explicit submit, NOT on-keystroke. User enters filters then clicks Search. This prevents spamming the API on every keypress.
- **"Clear" button** — resets all filters to defaults and re-fetches
- Responsive layout: filter inputs wrap to multiple rows on narrow viewports (CSS `flex-wrap`)

**3. Pagination component — shared `<PilotPaginator>` component:**

```
[<<] [<]  Page [  3  ] of 10  [>] [>>]
          ^editable input^
```

- `<<` → go to page 1
- `<` → previous page
- `>` → next page
- `>>` → last page (requires `total` count to compute)
- Center: `Page X of Y` where Y = `Math.ceil(total / limit)`
- The page number in the center is an `<input type="number">` — user can type a page number and press Enter to jump directly
- Buttons disabled at boundaries (`<<` and `<` disabled on page 1; `>` and `>>` disabled on last page)
- Design: clean minimal style using existing Pilot token colors (`text-neutral-600`, `border-neutral-200`), not heavy/busy

**4. Remove "Load More" button pattern** — replaced entirely by the new pagination component.

**5. Status filter change** — convert status filter pills to `<select>` dropdown:
- Default option: `<option value="">All</option>`
- One option per status code
- Clears to "All" when the "Clear" button is clicked
- Submit via the "Search" button (not auto-trigger on change)

---

### Scope Summary

| Component | Layer | Effort |
|---|---|---|
| Add `total` + `offset` standardization + filter params to Customers endpoint | BE | ~1.5h |
| Add `total` + filter params to Quotes endpoint (currently has no pagination at all) | BE | ~2h |
| Add customer_search + date filters to Invoices endpoint | BE | ~1h |
| Add `total` + filter params to Catalog endpoint | BE | ~1.5h |
| Add `total` + filter params to Jobs endpoint | BE | ~1.5h |
| Shared `LIST_PAGE_SIZE` constant | FE | ~15min |
| Shared `<PilotPaginator>` component | FE | ~2h |
| Filter bar + status dropdown + Search button on each of 5 list pages | FE | ~4h (5 × ~45min) |
| Remove "Load More", wire up pagination to each page | FE | ~1h |
| Tests (backend filter params + FE paginator unit test) | Both | ~2h |

**Total estimate**: ~17h — this is a significant batch. Should be split:
- **Backend batch** (Python Engineer): All 5 endpoint enhancements
- **Frontend batch** (React Engineer): `PilotPaginator`, filter bars, status dropdowns, wire-up to updated APIs

---

<!-- ═══════════════════════════════════════════════════════════════════ -->
<!-- ADD NEW FINDINGS BELOW THIS LINE AS INVESTIGATION CONTINUES       -->
<!-- ═══════════════════════════════════════════════════════════════════ -->

---

## Implementation Batches

Designed 2026-07-17. Three batches scope all open fixes. FIX-004 (Stripe Connect) is a larger pre-launch batch, designed separately.

### Batch Overview

| Batch | Type | Engineer | Fixes | Estimated Effort | Status |
|---|---|---|---|---|---|
| **UI-FIX-1A** | Backend (seed data + API schema) | Python Engineer | FIX-003, 005, 006, 007, 008, 011, 012, 013-BE | ~4–5h | ✅ Complete — 2026-07-17 |
| **UI-FIX-1B** | Frontend (web only) | React Engineer | FIX-001, 010, 013-FE | ~3–4h | ✅ Complete — 2026-07-18 |
| **UI-FIX-1C** | Mixed (BE + FE) — Server-side pagination & search | Python Engr + React Engr | FIX-014 | ~17h | ✅ Complete — Part A (Backend) 2026-07-18 + Part B (Frontend) 2026-07-18 |

### UI-FIX-1A — Backend: Seed Data Repair + InvoiceResponse Payments (Python Engineer)

**Design doc**: `batch-ui-fix-1a-design.md`
**Prompt**: `batch-ui-fix-1a-python-engr-prompt.md`

| Fix | What changes |
|---|---|
| FIX-003 | `seed_scenario_customer_comms.py` — SMS body URL corrected to `https://app.pilotfortrades.com/i/EXAMPLE_TOKEN_abc123` |
| FIX-005 | `seed_scenario_reporting.py` or `seed_jobs.py` — add `job_assignment` rows for all `scheduled`/`in_progress` jobs; update `scheduled_start_at` to relative dates (`NOW() + interval`) |
| FIX-006 | Add `job_time_entry` rows (2 per job), `job_expense` rows (1–2 per job), `job_note` rows (1 per job) for all `in_progress`/`scheduled` jobs |
| FIX-007 | Add 6 new invoices covering all AR aging buckets (current, 30+, 60+, 90+, partial, existing writeoff kept) |
| FIX-008 | Update all seeded quote `title` values in `seed_scenario_quote_to_cash.py` — remove status from title strings |
| FIX-011 | Rename `INV-SEED-A` through `INV-SEED-G` → `INV-900002` through `INV-900008` in `seed_scenario_reporting.py` + cross-references in `seed_scenario_notifications.py` |
| FIX-012 | Update all customer `email` → `info@pilotfortrades.com` and `mobile_phone` → `+14105550123` in `seed_scenario_quote_to_cash.py` + `seed_test_tenant.py` |
| FIX-013-BE | Add `PaymentSummaryResponse` Pydantic schema + `payments: list[PaymentSummaryResponse]` to `InvoiceResponse`; update `get_invoice()` route handler to JOIN `payment` table and return payments |

### UI-FIX-1B — Frontend: Quote Approved Flow + AR Widget + Payment History (React Engineer)

**Design doc**: `batch-ui-fix-1b-design.md`
**Prompt**: `batch-ui-fix-1b-react-engr-prompt.md`
**Depends on**: UI-FIX-1A complete ✅ — React Engineer must run `pnpm sync-api-types` before starting (`InvoiceResponse` gains `payments` field)

| Fix | What changes |
|---|---|
| FIX-001 | `QuotesPage.tsx` — add `approved` to STATUS_FILTERS and actions column; `QuoteActionBar.tsx` — add `isApproved` guard; `QuoteDetailPage.tsx` — add `isApproved` to mount condition |
| FIX-010 | `ArSummaryWidget.tsx` — wrap bucket rows in Next.js `<Link>` with `?due_before=` params (backend `due_before` param already live ✅); `InvoicesPage.tsx` — add computed "Aging" column with colored bucket badge |
| FIX-013-FE | `InvoiceDetailPage.tsx` — pass `invoice.payments ?? []` to `<InvoicePaymentHistory>`; update `useInvoice` hook return type to include `payments` |

### UI-FIX-1C — Server-Side Pagination + Filter (FIX-014) — Separate Design Doc

Design doc: `batch-ui-fix-1c-design.md`. ✅ **Both Part A (Backend) and Part B (Frontend) complete — 2026-07-18**.

---

### UI-FIX-1C Part A — Server-Side Pagination Backend: Completion Summary

**Completed**: 2026-07-18
**Mode**: Pilot Python Engineer
**Baseline**: 4048 passed, 1 skipped
**Final**: 4062 passed (unit) / 4097 passed (full suite), 0 failed (+14 new tests)

#### What Was Accomplished

- Added `PaginatedResponse[T]` generic schema + `PaginatedCustomerResponse`, `PaginatedJobListResponse`, `PaginatedCatalogResponse` to `schemas.py`; `PaginatedQuoteListResponse` to `api/schemas/quotes.py`
- Updated 5 list endpoints with `total` count, canonical `offset` param (backward-compat `skip` alias), default `limit=25`, and new filter params
- **Caller audit**: No internal callers relied on default `limit=100`; tests that searched by ID (not count) were naturally resilient. Tests that fetched all records with seed data needed explicit `limit=200` added
- Updated 8 existing test files to access `resp.json()["items"]` instead of bare list

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/schemas/schemas.py` | Updated — `PaginatedResponse` generic + 3 concrete types + `PaginatedCatalogResponse` |
| `backend/api/schemas/quotes.py` | Updated — `PaginatedQuoteListResponse` concrete type |
| `backend/api/routes/customers.py` | Updated — `PaginatedCustomerResponse`, `offset`, `status` filter |
| `backend/api/routes/quotes.py` | Updated — `PaginatedQuoteListResponse`, `customer_search`, `title_search`, date range |
| `backend/api/routes/invoices.py` | Updated — `customer_search`, `issued_from`, `issued_to` filter params |
| `backend/api/routes/jobs.py` | Updated — `PaginatedJobListResponse`, `status`, `customer_search`, `scheduled_from/to` |
| `backend/api/routes/catalog.py` | Updated — `PaginatedCatalogResponse`, `search` param |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/tests/domains/platform_infrastructure/test_ui_fix_1c_pagination.py` | Created — 14 unit tests covering all 5 endpoints |
| `backend/tests/domains/crm/test_customer_search.py` | Updated — access `.["items"]` |
| `backend/tests/domains/sales_quoting/test_quote_list_enhancements.py` | Updated — access `.["items"]` |
| `backend/tests/domains/field_operations/test_job_list_enhancements.py` | Updated — access `.["items"]` |
| `backend/tests/test_multi_tenancy_isolation.py` | Updated — access `.["items"]` |
| `backend/tests/test_test_endpoints.py` | Updated — access `.["items"]` |
| `backend/tests/batch_b20/test_pricebook_item_crud.py` | Updated — access `.["items"]` |
| `backend/tests/batch_tp_b5/test_tp_b5_catalog_pricebook.py` | Updated — access `.["items"]` |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/platform_infrastructure/test_ui_fix_1c_pagination.py` | `domain_platform_infrastructure` | 14 | ✅ |

---

### UI-FIX-1C Part B — Server-Side Pagination Frontend: Completion Summary

**Completed**: 2026-07-18
**Mode**: Pilot React Engineer
**Baseline**: 1261 passed (web)
**Final**: 1294 passed (+33 new tests), 0 failed

#### What Was Accomplished

- Added `LIST_PAGE_SIZE = 25` constant to `packages/shared-api/src/constants.ts` (exported via barrel)
- Created `PilotPaginator.tsx` web-only pagination component with page-jump input; renders nothing when `total <= limit`
- Updated all 5 list hooks to return `PaginatedResult<T>` and accept new server-side filter params:
  - `useCustomers`: `offset`, `status` (active/inactive)
  - `useQuotes`: `offset`, `customer_search`, `title_search`, `date_from`, `date_to`
  - `useInvoices`: `customer_search`, `issued_from`, `issued_to` (existing shape kept)
  - `useJobs`: complete rewrite to option-based params; `offset`, `status`, `customer_search`, `scheduled_from`/`to`; dispatch board `tech_id`/`scheduled_date` preserved
  - `usePricebook`: `offset`, `status` (maps to `is_active` param)
- Added filter bars to all 5 pages with explicit "Search" + "Clear" buttons (no on-keystroke API firing)
- Replaced status pills with `<select>` dropdown on Customers, Quotes, Jobs, Catalog; kept status pills on InvoicesPage
- Replaced Load More pattern with `PilotPaginator` on all 5 pages
- Updated all 5 MSW handlers to return `{ items, total, limit, offset }` paginated shape
- Fixed all downstream callers: `CustomerCombobox`, `QuoteCreatePage`, `InvoiceCreateModal`, `useCreatePricebookItem`, `useUpdatePricebookItem`, `useAddPricebookItemPrice`

#### Files Changed / Created

| File | Action |
|---|---|
| `packages/shared-api/src/constants.ts` | Created — `LIST_PAGE_SIZE = 25` |
| `apps/web/src/components/PilotPaginator.tsx` | Created |
| `apps/web/src/components/__tests__/PilotPaginator.test.tsx` | Created |
| `apps/web/src/features/customers/hooks/useCustomers.ts` | Updated |
| `apps/web/src/features/customers/components/CustomersPage.tsx` | Updated |
| `apps/web/src/features/quotes/hooks/useQuotes.ts` | Updated |
| `apps/web/src/features/quotes/components/QuotesPage.tsx` | Updated |
| `apps/web/src/features/invoices/hooks/useInvoices.ts` | Updated |
| `apps/web/src/features/invoices/components/InvoicesPage.tsx` | Updated |
| `apps/web/src/features/jobs/hooks/useJobs.ts` | Updated |
| `apps/web/src/features/jobs/components/JobsPage.tsx` | Updated |
| `apps/web/src/features/catalog/hooks/usePricebook.ts` | Updated |
| `apps/web/src/features/catalog/components/PricebookItemsPage.tsx` | Updated |
| `apps/web/src/mocks/handlers/customerHandlers.ts` | Updated — paginated shape |
| `apps/web/src/mocks/handlers/quotesListHandlers.ts` | Updated — paginated shape |
| `apps/web/src/mocks/handlers/jobs.ts` | Updated — paginated shape |
| `apps/web/src/mocks/handlers/catalogHandlers.ts` | Updated — paginated shape |
| (invoiceDetailHandlers.ts already returned paginated shape ✅) | No change |
| `apps/web/src/__tests__/batch_ui_fix_1c/pagination_customers.integration.test.tsx` | Created |
| `apps/web/src/__tests__/batch_ui_fix_1c/pagination_jobs.integration.test.tsx` | Created |
| `apps/web/src/components/CustomerCombobox.tsx` | Updated — unwrap `.items` |
| `apps/web/src/features/quotes/components/QuoteCreatePage.tsx` | Updated — unwrap `.items` |
| `apps/web/src/features/invoices/components/InvoiceCreateModal.tsx` | Updated — unwrap `.items` |
| `apps/web/src/features/catalog/hooks/useCreate/UpdatePricebookItem.ts` | Updated — `PRICEBOOK_QUERY_KEY({})` |
| Various existing tests (12 files) | Updated for new paginated return shape |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `components/__tests__/PilotPaginator.test.tsx` | Unit | 10 | ✅ |
| `__tests__/batch_ui_fix_1c/pagination_customers.integration.test.tsx` | Integration | 5 | ✅ |
| `__tests__/batch_ui_fix_1c/pagination_jobs.integration.test.tsx` | Integration | 5 | ✅ |
| `features/customers/hooks/__tests__/useCustomers.test.ts` | Unit (updated) | 8 | ✅ |
| `features/quotes/hooks/__tests__/useQuotes.test.ts` | Unit (updated) | 8 | ✅ |
| `features/jobs/hooks/__tests__/useJobs.test.ts` | Unit (created) | 7 | ✅ |

---

### UI-FIX-1A — Seed Data Repair + InvoiceResponse Payments: Completion Summary

**Completed**: 2026-07-17
**Mode**: Pilot Python Engineer
**Baseline**: 4045 passed, 1 skipped, 0 failed
**Final**: 4048 passed (unit) / 4083 passed (full suite), 0 failed (+3 new tests)

#### What Was Accomplished

- **FIX-011**: All `INV-SEED-A` through `INV-SEED-G` invoice numbers renamed to `INV-900002`–`INV-900008` in `seed_scenario_reporting.py` (including dynamic format string) and cross-references in `seed_scenario_notifications.py`
- **FIX-012**: All customer `email` → `info@pilotfortrades.com` and `mobile_phone` → `+14105550123` (E.164) across `seed_scenario_quote_to_cash.py` (all 8 customers including previously-null ones) and `seed_scenario_customer_comms.py`
- **FIX-008**: All 9 seeded quote `title` values updated to remove status keywords — `seed_scenario_quote_to_cash.py` + `QTC-001` inline title
- **FIX-003**: SMS body URL corrected to `https://app.pilotfortrades.com/i/EXAMPLE_TOKEN_abc123` in `seed_scenario_customer_comms.py`
- **FIX-005**: `seed_scenario_dispatch.py` updated to refresh `scheduled_start_at` for DISP jobs to relative dates; `job_assignment` rows added for all `scheduled`/`in_progress` DISP jobs via new `mode_seed()` section
- **FIX-006**: `job_time_entry` (2 per job), `job_expense` (2 per job), `job_notes` (1 per job) added for all `scheduled`/`in_progress` DISP jobs; at-risk scenario seeded for `in_progress` job (high material cost)
- **FIX-007**: 6 new AR aging invoices added to `seed_scenario_reporting.py` — `INV-900009` through `INV-900014` covering Current (×2), 30+, 60+, 90+, and Partial buckets with relative `NOW()` dates; `INV-900014` includes a `$500` payment row
- **FIX-013-BE**: `PaymentSummaryResponse` Pydantic schema added to `schemas.py`; `payments: list[PaymentSummaryResponse] = []` field added to `InvoiceResponse`; `get_invoice()` (shared `_get_invoice_impl`) updated to fetch tenant-scoped payments and return them in response; 404 detail upgraded to RFC 7807 format

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_scenario_reporting.py` | Updated — INV-SEED-* renamed (incl. dynamic format), AR aging invoices added |
| `backend/migrations/scripts/seed_scenario_notifications.py` | Updated — INV-SEED-* cross-references renamed |
| `backend/migrations/scripts/seed_scenario_quote_to_cash.py` | Updated — all customer email/phone + all quote titles |
| `backend/migrations/scripts/seed_scenario_customer_comms.py` | Updated — customer email/phone + SMS URL corrected |
| `backend/migrations/scripts/seed_scenario_dispatch.py` | Updated — FIX-005 date refresh + job_assignment; FIX-006 time entries + expenses + notes |
| `backend/api/schemas/schemas.py` | Updated — `PaymentSummaryResponse` added; `InvoiceResponse.payments` added |
| `backend/api/routes/invoices.py` | Updated — `_get_invoice_impl()` JOINs payment table; RFC 7807 404 detail; `PaymentSummaryResponse` imported |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/tests/domains/invoicing_billing/test_invoice_payments_embedded.py` | Created — 3 unit tests |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/invoicing_billing/test_invoice_payments_embedded.py` | `domain_invoicing_billing` | 3 | ✅ |

#### Handoff to React Engineer (UI-FIX-1B)

Run `pnpm sync-api-types` before starting UI-FIX-1B. The `InvoiceResponse` type now includes `payments: PaymentSummaryResponse[]` — the React Engineer's `useInvoice` hook needs updating to wire this to `<InvoicePaymentHistory>`.

---

### UI-FIX-1B — Quote Approved Flow + AR Widget Links + Payment History: Completion Summary

**Completed**: 2026-07-17
**Mode**: Pilot React Engineer
**Baseline**: 1251 passed, 1 failed (web; pre-existing flaky test in batch_fe_b29)
**Final**: 1261 passed, 0 failed (+10 new tests)

#### What Was Accomplished

- **FIX-001**: `approved` status now has a filter pill in the quotes list, an inline "Send to Customer" list action (navigates to detail), an `isApproved` guard in `QuoteActionBar` that renders the Send button and prevents the early-return from firing, and `isApproved` added to the `QuoteDetailPage` action bar mount condition — full `approved` → send-to-customer flow is now accessible
- **FIX-010**: AR widget bucket rows (`Current`, `30+ days`, `60+ days`, `90+ days`) and Total Outstanding are now wrapped in Next.js `<Link>` with computed `?due_before=YYYY-MM-DD` params; `InvoicesPage` now has a computed "Aging" column with color-coded bucket badges (`Current` / `30+` / `60+` / `90+`) rendered after the Due column
- **FIX-013-FE**: `InvoiceDetailPage` now passes `invoice.payments ?? []` to `<InvoicePaymentHistory>`; `useInvoice` hook extended with `PaymentSummaryEntry` interface and `payments` field; `InvoicePaymentHistory` interface updated to use `customer_payment_comment` / `psp_provider` for Reference column (replaces removed `idempotency_key`); `invoiceDetailHandlers.ts` mock updated to include payments array

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/features/quotes/components/QuotesPage.tsx` | Updated — `approved` filter pill + "Send to Customer" list action |
| `apps/web/src/features/quotes/components/QuoteActionBar.tsx` | Updated — `isApproved` guard + Send to Customer button |
| `apps/web/src/features/quote-approval/QuoteDetailPage.tsx` | Updated — `isApproved` added to action bar mount condition |
| `apps/web/src/features/invoices/hooks/useInvoice.ts` | Updated — `PaymentSummaryEntry` interface + `payments` field on `InvoiceResponse` |
| `apps/web/src/features/invoices/components/InvoicePaymentHistory.tsx` | Updated — `PaymentEntry` interface aligned with backend; `customer_payment_comment`/`psp_provider` Reference column; nullable `paid_via`/`paid_at` |
| `apps/web/src/features/invoices/components/InvoiceDetailPage.tsx` | Updated — pass `invoice.payments ?? []` to `<InvoicePaymentHistory>` |
| `apps/web/src/features/dashboard/components/ArSummaryWidget.tsx` | Updated — `next/link` imported; bucket rows + Total Outstanding wrapped in `<Link>` with `?due_before=` params |
| `apps/web/src/features/invoices/components/InvoicesPage.tsx` | Updated — `getAgingBucket()` helper + `AGING_BADGE` map + Aging column after Due column |
| `apps/web/src/features/invoices/hooks/useInvoices.ts` | Updated — `due_before?: string` param added to `UseInvoicesOptions` and `queryFn` |
| `apps/web/src/mocks/handlers/invoiceDetailHandlers.ts` | Updated — `MOCK_INVOICES` record 001 now includes `payments: [...]`; record 002 includes `payments: []` |
| `apps/web/src/features/quotes/components/__tests__/QuoteActionBar.test.tsx` | Updated — +3 new `approved` status tests |
| `apps/web/src/features/dashboard/components/__tests__/ArSummaryWidget.test.tsx` | Updated — `next/link` mock added; +1 bucket links test |
| `apps/web/src/__tests__/batch_ui_fix_1b/invoice_payment_history.integration.test.tsx` | Created — 5 integration tests for InvoicePaymentHistory |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/quotes/components/__tests__/QuoteActionBar.test.tsx` | Unit | +3 | ✅ |
| `features/dashboard/components/__tests__/ArSummaryWidget.test.tsx` | Unit | +1 | ✅ |
| `__tests__/batch_ui_fix_1b/invoice_payment_history.integration.test.tsx` | Integration | 5 | ✅ |

#### Final Verification

```
=== UI - Type Check ===   ✅ 0 errors
=== Web - Type Check ===  ✅ 0 errors
=== Mobile - Type Check === ✅ 0 errors
=== UI - Lint ===          ✅ 0 warnings
=== Web - Lint ===         ✅ 0 warnings
=== Mobile - Lint ===      ✅ 0 warnings
=== UI - Tests ===         ✅ 634 passed
=== Web - Tests ===        ✅ 1261 passed (+10)
=== Mobile - Tests ===     ✅ 669 passed
=== MVP FINAL VERIFICATION COMPLETE ===
```
