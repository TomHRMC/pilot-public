# Batch Design — Seed Data Design Sprint: SD-05 through SD-10

**Mode**: Pilot Architect  
**Type**: Design sprint — 6 tasks, no code written here  
**Sprint source**: `dev-docs/implementation-prompts/seed-data/sd-05-thru-10-architect-design-sprint.md`  
**Design doc date**: 2026-07-06  
**Status**: Complete — all 6 tasks dispositioned

---

## Summary of Dispositions

| Task | Title | Disposition |
|:---|:---|:---|
| SD-05 | Payment Refund Status Support | `[APPROVED FOR IMPLEMENTATION]` |
| SD-06 | Invoice Status Alignment + Automated Late Invoice Reminders | `[APPROVED FOR IMPLEMENTATION]` |
| SD-07 | Product Feature / Usage Billing Competitive Review | `[APPROVED FOR IMPLEMENTATION]` |
| SD-08 | Email Template + Notification Template Review & Update | `[APPROVED FOR IMPLEMENTATION]` |
| SD-09 | Seed Data for Empty Functional Tables | `[APPROVED FOR IMPLEMENTATION]` (6 of 8 tables; 2 deferred) |
| SD-10 | Scenario Coverage Analysis + E2E Test Harness | `[APPROVED FOR IMPLEMENTATION]` (architecture recommendation) |

---

## A. Input Read Summary

All mandatory inputs were read before writing any design decision.

| Input | What Was Read | Key Finding |
|:---|:---|:---|
| `README-seed-data.md` §10 | Full SD-05 through SD-10 specs | Task definitions, design questions, implementation requirements |
| `pilot-launch-plan.md` | §P1 Seed Data Batch + Beta Gate | Gate item confirmed: `SD-05 through SD-10 design decisions made ☐` |
| `gtm-feature-tier-matrix-v1.md` | Full doc — all 19 sections | Tom's locked decisions: Starter/Teams/Enterprise at $49/$149/$499; dispatch_slots (5/25/75), voice_ai_minutes (60/240/1000), sms_segments (100/500/2500) are the primary metered features; QB sync is **unlimited on all tiers** |
| `17-cust-comms-templates.md` | Full doc — 13 MVP + 14 Phase 2 templates | All 13 MVP active codes confirmed: on_my_way, running_late, arrived, parts_delay, change_order_approval, job_complete, invoice_sent, payment_reminder, payment_received, confirm_appointment, tech_assigned, quote_accepted, quote_expiring |
| MCP — `payment_status` | Live DB query | 4 codes: `canceled`, `failed`, `pending`, `succeeded` — no `refunded` |
| MCP — `payment` columns | Live DB query | No `refunded_amount_cents` or `refunded_at` columns |
| MCP — `invoice_status` | Live DB query | 5 codes: `draft`, `issued`, `paid`, `void`, `writeoff` — no `sent` or `overdue` |
| MCP — `invoice` columns | Live DB query | No `last_reminder_sent_at` or `reminder_count` columns |
| MCP — `email_template` | Live DB query (by actual column `template_id`) | 16 rows confirmed; 5 customer-facing templates have single-sentence stub HTML body |
| MCP — `notification_template` | Live DB query | 9 rows (3 types × 3 channels); ALL bodies are literal placeholder strings |
| MCP — `customer_comm_template_type` | Live DB query | 27 rows confirmed (13 is_active=true; 14 is_active=false) |
| MCP — SD-09 tables | Live DB row counts | `payment_method`=0, `help_article`=0, `help_article_chunk`=0, `discount_version`=0, `supplier`=0, `supplier_item`=0, `supplier_item_price`=0, `quote_template`=3 |
| MCP — `quote_template` origin | Live DB `created_at` timestamps | All 3 rows have `created_at = 2026-05-01T11:10:45.578Z` — matches Alembic migration `29384efbde55` timestamp |
| `backend/tasks/` grep | `dunning.py` found | Celery Beat dunning task already exists — fires every 60min for all `due_at < now() AND balance_due_cents > 0`; sends **internal** notifications to tenant owner only (not customer SMS) |
| Frontend grep | `InvoicesPage.tsx` | Bug confirmed: filter uses hardcoded `"sent"` (wrong; should be `"issued"`) and `"overdue"` (non-existent DB code) |

---

## §SD-05 — Payment Refund Status Support

### `[APPROVED FOR IMPLEMENTATION]`

---

### Design Questions Answered

**1. New status codes vs. new columns on `payment`?**

**Decision: New columns on `payment`, NOT new status codes.**

Rationale based on live DB and Stripe alignment:

- Stripe's `charge.refunded` and `payment_intent.partially_refunded` webhooks fire when a refund occurs. In Stripe's own data model, the `PaymentIntent.status` remains `succeeded` — refund state is tracked on a separate `Refund` object with its own `amount`, `status`, and `created` fields.
- Adding `refunded` as a new `payment_status` code would diverge from Stripe's model and require webhook handlers to manage a status transition that Stripe itself never makes.
- A partially refunded payment is still a succeeded payment — adding `partially_refunded` as a status would require a new webhook path, new UI states, and complicates the reconciliation with Stripe's dashboard.
- The clean solution is to track refund state inline on the `payment` row alongside the existing `succeeded` status.

**Exception**: When a full refund is issued (`refunded_amount_cents == amount_cents`), a `refunded` status code does represent a genuinely different business state and is useful for UI filtering. However, even here Stripe's own `PaymentIntent` does not change status — so we track it as a derived state from the columns, not a webhook-written status.

**2. Stripe webhook events that fire on refund:**

| Event | When it fires | What we write |
|:---|:---|:---|
| `charge.refunded` | Full or partial refund issued | Write `refunded_amount_cents`, `refunded_at` to `payment` row |
| `refund.created` | Same trigger as above (more granular) | Same — update `payment` row |
| `refund.updated` | Refund status changes (e.g., succeeded → failed) | Update/clear if refund failed |

**3. Partial refunds in UI?**

P2 — not surfaced in AR aging or invoice detail for launch. The columns are added now to capture the data from Stripe webhooks so it is not lost; display is a Phase 1.5 item. The invoice balance calculation (`balance_due_cents`) remains unchanged by refund events for MVP.

### Schema Change

**Add to `payment` table via Alembic migration:**

```sql
ALTER TABLE public.payment
  ADD COLUMN refunded_amount_cents INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN refunded_at TIMESTAMPTZ;
```

**Constraints:**
- `refunded_amount_cents` is NOT NULL with DEFAULT 0 — safe to add without backfill
- `refunded_at` is nullable — NULL means no refund; non-NULL means at least one refund was processed
- No `payment_status` table changes needed for launch

