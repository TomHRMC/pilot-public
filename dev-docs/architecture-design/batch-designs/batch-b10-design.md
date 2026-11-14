# Batch B10 Design Document — Notification System

**Batch**: B10  
**Items**: A56, A57, A58  
**Prerequisite Batches**: B9 (three-tier resolver `services/setting_resolver.py` must be live)  
**Gates**: B11 (SMS quota threshold notifications require `billing` category from A56; dispatcher gate from A58 must be live before real SMS sends)  
**Estimated Effort**: 12–14 days  
**Test Subfolder**: `tests/batch_b10/`  
**Design Date**: 2026-05-02  

---

## A. MIGRATION PLAN

### Pre-Migration Verification

Live DB MCP queries confirmed the following **before** this design was written:

| Table | Status |
|---|---|
| `notification_outbox` | EXISTS — 24 columns confirmed; `category_id`, `sub_trigger_id`, `recipient_user_id_originating` **absent** |
| `notification_category` | **DOES NOT EXIST** — safe to create |
| `notification_category_sub_trigger` | **DOES NOT EXIST** — safe to create |
| `notification_default_policy` | **DOES NOT EXIST** — safe to create |
| `notification_preference` | **DOES NOT EXIST** — safe to create |
| `in_app_notification` | **DOES NOT EXIST** — safe to create |

---

### Migration 1 — `phase_fe_1_batch_b10_notification_category_registry`

**Scope**: A56. Creates 3 new tables, seeds 8 categories + forced-minimum sub-triggers + system default policies, then extends `notification_outbox` with 3 new columns. Column addition uses the 3-part nullable-backfill-lock pattern because `category_id` will ultimately be NOT NULL.

#### New Table: `notification_category`

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `category_id` | TEXT | NO | — | PK; one of 8 values (see seed below) |
| `display_label` | TEXT | NO | — | User-facing label in matrix UI |
| `description` | TEXT | NO | — | Helper text shown below category row |
| `category_group_id` | TEXT | YES | NULL | Phase 2 grouping forward-compat |
| `display_order` | INTEGER | NO | — | Sort order in matrix |

- Primary key: `category_id`
- No FK references (top-level lookup table)
- Triggers: `audit_notification_category_changes`, `trg_notification_category_guard_created_immutable`, `trg_notification_category_set_updated_at` ← requires `StandardAuditMixin`
- No `is_active` needed — categories are platform-defined; soft-delete not applicable for lookup tables

**Seed data (8 categories, inserted in `upgrade()`)**:

| `category_id` | `display_label` | `display_order` |
|---|---|---|
| `quote_approvals` | Quote Approvals | 1 |
| `field_issues` | Field Issues | 2 |
| `sync_conflicts` | Sync Conflicts | 3 |
| `job_activity` | Job Activity | 4 |
| `customer_activity` | Customer Activity | 5 |
| `billing` | Billing | 6 |
| `background_sync_alerts` | Background Sync Alerts | 7 |
| `system_announcements` | System Announcements | 8 |

---

#### New Table: `notification_category_sub_trigger`

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `sub_trigger_id` | TEXT | NO | — | PK; e.g. `customer_activity.inbound_sms_reply` |
| `category_id` | TEXT | NO | — | FK → `notification_category.category_id` |
| `display_label` | TEXT | YES | NULL | For admin/help surfaces |
| `forced_minimum_push_uniform` | BOOLEAN | NO | FALSE | Applies to ALL recipients (critical alerts) |
| `forced_minimum_push_recipient_only` | BOOLEAN | YES | FALSE | Applies only to `recipient_user_id_originating` match |

- Primary key: `sub_trigger_id`
- FK: `fk_notif_sub_trigger_category` → `notification_category(category_id)` ON DELETE RESTRICT
- Index: `ix_notif_sub_trigger_category_id` on `category_id`
- Triggers: standard 3-trigger set (audit + immutable + updated_at)

**Seed data (forced-minimum sub-triggers)**:

| `sub_trigger_id` | `category_id` | `forced_minimum_push_uniform` | `forced_minimum_push_recipient_only` |
|---|---|---|---|
| `field_issues.all` | `field_issues` | TRUE | FALSE |
| `job_activity.assignment` | `job_activity` | FALSE | TRUE |
| `system_announcements.critical` | `system_announcements` | TRUE | FALSE |
| `customer_activity.inbound_sms_reply` | `customer_activity` | FALSE | TRUE |

Additional non-forced sub-triggers may be added without migration; these four define the forced-minimum semantics that drive the dispatcher gate.

---

#### New Table: `notification_default_policy`

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | NO | uuid4 | PK |
| `tenant_id` | UUID | YES | NULL | NULL = Pilot system default; non-NULL = tenant override |
| `category_id` | TEXT | NO | — | FK → `notification_category.category_id` |
| `channel` | TEXT | NO | — | `push` \| `email` \| `in_app` |
| `enabled` | BOOLEAN | NO | — | Whether this category×channel is on by default |
| `created_at` | TIMESTAMPTZ | NO | now() | StandardAuditMixin |
| `updated_at` | TIMESTAMPTZ | NO | now() | StandardAuditMixin |
| `created_by` | UUID | YES | NULL | FK → `user.id` RESTRICT |
| `updated_by` | UUID | YES | NULL | FK → `user.id` RESTRICT |

