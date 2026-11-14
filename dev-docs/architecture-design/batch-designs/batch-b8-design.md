# Batch B8 Design Document — Pass 4 Tier 1: Conflict UIs + Background Sync

**Generated**: 2026-05-02  
**Status**: READY FOR IMPLEMENTATION  
**Batch**: B8  
**Prerequisite batches**: B6 (calendar conflict pattern), B7b (escalation table + classification engine)  
**Gates**: None (B10, B11 do not depend on B8)  
**Estimated effort**: 23–30 days  
**Test subfolder**: `tests/batch_b8/`  
**Items**: A51 → A47 → A48 → A49 → A50

---

## A. MIGRATION PLAN

### New Tables

#### Migration 1: `phase_fe_1_batch_b8_mobile_device_push_token`

New canonical push token registry table introduced by A51. Referenced by A47/A48 loop closure and B11/B14 future surfaces.

```sql
CREATE TABLE mobile_device_push_token (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                    UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    user_id                      UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    device_id                    UUID NOT NULL,
    platform                     TEXT NOT NULL,           -- CHECK: 'ios' | 'android'
    push_token                   TEXT NOT NULL,
    app_version                  TEXT NULL,
    os_version                   TEXT NULL,
    registered_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    notification_permission_granted  BOOLEAN NOT NULL DEFAULT TRUE,
    revoked_at                   TIMESTAMPTZ NULL,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by                   UUID NULL,
    updated_by                   UUID NULL,
    CONSTRAINT mobile_device_push_token_platform_chk
        CHECK (platform IN ('ios', 'android')),
    CONSTRAINT mobile_device_push_token_tenant_user_device_uq
        UNIQUE (tenant_id, user_id, device_id)
);

CREATE INDEX idx_mobile_device_push_token_tenant_user
    ON mobile_device_push_token (tenant_id, user_id);
CREATE INDEX idx_mobile_device_push_token_active
    ON mobile_device_push_token (tenant_id, user_id, device_id)
    WHERE revoked_at IS NULL;
```

**Verification**: `SELECT table_name FROM information_schema.tables WHERE table_name = 'mobile_device_push_token'` returned empty — table does not exist.

---

#### Migration 2: `phase_fe_1_batch_b8_mobile_sync_session`

New sync session telemetry table (A51). Records outcomes of each background sync run per device.

```sql
CREATE TABLE mobile_sync_session (
    session_id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                    UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    user_id                      UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    device_id                    UUID NOT NULL,
    triggered_by                 TEXT NOT NULL,   -- CHECK: 'silent_push' | 'os_opportunistic' | 'foreground' | 'manual'
    started_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at                 TIMESTAMPTZ NULL,
    outcome                      TEXT NULL,       -- CHECK: 'success' | 'partial' | 'failed' | 'throttled'
    items_attempted              INTEGER NOT NULL DEFAULT 0,
    items_committed              INTEGER NOT NULL DEFAULT 0,
    items_deferred               INTEGER NOT NULL DEFAULT 0,
    items_failed                 INTEGER NOT NULL DEFAULT 0,
    failure_reason               TEXT NULL,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT mobile_sync_session_triggered_by_chk
        CHECK (triggered_by IN ('silent_push', 'os_opportunistic', 'foreground', 'manual')),
    CONSTRAINT mobile_sync_session_outcome_chk
        CHECK (outcome IS NULL OR outcome IN ('success', 'partial', 'failed', 'throttled'))
);

CREATE INDEX idx_mobile_sync_session_tenant_user_device
    ON mobile_sync_session (tenant_id, user_id, device_id, started_at DESC);
CREATE INDEX idx_mobile_sync_session_device_recent
    ON mobile_sync_session (device_id, started_at DESC);
```

**Verification**: `SELECT table_name FROM information_schema.tables WHERE table_name = 'mobile_sync_session'` returned empty — table does not exist.

---

#### Migration 3: `phase_fe_1_batch_b8_mobile_push_rate_limit`

Per-device server-side rate limiting table for silent push dispatch (A51 frequency cap).

```sql
CREATE TABLE mobile_push_rate_limit (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                    UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    device_id                    UUID NOT NULL,
    last_push_sent_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    push_count_current_window    INTEGER NOT NULL DEFAULT 1,
    window_start_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT mobile_push_rate_limit_device_uq UNIQUE (device_id)
);

CREATE INDEX idx_mobile_push_rate_limit_tenant
    ON mobile_push_rate_limit (tenant_id);
```

**Verification**: `SELECT table_name FROM information_schema.tables WHERE table_name = 'mobile_push_rate_limit'` returned empty — table does not exist.

---

#### Migration 4: `phase_fe_1_batch_b8_mobile_sync_event_audit`

Audit log for owner resolution of escalated mobile conflicts (A48). Append-only.

```sql
CREATE TABLE mobile_sync_event_audit (
    id                               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                        UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    escalation_id                    UUID NOT NULL REFERENCES mobile_sync_owner_escalation(id),
    originator_user_id               UUID NOT NULL REFERENCES "user"(id),
    resolver_user_id                 UUID NOT NULL REFERENCES "user"(id),
    resolution_action                TEXT NOT NULL,
    resolution_channel               TEXT NOT NULL DEFAULT 'web',  -- CHECK: 'web' | 'voice'
    tech_local_snapshot_at_commit    JSONB NULL,
    server_state_snapshot_at_commit  JSONB NULL,
    post_commit_state                JSONB NULL,
    resolved_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT mobile_sync_event_audit_channel_chk
        CHECK (resolution_channel IN ('web', 'voice'))
);

CREATE INDEX idx_mobile_sync_event_audit_escalation
    ON mobile_sync_event_audit (escalation_id);
CREATE INDEX idx_mobile_sync_event_audit_tenant_resolver
    ON mobile_sync_event_audit (tenant_id, resolver_user_id, resolved_at DESC);
```