### Webhook Handler Update

`backend/tasks/stripe_subscriptions.py` (or the Stripe webhook router) must handle `charge.refunded` and `refund.created` events:

```python
# Pseudo-code — exact implementation is Python Engineer's work
payment = db.exec(select(Payment).where(
    Payment.psp_payment_id == event.data.object.payment_intent
)).first()
if payment:
    refund_amount = event.data.object.amount_refunded  # in cents
    payment.refunded_amount_cents = refund_amount
    payment.refunded_at = datetime.now(UTC)
    db.add(payment)
    db.commit()
```

### Seed Script Impact

No `seed_platform.py` changes needed — `payment_status` is unchanged. The Python Engineer should add an `inspect` check for `refunded_amount_cents` when verifying payment rows.

### Implementation Guidance

- **Alembic migration**: 1 migration — `ALTER TABLE payment ADD COLUMN refunded_amount_cents INTEGER NOT NULL DEFAULT 0, ADD COLUMN refunded_at TIMESTAMPTZ`
- **Webhook handler**: update Stripe `charge.refunded` / `refund.created` handler to write the two new columns
- **Test**: add unit test asserting that a `charge.refunded` webhook call writes the correct `refunded_amount_cents` value to the payment row
- **seed_core.py**: no change — `payment_status` lookup table is unchanged

---

## §SD-06 — Invoice Status Alignment + Automated Late Invoice Reminders

### `[APPROVED FOR IMPLEMENTATION]`

---

### Design Questions Answered

#### Part A — Status Code Alignment

**Live DB confirmed:** `invoice_status` has exactly 5 codes: `draft`, `issued`, `paid`, `void`, `writeoff`.

**Frontend bug confirmed (MCP + grep):**

`InvoicesPage.tsx` line 29–31 contains:
```typescript
{ label: "Sent", value: "sent" },      // ← WRONG: "sent" does not exist in invoice_status
{ label: "Overdue", value: "overdue" }, // ← WRONG: "overdue" does not exist in invoice_status
```

This means the "Sent" filter button sends `status=sent` to the API, which returns 0 results. The "Overdue" filter button likewise returns 0 results. Both are silent bugs — no error, just empty state.

**Additional finding:** `InvoicesPage.test.tsx` uses `status_code: "sent"` in mock data — the test mock uses the wrong code, meaning the test never exercises the correct `issued` path.

**Fixes required:**

| Location | Current (wrong) | Correct |
|:---|:---|:---|
| `InvoicesPage.tsx` filter array | `value: "sent"` | `value: "issued"` |
| `InvoicesPage.tsx` filter array | `value: "overdue"` | **Remove** (derived state — see below) |
| `InvoicesPage.test.tsx` | `status_code: "sent"` | `status_code: "issued"` |

**"Overdue" as derived display property (NOT a DB status):**

Overdue is computed at render time:

```typescript
const isOverdue = (invoice: Invoice): boolean =>
  invoice.due_at !== null &&
  new Date(invoice.due_at) < new Date() &&
  !["paid", "void", "writeoff"].includes(invoice.status_code);
```

This rule must NOT be stored as a DB column. The `InvoicesPage` "Overdue" filter should be removed from the status filter pills and replaced with a separate "Show overdue only" toggle that calls a backend endpoint with `overdue=true` as a query parameter. The backend derives overdue the same way: `due_at < NOW() AND status_code NOT IN ('paid', 'void', 'writeoff')`.

**Other frontend references to `"sent"` status:**
- `QuotesPage.tsx` line 31 — `{ label: "Sent", value: "sent" }` — this is for **quotes**, not invoices. `quote_status` has a `sent` code. ✅ Correct.
- `PublicQuotePage.tsx` — `quote.status === "sent"` — quote context. ✅ Correct.
- `comms/page.tsx` and `CustomerCommsHistoryView.tsx` — SMS message delivery status, not invoice status. ✅ Correct.

**Summary**: Only the invoice filter array contains the bug. All other `"sent"` references are in correct quote or SMS contexts.

#### Part B — Automated Reminders

**Key finding: `backend/tasks/dunning.py` already exists.**

The existing `dunning.py` task (`send_overdue_invoice_reminders_task`) fires every 60 minutes via Celery Beat. It queries `due_at < now() AND balance_due_cents > 0` and creates `notification_outbox` rows for the **tenant owner** via `in_app` and `email` channels. 

**Critical gap**: The existing dunning task sends internal notifications to the **tenant owner** (reminder to follow up). It does NOT send customer-facing SMS or email reminders to the actual customer. The `customer_comm_template_type` row `payment_reminder` (is_active=true, preferred_channel=sms) exists but is not wired to the dunning task.

**Design for enhanced dunning task:**

| Gap | Resolution |
|:---|:---|
| Fires every 60 min, re-notifying the same invoice | Add `last_reminder_sent_at` and `reminder_count` columns to `invoice` |
| Does not send customer SMS | Add customer-facing SMS leg using `communication_template` for `payment_reminder` code |
| No reminder schedule | Implement 1d/7d/14d thresholds; tenant-configurable via `platform_setting_catalog` |

### Schema Change — New `invoice` Columns

```sql
ALTER TABLE public.invoice
  ADD COLUMN last_reminder_sent_at TIMESTAMPTZ,
  ADD COLUMN reminder_count INTEGER NOT NULL DEFAULT 0;
```

These two columns allow the dunning task to check "was a reminder sent in the last 7 days?" without querying `notification_log`, keeping the query efficient.

### New `platform_setting_catalog` Keys

Add 3 new catalog keys for tenant-configurable reminder schedule:

| Key | value_type | Default | Description |
|:---|:---|:---|:---|
| `invoice_reminder_days_1` | `integer` | `1` | Days overdue before first reminder fires |
| `invoice_reminder_days_2` | `integer` | `7` | Days overdue before second reminder fires |
| `invoice_reminder_days_3` | `integer` | `14` | Days overdue before final reminder fires |

These keys must be added to `seed_core.py` `platform_setting_catalog` section and a corresponding null-tenant default row in `platform_setting`.

### F. Shared Module Interface — Celery Task

Enhanced `send_overdue_invoice_reminders` Celery Beat task:

