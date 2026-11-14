# Batch B4 Design Document — Customer Comms Base

**Batch**: B4  
**Theme**: Customer Comms Base  
**Prerequisite batches**: None (parallel-safe with B1, B2, B3, B5)  
**Gates**: B11 (SMS/Telnyx stack extends this base)  
**Estimated effort**: 11–16 days  
**Test subfolder**: `tests/batch_b4/`  
**Design completed**: 2026-05-01  
**Source documents**: impl-plan §6.B4; additions-ledger A4, A8, A21, A22, A23; mvp-arch §6.2, §6.6, §16.3, §16.7; pilot-python-engineer-methods §20, §22

---

## A. MIGRATION PLAN

### A.1 Verification Results from Live DB (via postgres-local MCP)

The following queries were executed before writing this migration plan:

| Table | Status | Action |
|:------|:-------|:-------|
| `communication_template` | **DOES NOT EXIST** | Full CREATE TABLE |
| `customer_communication` | **DOES NOT EXIST** | Full CREATE TABLE |
| `customer.preferred_contact_channel` | **DOES NOT EXIST** | ADD COLUMN to `customer` |
| `notification_outbox` | EXISTS — channel CHECK: `'email','sms','in_app'` | No change needed; SMS already in enum |
| `notification_outbox.category_id` | **DOES NOT EXIST** | Not B4's concern (B9/A56) |

---

### Migration 1: `phase_fe_1_batch_b4_communication_tables`

Creates both new tables in a single migration. `communication_template` must precede `customer_communication` (FK dependency).

#### Table: `communication_template`

A tenant-aware lookup table. `tenant_id IS NULL` = system-managed template; `tenant_id IS NOT NULL` = tenant-specific customization (planned for post-MVP; seeded at system level in B4).

```sql
CREATE TABLE communication_template (
    -- audit mixin fields
    created_at             TIMESTAMPTZ NOT NULL,
    updated_at             TIMESTAMPTZ NOT NULL,
    created_by             UUID REFERENCES "user"(id) ON DELETE RESTRICT,
    updated_by             UUID REFERENCES "user"(id) ON DELETE RESTRICT,

    -- primary key
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- tenant scoping (NULL = system-level template)
    tenant_id              UUID REFERENCES tenant(id) ON DELETE RESTRICT,

    -- template identity
    template_code          VARCHAR NOT NULL,   -- 'on_my_way' | 'running_late' | 'arrived' | 'job_complete' | 'parts_delay' | 'confirm_appointment'
    channel                VARCHAR NOT NULL,   -- 'sms' | 'email'

    -- content
    subject                TEXT,              -- email subject (NULL for SMS)
    body_template          TEXT NOT NULL,     -- Jinja2 template string; vars: {customer_name}, {customer_first_name}, {eta}, {minutes_late}, {date_time}, {site_address}

    -- lifecycle
    is_active              BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT communication_template_channel_chk
        CHECK (channel IN ('sms', 'email')),

    CONSTRAINT communication_template_code_chk
        CHECK (template_code IN ('on_my_way','running_late','arrived','job_complete','parts_delay','confirm_appointment')),

    CONSTRAINT communication_template_email_subject_chk
        CHECK (channel <> 'email' OR subject IS NOT NULL)
);

-- Composite unique: one active template per (tenant_or_system, code, channel)
CREATE UNIQUE INDEX uq_communication_template_scope
    ON communication_template (COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid), template_code, channel)
    WHERE is_active = TRUE;

CREATE INDEX idx_communication_template_tenant_id
    ON communication_template (tenant_id);

CREATE INDEX idx_communication_template_code_channel
    ON communication_template (template_code, channel);
```

**Seed data** (inserted in the same migration `data_migrations` block or a companion seed script):

| template_code | channel | body_template |
|:---|:---|:---|
| `on_my_way` | `sms` | `Hi {{ customer_first_name }}, this is {{ sender_name }} — I'm on my way, ETA {{ eta }}. Reply STOP to opt out.` |
| `on_my_way` | `email` | Subject: `On my way — ETA {{ eta }}` · Body: `Hi {{ customer_first_name }},\n\nI'm on my way to {{ site_address }}. ETA {{ eta }}.\n\n{{ sender_name }}` |
| `running_late` | `sms` | `Hi {{ customer_first_name }}, {{ sender_name }} here — running about {{ minutes_late }} minutes behind. Apologies for the delay. Reply STOP to opt out.` |
| `arrived` | `sms` | `Hi {{ customer_first_name }}, {{ sender_name }} here — I've arrived and am starting work. Reply STOP to opt out.` |
| `job_complete` | `sms` | `Hi {{ customer_first_name }}, {{ sender_name }} here — work is complete. Invoice to follow. Reply STOP to opt out.` |
| `parts_delay` | `sms` | `Hi {{ customer_first_name }}, {{ sender_name }} here — there's a parts delay. I'll update you as soon as I have more info. Reply STOP to opt out.` |
| `confirm_appointment` | `sms` | `Hi {{ customer_first_name }}, please confirm your appointment for {{ date_time }} at {{ site_address }}. Reply YES to confirm or call us. Reply STOP to opt out.` |

