# Batch B7a Design Document — Offline Sync Foundation

**Batch**: B7a  
**Name**: Offline Sync Foundation  
**Items**: A37, A39, A38 (in execution order)  
**Estimated Effort**: 8–11 days  
**Test Subfolder**: `tests/batch_b7a/`  
**Prerequisite Batches**: None (parallel-safe; best started after B3 since B3 establishes the `job_time_entry` model A37 extends)  
**Gates**: B7b (cannot start until B7a schema is confirmed clean)  
**Design Prepared**: 2026-05-01  
**Source Reads Completed**: impl-plan §6.B7a, additions ledger A37/A38/A39, mvp-arch §7.6/§15.2–15.4, pilot-python-engineer-methods §16.1–16.5, live DB via postgres-local MCP, backend source files

---

## A. MIGRATION PLAN

### Live DB State (confirmed via postgres-local MCP on 2026-05-01)

The following tables are confirmed **in the live database** and are the target of `client_capture_at` additions:

| Architecture Name | Actual Table Name | `client_capture_at` Exists? |
|:---|:---|:---|
| `job_time_entry` | `job_time_entry` | ❌ — must add |
| `expense` | `job_expense` | ❌ — must add |
| `photo` | `job_attachment` | ❌ — must add |
| `change_order` | `change_order` | ❌ — must add |
| `job_note` | `job_notes` | ❌ — must add |
| `loto_check` | **NOT IN LIVE DB** | N/A — see §F |
| `job_status_change` | **NOT IN LIVE DB** | N/A — see §F |
| `mobile_sync_event` | **NOT IN LIVE DB** | N/A — new table created in A38 |

All `client_capture_at` columns confirmed **absent** via column-level `information_schema.columns` queries. Safe to add in migration.

---

### Migration 1: `phase_fe_1_batch_b7a_offline_capture_timestamps`

**Scope**: Add `client_capture_at TIMESTAMPTZ NULL` to five offline-capturable tables.  
**Pattern**: Single nullable-add migration — no backfill needed (NULL = not captured offline; existing rows are online-created).

```python
def upgrade() -> None:
    # job_time_entry
    op.add_column(
        'job_time_entry',
        sa.Column('client_capture_at', sa.DateTime(timezone=True), nullable=True)
    )
    # job_expense
    op.add_column(
        'job_expense',
        sa.Column('client_capture_at', sa.DateTime(timezone=True), nullable=True)
    )
    # job_attachment (architecture name: "photo")
    op.add_column(
        'job_attachment',
        sa.Column('client_capture_at', sa.DateTime(timezone=True), nullable=True)
    )
    # change_order
    op.add_column(
        'change_order',
        sa.Column('client_capture_at', sa.DateTime(timezone=True), nullable=True)
    )
    # job_notes (architecture name: "job_note")
    op.add_column(
        'job_notes',
        sa.Column('client_capture_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('job_notes', 'client_capture_at')
    op.drop_column('change_order', 'client_capture_at')
    op.drop_column('job_attachment', 'client_capture_at')
    op.drop_column('job_expense', 'client_capture_at')
    op.drop_column('job_time_entry', 'client_capture_at')
```

**Why nullable, no backfill**: `client_capture_at` semantics are "timestamp the tech captured this event on device." All existing rows were created online (server-side `created_at` == capture time). Setting them to NULL is the correct value — NULL means "captured online." The gap metric (`created_at - client_capture_at`) is undefined for online rows, which is correct. A NOT NULL constraint would be incorrect semantics.

---

### Migration 2: `phase_fe_1_batch_b7a_mobile_sync_event`

**Scope**: Create new `mobile_sync_event` append-only table and its primary index.  
**Mixin**: Uses `AppendOnlyMixin` semantics (no `updated_at`; append-only log). Implemented as a standalone SQLModel table (not inheriting `StandardAuditMixin` to avoid `updated_at` confusion on an immutable log).