```python
@celery_app.task(name="send_overdue_invoice_reminders", bind=True)
def send_overdue_invoice_reminders_task(self) -> dict:
    """
    Celery Beat daily task — fires at 09:00 UTC.
    
    For each invoice WHERE:
        status_id → 'issued'
        AND due_at < NOW()
        AND balance_due_cents > 0
        AND (last_reminder_sent_at IS NULL 
             OR last_reminder_sent_at < NOW() - INTERVAL '1 day')
    
    Sends:
        1. Internal notification_outbox to tenant owner (existing behavior)
        2. Customer SMS via communication_template 'payment_reminder' code
    
    Respects reminder schedule from platform_setting_catalog:
        invoice_reminder_days_1, invoice_reminder_days_2, invoice_reminder_days_3
    
    Updates: invoice.last_reminder_sent_at, invoice.reminder_count
    
    Returns: {"invoices_processed": N, "customer_sms_sent": M, "owner_notifications": P}
    """
```

**Beat schedule**: Change from every-60-minutes to once-daily at 09:00 UTC. The existing 60-minute schedule is overly aggressive and would spam customers.

### D. New API Endpoints

No new endpoints needed. The `invoice_status` filter fix is a frontend-only change. The derived `isOverdue()` logic lives in the frontend. The backend `/invoices` list endpoint may need an `overdue=true` query parameter added, but this is a lightweight change to the existing endpoint, not a new endpoint.

| Change | Type | Owner |
|:---|:---|:---|
| `GET /api/v1/invoices?overdue=true` | New query param on existing endpoint | Python Engineer |
| `InvoicesPage.tsx` filter fix | Frontend bug fix | React Engineer |
| `invoice` table — 2 new columns | Alembic migration | Python Engineer |
| `platform_setting_catalog` — 3 new keys | Alembic data migration + `seed_core.py` update | Python Engineer |
| `dunning.py` enhancement | Celery task update | Python Engineer |

---

## §SD-07 — Product Feature / Usage Billing Competitive Review

### `[APPROVED FOR IMPLEMENTATION]`

**Tom's decisions (2026-07-06)**:

---

### Competitive Analysis

The following is the author's mid-2026 reading of publicly available FSM pricing; figures may have changed since:

| Competitor | Primary Pricing Model | Key Gated Features | Usage Limits |
|:---|:---|:---|:---|
| **ServiceTitan** | $125–$250/user/month | Nearly all features gated; heavy per-seat + module charges | No published usage limits; very high cost at scale |
| **Jobber** | $9–$99/user/month | Core PM on all tiers; reporting + automation gated to Growth/Premium | No explicit usage limits; seat-based |
| **Housecall Pro** | $79–$249/month flat (up to 5 techs) + per-tech overages | Text messaging gated; reporting gated | SMS credits included per tier; limited per plan |
| **Workiz** | $45–$225/month flat | Limited automation/AI on base; multi-location Enterprise | Voice minutes gated at higher tiers |
| **BuildOps** | Enterprise-only quoting | Heavy per-user model | No usage limits published |

**Key competitive findings:**

1. **Dispatch slot gating is rare in FSM** — most competitors charge per seat (including admin/owner). Pilot's approach (unlimited users, slot-gated field techs only) is a meaningful differentiator.
2. **Voice AI is Pilot-unique** — no FSM competitor gates voice AI minutes because no FSM competitor has voice AI at this depth. The `voice_ai_minutes` feature is correctly modeled.
3. **SMS is commonly gated** — Housecall Pro, Jobber, and Workiz all gate SMS volume. Our `outbound_sms_segments` metering aligns with industry practice.
4. **QB sync is universally unlimited** — no major FSM competitor charges per QB sync operation. Having `qb_sync_operations` in `product_feature` is a pricing anti-pattern that will create sales friction. It should be removed.
5. **Data exports are gated at higher tiers** by Jobber (Growth+ only) and ServiceTitan — `data_exports` as a plan gate is market-aligned.
6. **Dispatch slots** are our primary upgrade lever — the GTM matrix has locked 5/25/75 per tier. This is the most important feature to meter.

### Current vs. Proposed `product_feature` Set

**Current state (from live DB + `seed_platform.py`):**

| feature code | Starter | Professional | Enterprise |
|:---|:---|:---|:---|
| `voice_ai_minutes` | 60 | 300 | -1 (unlimited) |
| `qb_sync_operations` | 100 | 500 | -1 (unlimited) |
| `data_exports` | 5 | 25 | -1 (unlimited) |

**Problems with current state:**
1. Tier names `starter/professional/enterprise` mismatch the GTM-locked names `starter/teams/enterprise`
2. `qb_sync_operations` should not be a metered feature (anti-pattern vs. competitors)
3. `dispatch_slots` is missing — it's the primary upgrade driver per the GTM matrix
4. `outbound_sms_segments` is missing — all competitors meter SMS

**Proposed revised `product_feature` set:**

| feature code | Starter | Teams | Enterprise | Overage Rate |
|:---|:---|:---|:---|:---|
| `voice_ai_minutes` | 60 | 240 | 1,000 | $0.05/min |
| `dispatch_slots` | 5 | 25 | 75 | See §1.3 add-on packs |
| `outbound_sms_segments` | 100 | 500 | 2,500 | $0.05/segment |
| `data_exports` | ❌ (Teams+) | ✅ | ✅ | n/a |

Note: `data_exports` transitions from a metered integer limit to a boolean gate (Starter=0, Teams/Enterprise=unlimited). This simplifies pricing and aligns with Jobber's model.

**`qb_sync_operations` proposed disposition**: Remove from `product_feature`. Mark as unlimited on all tiers in the pricing page. Add one `product_feature` row removal migration.

**Tier name alignment**: `product_plan` in DB currently has `starter_plan`, `professional_plan`, `enterprise_plan`. The GTM matrix locks the marketing names as Starter/Teams/Enterprise. The DB `code` values should be updated to `starter`, `teams`, `enterprise` (matching the public-facing names), or at minimum the display names on the pricing page must be `Teams` not `Professional`. This is a separate data migration.

### Tom's Decision Gate

Tom confirmed on 2026-07-06:
1. ✅ Feature set approved as proposed: `voice_ai_minutes`, `dispatch_slots`, `outbound_sms_segments`, `data_exports`
2. ✅ Limit values approved: 60/240/1000 min; 5/25/75 slots; 100/500/2500 segments
3. ✅ `data_exports` remains Teams+ gate for now; flexibility to add to Starter later if demand warrants (no schema change needed — just update the limit value row)
4. ✅ `qb_sync_operations` removed from metered features — QB sync is unlimited on all tiers
5. ✅ `professional_plan` → `teams` DB name alignment confirmed

---

## §SD-08 — Email Template + Notification Template Review & Update

### `[APPROVED FOR IMPLEMENTATION]`

**Tom's decision (2026-07-06)**: Templates design approved. Draft copy provided by Architect (below) — Tom confirmed this approach is acceptable as initial v1 copy. Python Engineer to update the 5 customer-facing JSON files in `data/email_templates/` and the `notification_template` rows in `seed_platform.py`.