*Email variants for all codes except `on_my_way` are post-MVP; SMS is the default for all codes in B4.*

#### Table: `customer_communication`

The durable send-log. One row per outbound message dispatched.

```sql
CREATE TABLE customer_communication (
    -- audit mixin fields
    created_at             TIMESTAMPTZ NOT NULL,
    updated_at             TIMESTAMPTZ NOT NULL,
    created_by             UUID REFERENCES "user"(id) ON DELETE RESTRICT,
    updated_by             UUID REFERENCES "user"(id) ON DELETE RESTRICT,

    -- primary key
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- tenant + CRM FKs
    tenant_id              UUID NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
    customer_id            UUID NOT NULL REFERENCES customer(id) ON DELETE RESTRICT,
    job_id                 UUID REFERENCES job(id) ON DELETE SET NULL,
    sender_user_id         UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,

    -- template reference
    template_code          VARCHAR NOT NULL,
    template_id            UUID REFERENCES communication_template(id) ON DELETE SET NULL,  -- snapshot reference

    -- rendered content (server-side at send time)
    rendered_subject       TEXT,              -- NULL for SMS
    rendered_message       TEXT NOT NULL,

    -- channel metadata (populated by A4 base + extended by A21)
    channel                VARCHAR NOT NULL,  -- 'sms' | 'email'
    customer_preferred_channel VARCHAR,       -- A21: customer's stored preference at send time (audit field)
    actual_channel         VARCHAR NOT NULL,  -- A21: the channel actually used
    channel_override_flag  BOOLEAN NOT NULL DEFAULT FALSE,  -- A21: TRUE when actual_channel != customer_preferred_channel

    -- delivery tracking
    status                 VARCHAR NOT NULL DEFAULT 'pending',  -- 'pending' | 'sent' | 'failed' | 'canceled'
    sent_at                TIMESTAMPTZ,
    notification_outbox_id UUID REFERENCES notification_outbox(id) ON DELETE SET NULL,

    -- variables snapshot (for audit/preview reproducibility)
    variables_json         JSONB,

    CONSTRAINT customer_communication_channel_chk
        CHECK (channel IN ('sms', 'email')),
    CONSTRAINT customer_communication_actual_channel_chk
        CHECK (actual_channel IN ('sms', 'email')),
    CONSTRAINT customer_communication_status_chk
        CHECK (status IN ('pending', 'sent', 'failed', 'canceled')),
    CONSTRAINT customer_communication_template_code_chk
        CHECK (template_code IN ('on_my_way','running_late','arrived','job_complete','parts_delay','confirm_appointment'))
);

CREATE INDEX idx_customer_communication_tenant_id
    ON customer_communication (tenant_id);

CREATE INDEX idx_customer_communication_customer_id
    ON customer_communication (customer_id);

CREATE INDEX idx_customer_communication_customer_sent
    ON customer_communication (customer_id, sent_at DESC NULLS LAST);

CREATE INDEX idx_customer_communication_tenant_sent
    ON customer_communication (tenant_id, sent_at DESC NULLS LAST);

CREATE INDEX idx_customer_communication_job_id
    ON customer_communication (job_id)
    WHERE job_id IS NOT NULL;

CREATE INDEX idx_customer_communication_notification_outbox_id
    ON customer_communication (notification_outbox_id)
    WHERE notification_outbox_id IS NOT NULL;
```

---

### Migration 2: `phase_fe_1_batch_b4_customer_preferred_channel`

Adds the `preferred_contact_channel` field to `customer`. Verified via MCP: this column **does not exist** in the live `customer` table.

```sql
ALTER TABLE customer
    ADD COLUMN preferred_contact_channel VARCHAR(10) NOT NULL DEFAULT 'sms';

ALTER TABLE customer
    ADD CONSTRAINT customer_preferred_contact_channel_chk
        CHECK (preferred_contact_channel IN ('sms', 'email'));
```

**Rationale**: A21 requires this field for the channel override audit trail and for the send endpoint to resolve the customer's stored preference. Default `'sms'` aligns with the existing MVP assumption that tech-to-customer communications are SMS-first.

---

### Summary of all schema changes

| Table | Change type | Columns |
|:------|:------------|:--------|
| `communication_template` | **NEW TABLE** | id, tenant_id, template_code, channel, subject, body_template, is_active + audit mixin |
| `customer_communication` | **NEW TABLE** | id, tenant_id, customer_id, job_id, sender_user_id, template_code, template_id, rendered_subject, rendered_message, channel, customer_preferred_channel, actual_channel, channel_override_flag, status, sent_at, notification_outbox_id, variables_json + audit mixin |
| `customer` | **ADD COLUMN** | `preferred_contact_channel VARCHAR(10) NOT NULL DEFAULT 'sms'` |

---

## B. EXECUTION ORDER