```python
def upgrade() -> None:
    op.create_table(
        'mobile_sync_event',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('device_id', sa.Text(), nullable=False),
        sa.Column('operation_type', sa.Text(), nullable=False),
        sa.Column('operation_payload_summary', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('conflict_severity', sa.Text(), nullable=True),
        sa.Column('client_capture_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_detail', postgresql.JSONB(), nullable=True),
        sa.Column('idempotency_uuid', sa.UUID(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id', name='pk_mobile_sync_event'),
        sa.ForeignKeyConstraint(
            ['tenant_id'], ['tenant.id'],
            name='fk_mobile_sync_event_tenant',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], ['user.id'],
            name='fk_mobile_sync_event_user',
            ondelete='RESTRICT',
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'syncing', 'succeeded', 'failed', 'conflict')",
            name='chk_mobile_sync_event_status',
        ),
        sa.CheckConstraint(
            "conflict_severity IS NULL OR conflict_severity IN "
            "('auto_silent', 'auto_notice', 'tech_resolvable', 'owner_escalation')",
            name='chk_mobile_sync_event_conflict_severity',
        ),
    )
    # Primary index: fast per-tech queue queries by status
    op.create_index(
        'ix_mobile_sync_event_tenant_user_status',
        'mobile_sync_event',
        ['tenant_id', 'user_id', 'status'],
    )
    # Secondary index: retention cleanup (archive rows > 30 days)
    op.create_index(
        'ix_mobile_sync_event_created_at',
        'mobile_sync_event',
        ['created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_mobile_sync_event_created_at', table_name='mobile_sync_event')
    op.drop_index('ix_mobile_sync_event_tenant_user_status', table_name='mobile_sync_event')
    op.drop_table('mobile_sync_event')
```

**Column specifications** (from A38 ledger + §15.3 arch, confirmed against no pre-existing table):

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `id` | `UUID` | NOT NULL | — | PK |
| `tenant_id` | `UUID` | NOT NULL | — | FK → `tenant.id` RESTRICT |
| `user_id` | `UUID` | NOT NULL | — | FK → `user.id` RESTRICT |
| `device_id` | `TEXT` | NOT NULL | — | Client-reported device identifier |
| `operation_type` | `TEXT` | NOT NULL | — | `'time_entry'` \| `'expense'` \| `'photo'` \| `'change_order'` \| `'job_note'` \| `'loto_check'` \| `'job_status_change'` \| `'voice_audio'` \| `'clock_in'` \| `'clock_out'` |
| `operation_payload_summary` | `JSONB` | NULL | — | Non-PII summary (amount, job_id, etc.) |
| `status` | `TEXT` | NOT NULL | — | `'pending'` \| `'syncing'` \| `'succeeded'` \| `'failed'` \| `'conflict'` — CHECK constraint enforced |
| `conflict_severity` | `TEXT` | NULL | — | `'auto_silent'` \| `'auto_notice'` \| `'tech_resolvable'` \| `'owner_escalation'` — CHECK constraint enforced |
| `client_capture_at` | `TIMESTAMPTZ` | NOT NULL | — | Device capture timestamp; required for sync events |
| `synced_at` | `TIMESTAMPTZ` | NULL | — | Set when status transitions to `succeeded` |
| `error_detail` | `JSONB` | NULL | — | Set when status transitions to `failed` |
| `idempotency_uuid` | `UUID` | NOT NULL | — | Client-generated UUID v4, matches `Idempotency-Key` header |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Server-side insert timestamp; never updated |

**Append-only enforcement note**: No `updated_at` column. The ORM model must **not** inherit `StandardAuditMixin`. Use `AppendOnlyMixin` or define the model manually. Status transitions are implemented by inserting new rows, not updating existing ones.

---

### Migration 3: `phase_fe_1_batch_b7a_natural_key_dedup_indexes`

**Scope**: Create partial indexes supporting natural-key dedup lookups. These indexes are the performance backstop for the 7-day/30-day offline dedup window — without them, dedup queries become full table scans.