---

### Email Template Audit (16 rows via MCP)

**Column structure confirmed**: `template_id` (PK, text), `display_name`, `category` (internal | customer_facing), `subject_template`, `body_html_template`, `body_plain_template`, `variables` (JSONB).

#### Customer-Facing Templates (5) — All have stub/placeholder copy ⚠️

| template_id | subject_template | Current html body | Variables | Assessment |
|:---|:---|:---|:---|:---|
| `invoice_sent` | `Invoice from {{company_name}}` | `<p>Your invoice is ready.</p>` | customer_name, company_name, invoice_total, invoice_url | ⚠️ Stub — customer receives this on every invoice. Needs full body with invoice summary, amount, CTA button. |
| `payment_failed` | `Payment issue with your invoice` | `<p>Your payment could not be processed.</p>` | customer_name, invoice_url | ⚠️ Stub — sent when Stripe charge fails. Needs clear instructions and retry CTA. |
| `payment_received_customer` | `Payment confirmation from {{company_name}}` | `<p>Thank you for your payment.</p>` | customer_name, company_name, amount, payment_date | ⚠️ Stub — customer receives this as a receipt. Needs amount, date, and company branding. |
| `quote_expiring` | `Your quote expires soon` | `<p>Your quote expires in 3 days.</p>` | customer_name, quote_url, expires_at | ⚠️ Stub — "3 days" is hardcoded but `expires_at` variable exists. Needs dynamic copy. |
| `quote_sent` | `Your quote from {{company_name}}` | `<p>Please review your quote.</p>` | customer_name, company_name, quote_total, quote_url | ⚠️ Stub — first customer touchpoint for a quote. Needs full body with summary and CTA. |

#### Internal Templates (11) — Functional but minimal

| template_id | subject_template | Category | Assessment |
|:---|:---|:---|:---|
| `email_verification` | `Verify your email address` | internal | Non-customer-facing. Functional stub acceptable for beta. |
| `mfa_reset_by_owner` | `Your MFA has been reset` | internal | Non-customer-facing. Functional. |
| `password_reset` | `Reset your Pilot password` | internal | Non-customer-facing. Functional. |
| `payment_received_tenant` | `Payment received from {{customer_name}}` | internal | Tenant-only notification. Low urgency. |
| `quote_accepted` | `Customer accepted your quote` | internal | Tenant-only notification. Low urgency. |
| `quote_declined` | `Customer declined your quote` | internal | Tenant-only notification. Low urgency. |
| `subscription_payment_failed` | `Action required: subscription payment failed` | internal | Billing alert to owner. Moderate urgency. |
| `subscription_renewal` | `Your Pilot subscription has renewed` | internal | Billing confirmation. Low urgency. |
| `trial_expired` | `Your free trial has ended` | internal | Conversion touchpoint. Should be compelling. |
| `trial_expiring` | `Your free trial ends soon` | internal | Conversion touchpoint. Should be compelling. |
| `welcome` | `Welcome to Pilot for Trades` | internal | First impression. Should be warm and actionable. |

### Notification Template Audit (9 rows via MCP)

All 9 `notification_template` rows are confirmed placeholder stubs. The `body` column for every row reads literally:
> `"This is a placeholder {notification_type_code} notification via {channel}."`

| notification_type_code | Channels | Assessment |
|:---|:---|:---|
| `customer_communication_sent` | email, in_app, push | Fires when a comm is sent to customer. All 3 channels are stubs. |
| `dunning_reminder` | email, in_app, push | Fires for overdue invoices. All 3 channels are stubs. Currently used by `dunning.py`. |
| `quote_accepted` | email, in_app, push | Fires when customer accepts a quote. All 3 channels are stubs. |

### Cross-Reference: `customer_comm_template_type` vs. `17-cust-comms-templates.md`

All 13 MVP active template codes from `17-cust-comms-templates.md` are confirmed present in the live DB with correct `is_active=true`:

| Code | is_active | preferred_channel | Assessment |
|:---|:---|:---|:---|
| `confirm_appointment` | ✅ | sms | Present |
| `tech_assigned` | ✅ | sms | Present |
| `quote_accepted` | ✅ | email | Present |
| `quote_expiring` | ✅ | email | Present |
| `on_my_way` | ✅ | sms | Present |
| `running_late` | ✅ | sms | Present |
| `arrived` | ✅ | sms | Present |
| `parts_delay` | ✅ | sms | Present |
| `change_order_approval` | ✅ | sms | Present |
| `job_complete` | ✅ | sms | Present |
| `invoice_sent` | ✅ | email | Present |
| `payment_reminder` | ✅ | sms | Present |
| `payment_received` | ✅ | email | Present |

**No gaps** between `17-cust-comms-templates.md` and live DB. ✅

The 14 Phase 2 inactive rows are also correctly present (`is_active=false`).

### Draft Email Copy — All 5 Customer-Facing Templates

The following copy is Architect-authored v1 draft based on industry-standard FSM/SaaS transactional email patterns (Jobber, Housecall Pro, ServiceTitan, Stripe). Variables in `{{double_braces}}` match the `variables` JSONB array already in each `email_template` row.

---

#### `invoice_sent` — "Invoice from {{company_name}}"

**Subject**: `Invoice from {{company_name}} — ${{invoice_total}} due {{due_date}}`

**HTML body**:
```html
<p>Hi {{customer_name}},</p>

<p>Your invoice from <strong>{{company_name}}</strong> is ready to view and pay online.</p>

<table style="border-collapse:collapse;width:100%;max-width:480px;margin:16px 0;">
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Invoice total</td>
    <td style="padding:8px 0;font-weight:600;text-align:right;">${{invoice_total}}</td>
  </tr>
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Due date</td>
    <td style="padding:8px 0;text-align:right;">{{due_date}}</td>
  </tr>
</table>

<p style="margin:24px 0;">
  <a href="{{invoice_url}}" style="background:#2563eb;color:#ffffff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;">Pay Invoice →</a>
</p>

<p style="color:#6b7280;font-size:13px;">You can pay securely online by credit card or bank transfer. No account required.</p>

<p style="color:#6b7280;font-size:13px;">Questions? Reply to this email or contact us at <a href="mailto:support@{{company_domain}}">support@{{company_domain}}</a>.</p>

<p>Thank you,<br><strong>{{company_name}}</strong></p>

<p style="color:#9ca3af;font-size:11px;margin-top:32px;">Do not reply directly to this email — contact support@pilotfortrades.com for help.</p>
```

