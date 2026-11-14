# Batch B11 Design Document — SMS / Telnyx Stack

**Batch**: B11  
**Prerequisites**: B4 (customer_communication + communication_template tables), B10 (notification_category registry + billing category)  
**Gates**: None  
**Estimated Effort**: 23–28 days  
**Items**: A59, A61, A60, A65, A62, A64, A66, A63  
**Test subfolder**: `tests/batch_b11/`  
**Design Date**: 2026-05-02  
**Status**: Ready for implementation

---

## A. MIGRATION PLAN

### Pre-Migration MCP Verification Summary

All six new B11 tables were confirmed absent from the live database:

| Table | Status |
|:------|:-------|
| `customer_communication_thread` | ✅ Absent — create |
| `customer_communication_message` | ✅ Absent — create |
| `customer_communication_unrouted` | ✅ Absent — create |
| `customer_communication_message_read_state` | ✅ Absent — create |
| `tenant_phone_number` | ✅ Absent — create |
| `sms_quota_period` | ✅ Absent — create |

All five TCPA columns on `customer` were confirmed absent from the live database (confirmed columns: `id`, `tenant_id`, `type`, `display_name`, `first_name`, `last_name`, `company_name`, `dba_name`, `email`, `mobile_phone`, `preferred_contact_channel`, `locale`, `timezone`, `notes`, `is_active`, `lifecycle_status_id`, `created_by`, `updated_by`, `created_at`, `updated_at`).

**Schema resolution for `voice_audio_id` FK**: `voice_command_log.id` is `BIGINT` (confirmed via MCP). The additions ledger spec says `UUID NULL REFERENCES voice_command_log` — this is incorrect. The correct type is `BIGINT NULL` with FK to `voice_command_log(id)`. See §F for the resolved decision.

---

### Migration 1 — `phase_fe_1_batch_b11_tcpa_customer_columns`

Adds 5 TCPA compliance columns to the existing `customer` table.

```sql
-- upgrade()
ALTER TABLE customer ADD COLUMN sms_opted_out       BOOLEAN     NOT NULL DEFAULT FALSE;
ALTER TABLE customer ADD COLUMN sms_opt_out_at      TIMESTAMPTZ NULL;
ALTER TABLE customer ADD COLUMN sms_opt_in_consent  BOOLEAN     NOT NULL DEFAULT FALSE;
ALTER TABLE customer ADD COLUMN sms_opt_in_at       TIMESTAMPTZ NULL;
ALTER TABLE customer ADD COLUMN sms_opt_in_source   TEXT        NULL;
    -- CHECK: sms_opt_in_source IN ('explicit_checkbox', 'inbound_initiated', 'verbal_captured')

ALTER TABLE customer ADD CONSTRAINT customer_sms_opt_in_source_chk
    CHECK (sms_opt_in_source IS NULL OR
           sms_opt_in_source IN ('explicit_checkbox', 'inbound_initiated', 'verbal_captured'));

-- downgrade()
ALTER TABLE customer DROP COLUMN sms_opted_out;
ALTER TABLE customer DROP COLUMN sms_opt_out_at;
ALTER TABLE customer DROP COLUMN sms_opt_in_consent;
ALTER TABLE customer DROP COLUMN sms_opt_in_at;
ALTER TABLE customer DROP COLUMN sms_opt_in_source;
```

**No indexes required** — TCPA opt-out status is always fetched via the customer row already being loaded.

---

### Migration 2 — `phase_fe_1_batch_b11_tenant_phone_number`

Creates the `tenant_phone_number` table required before threading tables (FK dependency).

```sql
-- upgrade()
CREATE TABLE tenant_phone_number (
    id                       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                UUID        NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
    phone_number             TEXT        NOT NULL,   -- E.164 format, e.g. +15125550001
    area_code                TEXT        NOT NULL,
    carrier                  TEXT        NOT NULL DEFAULT 'telnyx',
    carrier_provisioning_id  TEXT        NULL,       -- Telnyx's reference for the provisioned number
    monthly_fee_cents        INTEGER     NOT NULL DEFAULT 100,
    status                   TEXT        NOT NULL DEFAULT 'active',
    provisioned_at           TIMESTAMPTZ NULL,
    released_at              TIMESTAMPTZ NULL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by               UUID        NULL REFERENCES "user"(id) ON DELETE RESTRICT,
    updated_by               UUID        NULL REFERENCES "user"(id) ON DELETE RESTRICT,
    CONSTRAINT tenant_phone_number_status_chk
        CHECK (status IN ('active', 'released', 'provisioning_failed')),
    CONSTRAINT tenant_phone_number_carrier_chk
        CHECK (carrier IN ('telnyx'))
);

CREATE UNIQUE INDEX uq_tenant_phone_number_active
    ON tenant_phone_number(tenant_id)
    WHERE status = 'active';

CREATE INDEX idx_tenant_phone_number_tenant_id ON tenant_phone_number(tenant_id);
CREATE INDEX idx_tenant_phone_number_phone     ON tenant_phone_number(phone_number);

-- downgrade()
DROP TABLE tenant_phone_number;
```

---

### Migration 3 — `phase_fe_1_batch_b11_communication_threading`

Creates `customer_communication_thread`, `customer_communication_message`, and `customer_communication_unrouted`. Depends on Migration 2 (`tenant_phone_number` must exist before thread FK).

