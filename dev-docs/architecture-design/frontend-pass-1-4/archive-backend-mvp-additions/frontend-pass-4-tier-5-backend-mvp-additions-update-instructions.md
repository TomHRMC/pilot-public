# Backend MVP Additions Ledger — Tier 1.5 Update Instructions

**Purpose**: Update `backend-mvp-additions-v5.1.md` to v5.2 with Pass 4 Tier 1.5 additions A59–A66 (Flow 4 customer comms extension — inbound SMS, threading, free-form replies, voice-to-text, owner visibility, quota management, carrier-agnostic adapter).

**Estimated edit time**: 10 minutes — mostly paste-ins.

---

## Edit 1 — Doc header version bump

**Find** (top of doc):
```markdown
**Version**: 5.1 (extended through Pass 4 Tier 2 #4 — Tier 1 + settings UIs for configurable thresholds complete; Tier 2 #5 next)
```

**Replace with**:
```markdown
**Version**: 5.2 (extended through Pass 4 Tier 1.5 — Flow 4 customer comms extension complete; Tier 2 #5 next)
```

Update the "Last Updated" line to today's date.

---

## Edit 2 — Status tracker line

In the "Status tracker" list, **add this line at the bottom**:

```markdown
- Pass 4 Tier 1.5 additions (A59–A66): this update
```

---

## Edit 3 — Table of Contents

Below the existing Pass 4 Tier 2 #4 entry, **add this entry**:

```markdown
  - [Additions from Pass 4 Tier 1.5 (Flow 4 Customer Communications Extension — Inbound SMS, Threading, Replies)](#additions-from-pass-4-tier-1-5-flow-4-customer-communications-extension--inbound-sms-threading-replies)
```

---

## Edit 4 — New section header to insert before A59

After the last addition in the existing Tier 2 #4 section (`### A55. Per-User Override Write Endpoints`), and before the `## Rough Effort Estimate` section, **insert this new section header**:

```markdown
## Additions from Pass 4 Tier 1.5 (Flow 4 Customer Communications Extension — Inbound SMS, Threading, Replies)
```

---

## Edit 5 — Eight new addition sections (A59–A66)

Paste these eight sections immediately after the section header from Edit 4. They appear in order:

### A59

```markdown
### A59. Telnyx Webhook Handler + Carrier-Agnostic Adapter Layer

**Triggered by**: Tier 1.5 Decisions 3, 13 — inbound SMS receive infrastructure with carrier abstraction.

**Scope**:
- New module `services/sms_carrier.py` with abstract `SmsCarrier` interface
  - Methods: `provision_number()`, `send_message()`, `verify_webhook_signature()`, `parse_inbound_webhook()`, `get_delivery_status()`, `release_number()`
- `TelnyxSmsCarrier(SmsCarrier)` implementation:
  - Webhook signature verification using Telnyx's public-key signature scheme
  - `parse_inbound_webhook()` extracting sender, recipient, body, timestamp, carrier_message_id
  - `send_message()` calling Telnyx send API
  - `provision_number()` calling Telnyx number search + acquire APIs
  - `release_number()` calling Telnyx number release API
  - `get_delivery_status()` calling Telnyx message status API
- `MockSmsCarrier(SmsCarrier)` for integration testing — captures calls without making real API requests
- New API endpoint: `POST /api/v1/webhooks/sms/telnyx-inbound` — receives Telnyx webhook
- Configuration: `SMS_CARRIER` env var (`telnyx | mock`); same carrier for all tenants on a deployment
- Failure handling: signature verification failure returns 401 (Telnyx will retry); routing failure parks inbound in unrouted queue per A60

**Architectural pattern**: carrier-agnostic adapter — generalizable to other external service integrations (payment processors, email services, mapping providers). Future Phase 2 surfaces inherit this approach.

**Effort estimate**: Small-Medium — 3 days (interface + Telnyx implementation + Mock implementation + webhook endpoint + signature verification).
```

### A60

