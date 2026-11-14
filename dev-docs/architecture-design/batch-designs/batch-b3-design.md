# Batch B3 Design Document — Dispatch Board & ETC

**Batch**: B3  
**Items**: A18, A20, A19, A14, A15, A16, A17  
**Estimated Effort**: 16–22 days  
**Test Subfolder**: `tests/batch_b3/`  
**Prerequisite Batches**: None (parallel-safe with B1, B2, B4, B5)  
**Gates This Batch Sets**: SSE pattern established here is reused in B6, B8, B11  
**Design Date**: May 1, 2026  
**Inputs**: impl plan §6.B3 (v1.1), ledger v6.1 (A14–A20), mvp-arch.md v5, pilot-python-engineer-methods.md, live DB queries, backend source reads

---

## A. MIGRATION PLAN

All migrations follow the naming convention `phase_fe_1_batch_b3_{short_description}`. One migration per logical unit. Run in the order listed. Every migration must pass the triple-verify loop: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head`.

---

### Migration 1 of 4 — `phase_fe_1_batch_b3_tech_color`

**Tables modified**: `user`, `tenant_settings`  
**Rationale**: A18 schema-first. `display_color` on `user` is consumed by all dispatch board rendering. `tech_color_palette` on `tenant_settings` is the tenant override.

**Verified pre-existing columns**: Live DB query on `user` confirmed columns `id`, `email`, `first_name`, `last_name`, `is_platform_user`, `platform_role_code`, `password_hash`, `email_verified_at`, `failed_login_count`, `locked_until`, `password_updated_at`, `require_password_reset`, `mfa_enforced`, `preferred_mfa_channel`, `totp_secret`, `is_active`, `last_login_at`. **`display_color` does NOT exist** — safe to add.

Live DB query on `tenant_settings` confirmed columns `tenant_id`, `default_labor_rate_cents`, `default_billable_labor_rate_cents`, `default_quote_validity_days`, `default_invoice_terms_days`, `require_approval_for_tech_quotes`, `max_discount_pct_owner`. **`tech_color_palette` does NOT exist** — safe to add.

**New columns on `user`**:

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `display_color` | `VARCHAR(7)` | YES | `NULL` | Hex color e.g. `#3B43D6`. NULL until auto-assigned. |

**New columns on `tenant_settings`**:

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `tech_color_palette` | `JSONB` | YES | `NULL` | Array of hex strings. NULL = use system default 12-hue palette. |

**New indexes**:

| Index | Table | Columns | Notes |
|:---|:---|:---|:---|
| `ix_user_display_color` | `user` | `display_color` | Partial; useful for cycling palette assignment queries. Optional — include if palette cycling query benchmarks poorly. |

**Migration pattern** (additive nullable column — no backfill required for `display_color`, `tech_color_palette`):

```python
def upgrade() -> None:
    op.add_column('user', sa.Column('display_color', sa.String(7), nullable=True))
    op.add_column('tenant_settings', sa.Column('tech_color_palette', postgresql.JSONB(), nullable=True))

def downgrade() -> None:
    op.drop_column('tenant_settings', 'tech_color_palette')
    op.drop_column('user', 'display_color')
```

---

### Migration 2 of 4 — `phase_fe_1_batch_b3_dispatch_optimistic_locking`

**Tables modified**: `job`, `job_tech_assignment`  
**Rationale**: A19 requires `version` integer column on both tables for optimistic concurrency control on the move/assign write path.

**Verified pre-existing columns on `job`**: `id`, `tenant_id`, `quote_id`, `quote_version_id`, `customer_id`, `site_id`, `status_id`, `scheduled_start_at`, `scheduled_end_at`, `actual_labor_cost_cents`, `actual_material_cost_cents`, `actual_profit_cents`, `is_active`, `estimated_duration_minutes`, `external_calendar_event_id`. **`version` does NOT exist** — safe to add.

**Verified pre-existing columns on `job_tech_assignment`**: `id`, `tenant_id`, `job_id`, `user_id`, `assigned_by_user_id`, `role`, `ordinal`, `assigned_at`, `is_active`. **`version` does NOT exist** — safe to add.

**New columns on `job`**:

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `version` | `INTEGER` | NO | `1` | Incremented on every write; used for optimistic concurrency. Backfill to `1` for all existing rows. |

**New columns on `job_tech_assignment`**:

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `version` | `INTEGER` | NO | `1` | Same pattern as `job.version`. Backfill to `1` for all existing rows. |

**Migration pattern** (3-part: add nullable → backfill → lock NOT NULL):

```python
def upgrade() -> None:
    # Part 1 — add nullable
    op.add_column('job', sa.Column('version', sa.Integer(), nullable=True))
    op.add_column('job_tech_assignment', sa.Column('version', sa.Integer(), nullable=True))

    # Part 2 — backfill
    op.execute("UPDATE job SET version = 1 WHERE version IS NULL")
    op.execute("UPDATE job_tech_assignment SET version = 1 WHERE version IS NULL")

    # Part 3 — lock NOT NULL with server_default
    op.alter_column('job', 'version', nullable=False, server_default=sa.text('1'))
    op.alter_column('job_tech_assignment', 'version', nullable=False, server_default=sa.text('1'))

def downgrade() -> None:
    op.drop_column('job_tech_assignment', 'version')
    op.drop_column('job', 'version')
```