| # | Item | Position Rationale |
|:--|:-----|:-------------------|
| 1 | **A4** — Templated Customer Communications (Core) | Foundation: creates both new tables (`communication_template`, `customer_communication`), the template variable substitution service (`customer_comms_service.py`), and the `POST /api/v1/communications/send` endpoint. All subsequent items depend on this schema and service. |
| 2 | **A8** — Communication History Endpoint | Trivial `GET` read on the table created by A4. Zero risk; zero new schema. Folds into A4's implementation as a second route handler in the same file. |
| 3 | **A21** — Per-Message Channel Override | Extends A4's `customer_communication` table with three audit columns (`customer_preferred_channel`, `actual_channel`, `channel_override_flag`) and adds the `preferred_contact_channel` column to `customer`. Also adds the optional `channel_override` parameter to the send endpoint built in A4. A4 must be complete before A21 modifies it. |
| 4 | **A23** — Communication Preview Endpoint | Extracts A4's template rendering logic into a shared service function and exposes it as a read-only `POST /api/v1/communications/preview` endpoint. Must follow A4 (it refactors A4's rendering) and A21 (it respects the channel override param). |
| 5 | **A22** — Voice Intent Grammar for Customer Communications | Depends on A4 (template codes and `customer_communication` write path), A23 (preview endpoint consumed by confirm-as-turn voice flow). Always-preview-before-send requires A23 to exist before A22 handlers can call it. Customer resolution priority chain reuses context from A10 (B2). |

---

## C. NEW API ENDPOINTS

### C.1 `POST /api/v1/communications/send` — A4 / A21

Send a templated customer communication.

**Auth**: JWT required  
**Permission**: `communications.send` (new permission — see Section D)

**Request body**:
```json
{
  "customer_id":    "uuid",
  "template_code":  "on_my_way",
  "job_id":         "uuid | null",
  "variables": {
    "eta":          "10:45 AM",
    "minutes_late": null,
    "date_time":    null,
    "site_address": "742 Evergreen Terrace"
  },
  "channel_override": "email | null"
}
```

*`channel_override` (A21)*: if provided, forces `actual_channel` to this value regardless of `customer.preferred_contact_channel`. The customer's stored preference is unchanged.

**Response** `201 Created`:
```json
{
  "communication_id":  "uuid",
  "template_code":     "on_my_way",
  "actual_channel":    "sms",
  "channel_override_flag": false,
  "status":            "pending",
  "rendered_message":  "Hi Jane, this is Mike — I'm on my way, ETA 10:45 AM. Reply STOP to opt out.",
  "rendered_subject":  null,
  "recipient_address": "+15125550123",
  "sent_at":           null
}
```

**Server-side behavior**:
1. Fetch `CommunicationTemplate` by `(template_code, actual_channel)` — tenant-specific override first; fall back to system template (tenant_id IS NULL).
2. Resolve `actual_channel`: `channel_override` if provided, else `customer.preferred_contact_channel`.
3. Set `channel_override_flag = (channel_override is not None and channel_override != customer.preferred_contact_channel)`.
4. Call `render_communication_preview()` from `services/customer_comms_service.py` to get rendered body and subject.
5. Write `CustomerCommunication` row with `status='pending'`.
6. Create `NotificationEvent` + `NotificationOutbox` entry (channel=`actual_channel`, `to_address=customer.mobile_phone` for SMS or `customer.email` for email) in the same DB transaction.
7. Update `CustomerCommunication.notification_outbox_id` and `status='pending'`.
8. Commit. The existing `poll_pending_notifications` Celery task (registered in `tasks/notification_worker.py`) handles the actual SMS/email dispatch.

---

### C.2 `GET /api/v1/customers/{customer_id}/communications` — A8

Paginated communication history for a customer.

**Auth**: JWT required  
**Permission**: `customers.view`

**Query params**: `page` (int, default 1), `page_size` (int, default 20, max 100)

**Response** `200 OK`:
```json
{
  "customer_id": "uuid",
  "total":       42,
  "page":        1,
  "page_size":   20,
  "items": [
    {
      "communication_id":       "uuid",
      "template_code":          "on_my_way",
      "actual_channel":         "sms",
      "channel_override_flag":  false,
      "customer_preferred_channel": "sms",
      "rendered_message":       "Hi Jane...",
      "rendered_subject":       null,
      "status":                 "sent",
      "sent_at":                "2026-05-01T14:30:00Z",
      "sender_user_id":         "uuid",
      "job_id":                 "uuid | null"
    }
  ]
}
```

---

### C.3 `POST /api/v1/communications/preview` — A23

Render a template without dispatching. Pure read operation.

**Auth**: JWT required  
**Permission**: `communications.send`

**Request body**:
```json
{
  "customer_id":    "uuid",
  "template_code":  "on_my_way",
  "variables": {
    "eta":          "10:45 AM",
    "minutes_late": null,
    "date_time":    null,
    "site_address": "742 Evergreen Terrace"
  },
  "channel_override": "email | null"
}
```