```sql
-- upgrade()
CREATE TABLE customer_communication_thread (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
    customer_id             UUID        NOT NULL REFERENCES customer(id) ON DELETE RESTRICT,
    tech_id                 UUID        NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
    tenant_phone_number_id  UUID        NOT NULL REFERENCES tenant_phone_number(id) ON DELETE RESTRICT,
    status                  TEXT        NOT NULL DEFAULT 'active',
    first_message_at        TIMESTAMPTZ NOT NULL,
    last_message_at         TIMESTAMPTZ NOT NULL,
    message_count           INTEGER     NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              UUID        NULL REFERENCES "user"(id) ON DELETE RESTRICT,
    updated_by              UUID        NULL REFERENCES "user"(id) ON DELETE RESTRICT,
    CONSTRAINT customer_communication_thread_status_chk
        CHECK (status IN ('active', 'archived'))
);

-- Routing key index: the 4-tuple that defines a unique thread
CREATE UNIQUE INDEX uq_comm_thread_routing_key
    ON customer_communication_thread(tenant_id, customer_id, tech_id, tenant_phone_number_id)
    WHERE status = 'active';

CREATE INDEX idx_comm_thread_tenant_id  ON customer_communication_thread(tenant_id);
CREATE INDEX idx_comm_thread_customer_id ON customer_communication_thread(customer_id);
CREATE INDEX idx_comm_thread_tech_id    ON customer_communication_thread(tech_id);
CREATE INDEX idx_comm_thread_last_msg   ON customer_communication_thread(tenant_id, last_message_at DESC);


CREATE TABLE customer_communication_message (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id           UUID        NOT NULL REFERENCES customer_communication_thread(id) ON DELETE RESTRICT,
    direction           TEXT        NOT NULL,   -- 'outbound' | 'inbound'
    channel             TEXT        NOT NULL DEFAULT 'sms',
    body                TEXT        NOT NULL,
    segment_count       INTEGER     NOT NULL DEFAULT 1,
    status              TEXT        NOT NULL DEFAULT 'pending_send',
    carrier_message_id  TEXT        NULL,
    sent_at             TIMESTAMPTZ NULL,
    delivered_at        TIMESTAMPTZ NULL,
    received_at         TIMESTAMPTZ NULL,
    composition_method  TEXT        NULL,       -- 'template' | 'free_form_text' | 'free_form_voice'
    template_id         UUID        NULL REFERENCES communication_template(id) ON DELETE SET NULL,
    -- voice_audio_id references voice_command_log.id which is BIGINT (confirmed via MCP)
    voice_audio_id      BIGINT      NULL REFERENCES voice_command_log(id) ON DELETE SET NULL,
    audit_user_id       UUID        NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT customer_communication_message_direction_chk
        CHECK (direction IN ('outbound', 'inbound')),
    CONSTRAINT customer_communication_message_channel_chk
        CHECK (channel IN ('sms')),
    CONSTRAINT customer_communication_message_status_chk
        CHECK (status IN ('pending_send', 'sent', 'delivered', 'failed', 'received')),
    CONSTRAINT customer_communication_message_composition_method_chk
        CHECK (composition_method IS NULL OR
               composition_method IN ('template', 'free_form_text', 'free_form_voice'))
);

CREATE INDEX idx_comm_message_thread_id  ON customer_communication_message(thread_id);
CREATE INDEX idx_comm_message_status     ON customer_communication_message(thread_id, status);
CREATE INDEX idx_comm_message_direction  ON customer_communication_message(thread_id, direction, received_at DESC);


CREATE TABLE customer_communication_unrouted (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID        NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
    from_number         TEXT        NOT NULL,   -- E.164
    to_number           TEXT        NOT NULL,   -- E.164 — the tenant_phone_number that received it
    body                TEXT        NOT NULL,
    carrier_message_id  TEXT        NULL,
    received_at         TIMESTAMPTZ NOT NULL,
    parked_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at         TIMESTAMPTZ NULL,
    resolved_by         UUID        NULL REFERENCES "user"(id) ON DELETE SET NULL,
    resolved_thread_id  UUID        NULL REFERENCES customer_communication_thread(id) ON DELETE SET NULL,
    status              TEXT        NOT NULL DEFAULT 'parked',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT customer_communication_unrouted_status_chk
        CHECK (status IN ('parked', 'assigned', 'dismissed'))
);

CREATE INDEX idx_comm_unrouted_tenant_id ON customer_communication_unrouted(tenant_id, status);
CREATE INDEX idx_comm_unrouted_parked_at ON customer_communication_unrouted(tenant_id, parked_at DESC);

-- downgrade()
DROP TABLE customer_communication_unrouted;
DROP TABLE customer_communication_message;
DROP TABLE customer_communication_thread;
```

---

### Migration 4 — `phase_fe_1_batch_b11_sms_quota_period`

Creates the `sms_quota_period` table. Independent of threading tables; depends only on `tenant`.

```sql
-- upgrade()
CREATE TABLE sms_quota_period (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID        NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
    period_start      TIMESTAMPTZ NOT NULL,
    period_end        TIMESTAMPTZ NOT NULL,
    included_segments INTEGER     NOT NULL DEFAULT 100,
    used_segments     INTEGER     NOT NULL DEFAULT 0,
    overage_segments  INTEGER     GENERATED ALWAYS AS (GREATEST(0, used_segments - included_segments)) STORED,
    cap_policy        TEXT        NOT NULL DEFAULT 'soft',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT sms_quota_period_cap_policy_chk
        CHECK (cap_policy IN ('soft', 'hard')),
    CONSTRAINT sms_quota_period_no_overlap
        EXCLUDE USING gist (
            tenant_id WITH =,
            tstzrange(period_start, period_end) WITH &&
        )
);

CREATE INDEX idx_sms_quota_period_tenant_active
    ON sms_quota_period(tenant_id, period_start DESC);

-- downgrade()
DROP TABLE sms_quota_period;
```

**Note on `overage_segments`**: using a `GENERATED ALWAYS AS … STORED` computed column avoids a separate counter and guarantees consistency. If the PostgreSQL version in use does not support generated columns on `TIMESTAMPTZ`, fall back to a regular `INTEGER` column updated in the same atomic transaction as `used_segments`.

---

### Migration 5 — `phase_fe_1_batch_b11_message_read_state`

Creates `customer_communication_message_read_state`. Depends on Migration 3 (messages must exist).

```sql
-- upgrade()
CREATE TABLE customer_communication_message_read_state (
    message_id  UUID        NOT NULL REFERENCES customer_communication_message(id) ON DELETE CASCADE,
    user_id     UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    read_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (message_id, user_id)
);

CREATE INDEX idx_msg_read_state_user
    ON customer_communication_message_read_state(user_id, message_id);

-- downgrade()
DROP TABLE customer_communication_message_read_state;
```

---

### Migration 6 — `phase_fe_1_batch_b11_sms_quota_cap_policy_setting`