- FK: `fk_notif_default_policy_tenant` → `tenant(id)` ON DELETE RESTRICT (nullable)
- FK: `fk_notif_default_policy_category` → `notification_category(category_id)` ON DELETE RESTRICT
- **Unique constraint**: Cannot use a standard PostgreSQL UNIQUE on `(tenant_id, category_id, channel)` because NULL != NULL in standard UNIQUE. Use a **partial unique index**:
  - `CREATE UNIQUE INDEX uq_notif_default_policy_system ON notification_default_policy (category_id, channel) WHERE tenant_id IS NULL;`
  - `CREATE UNIQUE INDEX uq_notif_default_policy_tenant ON notification_default_policy (tenant_id, category_id, channel) WHERE tenant_id IS NOT NULL;`
- Index: `ix_notif_default_policy_tenant_id` on `tenant_id`
- Triggers: standard 3-trigger set

**System-default seed data (24 rows; tenant_id = NULL)**:

| Category | Push | Email | In-app |
|---|---|---|---|
| `quote_approvals` | ON | ON | ON |
| `field_issues` | ON | ON | ON |
| `sync_conflicts` | OFF | ON | ON |
| `job_activity` | ON | OFF | ON |
| `customer_activity` | ON | OFF | ON |
| `billing` | OFF | ON | ON |
| `background_sync_alerts` | ON | OFF | ON |
| `system_announcements` | OFF | ON | ON |

---

#### Column Additions to `notification_outbox` (3-Part Pattern)

**Verified absent** via MCP query on 2026-05-02. Three columns must be added using the nullable-backfill-lock pattern because `category_id` ultimately becomes NOT NULL.

**Part 1** — Add as NULLABLE:
```sql
ALTER TABLE notification_outbox ADD COLUMN category_id TEXT NULL;
ALTER TABLE notification_outbox ADD COLUMN sub_trigger_id TEXT NULL;
ALTER TABLE notification_outbox ADD COLUMN recipient_user_id_originating UUID NULL;
```

**Part 2** — Backfill existing rows with a safe default:
```sql
UPDATE notification_outbox SET category_id = 'system_announcements'
WHERE category_id IS NULL;
```
> **Decision**: All pre-existing `notification_outbox` rows (before B10) receive `category_id = 'system_announcements'` as the backfill sentinel. These are historical rows; preferences weren't tracked. See §F Open Questions for rationale.

**Part 3** — Lock to NOT NULL (after backfill confirms 0 NULLs):
```sql
ALTER TABLE notification_outbox ALTER COLUMN category_id SET NOT NULL;
```

**Add FKs and indexes after lock**:
```sql
ALTER TABLE notification_outbox ADD CONSTRAINT fk_notif_outbox_category 
    FOREIGN KEY (category_id) REFERENCES notification_category(category_id);
ALTER TABLE notification_outbox ADD CONSTRAINT fk_notif_outbox_sub_trigger 
    FOREIGN KEY (sub_trigger_id) REFERENCES notification_category_sub_trigger(sub_trigger_id);
CREATE INDEX ix_notif_outbox_category_id ON notification_outbox (category_id);
CREATE INDEX ix_notif_outbox_sub_trigger_id ON notification_outbox (sub_trigger_id) 
    WHERE sub_trigger_id IS NOT NULL;
```

`recipient_user_id_originating` remains nullable permanently (no FK — it mirrors `recipient_user_id` semantics but is not always the same user).

**CheckConstraint update**: Existing `notification_outbox_channel_chk` constrains `channel IN ('email','sms','in_app')`. The new `push` channel value for preferences is stored in `notification_default_policy` and `notification_preference` — NOT in `notification_outbox.channel`. The outbox channel constraint does NOT need updating; in-app delivery is the outbox channel; push dispatch is a separate delivery path outside the outbox in B10.

---

### Migration 2 — `phase_fe_1_batch_b10_notification_preference_in_app`

**Scope**: A57. Creates `notification_preference` and `in_app_notification` tables. No backfill required.

#### New Table: `notification_preference`

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | NO | uuid4 | PK |
| `tenant_id` | UUID | NO | — | FK → `tenant(id)` RESTRICT |
| `user_id` | UUID | YES | NULL | NULL = tenant-level override; non-NULL = user override |
| `category_id` | TEXT | NO | — | FK → `notification_category.category_id` |
| `channel` | TEXT | NO | — | `push` \| `email` \| `in_app` |
| `enabled` | BOOLEAN | NO | — | User/tenant preference value |
| `created_at` | TIMESTAMPTZ | NO | now() | StandardAuditMixin |
| `updated_at` | TIMESTAMPTZ | NO | now() | StandardAuditMixin |
| `created_by` | UUID | YES | NULL | FK → `user.id` RESTRICT |
| `updated_by` | UUID | YES | NULL | FK → `user.id` RESTRICT |

- FK: `fk_notif_pref_tenant` → `tenant(id)` ON DELETE RESTRICT
- FK: `fk_notif_pref_user` → `user(id)` ON DELETE RESTRICT (nullable)
- FK: `fk_notif_pref_category` → `notification_category(category_id)` ON DELETE RESTRICT
- Same **partial unique index** pattern as `notification_default_policy`:
  - `CREATE UNIQUE INDEX uq_notif_pref_user ON notification_preference (tenant_id, user_id, category_id, channel) WHERE user_id IS NOT NULL;`
  - `CREATE UNIQUE INDEX uq_notif_pref_tenant ON notification_preference (tenant_id, category_id, channel) WHERE user_id IS NULL;`