**Response** `200 OK`:
```json
{
  "rendered_subject":   null,
  "rendered_body":      "Hi Jane, this is Mike — I'm on my way, ETA 10:45 AM. Reply STOP to opt out.",
  "recipient_name":     "Jane Johnson",
  "recipient_address":  "+15125550123",
  "actual_channel":     "sms",
  "editable_variables": [
    {"name": "eta",          "current_value": "10:45 AM",  "description": "Estimated arrival time"},
    {"name": "site_address", "current_value": "742 Evergreen Terrace", "description": "Job site address"}
  ]
}
```

**Critical constraint**: This endpoint **NEVER** writes to `customer_communication` and **NEVER** creates a `NotificationOutbox` entry. It calls `render_communication_preview()` from `services/customer_comms_service.py` and returns the result. No side effects.

---

### C.4 Voice intent handlers — A22

No separate HTTP endpoints. These are function additions to `backend/services/voice_action_router.py` registered in `INTENT_HANDLERS`. The voice pipeline calls them via `execute_action()`. Each handler calls `POST /api/v1/communications/preview` internally (or calls `render_communication_preview()` directly) then applies the confirm-as-turn gate.

| Intent key | Handler function | Utterance examples |
|:-----------|:----------------|:-------------------|
| `tell_customer` | `tell_customer_via_voice()` | "Tell Johnson I'm 20 out" → `on_my_way` |
| `tell_customer_running_late` | `tell_customer_running_late_via_voice()` | "Tell Davis I'm running 30 minutes late" → `running_late` |
| `tell_customer_arrived` | `tell_customer_arrived_via_voice()` | "I just arrived", "I'm here" → `arrived` |
| `tell_customer_completed` | `tell_customer_completed_via_voice()` | "The job's done", "All finished" → `job_complete` |

*`parts_delay` and `confirm_appointment` are dispatched by `tell_customer` intent with sub-entity routing. All 6 template codes must be reachable from voice.*

---

## D. PATTERN REUSE DECISIONS

### D.1 Always-Preview-Before-Send — §16.7 (arch) — A23, A22

**First established**: Flow 4 (Customer Comms). This batch IS the founding implementation.

**Pattern**: The preview endpoint (`POST /api/v1/communications/preview`) is the server-side gate. The frontend (and voice path) always calls preview before calling send. They are separate HTTP requests — the preview never dispatches.

**Voice path enforcement** (A22): each voice handler renders preview first, writes `pending_confirmation` to `context_window_json`, and returns the preview text as the AI's spoken response. The user's next utterance ("yes" / "send it") triggers the actual `POST /api/v1/communications/send` call with the same parameters.

**Shared function** (`services/customer_comms_service.py`):
```python
def render_communication_preview(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    template_code: str,
    variables: Dict[str, Any],
    channel_override: str | None = None,
    sender_user: AuthenticatedUser | None = None,
) -> CommunicationPreviewResult:
    """
    Pure render — no writes, no side effects.
    Called by both the preview endpoint (A23) and the send endpoint (A4)
    to ensure preview and send always render identically.
    """
```

Both A4 (send) and A23 (preview) call this function. This guarantees the message the user previewed is exactly what gets sent.

### D.2 Confirm-As-Turn for Voice — §16.3 (arch) / §6.6 (arch) — A22

**Applied to**: All 4 voice handlers added in A22.

**Mechanism**: Before committing a send, the handler writes to `ConversationSession.context_window_json.pending_confirmation`:
```json
{
  "intent_type":    "tell_customer",
  "entities":       { "customer_id": "uuid", "template_code": "on_my_way", "eta": "10:45 AM" },
  "preview_text":   "Hi Jane, this is Mike — I'm on my way, ETA 10:45 AM. Reply STOP to opt out.",
  "summary_prompt": "Ready to send to Jane Johnson via SMS: 'Hi Jane, this is Mike...' — confirm?",
  "expires_at":     "2026-05-01T14:32:00Z"
}
```

The AI reads `preview_text` aloud. User confirms → `execute_action()` reads `pending_confirmation`, calls `POST /api/v1/communications/send`, clears `pending_confirmation`.

**Integration with `execute_action()`**: uses existing `execute_action(intent_type, entities, current_user, db, session)` signature. No changes to the router itself — only new handler functions added.

### D.3 Existing Template Renderer — A4, A23

**Reuses**: `services/template_renderer.py` — `render_template(template_string: str, context: Dict[str, Any]) -> str` (Jinja2-based, line 12) and `render_subject(subject_string: str, context: Dict[str, Any]) -> str` (line 42).

`services/customer_comms_service.py` imports these. No changes to `template_renderer.py`.

### D.4 Existing Notification Outbox Infrastructure — A4

**Reuses**: `app/models/system.py` — `NotificationOutbox`, `NotificationEvent`, `NotificationType`.