---

### Migration 3 of 4 — `phase_fe_1_batch_b3_etc_columns`

**Table modified**: `job_time_entry`  
**Rationale**: A14 ETC Capture System. All four columns are new — confirmed absent from live DB query.

**Verified pre-existing columns on `job_time_entry`**: `id`, `job_id`, `user_id`, `started_at`, `ended_at`, `hours`, `notes`, `hourly_rate_cents`, `total_cost_cents`, `tenant_id`, `check_in_lat`, `check_in_lng`, `gps_variance_meters`. **`hours_remaining_estimate`, `hours_remaining_was_overridden`, `override_note`, `quote_line_id` do NOT exist** — safe to add.

**New columns on `job_time_entry`**:

| Column | Type | Nullable | Default | FK Target | Notes |
|:---|:---|:---|:---|:---|:---|
| `hours_remaining_estimate` | `NUMERIC(6,2)` | YES | `NULL` | — | Tech's ETC at clock-out. NULL = no ETC entered. |
| `hours_remaining_was_overridden` | `BOOLEAN` | YES | `NULL` | — | True when tech changed the auto-populated value. NULL = no ETC entered. |
| `override_note` | `TEXT` | YES | `NULL` | — | Required when override increases hours > tenant threshold. |
| `quote_line_id` | `UUID` | YES | `NULL` | `quote_line.id` (RESTRICT) | When present, ETC is per-task; when NULL, ETC is per-job. |

**New indexes on `job_time_entry`**:

| Index | Columns | Notes |
|:---|:---|:---|
| `ix_jte_quote_line_id` | `quote_line_id` | Speeds per-task ETC latest-query DISTINCT ON pattern. |
| `ix_jte_etc_not_null` | `job_id, quote_line_id, created_at DESC` | Partial on `hours_remaining_estimate IS NOT NULL`. Supports latest-ETC query pattern directly. |

**Migration pattern** (all nullable — no backfill required):

```python
def upgrade() -> None:
    op.add_column('job_time_entry',
        sa.Column('hours_remaining_estimate', sa.Numeric(6, 2), nullable=True))
    op.add_column('job_time_entry',
        sa.Column('hours_remaining_was_overridden', sa.Boolean(), nullable=True))
    op.add_column('job_time_entry',
        sa.Column('override_note', sa.Text(), nullable=True))
    op.add_column('job_time_entry',
        sa.Column('quote_line_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_jte_quote_line', 'job_time_entry', 'quote_line',
        ['quote_line_id'], ['id'], ondelete='RESTRICT')
    op.create_index('ix_jte_quote_line_id', 'job_time_entry', ['quote_line_id'])
    op.execute("""
        CREATE INDEX ix_jte_etc_not_null
        ON job_time_entry (job_id, quote_line_id, created_at DESC)
        WHERE hours_remaining_estimate IS NOT NULL
    """)

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_jte_etc_not_null")
    op.drop_index('ix_jte_quote_line_id', table_name='job_time_entry')
    op.drop_constraint('fk_jte_quote_line', 'job_time_entry', type_='foreignkey')
    op.drop_column('job_time_entry', 'quote_line_id')
    op.drop_column('job_time_entry', 'override_note')
    op.drop_column('job_time_entry', 'hours_remaining_was_overridden')
    op.drop_column('job_time_entry', 'hours_remaining_estimate')
```

---

### Migration 4 of 4 — `phase_fe_1_batch_b3_tenant_settings_b3`

**Table modified**: `tenant_settings`  
**Rationale**: A15, A16, A17 all add settings. Batched into one migration to avoid multiple ALTERs on the same table.

**Verified absent from live DB**: `report_chart_threshold`, `etc_variance_owner_notify_pct`, `etc_variance_note_required_pct`, `margin_bucket_boundaries`, `margin_target_pct` — all confirmed NOT in the current `tenant_settings` schema.

**New columns on `tenant_settings`**:

| Column | Type | Nullable | Default | Source | Notes |
|:---|:---|:---|:---|:---|:---|
| `report_chart_threshold` | `INTEGER` | NO | `8` | A15 | Row count below which report endpoints return `display_mode: 'chart'`. |
| `etc_variance_owner_notify_pct` | `INTEGER` | NO | `50` | A16 | % over quoted hours that triggers owner push + email notification. |
| `etc_variance_note_required_pct` | `INTEGER` | NO | `10` | A16 | % increase in projection that requires a tech override note. |
| `margin_bucket_boundaries` | `JSONB` | NO | `'[10, 20, 30]'::jsonb` | A17 | Ascending int array. 3 values = 4 buckets. |
| `margin_target_pct` | `INTEGER` | NO | `20` | A17 | "Below target" indicator threshold in report rendering. |

**New check constraints on `tenant_settings`**:

| Constraint | Expression | Notes |
|:---|:---|:---|
| `ck_ts_report_chart_threshold_positive` | `report_chart_threshold > 0` | Threshold must be at least 1 |
| `ck_ts_etc_notify_pct_range` | `etc_variance_owner_notify_pct BETWEEN 1 AND 500` | Reasonable range |
| `ck_ts_etc_note_pct_range` | `etc_variance_note_required_pct BETWEEN 1 AND 100` | Reasonable range |
| `ck_ts_margin_target_range` | `margin_target_pct BETWEEN 0 AND 100` | Percentage |

