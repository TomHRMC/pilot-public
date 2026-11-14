# Backend Ledger v6 — Cross-Check Findings Update Instructions

**Date**: April 30, 2026
**Source of findings**: `pilot-ap-prd-arch-cross-check-w-backend-adds.md` v2.0 (April 30, 2026)
**Scope**: Apply all 12 cross-check findings (10 PRD gaps G1–G10 + 2 net-new arch findings A1, A6) to backend ledger v6 as scope additions, verification notes, or doc cleanup as appropriate.

The cross-check found three categories of items:

- **Category 1 — Confirmed scope additions** (must add to backend ledger): G5, G6, A1, plus a B13/A70 integration note for G3
- **Category 2 — Verification before implementing** (note in relevant batches): G1, G2, G3, G4, G7, G9
- **Category 3 — Doc cleanup or scope clarification** (no new code, just clearer docs): G8, G10, A6

This update applies all three categories to the v6 ledger. After applying, the ledger reflects all known scope and surfaces verification work to perform before relevant batches start.

---

## Edit 1 — Doc header version bump

**Find** (line 4):

```markdown
**Version**: 6 (Pass 4 design phase complete — A1–A88 cumulative; consolidates all interim versions v5.x; ready as backend implementation source of truth)
```

**Replace with**:

```markdown
**Version**: 6.1 (Pass 4 design phase complete + cross-check findings applied — A1–A88 cumulative plus TCPA opt-in/opt-out scope additions to A59, Stripe webhook dedup added to A76, password change cross-device session invalidation note in A70/B13 context. Verification notes added for receipt OCR, profile/password endpoints, dunning, schedule history. Cross-check audit completed April 30, 2026.)
```

Update "Last Updated" line:

```markdown
**Last Updated**: April 30, 2026 (Cross-check findings applied — see "Cross-Check Update Notes" section)
```

---

## Edit 2 — Add new section: "Cross-Check Update Notes" near the top

**Insertion point**: After the existing Status tracker (around line 65 if your TOC is in that area; locate the end of the "Status tracker" sub-list and insert after).

**Content to insert**:

```markdown
---

## Cross-Check Update Notes (April 30, 2026)

A formal cross-check of `mvp-prd.md` v3.1 (final) and `mvp-arch.md` v5 against the backend additions A2–A88 was performed at Pass 4 close. The cross-check identified 12 findings, all addressed in this v6.1 update. Findings fall into three categories:

**Category 1 — Confirmed scope additions** (real new work added to existing additions; no net-new addition numbers):

- **A59 expanded** — TCPA SMS STOP keyword detection + opt-out handler + 5 new `customer` table columns (`sms_opted_out`, `sms_opt_out_at`, `sms_opt_in_consent`, `sms_opt_in_at`, `sms_opt_in_source`). **TCPA legal compliance gap; must be implemented before B11 is considered complete.**
- **A65 extended** — outbound block when `customer.sms_opted_out = TRUE` (`check_quota` returns blocked); ensures Pilot doesn't send SMS to opted-out customers.
- **A76 expanded** — `stripe_webhook_event_processed` dedup table + handler check before processing webhook events. **Stripe data integrity gap; gates correct payment recording.**
- **A70 + B13 integration note** — password change endpoint must call A70's `revoke-others` logic on success. Cross-device session invalidation per arch doc §4.8.1.

**Category 2 — Verification before implementing** (notes added to relevant batches; not new scope until verification confirms missing):

- **G1 (Receipt OCR)** — verify pre-existing pipeline before B3 starts; if missing, becomes A89.
- **G2 + G3 (Profile/Password endpoints)** — verify existing endpoints before B13 starts; existing endpoints likely sufficient with the A70 integration note above.
- **G4 (Tax Setup JIT 412 response)** — verify existing invoice endpoint returns 412 with structured payload when tax not configured; precondition check for tax setup.
- **G7 (Automated Dunning)** — verify pre-existing Celery task before B5 or B15 starts; if missing, add to relevant batch scope.
- **G9 (Schedule History per Job endpoint)** — verify dedicated `GET /api/v1/jobs/{job_id}/schedule-history` endpoint exists; if missing, add to B3 scope.

**Category 3 — Doc cleanup / scope clarification** (no new code; clarifies existing scope):

- **G8 (Trial Expiration Warning Sequence)** — A73 scope note clarifies the 4-step warning cadence (7d, 3d, 1d, 0d) per arch doc §4.7.5.
- **G10 (Calendar auto-expire mechanism)** — A34 scope note clarifies that arch doc §13.5 uses BOTH a separate `calendar_conflict_auto_expire_enabled` boolean AND nullable days integer; implementation must include both.
- **A6 (Arch doc §15.13 stale title)** — documentation-only fix; no code impact. Arch doc §15.13 title should be updated from "No Background Sync in MVP" to "Sync Triggers (Foreground + Background)" — implementation reference is §16.12, not §15.13.

**Pre-batch verification checklist** (run via postgres-local MCP before starting relevant batches):

1. **Before B3**: `SELECT routine_name FROM information_schema.routines WHERE routine_name LIKE '%receipt%' OR routine_name LIKE '%ocr%'` — resolves G1
2. **Before B3**: Check `api/routes/jobs.py` for schedule-history endpoint — resolves G9
3. **Before B5 or B15**: Check `tasks/` directory for dunning-related Celery task — resolves G7
4. **Before B11**: `SELECT column_name FROM information_schema.columns WHERE table_name = 'customer' AND column_name LIKE 'sms%'` — resolves G5/G6 (verifies which TCPA columns already exist; informs A59 migration scope)
5. **Before B13**: Check `api/routes/` directory for `profile.py`, `password.py`, or equivalent — resolves G2/G3
6. **Before B14**: Check existing invoice endpoint for 412 precondition response on missing tax setup — resolves G4

The cross-check report itself lives in: `pilot-app-prd-arch-cross-check-w-backend-adds.md` v2.0.

---
```