**Creation pattern** (mirrors `quickbooks_sync.py` and `scheduling.py`):
```python
from app.models.system import NotificationEvent, NotificationOutbox, NotificationType

# Step 1: create event
event = NotificationEvent(
    tenant_id=tenant_id,
    notification_type_code="customer_communication_sent",
    entity_type_code="customer_communication",
    entity_id=str(comm.id),
)
db.add(event)
db.flush()

# Step 2: create outbox entry
outbox = NotificationOutbox(
    tenant_id=tenant_id,
    notification_event_id=event.id,
    channel=actual_channel,   # 'sms' or 'email'
    to_address=recipient_address,  # mobile_phone for SMS, email for email
    body=rendered_message,
    subject=rendered_subject,      # None for SMS
    idempotency_key=str(comm.id),
)
db.add(outbox)
db.flush()

# Step 3: link back
comm.notification_outbox_id = outbox.id
db.add(comm)
db.commit()
```

**Existing worker**: `tasks/notification_worker.py` — `poll_pending_notifications` Celery task already handles SMS + email dispatch. B4 does not modify this task.

### D.5 Customer Fuzzy-Match Pattern — A22

**Reuses**: Customer resolution pattern established in `services/voice_action_router.py` in `create_quote_via_voice()`:
```python
customer = db.exec(
    select(Customer)
    .where(Customer.tenant_id == current_user.tenant_id)
    .where(Customer.display_name.ilike(f"%{customer_name}%"))
).first()
```

A22 handlers extend this with the B4-specific **customer resolution priority chain**:
1. `context_window_json.active_customer_id` — customer already in session context
2. Named in utterance → fuzzy match on `Customer.display_name`
3. Multiple matches → disambiguation prompt (return clarification response, do not write `pending_confirmation`)
4. No name and no context → prompt for customer name

### D.6 INTENT_HANDLERS Registration — A22

**Extends** the `INTENT_HANDLERS` dict at `services/voice_action_router.py`. New entries:
```python
INTENT_HANDLERS = {
    # ... existing entries ...
    # A22: Customer Communications (B4)
    "tell_customer":               tell_customer_via_voice,
    "tell_customer_running_late":  tell_customer_running_late_via_voice,
    "tell_customer_arrived":       tell_customer_arrived_via_voice,
    "tell_customer_completed":     tell_customer_completed_via_voice,
}
```

### D.7 RBAC — New Permission `communications.send`

**Does not exist** in current `permissions.py` system. Must be added to the relevant role definitions in the seed migration. Scope:
- `owner` role: inherits via `*` wildcard (no change needed)
- `technician` role: must have `communications.send` explicitly added — techs are the primary senders
- `office_staff` role: add `communications.send` — dispatchers can send comms

`customers.view` (already exists) covers A8's history endpoint.

---

## E. SHARED MODULE INTERFACES

### E.1 `services/customer_comms_service.py` — New file (B4)