**Migration pattern** (all have server defaults — no backfill needed):

```python
def upgrade() -> None:
    op.add_column('tenant_settings',
        sa.Column('report_chart_threshold', sa.Integer(),
                  nullable=False, server_default=sa.text('8')))
    op.add_column('tenant_settings',
        sa.Column('etc_variance_owner_notify_pct', sa.Integer(),
                  nullable=False, server_default=sa.text('50')))
    op.add_column('tenant_settings',
        sa.Column('etc_variance_note_required_pct', sa.Integer(),
                  nullable=False, server_default=sa.text('10')))
    op.add_column('tenant_settings',
        sa.Column('margin_bucket_boundaries', postgresql.JSONB(),
                  nullable=False, server_default=sa.text("'[10, 20, 30]'::jsonb")))
    op.add_column('tenant_settings',
        sa.Column('margin_target_pct', sa.Integer(),
                  nullable=False, server_default=sa.text('20')))
    op.create_check_constraint(
        'ck_ts_report_chart_threshold_positive', 'tenant_settings',
        'report_chart_threshold > 0')
    op.create_check_constraint(
        'ck_ts_etc_notify_pct_range', 'tenant_settings',
        'etc_variance_owner_notify_pct BETWEEN 1 AND 500')
    op.create_check_constraint(
        'ck_ts_etc_note_pct_range', 'tenant_settings',
        'etc_variance_note_required_pct BETWEEN 1 AND 100')
    op.create_check_constraint(
        'ck_ts_margin_target_range', 'tenant_settings',
        'margin_target_pct BETWEEN 0 AND 100')

def downgrade() -> None:
    op.drop_constraint('ck_ts_margin_target_range', 'tenant_settings', type_='check')
    op.drop_constraint('ck_ts_etc_note_pct_range', 'tenant_settings', type_='check')
    op.drop_constraint('ck_ts_etc_notify_pct_range', 'tenant_settings', type_='check')
    op.drop_constraint('ck_ts_report_chart_threshold_positive', 'tenant_settings', type_='check')
    op.drop_column('tenant_settings', 'margin_target_pct')
    op.drop_column('tenant_settings', 'margin_bucket_boundaries')
    op.drop_column('tenant_settings', 'etc_variance_note_required_pct')
    op.drop_column('tenant_settings', 'etc_variance_owner_notify_pct')
    op.drop_column('tenant_settings', 'report_chart_threshold')

def downgrade() -> None:
    # Note: tech_color_palette already dropped in migration 1 downgrade
    pass
```

---

## B. EXECUTION ORDER

| # | Item | Rationale |
|:---|:---|:---|
| 1 | **A18** — Tech Color Assignment & Configuration | Schema-first: adds `display_color` to `user` and `tech_color_palette` to `tenant_settings`. Dispatch board rendering, avatar fills, and all downstream B3 items consume this. Auto-assignment logic at user creation must exist before board endpoints return color data. |
| 2 | **A20** — Drive-Time Caching Verification | Verification + observability item, not a feature build. Must confirm the Redis caching layer in `services/map_service.py` and `services/scheduling_service.py` is correct before building move/check-conflict endpoints that trigger drive-time lookups (A19). Also establishes the `map_provider.cache_hit_ratio` metric that the alarm in item 3 will monitor. |
| 3 | **A19** — Dispatch Board API Endpoints (Optimistic Locking + SSE) | Main dispatch feature. Depends on A18 (color in board payload) and A20 (drive-time layer verified). Adds `version` column to `job` and `job_tech_assignment`, the move/check-conflict endpoints, and the SSE stream. **SSE pattern established here is the canonical template for B6, B8, B11** — must be built cleanly. |
| 4 | **A14** — ETC Capture System | New columns on `job_time_entry` + projected-margin endpoint. Independent of A18/A19/A20 at DB level, but placed after the dispatch items because the ETC prompt trigger (end-of-day clock-out, task completion) is surfaced in the same scheduling/dispatch context. A16 depends on A14's columns existing. |
| 5 | **A15** — Chart-or-Table Threshold Setting | Trivial tenant setting (`report_chart_threshold`) that all report endpoints consume. Placed before A16 because A16's notification content references margin data that may render via report endpoints, and the setting must exist. Half-day item. |
| 6 | **A16** — ETC Variance Notification System | Depends on A14 (ETC columns must exist on `job_time_entry`) and A15 (`etc_variance_note_required_pct` / `etc_variance_owner_notify_pct` settings). Fires every time a `job_time_entry` with ETC is saved. |
| 7 | **A17** — Margin Bucket Configuration | Independent tenant settings (`margin_bucket_boundaries`, `margin_target_pct`). No B3 dependency; placed last as purely additive settings consumed by the report layer (B5). Safe to parallelize with A16 if effort allows. |

---

## C. NEW API ENDPOINTS

All endpoints follow RFC 7807 error format, require `Authorization: Bearer <JWT>` unless noted, and follow the existing route prefix pattern. The existing scheduling route file uses the prefix `/api/v1/scheduling/` (per the file header and dispatch-board route `GET /api/v1/scheduling/dispatch-board`). See §F Open Questions for the `/scheduling/` vs `/schedule/` prefix resolution.

---

### A18 — Tech Color Endpoints

