# Batch B6 — Calendar Conflict Resolution: Design Document

**Batch**: B6  
**Theme**: Calendar Conflict Resolution  
**Prerequisite Batches**: B2 (A36 voice grammar uses session infrastructure from B2)  
**Gates**: B8 (QB conflict resolution explicitly reuses B6's diff/staleness/auto-expiry patterns)  
**Estimated Effort**: 11–14 days  
**Test Subfolder**: `tests/batch_b6/`  
**Design Status**: READY FOR IMPLEMENTATION  
**Produced**: 2026-05-01  

---

## PRE-WORK VERIFICATION SUMMARY

All six input reads completed before this document was written.

| Read | Source | Status |
|:---|:---|:---|
| READ 1 | `pilot-app-mvp-backend-impl-plan.md` §B6 (lines 525–555) | ✅ Complete |
| READ 2 | `frontend-backend-mvp-additions-latest.md` A32–A36 (lines 1027–1186) | ✅ Complete |
| READ 3 | `mvp-arch.md` §13.5, §16.1–16.5 | ✅ Complete |
| READ 4 | `pilot-python-engineer-methods.md` §16.1–16.5 (workflow patterns) | ✅ Complete |
| READ 5 | Live MCP queries on `calendar_sync_conflict`, `tenant_settings`, `notification_outbox` | ✅ Complete |
| READ 6 | `calendar_integration.py`, `voice_action_router.py`, `scheduling.py`, `calendar_sync.py`, `db_models_map.md`, `permissions.py` | ✅ Complete |

---

## A. MIGRATION PLAN

### Live Schema State Verified (MCP Queries)

**`calendar_sync_conflict` — current live columns (12 total):**

| Column | Type | Nullable | Default |
|:---|:---|:---|:---|
| `created_at` | `TIMESTAMPTZ` | NO | — |
| `updated_at` | `TIMESTAMPTZ` | NO | — |
| `created_by` | `UUID` | YES | NULL |
| `updated_by` | `UUID` | YES | NULL |
| `id` | `UUID` | NO | — |
| `tenant_id` | `UUID` | NO | — |
| `job_id` | `UUID` | NO | — |
| `local_snapshot` | `JSONB` | NO | — |
| `remote_snapshot` | `JSONB` | NO | — |
| `resolution` | `TEXT` | YES | NULL |
| `resolved_by_user_id` | `UUID` | YES | NULL |
| `resolved_at` | `TIMESTAMPTZ` | YES | NULL |

**`tenant_settings` — current live columns (17 total):** `created_at`, `updated_at`, `created_by`, `updated_by`, `tenant_id`, `default_labor_rate_cents`, `default_billable_labor_rate_cents`, `default_quote_validity_days`, `default_invoice_terms_days`, `require_approval_for_tech_quotes`, `max_discount_pct_owner`, `tech_color_palette`, `report_chart_threshold`, `etc_variance_owner_notify_pct`, `etc_variance_note_required_pct`, `margin_bucket_boundaries`, `margin_target_pct`.

**Existing indexes on `calendar_sync_conflict`:**
- `idx_calendar_sync_conflict_pending` (partial, `WHERE resolution IS NULL`) ✅ exists
- `idx_csc_tenant` ✅ exists
- `pk_calendar_sync_conflict` ✅ exists

---

### Migration 1: `phase_fe_1_batch_b6_calendar_conflict_diff_payload`

**Scope**: A32 — Add diff-payload columns to `calendar_sync_conflict`.

**New columns (ALL confirmed absent from live DB):**

| Column | Type | Nullable | Default | FK |
|:---|:---|:---|:---|:---|
| `conflict_type` | `TEXT` | NO | `'modified_modified'` (backfill then lock) | — |
| `base_snapshot` | `JSONB` | YES | NULL | — |
| `pilot_modified_by_user_id` | `UUID` | YES | NULL | → `user.id` SET NULL |
| `pilot_modified_at` | `TIMESTAMPTZ` | NO | backfill `created_at` then lock | — |
| `external_modified_at` | `TIMESTAMPTZ` | NO | backfill `created_at` then lock | — |
| `urgency_score` | `INTEGER` | YES | NULL | — |
| `auto_resolved_stale` | `BOOLEAN` | NO | `false` | — |

**Resolution on `related_job_id`**: The arch doc §13.5 references `related_job_id`; the live model uses `job_id NOT NULL`. These are the same semantic field. `job_id` already exists on `calendar_sync_conflict` and is NOT NULL. **Do NOT add `related_job_id`**. All design references to `related_job_id` map to the existing `job_id` column.

**Check constraint additions:**
```sql
ALTER TABLE calendar_sync_conflict
  ADD CONSTRAINT ck_csc_conflict_type
  CHECK (conflict_type IN ('modified_modified', 'deleted_modified', 'modified_deleted'));

ALTER TABLE calendar_sync_conflict
  DROP CONSTRAINT IF EXISTS ck_resolution;
ALTER TABLE calendar_sync_conflict
  ADD CONSTRAINT ck_resolution
  CHECK (
    resolution IS NULL OR
    resolution IN (
      'accept_local', 'accept_remote',
      'restore_from_calendar', 'delete_calendar_too',
      'recreate_calendar_event', 'delete_pilot_job'
    )
  );
```

**New index:**
```sql
CREATE INDEX idx_csc_urgency_pending
  ON calendar_sync_conflict (tenant_id, urgency_score DESC NULLS LAST)
  WHERE resolution IS NULL;
```

**Migration pattern** (3-part additive per §16.2):
```python
def upgrade() -> None:
    # conflict_type: add nullable, backfill, lock NOT NULL
    op.add_column('calendar_sync_conflict', sa.Column('conflict_type', sa.Text(), nullable=True))
    op.execute("UPDATE calendar_sync_conflict SET conflict_type = 'modified_modified' WHERE conflict_type IS NULL")
    op.alter_column('calendar_sync_conflict', 'conflict_type', nullable=False)
    op.execute("ALTER TABLE calendar_sync_conflict ADD CONSTRAINT ck_csc_conflict_type CHECK (conflict_type IN ('modified_modified','deleted_modified','modified_deleted'))")

    # base_snapshot: nullable JSONB
    op.add_column('calendar_sync_conflict', sa.Column('base_snapshot', postgresql.JSONB(), nullable=True))

    # pilot_modified_by_user_id: nullable UUID FK
    op.add_column('calendar_sync_conflict', sa.Column('pilot_modified_by_user_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_csc_pilot_modified_by', 'calendar_sync_conflict', 'user', ['pilot_modified_by_user_id'], ['id'], ondelete='SET NULL')

    # pilot_modified_at: add nullable, backfill created_at, lock NOT NULL
    op.add_column('calendar_sync_conflict', sa.Column('pilot_modified_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE calendar_sync_conflict SET pilot_modified_at = created_at WHERE pilot_modified_at IS NULL")
    op.alter_column('calendar_sync_conflict', 'pilot_modified_at', nullable=False)

    # external_modified_at: add nullable, backfill created_at, lock NOT NULL
    op.add_column('calendar_sync_conflict', sa.Column('external_modified_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE calendar_sync_conflict SET external_modified_at = created_at WHERE external_modified_at IS NULL")
    op.alter_column('calendar_sync_conflict', 'external_modified_at', nullable=False)

    # urgency_score: nullable INT
    op.add_column('calendar_sync_conflict', sa.Column('urgency_score', sa.Integer(), nullable=True))

    # auto_resolved_stale: NOT NULL BOOLEAN DEFAULT false
    op.add_column('calendar_sync_conflict', sa.Column('auto_resolved_stale', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    # Drop old resolution constraint, add extended one
    op.execute("ALTER TABLE calendar_sync_conflict DROP CONSTRAINT IF EXISTS ck_resolution")
    op.execute("""
        ALTER TABLE calendar_sync_conflict ADD CONSTRAINT ck_resolution
        CHECK (resolution IS NULL OR resolution IN (
          'accept_local','accept_remote',
          'restore_from_calendar','delete_calendar_too',
          'recreate_calendar_event','delete_pilot_job'
        ))
    """)

    # New index for urgency-sorted pending list
    op.execute("""
        CREATE INDEX idx_csc_urgency_pending
          ON calendar_sync_conflict (tenant_id, urgency_score DESC NULLS LAST)
          WHERE resolution IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_csc_urgency_pending")
    op.execute("ALTER TABLE calendar_sync_conflict DROP CONSTRAINT IF EXISTS ck_resolution")
    op.execute("""
        ALTER TABLE calendar_sync_conflict ADD CONSTRAINT ck_resolution
        CHECK (resolution IS NULL OR resolution IN ('accept_local','accept_remote'))
    """)
    op.drop_column('calendar_sync_conflict', 'auto_resolved_stale')
    op.drop_column('calendar_sync_conflict', 'urgency_score')
    op.drop_column('calendar_sync_conflict', 'external_modified_at')
    op.drop_column('calendar_sync_conflict', 'pilot_modified_at')
    op.drop_constraint('fk_csc_pilot_modified_by', 'calendar_sync_conflict', type_='foreignkey')
    op.drop_column('calendar_sync_conflict', 'pilot_modified_by_user_id')
    op.drop_column('calendar_sync_conflict', 'base_snapshot')
    op.execute("ALTER TABLE calendar_sync_conflict DROP CONSTRAINT IF EXISTS ck_csc_conflict_type")
    op.drop_column('calendar_sync_conflict', 'conflict_type')
```

---

### Migration 2: `phase_fe_1_batch_b6_tenant_settings_auto_expiry`

**Scope**: A34 — Add auto-expiry configuration columns to `tenant_settings`.

**New columns (ALL confirmed absent from live DB):**

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `calendar_conflict_auto_expire_enabled` | `BOOLEAN` | NO | `true` | On/off switch; FALSE disables for tenant |
| `calendar_conflict_auto_expire_days` | `INTEGER` | YES | NULL | NULL = inherit system default (30 days) |
| `calendar_conflict_pre_warning_days` | `INTEGER` | YES | NULL | NULL = inherit system default (7 days) |

**Validation constraint:**
```sql
ALTER TABLE tenant_settings ADD CONSTRAINT ck_ts_calendar_conflict_days
  CHECK (
    calendar_conflict_auto_expire_days IS NULL OR
    calendar_conflict_pre_warning_days IS NULL OR
    calendar_conflict_pre_warning_days < calendar_conflict_auto_expire_days
  );
```

**Migration pattern:**
```python
def upgrade() -> None:
    op.add_column('tenant_settings', sa.Column(
        'calendar_conflict_auto_expire_enabled',
        sa.Boolean(), server_default=sa.text('true'), nullable=False
    ))
    op.add_column('tenant_settings', sa.Column('calendar_conflict_auto_expire_days', sa.Integer(), nullable=True))
    op.add_column('tenant_settings', sa.Column('calendar_conflict_pre_warning_days', sa.Integer(), nullable=True))
    op.execute("""
        ALTER TABLE tenant_settings ADD CONSTRAINT ck_ts_calendar_conflict_days
        CHECK (
          calendar_conflict_auto_expire_days IS NULL OR
          calendar_conflict_pre_warning_days IS NULL OR
          calendar_conflict_pre_warning_days < calendar_conflict_auto_expire_days
        )
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE tenant_settings DROP CONSTRAINT IF EXISTS ck_ts_calendar_conflict_days")
    op.drop_column('tenant_settings', 'calendar_conflict_pre_warning_days')
    op.drop_column('tenant_settings', 'calendar_conflict_auto_expire_days')
    op.drop_column('tenant_settings', 'calendar_conflict_auto_expire_enabled')
```

---

### Migration 3: `phase_fe_1_batch_b6_calendar_rate_limit_index`

**Scope**: A35 — Rate-limit dedup requires a fast lookup for conflict-detection notifications per tenant per hour.

**New index on `notification_outbox`** (table confirmed in live DB with `tenant_id`, `created_at`, `contextdata` columns):
```sql
CREATE INDEX idx_notif_outbox_tenant_type_hour
  ON notification_outbox (tenant_id, created_at DESC)
  WHERE channel = 'push';
```

**No new columns required** — rate-limit counter is computed at query time from existing `notification_outbox` rows.

```python
def upgrade() -> None:
    op.execute("""
        CREATE INDEX idx_notif_outbox_tenant_type_hour
          ON notification_outbox (tenant_id, created_at DESC)
          WHERE channel = 'push'
    """)

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_notif_outbox_tenant_type_hour")
```

---

## B. EXECUTION ORDER

| # | Item | Rationale |
|:---|:---|:---|
| 1 | **A32** — Calendar Conflict Diff Payload | Schema foundation. A33, A35, and A36 all depend on the new `field_diffs` response shape and the `conflict_type` + `urgency_score` columns. Must land first. |
| 2 | **A33** — Pre-Resolution Staleness Check | Small addition to the resolve endpoint; depends on A32 columns (`pilot_modified_at`, `external_modified_at`) being present in DB. Establishes the canonical staleness shape reused by A45, A48, A50, A62 — build carefully here. |
| 3 | **A34** — Auto-Expiry of Stale Conflicts | Depends on `auto_resolved_stale` from A32 (Migration 1) and the new `tenant_settings` columns (Migration 2). Creates `system_config.py` — new platform infrastructure. Must precede A35 which reads effective expiry count. |
| 4 | **A35** — Mobile Pending-Conflicts Status & Rate Limiting | Extends `GET /api/v1/integrations/calendar/status`. Rate-limit index (Migration 3) must be deployed. Depends on A32 (conflict query reads `urgency_score`). |
| 5 | **A36** — Voice Intent Grammar for Conflict Resolution | Last: depends on A32 diff payload (voice readback renders from `field_diffs`), A33 staleness check (voice handler catches 409), and A35 `list_pending_calendar_conflicts` pathway which reads pending count. |

---

## C. NEW API ENDPOINTS

### C.1 — A32: `GET /api/v1/integrations/calendar/conflicts`

**Purpose**: List pending calendar sync conflicts, urgency-sorted.

**Auth**: JWT required  
**RBAC**: `integrations.manage` (via `require_permission("integrations.manage")`)

**Request**: No body. Optional query params:
```
?status=pending|resolved|all   (default: pending)
?cursor=<opaque>               (cursor-based pagination per §7.8)
?limit=<int>                   (default 20, max 100)
```

**Response** `200 OK`:
```json
{
  "conflicts": [
    {
      "id": "uuid",
      "conflict_type": "modified_modified",
      "job_id": "uuid",
      "job_title": "Panel Upgrade — Johnson",
      "scheduled_start_at": "2026-05-10T09:00:00Z",
      "urgency_score": 3,
      "pilot_modified_at": "2026-05-01T14:00:00Z",
      "external_modified_at": "2026-05-01T15:30:00Z",
      "resolution": null,
      "detected_at": "2026-05-01T15:35:00Z"
    }
  ],
  "next_cursor": "opaque_cursor_string",
  "total_pending": 4
}
```

---

### C.2 — A32: `GET /api/v1/integrations/calendar/conflicts/{id}`

**Purpose**: Detail view with server-computed field-level diff.

**Auth**: JWT required  
**RBAC**: `integrations.manage`

**Response** `200 OK`:
```json
{
  "id": "uuid",
  "conflict_type": "modified_modified",
  "job_id": "uuid",
  "job_title": "Panel Upgrade — Johnson",
  "scheduled_start_at": "2026-05-10T09:00:00Z",
  "urgency_score": 3,
  "pilot_modified_by_user_id": "uuid",
  "pilot_modified_by_name": "Tom Lang",
  "pilot_modified_at": "2026-05-01T14:00:00Z",
  "external_modified_at": "2026-05-01T15:30:00Z",
  "resolution": null,
  "resolved_by_user_id": null,
  "resolved_at": null,
  "auto_resolved_stale": false,
  "pilot_snapshot": { ... },
  "external_snapshot": { ... },
  "base_snapshot": { ... },
  "field_diffs": [
    {
      "field_name": "scheduled_start_at",
      "pilot_value": "2026-05-10T09:00:00Z",
      "external_value": "2026-05-10T10:00:00Z",
      "base_value": "2026-05-10T09:00:00Z",
      "pilot_change": "unchanged",
      "external_change": "modified"
    },
    {
      "field_name": "site_address",
      "pilot_value": "742 Main St",
      "external_value": null,
      "base_value": "742 Main St",
      "pilot_change": "unchanged",
      "external_change": "removed"
    }
  ]
}
```

---

### C.3 — A33: `POST /api/v1/integrations/calendar/conflicts/{id}/resolve`

**Purpose**: Resolve a conflict with staleness guard.

**Auth**: JWT required  
**RBAC**: `integrations.manage`

**Request body**:
```json
{
  "resolution": "accept_local | accept_remote | restore_from_calendar | delete_calendar_too | recreate_calendar_event | delete_pilot_job",
  "expected_pilot_modified_at": "2026-05-01T14:00:00Z",
  "expected_external_modified_at": "2026-05-01T15:30:00Z"
}
```

**Response** `200 OK` (success):
```json
{
  "id": "uuid",
  "resolution": "accept_local",
  "resolved_at": "2026-05-01T18:00:00Z",
  "resolved_by_user_id": "uuid"
}
```

**Response** `409 Conflict` (staleness detected — A33 canonical pattern):
```json
{
  "type": "https://pilotfortrades.com/errors/conflict-stale",
  "title": "Conflict State Has Changed",
  "status": 409,
  "detail": "The conflict was modified since you last viewed it. Review the updated diff and re-submit.",
  "refreshed_conflict": { ... /* same shape as GET /conflicts/{id} response */ }
}
```

**Resolution-type validation**: Endpoint validates that the requested `resolution` is legal for the `conflict_type`:

| `conflict_type` | Legal resolutions |
|:---|:---|
| `modified_modified` | `accept_local`, `accept_remote` |
| `deleted_modified` | `restore_from_calendar`, `delete_calendar_too` |
| `modified_deleted` | `recreate_calendar_event`, `delete_pilot_job` |

---

### C.4 — A35: `GET /api/v1/integrations/calendar/status` (extended)

**Purpose**: Extend existing endpoint for mobile Owner tab "Calendar sync" row.

**Auth**: JWT required  
**RBAC**: `integrations.view` (existing permission)

**Current response shape** (live): `is_connected`, `provider_code`, `sync_status`, `connected_at`, `token_expires_at`, `last_sync_at`

**Extended response** — new fields added (non-breaking):
```json
{
  "is_connected": true,
  "provider_code": "google",
  "sync_status": "active",
  "connection_status": "connected",
  "connected_at": "2026-04-01T10:00:00Z",
  "token_expires_at": "2026-05-02T10:00:00Z",
  "last_sync_at": "2026-05-01T18:00:00Z",
  "last_successful_sync_at": "2026-05-01T18:00:00Z",
  "pending_conflicts_count": 3,
  "requires_reconnect": false
}
```

New fields:
- `connection_status`: `"connected" | "syncing" | "error" | "disconnected"` — mapped from `sync_status`
- `last_successful_sync_at`: last `calendar_sync_log` entry with `status = 'success'`
- `pending_conflicts_count`: COUNT of `calendar_sync_conflict` WHERE `resolution IS NULL AND tenant_id = $1`
- `requires_reconnect`: `true` when `sync_status = 'error'` and token-related error code

---

### C.5 — A36 Voice: No new HTTP endpoints

A36 adds two intents to `backend/services/voice_action_router.py` (`INTENT_HANDLERS` dict). Voice commands route through the existing `POST /api/v1/voice/command` endpoint — no new HTTP route needed. See Section E for handler signatures.

---

## D. PATTERN REUSE DECISIONS

### D.1 — §16.2 Track-Changes Diff Vocabulary (A32)

**Pattern**: `mvp-arch.md §16.2`  
**Applied to**: A32 `field_diffs` payload shape.

The `field_diffs` array uses the platform-standard vocabulary:
- `pilot_change` / `external_change` enum: `unchanged | modified | added | removed`
- Amber = `modified`, Green = `added`, Red = `removed`

Server-side diff is computed in `CalendarConflictService.compute_field_diffs(local_snapshot, remote_snapshot, base_snapshot)`. The same payload drives both the web diff view and A36 voice readback — consistency is guaranteed because both render from the same JSONB stored at detection time.

---

### D.2 — §16.4 Pre-Commit Staleness Check (A33)

**Pattern**: `mvp-arch.md §16.4`, `mvp-arch.md §7.9`  
**Applied to**: A33 resolve endpoint.  
**Pattern checklist** (per §16.4):

1. Version fields: `pilot_modified_at` + `external_modified_at` (two-field version, both required)
2. Accept `expected_pilot_modified_at` + `expected_external_modified_at` on `POST .../resolve`
3. Re-query conflict at write time; compare both timestamps
4. Mismatch → 409 with `refreshed_conflict` payload (same shape as GET detail)
5. OpenAPI spec documents both parameters with ISO 8601 format
6. Client handler: refresh diff view, surface "conflict updated" banner, owner re-decides

**Canonical shape** (reused verbatim by A45/B7b, A48/B8, A50/B8, A62/B11):
```python
async def _check_staleness(
    conflict: CalendarSyncConflict,
    expected_pilot_modified_at: datetime,
    expected_external_modified_at: datetime,
) -> bool:
    """Returns True if stale (caller should return 409)."""
    return (
        conflict.pilot_modified_at != expected_pilot_modified_at
        or conflict.external_modified_at != expected_external_modified_at
    )
```

---

### D.3 — §16.5 System Default + Tenant Override Two-Tier Configuration (A34)

**Pattern**: `mvp-arch.md §16.5`  
**Applied to**: A34 auto-expiry settings.

B6 is the **first batch to instantiate this pattern in code**. `system_config.py` does not exist in the codebase (confirmed by search). B6 creates it at `backend/core/system_config.py`.

Effective-value resolution function (see Section E for full interface):
```python
def get_effective_setting(tenant_settings, key, system_default):
    ...
```

Specifically for calendar conflict auto-expiry, the three-step resolution per A34 clarification:
1. If `calendar_conflict_auto_expire_enabled = FALSE` → skip auto-expiry entirely
2. If `TRUE` → use `calendar_conflict_auto_expire_days` (NULL → system default 30)
3. Pre-warning at `(auto_expire_days - pre_warning_days)` (NULL pre-warning → system default 7)

**CRITICAL distinction** (per B6 test focus): NULL tenant value = "use system default"; `auto_expire_enabled = FALSE` = "disable entirely". These are distinct code paths.

---

### D.4 — §16.3 Confirm-as-Turn for Destructive Voice Actions (A36)

**Pattern**: `mvp-arch.md §16.3`, `mvp-arch.md §6.6`  
**Applied to**: A36 `resolve_calendar_conflict` voice intent.

Reuses the exact pattern from `delete_session_via_voice()` (lines 2207–2343 of `backend/services/voice_action_router.py`):

```python
# Turn 1: Write pending_confirmation, return requires_confirmation=True
ctx_dict["pending_confirmation"] = {
    "action": "resolve_calendar_conflict",
    "conflict_id": str(conflict.id),
    "resolution": resolution_side,
    "expected_pilot_modified_at": conflict.pilot_modified_at.isoformat(),
    "expected_external_modified_at": conflict.external_modified_at.isoformat(),
    "summary_prompt": server_rendered_summary,
}
session.context_window_json = ctx_dict

# Turn 2: Check pending, execute resolve, clear pending_confirmation
pending = context.get("pending_confirmation", {})
if pending.get("action") == "resolve_calendar_conflict":
    # call resolve endpoint logic + staleness check
    ctx_dict.pop("pending_confirmation", None)
    session.context_window_json = ctx_dict
```

**Staleness race in A36**: if A33 returns 409 between Turn 1 and Turn 2, the handler announces "the conflict has changed since you last looked at it — opening the diff view on web" and pushes a deep link via `notification_outbox`.

---

### D.5 — §16.9 Mobile Owner Status Row + Deep-Link (A35)

**Pattern**: `mvp-arch.md §16.9`  
**Applied to**: A35 `GET /api/v1/integrations/calendar/status` extension.

The extended status response feeds the mobile Owner tab "Calendar sync" row. Pattern established in Pass 2 for QuickBooks. B6 extends the calendar endpoint to match parity.

---

### D.6 — Python Engineer Methods §16.2 — 4-Step Execution Loop

**Applied to all B6 items**. Mandatory order per methods doc:
1. ORM model updates in `backend/app/models/scheduling.py` and `backend/app/models/core.py`
2. Manual Alembic migration (never autogenerate)
3. Master Blueprint JSON sync (`dev-docs/db-design/pilot-db-schema-v2.6h.json`)
4. Service/route implementation + tests

---

## E. SHARED MODULE INTERFACES

### E.1 — `backend/core/system_config.py` (NEW — A34)

**Purpose**: System-level defaults for two-tier configuration pattern. First instantiation of `mvp-arch.md §16.5` in backend code.

```python
"""
System-level configuration constants for platform-wide two-tier settings.

All values are loaded from environment variables with hard-coded fallback
constants. Phase 2 will upgrade this to an admin-tier DB table.

Usage:
    from core.system_config import SystemConfig
    expire_days = SystemConfig.CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS
"""


class SystemConfig:
    """Platform-wide system defaults for two-tier settings (§16.5)."""

    # Calendar conflict auto-expiry
    CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS: int = int(
        os.environ.get("SYSTEM_CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS", "30")
    )
    CALENDAR_CONFLICT_PRE_WARNING_DAYS: int = int(
        os.environ.get("SYSTEM_CALENDAR_CONFLICT_PRE_WARNING_DAYS", "7")
    )
```

---

### E.2 — `backend/services/calendar_conflict_service.py` (NEW — A32, A33, A34, A35)

**Purpose**: All calendar conflict business logic extracted from routes into a dedicated service.

```python
"""
Calendar Conflict Resolution Service

Provides diff computation, staleness checking, resolution execution,
effective-setting resolution for auto-expiry, and notification rate-limit
enforcement.

Referenced by:
  - backend/api/routes/calendar_integration.py (A32, A33, A35)
  - backend/tasks/expire_stale_calendar_conflicts.py (A34)
  - backend/services/voice_action_router.py (A36)
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.models.scheduling import CalendarSyncConflict
from app.models.core import TenantSettings
from app.models.system import NotificationOutbox
from core.system_config import SystemConfig
from sqlmodel import Session, select


class FieldDiff:
    """Single field-level diff entry for the field_diffs payload (§16.2)."""

    field_name: str
    pilot_value: Any
    external_value: Any
    base_value: Any
    pilot_change: str    # 'unchanged' | 'modified' | 'added' | 'removed'
    external_change: str # 'unchanged' | 'modified' | 'added' | 'removed'


class CalendarConflictService:

    @staticmethod
    def compute_field_diffs(
        pilot_snapshot: Dict[str, Any],
        external_snapshot: Dict[str, Any],
        base_snapshot: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Compute server-side field-level diff from three snapshots.

        Returns a list of FieldDiff dicts. Called at conflict-detection time
        and stored implicitly (computed on GET, not stored in DB — consistent
        because inputs are stored JSONB snapshots).

        Note: local_snapshot = pilot_snapshot, remote_snapshot = external_snapshot
        in the live model field naming.

        Args:
            pilot_snapshot: Current Pilot state at detection (local_snapshot).
            external_snapshot: Current calendar state at detection (remote_snapshot).
            base_snapshot: Last shared state before conflict (may be None for legacy rows).

        Returns:
            List of field diff dicts conforming to §16.2 vocabulary.
        """
        ...

    @staticmethod
    def check_staleness(
        conflict: CalendarSyncConflict,
        expected_pilot_modified_at: datetime,
        expected_external_modified_at: datetime,
    ) -> bool:
        """
        A33 canonical staleness check pattern.

        Returns True if the conflict has been modified since the client last viewed it.
        Caller returns HTTP 409 with refreshed conflict payload when True.

        Reused verbatim by: A45 (B7b), A48 (B8), A50 (B8), A62 (B11).
        """
        return (
            conflict.pilot_modified_at != expected_pilot_modified_at
            or conflict.external_modified_at != expected_external_modified_at
        )

    @staticmethod
    def get_effective_expire_days(tenant_settings: Optional[TenantSettings]) -> Optional[int]:
        """
        A34 two-tier resolution for auto-expire days (§16.5).

        Resolution chain:
          1. If tenant_settings is None or auto_expire_enabled is False → return None (disabled)
          2. If calendar_conflict_auto_expire_days is not None → return tenant override
          3. Return SystemConfig.CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS (system default 30)

        Returns:
            int: effective expire days, or None if auto-expiry is disabled.
        """
        if tenant_settings is None:
            return SystemConfig.CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS
        if not tenant_settings.calendar_conflict_auto_expire_enabled:
            return None  # explicitly disabled
        if tenant_settings.calendar_conflict_auto_expire_days is not None:
            return tenant_settings.calendar_conflict_auto_expire_days
        return SystemConfig.CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS

    @staticmethod
    def get_effective_pre_warning_days(tenant_settings: Optional[TenantSettings]) -> Optional[int]:
        """
        A34 two-tier resolution for pre-warning days (§16.5).

        Returns:
            int: effective pre-warning days, or None if disabled.
        """
        if tenant_settings is None:
            return SystemConfig.CALENDAR_CONFLICT_PRE_WARNING_DAYS
        if not tenant_settings.calendar_conflict_auto_expire_enabled:
            return None
        if tenant_settings.calendar_conflict_pre_warning_days is not None:
            return tenant_settings.calendar_conflict_pre_warning_days
        return SystemConfig.CALENDAR_CONFLICT_PRE_WARNING_DAYS

    @staticmethod
    def count_recent_conflict_notifications(
        db: Session,
        tenant_id: UUID,
        window_hours: int = 1,
    ) -> int:
        """
        A35 rate-limit check: count push notifications for conflict-detection
        events in the last `window_hours` for a tenant.

        Rate limit: max 4 per tenant per hour. Fifth+ collapse to batched notification.

        Args:
            db: Active SQLModel session.
            tenant_id: Tenant to check.
            window_hours: Look-back window in hours (default 1).

        Returns:
            int: count of conflict-detection push notifications in window.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
        # Query notification_outbox for calendar_conflict_detected notifications
        # filtered by tenant_id and created_at > cutoff
        ...

    @staticmethod
    def get_pending_conflicts_count(db: Session, tenant_id: UUID) -> int:
        """
        Return count of unresolved calendar_sync_conflict rows for a tenant.
        Used by A35 status endpoint extension.
        """
        from sqlmodel import func
        return db.exec(
            select(func.count(CalendarSyncConflict.id)).where(
                CalendarSyncConflict.tenant_id == tenant_id,
                CalendarSyncConflict.resolution.is_(None),  # type: ignore[attr-defined]
            )
        ).one()

    @staticmethod
    def validate_resolution_for_conflict_type(
        conflict_type: str,
        resolution: str,
    ) -> bool:
        """
        Validate that the requested resolution action is legal for this conflict type.

        Returns True if valid.
        """
        LEGAL_RESOLUTIONS = {
            "modified_modified": {"accept_local", "accept_remote"},
            "deleted_modified": {"restore_from_calendar", "delete_calendar_too"},
            "modified_deleted": {"recreate_calendar_event", "delete_pilot_job"},
        }
        return resolution in LEGAL_RESOLUTIONS.get(conflict_type, set())

    @staticmethod
    def build_voice_readback_summary(
        conflict: CalendarSyncConflict,
        field_diffs: List[Dict[str, Any]],
        chosen_side: str,  # 'pilot' | 'external'
    ) -> str:
        """
        A36 server-side voice readback copy template.

        Renders the confirm-as-turn spoken summary from the field_diffs payload
        (same data that drives the visual diff — ensures web/voice consistency).

        Template:
          "Accepting the {side} version of {conflict_identifier}.
           That keeps: {summary of chosen side}.
           That discards: {summary of rejected side}.
           Confirm?"

        Args:
            conflict: The CalendarSyncConflict record.
            field_diffs: Pre-computed field diffs from compute_field_diffs().
            chosen_side: Which side the owner wants to keep ('pilot' or 'external').

        Returns:
            str: Spoken confirmation prompt for the AI to read.
        """
        ...
```

---

### E.3 — `backend/tasks/expire_stale_calendar_conflicts.py` (NEW — A34)

```python
"""
Celery Beat task: expire_stale_calendar_conflicts

Daily task that:
  1. Iterates all tenants with active calendar integrations
  2. Resolves effective expire_days and pre_warning_days per tenant (two-tier)
  3. Sends pre-warning notification at (expire_days - pre_warning_days)
  4. Auto-resolves conflicts >= expire_days old to 'accept_local'
  5. Flags auto_resolved_stale = TRUE on resolved rows
  6. Logs auto-resolution to calendar_sync_log

Registration: added to core/celery_app.py beat schedule.
"""

from core.celery_app import celery_app


@celery_app.task(name="tasks.expire_stale_calendar_conflicts")
def expire_stale_calendar_conflicts() -> dict:
    """
    Daily Celery Beat task for calendar conflict auto-expiry (A34).

    Returns:
        dict: {"expired": int, "pre_warned": int, "tenants_processed": int}
    """
    ...
```

**Beat registration** in `backend/core/celery_app.py`:
```python
"expire-stale-calendar-conflicts": {
    "task": "tasks.expire_stale_calendar_conflicts",
    "schedule": crontab(hour=2, minute=0),  # daily at 02:00 UTC
},
```

---

### E.4 — A36 Voice Handler Signatures (additions to `backend/services/voice_action_router.py`)

Two new async handlers added to `backend/services/voice_action_router.py`:

```python
async def list_pending_calendar_conflicts_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> Dict[str, Any]:
    """
    A36: 'list_pending_calendar_conflicts' intent handler.

    Read-only. AI announces count + urgency summary. No confirm-as-turn needed
    (read-only operation).

    Example response message:
      "You have 3 pending calendar conflicts. The most urgent is the Johnson
       panel upgrade on May 10th — both Pilot and Google Calendar changed it."

    Returns:
        Standard voice action response dict with action='list_pending_calendar_conflicts'.
    """
    ...


async def resolve_calendar_conflict_via_voice(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> Dict[str, Any]:
    """
    A36: 'resolve_calendar_conflict' intent handler.

    Implements confirm-as-turn pattern (§16.3) matching delete_session_via_voice().
    Turn 1: identifier match → disambiguation if needed → write pending_confirmation
            → return spoken summary with 'pending_confirmation': True.
    Turn 2: affirmative detected → call resolve logic with staleness check (A33)
            → 409 branch: announce change + push deep link → clear pending_confirmation.

    Refusal-with-redirect for:
      - Deletion conflicts (conflict_type in {'deleted_modified','modified_deleted'})
      - Multi-resolve attempts ("resolve all")
      - Field-level edits ("change the time to 3pm")

    Returns:
        Standard voice action response dict with action='resolve_calendar_conflict'.
    """
    ...
```

**INTENT_HANDLERS additions** (lines appended to existing dict):
```python
# A36: Calendar Conflict Resolution voice intents (B6)
"list_pending_calendar_conflicts": list_pending_calendar_conflicts_via_voice,
"resolve_calendar_conflict": resolve_calendar_conflict_via_voice,
```

---

## F. OPEN QUESTIONS RESOLVED

### F.1 — `related_job_id` vs `job_id`

**Question**: Arch doc §13.5 shows `related_job_id UUID NULL`; live model has `job_id UUID NOT NULL`. Are these different columns?

**Decision**: They are the same field. The live `calendar_sync_conflict.job_id` (NOT NULL) IS the `related_job_id` referenced in A32 spec. **Do not add a new column.** All design references to `related_job_id` resolve to `job_id` in code. The `job_id` FK is already `→ job.id ON DELETE RESTRICT`.

---

### F.2 — `local_snapshot` / `remote_snapshot` vs `pilot_snapshot` / `external_snapshot`

**Question**: A32 uses `pilot_snapshot` and `external_snapshot`; live DB has `local_snapshot` and `remote_snapshot`. Do we rename?

**Decision**: **Do not rename.** Column renames are high-risk and require multi-step migrations with code changes to all readers. The live columns `local_snapshot` = pilot state, `remote_snapshot` = calendar state. Internally `CalendarConflictService.compute_field_diffs()` maps these correctly. The API response uses the `pilot_snapshot`/`external_snapshot` naming for frontend clarity — the service layer translates on read.

---

### F.3 — `detected_at` column

**Question**: Arch doc §13.5 lists `detected_at TIMESTAMPTZ NOT NULL` as a distinct column; live model does not have it.

**Decision**: `created_at` from `StandardAuditMixin` serves as `detected_at`. Conflicts are created at detection time; `created_at` is immutable after insert. **Do not add a separate `detected_at` column.** API responses that need `detected_at` expose `created_at` as `detected_at` in the Pydantic schema.

---

### F.4 — `system_config.py` does not exist

**Question**: A34 requires `system_config.py` for system defaults — does it already exist?

**Decision**: Confirmed absent (search across `backend/**/*.py` returned zero results for `SystemConfig`, `system_config`, `SYSTEM_CALENDAR`). **B6 creates `backend/core/system_config.py`** as the first instantiation of the §16.5 two-tier pattern. File is intentionally simple for MVP: typed class constants loaded from environment variables with hard-coded fallbacks. Phase 2 upgrades to a DB-backed admin table.

---

### F.5 — Rate-limit storage for A35 (where is the counter?)

**Question**: A35 requires "max 4 conflict-detection notifications per tenant per hour". Where is the counter persisted?

**Decision**: **No separate counter table.** The counter is derived at query time from existing `notification_outbox` rows filtered by `tenant_id`, `channel = 'push'`, `created_at > NOW() - 1h`, and `contextdata->>'event_type' = 'calendar_conflict_detected'`. The new index `idx_notif_outbox_tenant_type_hour` (Migration 3) makes this O(tenant-notifications-per-hour). Redis is NOT used here — volume is low (≤100 push notifications per hour across all tenants at MVP scale). If this proves slow at scale, Redis incr can be added without schema changes.

---

### F.6 — Pre-warning dedup for A34 (how to prevent repeated pre-warnings?)

**Question**: How does the `expire_stale_calendar_conflicts` task know a pre-warning has already been sent for a given conflict?

**Decision**: Query `notification_outbox` for an existing pre-warning for `conflict_id` in `contextdata`. If found → skip. The task sets `contextdata->>'conflict_id'` and `contextdata->>'notification_subtype' = 'pre_warning'` when enqueuing. No new column needed on `calendar_sync_conflict`. This approach reuses existing infrastructure and is searchable.

---

### F.7 — Urgency score: computed when?

**Question**: `urgency_score` is described as "derived from related job's `scheduled_start_at` proximity." Is it stored or computed on read?

**Decision**: **Stored at conflict-detection time** and updated daily by the `expire_stale_calendar_conflicts` task. Rationale: conflicts are listed by urgency score frequently (every time the conflicts list is opened). Recomputing on every list request would require a JOIN to `job` on every page. The daily task re-scores conflicts as jobs' `scheduled_start_at` approaches. Score formula: `FLOOR(EXTRACT(epoch FROM (job.scheduled_start_at - NOW())) / 86400)` clamped to 0–100 (lower = more urgent; NULL for past-dated or unscheduled jobs).

---

### F.8 — Resolution constraint expansion (A32)

**Question**: The existing `ck_resolution` check constraint only allows `accept_local | accept_remote | NULL`. A32 adds four new resolution variants. How to update the constraint?

**Decision**: Migration 1 DROPs the existing `ck_resolution` constraint and re-creates it with all six resolution variants. The migration downgrade restores the original two-variant constraint. This is a safe additive change (no existing data uses the new variants; downgrade is safe because new variants only exist for post-B6 data).

---

## G. EXTERNAL DEPENDENCY STATUS

### G.1 — Google Calendar API (A32, A33, A34, A35)

**Dependency**: Conflict detection that populates `base_snapshot`, `pilot_modified_at`, `external_modified_at` runs inside the existing `pull_calendar_blocks_task` in `backend/tasks/calendar_sync.py`.

**Mock strategy**: The existing `calendar_sync.py` task is already mocked in tests via `httpx` patch. B6 extends mock fixtures to return events with modification timestamps. Test fixtures in `tests/batch_b6/fixtures/` provide pre-built conflict rows with all new columns populated.

**Tom must action**: Nothing new — Google Calendar API connection is already implemented. B6 only adds new columns to what the existing sync task writes.

---

### G.2 — `notification_outbox` / Push Notifications (A34, A35, A36)

**Dependency**: Pre-warning notifications and rate-limited conflict notifications write to `notification_outbox`. The `notification_worker` Celery task dispatches them.

**Mock strategy**: `notification_outbox` inserts are testable directly (no external call mocked). Tests assert the row is written with correct `contextdata`, not that the push is delivered.

**Tom must action**: Nothing new for MVP — push delivery is handled by the existing `notification_worker`. Push token infrastructure (APNs/FCM) is a B8 deliverable (A51).

---

### G.3 — Voice AI (Whisper + Ollama on GPU) (A36)

**Dependency**: A36 voice intents are parsed by Ollama's intent classifier. New intents `list_pending_calendar_conflicts` and `resolve_calendar_conflict` must be covered in the Ollama grammar/prompt used for intent classification.

**Mock strategy**: Voice integration tests use the existing `AI_MOCK_RESPONSES` fixture pattern (no live GPU call in CI). Grammar additions require updating the Ollama system prompt with the two new intent names and example utterances (see A36 spec).

**Tom must action**: Update the Ollama system prompt to include the two new intents before production voice testing. Lead time: 1–2 hours (prompt update + GPU instance restart). No external vendor action required.

---

### G.4 — No Stripe / Telnyx / 10DLC / SendGrid dependency

B6 has zero dependency on payment, SMS, or email external providers. All B6 work is self-contained to the calendar conflict domain, the notification_outbox (internal), and the voice AI pipeline (local GPU).

---

*End of Batch B6 Design Document*