- Index: `ix_notif_pref_tenant_user` on `(tenant_id, user_id)`
- Index: `ix_notif_pref_category_channel` on `(category_id, channel)`
- Triggers: standard 3-trigger set
- CheckConstraint: `channel IN ('push', 'email', 'in_app')` — named `chk_notif_pref_channel`

---

#### New Table: `in_app_notification`

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `notification_id` | UUID | NO | uuid4 | PK |
| `tenant_id` | UUID | NO | — | FK → `tenant(id)` RESTRICT |
| `user_id` | UUID | NO | — | FK → `user(id)` RESTRICT |
| `category_id` | TEXT | NO | — | FK → `notification_category.category_id` |
| `body` | TEXT | NO | — | Notification body text |
| `deep_link_target` | TEXT | NO | — | Frontend route for click-to-navigate |
| `priority` | TEXT | NO | `standard` | `standard` \| `critical` |
| `created_at` | TIMESTAMPTZ | NO | now() | AppendOnlyMixin |
| `read_at` | TIMESTAMPTZ | YES | NULL | Set when user marks read |
| `created_by` | UUID | YES | NULL | FK → `user.id` RESTRICT |

- AppendOnlyMixin (no `updated_at`) — notifications are immutable after creation
- FK: `fk_in_app_notif_tenant` → `tenant(id)` ON DELETE RESTRICT
- FK: `fk_in_app_notif_user` → `user(id)` ON DELETE RESTRICT
- FK: `fk_in_app_notif_category` → `notification_category(category_id)` ON DELETE RESTRICT
- Index: `ix_in_app_notif_user_unread` — partial index for unread count: `CREATE INDEX ix_in_app_notif_user_unread ON in_app_notification (tenant_id, user_id, created_at DESC) WHERE read_at IS NULL;`
- Index: `ix_in_app_notif_user_created` on `(tenant_id, user_id, created_at DESC)` — for the bell panel recent-50 query
- CheckConstraint: `priority IN ('standard', 'critical')` — named `chk_in_app_notif_priority`
- Triggers: `audit_in_app_notification_changes`, `trg_in_app_notification_guard_created_immutable`; **no** `set_updated_at` trigger (AppendOnly has no `updated_at`)

---

### Migration 3 — A58

**No schema migration.** A58 is a code-only change to `backend/tasks/notification_worker.py`. The preference gate reads tables created in Migrations 1 and 2.

---

## B. EXECUTION ORDER

| # | Item | Rationale |
|---|---|---|
| 1 | **A56** — Notification Category Registry | Foundation layer. Every downstream item in this batch depends on `notification_category` table and the `notification_outbox` column extensions. The audit pass (updating ~6 production firing sites + 2 task firing sites) must complete before A57/A58 can be built, because A57's preference gate is only meaningful once every outbox entry declares a category. |
| 2 | **A57** — Preference Matrix Endpoints + In-App Banner | Depends on A56. Reads `notification_category` for the registry endpoint. Writes to `notification_preference` which FKs to `notification_category`. The `in_app_notification` table and SSE stream are also created here — the dispatcher (A58) writes to `in_app_notification` directly when channel = `in_app`. |
| 3 | **A58** — Delivery Dispatcher Preference Gate | Depends on A56 (needs `category_id`/`sub_trigger_id` on outbox rows) and A57 (reads `notification_preference` rows and calls `notification_resolver.get_effective_preference()`). Cannot run preference logic until both upstream items are complete. |

---

## C. NEW API ENDPOINTS

All endpoints use the prefix `/api/v1/notifications/`. JWT required on all authenticated endpoints. Test variant endpoints follow the dual-endpoint architecture from `§8.2 of pilot-python-engineer-methods.md`.

---

### A56 Endpoints

#### `GET /api/v1/notifications/categories`

**Auth**: JWT required  
**Permission**: `notification_preference.user_override.edit` (all authenticated roles can read the registry)  
**Query params**: none  

**Response 200**:
```json
{
  "categories": [
    {
      "category_id": "quote_approvals",
      "display_label": "Quote Approvals",
      "description": "Notifications when quotes are submitted, approved, or rejected.",
      "display_order": 1,
      "channels": {
        "push": {"system_default": true, "tenant_default": true, "effective": true},
        "email": {"system_default": true, "tenant_default": true, "effective": true},
        "in_app": {"system_default": true, "tenant_default": true, "effective": true}
      }
    }
  ]
}
```
Effective values are the tenant-level resolved defaults (NOT user-level — this endpoint feeds the matrix header row). Route file: `api/routes/notification_categories.py`.

---

#### `GET /api/v1/notifications/sub-triggers`

**Auth**: JWT required  
**Permission**: `notification_preference.user_override.edit`  
**Query params**: `category_id` (optional filter)  

**Response 200**:
```json
{
  "sub_triggers": [
    {
      "sub_trigger_id": "job_activity.assignment",
      "category_id": "job_activity",
      "display_label": "Job Assignment",
      "forced_minimum_push_uniform": false,
      "forced_minimum_push_recipient_only": true
    }
  ]
}
```

---

### A57 Endpoints