```markdown
### A60. Customer Communication Threading Schema and Routing

**Triggered by**: Tier 1.5 Decision 4 — threading model.

**Scope**:
- New table `customer_communication_thread`:
  - `thread_id` UUID PK
  - `tenant_id` UUID
  - `customer_id` UUID
  - `tech_id` UUID
  - `tenant_phone_number_id` UUID FK → `tenant_phone_number` (per A61)
  - `status` TEXT (`active | archived`)
  - `first_message_at`, `last_message_at` TIMESTAMPTZ
  - `message_count` INT
  - `created_at`, `updated_at` TIMESTAMPTZ
- New table `customer_communication_message`:
  - `message_id` UUID PK
  - `thread_id` UUID FK
  - `direction` TEXT (`outbound | inbound`)
  - `channel` TEXT (`sms`; MMS Phase 2)
  - `body` TEXT
  - `segment_count` INT (for billing/quota)
  - `status` TEXT (`pending_send | sent | delivered | failed | received`)
  - `carrier_message_id` TEXT (Telnyx's message ID for status polling)
  - `sent_at`, `delivered_at`, `received_at` TIMESTAMPTZ
  - `composition_method` TEXT (`template | free_form_text | free_form_voice`)
  - `template_id` UUID NULL (for templated outbound; references existing `communication_template` table from A4)
  - `voice_audio_id` UUID NULL (for voice-dictated replies; references `voice_command_log.id`)
  - `audit_user_id` UUID (the tech who sent for outbound; the tech the inbound was routed to for inbound)
- New table `customer_communication_unrouted` for inbound messages that couldn't be matched to an existing thread (per Decision 3 edge case)
- New module `services/customer_communication_threading.py`:
  - `route_inbound_message(inbound: InboundMessage) -> ThreadingResult`
  - Match by sender phone + recent outbound thread + 7-day window
  - Fallback: customer's `last_assigned_tech_id` if no recent outbound
  - If still no match: park in unrouted queue with owner notification
- API: `GET /api/v1/communications/unrouted` — owner-only surface to review and manually route unrouted messages
- API: `POST /api/v1/communications/unrouted/{id}/assign-to-thread` — owner manually assigns an unrouted inbound to a thread
- Schema migrations including coexistence with existing `customer_communication` table (A4) — the threading model wraps the flat table; existing outbound rows backfill into threads at deployment time

**Effort estimate**: Medium — 4 days (schema + migration + routing logic + unrouted handling + tests).
```

### A61

```markdown
### A61. Telnyx Number Provisioning at First Use

**Triggered by**: Tier 1.5 Decision 12 — lazy provisioning of tenant phone numbers.

**Scope**:
- New table `tenant_phone_number`:
  - `phone_number_id` UUID PK
  - `tenant_id` UUID FK
  - `phone_number` TEXT (E.164 format)
  - `area_code` TEXT
  - `carrier` TEXT (`telnyx`)
  - `carrier_provisioning_id` TEXT (Telnyx's reference for the provisioning record)
  - `monthly_fee_cents` INT (for billing tracking and reconciliation)
  - `provisioned_at`, `released_at` TIMESTAMPTZ
  - `status` TEXT (`active | released | provisioning_failed`)
- New module `services/sms_provisioning.py`:
  - `provision_for_tenant(tenant_id) -> ProvisioningResult` — handles area code selection, Telnyx API call, billing integration
  - Default area code: tenant's primary office area code from address
  - Fallback: suggest 3 nearby area codes if primary is unavailable
  - Failure handling: queue SMS attempt; notify owner to retry
- Provisioning trigger: first SMS attempt for a tenant without `tenant_phone_number.status = 'active'` invokes provisioning before send
- Pre-provisioning UI affordance: API endpoint `POST /api/v1/tenants/{tenant_id}/phone-numbers/provision` invokable from `Settings > Integrations > SMS messaging > Set up SMS messaging`
- Subscription billing integration: provisioned number adds `monthly_fee_cents` to tenant's recurring billing line items (existing subscription billing infrastructure handles the addition)
- API: `GET /api/v1/tenants/{tenant_id}/phone-numbers` — list assigned numbers (active and released history)

**Effort estimate**: Medium — 3 days (schema + provisioning service + Telnyx integration + billing integration + failure handling).
```

### A62

```markdown
### A62. Free-Form Reply Composition Endpoints

**Triggered by**: Tier 1.5 Decision 7 — free-form tech reply UI.

**Scope**:
- API: `POST /api/v1/communications/threads/{thread_id}/reply` — send a free-form reply
  - Request body: `{body: str, composition_method: 'free_form_text' | 'free_form_voice', voice_audio_id: UUID?}`
  - Validates: body within segment limits; tenant within quota (per A65); thread status is `active`
  - Computes `segment_count` from body (160 GSM chars per segment for plain ASCII; 70 chars for Unicode)
  - Pre-commit staleness check per arch doc §16.4 (concurrent thread modifications)
  - Dispatches via `SmsCarrier.send_message()` (per A59)
  - Updates `customer_communication_message` and `customer_communication_thread.last_message_at`, `.message_count`
  - Decrements tenant quota (per A65)
  - Audit log entry per Tier 1.5 Decision 14
- Optimistic UI support: 200 response includes the new message in the thread payload
- Validation rules:
  - Body cannot be empty
  - Body length cap: 1600 characters (10 segments) — protects against runaway voice transcriptions
  - Quota check returns 402 if hard cap reached; 200 with overage flag if soft cap; 200 normal if within quota
- Real-time delivery to other tenant users via SSE per arch doc §13.11

**Effort estimate**: Small — 2 days.
```