---

## Edit 3 — A56 audit pass clarification (small note addition)

**Find** the A56 effort estimate line (around line 1834):

```markdown
**Effort estimate**: Medium — 4 days. The category registry itself is a small schema; the audit pass over existing firing sites is the cost driver. Each firing site needs a code change to declare its category and (where applicable) sub-trigger.
```

**Replace with**:

```markdown
**Effort estimate**: Medium — 4 days. The category registry itself is a small schema; the audit pass over existing firing sites is the cost driver. Each firing site needs a code change to declare its category and (where applicable) sub-trigger.

**Audit pass deliverable** (per A56): a checklist tracked alongside this addition listing each of the ~8 existing `notification_outbox.create()` call sites with assigned `category_id` and `sub_trigger_id`. This deliverable is part of A56 completion criteria — A56 is not done until every existing firing site has a category. Categorization choices should follow the 8 categories defined in Tier 2 #5 spec Decision 2.
```

This makes the audit pass a tracked deliverable rather than a vague mention, which is the cross-check-equivalent improvement.

---

## Edit 4 — A59 expanded scope (TCPA STOP handling + opt-out columns)

**Find** the entire A59 section (lines 1904–1925).

**Replace the section content** (everything between the `### A59...` header and the next `### A60...` header) with this expanded version:

```markdown
### A59. Telnyx Webhook Handler + Carrier-Agnostic Adapter Layer + TCPA Opt-In/Opt-Out Tracking

**Triggered by**: Tier 1.5 Decisions 3, 13 — inbound SMS receive infrastructure with carrier abstraction. **Cross-check finding G5/G6 (April 30, 2026) added TCPA opt-in/opt-out scope to this addition** — these are legal compliance requirements per TCPA law and A2P 10DLC carrier rules.

**Scope**:
- New module `services/sms_carrier.py` with abstract `SmsCarrier` interface
  - Methods: `provision_number()`, `send_message()`, `verify_webhook_signature()`, `parse_inbound_webhook()`, `get_delivery_status()`, `release_number()`
- `TelnyxSmsCarrier(SmsCarrier)` implementation:
  - Webhook signature verification using Telnyx's public-key signature scheme
  - `parse_inbound_webhook()` extracting sender, recipient, body, timestamp, carrier_message_id
  - **STOP keyword detection** — detect: STOP, STOPALL, UNSUBSCRIBE, QUIT, CANCEL, END, ARRET (case-insensitive); exact-match on body content (no partial-match — "I want to STOP working on this" should not trigger opt-out)
  - `send_message()` calling Telnyx send API
  - `provision_number()` calling Telnyx number search + acquire APIs
  - `release_number()` calling Telnyx number release API
  - `get_delivery_status()` calling Telnyx message status API
- `MockSmsCarrier(SmsCarrier)` for integration testing — captures calls without making real API requests; supports STOP-keyword test injection
- New API endpoint: `POST /api/v1/webhooks/sms/telnyx-inbound` — receives Telnyx webhook
- Configuration: `SMS_CARRIER` env var (`telnyx | mock`); same carrier for all tenants on a deployment
- Failure handling: signature verification failure returns 401 (Telnyx will retry); routing failure parks inbound in unrouted queue per A60

**Schema additions to `customer` table** (TCPA compliance — verify with postgres-local MCP before writing migration; columns may partially pre-exist):

```sql
ALTER TABLE customer ADD COLUMN sms_opted_out BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE customer ADD COLUMN sms_opt_out_at TIMESTAMPTZ NULL;
ALTER TABLE customer ADD COLUMN sms_opt_in_consent BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE customer ADD COLUMN sms_opt_in_at TIMESTAMPTZ NULL;
ALTER TABLE customer ADD COLUMN sms_opt_in_source TEXT NULL;
    -- 'explicit_checkbox' | 'inbound_initiated' | 'verbal_captured'