**Verification**: `SELECT table_name FROM information_schema.tables WHERE table_name = 'mobile_sync_event_audit'` returned empty — table does not exist.

---

### Column Additions to Existing Tables

#### Migration 5: `phase_fe_1_batch_b8_integration_sync_conflict_diff_columns`

Adds diff/staleness columns to `integration_sync_conflict` for QB conflict display (A49).

**Pre-migration schema confirmed from live DB**:
```
integration_sync_conflict columns (current):
  created_at, updated_at, created_by, updated_by, id, tenant_id, app_service_id,
  entity_type_code, entity_id, external_id, status, internal_payload,
  external_payload, resolved_at, resolved_by
```

**None of the following columns exist** — all are net-new additions:

```sql
ALTER TABLE integration_sync_conflict
    ADD COLUMN base_snapshot              JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN field_diffs                JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN pilot_modified_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN pilot_modified_by_user_id  UUID NULL,
    ADD COLUMN qb_modified_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN qb_modified_by_external_user_label  TEXT NULL,
    ADD COLUMN auto_expire_at             TIMESTAMPTZ NULL,
    ADD COLUMN pre_warning_at             TIMESTAMPTZ NULL;

-- Partial indexes for expiry background task performance
CREATE INDEX idx_integration_sync_conflict_auto_expire
    ON integration_sync_conflict (tenant_id, auto_expire_at)
    WHERE status = 'pending' AND auto_expire_at IS NOT NULL;
CREATE INDEX idx_integration_sync_conflict_pre_warning
    ON integration_sync_conflict (tenant_id, pre_warning_at)
    WHERE status = 'pending' AND pre_warning_at IS NOT NULL;
```

> **Note on defaults**: The `NOT NULL DEFAULT now()` on `pilot_modified_at` and `qb_modified_at` is only safe because no existing `integration_sync_conflict` rows have conflict-resolution diff context — existing rows have `internal_payload` / `external_payload` only. After migration, the sync engine (B6 pattern) must populate these on every new conflict insert.

---

#### Migration 6: `phase_fe_1_batch_b8_tenant_settings_qb_background_sync`

Adds QB auto-expiry settings (A50) and background sync settings (A51) to `tenant_settings`.

**Pre-migration schema confirmed from live DB** — none of the following exist in `tenant_settings`:

```sql
ALTER TABLE tenant_settings
    -- QB auto-expiry per entity type (A50) — default OFF per Tier 1 #2 Decision 9
    ADD COLUMN qb_auto_expire_customer_enabled   BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN qb_auto_expire_customer_direction TEXT    NULL,
    ADD COLUMN qb_auto_expire_quote_enabled      BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN qb_auto_expire_quote_direction    TEXT    NULL,
    ADD COLUMN qb_auto_expire_invoice_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN qb_auto_expire_invoice_direction  TEXT    NULL,
    ADD COLUMN qb_auto_expire_expense_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN qb_auto_expire_expense_direction  TEXT    NULL,
    ADD COLUMN qb_auto_expire_days               INTEGER NULL,   -- NULL = system default (60)
    ADD COLUMN qb_pre_warning_days               INTEGER NULL,   -- NULL = system default (14)
    -- Background sync (A51)
    ADD COLUMN background_sync_enabled           BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN background_sync_wifi_only         BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN background_sync_battery_floor_pct INTEGER NOT NULL DEFAULT 20,
    ADD COLUMN background_sync_push_interval_minutes  INTEGER NULL;  -- NULL = system default (5)
```

---

#### Migration 7: `phase_fe_1_batch_b8_notification_outbox_push_channel`

Adds `push` to the `notification_outbox.channel` CHECK constraint (required by A51 silent-push dispatch). 

**Current constraint confirmed from live DB**:
```
notification_outbox_channel_chk: CHECK (channel IN ('email', 'sms', 'in_app'))
```

```sql
ALTER TABLE notification_outbox
    DROP CONSTRAINT notification_outbox_channel_chk,
    ADD CONSTRAINT notification_outbox_channel_chk
        CHECK (channel IN ('email', 'sms', 'in_app', 'push'));
```

> **Backward safety**: Existing rows are all `email | sms | in_app` — this is an additive constraint relaxation. No data migration needed. The `notification_outbox_inapp_requires_user_chk` constraint (`in_app` requires `recipient_user_id`) does not conflict with `push` records.

---

### Migration Naming Summary

| # | Migration name | Logical unit |
|---|---|---|
| 1 | `phase_fe_1_batch_b8_mobile_device_push_token` | New table |
| 2 | `phase_fe_1_batch_b8_mobile_sync_session` | New table |
| 3 | `phase_fe_1_batch_b8_mobile_push_rate_limit` | New table |
| 4 | `phase_fe_1_batch_b8_mobile_sync_event_audit` | New table |
| 5 | `phase_fe_1_batch_b8_integration_sync_conflict_diff_columns` | Column additions |
| 6 | `phase_fe_1_batch_b8_tenant_settings_qb_background_sync` | Column additions |
| 7 | `phase_fe_1_batch_b8_notification_outbox_push_channel` | Constraint relaxation |

---