### A63

```markdown
### A63. Voice-to-Text Reply Integration

**Triggered by**: Tier 1.5 Decisions 7, 9 — voice-to-text composition flow and `reply_to_customer_sms` voice intent.

**Scope**:
- New voice intent `reply_to_customer_sms` added to voice intent registry (`api/voice/intents.py`)
- Intent handler:
  - Extract customer identifier from utterance (most recent active thread by default; explicit by name/job context if specified)
  - Extract message body
  - If ambiguous (sounds like template + free-form), AI clarifies: "Is this a template or free-form?"
  - Call `customer_communication_preview_service.render(...)` with composition_method `free_form_voice`
  - Render preview: "I'll send to [customer]: '[body].' That's [segment_count] segments, you have [remaining] left this month. Confirm?"
  - On confirmation, invoke A62 `POST /threads/{thread_id}/reply` with `voice_audio_id` populated
- Voice anywhere: voice composition can be initiated from any screen per Flow 4 Decision 7's "Voice override anywhere" pattern
- The voice composition path on mobile reply UI (per Tier 1.5 Decision 7) calls the same intent flow
- `voice_audio_id` references `voice_command_log.id` to maintain audit trail
- Confirm-as-turn safeguard per arch doc §16.3
- Always-preview-before-send safeguard per arch doc §16.7

**Effort estimate**: Small-Medium — 2–3 days (intent handler + preview rendering + integration with A62).
```

### A64

```markdown
### A64. Owner Visibility Surfaces — Web Comm History Extension and Dashboard Widget

**Triggered by**: Tier 1.5 Decision 6 — owner visibility.

**Scope**:
- Web `Customers > [customer] > Comm history` surface extended:
  - Two-direction message rendering (outbound: brand-indigo left-aligned; inbound: neutral right-aligned; chat-style bubbles)
  - Threaded by `thread_id`; multiple threads per customer when multiple techs have communicated
  - API: `GET /api/v1/customers/{customer_id}/communication-history` — returns threaded message list grouped by thread
  - Real-time updates via SSE per arch doc §13.11
- New dashboard widget: "Recent customer messages"
  - API: `GET /api/v1/dashboard/widgets/recent-customer-messages?limit=10` — returns last N messages across the tenant (cross-customer, cross-tech)
  - Each row shows: customer name, tech name, direction, last message preview, time
  - Widget config (per Pass 2 §5 pin-to-dashboard pattern): owner pins to dashboard, configurable `limit`
  - Real-time updates via SSE
- Mobile owner: per Tier 2 #5 default policy for Customer activity category (push ON for owners by default; can be muted)

**Effort estimate**: Small-Medium — 2–3 days.
```

### A65

```markdown
### A65. SMS Quota Tracking and Cap Enforcement

**Triggered by**: Tier 1.5 Decision 8 — subscription quota model.

**Scope**:
- New table `sms_quota_period`:
  - `period_id` UUID PK
  - `tenant_id` UUID FK
  - `period_start`, `period_end` TIMESTAMPTZ (aligned to subscription billing cycle)
  - `included_segments` INT (computed: 100 base + 100 per active add-on number)
  - `used_segments` INT (incremented atomically per outbound send)
  - `overage_segments` INT (computed: max(0, used - included); for billing)
  - `cap_policy` TEXT (`soft | hard`; copied from tenant setting at period start to lock in policy mid-period)
- New tenant setting `sms_quota_cap_policy` (`soft | hard`; default `soft`; owner-only edit)
- Setting placement: `Settings > Subscription & Billing > SMS quota`
- New module `services/sms_quota.py`:
  - `check_quota(tenant_id, requested_segments) -> QuotaCheckResult` — returns `{allowed: bool, overage: bool, blocked_reason: str?}`
  - `consume_quota(tenant_id, segments)` — atomic increment; rolls back on send failure
  - Hard cap: `check_quota` returns `allowed: False, blocked_reason: 'monthly_quota_reached'` when used + requested > included
  - Soft cap: `check_quota` always returns `allowed: True`; flags `overage: True` when crossing the threshold
- Periodic notification dispatch:
  - 80% usage: push + email to owner via `notification_outbox` (Billing category from Tier 2 #5)
  - 100% usage: push + email; if soft cap, includes overage rate; if hard cap, includes "techs cannot send more SMS until [billing date]"
  - Celery task `monitor_sms_quota_thresholds` runs hourly to detect threshold crossings
- Period rollover: scheduled Celery task `rollover_sms_quota_periods` runs daily; creates new `sms_quota_period` row for tenants whose subscription cycle just rolled
- Billing integration: at month-end, `overage_segments × $0.05` added to tenant invoice
- API: `GET /api/v1/sms/quota` — returns current period status (used, remaining, projected month-end based on current pace, policy)
- Failed send refund: if `SmsCarrier.send_message()` returns failure, `consume_quota` is rolled back atomically

**Effort estimate**: Medium — 4 days (schema + quota service + billing integration + period rollover + notifications + Celery tasks).
```