Inserts the `sms_quota_cap_policy` setting catalog entry and the `billing` sub-trigger IDs needed by A65 quota notifications. Uses existing `notification_category` (`category_id='billing'` confirmed live).

```sql
-- upgrade()
-- Register sms_quota_cap_policy in settings catalog (B9/A52 settings_catalog table)
INSERT INTO settings_catalog (key, scope, value_type, default_value, allow_user_override, description)
VALUES (
    'sms_quota_cap_policy',
    'tenant',
    'enum',
    'soft',
    FALSE,
    'Controls SMS overage behavior: soft = send + bill overage at $0.05/segment; hard = block sends at 100% quota'
)
ON CONFLICT (key) DO NOTHING;

-- downgrade()
DELETE FROM settings_catalog WHERE key = 'sms_quota_cap_policy';
```

**Note**: This migration will fail silently on conflict (`ON CONFLICT DO NOTHING`) if B9's settings_catalog table already has this entry — safe to run multiple times.

---

### Summary Table

| Migration | Name | Logical Unit | Depends On |
|:---|:---|:---|:---|
| 1 | `phase_fe_1_batch_b11_tcpa_customer_columns` | TCPA opt-in/opt-out columns on `customer` | None |
| 2 | `phase_fe_1_batch_b11_tenant_phone_number` | New `tenant_phone_number` table | None |
| 3 | `phase_fe_1_batch_b11_communication_threading` | `customer_communication_thread`, `customer_communication_message`, `customer_communication_unrouted` | Migration 2 |
| 4 | `phase_fe_1_batch_b11_sms_quota_period` | `sms_quota_period` table | None |
| 5 | `phase_fe_1_batch_b11_message_read_state` | `customer_communication_message_read_state` table | Migration 3 |
| 6 | `phase_fe_1_batch_b11_sms_quota_cap_policy_setting` | Settings catalog entry for `sms_quota_cap_policy` | B9 settings_catalog |

---

## B. EXECUTION ORDER

| # | Item | One-Line Rationale |
|:---|:---|:---|
| 1 | **A59** — Telnyx Webhook Handler + Carrier-Agnostic Adapter | Foundation layer — `SmsCarrier` ABC, `TelnyxSmsCarrier`, `MockSmsCarrier`, `GET /api/v1/webhooks/sms/telnyx-inbound`, TCPA opt-out handler, 5 customer schema columns. All subsequent B11 items call through `get_sms_carrier()`. |
| 2 | **A61** — Telnyx Number Provisioning | Depends on A59 (`TelnyxSmsCarrier.provision_number()` must exist); creates `tenant_phone_number` table; `services/sms_provisioning.py`; provisioning endpoints. A60 threading schema has a FK to `tenant_phone_number`. |
| 3 | **A60** — Communication Threading Schema + Routing | Depends on A59 (inbound webhook delivers to threading router) and A61 (`tenant_phone_number_id` FK). Establishes the 3 core threading tables + `services/customer_communication_threading.py::route_inbound_message()`. Includes backfill of existing `customer_communication` rows from B4. |
| 4 | **A65** — SMS Quota Tracking + Cap Enforcement | Depends on A61 (quota period tied to provisioned number) and A60 (segment count tracked per message). Establishes `sms_quota_period` + `services/sms_quota.py::check_quota()` / `consume_quota()`. A62 (reply) calls quota check; must exist first. |
| 5 | **A62** — Free-Form Reply Composition Endpoint | Depends on A60 (thread must exist), A61 (number provisioned), A65 (quota check before send). Adds `POST /api/v1/communications/threads/{thread_id}/reply` with staleness check + SSE. |
| 6 | **A64** — Owner Visibility Surfaces | Depends on A60 (threaded messages must exist). Extends existing `GET /api/v1/customers/{id}/communication-history` + adds `GET /api/v1/dashboard/widgets/recent-customer-messages`. Read-only; no write dependency on A62. |
| 7 | **A66** — Mobile Inbox + Conversation Thread Screen | Depends on A60 (thread/message data), A65 (quota context in responses). Adds read-state table + mobile inbox endpoints. Does not depend on A62's reply path being live. |
| 8 | **A63** — Voice-to-Text Reply Integration | Must be last: calls A62's reply endpoint on confirmation. Depends on B2/A12 confirm-as-turn infrastructure (voice_action_router.py) being live from B2. |

---

## C. NEW API ENDPOINTS

### A59 Endpoints

#### `POST /api/v1/webhooks/sms/telnyx-inbound`
- **Auth**: Public (no JWT — webhook receiver from Telnyx infrastructure)  
- **RBAC**: None  
- **Route file**: `backend/api/routes/webhooks_sms.py` (new file)  
- **Request body**: Raw bytes (application/json from Telnyx); verified via `SmsCarrier.verify_webhook_signature(payload_bytes, signature_header)`
- **Processing**:
  1. Verify signature — 401 on failure (Telnyx retries)
  2. `parse_inbound_webhook()` → `InboundMessage`
  3. TCPA check: exact-match body against STOP keywords → `handle_sms_opt_out()` OR opt-in keywords → re-opt-in flow
  4. Otherwise → `route_inbound_message(inbound)` → thread match or unrouted queue
- **Response**: `{"status": "received"}` (200 always to Telnyx after signature valid)
- **Response on signature fail**: 401

---

### A61 Endpoints

#### `POST /api/v1/tenants/{tenant_id}/phone-numbers/provision`
- **Auth**: JWT required  
- **RBAC**: `require_permission("settings.manage")`  
- **Route file**: `backend/api/routes/tenant_phone_numbers.py` (new file)  
- **Request body**:
  ```json
  { "area_code": "512" }
  ```
- **Response 200**:
  ```json
  {
    "phone_number_id": "uuid",
    "phone_number": "+15125550001",
    "area_code": "512",
    "carrier": "telnyx",
    "status": "active",
    "monthly_fee_cents": 100,
    "provisioned_at": "2026-05-02T16:00:00Z"
  }
  ```
- **Response 409**: Tenant already has an active provisioned number