```python
# backend/services/customer_comms_service.py
"""
Customer Communication Service — B4 (A4, A21, A22, A23)

Provides the shared render function used by both the preview endpoint (A23)
and the send endpoint (A4). Ensures preview and send are always identical.

Import path: from services.customer_comms_service import render_communication_preview, CommunicationPreviewResult
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict
from uuid import UUID

from sqlmodel import Session, select

from app.models.communications import CommunicationTemplate, CustomerCommunication
from app.models.crm import Customer
from services.template_renderer import render_subject, render_template

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class EditableVariable:
    name: str
    current_value: str | None
    description: str


@dataclass
class CommunicationPreviewResult:
    rendered_body: str
    rendered_subject: str | None       # None for SMS
    recipient_name: str
    recipient_address: str             # E.164 phone for SMS; email address for email
    actual_channel: str                # 'sms' | 'email'
    editable_variables: list[EditableVariable]
    template_id: UUID | None           # FK snapshot for the send path
    customer_preferred_channel: str    # stored preference at render time (A21 audit)
    channel_override_flag: bool        # True when channel_override differed from preference


# ---------------------------------------------------------------------------
# Template variable namespace
# ---------------------------------------------------------------------------

MVP_TEMPLATE_VARIABLES = {
    "on_my_way":            ["customer_first_name", "sender_name", "eta", "site_address"],
    "running_late":         ["customer_first_name", "sender_name", "minutes_late"],
    "arrived":              ["customer_first_name", "sender_name"],
    "job_complete":         ["customer_first_name", "sender_name"],
    "parts_delay":          ["customer_first_name", "sender_name"],
    "confirm_appointment":  ["customer_first_name", "date_time", "site_address"],
}


# ---------------------------------------------------------------------------
# Core render function — called by both preview (A23) and send (A4) paths
# ---------------------------------------------------------------------------

def render_communication_preview(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    template_code: str,
    variables: Dict[str, Any],
    channel_override: str | None = None,
    sender_name: str | None = None,
) -> CommunicationPreviewResult:
    """
    Render a communication template with the given variables.

    Pure function — no writes, no side effects.
    Called identically by the preview endpoint (A23) and the send endpoint (A4).

    Args:
        db:               Database session.
        tenant_id:        Tenant scope for template lookup.
        customer_id:      Customer whose contact details drive recipient resolution.
        template_code:    One of the 6 MVP template codes.
        variables:        Caller-supplied substitution variables (eta, minutes_late, etc.).
        channel_override: Optional explicit channel ('sms' | 'email'); overrides customer preference.
        sender_name:      Sender's display name for template {sender_name} variable.

    Returns:
        CommunicationPreviewResult with rendered content and metadata.

    Raises:
        ValueError: If template not found or customer contact info missing for channel.
        HTTPException(422): Propagated from template renderer on bad template syntax.
    """
    # 1. Resolve customer and preferred channel
    customer = db.exec(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == tenant_id)
    ).first()
    if not customer:
        raise ValueError(f"Customer {customer_id} not found in tenant {tenant_id}")

    preferred_channel = customer.preferred_contact_channel  # 'sms' | 'email'
    actual_channel = channel_override if channel_override else preferred_channel
    channel_override_flag = bool(
        channel_override and channel_override != preferred_channel
    )

    # 2. Resolve recipient address
    if actual_channel == "sms":
        recipient_address = customer.mobile_phone
        if not recipient_address:
            raise ValueError(
                f"Customer {customer_id} has no mobile_phone — cannot send SMS"
            )
    else:
        recipient_address = str(customer.email) if customer.email else None
        if not recipient_address:
            raise ValueError(
                f"Customer {customer_id} has no email — cannot send email"
            )

    # 3. Resolve template (tenant-specific override first; system fallback)
    template = _resolve_template(db, tenant_id, template_code, actual_channel)

    # 4. Build full variable context
    ctx = {
        "customer_name":       customer.display_name,
        "customer_first_name": customer.first_name or customer.display_name,
        "site_address":        variables.get("site_address", ""),
        "eta":                 variables.get("eta", ""),
        "minutes_late":        variables.get("minutes_late", ""),
        "date_time":           variables.get("date_time", ""),
        "sender_name":         sender_name or "",
    }
    ctx.update(variables)  # caller values override defaults

    # 5. Render
    rendered_body = render_template(template.body_template, ctx)
    rendered_subject = render_subject(template.subject, ctx) if template.subject else None

    # 6. Build editable variable list for preview UI
    var_names = MVP_TEMPLATE_VARIABLES.get(template_code, [])
    editable_vars = [
        EditableVariable(
            name=v,
            current_value=str(ctx.get(v)) if ctx.get(v) else None,
            description=_variable_description(v),
        )
        for v in var_names
        if v not in ("customer_first_name", "sender_name", "customer_name")
    ]

    return CommunicationPreviewResult(
        rendered_body=rendered_body,
        rendered_subject=rendered_subject,
        recipient_name=customer.display_name,
        recipient_address=recipient_address,
        actual_channel=actual_channel,
        editable_variables=editable_vars,
        template_id=template.id,
        customer_preferred_channel=preferred_channel,
        channel_override_flag=channel_override_flag,
    )


def _resolve_template(
    db: Session,
    tenant_id: UUID,
    template_code: str,
    channel: str,
) -> "CommunicationTemplate":
    """
    Tenant-specific template first; fall back to system template (tenant_id IS NULL).

    Raises ValueError if no template found.
    """
    # Tier 1: tenant-specific
    template = db.exec(
        select(CommunicationTemplate)
        .where(CommunicationTemplate.tenant_id == tenant_id)
        .where(CommunicationTemplate.template_code == template_code)
        .where(CommunicationTemplate.channel == channel)
        .where(CommunicationTemplate.is_active == True)
    ).first()

    if template:
        return template

    # Tier 2: system-level
    template = db.exec(
        select(CommunicationTemplate)
        .where(CommunicationTemplate.tenant_id == None)
        .where(CommunicationTemplate.template_code == template_code)
        .where(CommunicationTemplate.channel == channel)
        .where(CommunicationTemplate.is_active == True)
    ).first()

    if not template:
        raise ValueError(
            f"No active template found for code='{template_code}' channel='{channel}'"
        )
    return template


def _variable_description(var_name: str) -> str:
    """Human-readable description for the preview UI editable_variables list."""
    descriptions = {
        "eta":          "Estimated arrival time",
        "minutes_late": "Minutes behind schedule",
        "date_time":    "Appointment date and time",
        "site_address": "Job site address",
    }
    return descriptions.get(var_name, var_name)
```

**File path**: `backend/services/customer_comms_service.py`

### E.2 `app/models/communications.py` — New file (B4)