**Plain text body**:
```
Hi {{customer_name}},

Your invoice from {{company_name}} is ready.

Invoice total: ${{invoice_total}}
Due date: {{due_date}}

Pay online: {{invoice_url}}

You can pay securely by credit card or bank transfer. No account required.

Questions? Contact us at support@{{company_domain}}.

Thank you,
{{company_name}}
```

**Variables note**: Add `due_date` and `company_domain` to the `variables` JSONB array (currently: `["customer_name","company_name","invoice_total","invoice_url"]`).

---

#### `quote_sent` — "Your quote from {{company_name}}"

**Subject**: `Your quote from {{company_name}} — ${{quote_total}}`

**HTML body**:
```html
<p>Hi {{customer_name}},</p>

<p><strong>{{company_name}}</strong> has sent you a quote for your review.</p>

<table style="border-collapse:collapse;width:100%;max-width:480px;margin:16px 0;">
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Quote total</td>
    <td style="padding:8px 0;font-weight:600;text-align:right;">${{quote_total}}</td>
  </tr>
</table>

<p style="margin:24px 0;">
  <a href="{{quote_url}}" style="background:#2563eb;color:#ffffff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;">Review Your Quote →</a>
</p>

<p style="color:#6b7280;font-size:13px;">You can review the full details, ask questions, and accept or decline online. No account required.</p>

<p>Thank you for considering us,<br><strong>{{company_name}}</strong></p>

<p style="color:#9ca3af;font-size:11px;margin-top:32px;">Do not reply directly to this email — contact support@pilotfortrades.com for help.</p>
```

**Plain text body**:
```
Hi {{customer_name}},

{{company_name}} has sent you a quote for your review.

Quote total: ${{quote_total}}

Review your quote online: {{quote_url}}

You can review the full details, ask questions, and accept or decline. No account required.

Thank you,
{{company_name}}
```

**Variables note**: Existing variables `["customer_name","company_name","quote_total","quote_url"]` are sufficient.

---

#### `payment_received_customer` — "Payment confirmation from {{company_name}}"

**Subject**: `Payment confirmed — ${{amount}} received by {{company_name}}`

**HTML body**:
```html
<p>Hi {{customer_name}},</p>

<p>We've received your payment. Here's your receipt.</p>

<table style="border-collapse:collapse;width:100%;max-width:480px;margin:16px 0;">
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Amount paid</td>
    <td style="padding:8px 0;font-weight:600;text-align:right;">${{amount}}</td>
  </tr>
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Payment date</td>
    <td style="padding:8px 0;text-align:right;">{{payment_date}}</td>
  </tr>
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Paid to</td>
    <td style="padding:8px 0;text-align:right;">{{company_name}}</td>
  </tr>
</table>

<p style="color:#6b7280;font-size:13px;">Please keep this email as your receipt. If you have any questions about this payment, contact us at <a href="mailto:support@{{company_domain}}">support@{{company_domain}}</a>.</p>

<p>Thank you for your business,<br><strong>{{company_name}}</strong></p>

<p style="color:#9ca3af;font-size:11px;margin-top:32px;">Do not reply directly to this email — contact support@pilotfortrades.com for help.</p>
```

**Plain text body**:
```
Hi {{customer_name}},

We've received your payment. Here's your receipt.

Amount paid: ${{amount}}
Payment date: {{payment_date}}
Paid to: {{company_name}}

Please keep this email as your receipt. Questions? Contact us at support@{{company_domain}}.

Thank you for your business,
{{company_name}}
```

**Variables note**: Add `company_domain` to the variables array (currently: `["customer_name","company_name","amount","payment_date"]`).

---

#### `quote_expiring` — "Your quote expires soon"

**Subject**: `Your quote from {{company_name}} expires {{expires_at}}`

**HTML body**:
```html
<p>Hi {{customer_name}},</p>

<p>Just a heads up — your quote from <strong>{{company_name}}</strong> is expiring soon.</p>

<table style="border-collapse:collapse;width:100%;max-width:480px;margin:16px 0;">
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Quote expires</td>
    <td style="padding:8px 0;font-weight:600;text-align:right;">{{expires_at}}</td>
  </tr>
</table>

<p style="margin:24px 0;">
  <a href="{{quote_url}}" style="background:#2563eb;color:#ffffff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;">View Quote →</a>
</p>

<p style="color:#6b7280;font-size:13px;">If you'd like to move forward, accept the quote before it expires. If you need more time or have questions, just reply and let us know.</p>

<p>Thank you,<br><strong>{{company_name}}</strong></p>

<p style="color:#9ca3af;font-size:11px;margin-top:32px;">Do not reply directly to this email — contact support@pilotfortrades.com for help.</p>
```

**Plain text body**:
```
Hi {{customer_name}},

Your quote from {{company_name}} is expiring soon.

Quote expires: {{expires_at}}

View quote: {{quote_url}}

If you'd like to move forward, accept the quote before it expires. If you need more time or have questions, just reach out.

Thank you,
{{company_name}}
```

**Variables note**: Existing variables `["customer_name","quote_url","expires_at"]` are sufficient. Remove the hardcoded "3 days" from the current stub body.

---

#### `payment_failed` — "Payment issue with your invoice"

**Subject**: `Action needed — payment issue on your invoice from {{company_name}}`

**HTML body**:
```html
<p>Hi {{customer_name}},</p>

<p>We weren't able to process your payment for your recent invoice from <strong>{{company_name}}</strong>. This can happen when a card expires, has insufficient funds, or the bank blocks the charge.</p>

<p style="margin:24px 0;">
  <a href="{{invoice_url}}" style="background:#dc2626;color:#ffffff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;">Retry Payment →</a>
</p>

<p style="color:#6b7280;font-size:13px;">You can retry with the same card or use a different payment method online. No account required.</p>

<p style="color:#6b7280;font-size:13px;">If you need help or believe this is a mistake, contact us at <a href="mailto:support@{{company_domain}}">support@{{company_domain}}</a> and we'll sort it out quickly.</p>

<p>Thank you,<br><strong>{{company_name}}</strong></p>

<p style="color:#9ca3af;font-size:11px;margin-top:32px;">Do not reply directly to this email — contact support@pilotfortrades.com for help.</p>
```

**Plain text body**:
```
Hi {{customer_name}},

We weren't able to process your payment for your recent invoice from {{company_name}}.

This can happen when a card expires, has insufficient funds, or the bank blocks the charge.

Retry payment: {{invoice_url}}

You can retry with the same card or use a different payment method. No account required.

If you need help, contact us at support@{{company_domain}}.

Thank you,
{{company_name}}
```