#### `GET /api/v1/tenants/{tenant_id}/phone-numbers`
- **Auth**: JWT required  
- **RBAC**: `require_permission("settings.view")`  
- **Route file**: `backend/api/routes/tenant_phone_numbers.py`  
- **Response 200**:
  ```json
  {
    "numbers": [
      {
        "phone_number_id": "uuid",
        "phone_number": "+15125550001",
        "status": "active",
        "provisioned_at": "2026-05-02T16:00:00Z",
        "monthly_fee_cents": 100
      }
    ]
  }
  ```

---

### A60 Endpoints

#### `GET /api/v1/communications/unrouted`
- **Auth**: JWT required  
- **RBAC**: `require_permission("communications.manage")` (owner-only)  
- **Route file**: `backend/api/routes/communications_threads.py` (new file)  
- **Query params**: `status=parked` (default), `limit=20`, `before=<cursor_timestamp>`  
- **Response 200**:
  ```json
  {
    "items": [
      {
        "id": "uuid",
        "from_number": "+15125551234",
        "body": "Is anyone available tomorrow?",
        "received_at": "2026-05-02T14:00:00Z",
        "status": "parked"
      }
    ],
    "next_cursor": "2026-05-02T13:00:00Z"
  }
  ```

#### `POST /api/v1/communications/unrouted/{id}/assign-to-thread`
- **Auth**: JWT required  
- **RBAC**: `require_permission("communications.manage")`  
- **Route file**: `backend/api/routes/communications_threads.py`  
- **Request body**:
  ```json
  { "thread_id": "uuid" }
  ```
- **Response 200**: Updated unrouted record with `status: "assigned"`, `resolved_thread_id`

---

### A65 Endpoints

#### `GET /api/v1/sms/quota`
- **Auth**: JWT required  
- **RBAC**: `require_permission("settings.view")`  
- **Route file**: `backend/api/routes/sms_quota.py` (new file)  
- **Response 200**:
  ```json
  {
    "period_start": "2026-05-01T00:00:00Z",
    "period_end": "2026-05-31T23:59:59Z",
    "included_segments": 100,
    "used_segments": 73,
    "overage_segments": 0,
    "remaining_segments": 27,
    "cap_policy": "soft",
    "projected_month_end_segments": 95
  }
  ```

---

### A62 Endpoints

#### `POST /api/v1/communications/threads/{thread_id}/reply`
- **Auth**: JWT required  
- **RBAC**: `require_permission("communications.send")`  
- **Route file**: `backend/api/routes/communications_threads.py`  
- **Request body**:
  ```json
  {
    "body": "I'm on my way, should be there in 20 minutes.",
    "composition_method": "free_form_text",
    "voice_audio_id": null,
    "expected_updated_at": "2026-05-02T14:30:00Z"
  }
  ```
  - `body`: max 1600 chars; non-empty
  - `composition_method`: `"free_form_text" | "free_form_voice"`
  - `voice_audio_id`: BIGINT if `composition_method = "free_form_voice"`; nullable otherwise
  - `expected_updated_at`: optional; triggers staleness check on thread via `assert_not_stale()`
- **Response 200**:
  ```json
  {
    "message_id": "uuid",
    "thread_id": "uuid",
    "direction": "outbound",
    "body": "I'm on my way, should be there in 20 minutes.",
    "segment_count": 1,
    "status": "sent",
    "carrier_message_id": "telnyx-msg-abc123",
    "sent_at": "2026-05-02T14:31:00Z",
    "quota": {
      "used_segments": 74,
      "remaining_segments": 26,
      "overage": false
    }
  }
  ```
- **Response 402**: Hard cap reached — `{"blocked_reason": "monthly_quota_reached"}`
- **Response 403**: Customer opted out — `{"blocked_reason": "customer_opted_out"}`
- **Response 409**: Staleness conflict — thread updated since client read; includes refreshed thread payload

---

### A64 Endpoints

#### `GET /api/v1/customers/{customer_id}/communication-history` (extended from B4)
- **Auth**: JWT required  
- **RBAC**: `require_permission("customers.view")`  
- **Route file**: `backend/api/routes/communications.py` (existing — extend)  
- **Change**: Return threaded message list grouped by `thread_id`; two-direction rendering support; multiple threads per customer when multiple techs have communicated  
- **Response 200** (extended):
  ```json
  {
    "threads": [
      {
        "thread_id": "uuid",
        "tech_id": "uuid",
        "tech_name": "Luis M.",
        "status": "active",
        "first_message_at": "2026-04-28T09:00:00Z",
        "last_message_at": "2026-05-02T14:31:00Z",
        "message_count": 5,
        "messages": [
          {
            "message_id": "uuid",
            "direction": "outbound",
            "body": "I'm on my way.",
            "sent_at": "2026-05-02T14:31:00Z",
            "segment_count": 1,
            "status": "delivered"
          }
        ]
      }
    ],
    "legacy_communications": []
  }
  ```

#### `GET /api/v1/dashboard/widgets/recent-customer-messages`
- **Auth**: JWT required  
- **RBAC**: `require_permission("communications.view")`  
- **Route file**: `backend/api/routes/dashboard.py` (existing — add endpoint)  
- **Query params**: `limit=10` (max 50)  
- **Response 200**:
  ```json
  {
    "messages": [
      {
        "thread_id": "uuid",
        "customer_id": "uuid",
        "customer_name": "Johnson Electric",
        "tech_id": "uuid",
        "tech_name": "Luis M.",
        "direction": "inbound",
        "body_preview": "Is anyone available tomorrow?",
        "last_message_at": "2026-05-02T13:45:00Z",
        "unread_count": 1
      }
    ]
  }
  ```

---

### A66 Endpoints

#### `GET /api/v1/mobile/inbox/customer-threads`
- **Auth**: JWT required  
- **RBAC**: `require_permission("communications.view")`  
- **Route file**: `backend/api/routes/communications_threads.py`  
- **Query params**: `limit=5` (default), `before=<cursor_timestamp>` (pagination)  
- **Response 200**:
  ```json
  {
    "threads": [
      {
        "thread_id": "uuid",
        "customer_name": "Davis Electrical",
        "last_message_preview": "Is anyone available tomorrow?",
        "last_message_at": "2026-05-02T13:45:00Z",
        "unread_count": 2,
        "originating_job_context": {
          "job_id": "uuid",
          "job_number": "JOB-0042"
        }
      }
    ],
    "next_cursor": "2026-05-02T10:00:00Z"
  }
  ```