```python
def upgrade() -> None:
    # Time entry natural key: (user_id, job_id, started_at) — 7-day window
    # Note: field is "started_at" in job_time_entry (confirmed live DB)
    op.create_index(
        'ix_jte_natural_key_dedup',
        'job_time_entry',
        ['user_id', 'job_id', 'started_at'],
    )
    # Expense natural key: (user_id, job_id, incurred_at, cost_cents) — 7-day window
    # Note: field is "incurred_at" in job_expense (confirmed live DB: incurred_at TIMESTAMPTZ)
    # Note: cost_cents is the live DB name (confirmed: cost_cents INTEGER)
    op.create_index(
        'ix_job_expense_natural_key_dedup',
        'job_expense',
        ['user_id', 'job_id', 'incurred_at', 'cost_cents'],
    )
    # Job notes natural key: (created_by, job_id, created_at) — 7-day window
    # Note: job_notes has no user_id column; created_by is the author FK
    op.create_index(
        'ix_job_notes_natural_key_dedup',
        'job_notes',
        ['created_by', 'job_id', 'created_at'],
    )
    # job_attachment photo natural key: (created_by, job_id, created_at) — 30-day window
    # Note: file_hash is NOT a current column in job_attachment (confirmed live DB)
    # See §F for resolution on this
    op.create_index(
        'ix_job_attachment_natural_key_dedup',
        'job_attachment',
        ['created_by', 'job_id', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_job_attachment_natural_key_dedup', table_name='job_attachment')
    op.drop_index('ix_job_notes_natural_key_dedup', table_name='job_notes')
    op.drop_index('ix_job_expense_natural_key_dedup', table_name='job_expense')
    op.drop_index('ix_jte_natural_key_dedup', table_name='job_time_entry')
```

---

## B. EXECUTION ORDER

| # | Item | Rationale |
|:---|:---|:---|
| 1 | **A37** — Offline-Capable Operations API Contract | Foundation: establishes which 9 operations are offline-capable, adds `client_capture_at` to all 5 existing tables. Schema changes must land first — A39 and A38 both depend on columns and operation-type definitions from A37. |
| 2 | **A39** — Idempotency UUIDs for Offline Operations | Second: extends idempotency to offline-capable endpoints from A37 and establishes the shared `utils/idempotency.py` module. Depends on A37 for the list of offline endpoints to wire. Creates the central shared module that all B7b endpoints and B8/A51 will import. Must be established before B7b starts. |
| 3 | **A38** — Sync Queue State Model (Server-Side Visibility) | Third: creates the `mobile_sync_event` table and admin endpoint. Depends on A37 for the `operation_type` enum values (must be defined before the table that stores them). Does not depend on A39's dedup logic — ordering after A39 is for clean dependency sequencing only. |

---

## C. NEW API ENDPOINTS

### A38 — `GET /api/v1/mobile-sync/state/{user_id}`

**Purpose**: Owner/admin view of a tech's server-side sync state for troubleshooting and oversight.  
**Auth**: JWT required  
**RBAC Permission**: `mobile_sync.view` (new permission — see note below)  
**New Route File**: `backend/api/routes/mobile_sync.py`

**Request**:
```
GET /api/v1/mobile-sync/state/{user_id}?cursor=<cursor>&limit=50&status=<status_filter>
```

| Parameter | Type | Required | Notes |
|:---|:---|:---|:---|
| `user_id` | UUID (path) | ✅ | The tech's user UUID — caller must belong to same tenant |
| `cursor` | string (query) | ❌ | Cursor-based pagination per §7.8 |
| `limit` | int (query) | ❌ | Default 50; max 200 |
| `status` | string (query) | ❌ | Optional filter: `pending`, `syncing`, `succeeded`, `failed`, `conflict` |

**Response — 200 OK**:
```json
{
  "user_id": "uuid",
  "items": [
    {
      "id": "uuid",
      "device_id": "string",
      "operation_type": "time_entry",
      "operation_payload_summary": { "job_id": "uuid", "hours": 3.5 },
      "status": "succeeded",
      "conflict_severity": null,
      "client_capture_at": "2026-04-28T14:23:00Z",
      "synced_at": "2026-04-28T20:01:05Z",
      "error_detail": null,
      "idempotency_uuid": "uuid",
      "created_at": "2026-04-28T20:01:04Z"
    }
  ],
  "cursor": "eyJpZCI6ICJ1dWlkIn0",
  "has_more": true
}
```

**Response — 403 Forbidden**: User does not have `mobile_sync.view` permission.  
**Response — 404 Not Found**: `user_id` does not exist within the caller's tenant (tenant isolation enforced — owners cannot query techs in other tenants).

**RBAC Note**: `mobile_sync.view` is a new permission. It must be seeded into the `owner` role and `operator` (Pilot admin) role. Technicians do NOT have this permission — they cannot view their own sync state via this admin endpoint (sync state is surfaced to techs via client-side queue, not this API). Add the permission string to the role-seeding migration or to the existing role-seed data file.