**PATCH `/api/v1/users/{user_id}/color`**  
Set or update a user's display color (owner override per tech in Settings → Users).

- **Auth**: JWT required  
- **Permission**: `users.update` (owner/admin only — tech cannot set their own color)  
- **Request body**:
  ```json
  { "display_color": "#3B43D6" }
  ```
- **Validation**: must match `/^#[0-9A-Fa-f]{6}$/`
- **Response 200**:
  ```json
  { "user_id": "uuid", "display_color": "#3B43D6", "updated_at": "ISO8601" }
  ```
- **Response 422**: invalid hex format

**GET `/api/v1/users/{user_id}`** (extension — no new endpoint, add `display_color` to existing user response shape)  
The `display_color` field is returned on all user responses. No new endpoint required; `User` ORM model gains the field.

---

### A19 — Dispatch Board Endpoints

**GET `/api/v1/scheduling/dispatch-board`** (already exists — extend response shape)  
- **Extension**: add `display_color` per tech group entry, add drive-time data computed from Redis cache (or fresh map provider call on cache miss).  
- **New response fields on each job entry**: `version` (integer), `drive_time_minutes_to_next` (integer | null)

**POST `/api/v1/scheduling/jobs/{job_id}/move`** ← *new endpoint*  
Atomic operation: reassign tech and/or change scheduled time window. Performs conflict check before commit. Implements optimistic concurrency.

- **Auth**: JWT required  
- **Permission**: `schedule.manage`  
- **Request body**:
  ```json
  {
    "tech_user_id": "uuid",
    "scheduled_start_at": "ISO8601",
    "scheduled_end_at": "ISO8601",
    "expected_job_version": 3,
    "expected_assignment_version": 2
  }
  ```
- **Response 200** (success):
  ```json
  {
    "job_id": "uuid",
    "job_version": 4,
    "assignment_id": "uuid",
    "assignment_version": 3,
    "tech_user_id": "uuid",
    "scheduled_start_at": "ISO8601",
    "scheduled_end_at": "ISO8601",
    "conflicts": []
  }
  ```
- **Response 409** (stale — optimistic lock failed):
  ```json
  {
    "type": "https://pilotfortrades.com/errors/conflict",
    "title": "Concurrent Modification",
    "status": 409,
    "detail": "Job or assignment was modified by another user. Review the refreshed state.",
    "current_job_version": 5,
    "current_assignment_version": 3,
    "current_state": { ... }
  }
  ```
- **Response 422**: validation errors (end before start, etc.)

**POST `/api/v1/scheduling/jobs/{job_id}/check-conflicts`** ← *new endpoint*  
Preview-only conflict check for drag-operation what-if. No commit, no version bump, no SSE event emitted.

- **Auth**: JWT required  
- **Permission**: `schedule.manage`  
- **Request body**:
  ```json
  {
    "tech_user_id": "uuid",
    "scheduled_start_at": "ISO8601",
    "scheduled_end_at": "ISO8601"
  }
  ```
- **Response 200**:
  ```json
  {
    "is_feasible": true,
    "conflicts": [
      {
        "conflict_type": "drive_time",
        "severity": "warning",
        "description": "Only 8 min gap; drive time is 22 min",
        "conflicting_entity_id": "uuid"
      }
    ],
    "drive_time_to_next_minutes": 22,
    "drive_time_from_prev_minutes": 14
  }
  ```

**GET `/api/v1/scheduling/board/stream`** ← *new SSE endpoint*  
Opens a Server-Sent Events connection for the dispatch board. JWT passed as URL query parameter `?token=<jwt>` (SSE browsers cannot set headers on the initial handshake).

- **Auth**: JWT in `?token=` query param (validated server-side; discarded after auth; connection carries `(tenant_id, user_id)`)
- **Permission**: `schedule.manage` (or `schedule.view_all` — owner/dispatcher roles only)
- **Channel**: `dispatch:{tenant_id}` (one per tenant; cross-tenant isolation enforced at channel name)
- **SSE Event types** (from mvp-arch.md §13.11):

  | Event | Payload |
  |:---|:---|
  | `job_scheduled` | `{job_id, tech_id, scheduled_start_at, scheduled_end_at}` |
  | `job_rescheduled` | `{job_id, prev_start_at, new_start_at, prev_end_at, new_end_at}` |
  | `job_reassigned` | `{job_id, prev_tech_id, new_tech_id}` |
  | `job_unassigned` | `{job_id, prev_tech_id}` |
  | `conflict_detected` | `{job_id, conflict_class, severity}` |
  | `conflict_cleared` | `{job_id}` |
  | `calendar_sync_status` | `{integration_id, status, pending_conflicts_count}` |

- **Heartbeat**: server comment line every 15 seconds
- **Reconnect**: `Last-Event-ID` header enables replay of last 100 events per channel (stored in Redis list `dispatch_stream:{tenant_id}:events`)
- **Idle timeout**: server closes connections idle > 5 minutes

---

### A14 — ETC Endpoints

**POST `/api/v1/jobs/{job_id}/time-entries`** (already exists — extend request body)  
Extension: accept new ETC fields. No new endpoint; existing route in `backend/api/routes/scheduling.py` is extended.

- **Auth**: JWT required  
- **Permission**: `time_entries.create`  
- **New request fields**:
  ```json
  {
    "hours_remaining_estimate": 3.5,
    "hours_remaining_was_overridden": true,
    "override_note": "Found additional conduit run not in scope",
    "quote_line_id": "uuid or null"
  }
  ```