#### `GET /api/v1/communications/threads/{thread_id}/messages`
- **Auth**: JWT required  
- **RBAC**: `require_permission("communications.view")`  
- **Route file**: `backend/api/routes/communications_threads.py`  
- **Query params**: `limit=20`, `before=<cursor_message_id>`  
- **Response 200**: Paginated message list with direction, body, status, timestamps, segment_count

#### `POST /api/v1/communications/threads/{thread_id}/mark-read`
- **Auth**: JWT required  
- **RBAC**: `require_permission("communications.view")`  
- **Route file**: `backend/api/routes/communications_threads.py`  
- **Request body**: `{}` (no body needed — marks all unread messages in thread as read for requesting user)  
- **Response 200**: `{"marked_read_count": 2}`

---

### A63 Endpoints

No new HTTP endpoints. A63 registers a new voice intent `reply_to_customer_sms` in the existing intent registry at `backend/services/voice_action_router.py`. On confirmation the intent calls `POST /api/v1/communications/threads/{thread_id}/reply` (A62) internally.

---

## D. PATTERN REUSE DECISIONS

### §20 — Pre-Commit Staleness Check (`utils/staleness_check.py`)
**Established**: B3/A19  
**Applies to**: A62 (reply endpoint on `customer_communication_thread.updated_at`)

```python
# In POST /api/v1/communications/threads/{thread_id}/reply
from utils.staleness_check import assert_not_stale

thread = db.exec(
    select(CustomerCommunicationThread)
    .where(CustomerCommunicationThread.id == thread_id)
    .where(CustomerCommunicationThread.tenant_id == current_user.tenant_id)
).first()
if not thread:
    raise HTTPException(status_code=404, detail="Thread not found")

assert_not_stale(
    expected_updated_at=payload.expected_updated_at,
    actual_updated_at=thread.updated_at,
    refreshed_payload=ThreadDetailResponse.model_validate(thread).model_dump(),
    entity_label="communication thread",
)
```

The `assert_not_stale()` signature from `backend/utils/staleness_check.py` is: `assert_not_stale(expected_updated_at, actual_updated_at, refreshed_payload, entity_label)`. When `expected_updated_at=None`, check is skipped (opt-out).

---

### §22 — Carrier-Agnostic Adapter (`services/sms_carrier.py`)
**Established**: B11/A59 (first implementation of this pattern)  
**Applies to**: A59 (defines), A61 (provision_number), A62 (send_message), A60 (parse_inbound_webhook, verify_webhook_signature), A65 (send failure rolls back quota)

Full interface from `dev-docs/architecture-design/pilot-python-engineer-methods.md §22`:

```python
# services/sms_carrier.py  — factory function (call this everywhere, never instantiate directly)
def get_sms_carrier() -> SmsCarrier:
    from core.config import settings
    carrier_name = getattr(settings, "SMS_CARRIER", "mock")
    if carrier_name == "telnyx":
        from services.telnyx_sms_carrier import TelnyxSmsCarrier
        return TelnyxSmsCarrier()
    return MockSmsCarrier()
```

`TelnyxSmsCarrier` lives in `backend/services/telnyx_sms_carrier.py` (new file). The ABC and `MockSmsCarrier` live in `backend/services/sms_carrier.py` (new file).

**Anti-pattern guard**: The existing `backend/services/sms_service.py` contains a direct Twilio `Client` instantiation — A59 adds the new carrier module but does NOT delete `sms_service.py` in B11. B4's `customer_comms_service.py` still calls `sms_service.send_sms()` for templated sends. The threading model routes free-form replies through the new carrier; templated sends continue through the existing service until a future cleanup batch.

---

### §19.2 — Telnyx-Specific Webhook Pattern
**Applies to**: A59 webhook handler at `POST /api/v1/webhooks/sms/telnyx-inbound`

Telnyx uses `application/json` (not form-encoded like Twilio) with a public-key signature scheme via their SDK. The `verify_webhook_signature()` method on `TelnyxSmsCarrier` encapsulates the SDK call. Route file `backend/api/routes/webhooks_sms.py` mirrors the structure of the existing `backend/api/routes/webhooks.py` (QB webhook) — raw body capture before `Request.body()` parse, signature verify first, then background task dispatch.

---

### §17.1 — Periodic Poll Celery Task Pattern
**Applies to**: A65's two new Celery tasks

```python
# tasks/monitor_sms_quota_thresholds.py
@celery_app.task(name="monitor_sms_quota_thresholds")
def monitor_sms_quota_thresholds() -> dict:
    """Hourly. Detect 80%/100% threshold crossings; dispatch billing notifications."""

# tasks/rollover_sms_quota_periods.py
@celery_app.task(name="rollover_sms_quota_periods")
def rollover_sms_quota_periods() -> dict:
    """Daily. Create new sms_quota_period rows at subscription billing cycle boundaries."""
```

Both follow the `@celery_app.task(name=...)` + `db: Session = next(get_db())` pattern from §17.1.

---

### §6.6 (mvp-arch.md) — Confirm-as-Turn for Destructive Voice Actions
**Applies to**: A63 (`reply_to_customer_sms` voice intent)

The `reply_to_customer_sms` intent is a one-way-door action (SMS is sent and cannot be recalled). The intent handler must:
1. Extract customer + body
2. Call preview render (read back: "I'll send to [customer]: '[body].' That's [N] segments, [R] remaining. Confirm?")
3. Store pending confirmation in `conversation_session.context_window_json.pending_confirmation`
4. Only invoke A62's `POST /api/v1/communications/threads/{thread_id}/reply` after explicit "yes/confirm" on the next turn

Implementation lives in `backend/services/voice_action_router.py`'s `execute_action()` dispatcher — the new `reply_to_customer_sms` case follows the same pending_confirmation pattern used by `send_quote`, `reassign_job`, etc.

---

### §16.7 (mvp-arch.md) — Always-Preview-Before-Send for One-Way-Door Actions
**Applies to**: A62 (preview computed before dispatching), A63 (voice always renders preview before confirm-as-turn)