**Implementation location**:
- Route: `backend/api/routes/mobile_sync.py` (new file)
- Register in `backend/app/main.py`
- Pagination: cursor-based per §7.8 pattern; order by `created_at DESC`
- Tenant isolation: query must include `WHERE tenant_id = current_user.tenant_id AND user_id = path_user_id`

---

### A39 — No new public endpoints

A39 extends **existing** offline-capable endpoints by:
1. Expanding the scope of `idempotency_middleware` (already in `core/idempotency.py`) to handle the natural-key fallback for the 5 existing offline-capable tables
2. The shared module `utils/idempotency.py` is internal utility — not an HTTP endpoint

Existing endpoints that become offline-capable via A39's natural-key dedup (no URL changes; behavior changes on duplicate detection):

| Endpoint | Natural Key | Window |
|:---|:---|:---|
| `POST /api/v1/jobs/{id}/time-entries` | `(user_id, job_id, started_at)` | 7 days |
| `POST /api/v1/jobs/{id}/expenses` | `(user_id, job_id, incurred_at, cost_cents)` | 7 days |
| `POST /api/v1/jobs/{id}/notes` | `(created_by, job_id, created_at_approx)` | 7 days |
| `POST /api/v1/jobs/{id}/attachments` (photos) | `(created_by, job_id, client_capture_at)` | 30 days |
| `PATCH /api/v1/jobs/{id}/status` | `(user_id, job_id, client_capture_at, new_status)` | 7 days |

> **Note**: Change-order endpoint dedup is deferred to B7b since change orders require conflict classification context to handle `version-superseded` cases safely.

---

## D. PATTERN REUSE DECISIONS

### §7.6 Idempotency Keys — Extended by A39

**Pattern**: `core/idempotency.py::idempotency_middleware()` — already in production.  
**Extension**: A39 adds a **natural-key fallback** check for offline operations. This runs *after* the primary idempotency key lookup fails (key expired). The extension is implemented in a new shared utility `utils/idempotency.py::check_natural_key_dedup()` (see §E).

**How it integrates**: The existing `idempotency_middleware` function is NOT modified. Instead, each offline-capable endpoint's service layer calls `check_natural_key_dedup()` before inserting, as a second guard. The middleware handles the hot path (24h window); the service call handles the long-tail path (7–30 day window).

**Pattern cite**: `mvp-arch.md §7.6` — "Natural-Key Fallback Dedup for Offline Operations" table; `mvp-arch.md §15.4` — "Idempotency UUIDs with Natural-Key Fallback."

**Which items use it**: A39 (establishes), all B7b offline sync endpoints (consume), B8/A51 background sync (consumes).

---

### §15.3 Sync Queue State Model — Implemented by A38

**Pattern**: Append-only log pattern. The `mobile_sync_event` table must never have rows updated — only new rows inserted for each status transition.  
**How it integrates**: The ORM model uses `AppendOnlyMixin` which provides only `created_at` (no `updated_at`). Service layer must raise if anyone attempts an UPDATE on this table.  
**Pattern cite**: `mvp-arch.md §15.3` — "Server-side append-only log captures every sync attempt."  
**Which items use it**: A38 (establishes), B7b (all conflict items write to it), B8/A47–A48 (read from it for escalation queue).

---

### §16.2 Step 2 — 3-Part Additive Column Migration (applies to A37)

**Pattern**: For adding nullable columns to existing tables per `pilot-python-engineer-methods.md §16.2`.  
**In this batch**: All 5 `client_capture_at` additions are nullable (no backfill needed). Single `op.add_column()` pattern applies — the 3-part pattern (nullable → backfill → NOT NULL) is not required here because the semantic default for existing rows is NULL (online-captured), not a derived value.  
**Which items use it**: A37.

---

### §16.1 Pre-Work Regression Baseline — Applies to all items

**Pattern**: Run full test suite before any file changes; all currently-passing tests must still pass at completion.  
**Batch B7a baseline**: Run `pytest tests/ -v` in `backend/` before starting A37. Record the passing count. B7a must not break any test from B1–B6.  
**Which items use it**: All (pre-condition).

---

### §16.5 Definition of Done — Applies to all items