```

**STOP routing flow**:
- STOP-detected inbound bypasses normal threading (`route_inbound_message()` per A60)
- Routes directly to new handler `handle_sms_opt_out(customer_id, opt_out_message)`:
  - Sets `customer.sms_opted_out = TRUE`
  - Sets `customer.sms_opt_out_at = NOW()`
  - Records opt-out event in audit log
  - Sends confirmation reply per Telnyx requirements ("You've been unsubscribed. Reply START to opt back in.")
- Future inbound from this customer: continue to be received and threaded normally; outbound is blocked (per A65 quota check extension)

**Opt-in tracking** — non-STOP inbound from previously opted-out customer triggers opt-in re-establishment:
- If `customer.sms_opted_out = TRUE` and inbound contains "START" or "UNSTOP" or "YES" (case-insensitive exact-match)
- Sets `customer.sms_opted_out = FALSE`; clears `sms_opt_out_at`
- Sets `customer.sms_opt_in_consent = TRUE`; `sms_opt_in_at = NOW()`; `sms_opt_in_source = 'inbound_initiated'`
- Sends confirmation reply ("You've been resubscribed.")

**Opt-in capture during normal flow** — for new customers being added to the tenant:
- Customer creation form must include opt-in checkbox (UI work; backend stores result)
- Sets `customer.sms_opt_in_consent` based on checkbox; `sms_opt_in_at` to creation time; `sms_opt_in_source = 'explicit_checkbox'`
- For verbally-captured opt-in (e.g., during a service call), tenant can update via customer record edit; sets `sms_opt_in_source = 'verbal_captured'`

**Audit log capture**:
- All STOP / opt-out events written to `audit_log` with event type `sms_opt_out`
- All opt-in events written with event type `sms_opt_in`
- TCPA-required: audit log must be queryable for compliance review

**Architectural pattern**: carrier-agnostic adapter — generalizable to other external service integrations (payment processors, email services, mapping providers). Future Phase 2 surfaces inherit this approach.

**Effort estimate**: Medium — 4–5 days (interface + Telnyx implementation + Mock implementation + webhook endpoint + signature verification + STOP detection + opt-in/opt-out flow + 5 customer schema columns + audit log integration). **+1.5–2 days versus original A59 estimate due to TCPA additions per cross-check finding G5/G6.**
```

---

## Edit 5 — A65 extended scope (outbound block on opted-out customers)

**Find** the bullet in A65 about "Failed send refund" (around line 2085):

```markdown
- Failed send refund: if `SmsCarrier.send_message()` returns failure, `consume_quota` is rolled back atomically
```

**Replace with**:

```markdown
- Failed send refund: if `SmsCarrier.send_message()` returns failure, `consume_quota` is rolled back atomically
- **TCPA opt-out enforcement** (per A59): `check_quota()` first checks `customer.sms_opted_out` for the recipient customer. If TRUE, returns `{allowed: false, blocked_reason: 'customer_opted_out'}`. Outbound SMS to opted-out customers is blocked at the quota layer regardless of available segments. This ensures Pilot does not send SMS to customers who have opted out, satisfying TCPA legal requirements.
- Audit log entry on blocked-by-opt-out attempts for compliance review
```

---

## Edit 6 — A70 expanded scope (password change cross-device session invalidation)

**Find** the A70 APIs section (around line 2284):