The preview for a free-form reply includes segment count + quota remaining — this is not optional. For the voice path (A63), preview is rendered server-side and read back aloud before the confirm-as-turn. The existing `POST /api/v1/communications/preview` endpoint (B4/A23 in `backend/api/routes/communications.py`) handles template preview; A62's reply endpoint performs its own inline preview computation rather than re-routing through the existing preview endpoint (different content type: free-form vs. template).

---

### B10 Notification Category — `billing`
**Applies to**: A65 quota threshold notifications (80% and 100%)

Confirmed live in DB: `notification_category.category_id = 'billing'` (display_order=6). A65's `monitor_sms_quota_thresholds` task dispatches via `notification_outbox` with `category_id = 'billing'`. The `notification_outbox` table (confirmed live) has the `category_id TEXT NOT NULL` column. No new category registration needed.

**Notification sub-trigger IDs** for A65 (inserted via Migration 6 or seed):
- `sms_quota_80_pct` — 80% threshold crossing
- `sms_quota_100_pct_soft` — 100% threshold, soft cap (overage billing info)
- `sms_quota_100_pct_hard` — 100% threshold, hard cap (blocking info)

---

### B4 Coexistence — `customer_communication` Table
**Applies to**: A60 threading schema + backfill

The existing `CustomerCommunication` model in `backend/app/models/communications.py` is preserved. Migration 3 includes a backfill SQL block that creates thread rows for existing `customer_communication` records grouped by `(tenant_id, customer_id, sender_user_id)`. New code reads/writes through the threading model; existing templated sends continue to write `customer_communication` rows and optionally back-link to a thread via a new nullable `thread_id` column (added in Migration 3 as `ALTER TABLE customer_communication ADD COLUMN thread_id UUID NULL REFERENCES customer_communication_thread(id) ON DELETE SET NULL`).

---

### SSE Real-Time Updates (mvp-arch.md §13.11)
**Applies to**: A62 (new inbound/outbound messages), A64 (communication history), A66 (inbox)

The existing SSE infrastructure at `backend/services/dispatch_board_stream.py` and `backend/api/routes/notification_sse.py` is the model. A62's reply handler emits an SSE event after successful send so other open sessions (web owner + tech mobile) see the new message appear without polling.

---

## E. SHARED MODULE INTERFACES

### `services/sms_carrier.py` (new — established in A59)

```python
# backend/services/sms_carrier.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass
class InboundMessage:
    from_number: str        # E.164
    to_number: str          # E.164 — the tenant_phone_number that received it
    body: str
    carrier_message_id: str
    received_at: str        # ISO timestamp from carrier


@dataclass
class SendResult:
    status: str             # "sent" | "failed"
    carrier_message_id: str | None
    error_message: str | None
    http_status: int
    retryable: bool


@dataclass
class ProvisionedNumber:
    phone_number: str       # E.164
    carrier_provisioning_id: str
    monthly_fee_cents: int


class SmsCarrier(ABC):
    """
    Abstract interface for SMS carrier integrations.
    All carrier interactions must go through this interface — never import
    Telnyx SDK directly in routes or services.
    Configuration: SMS_CARRIER env var selects implementation at startup.
    """

    @abstractmethod
    def provision_number(self, area_code: str, tenant_id: UUID) -> ProvisionedNumber:
        """Acquire a new phone number from the carrier for this tenant."""
        ...

    @abstractmethod
    def send_message(self, from_number: str, to_number: str, body: str) -> SendResult:
        """Send an outbound SMS. Returns SendResult with status and carrier_message_id."""
        ...

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Return True if the webhook payload's signature is valid. False = reject (401)."""
        ...

    @abstractmethod
    def parse_inbound_webhook(self, payload: bytes) -> InboundMessage:
        """Parse carrier webhook payload into normalized InboundMessage dataclass."""
        ...

    @abstractmethod
    def get_delivery_status(self, carrier_message_id: str) -> str:
        """Return delivery status string: 'delivered' | 'failed' | 'sent' | 'unknown'."""
        ...

    @abstractmethod
    def release_number(self, phone_number: str) -> None:
        """Release a provisioned number back to the carrier pool."""
        ...


def get_sms_carrier() -> SmsCarrier:
    """
    Factory function — returns the configured SmsCarrier implementation.
    Call this instead of instantiating a carrier class directly.

    Configuration via SMS_CARRIER env var: 'telnyx' | 'mock' (default: 'mock')
    """
    from core.config import settings

    carrier_name = getattr(settings, "SMS_CARRIER", "mock")
    if carrier_name == "telnyx":
        from services.telnyx_sms_carrier import TelnyxSmsCarrier
        return TelnyxSmsCarrier()
    return MockSmsCarrier()
```

**File location**: `backend/services/sms_carrier.py`

---

### `services/sms_quota.py` (new — established in A65)

```python
# backend/services/sms_quota.py
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session


@dataclass
class QuotaCheckResult:
    allowed: bool
    overage: bool
    blocked_reason: str | None  # 'monthly_quota_reached' | 'customer_opted_out' | None
    used_segments: int
    included_segments: int
    remaining_segments: int


def check_quota(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    requested_segments: int,
) -> QuotaCheckResult:
    """
    Check whether a tenant can send `requested_segments` of SMS to `customer_id`.

    Checks in order:
    1. customer.sms_opted_out — returns blocked_reason='customer_opted_out' if True
    2. Current sms_quota_period for tenant — compares used vs. included
    3. cap_policy='hard' → blocked if over limit; 'soft' → allowed with overage=True

    Returns QuotaCheckResult without modifying used_segments.
    Call consume_quota() only after successful send.
    """
    ...


def consume_quota(
    db: Session,
    tenant_id: UUID,
    segments: int,
) -> None:
    """
    Atomically increment used_segments on the active sms_quota_period.
    Must be called in the same transaction as the successful send.
    Caller is responsible for rollback on send failure (do not call on failed send).
    """
    ...


def get_current_period(
    db: Session,
    tenant_id: UUID,
) -> "SmsQuotaPeriod | None":
    """Return the active sms_quota_period for tenant, or None if not yet created."""
    ...
```

**File location**: `backend/services/sms_quota.py`

---