**DoD requirements for B7a**:
- [ ] All three migrations: `upgrade head` → `downgrade -1` → `upgrade head` succeed cleanly
- [ ] Golden Master JSON (`dev-docs/db-design/pilot-db-schema-v2.6h.json`) updated with `client_capture_at` on all 5 tables and full `mobile_sync_event` table
- [ ] `mobile_sync.view` permission seeded for owner + operator roles
- [ ] `utils/idempotency.py::check_natural_key_dedup()` has 100% test coverage for all 5 operation types
- [ ] `GET /api/v1/mobile-sync/state/{user_id}` returns 403 for technician role; 200 for owner role
- [ ] No existing B1–B6 tests broken

---

## E. SHARED MODULE INTERFACES

### `backend/utils/idempotency.py` — Established in B7a (A39)

This is a **new file**, distinct from the existing `backend/core/idempotency.py` which is the middleware layer. `utils/idempotency.py` is the **service-layer natural-key dedup utility** consumed by offline-capable endpoints.

```python
"""
utils/idempotency.py

Natural-key fallback deduplication for offline-capable operations.

Implements the 7-day/30-day dedup window described in mvp-arch §7.6 and §15.4.
Called by service layer AFTER the 24-hour idempotency middleware has already
determined the idempotency key is expired or absent.

Consumed by:
    - All B7a offline-capable endpoints (time_entry, expense, photo, job_note)
    - All B7b offline-capable endpoints (loto_check, job_status_change, change_order)
    - B8/A51 background sync infrastructure
"""

from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select


# Natural-key dedup window definitions (authoritative source)
NATURAL_KEY_WINDOWS = {
    "time_entry": timedelta(days=7),
    "expense":    timedelta(days=7),
    "photo":      timedelta(days=30),
    "job_note":   timedelta(days=7),
    "job_status_change": timedelta(days=7),   # deferred to B7b (table not yet in DB)
    "loto_check":        timedelta(days=7),   # deferred to B7b (table not yet in DB)
    "change_order":      timedelta(days=7),   # classification handled in B7b
    "voice_audio":       timedelta(days=7),   # deferred to B7b (A42)
}


def check_natural_key_dedup(
    db: Session,
    operation_type: str,
    natural_key_fields: dict,
    window_days: Optional[int] = None,
) -> Optional[dict]:
    """
    Check whether a duplicate offline operation exists based on natural-key fields.

    Called after the primary idempotency-key lookup (24h window) fails to find
    a match. Provides the backstop dedup for the 72-hour offline scenario where
    the idempotency key has expired.

    When a natural-key match is found, the caller must return the existing record
    with HTTP 200 and header `X-Idempotency-Replay: true` — same semantics as a
    primary idempotency-key hit.

    Args:
        db: SQLModel session (injected via Depends(get_db))
        operation_type: One of NATURAL_KEY_WINDOWS keys (e.g., 'time_entry')
        natural_key_fields: Dict of field name → value for the natural key tuple.
            time_entry:  {'user_id': UUID, 'job_id': UUID, 'started_at': datetime}
            expense:     {'user_id': UUID, 'job_id': UUID, 'incurred_at': datetime, 'cost_cents': int}
            photo:       {'created_by': UUID, 'job_id': UUID, 'client_capture_at': datetime}
            job_note:    {'created_by': UUID, 'job_id': UUID, 'created_at': datetime}
        window_days: Override the default window from NATURAL_KEY_WINDOWS. Use only
            for testing or tenant-configurable window settings (future).

    Returns:
        dict with keys {'id': UUID, 'record': <ORM row>} if a duplicate exists,
        None if no duplicate found within the window.

    Raises:
        ValueError: If operation_type is not in NATURAL_KEY_WINDOWS.
        ValueError: If required natural_key_fields for the operation_type are missing.

    Example:
        existing = check_natural_key_dedup(
            db=db,
            operation_type='time_entry',
            natural_key_fields={
                'user_id': current_user.user_id,
                'job_id': job_id,
                'started_at': body.started_at,
            },
        )
        if existing:
            return JSONResponse(
                content=existing['record'].model_dump(),
                headers={'X-Idempotency-Replay': 'true'},
            )
    """
    ...


def record_sync_event(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    device_id: str,
    operation_type: str,
    idempotency_uuid: UUID,
    client_capture_at: datetime,
    status: str,
    operation_payload_summary: Optional[dict] = None,
    conflict_severity: Optional[str] = None,
    synced_at: Optional[datetime] = None,
    error_detail: Optional[dict] = None,
) -> None:
    """
    Insert a new row into mobile_sync_event (append-only — never updates).

    Called at each sync-attempt status transition: pending, syncing, succeeded,
    failed, or conflict. Multiple calls for the same operation produce multiple
    rows — this is intentional for the full audit trail.

    Args:
        db: SQLModel session
        tenant_id: Tenant UUID (from current_user.tenant_id)
        user_id: Tech's user UUID
        device_id: Client-reported device identifier (opaque string)
        operation_type: Must be in NATURAL_KEY_WINDOWS keys
        idempotency_uuid: The client-generated UUID v4 from the Idempotency-Key header
        client_capture_at: The client_capture_at from the request body
        status: One of 'pending' | 'syncing' | 'succeeded' | 'failed' | 'conflict'
        operation_payload_summary: Non-PII summary dict (e.g., {'job_id': str, 'hours': float})
        conflict_severity: One of the 4 severity classes, or None if not a conflict
        synced_at: Set when status is 'succeeded'
        error_detail: Set when status is 'failed'; structured error info

    Returns:
        None (fire-and-forget log; never raises on failure — log and swallow)

    Design note:
        This function swallows exceptions and logs them. Sync-event recording must
        never cause the originating sync operation to fail. The audit trail is
        important but not worth dropping a tech's time entry over.
    """
    ...
```