```python
# backend/app/models/communications.py
"""
Customer Communications models — B4

CommunicationTemplate: lookup table for 6 MVP templates.
CustomerCommunication:  durable send log; one row per dispatched message.

Import path: from app.models.communications import CommunicationTemplate, CustomerCommunication
"""

import uuid
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import StandardAuditMixin


class CommunicationTemplate(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "communication_template"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('sms', 'email')",
            name="communication_template_channel_chk",
        ),
        CheckConstraint(
            "template_code IN ('on_my_way','running_late','arrived','job_complete','parts_delay','confirm_appointment')",
            name="communication_template_code_chk",
        ),
        CheckConstraint(
            "channel <> 'email' OR subject IS NOT NULL",
            name="communication_template_email_subject_chk",
        ),
        Index("idx_communication_template_tenant_id", "tenant_id"),
        Index("idx_communication_template_code_channel", "template_code", "channel"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=True, index=False),
    )
    template_code: str = Field(nullable=False)
    channel: str = Field(nullable=False)
    subject: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    body_template: str = Field(sa_column=Column(Text, nullable=False))
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    created_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class CustomerCommunication(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "customer_communication"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('sms', 'email')",
            name="customer_communication_channel_chk",
        ),
        CheckConstraint(
            "actual_channel IN ('sms', 'email')",
            name="customer_communication_actual_channel_chk",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'canceled')",
            name="customer_communication_status_chk",
        ),
        CheckConstraint(
            "template_code IN ('on_my_way','running_late','arrived','job_complete','parts_delay','confirm_appointment')",
            name="customer_communication_template_code_chk",
        ),
        Index("idx_customer_communication_tenant_id", "tenant_id"),
        Index("idx_customer_communication_customer_id", "customer_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    tenant_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False)
    )
    customer_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("customer.id", ondelete="RESTRICT"), nullable=False, index=True)
    )
    job_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("job.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    sender_user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"), nullable=False)
    )

    template_code: str = Field(nullable=False)
    template_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("communication_template.id", ondelete="SET NULL"), nullable=True),
    )

    rendered_subject: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    rendered_message: str = Field(sa_column=Column(Text, nullable=False))

    # Channel fields (A4 base + A21 override audit)
    channel: str = Field(nullable=False)
    customer_preferred_channel: Optional[str] = Field(
        default=None, sa_column=Column(String(10), nullable=True)
    )
    actual_channel: str = Field(nullable=False)
    channel_override_flag: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # Delivery tracking
    status: str = Field(
        default="pending",
        sa_column=Column(String, server_default=text("'pending'"), nullable=False),
    )
    sent_at: Optional[Any] = Field(default=None)
    notification_outbox_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("notification_outbox.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    variables_json: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    created_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
```

**File path**: `backend/app/models/communications.py`

Register both models in `backend/app/models/__init__.py` alongside existing imports.

---

## F. OPEN QUESTIONS RESOLVED

### F.1 Does `customer.preferred_contact_channel` already exist?

**Question**: The ledger (A21) says "confirm that the `customer` table has a `preferred_contact_channel` field." Does it?

**Resolution**: **NO.** Live MCP query on `customer` returned 19 columns; `preferred_contact_channel` is not among them. Migration 2 (`phase_fe_1_batch_b4_customer_preferred_channel`) adds it as `VARCHAR(10) NOT NULL DEFAULT 'sms'`.

---

### F.2 Do `communication_template` or `customer_communication` already exist?

**Question**: Are either of these tables pre-existing in the live DB?

**Resolution**: **NO.** MCP query for both table names in `information_schema.columns` returned zero rows. Migration 1 creates both from scratch.

---

### F.3 Does `notification_outbox.channel` support `'sms'`?

**Question**: Can B4 route SMS through `notification_outbox` or does it need a custom dispatch path?

**Resolution**: **YES.** Live DB confirms `CHECK (channel IN ('email','sms','in_app'))`. SMS is already in the enum. B4 writes `channel='sms'` outbox entries; the existing `poll_pending_notifications` worker handles dispatch via `services/sms_service.py` (the current Twilio implementation). B11/A59 will later swap `sms_service.py` for the carrier-agnostic adapter.

---

### F.4 Template variable namespace — conflict with A27 (B1)?

**Question**: Impl plan says "namespace must align with A27's quote template variable namespace (defined in B1). Cross-reference before finalizing."

**Resolution**: B1/A27 covers quote templates; its variables are `{customer_name}`, `{quote_number}`, `{quote_total}`, `{tech_name}`, `{company_name}`, `{expiry_date}`. B4's variables are `{customer_name}`, `{customer_first_name}`, `{eta}`, `{minutes_late}`, `{date_time}`, `{site_address}`, `{sender_name}`. **No conflicts** — the namespaces are disjoint except for `{customer_name}` which has identical semantics in both contexts. The B4 namespace can be finalized as specified.

---

### F.5 How does A4's send endpoint create a `NotificationOutbox` entry?

**Question**: `NotificationOutbox` requires a `notification_event_id` FK (NOT NULL). What `NotificationType` code should be used?

**Resolution**: Follow the pattern in `quickbooks_sync.py` and `scheduling.py`:
1. Create `NotificationEvent` with `notification_type_code="customer_communication_sent"`. If this type code does not exist in `notification_type`, it must be seeded in the migration alongside the template data.
2. Create `NotificationOutbox` referencing the event, with `channel=actual_channel`, `to_address=customer.mobile_phone` (SMS) or `str(customer.email)` (email), and `body=rendered_message`.
3. Link `CustomerCommunication.notification_outbox_id` to the new outbox row.

**Decision**: Add `"customer_communication_sent"` to `notification_type` seed data in Migration 1's data block.