```markdown
**APIs**:
- `GET /api/v1/users/me/sessions` — list all active sessions for requesting user
- `DELETE /api/v1/users/me/sessions/{session_id}` — revoke a specific session (invalidate refresh token; clear access token cache)
- `POST /api/v1/users/me/sessions/revoke-others` — bulk revoke all sessions except the current one
```

**Replace with**:

```markdown
**APIs**:
- `GET /api/v1/users/me/sessions` — list all active sessions for requesting user
- `DELETE /api/v1/users/me/sessions/{session_id}` — revoke a specific session (invalidate refresh token; clear access token cache)
- `POST /api/v1/users/me/sessions/revoke-others` — bulk revoke all sessions except the current one

**Password change cross-device session invalidation** (per cross-check finding G3 / arch doc §4.8.1): when implementing B13, the password change endpoint (likely pre-existing per cross-check finding A4 — verify via `/api/v1/users/me/change-password` or equivalent) must be wired to call the same logic as `revoke-others` on successful password change. This ensures all sessions other than the current one are auto-revoked when password changes — security best practice.

**B13 implementation note**: pre-batch verification finds the existing password change endpoint; B13 adds the post-success hook to call `revoke-others` logic (extracted from the API handler into a shared service function so both the API and the password-change hook can call it). Estimated 0.5 day of integration work in B13 scope.
```

---

## Edit 7 — A73 trial expiration warning sequence clarification

**Find** the A73 section. The trial expiration enforcement description should be augmented with the explicit warning sequence.

**Find** the "Trial expiration enforcement" sub-section (around line 2378–2384):

```markdown
**Trial expiration enforcement**:
- New Celery task `enforce_trial_expirations` runs hourly
- For tenants where `trial_ends_at <= now()` and tier is still trial, transitions to `trial_expired` state
- Sends paywall notification (push + email + in-app banner)
```

**Replace with**:

```markdown
**Trial expiration enforcement**:
- New Celery task `enforce_trial_expirations` runs hourly
- For tenants where `trial_ends_at <= now()` and tier is still trial, transitions to `trial_expired` state
- Sends paywall notification (push + email + in-app banner)

**Pre-expiration warning sequence** (per cross-check finding G8 / arch doc §4.7.5): four scheduled warning notifications fire before expiration to give tenants time to convert:

| Days before expiration | Notification urgency | Channels | Notes |
| :--- | :--- | :--- | :--- |
| 7 days | Gentle | Push + email + in-app banner | "Your trial ends in 7 days. Pick a plan to keep using Pilot." |
| 3 days | More urgent | Push + email + in-app banner | Same channels, more urgent copy |
| 1 day | Final | Push + email + in-app banner | Final notice |
| 0 days (day of expiration) | Critical | Push + email + in-app banner; paywall activates | Tenant transitions to trial_expired state at scheduled hour |

Implementation: `enforce_trial_expirations` Celery task runs hourly and dispatches the appropriate warning based on time-to-expiration. Notification routes through `notification_outbox` per Tier 2 #5 "Billing" or "System announcements" category (final decision per Pilot operator).

In-app banner persistence: starting 7 days before expiration, an in-app banner appears in the active session and persists until tenant either upgrades or expiration occurs. Banner is dismissable per session but reappears on next session.
```

---

## Edit 8 — A34 calendar auto-expire mechanism clarification

A34 is in the Pass 3 Flow 6 section (around line 1118 area). Locate it.

<br>

**Find** the A34 schema description (the `calendar_conflict_auto_expire_*` settings list).

If your A34 only mentions nullable-days as the disable mechanism, **add this clarification note** at the end of the A34 scope description (just before the Effort estimate line):

```markdown
**Cross-check finding G10 clarification (April 30, 2026)** — per arch doc §13.5, the calendar auto-expiry implementation uses BOTH mechanisms together:

- `calendar_conflict_auto_expire_enabled` — boolean (default TRUE); FALSE disables auto-expiry entirely for the tenant regardless of days setting
- `calendar_conflict_auto_expire_days` — integer NULL; NULL = use system default of 30; integer = use this value
- `calendar_conflict_pre_warning_days` — integer NULL; NULL = use system default of 7

Effective resolution logic:
1. If `calendar_conflict_auto_expire_enabled = FALSE` → skip auto-expiry entirely; conflicts persist until manually resolved
2. If TRUE → apply `calendar_conflict_auto_expire_days` (NULL → use system default of 30)
3. Pre-warning sent at `(auto_expire_days - pre_warning_days)` (NULL pre-warning → use system default of 7)

A34 implementation includes all three columns. The boolean is the on/off switch; the nullable integer is the value override.
```