**File path**: `backend/utils/idempotency.py`  
**Consumed by**: All B7b offline-capable endpoint handlers; B8/A51 background sync; the cleanup Celery task `cleanup_mobile_sync_events` in `tasks/mobile_sync_cleanup.py`.

---

### `backend/app/models/sync.py` — New model file for `MobileSyncEvent`

```python
"""
app/models/sync.py

SQLModel models for mobile sync infrastructure (B7a).

Tables:
    MobileSyncEvent — append-only sync attempt log (§15.3)
"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from pydantic import AwareDatetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin


class MobileSyncEvent(AppendOnlyMixin, SQLModel, table=True):
    """
    Append-only log of sync attempts per device per offline operation.

    Never update existing rows. Insert new rows for each status transition.
    Retained for 30 days then archived via cleanup_mobile_sync_events Celery task.
    """
    __tablename__ = "mobile_sync_event"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'syncing', 'succeeded', 'failed', 'conflict')",
            name="chk_mobile_sync_event_status",
        ),
        CheckConstraint(
            "conflict_severity IS NULL OR conflict_severity IN "
            "('auto_silent', 'auto_notice', 'tech_resolvable', 'owner_escalation')",
            name="chk_mobile_sync_event_conflict_severity",
        ),
        Index("ix_mobile_sync_event_tenant_user_status", "tenant_id", "user_id", "status"),
        Index("ix_mobile_sync_event_created_at", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    device_id: str = Field(sa_column=Column(Text, nullable=False))
    operation_type: str = Field(sa_column=Column(Text, nullable=False))
    operation_payload_summary: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    status: str = Field(sa_column=Column(Text, nullable=False))
    conflict_severity: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    client_capture_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    synced_at: Optional[AwareDatetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    error_detail: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    idempotency_uuid: uuid.UUID = Field(
        sa_column=Column(PG_UUID, nullable=False)
    )
```

**File path**: `backend/app/models/sync.py`  
**Add to**: `backend/db_models_map.md` and `backend/app_model_import.md`

---

## F. OPEN QUESTIONS RESOLVED

### F.1 — `loto_check` and `job_status_change` do not exist in the live DB

**Question**: The architecture docs (mvp-arch §15.2, §15.3, A37 ledger) list 7 offline-capturable tables including `loto_check` and `job_status_change`. Live DB query (2026-05-01) confirms neither table exists. `db_models_map.md` confirms no SQLModel class for these tables. What does B7a do about them?

**Resolution**: **B7a adds `client_capture_at` only to the 5 tables that currently exist**. `loto_check` and `job_status_change` are not stub tables — they are substantive domain tables that belong to a not-yet-implemented domain. Creating empty stub tables in B7a would create orphaned schema with no backing service layer. The correct approach:

- **B7a (this batch)**: Adds `client_capture_at` to `job_time_entry`, `job_expense`, `job_attachment`, `change_order`, `job_notes` — the 5 existing tables. Documents the 7-operation offline contract including the 2 pending operation types.
- **B7b (next batch)**: When A40 (Conflict Severity Classification Engine) is built, it must define the full operation type matrix including `loto_check` and `job_status_change`. These tables should be created **with `client_capture_at` from birth** in B7b migrations, not added retroactively. The Python engineer implementing B7b must:
  1. Create `loto_check` table with `client_capture_at TIMESTAMPTZ NULL` included at table creation
  2. Create `job_status_change` table with `client_capture_at TIMESTAMPTZ NULL` included at table creation
  3. Register both `operation_type` values in `utils/idempotency.py::NATURAL_KEY_WINDOWS`

**Impact on B7a**: None. The 5 existing tables are sufficient to implement and test the `client_capture_at` contract, the natural-key dedup utility, and the `mobile_sync_event` log.

---

### F.2 — `job_expense` natural key uses `incurred_at` not `captured_at`

**Question**: The A39 ledger and §7.6 arch doc both name the expense natural key field as `captured_at`. The live DB column in `job_expense` is `incurred_at TIMESTAMPTZ NOT NULL`. Which name takes precedence?

**Resolution**: **Use `incurred_at`** — it is the live DB column name (confirmed via `information_schema.columns` query). The ledger/arch doc use `captured_at` as a conceptual alias for "the timestamp the expense was incurred/captured." When `client_capture_at` is added to `job_expense` (Migration 1), offline expenses will carry both:
- `incurred_at` — the time the expense was actually incurred (existing field, always set)
- `client_capture_at` — the time the tech tapped "save" on the device (new field, NULL if online)

For natural-key dedup, the key is `(user_id, job_id, incurred_at, cost_cents)` using the existing `incurred_at` field. **Do not create a `captured_at` column** — this would be a confusing duplicate.

---

### F.3 — Photo natural key includes `file_hash`, but `job_attachment` has no `file_hash` column

**Question**: The A39 ledger specifies the photo natural key as `(user_id, job_id, captured_at, file_hash)` on a `photo` table. Live DB shows `job_attachment` is the photo table, and it has no `file_hash` or `user_id` column. The `created_by` column serves as the author FK. How to implement the photo natural-key dedup?

**Resolution**:
1. **Table name**: use `job_attachment` (the live DB table)
2. **`file_hash`**: The `job_attachment` table does not have a `file_hash` column. Adding it in B7a would be correct since it enables strong dedup (file content hash = true dedup vs. timestamp-only dedup). **Add `file_hash TEXT NULL`** to `job_attachment` in Migration 1 alongside `client_capture_at`. This is additive and null-safe for existing rows.
3. **`user_id`**: The live DB `job_attachment` has no `user_id` column; use `created_by` (the FK to `user.id`, confirmed present in live DB) as the user identifier for the natural key.
4. **Updated natural key**: `(created_by, job_id, file_hash)` on a 30-day window when `file_hash IS NOT NULL`. Fallback when `file_hash IS NULL` (legacy or no-hash upload): `(created_by, job_id, client_capture_at)` on 30-day window.

**Migration 1 amendment** — add `file_hash` to Migration 1 body:
```python
op.add_column(
    'job_attachment',
    sa.Column('file_hash', sa.Text(), nullable=True),
)
op.create_index(
    'ix_job_attachment_file_hash',
    'job_attachment',
    ['created_by', 'job_id', 'file_hash'],
    postgresql_where=sa.text('file_hash IS NOT NULL'),
)
```

---

### F.4 — `mobile_sync_event.operation_type` CHECK constraint vs. open enum

**Question**: Should `operation_type` have a CHECK constraint limiting it to the 9 known values, or be a free-text column to allow future operation types without a migration?

**Resolution**: **No CHECK constraint on `operation_type`** — leave it as free-text `TEXT NOT NULL`. Rationale:
- `loto_check` and `job_status_change` are expected operation types in B7b; a CHECK constraint would require a migration to extend the enum for each new operation type.
- The classification matrix in B7b/A40 is data-driven (configuration table), which implies new operation types will be added at runtime.
- Validation belongs in the service layer (`record_sync_event()` validates against `NATURAL_KEY_WINDOWS` keys), not the DB constraint.

The `status` and `conflict_severity` columns DO have CHECK constraints because their valid values are architecturally fixed (4-class severity, 5-state status machine).

---

### F.5 — `mobile_sync.view` permission: new or reuse existing?

**Question**: The `GET /api/v1/mobile-sync/state/{user_id}` endpoint needs an RBAC guard. Does an existing permission cover this, or is a new one required?