---

### F.6 Opt-out / STOP keyword enforcement for SMS

**Question**: The MVP SMS templates include "Reply STOP to opt out." Who enforces the STOP?

**Resolution**: B4 **does not** implement STOP enforcement. The current `sms_service.py` (Twilio) handles inbound STOP at the Twilio platform level. B11/A59 migrates to Telnyx and implements full opt-in/opt-out tracking (TCPA). For B4, the STOP footer in templates is advisory. This is explicitly deferred to B11. **No blocking issue for B4.**

---

### F.7 Channel fallback when customer has no mobile_phone for SMS

**Question**: What happens if `customer.preferred_contact_channel = 'sms'` but `customer.mobile_phone IS NULL`?

**Resolution**: `render_communication_preview()` raises `ValueError("Customer has no mobile_phone — cannot send SMS")`. The send endpoint returns `422 Unprocessable Entity` with a clear message. The preview endpoint returns the same error shape. Callers (web UI and voice handler) must surface this to the user: "This customer has no phone number on file. Update the customer record or use email."

---

### F.8 What `communications.send` permission is needed and for which roles?

**Question**: No `communications.send` permission exists in the current role system. Which roles need it?

**Resolution**: New permission string: `"communications.send"`. Must be added to the role definitions:
- `owner` role: already has `"*"` wildcard — no change needed
- `technician` role: add `"communications.send"` — primary users of voice comms
- `office_staff` role: add `"communications.send"` — dispatchers sending comms from web

Add this to the role seed migration as part of Migration 1 data block.

---

### F.9 Voice customer resolution — what if no customer in context and no name in utterance?

**Question**: A22 requires a customer resolution priority chain. What's the response when neither context nor name is available?

**Resolution**: Return a clarification response — do NOT write `pending_confirmation`:
```python
return {
    "action": "tell_customer",
    "success": False,
    "message": "Who would you like to message? Please say the customer's name.",
    "next_prompts": ["Tell Johnson I'm 20 out", "Tell the Davis customer I arrived"],
}
```
This is a non-destructive clarification prompt; confirm-as-turn does not apply until a customer is identified.

---

## G. EXTERNAL DEPENDENCY STATUS

### G.1 SMS Delivery — `sms_service.py` (Twilio)

**Item**: A4 send endpoint writes to `notification_outbox` channel `'sms'`. The existing `poll_pending_notifications` Celery task delivers via `services/sms_service.py` (Twilio).

**B4 mock strategy**: `MockNotificationWorker` — in tests, use `unittest.mock.patch` on the `poll_pending_notifications` task or inject a mock `sms_service.send_sms()`. Tests verify the `CustomerCommunication` row is created with `status='pending'` and a matching `NotificationOutbox` row; they do not test actual SMS delivery.

**Production action**: None required for B4. Twilio is already configured. B11/A59 will replace `sms_service.py` with the carrier-agnostic adapter (§22 of python-engineer-methods); B4 is forward-compatible because B11 replaces the dispatch layer, not the `notification_outbox` write path.

**Lead time**: None for B4 (Twilio already active). Telnyx migration (B11) requires 10DLC registration — see B11 design doc.

---

### G.2 Email Delivery — `email_service.py` (SendGrid)

**Item**: A4 send endpoint may dispatch `channel='email'` via `notification_outbox`. The `poll_pending_notifications` worker handles email via `services/email_service.py`.

**B4 mock strategy**: Same as SMS — mock `email_service.send_email()` in tests. Email templates are SMS-first in B4 (`on_my_way` email variant is the only one seeded for B4; others are post-MVP).

**Production action**: None required. SendGrid is already configured and operational.

---

### G.3 Ollama (LLaMA 3.1:8b) — Voice Intent Classification

**Item**: A22 voice grammar requires Ollama to extract variables from utterances ("I'm 20 out" → `eta = now + 20 minutes`). System prompt engineering for the new voice intents (time extraction, customer name extraction) is part of A22 scope.

**B4 mock strategy**: Unit tests for A22 handlers mock `execute_action()` with pre-parsed `entities` dicts. Integration tests for the full voice pipeline use the running Ollama instance (GPU server). Voice pipeline tests are tagged `@pytest.mark.voice` and can run against a local Ollama container for CI.

**Production action**: No new model required. `llama3.1:8b` already loaded on the GPU instance. Prompt engineering work is developer time only.

---

### G.4 No Stripe / Telnyx / 10DLC / OpenAI Required in B4

B4 is self-contained: it writes to `notification_outbox` (existing infrastructure), renders templates via Jinja2 (existing `template_renderer.py`), and dispatches via existing Twilio + SendGrid workers. No new external accounts, credentials, or carrier registrations are required for B4.

**Future dependency note**: B11 (SMS/Telnyx stack) gates on B4's `customer_communication` table. Telnyx provisioning + 10DLC registration for B11 should begin **concurrently with B4 implementation** (estimated 3–6 week 10DLC approval lead time). Tom must action this independently of B4's delivery date.