## B. EXECUTION ORDER

| # | Item | One-line rationale |
|---|---|---|
| 1 | **A51** — Background Sync Infrastructure | Creates `mobile_device_push_token` table consumed by A47/A48 loop-closure push and A50 QB conflict notifications; must be first. |
| 2 | **A47** — Owner-Side Mobile-Conflict Escalation Queue Endpoints | Extends existing B7b/A46 route file; reads `mobile_sync_owner_escalation` (B7b); depends on A51 push token infra for SSE channel enrichment. |
| 3 | **A48** — Owner-Side Mobile-Conflict Resolution Write Path | Resolves items surfaced by A47; uses A51 push dispatch for loop closure to originating tech. |
| 4 | **A49** — QuickBooks Conflict Queue Endpoints + Schema Extension | Depends on Migration 5 (diff columns on `integration_sync_conflict`); extends existing `integrations.py` router; SSE wiring is parallel pattern to A47. |
| 5 | **A50** — QuickBooks Conflict Resolution Write Path + Auto-Expiry | Resolves items surfaced by A49; Celery Beat task registration; A51 push channel required for pre-warning notifications. |

---

## C. NEW API ENDPOINTS

### A51 — Background Sync Infrastructure

#### `POST /api/v1/mobile/push-tokens`
Register or refresh a device push token (called on every app launch).

- **Auth**: JWT required
- **RBAC**: Any authenticated user (no explicit permission check — implicit by valid JWT)
- **Request body**:
  ```json
  {
    "device_id": "uuid",
    "platform": "ios | android",
    "push_token": "string",
    "app_version": "string (optional)",
    "os_version": "string (optional)",
    "notification_permission_granted": true
  }
  ```
- **Response 200**:
  ```json
  {
    "device_id": "uuid",
    "registered_at": "ISO8601",
    "last_seen_at": "ISO8601"
  }
  ```
- **Idempotent**: upserts on `(tenant_id, user_id, device_id)` unique constraint.

---

#### `DELETE /api/v1/mobile/push-tokens/{device_id}`
Revoke a device push token (called on logout or explicit token invalidation).

- **Auth**: JWT required
- **RBAC**: Any authenticated user (own token only; cross-tenant revocation is 404)
- **Response 204**: No content on success.
- **Response 404**: If `(user_id, device_id)` does not match current user's tenant.

---

#### `POST /api/v1/mobile/sync-sessions/{session_id}/complete`
Client reports background sync session telemetry on completion.

- **Auth**: JWT required
- **RBAC**: Any authenticated user (own session only)
- **Request body**:
  ```json
  {
    "outcome": "success | partial | failed | throttled",
    "items_attempted": 0,
    "items_committed": 0,
    "items_deferred": 0,
    "items_failed": 0,
    "failure_reason": "string (optional)"
  }
  ```
- **Response 200**:
  ```json
  {
    "session_id": "uuid",
    "outcome": "string",
    "completed_at": "ISO8601"
  }
  ```

---

### A47 — Owner-Side Mobile-Conflict Escalation Queue Endpoints

> **Path clarification**: The existing B7b/A46 route file `backend/api/routes/owner_escalations.py` already exposes `/owner/mobile-sync-escalations`. A47 **extends this existing file** with additional query parameters, a history sub-route, and SSE wiring. The path remains `/mobile-sync-escalations` (not renamed to `/field-issues`) to preserve B7b test contracts.

#### `GET /api/v1/owner/mobile-sync-escalations` (extended)
Enhanced list endpoint with full A47 filtering spec.

- **Auth**: JWT required
- **RBAC**: `require_permission("field_issue.view")` — owner, accountant roles
- **Query params** (added to B7b baseline):
  - `status` (default `pending`; accepts `pending | auto_recovered | stale | all`)
  - `tech_active_within_hours` (default 24; `null` for all)
  - `operation_type` (multi-value)
  - `sort` (default `-escalated_at`; accepts `-escalated_at | escalated_at | -captured_at | captured_at`)
  - `limit`, `offset` (existing)
- **Response 200**:
  ```json
  {
    "items": [{
      "id": "uuid",
      "originating_user_id": "uuid",
      "tech_name": "string",
      "tech_role": "string",
      "tech_last_active_at": "ISO8601",
      "operation_type": "string",
      "operation_summary": "string",
      "escalation_reason_explainer": "string",
      "captured_at": "ISO8601",
      "escalated_at": "ISO8601",
      "status": "string",
      "server_state_summary": {}
    }],
    "next_cursor": "string | null",
    "total_pending": 0
  }
  ```

---

#### `GET /api/v1/owner/mobile-sync-escalations/{escalation_id}` (extended)
Full detail with A47 diff payload.

- **Auth**: JWT required
- **RBAC**: `require_permission("field_issue.view")`
- **Response 200** (extension of existing B7b shape):
  ```json
  {
    "id": "uuid",
    "originating_user_id": "uuid",
    "conflict_id": "uuid",
    "escalation_reason": "string",
    "escalation_reason_explainer": "string",
    "escalation_type": "field_diff | deletion_conflict_tech_captured_against_deleted | deletion_conflict_status_change_collision | permission_revoked_capture",
    "status": "string",
    "escalated_at": "ISO8601",
    "tech_local_snapshot": {},
    "server_state_snapshot": {},
    "field_diffs": [{"field": "string", "tech_value": {}, "server_value": {}, "change_type": "modified | added | removed"}],
    "available_resolutions": ["use_tech", "use_server", "..."],
    "resolved_by_user_id": "uuid | null",
    "resolved_at": "ISO8601 | null",
    "resolution_action": "string | null",
    "resolution_channel": "web | voice | null"
  }
  ```