**Resolution**: **Create new permission `mobile_sync.view`**. Rationale:
- Existing permissions in `core/permissions.py` cover: `quotes`, `customers`, `jobs`, `time_entries`, `expenses`, `voice`, `audit`, `users`, `integrations`. None covers admin visibility into a tech's device sync state.
- This is an owner/operator-only surface (not a tech-accessible view). It should be explicitly named.
- Seed `mobile_sync.view` into the `owner` and `operator` platform roles. Technician and `office_staff` roles do NOT get this permission.
- No new `require_permission("mobile_sync.view")` change to the permissions module is needed — the existing `require_permission()` factory in `backend/core/permissions.py` accepts any permission string.

---

### F.6 — ORM model file placement for `MobileSyncEvent`

**Question**: `db_models_map.md` has no `sync.py` model file. Should `MobileSyncEvent` go in `system.py` (alongside other infrastructure tables) or a new `sync.py`?

**Resolution**: **New `backend/app/models/sync.py` file**. Rationale:
- `system.py` already has 20 models (confirmed via `db_models_map.md`); adding more to it reduces maintainability.
- `mobile_sync_event` is the first of at least 2–3 mobile-sync-specific tables (`mobile_sync_owner_escalation` in B7b/A46; `mobile_sync_session` in B8/A51). A dedicated `sync.py` groups all offline sync infrastructure cleanly.
- B7b and B8 models will be added to the same `sync.py` file.

---

## G. EXTERNAL DEPENDENCY STATUS

| Item | External Dependency | Mock Strategy | Tom Action Required |
|:---|:---|:---|:---|
| **A37** | None — pure schema additions and contract documentation | N/A | None |
| **A39** | None — extends existing `idempotency_key` table (already in live DB) | N/A | None |
| **A38** | None — new table + admin endpoint | N/A | None |

**B7a is fully internal infrastructure with zero external dependencies.** All three items can be built, tested, and deployed without any third-party service credential or configuration.

**Downstream dependency notes** (for planning, not B7a blockers):
- B7b/A41 (Resumable Photo Upload Pipeline) will require **AWS S3** credentials and multipart upload configuration. This is a B7b concern, not B7a.
- B7b/A42 (Voice Command Offline Capture) requires the **GPU instance** (already provisioned per infrastructure constraints). The Celery worker `process_voice_audio_async` in `tasks/voice_deferred_processor.py` is already registered per `mvp-arch §3.2` — no new infrastructure needed for B7b's voice offline path.

---

## Appendix: Column Addition Summary for ORM Models

The following SQLModel field additions are required in existing model files (per §16.2 Step 1 — "Open `db_models_map.md` first"):

### `backend/app/models/fulfillment.py`

**`JobTimeEntry`** — add after `etc_captured_at` field (line ~362):
```python
# B7a/A37: Offline capture timestamp — NULL means captured online
client_capture_at: Optional[AwareDatetime] = Field(
    default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
)
```

**`JobExpense`** — add after `receipt_object_key` field (line ~463):
```python
# B7a/A37: Offline capture timestamp — NULL means captured online
client_capture_at: Optional[AwareDatetime] = Field(
    default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
)
```

**`JobNotes`** — add after `customer_visible` field (line ~189):
```python
# B7a/A37: Offline capture timestamp — NULL means captured online
client_capture_at: Optional[AwareDatetime] = Field(
    default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
)
```

**`JobAttachment`** — add after `description` field (line ~228) and add `file_hash` (§F.3):
```python
# B7a/A37: Offline capture timestamp — NULL means captured online
client_capture_at: Optional[AwareDatetime] = Field(
    default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
)
# B7a/A39: SHA-256 hash of photo file for natural-key dedup — NULL for legacy rows
file_hash: Optional[str] = Field(
    default=None, sa_column=Column(Text, nullable=True)
)
```

### Where `ChangeOrder` lives — verify before editing

`change_order` exists in the live DB but `ChangeOrder` is listed in `db_models_map.md` under `models/quoting.py`. Add `client_capture_at` to the `ChangeOrder` model in that file. Confirm the field position by reading the current file before editing.

```python
# B7a/A37: Offline capture timestamp — NULL means captured online
client_capture_at: Optional[AwareDatetime] = Field(
    default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
)
```