Route file: `api/routes/notification_preferences.py` and `api/routes/notification_in_app.py`.

---

#### `GET /api/v1/notifications/preferences`

**Auth**: JWT required  
**Permission**: `notification_preference.user_override.edit`  
**Query params**: `user_id` (UUID, optional — defaults to requesting user; owner can query other users' preferences)  

**Response 200** (8 categories × 3 channels = 24 cells):
```json
{
  "user_id": "uuid",
  "preferences": [
    {
      "category_id": "quote_approvals",
      "channel": "push",
      "enabled": true,
      "scope": "system",
      "forced_minimum": false,
      "can_disable": true
    },
    {
      "category_id": "field_issues",
      "channel": "push",
      "enabled": true,
      "scope": "system",
      "forced_minimum": true,
      "can_disable": false
    }
  ]
}
```
`scope` values: `"user" | "tenant" | "system"`. `forced_minimum` and `can_disable` are computed server-side from the sub-trigger metadata for this user's context.

---

#### `PUT /api/v1/notifications/preferences/{category_id}/{channel}`

**Auth**: JWT required  
**Permission**: `notification_preference.user_override.edit`  
**Path params**: `category_id` TEXT, `channel` TEXT (`push | email | in_app`)  
**Request body**:
```json
{"enabled": false}
```
**Response 200**:
```json
{"category_id": "sync_conflicts", "channel": "push", "enabled": false, "scope": "user"}
```
**Response 403**: When attempting to disable a forced-minimum push for a sub-trigger that affects this user as `recipient_user_id_originating`.

---

#### `DELETE /api/v1/notifications/preferences/{category_id}/{channel}`

**Auth**: JWT required  
**Permission**: `notification_preference.user_override.edit`  
**Effect**: Deletes the `notification_preference` row for `(tenant_id, user_id, category_id, channel)`. Subsequent reads fall back to tenant/system default.  
**Response 200**: `{"cleared": true, "reverted_to_scope": "tenant"}`

---

#### `PUT /api/v1/notifications/tenant-policy/{category_id}/{channel}`

**Auth**: JWT required  
**Permission**: `notification_preference.tenant_default.edit` — owner only  
**Request body**: `{"enabled": bool}`  
**Effect**: Upserts a `notification_default_policy` row with this tenant's `tenant_id`.  
**Response 200**: `{"category_id": "...", "channel": "...", "enabled": bool, "scope": "tenant"}`

---

#### `DELETE /api/v1/notifications/tenant-policy/{category_id}/{channel}`

**Auth**: JWT required  
**Permission**: `notification_preference.tenant_default.edit`  
**Effect**: Deletes the tenant-override row from `notification_default_policy`. Subsequent reads fall back to system default.  
**Response 200**: `{"cleared": true, "reverted_to_scope": "system"}`

---

#### `POST /api/v1/notifications/preferences/mute-all-push-non-critical`

**Auth**: JWT required  
**Permission**: `notification_preference.user_override.edit`  
**Effect**: For every category where `forced_minimum_push_uniform = FALSE` and the user is not the originating recipient of a forced-minimum-recipient-only sub-trigger (cannot be statically determined at bulk-mute time, so skip categories with `forced_minimum_push_recipient_only = TRUE`), upsert `notification_preference(enabled=False, channel='push')` rows.  
**Response 200**: `{"muted_count": 6}`

---

#### `POST /api/v1/notifications/preferences/mute-all-email`

**Auth**: JWT required  
**Permission**: `notification_preference.user_override.edit`  
**Effect**: Upsert `notification_preference(enabled=False, channel='email')` for all 8 categories for the requesting user.  
**Response 200**: `{"muted_count": 8}`

---

#### `POST /api/v1/notifications/preferences/reset-to-tenant-defaults`

**Auth**: JWT required  
**Permission**: `notification_preference.user_override.edit`  
**Effect**: Delete all `notification_preference` rows with `(tenant_id, user_id=requesting_user_id)`. All cells revert to tenant or system defaults.  
**Response 200**: `{"cleared_count": 14}`

---

#### `GET /sse/notifications`

**Auth**: JWT required (via `Authorization: Bearer` header; SSE clients that cannot set headers may pass `?token=<jwt>` — validated and immediately discarded after auth)  
**Permission**: `notification_preference.user_override.edit` (all authenticated roles)  
**Protocol**: `text/event-stream`  
**Channel**: One SSE connection per active session; delivers `in_app_notification` rows in real-time  
**Event format**:
```
data: {"type": "in_app_notification", "notification_id": "uuid", "category_id": "job_activity", "body": "...", "deep_link_target": "/jobs/uuid", "priority": "standard", "created_at": "..."}
```
**Headers required**: `Cache-Control: no-cache`, `X-Accel-Buffering: no`  
Route file: `api/routes/notification_sse.py`

---

#### `POST /api/v1/notifications/in-app/mark-read`

**Auth**: JWT required  
**Permission**: `notification_preference.user_override.edit`  
**Request body**:
```json
{"notification_ids": ["uuid1", "uuid2"]}
```
**Effect**: Sets `read_at = NOW()` on each `in_app_notification` row owned by the requesting user.  
**Response 200**: `{"marked_count": 2}`

---

#### `GET /api/v1/notifications/in-app/recent`

**Auth**: JWT required  
**Permission**: `notification_preference.user_override.edit`  
**Query params**: `limit` (int, max 50, default 50)  
**Response 200**:
```json
{
  "notifications": [
    {
      "notification_id": "uuid",
      "category_id": "job_activity",
      "body": "You've been assigned to the Davis panel upgrade.",
      "deep_link_target": "/jobs/uuid",
      "priority": "standard",
      "created_at": "2026-05-02T14:00:00Z",
      "read_at": null
    }
  ],
  "unread_count": 3
}
```

---

## D. PATTERN REUSE DECISIONS

### §21 Three-Tier Settings Resolver → `services/notification_resolver.py`

B9 established `services/setting_resolver.py::get_effective_setting()` and `get_effective_setting_for_user()`. B10/A58 needs an analogous resolver for notification preferences. A **new module** `services/notification_resolver.py` is created (not overloaded into setting_resolver.py — different tables, different resolution chain).

The resolution chain mirrors §16.5 / §21 exactly:
1. User-level row in `notification_preference` with matching `(tenant_id, user_id, category_id, channel)`
2. Tenant-level row in `notification_preference` with matching `(tenant_id, user_id=NULL, category_id, channel)`
3. Tenant-override row in `notification_default_policy` with matching `(tenant_id, category_id, channel)`
4. System-default row in `notification_default_policy` with `tenant_id IS NULL`
5. Fallback constant: `enabled=False`

**Items using this**: A57 (the GET preferences endpoint builds the full matrix) and A58 (the dispatcher gate calls it per-recipient per-channel).

See §E for the full interface.

---

### §18 SSE Pattern → `/sse/notifications`

B3/A19 established the SSE pattern in `api/routes/dispatch_board.py` (see `pilot-python-engineer-methods.md §18.2`). The `/sse/notifications` endpoint in A57 reuses the identical `_event_generator()` + `_sse_channels: dict[str, set[asyncio.Queue]]` + `emit_to_tenant()` pattern. The difference is channel scope: dispatch board is tenant-scoped (all dispatchers in a tenant see the same events); in-app notifications are user-scoped (each user has their own queue keyed on `(tenant_id, user_id)`).

```python
# Channel key is (tenant_id, user_id) not just tenant_id
_sse_notification_channels: dict[tuple[str, str], set[asyncio.Queue]] = {}
```

**emit_to_user()** function signature (new, mirrors existing `emit_to_tenant()`):
```python
def emit_to_user(tenant_id: str, user_id: str, event_type: str, payload: dict) -> None
```

Called from the dispatcher (A58) after writing an `in_app_notification` row, always AFTER `db.commit()` (per §18.4 anti-pattern rule).

**Items using this**: A57 (SSE endpoint definition), A58 (dispatcher calls `emit_to_user()` for in-app channel deliveries).

---

### §17.1 Periodic Poll Task → Extended `poll_pending_notifications`

The existing `tasks/notification_worker.py::poll_pending_notifications()` is a `@celery_app.task(name="poll_pending_notifications")` periodic task (§3.2). A58 extends it with a preference gate added to `_send_notification_impl()`. The outer polling loop and retry logic are unchanged; only the per-notification dispatch decision is gated.

**Critical implementation note**: The preference check must occur inside `_send_notification_impl()` BEFORE the `_send_via_channel()` call. If suppressed, the notification outbox row is updated to `status='suppressed_by_preferences'` (new status value — see CheckConstraint update in §F).

**Items using this**: A58 exclusively.

---

### §16.5 Three-Tier Resolver (arch §3.5.4) → Notification Dispatcher Gate

Arch doc §3.5.4 specifies the four-step resolution chain. A58 implements this in `notification_resolver.get_effective_preference()`. The forced-minimum override is applied AFTER the resolution chain returns:

```python
# Pseudocode matching arch doc §3.5.4 exactly
effective_enabled = get_effective_preference(db, tenant_id, user_id, category_id, channel)
sub_trigger = get_sub_trigger(outbox.sub_trigger_id)  # may be None

# Forced-minimum override for push channel only
if channel == 'push' and sub_trigger:
    if sub_trigger.forced_minimum_push_uniform:
        return True  # cannot be disabled
    if (sub_trigger.forced_minimum_push_recipient_only
        and outbox.recipient_user_id_originating == recipient_user_id):
        return True  # cannot be disabled for originating recipient

return effective_enabled
```

**Items using this**: A58.

---

### `services/setting_resolver.py::get_effective_setting()` → A57/A58 Cache Strategy

The settings resolver (B9) stores cache entries in Redis db=4 per `api/routes/settings.py::_get_settings_redis_client()`. A58 does NOT use Redis for preference caching — the arch doc §3.5.5 specifies "cache effective preferences per (user, category, channel) for the duration of a single dispatcher poll cycle." This is an **in-memory Python dict** within the task execution, not Redis. The dict is allocated at task start and discarded at task end. This is intentionally simpler than Redis — the poll cycle is seconds, not minutes.

```python
# In _poll_pending_notifications_impl():
pref_cache: dict[tuple[UUID, str, str], bool] = {}
```

**Items using this**: A58.

---

### Existing Outbox Firing Sites — Audit Pass (A56)

Six production `NotificationOutbox(...)` call sites identified via codebase search. All must receive `category_id` (and `sub_trigger_id` where applicable) as part of A56:

| File | Location | Assigned `category_id` | `sub_trigger_id` |
|---|---|---|---|
| `backend/services/quickbooks_sync.py` | QB conflict notification | `sync_conflicts` | NULL |
| `backend/api/routes/communications.py` | Customer comm send confirmation | `customer_activity` | NULL |
| `backend/api/routes/scheduling.py` | Job assignment notification | `job_activity` | `job_activity.assignment` |
| `backend/tasks/notify_etc_variance_owners.py` | ETC variance alert (email) | `job_activity` | NULL |
| `backend/tasks/auto_expire_qb_conflicts.py` | QB conflict pre-warning | `sync_conflicts` | NULL |
| `backend/tasks/auto_expire_qb_conflicts.py` | QB conflict auto-expiry notify | `sync_conflicts` | NULL |
| `backend/tasks/expire_stale_calendar_conflicts.py` | Calendar conflict pre-warning | `sync_conflicts` | NULL |

This audit pass is a **prerequisite completion criterion for A56** — A56 is not done until all seven sites above have `category_id` assigned.

---

## E. SHARED MODULE INTERFACES

### New Module: `backend/services/notification_resolver.py`

```python
"""
Notification preference resolver for Pilot for Trades.

Three-tier resolution chain per arch doc §3.5.4:
  User-level preference → Tenant-level preference → Notification default policy
  (tenant override) → Notification default policy (system default) → False

Established in B10/A58. Consumed by:
  - tasks/notification_worker.py::_send_notification_impl() (dispatcher gate)
  - api/routes/notification_preferences.py::_build_full_matrix() (GET preferences)
"""

from uuid import UUID
from typing import Optional
from sqlmodel import Session, select


def get_effective_preference(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    category_id: str,
    channel: str,
    pref_cache: Optional[dict] = None,
) -> bool:
    """
    Resolve the effective notification preference for a user × category × channel combination.

    Resolution order (§3.5.4):
      1. User-level row in notification_preference (user_id = user_id)
      2. Tenant-level row in notification_preference (user_id IS NULL)
      3. Tenant-override row in notification_default_policy (tenant_id = tenant_id)
      4. System-default row in notification_default_policy (tenant_id IS NULL)
      5. Fallback: False

    Args:
        db:           Active SQLModel session.
        tenant_id:    Tenant scope for the preference lookup.
        user_id:      Recipient user being evaluated.
        category_id:  Notification category (e.g., 'job_activity').
        channel:      Delivery channel ('push' | 'email' | 'in_app').
        pref_cache:   Optional in-memory dict for single-poll-cycle caching.
                      Key: (user_id, category_id, channel). Callers manage lifecycle.

    Returns:
        bool — True if the notification should be delivered via this channel to this user.
    """
    ...


def apply_forced_minimum_override(
    base_enabled: bool,
    channel: str,
    sub_trigger_id: Optional[str],
    recipient_user_id: UUID,
    recipient_user_id_originating: Optional[UUID],
    db: Session,
) -> bool:
    """
    Apply forced-minimum push override after the three-tier resolution chain.

    Forced-minimum only applies to the 'push' channel. Email and in-app always
    respect the resolved preference — no forced-minimum for those channels.

    Forced-minimum semantics (per arch §3.5.3):
      - forced_minimum_push_uniform: override to True for ALL recipients
      - forced_minimum_push_recipient_only: override to True ONLY when
        recipient_user_id == recipient_user_id_originating

    Args:
        base_enabled:                  Result from get_effective_preference().
        channel:                       Delivery channel being evaluated.
        sub_trigger_id:                Sub-trigger ID from the outbox row (may be None).
        recipient_user_id:             User being evaluated for delivery.
        recipient_user_id_originating: The 'owning' user from the outbox row.
        db:                            Active SQLModel session (needed to fetch sub_trigger row).

    Returns:
        bool — Final delivery decision after forced-minimum override applied.
    """
    ...


def should_deliver(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    category_id: str,
    channel: str,
    sub_trigger_id: Optional[str],
    recipient_user_id_originating: Optional[UUID],
    pref_cache: Optional[dict] = None,
) -> bool:
    """
    Combined resolver: get_effective_preference() + apply_forced_minimum_override().

    Single-call interface for the dispatcher gate. Returns the final delivery
    decision for one (user × category × channel) combination.

    Args:
        db:                             Active SQLModel session.
        tenant_id:                      Tenant scope.
        user_id:                        Recipient user being evaluated.
        category_id:                    Notification category.
        channel:                        Delivery channel.
        sub_trigger_id:                 Sub-trigger ID from outbox row (may be None).
        recipient_user_id_originating:  The 'owning' user from the outbox row (may be None).
        pref_cache:                     Optional in-memory cache dict.

    Returns:
        bool — True = deliver; False = suppress.
    """
    base = get_effective_preference(db, tenant_id, user_id, category_id, channel, pref_cache)
    return apply_forced_minimum_override(
        base, channel, sub_trigger_id, user_id, recipient_user_id_originating, db
    )
```

**File path**: `backend/services/notification_resolver.py` (new file)

---

### Extended Module: `backend/tasks/notification_worker.py`

A58 adds a preference gate to the existing `_send_notification_impl()` function. The gate is inserted between the "load notification outbox record" step and the "send via channel" step:

```python
# New function added to notification_worker.py in A58
def _build_recipient_list(
    notification: NotificationOutbox,
    db: Session,
) -> list[UUID]:
    """
    Determine the list of user IDs to evaluate for delivery.

    For notifications with recipient_user_id set: single-recipient list.
    For system-broadcast notifications: all active users in tenant (Phase 2 only;
    B10 scope is single-recipient evaluation only).

    Returns:
        List of user UUIDs to evaluate preference gate against.
    """
    ...
```

The `_send_notification_impl()` function gains a new early-exit path:

```python
# Preference gate (A58 addition — after loading notification, before _send_via_channel)
if notification.recipient_user_id and notification.category_id:
    from services.notification_resolver import should_deliver
    deliver = should_deliver(
        db=db,
        tenant_id=notification.tenant_id,
        user_id=notification.recipient_user_id,
        category_id=notification.category_id,
        channel=notification.channel,
        sub_trigger_id=notification.sub_trigger_id,
        recipient_user_id_originating=notification.recipient_user_id_originating,
        pref_cache=None,  # per-task caching is poll-loop level; single dispatch has no cache
    )
    if not deliver:
        notification.status = "suppressed_by_preferences"
        db.add(notification)
        db.commit()
        logger.info(
            f"Notification {notification.id} suppressed by preferences "
            f"(user={notification.recipient_user_id}, "
            f"category={notification.category_id}, channel={notification.channel})"
        )
        return {"status": "suppressed", "reason": "user_preferences"}
```

---

## F. OPEN QUESTIONS RESOLVED

### Q1: What category should pre-existing `notification_outbox` rows receive during backfill?

**Context**: The `category_id` column is ultimately NOT NULL. Before the migration runs, there are potentially hundreds of existing rows with no category.

**Decision**: Backfill with `system_announcements`. Rationale: these are historical rows that predate the category system; they will never be re-dispatched (they're already `sent` or `failed`). Using `system_announcements` as a backfill sentinel is semantically correct (it's the "everything else" category) and avoids the need for a more complex per-row backfill that would require examining the notification body or related entity. The preference gate in A58 only applies to NEW outbox rows created AFTER B10; historical rows are processed or dead-lettered before the gate goes live.

**Implementation**: `UPDATE notification_outbox SET category_id = 'system_announcements' WHERE category_id IS NULL;` — confirmed safe because all pre-existing rows either have `status IN ('sent', 'failed')` or are actively being processed. The migration must run the backfill AFTER seeding the `notification_category` table (the FK must exist before the column is backfilled).

---

### Q2: How to enforce UNIQUE constraints on `notification_default_policy` and `notification_preference` when `tenant_id` / `user_id` can be NULL (PostgreSQL NULL ≠ NULL in UNIQUE)?

**Context**: Standard `UNIQUE (tenant_id, category_id, channel)` fails to prevent two system-default rows (both with `tenant_id = NULL`) because PostgreSQL treats `NULL != NULL` in UNIQUE indexes.

**Decision**: Use **partial unique indexes** — a well-established PostgreSQL pattern for nullable uniqueness:

```sql
-- notification_default_policy
CREATE UNIQUE INDEX uq_notif_default_policy_system 
    ON notification_default_policy (category_id, channel) 
    WHERE tenant_id IS NULL;
CREATE UNIQUE INDEX uq_notif_default_policy_tenant 
    ON notification_default_policy (tenant_id, category_id, channel) 
    WHERE tenant_id IS NOT NULL;

-- notification_preference  
CREATE UNIQUE INDEX uq_notif_pref_tenant_level 
    ON notification_preference (tenant_id, category_id, channel) 
    WHERE user_id IS NULL;
CREATE UNIQUE INDEX uq_notif_pref_user_level 
    ON notification_preference (tenant_id, user_id, category_id, channel) 
    WHERE user_id IS NOT NULL;
```

This ensures: exactly one system-default row per `(category_id, channel)`; exactly one tenant-override row per `(tenant_id, category_id, channel)`; exactly one user-override row per `(tenant_id, user_id, category_id, channel)`.

---

### Q3: Should `notification_outbox.status` CheckConstraint be updated to include `'suppressed_by_preferences'`?

**Context**: A58 needs to mark suppressed notifications with a distinct status to distinguish from `failed` (delivery error) and `canceled` (explicitly voided).

**Decision**: **Yes — update the CheckConstraint** in the A58 implementation. The current constraint is:
```sql
CHECK (status IN ('pending', 'sent', 'failed', 'canceled'))
```
Add `'suppressed_by_preferences'`:
```sql
CHECK (status IN ('pending', 'sent', 'failed', 'canceled', 'suppressed_by_preferences'))
```
This requires: (1) dropping the existing constraint in the migration, (2) adding the updated constraint. The ORM `Literal` type annotation on `NotificationOutbox.status` must also be updated to include the new value. No new migration file is needed — this fits in the A58 code changes. **However**, because A58 is code-only, the status constraint update requires a small schema migration: `phase_fe_1_batch_b10_notification_dispatcher_gate`.

---

### Q4: Does the `in_app` channel in `notification_preference` and `notification_default_policy` conflict with the existing `notification_outbox.channel` value of `'in_app'`?

**Context**: `notification_outbox.channel` uses `'in_app'`. The preference tables use `'push' | 'email' | 'in_app'`. But the outbox CheckConstraint allows `('email','sms','in_app')` — not `'push'`.

**Decision**: **No conflict.** The outbox represents the actual delivery channel for a specific notification delivery row. Push notifications are NOT delivered through the `notification_outbox` in B10 — the outbox only tracks email, SMS, and in-app banner delivery. Push delivery infrastructure (FCM/APNs) is a B11+ concern. In B10, `'push'` in preference tables means "mobile push notification preference" — it is stored and respected by the dispatcher, but the dispatcher's push delivery path is a stub (`pass`) until B11 wires up the carrier. This is consistent with the mock strategy for push in §G.

---

### Q5: Should `notification_resolver.get_effective_preference()` be a direct DB query or cache-backed?

**Decision**: Both, with different call sites:
- **GET /preferences endpoint** (A57): direct DB query — user is actively viewing their settings; cache would show stale data.
- **Dispatcher gate** (A58, `poll_pending_notifications`): in-memory dict cache per poll cycle. The cache is a Python `dict[tuple[UUID, str, str], bool]` allocated in `poll_pending_notifications`, passed as `pref_cache` param to `should_deliver()`. On each poll cycle, up to 100 notifications are processed; for a tenant with 5 users and 8 categories × 3 channels = 120 potential cache entries per poll cycle. This is trivial memory and avoids 100 × 24 = 2,400 DB queries per poll execution at steady state.

---

## G. EXTERNAL DEPENDENCY STATUS

### Email (SendGrid)

**Status**: Already integrated in `backend/services/email_service.py`. B10 does NOT add new external email dependencies.  
**Mock strategy**: Existing `email_service.py` mock/test strategy applies. No new mock work required for B10.  
**Tom action required**: None.

---

### Mobile Push Notifications (FCM / APNs)

**Status**: B10 introduces the `'push'` channel in preference tables and the dispatcher gate respects it — but **push delivery is a STUB in B10**. The `_send_via_channel()` function's push path will return:
```python
elif channel == "push":
    # Push delivery deferred to B11+; stub returns "sent" to avoid infinite retry
    return {"status": "sent", "details": {"stub": True}, "error_message": None, "http_status": 200, "retryable": False}
```

**Mock strategy**: Push delivery is stubbed (no real carrier call). Tests validate preference gate logic (correct suppression/delivery decisions) without requiring a live push provider.  
**Tom action required**: Push delivery implementation is deferred to a future batch (post-B11). B10 only needs the preference infrastructure to be live so B11 SMS quotas can use the `billing` category. Tom does not need to take any action before B10 implementation.

---

### SendGrid (In-App Notifications)

**Status**: In-app notifications are delivered via SSE directly — no SendGrid dependency. In-app channel writes to `in_app_notification` table and emits via SSE using the existing in-process `asyncio.Queue` pattern from `emit_to_user()`. No third-party service required.  
**Mock strategy**: In tests, SSE delivery is not tested end-to-end (no live HTTP connection in unit tests). Tests verify: `in_app_notification` row created correctly, `emit_to_user()` called after `db.commit()`, preference gate correctly allows/suppresses based on mock preference rows.  
**Tom action required**: None.

---

### No New External Dependencies

B10 introduces no new external service accounts, API keys, or third-party dependencies beyond what is already live (SendGrid) or stubbed (push). All three items (A56, A57, A58) are entirely internal schema + API + Celery work.

---

## Implementation Notes

### `notification_worker.py` Import Safety

A58 imports `from services.notification_resolver import should_deliver` inside the function body (lazy import), not at module level. This follows the pattern established in `setting_resolver.py` (see `app.models.settings` lazy import there) to avoid circular import issues during app startup. The `notification_worker.py` task module is loaded by Celery; importing from `services/` at module level is safe, but the lazy import is cleaner for testability.

### SSE Channel Registry Thread Safety

The `_sse_notification_channels` dict in `notification_sse.py` uses `asyncio.Queue` objects. The existing dispatch board pattern (§18.2) notes that in production, the in-process queue registry should be backed by Redis Pub/Sub for multi-instance support. B10 uses the same in-process queue approach as the dispatch board — acceptable for MVP with 2 ECS Fargate tasks. Post-MVP, when push is live and the notification volume increases, migrate to Redis Pub/Sub per the same pattern note in the dispatch board implementation.

### `notification_event_id` FK on `notification_outbox`

The existing `NotificationOutbox` model requires `notification_event_id: uuid.UUID = Field(foreign_key="notification_event.id", nullable=False)`. The B10 items do NOT change this FK. All new `notification_outbox` rows created by B10-era code must still include a valid `notification_event_id`. The `notification_resolver.py` module does not create outbox rows — it only reads them. The firing sites updated during the A56 audit pass (§D) must continue to provide `notification_event_id`.

### Migration Execution Order Within B10

The three migrations must run in this sequence:
1. `phase_fe_1_batch_b10_notification_category_registry` — creates lookup tables + seeds data + extends outbox
2. `phase_fe_1_batch_b10_notification_preference_in_app` — creates `notification_preference` + `in_app_notification` (FKs to `notification_category` from Migration 1)
3. `phase_fe_1_batch_b10_notification_dispatcher_gate` — updates `notification_outbox` status CheckConstraint (code-only batch otherwise)

All three must cleanly survive `alembic upgrade head → downgrade -1 → upgrade head`.