---

#### `GET /api/v1/owner/mobile-sync-escalations/history`
Historical archive of resolved escalations.

- **Auth**: JWT required
- **RBAC**: `require_permission("field_issue.view")`
- **Query params**: Same as list + `resolved_at_after`, `resolved_at_before`; `status` defaults to `resolved`
- **Response 200**: Same shape as list with additional `resolved_at`, `resolved_by_user_id`, `resolution_action`, `resolution_channel` fields per item.

---

### A48 — Owner-Side Mobile-Conflict Resolution Write Path

#### `POST /api/v1/owner/mobile-sync-escalations/{escalation_id}/resolve` (extended)

Extends the existing B7b resolve endpoint with full A48 resolution variant set, three distinct 409 payload types, loop closure, and audit log capture.

- **Auth**: JWT required
- **RBAC**: `require_permission("field_issue.resolve")` — owner, accountant roles
- **Request body**:
  ```json
  {
    "resolution": "use_tech | use_server | restore_and_accept | override_with_tech | discard_tech | accept_authorized_at_capture | reject_unauthorized",
    "expected_server_state_at_view_time": "ISO8601"
  }
  ```
- **Response 200**:
  ```json
  {
    "committed": true,
    "resolution_outcome": "string",
    "post_commit_state": {},
    "originator_notification_dispatched": true
  }
  ```
- **Response 409** (`staleness_type = 'server_changed'`):
  ```json
  {
    "type": "https://pilotfortrades.com/errors/stale-state",
    "staleness_type": "server_changed",
    "refreshed_escalation": {}
  }
  ```
- **Response 409** (`staleness_type = 'auto_recovered'`):
  ```json
  {
    "staleness_type": "auto_recovered",
    "auto_recovery_outcome": "string",
    "message": "string"
  }
  ```
- **Response 409** (`staleness_type = 'stale'`):
  ```json
  {
    "staleness_type": "stale",
    "tech_force_discarded": true,
    "message": "string"
  }
  ```

---

### A49 — QuickBooks Conflict Queue Endpoints

> All three endpoints are added to the existing `backend/api/routes/integrations.py` router which already has `prefix="/integrations/quickbooks"`.

#### `GET /api/v1/integrations/quickbooks/conflicts`

- **Auth**: JWT required
- **RBAC**: `require_permission("qb_conflict.view")` — owner, accountant roles
- **Query params**: `entity_type` (multi: `customer | quote | invoice | expense`), `master` (multi: `pilot | quickbooks | user_choice`), `sort` (default `-financial_impact,-detected_at`), `limit`, `offset`
- **Response 200**:
  ```json
  {
    "items": [{
      "conflict_id": "uuid",
      "entity_type": "string",
      "entity_identifier": "string",
      "entity_summary": "string",
      "master_direction": "pilot | quickbooks | user_choice",
      "pilot_change_summary": "string",
      "qb_change_summary": "string",
      "detected_at": "ISO8601",
      "financial_delta_cents": 0,
      "affected_entity_url": "string"
    }],
    "total": 0,
    "offset": 0,
    "limit": 25
  }
  ```

---

#### `GET /api/v1/integrations/quickbooks/conflicts/{id}`

- **Auth**: JWT required
- **RBAC**: `require_permission("qb_conflict.view")`
- **Response 200**:
  ```json
  {
    "conflict_id": "uuid",
    "entity_type": "customer | quote | invoice | expense",
    "base_snapshot": {},
    "pilot_snapshot": {},
    "qb_snapshot": {},
    "field_diffs": [{"field": "string", "pilot_value": {}, "qb_value": {}, "change_type": "modified | added | removed"}],
    "master_direction": "string",
    "master_recommended_action": "string",
    "conflict_subtype": "field_diff | deleted_in_pilot_modified_in_qb | modified_in_pilot_deleted_in_qb",
    "available_resolutions": ["accept_local", "accept_remote", "..."],
    "financial_delta_payload": {},
    "tax_period_warning": false,
    "auto_expire_at": "ISO8601 | null",
    "pre_warning_at": "ISO8601 | null"
  }
  ```

---

#### `GET /api/v1/integrations/quickbooks/conflicts/history`

- **Auth**: JWT required
- **RBAC**: `require_permission("qb_conflict.view")`
- **Query params**: `entity_type` (multi-value), `resolved_at_after`, `resolved_at_before`, `limit`, `offset`
- **Response 200**: Same shape as list with `resolved_at`, `resolver_user_id`, `resolution_action` added per item.

---

### A50 — QuickBooks Conflict Resolution Write Path

#### `POST /api/v1/integrations/quickbooks/conflicts/{id}/resolve`

- **Auth**: JWT required
- **RBAC**: `require_permission("qb_conflict.resolve")` — owner, accountant roles
- **Request body**:
  ```json
  {
    "resolution": "accept_local | accept_remote | restore_and_accept_remote | recreate_and_keep_local | delete_both",
    "expected_pilot_modified_at": "ISO8601",
    "expected_qb_modified_at": "ISO8601"
  }
  ```
- **Response 200**:
  ```json
  {
    "committed": true,
    "resolution_outcome": "string",
    "post_commit_state": {},
    "push_to_other_side_dispatched": true
  }
  ```