- **Validation**: if `hours_remaining_estimate` changes projection by more than `etc_variance_note_required_pct`, `override_note` is required (422 if absent)

**GET `/api/v1/jobs/{job_id}/projected-margin`** ← *new endpoint*

- **Auth**: JWT required  
- **Permission**: `jobs.view`  
- **Response 200**:
  ```json
  {
    "job_id": "uuid",
    "quoted_total_cents": 450000,
    "actual_labor_cost_cents": 125000,
    "actual_material_cost_cents": 85000,
    "projected_labor_cost_cents": 187500,
    "projected_total_cents": 272500,
    "projected_margin_pct": 39.4,
    "below_margin_target": false,
    "margin_target_pct": 20,
    "etc_source": "per_task",
    "latest_etc_entries": [
      {
        "quote_line_id": "uuid or null",
        "hours_remaining": 3.5,
        "captured_at": "ISO8601"
      }
    ]
  }
  ```
- **Backward compat**: jobs with no ETC entries → `etc_source: "fallback"`, `projected_labor_cost_cents` computed as `MAX(quoted_hours, hours_worked_so_far) × hourly_rate_cents`

---

### A15 — Chart Threshold

No new endpoints. The `report_chart_threshold` tenant setting is read by all report endpoints (B5). The setting is exposed via the generic settings CRUD endpoints established in B9. No B3 endpoint work required beyond adding the DB column.

---

### A16 — ETC Variance Notification

No new HTTP endpoints. Implemented as a Celery Beat task. The existing `notification_outbox` infrastructure (confirmed in live DB with `recipient_user_id`, `channel`, `body`, `status` columns) is used for push + email dispatch.

---

### A17 — Margin Bucket Configuration

No new endpoints. Settings exposed via B9 settings CRUD. No B3 endpoint work required beyond adding the DB columns.

---

## D. PATTERN REUSE DECISIONS

### §16.4 — Pre-Commit Staleness Check (409-and-Refresh)

**Applies to**: A19 (`POST .../move`)

The move endpoint is the first B3 use of the canonical staleness/optimistic-lock pattern. It uses integer `version` columns (not `updated_at` timestamps) because dispatch-board moves are high-frequency and `updated_at` collisions are harder to surface cleanly in the drag-and-drop UI.

**Pattern**: move endpoint receives `expected_job_version` and `expected_assignment_version`. Before the write:
```python
# Tenant-scoped load (IDOR-safe per §16.3)
job = db.exec(
    select(Job)
    .where(Job.id == job_id)
    .where(Job.tenant_id == current_user.tenant_id)
).first()
if not job:
    raise HTTPException(status_code=404, detail="Not found")

if job.version != body.expected_job_version:
    raise HTTPException(
        status_code=409,
        detail={
            "type": "https://pilotfortrades.com/errors/conflict",
            "title": "Concurrent Modification",
            "status": 409,
            "current_job_version": job.version,
            "current_state": { ... }
        }
    )
# On success: job.version += 1
```

This 409 shape is the **canonical pattern** that B6 (A33), B7b (A45), B8 (A48, A50), and B11 (A62) will reuse. Build it well here.

### §17.1 — Periodic Poll Task (Celery Beat)

**Applies to**: A16 ETC variance notification

The `notify_etc_variance_owners` task runs every 15 minutes (per mvp-arch.md §3.2). Pattern from pilot-python-engineer-methods.md §17.1:

```python
# tasks/notify_etc_variance_owners.py
@celery_app.task(name="notify_etc_variance_owners")
def notify_etc_variance_owners() -> Dict[str, int]:
    """Scan recent job_time_entry rows with ETC; notify owners when variance threshold exceeded."""
    db: Session = next(get_db())
    notified = 0
    try:
        # Query: jobs with ETC entries saved since last run
        # Compare projection vs quoted_hours
        # Check variance_owner_notified_at to prevent duplicate notifications
        ...
        db.commit()
        return {"notified": notified}
    except Exception as e:
        db.rollback()
        logger.error(f"notify_etc_variance_owners error: {e}")
        raise
    finally:
        db.close()
```

Register in `celery_app.py` Beat schedule:
```python
"notify-etc-variance-owners-every-15min": {
    "task": "notify_etc_variance_owners",
    "schedule": crontab(minute="*/15"),
}
```

### §13.11 (mvp-arch.md) — SSE Dispatch Board Stream

**Applies to**: A19

New service module `services/dispatch_board_stream.py` per the arch spec. The SSE handler:
- Manages one Redis Pub/Sub channel per tenant: `dispatch:{tenant_id}`
- Stores last 100 events in `dispatch_stream:{tenant_id}:events` Redis list for `Last-Event-ID` replay
- Broadcasts are triggered from: (1) the `POST .../move` write path, (2) the calendar pull Celery task, (3) tech status changes

New middleware module `core/sse_middleware.py` handles: heartbeat (15s comment line), idle timeout (5 min), reconnection on `Last-Event-ID`.

### §7.9 (mvp-arch.md) — Pre-Commit Staleness Check Surfaces

**Applies to**: A19. This endpoint joins the table in §7.9 as:

| Endpoint | Expected-Version Field |
|:---|:---|
| `POST /api/v1/scheduling/jobs/{id}/move` | `expected_job_version`, `expected_assignment_version` |

### §16.2 Standard 4-Step Execution Loop

**Applies to**: all B3 items. Engineer must:
1. Use `backend/db_models_map.md` to locate model files before any changes
2. Use `backend/app_model_import.md` to confirm import paths
3. Follow 3-part migration pattern for `version` columns (add nullable → backfill → lock NOT NULL)
4. Run triple-verify loop on every migration

### §16.3 — Tenant-Scoped Queries (IDOR Prevention)

**Applies to**: all B3 write endpoints (A18 color PATCH, A19 move, A14 time-entry POST, projected-margin GET). All `session.get(Model, id)` patterns must be replaced with tenant-scoped `select()` queries per §16.3.

---

## E. SHARED MODULE INTERFACES

### `services/dispatch_board_stream.py` ← **new file, established in B3**

This module is the SSE canonical pattern — reused by B6, B8, B11. Build with the full interface here.

```python
"""
Dispatch Board SSE Stream Service.

Manages per-tenant Redis Pub/Sub channels for real-time dispatch board updates.
Consumed by: B3 (dispatch), B6 (calendar conflicts), B8 (QB conflicts + field issues), B11 (comms threads).
"""
from typing import AsyncIterator, Optional
import json
import redis.asyncio as aioredis

CHANNEL_PREFIX = "dispatch"
EVENT_HISTORY_PREFIX = "dispatch_stream"
MAX_HISTORY_LEN = 100
HEARTBEAT_INTERVAL_SECONDS = 15
IDLE_TIMEOUT_SECONDS = 300


def _channel_name(tenant_id: str) -> str:
    """Return the Redis Pub/Sub channel name for a tenant.
    
    Args:
        tenant_id: UUID string of the tenant.
    Returns:
        str: e.g. 'dispatch:a1b2c3d4-...'
    """
    return f"{CHANNEL_PREFIX}:{tenant_id}"


def _history_key(tenant_id: str) -> str:
    """Return the Redis list key for event replay history.
    
    Args:
        tenant_id: UUID string of the tenant.
    Returns:
        str: e.g. 'dispatch_stream:a1b2c3d4-...:events'
    """
    return f"{EVENT_HISTORY_PREFIX}:{tenant_id}:events"


async def broadcast_board_event(
    redis_client: aioredis.Redis,
    tenant_id: str,
    event_type: str,
    payload: dict,
    event_id: Optional[str] = None,
) -> None:
    """Publish a board event to the tenant's SSE channel and append to replay history.
    
    Args:
        redis_client: Async Redis client.
        tenant_id:    Tenant UUID string — enforces cross-tenant isolation.
        event_type:   One of: job_scheduled, job_rescheduled, job_reassigned,
                      job_unassigned, conflict_detected, conflict_cleared, calendar_sync_status.
        payload:      Event-specific dict (per §13.11 schema).
        event_id:     Optional string event ID for Last-Event-ID replay. Auto-generated if None.
    Returns:
        None
    Raises:
        redis.exceptions.RedisError: on connection failure (caller handles gracefully).
    """
    ...


async def sse_event_generator(
    redis_client: aioredis.Redis,
    tenant_id: str,
    user_id: str,
    last_event_id: Optional[str] = None,
) -> AsyncIterator[str]:
    """Async generator yielding SSE-formatted strings for a connected client.
    
    Replays missed events via last_event_id, then subscribes to live channel.
    Emits heartbeat comment lines every HEARTBEAT_INTERVAL_SECONDS.
    Raises asyncio.TimeoutError after IDLE_TIMEOUT_SECONDS with no data.
    
    Args:
        redis_client:  Async Redis client.
        tenant_id:     Tenant UUID string — SSE channel scoped to this tenant.
        user_id:       User UUID string — for audit/logging.
        last_event_id: If provided, replay all history events with ID > last_event_id.
    Yields:
        str: SSE-formatted event strings, e.g. 'event: job_rescheduled\ndata: {...}\nid: 42\n\n'
    """
    ...
```

**File path**: `backend/services/dispatch_board_stream.py`

---

### `services/etc_service.py` ← **new file, established in B3**