### A66

```markdown
### A66. Mobile Inbox "Customer Messages" Sub-Section + Conversation Thread Screen

**Triggered by**: Tier 1.5 Decisions 7, 10 — mobile UI surfaces.

**Scope**:
- API: `GET /api/v1/mobile/inbox/customer-threads` — returns recent threads for the requesting tech
  - Default: last 5 threads, ordered by `last_message_at` desc
  - Paginated for full inbox view
  - Response per thread: `{thread_id, customer_name, last_message_preview (first 80 chars), last_message_at, unread_count, originating_job_context (if available)}`
- API: `GET /api/v1/communications/threads/{thread_id}/messages?limit&before` — returns full message history for a thread, paginated
- API: `POST /api/v1/communications/threads/{thread_id}/mark-read` — marks all unread messages in thread as read; updates per-user read state
- New table `customer_communication_message_read_state`:
  - `(message_id, user_id)` composite PK
  - `read_at` TIMESTAMPTZ
- Real-time updates via SSE per arch doc §13.11 — when a new inbound arrives in an open thread, it appears immediately
- Push notification deep-link target: tapping a customer-message push opens the conversation thread screen for that thread
  - Push payload includes `thread_id` for deep-link routing
- Unread count computation: COUNT of inbound messages without a read_state row for the requesting user

**Effort estimate**: Medium — 3–4 days (multiple endpoints + read state schema + SSE integration + push deep-link).
```

---

## Edit 6 — Effort estimate table updates

In the "Rough Effort Estimate" table, after the row `A55 Per-User Override Write Endpoints | Small | 1–2`, **insert these eight rows**:

```markdown
| A59 Telnyx Webhook Handler + Carrier-Agnostic Adapter Layer | Small-Medium | 3 |
| A60 Customer Communication Threading Schema and Routing | Medium | 4 |
| A61 Telnyx Number Provisioning at First Use | Medium | 3 |
| A62 Free-Form Reply Composition Endpoints | Small | 2 |
| A63 Voice-to-Text Reply Integration | Small-Medium | 2–3 |
| A64 Owner Visibility Surfaces — Comm History + Dashboard Widget | Small-Medium | 2–3 |
| A65 SMS Quota Tracking and Cap Enforcement | Medium | 4 |
| A66 Mobile Inbox + Conversation Thread Screen | Medium | 3–4 |
```

**Update the subtotal row from**:

```markdown
| **Subtotal remaining MVP (Pass 4 Tier 1 + Tier 2 #4 complete)** | | **148–203.5 days** |
```

**To**:

```markdown
| **Subtotal remaining MVP (Pass 4 Tier 1 + 1.5 + Tier 2 #4 complete)** | | **171–229.5 days** |
```

**Update the trailing paragraph**:

Find:
> Plus Pass 4 Tier 2 #5–#7, Tier 3, and Tier 4 polish, states, and onboarding additions still to come. Plan for approximately **30–41 weeks** of backend work before UI implementation begins, depending on team parallelism.

Replace with:
> Plus Pass 4 Tier 2 #5–#7, Tier 3, and Tier 4 polish, states, and onboarding additions still to come. Plan for approximately **34–46 weeks** of backend work before UI implementation begins, depending on team parallelism. Some of the more-stable Pass 1/2/3 + Tier 1 + Tier 1.5 + Tier 2 #4 foundations could begin backend implementation in parallel with Pass 4 design if team bandwidth permits.

---

## Verification checklist after edits

- [ ] Doc header version bumped to v5.2
- [ ] Status tracker has Pass 4 Tier 1.5 entry
- [ ] TOC has Pass 4 Tier 1.5 entry
- [ ] New section header `## Additions from Pass 4 Tier 1.5...` inserted
- [ ] All 8 new addition sections (A59–A66) inserted in order
- [ ] Effort estimate table has 8 new rows
- [ ] Subtotal row updated to "Tier 1 + 1.5 + Tier 2 #4" with 171–229.5 days
- [ ] Trailing paragraph updated to "34–46 weeks"
- [ ] A1–A66 contiguous, no gaps