- **Response 409** (`staleness_type = 'server_changed'`):
  ```json
  {
    "type": "https://pilotfortrades.com/errors/stale-state",
    "staleness_type": "server_changed",
    "refreshed_conflict": {}
  }
  ```
- **Response 409** (`staleness_type = 'auto_recovered'`):
  ```json
  {
    "staleness_type": "auto_recovered",
    "auto_recovery_outcome": "string",
    "message": "string"
  }
  ```

---

## D. PATTERN REUSE DECISIONS

### §16.4 — Pre-Commit Staleness Check

**Established in**: B3/A19  
**Module**: `utils/staleness_check.py` — `assert_not_stale()` function  
**Already imported in B7b**: `backend/api/routes/owner_escalations.py`

| Item | Usage |
|---|---|
| **A48** | `assert_not_stale(expected_updated_at=data.expected_server_state_at_view_time, actual_updated_at=escalation.updated_at, refreshed_payload=<detail_payload>, entity_label="escalation")` — three distinct 409 shapes require custom staleness_type field added alongside the standard call |
| **A50** | `assert_not_stale()` called twice — once against `pilot_modified_at`, once against `qb_modified_at`. The existing `assert_not_stale()` signature takes a single timestamp; implement as two sequential calls with separate entity labels, or extend with a dual-timestamp variant |

**Dual-timestamp extension for A50**:

```python
# utils/staleness_check.py — extend with:
def assert_not_stale_dual(
    expected_pilot_modified_at: datetime | None,
    actual_pilot_modified_at: datetime,
    expected_qb_modified_at: datetime | None,
    actual_qb_modified_at: datetime,
    refreshed_payload: Dict[str, Any],
) -> None:
    """
    Dual-timestamp variant for QB conflicts where both sides can drift.
    Raises 409 if either timestamp mismatches.
    """
    pilot_stale = (
        expected_pilot_modified_at is not None
        and expected_pilot_modified_at.replace(microsecond=0)
            != actual_pilot_modified_at.replace(microsecond=0)
    )
    qb_stale = (
        expected_qb_modified_at is not None
        and expected_qb_modified_at.replace(microsecond=0)
            != actual_qb_modified_at.replace(microsecond=0)
    )
    if pilot_stale or qb_stale:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://pilotfortrades.com/errors/stale-state",
                "staleness_type": "server_changed",
                "refreshed": refreshed_payload,
            },
        )
```

---

### §16.6 — Four-Class Severity Classification

**Established in**: B7b/A40  
**Module**: `services/mobile_sync_conflict.py` — `classify_sync_conflict()`, `SyncResolution` dataclass

| Item | Usage |
|---|---|
| **A47** | Reads `conflict_severity` from `mobile_sync_event` (already classified at B7b/A40 insertion time); no re-classification needed |
| **A48** | Resolution routing branches on `SyncResolution.owner_escalation_required` — determines which domain-specific commit path to take |

---

### §16.11 — Mobile-to-Web Escalation Pattern

**Established in**: B7b/A46 (routing); **UI layer**: A47, A48  
**Module**: `backend/api/routes/owner_escalations.py` — existing B7b route file extended by A47/A48