```python
"""
ETC (Estimate-to-Complete) Service.

Computes projected margin for jobs with ETC entries.
Consumed by: B3 A14 (projected-margin endpoint), B3 A16 (variance notification task).
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlmodel import Session


def get_latest_etc_entries(
    db: Session,
    tenant_id: UUID,
    job_id: UUID,
) -> list[dict]:
    """Return the most recent ETC entry per (job_id, quote_line_id) combination.
    
    Uses DISTINCT ON pattern from ledger A14:
        DISTINCT ON (job_id, quote_line_id) ... ORDER BY job_id, quote_line_id, created_at DESC
    
    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID for IDOR isolation.
        job_id:    Target job UUID.
    Returns:
        list of dicts with keys: quote_line_id (UUID|None), hours_remaining_estimate (Decimal),
        created_at (datetime). Empty list if no ETC entries exist.
    """
    ...


def compute_projected_margin(
    db: Session,
    tenant_id: UUID,
    job_id: UUID,
    hourly_rate_cents: int,
    quoted_total_cents: int,
    actual_labor_cost_cents: int,
    actual_material_cost_cents: int,
    margin_target_pct: int,
) -> dict:
    """Compute projected margin incorporating latest ETC values.
    
    Fallback logic (from ledger A14): if no ETC entries exist,
    projected_total_hours = MAX(quoted_hours, hours_worked_so_far).
    
    Args:
        db:                         Open SQLModel session.
        tenant_id:                  Tenant UUID.
        job_id:                     Target job UUID.
        hourly_rate_cents:          Effective labor rate for projection.
        quoted_total_cents:         Original quote total in cents.
        actual_labor_cost_cents:    Actuals from job.actual_labor_cost_cents.
        actual_material_cost_cents: Actuals from job.actual_material_cost_cents.
        margin_target_pct:          From tenant_settings.margin_target_pct.
    Returns:
        dict with keys: projected_labor_cost_cents, projected_total_cents,
        projected_margin_pct (Decimal), below_margin_target (bool),
        etc_source ('per_task'|'per_job'|'fallback'), latest_etc_entries (list).
    """
    ...


def check_etc_variance(
    projected_total_hours: Decimal,
    quoted_hours: Decimal,
    notify_pct: int,
) -> tuple[bool, Decimal]:
    """Check whether ETC variance exceeds the owner notification threshold.
    
    Args:
        projected_total_hours: Sum of actuals + latest ETC.
        quoted_hours:          Original quoted labor hours.
        notify_pct:            tenant_settings.etc_variance_owner_notify_pct.
    Returns:
        tuple: (should_notify: bool, variance_pct: Decimal)
    """
    if quoted_hours == 0:
        return False, Decimal("0")
    variance_pct = (projected_total_hours / quoted_hours - 1) * 100
    return variance_pct >= notify_pct, variance_pct
```

**File path**: `backend/services/etc_service.py`

---

### `services/tech_color_service.py` ← **new file, established in B3**

```python
"""
Tech Color Assignment Service.

Auto-assigns display colors to new users from a cycling palette.
Consumed by: B3 A18 (user creation hook + manual override endpoint).
"""
from uuid import UUID
from sqlmodel import Session

# System default 12-hue WCAG AA-compliant palette (hex strings)
DEFAULT_PALETTE: list[str] = [
    "#3B43D6", "#D64343", "#43D68B", "#D6A143",
    "#8B43D6", "#43BDD6", "#D6438B", "#6BD643",
    "#D6435F", "#435FD6", "#D6C243", "#43D6C2",
]


def assign_next_color(
    db: Session,
    tenant_id: UUID,
    palette: list[str] | None = None,
) -> str:
    """Select the next available color for a new user within a tenant.
    
    Cycles through the palette ensuring no two active users in the same
    tenant share a color. Wraps around when all colors are in use.
    
    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID — color uniqueness is per-tenant, not global.
        palette:   Override palette (from tenant_settings.tech_color_palette).
                   Falls back to DEFAULT_PALETTE if None or empty.
    Returns:
        str: Hex color string, e.g. '#3B43D6'.
    """
    ...
```

**File path**: `backend/services/tech_color_service.py`

---

## F. OPEN QUESTIONS RESOLVED

### F1 — Route Prefix: `/api/v1/scheduling/` vs `/api/v1/schedule/`

**Observation**: The existing route file `backend/api/routes/scheduling.py` uses the prefix `/api/v1/scheduling/` (e.g., `GET /api/v1/scheduling/dispatch-board`). The arch doc (mvp-arch.md §13.7) and additions ledger (A19) specify `/api/v1/schedule/board`, `/api/v1/schedule/jobs/{id}/move`, etc.

**Decision**: Use the **existing `/api/v1/scheduling/` prefix** for all B3 endpoints. Do not introduce a parallel `/schedule/` router — that would break existing clients and tests. New B3 endpoints will be:
- `POST /api/v1/scheduling/jobs/{job_id}/move`
- `POST /api/v1/scheduling/jobs/{job_id}/check-conflicts`
- `GET /api/v1/scheduling/board/stream`
- The existing `GET /api/v1/scheduling/dispatch-board` is extended

**Rationale**: The arch doc uses shorthand notation; the real prefix is whatever is registered in `app/main.py`. Consistency with existing live routes takes precedence.

---

### F2 — ETC Column Names: Ledger vs Arch Doc

**Observation**: Additions ledger A14 names the new `job_time_entry` columns as `hours_remaining_estimate`, `hours_remaining_was_overridden`, `override_note`, `quote_line_id`. The mvp-arch.md §14.3 uses different names: `etc_hours_remaining`, `etc_captured_at`, `etc_variance_note` — and includes `etc_captured_at` which the ledger does not mention at all.