**Variables note**: Add `company_name` and `company_domain` to the variables array (currently: `["customer_name","invoice_url"]`). The backend must pass the tenant's company name and support domain when rendering this template.

---

### Notification Template Draft Copy

The 9 `notification_template` stubs (internal push/email/in-app for tenant owner) fire for tenant-facing events, not customer-facing. The following are v1 copy replacements for the Python Engineer — no Tom approval gate needed for these (internal-only).

| `notification_type_code` | channel | Proposed `body` |
|:---|:---|:---|
| `customer_communication_sent` | email | `A customer communication was sent to {{customer_name}} via {{channel}}.` |
| `customer_communication_sent` | in_app | `Message sent to {{customer_name}}.` |
| `customer_communication_sent` | push | `Message sent to {{customer_name}}.` |
| `dunning_reminder` | email | `Invoice {{invoice_number}} for {{customer_name}} is {{days_overdue}} days overdue. Balance due: ${{amount_due}}. Review and follow up in Pilot.` |
| `dunning_reminder` | in_app | `Invoice {{invoice_number}} is {{days_overdue}} days overdue — ${{amount_due}} outstanding.` |
| `dunning_reminder` | push | `Overdue invoice: {{invoice_number}} — ${{amount_due}} outstanding.` |
| `quote_accepted` | email | `{{customer_name}} accepted your quote. Log in to Pilot to create a job and schedule the work.` |
| `quote_accepted` | in_app | `{{customer_name}} accepted your quote.` |
| `quote_accepted` | push | `New quote acceptance from {{customer_name}}.` |

**Implementation:**
- Update the 5 customer-facing email JSON files in `backend/migrations/scripts/data/email_templates/` with the HTML/plain bodies above
- Update `notification_template` rows in `seed_platform.py` with the `body` values above
- Run the Alembic migration that owns `email_template` rows OR create a new data migration to update HTML/plain bodies
- Update `variables` JSONB arrays for the 3 templates that need new variables: `invoice_sent` (add `due_date`, `company_domain`), `payment_received_customer` (add `company_domain`), `payment_failed` (add `company_name`, `company_domain`)
- No schema changes needed

---

## §SD-09 — Seed Data for Empty Functional Tables

### Disposition by Table

| Table | Rows | Disposition | Owner Script | Difficulty |
|:---|:---:|:---|:---|:---|
| `payment_method` | 0 | `[DEFERRED — NOT A LAUNCH BLOCKER]` | n/a | n/a |
| `help_article` | 0 | `[DEFERRED — NOT A LAUNCH BLOCKER]` | n/a | n/a |
| `help_article_chunk` | 0 | `[DEFERRED — NOT A LAUNCH BLOCKER]` | n/a | n/a |
| `discount_version` | 0 | `[APPROVED FOR IMPLEMENTATION]` | `seed_test_tenant.py` (Group C) | Low |
| `supplier` | 0 | `[APPROVED FOR IMPLEMENTATION]` | `seed_scenario_supplier_catalog.py` (Group D) | Medium |
| `supplier_item` | 0 | `[APPROVED FOR IMPLEMENTATION]` | `seed_scenario_supplier_catalog.py` (Group D) | Medium |
| `supplier_item_price` | 0 | `[APPROVED FOR IMPLEMENTATION]` | `seed_scenario_supplier_catalog.py` (Group D) | Medium |
| `quote_template` | 3 | `[APPROVED FOR IMPLEMENTATION]` | `seed_core.py` (Group A) | Low |

---

### `payment_method` — `[DEFERRED — NOT A LAUNCH BLOCKER]`

**Decision rationale**: The live DB `payment_method` schema requires `tenant_id NOT NULL`, `payment_type_id NOT NULL`, `psp_provider NOT NULL`, and `psp_payment_method_id NOT NULL`. This is not a static platform row — it is a Stripe `PaymentMethod` object stored per-customer after a real Stripe API call. The README spec §B15 note about "1 system row needed for Stripe one-time public link payments" was likely referring to a system-level placeholder for the Stripe one-time payment type, but the schema requires a real Stripe `psp_payment_method_id` which cannot be faked without a Stripe API call. Seeding a fake `psp_payment_method_id` would cause any Stripe webhook reconciliation to fail. Deferring until Stripe test-mode data generation is included in the E2E harness design (SD-10).

---

### `help_article` + `help_article_chunk` — `[DEFERRED — NOT A LAUNCH BLOCKER]`

**Decision rationale**: Seeding these tables requires either (a) running the full embedding pipeline (OpenAI `text-embedding-3-small` → pgvector HNSW inserts) or (b) using pre-computed test vectors with the correct dimensions. For dev/QA, pre-computed test vectors are acceptable, but the vector dimensionality must match the `help_article_chunk` embedding column dimensions, which requires reading the HNSW index definition first. This is a non-trivial setup that warrants its own task. The help chat feature is gated behind a corpus anyway — without real articles, the AI returns "I don't know." The feature is still demonstrable with the stub "I don't know" response. Defer to a dedicated `seed_scenario_help_corpus.py` design (a follow-on after SD-10 test harness is approved, since the harness will need a corpus too).

---

### `discount_version` — `[APPROVED FOR IMPLEMENTATION]`

**MCP-confirmed schema**: `id bigint` (AppendOnly PK), `tenant_id UUID nullable`, `code VARCHAR NOT NULL`, `pct_off NUMERIC nullable`, `amount_off_cents INTEGER nullable`, `valid_period tstzrange NOT NULL`, `recorded_at TIMESTAMPTZ NOT NULL`, `created_at TIMESTAMPTZ NOT NULL`, `created_by UUID nullable`.

**No GiST exclusion constraint** — confirmed via `pg_constraint` query. Unlike `labor_rate_version`, `discount_version` has no exclusion constraint on `(tenant_id, valid_period)`. Only a simple CHECK that either `pct_off` or `amount_off_cents` is non-null (not both).

**What to seed**: Add 2 rows to `seed_test_tenant.py` alongside labor rates and markup:
1. `SUMMER_PROMO` — 10% off (`pct_off=10`), valid_period = closed past range `[2024-06-01, 2024-08-31)`
2. `NEW_CUSTOMER` — $25 off (`amount_off_cents=2500`), valid_period = open-ended range `[2026-01-01, NULL)`

**Script group**: Group C (`seed_test_tenant.py`) — discount_version is pricing engine config, same as labor rates and markup.

**Implementation note**: `valid_period` is a `tstzrange` — use `tstzrange('2024-06-01', '2024-08-31')` for the closed range and `tstzrange('2026-01-01', NULL)` for the open range. The `recorded_at` field requires an explicit value (not server default) — use `NOW()`.