| Item | Usage |
|---|---|
| **A47** | Extends `_list_escalations_impl()` with `tech_active_within_hours` join on `user.last_active_at`, `operation_type` filter, `sort` ordering, history sub-route |
| **A48** | Extends `_resolve_escalation_impl()` with full resolution variant set (7 values vs B7b's 4), three 409 types, loop-closure push dispatch via `notification_outbox`, `mobile_sync_event_audit` insert |

---

### §16.10 — Bilateral Integration Conflict Resolution Pattern

**Established in**: B6/A33 (calendar)  
**Inherited by**: A49/A50 (QuickBooks)

| Item | Pattern reuse |
|---|---|
| **A49** | `base_snapshot + field_diffs + pilot_modified_at + qb_modified_at` mirrors `calendar_sync_conflict` additions from B6/A32. Diff computation is entity-type-aware (customer/quote/invoice/expense each have different field sets). |
| **A50** | Pre-commit staleness check mirrors A33 shape. Auto-expiry Celery task `auto_expire_qb_conflicts_per_tenant` mirrors `expire_stale_calendar_conflicts` from B6/A34. Default expiry 60 days (vs calendar 30) per accounting cadence. |

---

### §16.12 — Background Sync Execution Pattern

**Reference implementation**: A51  
**Module**: `services/mobile_background_sync.py` (new file)

| Item | Pattern |
|---|---|
| **A51** | Silent push dispatcher detects queue age >15 min → pushes via `mobile_device_push_token`; per-device rate limit via `mobile_push_rate_limit`; iOS `{aps: {content-available: 1}}` / Android high-priority FCM; OS throttle detection after >2h gap |

---

### §16.5 — System-Default-with-Tenant-Override (Pre-B9 Inline Pattern)

`services/setting_resolver.py` is a **B9 deliverable** and is NOT available in B8. For A51's `background_sync_push_interval_minutes` frequency cap:

- Read directly from `tenant_settings.background_sync_push_interval_minutes` (nullable column added in Migration 6)
- Fall back to hardcoded system constant `SYSTEM_BG_SYNC_PUSH_INTERVAL_MINUTES = 5`
- When B9 ships, this inline fallback will be replaced by `get_effective_setting(db, tenant_id, "background_sync_push_interval_minutes", fallback=5)`

```python
# services/mobile_background_sync.py — inline two-tier until B9
def _get_push_interval_minutes(tenant_settings: TenantSettings) -> int:
    """Two-tier inline resolver. Replace with get_effective_setting() after B9."""
    SYSTEM_DEFAULT = 5
    val = tenant_settings.background_sync_push_interval_minutes
    return val if val is not None else SYSTEM_DEFAULT
```

---

### Existing `notification_outbox` — Push Channel Extension

**Pre-existing pattern**: `notification_outbox` used by B6/A35 for rate-limited in-app notifications.  
**B8 extension**: A51 adds `push` to the `channel` CHECK constraint (Migration 7), enabling silent push records. Silent push records have `recipient_user_id NOT NULL` (device lookup) and `body` = JSON-serialized payload (APNs/FCM data).

---

## E. SHARED MODULE INTERFACES

### `services/mobile_background_sync.py` (new — A51)

```python
# services/mobile_background_sync.py
"""
Background Sync Infrastructure — Push dispatcher and sync session manager.

Establishes §16.12 Background Sync Execution Pattern.
Canonical push token registry for B11 (SMS push) and future surfaces.

Introduced: B8/A51
Consumed by: A47/A48 (loop closure), B11/A66 (push inbox updates)
"""

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session


@dataclass
class PushDispatchResult:
    """Result of a single silent push attempt to one device."""
    device_id: UUID
    dispatched: bool
    skip_reason: str | None   # 'rate_limited' | 'revoked_token' | 'permission_denied' | None
    platform: str             # 'ios' | 'android'


def dispatch_silent_push_for_device(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    device_id: UUID,
    sync_session_id: UUID,
) -> PushDispatchResult:
    """
    Dispatch a single silent push to a registered device.

    Checks:
      1. Token exists and is not revoked in mobile_device_push_token
      2. Rate limit not exceeded (mobile_push_rate_limit; interval per tenant setting)
      3. notification_permission_granted = True

    On APNs/FCM 'invalid token' response: marks token revoked, returns dispatched=False.

    Args:
        db:               DB session
        tenant_id:        Tenant scope
        user_id:          Target user
        device_id:        Target device UUID
        sync_session_id:  Session ID to include in push payload

    Returns:
        PushDispatchResult with dispatch outcome
    """
    ...


def detect_pending_items_for_tenant(
    db: Session,
    tenant_id: UUID,
    age_threshold_minutes: int = 15,
) -> list[tuple[UUID, UUID]]:
    """
    Return list of (user_id, device_id) pairs that have mobile_sync_pending_operation
    items older than age_threshold_minutes and no recent push dispatch.

    Used by Celery Beat task to identify devices needing a silent push nudge.

    Args:
        db:                     DB session
        tenant_id:              Tenant scope
        age_threshold_minutes:  Minimum item age before triggering push (default 15)

    Returns:
        List of (user_id, device_id) tuples
    """
    ...


def detect_os_throttle_for_device(
    db: Session,
    device_id: UUID,
    throttle_threshold_hours: int = 2,
) -> bool:
    """
    Detect whether a device appears OS-throttled.

    Heuristic: push was dispatched but no sync session reported within
    throttle_threshold_hours despite pending items in queue.

    Used by the next foreground sync response to surface
    "Background sync delayed by your phone" banner.

    Args:
        db:                       DB session
        device_id:                Device UUID
        throttle_threshold_hours: No-sync window before declaring throttled (default 2)

    Returns:
        True if device appears OS-throttled
    """
    ...


def register_or_refresh_push_token(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    device_id: UUID,
    platform: str,
    push_token: str,
    app_version: str | None,
    os_version: str | None,
    notification_permission_granted: bool,
) -> None:
    """
    Upsert push token for (tenant_id, user_id, device_id).

    Called by POST /api/v1/mobile/push-tokens route.
    On token change (same device, new token), revokes old token row and inserts new.

    Args per mobile_device_push_token schema.
    """
    ...


def revoke_push_token(
    db: Session,
    user_id: UUID,
    device_id: UUID,
) -> bool:
    """
    Mark push token revoked for (user_id, device_id).

    Called by DELETE /api/v1/mobile/push-tokens/{device_id}.

    Returns:
        True if row found and revoked; False if not found (idempotent).
    """
    ...


def dispatch_loop_closure_push(
    db: Session,
    tenant_id: UUID,
    originator_user_id: UUID,
    escalation_id: UUID,
    resolution_action: str,
) -> list[PushDispatchResult]:
    """
    Dispatch loop-closure push to all active devices for the originating tech
    after owner resolves an escalated mobile conflict.

    Used by A48 resolution write path.
    Aggregates multiple resolved escalations in a window per A35 rate-limit pattern.

    Args:
        db:                   DB session
        tenant_id:            Tenant scope
        originator_user_id:   Tech whose conflict was resolved
        escalation_id:        Resolved escalation UUID
        resolution_action:    Resolution action taken by owner

    Returns:
        List of PushDispatchResult for each device targeted
    """
    ...


def _get_push_interval_minutes(tenant_settings) -> int:
    """
    Two-tier inline resolver for background_sync_push_interval_minutes.
    Replace with get_effective_setting() after B9/A53 ships.

    Args:
        tenant_settings: TenantSettings ORM row

    Returns:
        Effective interval in minutes (system default 5 if tenant override is None)
    """
    SYSTEM_DEFAULT = 5
    val = getattr(tenant_settings, "background_sync_push_interval_minutes", None)
    return val if val is not None else SYSTEM_DEFAULT
```

**File path**: `backend/services/mobile_background_sync.py`

---

### QB Conflict Diff Service (inline in new route file)

A49's per-entity-type field diff computation lives in a new file:

```python
# services/qb_conflict_diff.py
"""
QuickBooks conflict field diff computation.

Mirrors calendar_sync_conflict diff pattern from B6/A32 but is entity-type-aware.
Each entity type (customer, quote, invoice, expense) has a distinct field registry.
"""

from typing import Any


ENTITY_DIFF_FIELDS: dict[str, list[str]] = {
    "customer": ["display_name", "email", "phone", "billing_address", "shipping_address"],
    "quote": ["status", "total_amount_cents", "line_items", "expiry_date", "notes"],
    "invoice": ["status", "amount_due_cents", "due_date", "line_items", "payments"],
    "expense": ["amount_cents", "category", "description", "vendor", "date"],
}


def compute_qb_field_diffs(
    entity_type: str,
    pilot_snapshot: dict[str, Any],
    qb_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Compute field-level diffs between Pilot and QB snapshots for a given entity type.

    Returns list of diffs in the platform-wide track-changes vocabulary (§16.2):
        [{"field": str, "pilot_value": Any, "qb_value": Any, "change_type": "modified|added|removed"}]

    Args:
        entity_type:     One of 'customer' | 'quote' | 'invoice' | 'expense'
        pilot_snapshot:  Current state in Pilot (from base_snapshot + local edits)
        qb_snapshot:     Current state in QB (from base_snapshot + QB edits)

    Returns:
        List of field diff objects
    """
    ...


def compute_financial_delta(
    entity_type: str,
    pilot_snapshot: dict[str, Any],
    qb_snapshot: dict[str, Any],
) -> int | None:
    """
    Compute financial_delta_cents for invoice conflicts.
    Returns None for non-invoice entity types.

    Args:
        entity_type:     Entity type string
        pilot_snapshot:  Pilot snapshot
        qb_snapshot:     QB snapshot

    Returns:
        Delta in cents (Pilot - QB), or None
    """
    ...


def detect_tax_period_warning(
    entity_type: str,
    qb_snapshot: dict[str, Any],
) -> bool:
    """
    Detect whether the invoice spans a closed QB tax period.
    Returns False for non-invoice entity types.

    Args:
        entity_type:   Entity type string
        qb_snapshot:   QB snapshot

    Returns:
        True if invoice date falls within a closed QB tax period
    """
    ...
```

**File path**: `backend/services/qb_conflict_diff.py`

---

## F. OPEN QUESTIONS RESOLVED

### F.1 — URL Path: `/field-issues` vs `/mobile-sync-escalations`

**Question**: A47 spec says `GET /api/v1/owner/field-issues` but the live codebase at `backend/api/routes/owner_escalations.py` already registers `GET /api/v1/owner/mobile-sync-escalations` from B7b/A46.

**Decision**: Keep `/mobile-sync-escalations` path. A47 extends the existing route file with the additional filtering, history sub-route, and SSE wiring. The A47 additions ledger's `/field-issues` path was spec-only and was superseded by the B7b implementation. Renaming would break B7b test contracts.

**Rationale**: The tests at `tests/batch_b7b/` reference the existing path. Path rename is an API break that would require versioning or coordinated FE/test updates. The path `/mobile-sync-escalations` is functionally equivalent and already RBAC-gated.

---

### F.2 — `notification_outbox` Channel Constraint Blocks Push

**Question**: A51 inserts `push` channel records into `notification_outbox` but the live CHECK constraint only allows `email | sms | in_app`.

**Decision**: Migration 7 (`phase_fe_1_batch_b8_notification_outbox_push_channel`) must DROP the existing constraint and ADD a new one including `push`. This must run before any A51 notification dispatch code reaches production. Confirm migration ordering: migration 7 runs before `services/mobile_background_sync.py` is deployed.

**Confirmed safe**: Existing data is `email | sms | in_app` only — constraint relaxation has no impact on existing rows.

---

### F.3 — B9 `setting_resolver.py` Not Available in B8

**Question**: A51's `background_sync_push_interval_minutes` setting uses the §16.5 system-default-with-tenant-override pattern, but `services/setting_resolver.py` is a B9/A53 deliverable.

**Decision**: Implement inline two-tier resolver in `services/mobile_background_sync.py::_get_push_interval_minutes()` using hardcoded constant `SYSTEM_DEFAULT = 5`. When B9 ships, replace with `get_effective_setting(db, tenant_id, "background_sync_push_interval_minutes", fallback=5)`. The B9 engineer must search for `TODO_B9_RESOLVER` comment in `mobile_background_sync.py` and update the call site.

---

### F.4 — `mobile_sync_event_audit` Table Not in B7b

**Question**: A48 spec mentions inserting to `mobile_sync_event_audit` but no such table was created in B7b.

**Decision**: Create `mobile_sync_event_audit` in Migration 4 as a B8 deliverable. This table is append-only (no `StandardAuditMixin` update fields). FK references `mobile_sync_owner_escalation.id` and both `user.id` columns for originator and resolver.

---

### F.5 — A50 Voice Intent Registration Location

**Question**: Where does `list_pending_qb_conflicts` voice intent get registered?

**Decision**: Register in the existing voice action router module (`services/voice_action_router.py`) in `INTENT_HANDLERS` dict — same pattern as `list_pending_calendar_conflicts` from B6/A36. A50 adds the handler function; no new module needed. Handler is status-query-only: fetches pending count + oldest conflict date; returns structured content for voice readback. Explicitly refuses resolve attempts with redirect copy: "QuickBooks conflicts require manual review on the web. You have N pending."

---

### F.6 — A48 Resolution Variants vs B7b Existing Enum

**Question**: B7b/A46 `owner_escalations.py` `_resolve_escalation_impl()` accepts `{used_local, used_server, manual_edit, rejected}` but A48 spec has 7 variants: `{use_tech, use_server, restore_and_accept, override_with_tech, discard_tech, accept_authorized_at_capture, reject_unauthorized}`.

**Decision**: Extend `EscalationResolveRequest.resolution_action` enum to include all 7 A48 variants. Maintain backward compatibility — the existing 4 B7b variants map to A48 equivalents: `used_local` → `use_tech`, `used_server` → `use_server`, `rejected` → `reject_unauthorized`. The validation set in `_resolve_escalation_impl()` at `owner_escalations.py` must be updated. B7b tests use the old variant names — update those tests in B8.

---

### F.7 — `integration_sync_conflict.base_snapshot` and `field_diffs` DEFAULT Values

**Question**: Migration 5 adds `NOT NULL` columns to an existing table. If there are rows without prior diff data, the migration would fail.

**Decision**: Use `DEFAULT '{}'::jsonb` for `base_snapshot` and `DEFAULT '[]'::jsonb` for `field_diffs` in the migration DDL (as written in Migration 5 above). These defaults are structural — the sync engine will always populate real values on new conflict inserts. Existing rows are pre-B6 conflicts with `internal_payload`/`external_payload` only; they will never be surfaced through the new A49 diff UI. After migration, remove the DEFAULT constraint clause if strict schema hygiene is required (these fields should always be set by application code).

---

## G. EXTERNAL DEPENDENCY STATUS

### APNs / FCM (A51 — Push Token Dispatch)

| Item | Detail |
|---|---|
| **Dependency** | Apple Push Notification service (APNs) for iOS; Firebase Cloud Messaging (FCM) for Android |
| **Required by** | A51 `dispatch_silent_push_for_device()`, A48 `dispatch_loop_closure_push()` |
| **Mock strategy** | `MockPushCarrier` implementation in `services/mobile_background_sync.py` that captures dispatched push calls in-memory (same pattern as B11's `MockSmsCarrier` from §22 of python-engineer-methods). `PUSH_CARRIER=mock` env var selects implementation. All B8 tests use mock. |
| **Tom action required** | Register Apple Developer account for APNs p8 key (Team ID + Key ID + key file). Register Firebase project for FCM server key. Both needed before device-side push can be tested on real hardware. **Lead time**: APNs p8 key is immediate after Apple enrollment; FCM project is same-day. No approval gating for silent push (content-available=1). |
| **Production gate** | Push token registration endpoint and dispatch path can be fully unit-tested with mock. Integration test on real device requires valid APNs/FCM credentials. |

---

### APNs BGAppRefreshTask / Android WorkManager (A51 — OS-Scheduled Fallback)

| Item | Detail |
|---|---|
| **Dependency** | iOS BGAppRefreshTask registration (mobile app entitlement); Android WorkManager periodic task (mobile app code) |
| **Required by** | `triggered_by = 'os_opportunistic'` cases in `mobile_sync_session` |
| **Mock strategy** | Backend has no direct dependency — OS-scheduled trigger is client-side only. Backend only consumes the `POST /sync-sessions/{session_id}/complete` report. No backend mock needed. |
| **Tom action** | Mobile engineer enables `BGAppRefreshTask` entitlement in Xcode + registers task identifier `com.pilotfortrades.background-sync`. Android WorkManager periodic task with `PeriodicWorkRequest`. Backend requires no change. |

---

### QuickBooks Sync Engine (A49 / A50)

| Item | Detail |
|---|---|
| **Dependency** | Existing QuickBooks OAuth + sync pipeline from B2/B5 (`services/quickbooks_sync.py`) |
| **Required by** | A50 `accept_local` / `accept_remote` resolution paths invoke the existing QB sync push mechanism |
| **Mock strategy** | Existing `MockQuickBooksSync` or QB sync method stubs used in B2/B5 tests. A50 tests mock the sync push call, test the conflict row status transition and audit log capture. |
| **Tom action** | None beyond existing QB OAuth setup. Resolution push to QB reuses existing token refresh + API call pattern. |

---

### SendGrid / Email (A50 — Pre-Warning Notifications)

| Item | Detail |
|---|---|
| **Dependency** | Existing `notification_outbox` → `services/email_service.py` → SendGrid pipeline |
| **Required by** | A50 `auto_expire_qb_conflicts_per_tenant` Celery task inserts `notification_outbox` row at `pre_warning_at` |
| **Mock strategy** | Tests insert a conflict with `pre_warning_at = now() - 1 second`, trigger the Celery task synchronously (`task.apply()`), assert `notification_outbox` row created with correct channel/recipient. No actual email send in tests. |
| **Tom action** | None — existing SendGrid integration handles delivery. |

---

### Firebase Cloud Messaging (A48 — Loop Closure Push to Tech)

| Item | Detail |
|---|---|
| **Dependency** | FCM / APNs — same as A51 dependency above |
| **Required by** | `dispatch_loop_closure_push()` in `services/mobile_background_sync.py` called from A48 resolution write path |
| **Mock strategy** | `MockPushCarrier` as above. A48 tests assert `dispatch_loop_closure_push()` called with correct `originator_user_id` and `escalation_id`. |
| **Tom action** | Same as A51 — no separate registration needed. |

---

*All six reads complete. Schema ambiguities resolved. No open questions remain.*