---

## Edit 9 — A76 expanded scope (Stripe webhook dedup table)

**Find** the A76 "Stripe Webhooks" section (around lines 2475–2483):

```markdown
**Stripe Webhooks**:
- New endpoint `POST /api/v1/webhooks/stripe` — receives Stripe webhook payloads with signature verification
- Handles events:
  - `customer.subscription.created` — confirm tier activation
  - `customer.subscription.updated` — handle tier changes
  - `invoice.paid` — confirm successful payment
  - `invoice.payment_failed` — trigger payment retry / paywall
  - `customer.subscription.deleted` — handle cancellation
- Stripe webhook signing secret stored in environment
```

**Replace with**:

```markdown
**Stripe Webhooks**:
- New endpoint `POST /api/v1/webhooks/stripe` — receives Stripe webhook payloads with signature verification
- Handles events:
  - `customer.subscription.created` — confirm tier activation
  - `customer.subscription.updated` — handle tier changes
  - `invoice.paid` — confirm successful payment
  - `invoice.payment_failed` — trigger payment retry / paywall
  - `customer.subscription.deleted` — handle cancellation
- Stripe webhook signing secret stored in environment

**Webhook idempotency dedup** (per cross-check finding A1 / arch doc §20.6) — Stripe explicitly delivers webhooks multiple times and recommends idempotency. Without dedup, a webhook retry (e.g., `invoice.paid` received twice) could double-record a payment or double-activate a subscription tier. Dedup table:

```sql
stripe_webhook_event_processed (
    event_id      TEXT PRIMARY KEY,    -- Stripe event ID (e.g., "evt_1abc...")
    processed_at  TIMESTAMPTZ NOT NULL,
    event_type    TEXT NOT NULL
)
```

Handler flow:
1. On webhook arrival, after signature verification, check `event_id` in `stripe_webhook_event_processed`
2. If already exists → return 200 idempotently without reprocessing
3. If not → INSERT row + process event → return 200
4. Use SQL transaction to make insert + processing atomic; if processing fails, don't mark as processed

Cleanup: `cleanup_incomplete_stripe_payment_intents` Celery task per §3.2 cleans up abandoned payment intents; the dedup table itself does not require cleanup (event IDs are small text; retention is indefinite for audit purposes).
```

**Update A76 effort estimate** (around line 2498):

```markdown
**Effort estimate**: Medium-Large — 5.5–6.5 days. Stripe Elements integration + Subscriptions API + webhooks + payment failure handling + webhook dedup table. Stripe API integration is the cost driver; +0.5 day for webhook dedup per cross-check finding A1.
```

---

## Edit 10 — Add verification checklist items to relevant batch entries (where applicable)

The cross-check identified several "verify before implementing" items. The cleanest way to surface these is by adding small notes to the relevant addition descriptions. Three additions get verification notes:

### A14 (B3 — Field Operations: ETC Capture)

**Find** the A14 Effort estimate.

**Add this note above it**:

```markdown
**Cross-check verification before B3 starts** (April 30, 2026):

- **G1 (Receipt OCR Automation)**: PRD §3.4 mentions Textract/GPT-4V receipt parsing pipeline. Verify pre-existing — run `SELECT routine_name FROM information_schema.routines WHERE routine_name LIKE '%receipt%' OR routine_name LIKE '%ocr%'` plus check `tasks/` directory for OCR-related Celery tasks. If missing, add as A89 to B3 scope (estimated 3–5 days: async Celery task + Textract integration + cost_cents auto-fill + retry handling). Likely pre-existing.
- **G9 (Schedule History per Job endpoint)**: PRD §3.14 mentions "Dispatch board supports a 'history' view per job." Verify dedicated `GET /api/v1/jobs/{job_id}/schedule-history` endpoint exists. If missing, add to B3 scope (estimated 0.5–1 day: endpoint reading from existing `audit_log` filtered for job entity).
```

### A68 / B13 (Account Security)

**Find** the A68 Effort estimate.

**Add this note above it**:

```markdown
**Cross-check verification before B13 starts** (April 30, 2026):

- **G2 (User Profile Management endpoints)**: PRD §3.5 + arch doc §4.8 imply profile management uses existing user model. Verify endpoints exist: `PATCH /api/v1/users/me/profile` (display name, time zone, phone, language); `POST /api/v1/users/me/profile/photo` (S3 presigned URL upload). Likely pre-existing.
- **G3 (Password change cross-device session invalidation)**: per A70 expanded scope above, B13 must wire the password change endpoint to A70's revoke-others logic. Verify password change endpoint exists; add the integration hook in B13 (0.5 day).
- **G4 (Tax Setup JIT 412 response)**: arch doc §4.7.6 specifies invoice generation returns 412 (Precondition Required) with structured payload when tax setup is incomplete. Verify existing invoice creation endpoint enforces this precondition. If missing, add to B14 (or earliest invoice-related batch) scope (estimated 0.5–1 day: precondition check before invoice creation).
```

---

## Edit 11 — Note about §15.13 (no ledger change; arch doc cleanup)

This is a Category 3 item that doesn't affect the ledger. Add a note in the Cross-Check Update Notes section (Edit 2 above) — already covered there with "A6 (Arch doc §15.13 stale title)".

No additional ledger edit needed; the note in Edit 2 captures this.

---

## Verification checklist after applying edits

- [ ] Doc header version bumped to v6.1 (Edit 1)
- [ ] "Cross-Check Update Notes" section inserted with all 12 findings categorized (Edit 2)
- [ ] A56 audit pass deliverable note added (Edit 3)
- [ ] A59 expanded with TCPA opt-in/opt-out scope including 5 schema columns + STOP handler + opt-in flow + audit log (Edit 4)
- [ ] A65 extended with TCPA opt-out enforcement at quota check layer (Edit 5)
- [ ] A70 expanded with password change cross-device session invalidation hook for B13 (Edit 6)
- [ ] A73 trial expiration warning sequence (7d/3d/1d/0d) explicitly documented (Edit 7)
- [ ] A34 calendar auto-expire boolean + nullable integer dual-mechanism clarified (Edit 8)
- [ ] A76 Stripe webhook dedup table added with handler logic (Edit 9)
- [ ] Verification notes added to A14 (G1, G9), batch B5/B15 area (G7), A68 (G2, G3, G4) per Edit 10
- [ ] Effort estimates updated where applicable (A59 +1.5–2 days; A76 +0.5 day)

After applying:

| Addition | Original effort | Updated effort | Delta | Reason |
| :--- | :--- | :--- | :--- | :--- |
| A59 | 3 days | 4–5 days | +1.5–2 days | TCPA opt-in/opt-out scope additions per G5/G6 |
| A65 | 4 days | 4 days | 0 | Outbound block is small extension to existing logic |
| A70 + B13 hook | 3 days | 3 + 0.5 = 3.5 days | +0.5 day | Password change cross-device session integration |
| A76 | 5–6 days | 5.5–6.5 days | +0.5 day | Stripe webhook dedup table |
| **Net delta to backend MVP cumulative** | | | **+2.5–3 days** | All confirmed scope additions |

Updated cumulative remaining MVP backend work: was **259–334.5 days**; with cross-check additions becomes **~261.5–337.5 days**.

Plus potential additions if Category 2 verifications surface missing pre-existing implementations:

- G1 receipt OCR (if missing): +3–5 days
- G7 automated dunning (if missing): +2–3 days
- G9 schedule history endpoint (if missing): +0.5–1 day

Worst case all three missing: +5.5–9 days additional. Best case all three pre-existing: +0 days. Verification before relevant batches start determines the actual impact.

---

## Cross-check follow-up: implementation framework doc updates

After applying these ledger edits, two cross-references should be added to `pilot-app-mvp-implementation-framework.md`:

1. **Decision Log entry**: "April 30, 2026 — Cross-check audit completed; 12 findings applied to backend ledger v6 → v6.1. TCPA SMS opt-in/opt-out gap (G5/G6) was the most critical; Stripe webhook dedup (A1) second. Source: pilot-ap-prd-arch-cross-check-w-backend-adds.md v2.0."

2. **Risk Register entry update**: existing risk "10DLC approval delays beyond 6 weeks" gets a related note: "TCPA opt-in/opt-out compliance scope was added to A59 per cross-check April 30, 2026. Implementation must be complete before SMS testing in production environment, regardless of 10DLC status."

3. **Pre-batch verification checklist**: the 6-item verification checklist from Edit 2 above should be referenced in the implementation framework's Backend Implementation workstream section as the canonical pre-batch checks.

These framework doc updates are small touch-ups; not separate update instructions needed.