**Decision**: **Use ledger names** as the impl plan instruction states "the ledger has the authoritative detail." Add `etc_captured_at TIMESTAMPTZ NULL` as an additional column (not in the ledger but architecturally sound — it's needed for the latest-ETC query to show "when was ETC captured relative to clock-out"). This is a pure addition; it does not conflict with the ledger.

**Resolved names for migration 3**:
- `hours_remaining_estimate` (ledger)
- `hours_remaining_was_overridden` (ledger)
- `override_note` (ledger)
- `quote_line_id` (ledger)
- `etc_captured_at` (arch addition — populated to `ended_at` value at clock-out)

---

### F3 — `variance_owner_notified_at` — Where Does It Live?

**Observation**: Ledger A16 says "Mark job as `variance_owner_notified_at` (prevents repeat notifications)." The `job` table has no such column in the live DB.

**Decision**: Add `variance_owner_notified_at TIMESTAMPTZ NULL` and `variance_last_notified_pct NUMERIC(5,1) NULL` to the **`job`** table. Bundle these two columns into **Migration 2** (`phase_fe_1_batch_b3_dispatch_optimistic_locking`) to avoid a fifth migration file — they're logically grouped with `job` table changes.

**Rationale**: Re-notification logic requires knowing both *when* the owner was last notified and *at what variance level*, so that when variance worsens past the next band it triggers again.

---

### F4 — `job_tech_assignment.version` and Soft-Delete Interaction

**Observation**: `job_tech_assignment` uses soft-delete (`is_active`). When an assignment is soft-deleted (tech removed from job), the `version` on that row should not reset to 1.

**Decision**: The `version` column is maintained on the live row. Soft-delete sets `is_active = false` AND bumps `version` (so a client holding `expected_assignment_version = 2` will receive a 409 if another user concurrently soft-deleted the assignment). This is the correct behavior — the 409 with `current_state` will show `is_active: false`, which the client can interpret as "assignment was removed."

---

### F5 — Tech Color Auto-Assignment Trigger Point

**Observation**: A18 says "auto-assigned at user creation." The existing user creation flow is in the auth/onboarding path, not in scheduling.

**Decision**: Add the `assign_next_color()` call to the **user creation service** (or Cognito post-signup Lambda, whichever creates the `user` row). The color assignment must happen at row creation time, not lazily. If the user creation path cannot be identified before implementation starts, the fallback is a one-time Celery task that backfills `display_color` for all existing users without a color. This is a low-risk deferral — dispatch board gracefully renders a gray placeholder when `display_color IS NULL`.

---

### F6 — SSE Redis Backend: Sync vs Async

**Observation**: The main FastAPI app uses synchronous SQLModel sessions (`get_db()` yields `Session`). SSE requires async I/O for the long-lived connection.

**Decision**: The SSE route handler uses `async def` with `aioredis` (async Redis client). The route is registered with `StreamingResponse` returning the async generator. This is isolated from the synchronous DB session pattern — the SSE handler reads from Redis only, not from the DB session. JWT validation on the SSE connection is done synchronously before the async generator starts.

---

## G. EXTERNAL DEPENDENCY STATUS

### Google Maps API (A20 — Drive-Time Caching Verification)

- **Dependency**: Google Maps Distance Matrix API for live drive-time calculations
- **Mock strategy**: `settings.MAP_PROVIDER = "mock"` already implemented in `backend/services/map_service.py` using Haversine formula. The mock is the default for local dev and CI. No action needed for development.
- **Monitoring addition** (A20): `map_provider.cache_hit_ratio` metric added to CloudWatch. Cache alarm at < 70% over 1 hour. The Redis cache key is `(origin_lat, origin_lng, dest_lat, dest_lng, hour_of_day)`, TTL 24h — verify this key is actually used in `services/scheduling_service.py` at `check_slot_feasibility()` → `get_drive_time_minutes()` call chain.
- **Tom action required before production**: Ensure Google Maps API key is in AWS Secrets Manager under `GOOGLE_MAPS_API_KEY`. Enable Distance Matrix API and Geocoding API in the GCP project. Set up billing alert at $500/month. **No lead time issue** — done on-demand.

---

### Google Maps API — Cost Risk (A19 Dispatch Board)

- **Risk**: Dispatch board drag-and-drop operations can trigger many drive-time lookups. At 100 customers with 5 jobs/day × 10 matrix elements, estimated ~$770/month without caching (arch §13.8).
- **Mock strategy**: `MAP_PROVIDER=mock` prevents any API cost in dev/staging.
- **Production mitigation**: A20 verification ensures caching is correct before B3 goes live. The cache hit ratio alarm provides early warning if the caching layer breaks.
- **Tom action required**: None blocking for development. For production, confirm caching is working by checking the `map_provider.cache_hit_ratio` CloudWatch metric after first production week. If below 70%, investigate cache key generation in `scheduling_service.py`.

---

### SendGrid / Push Provider (A16 — ETC Variance Notification)

- **Dependency**: A16 uses the existing `notification_outbox` infrastructure. The `notification_outbox` table (confirmed in live DB) already supports `channel: 'email'` and `channel: 'push'`. The actual delivery is handled by the existing outbox processor task.
- **Mock strategy**: In dev/test, the outbox processor is not running — outbox rows are created and remain `status: 'pending'`. Tests assert on row creation, not delivery. This follows §1.5 Rule 2 of the impl plan: "external dependencies do not block development."
- **Tom action required**: None new for B3 specifically. If SendGrid is already configured (B4 pre-requisite), email delivery works at production. Push delivery depends on FCM/APNs configuration (B10 scope).

---

### No External Dependencies

- **A18** (Tech Color): pure internal. No external APIs.
- **A15** (Chart Threshold): pure tenant settings. No external APIs.
- **A17** (Margin Buckets): pure tenant settings. No external APIs.
- **A19 SSE**: uses Redis (already in stack as Celery broker). No new external service.

---

*All six input reads completed. All seven sections populated. No open questions remain unresolved.*