---

### `supplier`, `supplier_item`, `supplier_item_price` — `[APPROVED FOR IMPLEMENTATION]`

**What to seed**: A new `seed_scenario_supplier_catalog.py` (Group D) should seed:

**`supplier`** (1 row): One electrical supplier using existing `supplier_item_category` codes already in `seed_core.py`:
- Name: `Wesco Distribution` (major national electrical distributor)
- `lifecycle_status_code`: `active`
- Address: standard test address

**`supplier_item`** (5 rows — one per major category): Cover the most common electrical categories already seeded in `supplier_item_category`:
1. 12 AWG THHN Wire — `wire_cable`, UOM: `foot`
2. 1/2" EMT Conduit — `conduit_raceway`, UOM: `foot`
3. Square D QO115 15A Breaker — `dist_equip`, UOM: `each`
4. Standard Duplex Outlet — `wiring_devices`, UOM: `each`
5. 1/2" EMT Coupling — `fittings`, UOM: `each`

**`supplier_item_price`** (5 rows): Need to verify schema before implementation. One current-price row per item. Python Engineer must run `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'supplier_item_price'` before writing inserts.

**GiST constraints**: Need Python Engineer to verify `supplier_item_price` schema for date-range constraints before inserting.

**Script group**: Group D (`seed_scenario_supplier_catalog.py`) — supplier data is scenario-level, not core platform config. Register as `"supplier_catalog"` in `reset_dev_db.py`.

---

### `quote_template` — `[APPROVED FOR IMPLEMENTATION]`

**Origin confirmed via MCP**: All 3 rows have `created_at = 2026-05-01T11:10:45.578Z`, which matches Alembic migration `2026_05_01_1109-29384efbde55_phase_fe_1_batch_b1_quote_template_schema.py`. The 3 system templates (`Service Call Basic`, `Installation Standard`, `Fixed Bid Simple`) are definitively Alembic-owned.

**Action**: Add all 3 rows to `seed_core.py` Group A. The migration seeds them with `tenant_id IS NULL` (system templates). `seed_core.py` should use `INSERT ... ON CONFLICT (id) DO NOTHING`.

**Python Engineer must query the full schema** (`SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'quote_template' ORDER BY ordinal_position`) before writing inserts — verify all required columns and constraints.

---

## §SD-10 — Scenario Coverage Analysis + E2E Test Harness

### `[APPROVED FOR IMPLEMENTATION]` (architecture recommendation — Tom must approve full harness before implementation batch starts)

---

### Part A — Scenario Coverage Catalog

| Workflow | Key Runtime Tables | Current Scenario | Gap |
|:---|:---|:---|:---|
| Customer receives and replies to SMS | `customer_communication_thread`, `customer_communication_message`, `message_read_state` | ✅ SD-02 complete | Thread + messages seeded; `message_read_state` not seeded |
| Tech clocks in + out on a job | `job_time_entry` | ✅ SD-03 complete | 7 time entries seeded in reporting scenario |
| Tech logs expense on a job | `job_expense` | ✅ SD-03 complete | 5 expense rows seeded |
| Quote approved, sent to customer, accepted | `quote_acceptance`, `quote_message`, `quote_public_link`, `quote_pending_edit` | ☐ No scenario | `seed_scenario_quote_to_cash.py` has a draft quote only — not sent or accepted |
| Invoice created, sent, paid via Stripe | `invoice`, `invoice_public_link`, `payment`, `psp_transaction_log` | ☐ No scenario | Full invoice-to-payment flow not seeded |
| Voice session creates a quote | `conversation_session`, `conversation_message`, `voice_command_log`, `voice_command_entity_link` | ☐ No scenario | Voice AI flow requires real Whisper/Ollama — impractical to seed |
| NEC calculation run | `nec_calculation_log` | ☐ No scenario | Can be seeded with synthetic calculation records |
| QuickBooks connected + sync runs | `integration_credential`, `integration_sync_mapping`, `integration_sync_log`, `connector_run_log` | ☐ No scenario | Requires OAuth flow — not seedable without Stripe/QB mock |
| QB conflict detected and resolved | `integration_sync_conflict` | ☐ No scenario | Can insert synthetic conflict rows |
| Calendar integration synced | `tenant_calendar_integration`, `calendar_sync_log`, `calendar_sync_conflict` | ☐ No scenario | Requires Google OAuth — not seedable |
| Mobile tech syncs offline changes | `mobile_sync_session`, `mobile_sync_event`, `mobile_sync_event_audit` | ☐ No scenario | Can insert synthetic sync event rows |
| Owner escalation created + resolved | `mobile_sync_owner_escalation` | ☐ No scenario | Can insert synthetic escalation row |
| Stripe subscription created, webhook received | `subscription_usage`, `stripe_webhook_event_processed`, `psp_customer` | ☐ No scenario | Requires Stripe test mode — not seedable statically |
| User logs in, MFA enrolled | `user_mfa_method`, `auth_mfa_otp`, `mfa_grace_period_tracking` | ☐ No scenario | Can seed `user_mfa_method` rows for test user |
| Help chat session with AI response | `help_chat_session`, `help_chat_message`, `help_article_chunk` | ☐ Blocked by SD-09 | Blocked on help corpus — SD-09 deferred |
| Notification delivered across channels | `notification_event`, `notification_outbox`, `notification_delivery_attempt`, `in_app_notification` | ☐ No scenario | Can seed synthetic notification rows |

**Scenarios that can be seeded statically (no external API required):**
- Quote sent + accepted (extend `seed_scenario_quote_to_cash.py`)
- Invoice created + sent (extend quote-to-cash or new script)
- NEC calculation log rows
- QB sync conflict rows (synthetic)
- Mobile sync session + events (synthetic)
- Notification events + outbox (synthetic)
- MFA method enrollment (for test tech user)

**Scenarios that require a test/mock infrastructure layer:**
- Full invoice-to-payment (requires Stripe test webhook)
- QuickBooks connect + sync (requires QB sandbox OAuth)
- Voice AI session (requires Whisper/Ollama running)
- Calendar sync (requires Google OAuth)
- Stripe subscription webhooks

---

### Part B — Automated Test Harness Architecture Decision

#### Recommended Harness

**3-tier hybrid approach:**

| Tier | Technology | Scope | When Runs |
|:---|:---|:---|:---|
| **Tier 1** | `pytest` + `httpx` (FastAPI integration tests) | All API backend flows, webhook handlers, Celery task logic | Every PR |
| **Tier 2** | Playwright (browser E2E) | Web app critical paths (login → quote → invoice → pay) | Nightly + before release |
| **Tier 3** | Maestro (mobile E2E) | Mobile critical paths (login → today view → clock-in → voice) | Weekly (iOS Expo dev build) |