### `services/customer_communication_threading.py` (new — established in A60)

```python
# backend/services/customer_communication_threading.py
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session


@dataclass
class ThreadingResult:
    success: bool
    thread_id: UUID | None
    unrouted_id: UUID | None    # Set when message parked in unrouted queue
    error: str | None


@dataclass
class InboundMessage:
    from_number: str
    to_number: str
    body: str
    carrier_message_id: str
    received_at: str


def route_inbound_message(
    db: Session,
    inbound: "InboundMessage",
    tenant_id: UUID,
) -> ThreadingResult:
    """
    Route an inbound SMS to the correct customer communication thread.

    Routing logic (§17.4):
    1. Match by sender phone → look up customer.mobile_phone for this tenant
    2. Match by recipient phone → confirm equals a tenant_phone_number for this tenant
    3. Find most recent active thread within 7-day window
    4. If no recent thread: fall back to customer.last_assigned_tech_id
    5. If still no match: park in customer_communication_unrouted with owner notification

    Returns ThreadingResult with thread_id on success or unrouted_id on park.
    """
    ...


def handle_sms_opt_out(
    db: Session,
    customer_id: UUID,
    opt_out_message: "InboundMessage",
) -> None:
    """
    Process TCPA STOP command.
    - Sets customer.sms_opted_out = True, sms_opt_out_at = now()
    - Writes audit_log entry with event_type='sms_opt_out'
    - Sends confirmation reply via get_sms_carrier().send_message()
    """
    ...


def handle_sms_opt_in(
    db: Session,
    customer_id: UUID,
    opt_in_message: "InboundMessage",
) -> None:
    """
    Process TCPA START/UNSTOP/YES from a previously opted-out customer.
    - Sets customer.sms_opted_out = False, sms_opt_in_consent = True
    - Sets sms_opt_in_at = now(), sms_opt_in_source = 'inbound_initiated'
    - Writes audit_log entry with event_type='sms_opt_in'
    - Sends confirmation reply
    """
    ...
```

**File location**: `backend/services/customer_communication_threading.py`

---

### `services/sms_provisioning.py` (new — established in A61)

```python
# backend/services/sms_provisioning.py
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session


@dataclass
class ProvisioningResult:
    success: bool
    tenant_phone_number_id: UUID | None
    phone_number: str | None
    error: str | None
    suggested_area_codes: list[str]  # populated on failure with alternatives


def provision_for_tenant(
    db: Session,
    tenant_id: UUID,
    area_code: str | None = None,
) -> ProvisioningResult:
    """
    Provision a Telnyx phone number for tenant at first SMS send.

    - If area_code is None: derives from tenant's primary office address
    - Calls get_sms_carrier().provision_number(area_code, tenant_id)
    - Inserts tenant_phone_number row with status='active'
    - On failure: status='provisioning_failed'; returns suggested_area_codes (3 nearby)
    - Adds monthly_fee_cents to tenant recurring billing line items
    """
    ...


def get_active_number_for_tenant(
    db: Session,
    tenant_id: UUID,
) -> "TenantPhoneNumber | None":
    """
    Return the active tenant_phone_number for this tenant, or None.
    Raises no exception — caller decides whether to trigger provisioning.
    """
    ...
```

**File location**: `backend/services/sms_provisioning.py`

---

## F. OPEN QUESTIONS RESOLVED

### F1 — `voice_audio_id` FK type: UUID vs. BIGINT

**Question**: The additions ledger (A60) specifies `voice_audio_id UUID NULL REFERENCES voice_command_log`. The MCP query of the live database shows `voice_command_log.id` is `BIGINT` (`nextval('voice_command_log_id_seq'::regclass)`), not UUID.

**Decision**: Use `BIGINT NULL REFERENCES voice_command_log(id) ON DELETE SET NULL` in the `customer_communication_message` table migration. The Python model field must be `Optional[int]` (not `Optional[UUID]`). The additions ledger spec was written assuming UUID PKs throughout; the actual schema uses a BIGINT sequence for `voice_command_log`. The implementation engineer must use the MCP-confirmed type.

---

### F2 — Backfill of existing `customer_communication` rows into thread structure

**Question**: A60 says "existing outbound rows backfill into threads at deployment time." What is the safe backfill strategy given rows may have different `sender_user_id` combinations?

**Decision**: The backfill runs as a Python data migration step (not pure SQL) to avoid locking the table. The backfill groups existing `customer_communication` rows by `(tenant_id, customer_id, sender_user_id)` and creates one `customer_communication_thread` per group, setting `first_message_at = min(sent_at)`, `last_message_at = max(sent_at)`, `message_count = count(*)`. Each existing `customer_communication` row gets a corresponding `customer_communication_message` row with `direction='outbound'`, `composition_method='template'`, `template_id` from existing FK. The backfill is idempotent (skips rows with a `thread_id` already set). Run as a separate Alembic migration step after Migration 3. The `ALTER TABLE customer_communication ADD COLUMN thread_id UUID NULL` is included at the end of Migration 3.

---

### F3 — `sms_quota_cap_policy` setting: where is it stored?

**Question**: A65 defines `sms_quota_cap_policy` as a tenant setting. Does it go in the B9 `tenant_setting` table or in the legacy `TenantSettings` model from `backend/app/models/core.py`?

**Decision**: Use the B9 `tenant_setting` table (key-value store with `setting_key` + `value_json`). Read via `get_effective_setting(db, tenant_id, 'sms_quota_cap_policy', fallback='soft')` from `services/setting_resolver.py`. Do not add a column to the `TenantSettings` model. Migration 6 inserts the settings catalog entry. The `sms_quota.check_quota()` service calls `get_effective_setting()` to retrieve the policy for the current period.

---

### F4 — `last_assigned_tech_id` fallback: does the `customer` table have this column?

**Question**: A60's routing fallback uses `customer.last_assigned_tech_id`. The MCP query of the `customer` table did not show this column.

**Decision**: This column is not yet in the live schema. It should be added in Migration 1 alongside the TCPA columns:

```sql
ALTER TABLE customer ADD COLUMN last_assigned_tech_id UUID NULL REFERENCES "user"(id) ON DELETE SET NULL;
```

