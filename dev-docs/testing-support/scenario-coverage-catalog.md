# Scenario Coverage Catalog

**Source**: SD-10 Part A deliverable — `backend/migrations/scripts/README-seed-data.md` §10 SD-10
**Date**: 2026-07-07
**Last gap analysis**: 2026-07-12 (post E2E-B1 — W-05, W-07, W-11, W-14, W-16 closed)
**Author**: Pilot Architect
**Status**: Active — update as new scenarios are seeded or automated

---

- [Scenario Coverage Catalog](#scenario-coverage-catalog)
  - [How to Read This Document](#how-to-read-this-document)
  - [Part 1 — 16 Workflow Coverage Matrix](#part-1--16-workflow-coverage-matrix)
    - [Summary](#summary)
  - [Part 2 — Detailed Scenario Plans](#part-2--detailed-scenario-plans)
    - [CP-1 — Auth + Tenant Isolation](#cp-1--auth--tenant-isolation)
    - [CP-2 — Quote-to-Cash](#cp-2--quote-to-cash)
    - [CP-3 — Dispatch + Field Sync](#cp-3--dispatch--field-sync)
    - [CP-4 — Customer SMS Thread](#cp-4--customer-sms-thread)
    - [CP-5 — Dunning Cycle](#cp-5--dunning-cycle)
  - [Part 3 — Workflows Without Coverage: Seedable vs. External-Blocked](#part-3--workflows-without-coverage-seedable-vs-external-blocked)
    - [Group A — Seedable statically (no external API required)](#group-a--seedable-statically-no-external-api-required)
    - [Group B — Requires external API mock/sandbox](#group-b--requires-external-api-mocksandbox)
  - [Part 4 — Tier 2 Playwright Scope (Web Critical Paths)](#part-4--tier-2-playwright-scope-web-critical-paths)
  - [Part 5 — Maintenance Rules](#part-5--maintenance-rules)
  - [Part 6 — Gap Analysis (2026-07-07, Post SD-01 through SD-10)](#part-6--gap-analysis-2026-07-07-post-sd-01-through-sd-10)
    - [6.1 — What the 5 Critical Paths Actually Cover](#61--what-the-5-critical-paths-actually-cover)
    - [6.2 — Corrections to Part 1 Matrix](#62--corrections-to-part-1-matrix)
    - [6.3 — Complete Gap Register: All 16 Workflows](#63--complete-gap-register-all-16-workflows)
    - [6.4 — True Coverage Summary After E2E-B1 (2026-07-12)](#64--true-coverage-summary-after-e2e-b1-2026-07-12)
    - [6.5 — Recommended Batches](#65--recommended-batches)


---

## How to Read This Document

- **Seed data exists**: A Group D scenario script provides the initial DB state for this workflow
- **Tier 1 automated**: pytest + httpx integration test in `backend/tests/e2e/` exercises this workflow via API
- **Tier 2 automated**: Playwright browser test exercises this workflow through the web UI
- **External API required**: The workflow involves Stripe, QuickBooks, Google OAuth, or Telnyx — cannot be fully automated without a mock layer or sandbox credentials

**Coverage status codes**:
- ✅ — Covered
- ☐ — Not yet covered (gap)
- 🔄 — Partially covered
- ⛔ — Blocked (external dependency)

---

## Part 1 — 16 Workflow Coverage Matrix

| # | Workflow | Key Runtime Tables | Seed Data | Tier 1 (pytest) | Tier 2 (Playwright) | External API? |
|:---|:---|:---|:---:|:---:|:---:|:---:|
| W-01 | Customer receives and replies to SMS | `customer_communication_thread`, `customer_communication_message`, `message_read_state` | ✅ SD-02 | ✅ CP-4 | ✅ cp4_customer_sms | SMS mock |
| W-02 | Tech clocks in + out on a job | `job_time_entry` | ✅ SD-03 | ✅ CP-3 | ✅ cp3_dispatch_field_sync | — |
| W-03 | Tech logs expense on a job | `job_expense` | ✅ SD-03 | ✅ CP-3 | ✅ cp3_dispatch_field_sync | — |
| W-04 | Quote approved, sent to customer, accepted | `quote_acceptance`, `quote_message`, `quote_public_link`, `quote_pending_edit` | ✅ SD-01 (draft only) | ✅ CP-2 | ✅ cp2_quote_to_cash | — |
| W-05 | Invoice created, sent, paid via Stripe | `invoice`, `invoice_public_link`, `payment`, `psp_transaction_log` | ☐ | ✅ cp6_invoice_stripe | ☐ | ⛔ Stripe (skipped — needs real sk_test_ key) |
| W-06 | Voice session creates a quote | `conversation_session`, `conversation_message`, `voice_command_log`, `voice_command_entity_link` | ✅ SD-9 | ☐ | ☐ | ⛔ Whisper/Ollama (E2E — Phase 7) |
| W-07 | NEC calculation run | `nec_calculation_log` | ✅ SD-E2E-B1 | ✅ cp8_nec | ☐ | — |
| W-08 | QuickBooks connected + sync runs | `integration_credential`, `integration_sync_mapping`, `integration_sync_log`, `connector_run_log` | ☐ | ☐ | ☐ | ⛔ QB OAuth |
| W-09 | QB conflict detected and resolved | `integration_sync_conflict` | ☐ | ☐ | ☐ | ⛔ QB OAuth |
| W-10 | Calendar integration synced | `tenant_calendar_integration`, `calendar_sync_log`, `calendar_sync_conflict` | ☐ | ☐ | ☐ | ⛔ Google OAuth |
| W-11 | Mobile tech syncs offline changes | `mobile_sync_session`, `mobile_sync_event`, `mobile_sync_event_audit` | ✅ SD-E2E-B1 | ✅ cp9_mobile_sync | ☐ | — |
| W-12 | Owner escalation created + resolved | `mobile_sync_owner_escalation` | ☐ | ☐ | ☐ | — |
| W-13 | Stripe subscription created, webhook received | `subscription_usage`, `stripe_webhook_event_processed`, `psp_customer` | ☐ | ☐ | ☐ | ⛔ Stripe |
| W-14 | User logs in, MFA enrolled | `user_mfa_method`, `auth_mfa_otp`, `mfa_grace_period_tracking` | ☐ | ✅ CP-1 extended (MFA enrollment) | ✅ cp1_auth_rbac | — |
| W-15 | Help chat session with AI response | `help_chat_session`, `help_chat_message`, `help_article_chunk` | ⛔ SD-09 deferred | ☐ | ☐ | ⛔ Embedding pipeline |
| W-16 | Notification delivered across channels | `notification_event`, `notification_outbox`, `notification_delivery_attempt`, `in_app_notification` | 🔄 SD-03 partial | ✅ cp7_notifications | ☐ | — |

### Summary

| Status | Count |
|:---|:---:|
| Seed data exists | 9 of 16 |
| Tier 1 (pytest) automated | 9 of 16 (CP-1 through CP-9, E2E-B1 ✅ 2026-07-12) |
| Tier 2 (Playwright) automated | 5 of 16 (SD-10 Tier 2 — cp1 through cp5 ✅ 2026-07-07) |
| Requires external API mock | 6 of 16 |

---

## Part 2 — Detailed Scenario Plans

Each scenario below includes the exact sequence of API calls or UI steps, the expected outcome at each step, and the test assertion to validate.

---

### CP-1 — Auth + Tenant Isolation

**Critical path**: Owner, Tech, and Office Staff login paths; tenant ID scoping prevents cross-tenant data access; RBAC enforcement blocks unauthorized operations.

**Seed requirements**: Group C test tenant (always present). No Group D scenario needed.

**API sequence**:

| Step | Action | Endpoint | Expected Outcome | Assertion |
|:---|:---|:---|:---|:---|
| 1 | Owner logs in | `POST /api/v1/auth/login` (or Cognito mock) | JWT returned | `resp.status_code == 200; "access_token" in resp.json()` |
| 2 | Owner accesses dashboard | `GET /api/v1/dashboard` | 200 with BI data | `resp.status_code == 200` |
| 3 | Owner accesses invoices | `GET /api/v1/invoices` | 200 with tenant-scoped list | `all invoice["tenant_id"] == test_tenant_id` |
| 4 | Tech accesses invoices | `GET /api/v1/invoices` (as tech) | 403 or filtered result | Role-based — confirm with `require_permission` check |
| 5 | Create customer in tenant A | `POST /api/v1/customers/test` (tenant A context) | 201, customer_id returned | `resp.status_code == 201` |
| 6 | Access customer_id from tenant B | `GET /api/v1/customers/{customer_id}` (tenant B context) | 404 | `resp.status_code == 404` |

**Tier 1 file**: `backend/tests/e2e/cp1_auth_tenant/test_auth_rbac.py`  
**Tier 2 file**: `frontend/apps/web/src/__tests__/e2e/cp1_auth_rbac.playwright.ts` *(to be created)*

---

### CP-2 — Quote-to-Cash

**Critical path**: Create quote → send to customer → customer accepts via public link → invoice created → payment recorded → `status=paid`.

**Seed requirements**: Group C (test tenant). Group D quote-to-cash scenario (pricebook items).

**API sequence**:

| Step | Action | Endpoint | Expected Outcome | Assertion |
|:---|:---|:---|:---|:---|
| 1 | Create customer | `POST /api/v1/customers/test` | 201, `customer_id` | `resp.status_code == 201` |
| 2 | Create site | `POST /api/v1/sites/test` | 201, `site_id` | `resp.status_code == 201` |
| 3 | Create quote with 1 line item ($150 outlet install) | `POST /api/v1/quotes/test` | 201, `total_cents == 15000`, `status_code == "draft"` | `quote["total_cents"] == 15000` |
| 4 | Send quote | `PATCH /api/v1/quotes/{id}/send` | 200, `status_code == "sent"` | `quote["status_code"] == "sent"` |
| 5 | Customer accepts via public link | `POST /api/v1/quotes/public/{token}/accept` | 200, acceptance recorded | `resp.status_code == 200` |
| 6 | Create invoice from quote | `POST /api/v1/invoices/test` or `POST /api/v1/quotes/{id}/convert` | 201, `total_cents == 15000`, `status_code == "issued"` | `invoice["total_cents"] == 15000; invoice["status_code"] == "issued"` |
| 7 | Record manual payment | `POST /api/v1/payments/test` with `amount_cents=15000, payment_type_code="manual_check"` | 201, `status_code == "succeeded"` | `payment["status_code"] == "succeeded"` |
| 8 | Verify invoice is paid | `GET /api/v1/invoices/{id}` | `status_code == "paid"`, `balance_due_cents == 0` | Both assertions |

**Tier 1 file**: `backend/tests/e2e/cp2_quote_to_cash/test_quote_to_cash.py`  
**Tier 2 file**: `frontend/apps/web/src/__tests__/e2e/cp2_quote_to_cash.playwright.ts` *(to be created)*

---

### CP-3 — Dispatch + Field Sync

**Critical path**: Create job → assign tech → tech logs time entry (2h master rate) → tech logs expense → job marked complete.

**Seed requirements**: Group C (test tenant + labor rates). Group D dispatch scenario (tech user).

**API sequence**:

| Step | Action | Endpoint | Expected Outcome | Assertion |
|:---|:---|:---|:---|:---|
| 1 | Create job (draft) | `POST /api/v1/jobs/test` | 201, `status_code == "draft"` | `job["status_code"] == "draft"` |
| 2 | Assign tech user | `POST /api/v1/jobs/{id}/assignments/test` with `user_id=...0003` | 201, assignment created | `resp.status_code == 201` |
| 3 | Schedule job | `PATCH /api/v1/jobs/{id}` with `status_code="scheduled"` | 200 | `job["status_code"] == "scheduled"` |
| 4 | Log time entry (2h master rate @ $120/hr) | `POST /api/v1/jobs/{id}/time-entries/test` with `hours=2, skill_level_code="master"` | 201, `cost_cents == 24000` | `time_entry["cost_cents"] == 24000` |
| 5 | Log expense (materials $50) | `POST /api/v1/jobs/{id}/expenses/test` with `category_code="materials", cost_cents=5000` | 201 | `resp.status_code == 201` |
| 6 | Mark job complete | `PATCH /api/v1/jobs/{id}` with `status_code="completed"` | 200, `status_code == "completed"` | `job["status_code"] == "completed"` |

**Tier 1 file**: `backend/tests/e2e/cp3_dispatch_field_sync/test_dispatch.py`  
**Tier 2 file**: `frontend/apps/web/src/__tests__/e2e/cp3_dispatch_field_sync.playwright.ts` *(to be created)*

---

### CP-4 — Customer SMS Thread

**Critical path**: Create customer with phone number → send outbound SMS → simulate inbound reply → assert unread count = 1.

**Seed requirements**: Group C (test tenant). Group D customer comms scenario (phone numbers, threads).  
**Mock requirement**: `SMS_CARRIER=mock` — no real Telnyx calls.

**API sequence**:

| Step | Action | Endpoint | Expected Outcome | Assertion |
|:---|:---|:---|:---|:---|
| 1 | Create customer with E.164 phone | `POST /api/v1/customers/test` with `mobile_phone="+15125550199"` | 201, `mobile_phone` stored | `resp.status_code == 201` |
| 2 | Create contact + entity_contact | `POST /api/v1/contacts/test` + link | 201 | `resp.status_code == 201` |
| 3 | Send outbound SMS | `POST /api/v1/comms/send/test` with `customer_id, template_code="on_my_way"` | 201, thread created | `resp.status_code == 201` |
| 4 | Get thread | `GET /api/v1/comms/threads/{thread_id}` | Thread has 1 outbound message, `unread_count == 0` | `thread["unread_count"] == 0` |
| 5 | Simulate inbound reply | `POST /api/v1/webhooks/sms/test` with mock Telnyx inbound payload | 200, message created with `is_unread_inbound=True` | `resp.status_code == 200` |
| 6 | Get updated thread | `GET /api/v1/comms/threads/{thread_id}` | `unread_count == 1` | `thread["unread_count"] == 1` |

**Tier 1 file**: `backend/tests/e2e/cp4_customer_sms/test_sms_thread.py`  
**Tier 2 file**: `frontend/apps/web/src/__tests__/e2e/cp4_customer_sms.playwright.ts` *(to be created)*

---

### CP-5 — Dunning Cycle

**Critical path**: Create overdue invoice → run dunning task → assert `reminder_count=1`, `last_reminder_sent_at` set → record payment → assert dunning stops on next run.

**Seed requirements**: Group C (test tenant). No Group D needed — test creates its own invoice.

**API / task sequence**:

| Step | Action | Method | Expected Outcome | Assertion |
|:---|:---|:---|:---|:---|
| 1 | Create overdue invoice (issued, `due_at` 3 days ago) | `POST /api/v1/invoices/test` + `PATCH` to set `due_at` in past | `status_code == "issued"`, `balance_due_cents > 0` | `invoice["status_code"] == "issued"` |
| 2 | Run dunning impl | `_send_overdue_invoice_reminders_impl(db)` directly | Returns `{"overdue_invoices": ≥1}` | `result["overdue_invoices"] >= 1` |
| 3 | Verify reminder tracking | `GET /api/v1/invoices/{id}` | `reminder_count == 1`, `last_reminder_sent_at IS NOT NULL` | Both assertions |
| 4 | Run dunning again immediately | `_send_overdue_invoice_reminders_impl(db)` | Throttle guard: invoice not re-reminded (count still 1) | `invoice["reminder_count"] == 1` |
| 5 | Record full payment | `POST /api/v1/payments/test` with `amount_cents=full_balance` | Invoice → `status_code == "paid"` | `invoice["status_code"] == "paid"` |
| 6 | Run dunning again | `_send_overdue_invoice_reminders_impl(db)` | Paid invoice excluded: `overdue_invoices` count does not include this invoice | `invoice["reminder_count"]` unchanged |

**Tier 1 file**: `backend/tests/e2e/cp5_dunning_cycle/test_dunning.py`  
**Tier 2 file**: `frontend/apps/web/src/__tests__/e2e/cp5_dunning_cycle.playwright.ts` *(to be created)*

---

## Part 3 — Workflows Without Coverage: Seedable vs. External-Blocked

### Group A — Seedable statically (no external API required)

These 7 workflows have no current seed scenario or test but can be covered without any external API dependency:

| Workflow | What needs to be built |
|:---|:---|
| **NEC calculation run** (W-07) | 1 seed script inserting synthetic `nec_calculation_log` rows; 1 Tier 1 test calling the NEC calculator endpoint |
| **Mobile offline sync** (W-11) | Synthetic `mobile_sync_session` + `mobile_sync_event` rows; Tier 1 test calling the sync endpoint |
| **Owner escalation** (W-12) | Synthetic `mobile_sync_owner_escalation` row; Tier 1 test for the escalation flow |
| **MFA enrollment** (W-14, full) | Extend CP-1 with `user_mfa_method` creation and OTP verification steps |
| **Notification delivery** (W-16) | Use existing `notification_outbox` + `_notification_delivery_attempt` pipeline; seed a notification event and assert delivery attempt is created |
| **Quote-to-Cash full (Stripe payment)** (W-05) | Use Stripe test mode keys + webhook mock; requires `STRIPE_SECRET_KEY=sk_test_*` in `.env.e2e` — already configured |
| **QB sync conflict** (W-09) | Insert synthetic `integration_sync_conflict` row; Tier 1 test for conflict resolution endpoint without needing live QB OAuth |

### Group B — Requires external API mock/sandbox

These 6 workflows require real OAuth flows, sandbox credentials, or live API responses:

| Workflow | Blocker |
|:---|:---|
| QuickBooks connect + sync (W-08) | Needs QB OAuth sandbox credentials; `integration_credential` must be populated via live OAuth redirect |
| Calendar sync (W-10) | Needs Google OAuth sandbox credentials |
| Stripe subscription webhook (W-13) | Can partially test with Stripe test webhook signing, but requires `stripe-cli` for local event forwarding |
| Voice session creates quote (W-06) | Requires Whisper + Ollama running on GPU instance |
| Help chat with AI (W-15) | Requires embedding pipeline (OpenAI `text-embedding-3-small` + pgvector HNSW) |
| QB conflict resolve (W-09 full) | Can partially test with synthetic data; full test requires QB sandbox |

---

## Part 4 — Tier 2 Playwright Scope (Web Critical Paths)

The following 5 web UI flows are the priority Playwright specs. They map 1:1 to the 5 Tier 1 scenarios above, exercising the same critical paths through the browser.

| Playwright Spec | What it validates | Status |
|:---|:---|:---|
| `cp1_auth_rbac.playwright.ts` | Owner session authenticated → dashboard renders → invoices scoped to tenant → quotes RBAC gate allows | ✅ SD-10 Tier 2 (2026-07-07) |
| `cp2_quote_to_cash.playwright.ts` | Quotes list shows $150 seeded quote → sent status badge → invoices list renders → overdue toggle shows badge | ✅ SD-10 Tier 2 (2026-07-07) |
| `cp3_dispatch_field_sync.playwright.ts` | Jobs list renders seeded jobs → Scheduled badge → Completed badge → convert-to-invoice action visible | ✅ SD-10 Tier 2 (2026-07-07) |
| `cp4_customer_sms.playwright.ts` | Comms page container renders → Communications header → recent-comms-table visible → SMS channel badge shown | ✅ SD-10 Tier 2 (2026-07-07) |
| `cp5_dunning_cycle.playwright.ts` | Invoices page has overdue toggle → clicking filter shows past-due invoice → Overdue badge renders → aria-pressed toggles | ✅ SD-10 Tier 2 (2026-07-07) |

See `dev-docs/implementation-prompts/seed-data/batch-sd-10-playwright-react-engr-prompt.md` for the implementation prompt.

---

## Part 5 — Maintenance Rules

1. **Update this catalog when a new seed scenario script is created** — add ✅ to the Seed Data column for every workflow the script covers.
2. **Update this catalog when a new Tier 1 or Tier 2 test is added** — mark the relevant cell ✅ with the test file path.
3. **Update this catalog when any workflow status changes** — if a gap is closed, a CP is promoted from smoke to full workflow, a new CP is designed, or a new workflow is discovered, this document must be updated before the batch is marked complete.
4. **The "External API?" column does not change** — it reflects whether real external infrastructure is needed. The workflow coverage status is in the Tier 1/2 columns.
5. **Never mark a workflow ✅ based on a passing HTTP 200** — the test must assert on specific business outcome values (see CP-2 example: `invoice["total_cents"] == 15000`, not just `resp.status_code == 200`).
6. **Distinguish smoke from workflow E2E in the Tier 2 column** — a Playwright spec that verifies a page renders with seeded data is `✅ (smoke)`. A Playwright spec that executes the full workflow (fills forms, submits, asserts DB outcomes) is `✅ (full)`. Never collapse these two into a single ✅.
7. **Owner**: Pilot Architect maintains this document at batch design time. Python Engineer and React Engineer update ✅ markers when their tests pass.

---

---

## Part 6 — Gap Analysis (2026-07-07, Post SD-01 through SD-10)

This section is the authoritative gap assessment produced after the SD sprint completed. It corrects documentation inaccuracies, explains architectural scope decisions, maps the 5 CPs to the 16 workflows, and lists every remaining gap on the path to full automated E2E coverage.

---

### 6.1 — What the 5 Critical Paths Actually Cover

The 5 CPs defined in Part 2 do **not** cover all 16 workflows. They cover 6 of 16:

| CP | Workflows Covered | Workflows Not Covered By This CP |
|:---|:---|:---|
| CP-1 Auth + RBAC | W-14 (login only — MFA enrollment steps absent) | MFA full enrollment is uncovered |
| CP-2 Quote-to-Cash | W-04 (quote approved → accepted) | W-05 (invoice paid via Stripe) is a separate workflow — not covered by CP-2 |
| CP-3 Dispatch + Field Sync | W-02 (time entry), W-03 (expense) | — |
| CP-4 Customer SMS | W-01 (SMS thread) | — |
| CP-5 Dunning Cycle | W-16 (partial — dunning fires a notification but the notification delivery pipeline itself is not asserted) | — |
| **Not covered by any CP** | W-05, W-06, W-07, W-08, W-09, W-10, W-11, W-12, W-13, W-14 (full MFA), W-15, W-16 (full notification delivery) | 11 of 16 workflows have no CP assigned |

The end goal of this catalog is **full automated E2E coverage for every workflow that does not require a live external API sandbox**. The 5 CPs are the starting point, not the finish line.

---

### 6.2 — Corrections to Part 1 Matrix

#### Correction A — W-05 (Invoice/Stripe Payment): the Stripe key slot exists but is a placeholder

**Current matrix**: Tier 1 = ☐, External API = ⛔ Stripe
**What the file shows**: `backend/.env.e2e` contains:
```
STRIPE_SECRET_KEY=sk_test_e2e_placeholder
STRIPE_WEBHOOK_SECRET=whsec_test_e2e_placeholder
```
These are **placeholders**, not real Stripe test-mode keys. The slot and pattern are correct; real keys need to be pulled from the Stripe dashboard (test mode) and placed in `.env.e2e`. This is a ~5-minute configuration step, not an infrastructure gap.

**Why this matters**: Part 3 Group A of this document says W-05 "requires `STRIPE_SECRET_KEY=sk_test_*` in `.env.e2e` — already configured." That statement is inaccurate — the key slot exists but the real test key is not populated. Once Tom adds the real `sk_test_` key from the Stripe dashboard, W-05 can be covered by a Tier 1 test without any other infrastructure change.

**Action**: Tom populates `STRIPE_SECRET_KEY` in `.env.e2e` with the actual Stripe test-mode secret key → then a Python Engineer can write `cp6_invoice_stripe_payment`.

---

#### Correction B — Tier 2 Playwright specs are UI smoke tests, not full workflow E2E

**What the Playwright specs do**: They verify that pages **render with seeded data** and key UI states are visible (badges, table rows, filter toggles, RBAC gates). Example: `cp2_quote_to_cash.playwright.ts` verifies the Quotes list page shows the $150 draft quote from the seed data. It does **not** fill out a form, click "Send Quote," simulate a customer acceptance, or assert that an invoice was created.

**Why they were scoped this way**: The SD-10 Playwright batch prompt scoped Tier 2 to "smoke test the 5 critical path UIs against seeded data." This was the right first pass — it ensures the app is up and data is visible before advancing to full workflow automation. What was **missing from the SD-10 prompt**: an explicit definition of Phase 2 Playwright work covering full UI workflow automation (form fills → submits → outcome assertions).

**Impact of the inaccuracy**: The current ✅ marks in W-01 through W-04 Tier 2 column create false confidence. If the "Send Quote" button silently fails or the "Accept" public link endpoint returns a 500, the Playwright smoke test will not catch it. Tier 2 smoke ≠ Tier 2 full workflow.

**Resolution applied**: Part 5 Maintenance Rule 6 now requires `✅ (smoke)` vs. `✅ (full)` distinction to be used in this matrix going forward.

---

### 6.3 — Complete Gap Register: All 16 Workflows

The end goal is fully automated E2E coverage for every workflow that does not require a live external OAuth flow or GPU hardware. The table below shows the complete gap state across all 16 workflows after the SD sprint:

| # | Workflow | Tier 1 Gap | Tier 2 Gap | Path | Priority |
|:---|:---|:---|:---|:---|:---:|
| W-01 | Customer SMS thread | ✅ CP-4 covers | ✅ smoke only — no workflow E2E | Phase 2 Playwright: compose + send + assert unread count in UI | P2 |
| W-02 | Tech clocks in + out | ✅ CP-3 covers | ✅ smoke only | Phase 2 Playwright: time entry form → submit → assert cost_cents in UI | P2 |
| W-03 | Tech logs expense | ✅ CP-3 covers | ✅ smoke only | Phase 2 Playwright: expense form → submit → assert in job detail UI | P2 |
| W-04 | Quote approved, sent, accepted | ✅ CP-2 covers (draft→sent→accepted) | ✅ smoke only | Phase 2 Playwright: Send Quote action → public link accept → assert status badge | P2 |
| W-05 | Invoice created, sent, paid (Stripe) | ✅ `cp6_invoice_stripe` (skipped when placeholder key — needs real sk_test_ key) | ☐ | E2E-B1 ✅ done — full execution requires Tom to populate `STRIPE_SECRET_KEY` in `.env.e2e` | **P0 ✅** |
| W-06 | Voice session creates a quote | ☐ | ☐ | Requires Whisper + Ollama on GPU — Phase 7 | P3 |
| W-07 | NEC calculation run | ✅ `cp8_nec` — 3 tests | ☐ | E2E-B1 ✅ done | P1 ✅ |
| W-08 | QuickBooks connected + sync | ☐ | ☐ | Requires live QB OAuth sandbox credentials — Phase 7 | P3 |
| W-09 | QB conflict detected + resolved | ☐ (conflict resolution endpoint can be tested without live QB) | ☐ | E2E-B2: insert synthetic `integration_sync_conflict` row; test resolution endpoint without live QB | P2 |
| W-10 | Calendar sync | ☐ | ☐ | Requires Google OAuth sandbox — Phase 7 | P3 |
| W-11 | Mobile offline sync | ✅ `cp9_mobile_sync` — 3 tests | ☐ | E2E-B1 ✅ done | P1 ✅ |
| W-12 | Owner escalation created + resolved | ☐ No seed, no Tier 1 | ☐ | E2E-B2: synthetic `mobile_sync_owner_escalation` row + escalation endpoint test | P2 |
| W-13 | Stripe subscription webhook received | ☐ | ☐ | E2E-B2: `stripe-cli` replay of `customer.subscription.created` event (requires real Stripe test key — same dependency as W-05) | P2 |
| W-14 | User logs in, MFA enrolled | ✅ CP-1 extended — `TestMfaEnrollment` class verifies `user_mfa_method` row creation | ✅ smoke only (login path) | E2E-B1 ✅ done | **P0 ✅** |
| W-15 | Help chat session with AI response | ☐ | ☐ | Blocked: embedding pipeline + pgvector corpus required (SD-09 deferred) — Phase 7 | P3 |
| W-16 | Notification delivered across channels | ✅ `cp7_notifications` — 3 tests invoking `_send_notification_impl()` and asserting `notification_delivery_attempt` row | ☐ | E2E-B1 ✅ done | P1 ✅ |

**Legend**: P0 = blocks beta launch · P1 = should cover before beta · P2 = before GA / Phase 7 entry · P3 = Phase 7 or post-GA

---

### 6.4 — True Coverage Summary After E2E-B1 (2026-07-12)

| Metric | Post-SD-10 | Post-E2E-B1 |
|:---|:---:|:---:|
| Workflows with seed data | 7 / 16 | 9 / 16 ✅ |
| Workflows with Tier 1 full automated test | 5 / 16 | **9 / 16** (CP-1 through CP-9) |
| Workflows with Tier 2 full workflow E2E | 0 / 16 | **0 / 16** — all Tier 2 specs are smoke only |
| Workflows with Tier 2 smoke coverage | 5 / 16 | 5 / 16 |
| Workflows with no CP at all | 11 / 16 | **7 / 16** |
| P0 gaps closed | — | **2** — W-05 (test written, skipped pending sk_test_), W-14 (MFA enrollment verified) |
| P1 gaps closed | — | **3** — W-07, W-11, W-16 ✅ all closed |
| P2 gaps remaining | — | **4** — W-09, W-12, W-13, Tier 2 workflow for W-01 through W-04 |
| P3 / externally blocked | — | **6** — W-06, W-08, W-10, W-15, W-13 full |

---

### 6.5 — Recommended Batches

#### Pre-Beta: E2E-B1 (Python Engineer, ~1.5 days)

Closes all P0 and P1 gaps. **Prerequisite for E2E-B1-T1**: Tom must populate `STRIPE_SECRET_KEY` in `backend/.env.e2e` with the real Stripe test-mode secret key from the Stripe dashboard before this batch starts.

| Task | What | Output File(s) |
|:---|:---|:---|
| **E2E-B1-T0** | Tom: populate real `sk_test_` key in `.env.e2e` | `backend/.env.e2e` (not committed — local only) |
| **E2E-B1-T1** | Write W-05 Tier 1 test (invoice created → sent → paid via Stripe test mode) | `backend/tests/e2e/cp6_invoice_stripe/test_invoice_stripe.py` |
| **E2E-B1-T2** | Extend CP-1 with MFA enrollment + OTP verification steps | `backend/tests/e2e/cp1_auth_tenant/test_auth_rbac.py` |
| **E2E-B1-T3** | Write W-16 notification delivery Tier 1 test | `backend/tests/e2e/cp7_notifications/test_notification_delivery.py` |
| **E2E-B1-T4** | Write W-07 NEC seed + Tier 1 test | `backend/migrations/scripts/seed_scenario_nec.py` + `backend/tests/e2e/cp8_nec/test_nec_calculation.py` |
| **E2E-B1-T5** | Write W-11 mobile sync seed + Tier 1 test | `backend/migrations/scripts/seed_scenario_mobile_sync.py` + `backend/tests/e2e/cp9_mobile_sync/test_mobile_sync.py` |

**Pass gate**: `pytest -m e2e --tb=short` shows 0 failures across all CP-1 through CP-9 test files.

---

#### Before GA: E2E-B2 (Python Engineer + React Engineer, ~2 days)

Closes P2 gaps — no new external infrastructure needed:

| Task | What | Assignee |
|:---|:---|:---|
| **E2E-B2-T1** | W-09 QB conflict: insert synthetic conflict row + Tier 1 resolution endpoint test | Python Engineer |
| **E2E-B2-T2** | W-12 Owner escalation: synthetic row + Tier 1 escalation creation + resolution test | Python Engineer |
| **E2E-B2-T3** | W-13 Stripe subscription webhook: `stripe-cli` replay test (requires Stripe test key from E2E-B1-T0) | Python Engineer |
| **E2E-B2-T4** | Tier 2 Phase 2: Playwright full workflow specs for W-01 (SMS compose + send), W-02 (time entry form), W-03 (expense form), W-04 (Send Quote + accept) | React Engineer |

---

#### Phase 7: E2E-B3 (Post-Beta, Requires External Sandboxes)

| Task | Blocker |
|:---|:---|
| W-06 Voice AI session | GPU instance + Whisper/Ollama must be running in CI |
| W-08 QB OAuth connect + sync | QB sandbox app credentials + OAuth redirect in CI |
| W-10 Calendar sync | Google OAuth sandbox credentials |
| W-15 Help chat AI | Embedding pipeline + pgvector corpus populated |

---

*This document is the authoritative scenario coverage reference for the Pilot for Trades E2E test harness. For the harness architecture design (tier selection, CI/CD, seeding strategy), see `dev-docs/architecture-design/batch-designs/batch-sd-design-sprint-design.md` §SD-10 Part B.*