**Why this recommendation:**
- Tier 1 already exists (3,863 passing unit tests + integration suite). The PR gate should be expanded to include scenario-level integration tests, not just unit tests.
- Tier 2 (Playwright) provides the highest confidence for customer-visible flows. The 51 existing Playwright specs should be expanded to cover the 5 priority scenarios below.
- Tier 3 (Maestro) is expensive to maintain and should cover only the non-negotiable mobile paths (GPS clock-in, voice AI, offline sync) — not every feature.

#### Seeding Strategy

**Decision: Per-scenario seed state with nightly full reset.**

- Each scenario starts from a known seed state by calling `reset_dev_db.py --scenarios [list]` at the start of the scenario's test file
- A dedicated `pilot_e2e_db` database (separate from the dev DB) is used — never run teardown against the dev DB
- `pytest globalSetup.ts` for Playwright uses `/test` endpoints to seed tenant + scenario data
- Group A + B + C seed scripts run once at E2E environment init; only Group D is reset per scenario

#### CI/CD Integration

| Test Type | GitHub Actions Trigger | Expected Duration |
|:---|:---|:---|
| `pytest -m unit` (3,863 tests) | Every PR push | ~3 min |
| `pytest -m integration` (full suite) | Every PR merge to main | ~8 min |
| Playwright Tier 2 (priority 5) | Nightly at 02:00 UTC | ~15 min |
| Maestro Tier 3 (iOS 3 paths) | Every Monday 06:00 UTC | ~20 min |

#### Expected Outcome Assertion Pattern

Tests must assert **specific business outcomes**, not just HTTP 200:

```python
# Good — asserts specific data state
def test_quote_to_cash_flow():
    # Create quote
    quote = create_quote(line_items=[...], customer_id=...)
    assert quote["status_code"] == "draft"
    assert quote["total_cents"] == 24000
    
    # Send quote
    sent = send_quote(quote["id"])
    assert sent["status_code"] == "sent"  # Note: quote_status uses "sent" correctly
    
    # Customer accepts
    accepted = accept_quote_public(sent["quote_public_link_token"])
    assert accepted["status_code"] == "approved"
    
    # Invoice created from quote
    invoice = create_invoice_from_quote(quote["id"])
    assert invoice["total_cents"] == quote["total_cents"]
    assert invoice["status_code"] == "issued"
```

#### First 5 Priority Scenarios to Automate

| Priority | Scenario | Tier | Estimated Build Time |
|:---|:---|:---|:---|
| P1 | Auth + Tenant Isolation (owner/tech/office login + RBAC enforcement) | Tier 2 (Playwright) | 2 days |
| P2 | Quote-to-Cash (draft → send → customer accepts → invoice → payment recorded) | Tier 2 (Playwright) | 3 days |
| P3 | Dispatch + Field Sync (job create → assign tech → time entry → job complete) | Tier 1 (pytest httpx) | 2 days |
| P4 | Customer SMS thread (send → reply → unread badge clears) | Tier 1 (pytest httpx) | 1 day |
| P5 | Dunning cycle (invoice overdue → reminder sent → payment recorded → dunning stops) | Tier 1 (pytest httpx) | 1 day |

#### Maintenance Strategy

- **Owner**: Python Engineer (backend Tier 1) + React Engineer (Tier 2 Playwright)
- **Flaky test policy**: Any test that fails >2 times in 5 runs is quarantined (marked `@pytest.mark.flaky`) and filed as a P2 bug. Flaky tests are not allowed to block PR merge.
- **Schema changes**: When a migration adds/removes columns, the affected scenario tests must be updated in the same PR — enforced by a CI step that runs Tier 1 integration tests on every migration PR.

---

## G. Open Questions Resolved

| Question | Resolution |
|:---|:---|
| Should refund tracking use new `payment_status` codes or new `payment` columns? | Columns (`refunded_amount_cents`, `refunded_at`) — aligns with Stripe model, avoids status lifecycle complexity |
| Is "overdue" a DB status code or a derived property? | Derived property — computed at runtime; `InvoicesPage.tsx` has a bug using it as a filter value |
| Does `backend/tasks/` contain an invoice reminder task? | Yes — `dunning.py` exists but fires every 60min with only internal notifications; no customer SMS; needs enhancement |
| Is `discount_version` GiST-constrained like `labor_rate_version`? | No — confirmed via `pg_constraint` query; no exclusion constraint; insertion is straightforward |
| What is the origin of the 3 `quote_template` rows? | Alembic-owned (`created_at` = 2026-05-01 matches migration `29384efbde55`); add to `seed_core.py` |
| Should `qb_sync_operations` remain as a product feature? | No — GTM matrix confirms QB sync is unlimited on all tiers; this feature should be removed |
| Are all 13 MVP `customer_comm_template_type` codes present in the live DB? | Yes — all 13 confirmed `is_active=true`; no gaps |
| Does `notification_template` have real copy? | No — all 9 rows are confirmed literal placeholder strings; need copy before GA |
| Does the existing `payment_method` schema support a system seed row? | No — requires real Stripe `psp_payment_method_id`; seeding deferred |
| What are the correct `email_template` column names? | `template_id` (not `template_code`); `body_html_template` (not `html_body`); `body_plain_template` (not `plain_text_body`) |

---

## Implementation Batch Assignments

| Task | Disposition | Engineers | Prerequisites |
|:---|:---|:---|:---|
| SD-05 — Payment refund columns + webhook | `[APPROVED]` | Python Engineer | None |
| SD-06 Part A — InvoicesPage.tsx bug fixes | `[APPROVED]` | React Engineer | None |
| SD-06 Part B — Enhanced dunning + new invoice columns + platform settings | `[APPROVED]` | Python Engineer | None |
| SD-07 — Product feature table revision | `[BLOCKED — TOM]` | Python Engineer (after approval) | Tom approves feature set |
| SD-08 — Template copy updates | `[BLOCKED — TOM]` | Python Engineer (after approval) | Tom approves copy |
| SD-09 — `discount_version` seed + `quote_template` seed_core + supplier catalog script | `[APPROVED]` | Python Engineer | None |
| SD-10 — E2E harness implementation | `[APPROVED — recommendation]` | Python Engr + React Engr | Tom approves architecture; full implementation is a separate batch |

---

*Design doc complete. All 6 SD tasks dispositioned. See `dev-docs/analysis/pilot-launch-plan.md` and `backend/migrations/scripts/README-seed-data.md` §10 for updated gate status.*