This column is updated by the job dispatch system (existing or future batch) when a tech is assigned to a job for the customer. For MVP threading, if `last_assigned_tech_id IS NULL`, messages go directly to the unrouted queue. The routing service must handle NULL gracefully.

**Update to Migration 1**: add `last_assigned_tech_id` alongside the TCPA columns (rename migration description to `phase_fe_1_batch_b11_customer_sms_columns` to be inclusive).

---

### F5 — Do STOP detection keywords need a DB lookup, or hardcode?

**Question**: Should TCPA STOP keywords be configurable per tenant or hardcoded?

**Decision**: Hardcode in A59's `parse_inbound_webhook()` / TCPA detection logic. TCPA mandates recognition of the exact set: STOP, STOPALL, UNSUBSCRIBE, QUIT, CANCEL, END, ARRET (case-insensitive, exact-match on stripped body). Re-opt-in keywords: START, UNSTOP, YES. These are legal requirements, not tenant preferences. No DB lookup needed; no configurability in MVP.

---

### F6 — `notification_type` entries for SMS quota notifications: create or reuse?

**Question**: A65 needs to dispatch 80%/100% threshold notifications. Does it need new `notification_type` rows, or does the B10 category framework handle dispatch without them?

**Decision**: Use the B10 notification infrastructure pattern. The `notification_outbox` table has a `category_id` column (confirmed live). A65's Celery task constructs `NotificationOutbox` rows directly with `category_id='billing'` and `sub_trigger_id` set to `'sms_quota_80_pct'` / `'sms_quota_100_pct_soft'` / `'sms_quota_100_pct_hard'`. The B10 dispatcher gate (A58) routes to push + email for the `billing` category. No additional `notification_type` rows are required — B10's category-level dispatch is sufficient for MVP.

---

## G. EXTERNAL DEPENDENCY STATUS

| Item | External Dependency | Mock Strategy | Tom Action Required | Lead Time |
|:---|:---|:---|:---|:---|
| **A59** — Telnyx webhook + carrier adapter | Telnyx API (inbound webhook delivery, public-key signature verification) | `MockSmsCarrier` in `SMS_CARRIER=mock` mode — captures all calls without real API | Set up Telnyx account; configure webhook endpoint URL pointing to deployed API (`POST /api/v1/webhooks/sms/telnyx-inbound`) | ~1 day (account setup) |
| **A61** — Telnyx number provisioning | Telnyx Number Search + Acquire APIs; Telnyx billing for number rental (~$1/month per number) | `MockSmsCarrier.provision_number()` returns `+1{area_code}5550001` without real provisioning | Purchase at least 1 Telnyx number for staging/production testing | ~1 day after account setup |
| **A59 + A61** — A2P 10DLC brand + campaign registration | The Campaign Registry (TCR) via Telnyx 10DLC onboarding portal; carriers (T-Mobile, AT&T, Verizon) | `MockSmsCarrier` delivers all test messages without 10DLC; customer-facing deliverability requires registration | **Tom must start immediately** — submit brand registration → campaign registration with TCR. Use case: "Customer service / appointment notifications for trades businesses." This is the longest-lead-time item. | **4–6 weeks** (TCR brand approval 1–2 weeks; campaign approval 1–2 weeks; carrier propagation 1–2 weeks additional) |
| **A65** — Overage billing integration | Stripe (or existing subscription billing) for overage charges (`overage_segments × $0.05` added to invoice) | Log overage segments to `sms_quota_period.overage_segments`; mock billing integration with a log statement in dev | B14 (Stripe integration) must be live before real overage billing; B11 can ship with overage tracking but no automated invoice line items | B14 timeline (separate batch) |
| **A63** — Voice-to-text reply | Whisper + Ollama (GPU instance) — same infrastructure as B2 voice pipeline | Existing `MockSmsCarrier` + existing voice mock infrastructure from B2 | No new Tom action — uses existing GPU instance from B2 | None (B2 prerequisite) |
| **A59** — TCPA compliance | Legal: no external service, but requires documented opt-in consent flow and opt-out confirmation reply | N/A — TCPA compliance is code logic, not an API | Tom to confirm: (1) customer opt-in checkbox is included in new-customer creation UI (frontend scope), (2) legal review of opt-out confirmation message copy | ~1 week for legal copy review; no hard dependency on launch |
| **A64 / A66** — Push notifications for inbound SMS | B8/A51 `mobile_device_push_token` table + APNs/FCM (or mock push) must be live | `notification_outbox` rows created; push delivery mocked if B8 push infrastructure not yet live | No new Tom action if B8 is complete | None beyond B8 |

### Pre-Production Checklist for B11 (Tom-Owned)

1. **Telnyx Account**: Create account at telnyx.com; obtain API key; store as `TELNYX_API_KEY` in AWS Secrets Manager
2. **Telnyx Webhook Secret**: Configure webhook profile in Telnyx portal; store public key for signature verification as `TELNYX_PUBLIC_KEY` in AWS Secrets Manager
3. **Telnyx Number Purchase**: Buy one number via Telnyx portal for staging; production number provisioned lazily at first tenant SMS send
4. **A2P 10DLC Registration** ⚠️ START IMMEDIATELY:
   - Register brand: "Pilot for Trades" at [tcr.com](https://www.campaignregistry.com/) via Telnyx's 10DLC portal
   - Register campaign: use case "Customer service / appointment notifications for trades businesses"
   - Timeline: allow 4–6 weeks before reliable deliverability to T-Mobile/AT&T/Verizon customers
5. **TCPA Copy Review**: Legal review of opt-out confirmation message: `"You've been unsubscribed. Reply START to opt back in."` and opt-in confirmation: `"You've been resubscribed."`
6. **Staging SMS Test**: After Telnyx account is live, test `SMS_CARRIER=telnyx` with a real number against `MockSmsCarrier` → verify `TelnyxSmsCarrier` signature verification works end-to-end
7. **B14 Coordination**: Flag overage billing line item as deferred until B14 (Stripe) is live; A65 ships with `overage_segments` tracked in DB but no automated invoice creation

---

*Document complete. All six reads confirmed complete before writing. All seven sections populated. No open questions remain unresolved.*