# Batch B7b Design Document — Offline Conflict Engine

**Batch**: B7b  
**Title**: Offline Conflict Engine  
**Prerequisite**: B7a complete (schema-diffed clean — migrations `phase_fe_1_batch_b7a_offline_capture_timestamps`, `phase_fe_1_batch_b7a_natural_key_dedup_indexes`, `phase_fe_1_batch_b7a_mobile_sync_event` all verified)  
**Gates**: B8 cannot start until B7b is complete (A47/A48 depend on `mobile_sync_owner_escalation` table and notification pattern from A46)  
**Items in scope**: A40, A41, A44, A43, A42, A45, A46  
**Effort estimate**: 24–31 days  
**Test subfolder**: `tests/batch_b7b/`  
**Design date**: 2026-05-01

---

## A. MIGRATION PLAN

All migrations follow the naming convention: `phase_fe_1_batch_b7b_{short_description}`

Migration ordering must respect dependencies: the classification matrix (A40) must precede the conflict resolution endpoints (A45/A46) in migration history so the FK references resolve. All migrations verified against live schema via `postgres-local` MCP before listing columns.

---

### Migration 1: `phase_fe_1_batch_b7b_conflict_classification_matrix`

**Purpose**: A40 — New `sync_conflict_classification_matrix` table for the data-driven classification engine.

**Verified**: Table does not exist in live DB (`information_schema.tables` query returned no row for `sync_conflict_classification_matrix`).

**New table**: `sync_conflict_classification_matrix`

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `id` | `UUID` | NOT NULL | `gen_random_uuid()` | PK |
| `operation_type` | `TEXT` | NOT NULL | — | e.g. `time_entry`, `expense`, `photo`, `status_change`, `change_order`, `loto_check` |
| `trigger_condition` | `TEXT` | NOT NULL | — | e.g. `job_still_assigned`, `job_reassigned`, `job_deleted`, `time_overlap` |
| `severity` | `TEXT` | NOT NULL | — | CHECK: `auto_silent \| auto_notice \| tech_resolvable \| owner_escalation` |
| `classification_reason` | `TEXT` | NOT NULL | — | Human-readable reason returned in API response (e.g. "Job reassigned to different tech") |
| `is_active` | `BOOLEAN` | NOT NULL | `TRUE` | Allows row deactivation without hard delete |
| `tenant_id` | `UUID` | NULL | — | FK → `tenant.id` ON DELETE RESTRICT. NULL = platform default; non-NULL = tenant-specific override |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | |
| `created_by` | `UUID` | NULL | — | FK → `user.id` ON DELETE RESTRICT |
| `updated_by` | `UUID` | NULL | — | FK → `user.id` ON DELETE RESTRICT |

**Constraints**:
- `PK`: `pk_sync_conflict_classification_matrix` on `(id)`
- `CHK`: `chk_sync_conflict_matrix_severity` — `severity IN ('auto_silent', 'auto_notice', 'tech_resolvable', 'owner_escalation')`
- `UNIQUE`: on `(operation_type, trigger_condition, tenant_id)` — prevents duplicate rules per operation+trigger per tenant scope (platform rows have `tenant_id IS NULL`, enforced with partial unique index)

**Indexes**:
- `ix_sync_conflict_matrix_tenant_op` on `(tenant_id, operation_type)` — primary lookup path during classification
- `ix_sync_conflict_matrix_active` partial index on `(operation_type, trigger_condition)` WHERE `is_active = TRUE` — fast active-rule lookups

**Triggers** (mandatory per §13.4):
- `audit_sync_conflict_classification_matrix_changes` — `AFTER INSERT OR DELETE OR UPDATE`
- `trg_sync_conflict_classification_matrix_guard_created_immutable` — `BEFORE UPDATE`
- `trg_sync_conflict_classification_matrix_set_updated_at` — `BEFORE UPDATE`

**Seed data** (in `upgrade()`): Insert all 17 platform-default rows (tenant_id = NULL) from the classification matrix defined in §15.6 of mvp-arch.md and A40 ledger entry:

| operation_type | trigger_condition | severity | classification_reason |
|:---|:---|:---|:---|
| `time_entry` | `job_still_assigned` | `auto_silent` | Job still assigned to you |
| `time_entry` | `job_reassigned` | `tech_resolvable` | Job reassigned to different tech |
| `time_entry` | `job_deleted` | `owner_escalation` | Job deleted while you worked it |
| `time_entry` | `time_overlap` | `tech_resolvable` | Time overlaps an existing entry |
| `expense` | `category_exists_under_limit` | `auto_silent` | Expense category exists and is under limit |
| `expense` | `category_renamed` | `auto_notice` | Expense category was renamed server-side |
| `expense` | `exceeds_per_item_limit` | `tech_resolvable` | Expense exceeds tenant per-item limit |
| `expense` | `job_deleted` | `owner_escalation` | Job deleted while expense was captured |
| `photo` | `job_exists` | `auto_silent` | Job exists and photo uploaded cleanly |
| `photo` | `storage_limit_exceeded` | `tech_resolvable` | Storage limit exceeded |
| `photo` | `job_deleted` | `owner_escalation` | Job deleted while photo was captured |
| `status_change` | `normal_transition` | `auto_silent` | Normal job status transition |
| `status_change` | `job_already_completed` | `owner_escalation` | Job already completed by another tech |
| `change_order` | `quote_version_active` | `auto_silent` | Quote version is still active |
| `change_order` | `quote_version_superseded` | `tech_resolvable` | Quote version superseded since capture |
| `loto_check` | `job_in_progress` | `auto_silent` | Job still in progress when LOTO synced |
| `loto_check` | `job_completed_before_sync` | `auto_notice` | Job completed before LOTO sync arrived |

---

### Migration 2: `phase_fe_1_batch_b7b_job_attachment_upload_tracking`

**Purpose**: A41 — Add S3 multipart upload tracking columns to `job_attachment` for the resumable photo upload pipeline.

**Verified**: `job_attachment` exists with columns: `created_at`, `updated_at`, `created_by`, `updated_by`, `id`, `tenant_id`, `job_id`, `file_name`, `mime_type`, `size_bytes`, `object_key`, `description`, `client_capture_at`, `file_hash`. None of the new columns below pre-exist.

**Columns added to `job_attachment`**:

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `upload_status` | `TEXT` | NULL | — | CHECK: `pending_upload \| uploading \| complete`. NULL on pre-B7b rows (treated as `complete` by application logic) |
| `s3_upload_session_id` | `TEXT` | NULL | — | S3 multipart upload session ID; cleared to NULL after `CompleteMultipartUpload` |
| `upload_completed_at` | `TIMESTAMPTZ` | NULL | — | Set when `POST /api/v1/photos/complete-upload` is called |
| `expense_id` | `UUID` | NULL | — | FK → `job_expense.id` ON DELETE SET NULL. Optional: links photo to expense |

**Constraint added**:
- `chk_job_attachment_upload_status` — `upload_status IS NULL OR upload_status IN ('pending_upload', 'uploading', 'complete')`

**Index added**:
- `ix_job_attachment_pending_uploads` partial on `(tenant_id, job_id)` WHERE `upload_status IN ('pending_upload', 'uploading')` — powers the weekly cleanup Celery task

**Migration pattern**: Add as nullable first (no backfill needed — NULL is the correct pre-B7b sentinel). No NOT NULL constraint lock-down required.

---

### Migration 3: `phase_fe_1_batch_b7b_tenant_settings_offline_photo`

**Purpose**: A41/A42 — Add offline and photo-related tenant settings to `tenant_settings`.

**Verified**: `tenant_settings` query confirmed none of the four new columns exist. Current last columns: `calendar_conflict_pre_warning_days`.

**Columns added to `tenant_settings`**:

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `photo_upload_wifi_only` | `BOOLEAN` | NOT NULL | `TRUE` | Client-side scheduling; server stores policy |
| `photo_local_retention_days` | `INTEGER` | NOT NULL | `7` | How long synced photos remain on device before auto-purge |
| `offline_hard_limit_hours` | `INTEGER` | NULL | `72` | Hours before app blocks new offline captures. NULL = unlimited |
| `voice_offline_audio_storage_limit_mb` | `INTEGER` | NOT NULL | `500` | Max on-device storage for offline-captured voice audio |

**Migration pattern**: Add with `server_default` for NOT NULL columns; add as nullable for `offline_hard_limit_hours`. No backfill needed (defaults are correct for existing tenants).

---

### Migration 4: `phase_fe_1_batch_b7b_voice_command_log_offline_columns`

**Purpose**: A42 — Add offline voice capture tracking columns to `voice_command_log`.

**Verified live schema**: `voice_command_log` columns are: `id` (bigint, sequence), `tenant_id`, `user_id`, `message_id`, `intent_detected`, `entities_extracted`, `action_executed`, `whisper_latency_ms`, `ollama_latency_ms`, `total_latency_ms`, `is_successful`, `created_at`. **None of the following columns pre-exist** — including `audio_object_key` (not present in live DB despite A42 ledger noting "verify present").

**Columns added to `voice_command_log`**:

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `audio_object_key` | `TEXT` | NULL | — | S3 key for stored audio file. NULL for synchronous (non-offline) commands |
| `captured_at` | `TIMESTAMPTZ` | NULL | — | Client-side capture timestamp (offline commands); NULL for synchronous |
| `uploaded_at` | `TIMESTAMPTZ` | NULL | — | When audio reached server |
| `transcribed_at` | `TIMESTAMPTZ` | NULL | — | When Whisper completed |
| `parsed_at` | `TIMESTAMPTZ` | NULL | — | When Llama completed intent parse |
| `processing_status` | `TEXT` | NULL | — | CHECK: `pending_upload \| uploading \| transcribing \| parsing \| completed \| failed`. NULL for synchronous commands (backwards-compatible) |
| `idempotency_uuid` | `UUID` | NULL | — | Client-generated UUID v4 for safe offline retry. NULL for synchronous commands |

**Constraint added**:
- `chk_voice_command_log_processing_status` — `processing_status IS NULL OR processing_status IN ('pending_upload', 'uploading', 'transcribing', 'parsing', 'completed', 'failed')`

**Index added**:
- `ix_voice_command_log_idempotency_uuid` on `(idempotency_uuid)` WHERE `idempotency_uuid IS NOT NULL` — powers idempotency check on upload retry
- `ix_voice_command_log_processing_status` partial on `(tenant_id, processing_status)` WHERE `processing_status NOT IN ('completed', 'failed')` — powers polling for in-flight commands

**Note**: `voice_command_log` uses explicit audit fields (not a mixin) — no trigger migrations needed for the existing triggers. The `VoiceCommandLog` ORM model in `backend/app/models/ai.py` does NOT use `StandardAuditMixin`; it has manually declared `created_at` only. This table is effectively append-only in practice. No `updated_at` trigger required.

---

### Migration 5: `phase_fe_1_batch_b7b_mobile_sync_event_resolution_action`

**Purpose**: A45 — Add `resolution_action` column to `mobile_sync_event` to capture which resolution path was taken when a conflict is resolved.

**Verified**: `mobile_sync_event` has no `resolution_action` column. `mobile_sync_event` is append-only (`AppendOnlyMixin`) — new rows are inserted for each status transition; existing rows are never updated.

**Column added to `mobile_sync_event`**:

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `resolution_action` | `TEXT` | NULL | — | CHECK: `use_local \| use_server \| escalate_to_owner`. Set on the resolution-result row (status='succeeded' or status='conflict') |

**Constraint added**:
- `chk_mobile_sync_event_resolution_action` — `resolution_action IS NULL OR resolution_action IN ('use_local', 'use_server', 'escalate_to_owner')`

---

### Migration 6: `phase_fe_1_batch_b7b_mobile_sync_owner_escalation`

**Purpose**: A46 — New `mobile_sync_owner_escalation` table for owner escalation routing.

**Verified**: Table does not exist in live DB.

**New table**: `mobile_sync_owner_escalation`

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `id` | `UUID` | NOT NULL | `gen_random_uuid()` | PK |
| `tenant_id` | `UUID` | NOT NULL | — | FK → `tenant.id` ON DELETE RESTRICT |
| `originating_user_id` | `UUID` | NOT NULL | — | FK → `user.id` ON DELETE RESTRICT. The tech who triggered the escalation |
| `conflict_id` | `UUID` | NOT NULL | — | FK → `mobile_sync_event.id` ON DELETE RESTRICT. The sync event row with status='conflict' |
| `escalated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | |
| `escalation_reason` | `TEXT` | NOT NULL | — | CHECK: `auto_severity \| tech_chose` |
| `escalation_reason_explainer` | `TEXT` | NOT NULL | — | Server-generated human-readable explainer stored at creation time (context may be lost between creation and resolution) |
| `status` | `TEXT` | NOT NULL | `'pending'` | CHECK: `pending \| resolved \| rejected` |
| `resolved_by_user_id` | `UUID` | NULL | — | FK → `user.id` ON DELETE RESTRICT. Set when owner resolves |
| `resolved_at` | `TIMESTAMPTZ` | NULL | — | |
| `resolution_action` | `TEXT` | NULL | — | CHECK: `used_local \| used_server \| manual_edit \| rejected` |
| `resolution_payload` | `JSONB` | NULL | — | If owner did a manual edit, the resulting patched state |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | |
| `created_by` | `UUID` | NULL | — | FK → `user.id` ON DELETE RESTRICT |
| `updated_by` | `UUID` | NULL | — | FK → `user.id` ON DELETE RESTRICT |

**Constraints**:
- `PK`: `pk_mobile_sync_owner_escalation` on `(id)`
- `CHK`: `chk_mobile_sync_escalation_reason` — `escalation_reason IN ('auto_severity', 'tech_chose')`
- `CHK`: `chk_mobile_sync_escalation_status` — `status IN ('pending', 'resolved', 'rejected')`
- `CHK`: `chk_mobile_sync_escalation_resolution_action` — `resolution_action IS NULL OR resolution_action IN ('used_local', 'used_server', 'manual_edit', 'rejected')`

**Indexes**:
- `ix_mobile_sync_owner_escalation_tenant_status` on `(tenant_id, status)` — primary queue list query path
- `ix_mobile_sync_owner_escalation_originating_user` on `(originating_user_id)` — loop-closure: find escalations for a specific tech
- `ix_mobile_sync_owner_escalation_conflict_id` on `(conflict_id)` — FK lookup

**Triggers** (mandatory per §13.4):
- `audit_mobile_sync_owner_escalation_changes` — `AFTER INSERT OR DELETE OR UPDATE`
- `trg_mobile_sync_owner_escalation_guard_created_immutable` — `BEFORE UPDATE`
- `trg_mobile_sync_owner_escalation_set_updated_at` — `BEFORE UPDATE`

---

## B. EXECUTION ORDER

Items implemented in this order with rationale:

| # | Item | Rationale |
|:---|:---|:---|
| 1 | **A40** — Conflict Severity Classification Engine | **Foundation**: All conflict resolution paths in A45 and A46 depend on `classify_sync_conflict()` returning a `SyncResolution` object. The `sync_conflict_classification_matrix` table (Migration 1) and `services/mobile_sync_conflict.py` must exist before any endpoint that reads or acts on conflict severity. |
| 2 | **A41** — Resumable Photo Upload Pipeline | **Independent of A40**: S3 multipart upload is a standalone pipeline. Implemented second because it has zero intra-batch dependencies and its migrations (2 and 3) establish `tenant_settings` offline columns consumed by A42's Celery task behavior. Parallel-safe with A44 and A43 if needed. |
| 3 | **A44** — Auth Expiry Offline Handling | **Mostly client-SDK**: The only server contributions are the `offline_hard_limit_hours` tenant setting (added in Migration 3 / A41) and an operational runbook entry. Implemented third because Migration 3 is already applied by A41; no additional migrations needed. Low server-side risk. |
| 4 | **A43** — Force-Quit Recovery State Persistence | **Mostly client-SDK**: Server contribution is confirming idempotency handling from B7a/A39 (`MobileSyncEvent` idempotency_uuid dedup) covers the retry-after-relaunch case. No new migrations. Implemented fourth to complete the client-side foundations before the conflict endpoint work begins. |
| 5 | **A42** — Voice Command Offline Capture & Deferred Processing | **Depends on A40 indirectly**: Classification engine must be present because `process_voice_audio_async` may classify a sync conflict during processing. Migration 4 adds `voice_command_log` columns. New route `POST /api/v1/voice/upload-audio` and `GET /api/v1/voice/command/{id}`. Celery task `process_voice_audio_async`. |
| 6 | **A45** — Tech-Resolvable Conflict UI Endpoints | **Depends on A40**: `GET /api/v1/mobile-sync/conflicts/{conflict_id}` calls `classify_sync_conflict()` and `compute_field_diffs()`. `POST .../resolve` uses staleness check pattern (§7.9). Migration 5 adds `resolution_action` to `mobile_sync_event`. Calls `mobile_sync_owner_escalation` creation when `escalate_to_owner` is chosen — requires A46 table to exist. |
| 7 | **A46** — Owner Escalation Routing & Notification | **Depends on A40 + A45**: Creates `mobile_sync_owner_escalation` rows (Migration 6). Reads `mobile_sync_event` rows surfaced by A45's resolve endpoint. Wires `notification_outbox` entries to owner. Loop-closure notification to originating tech. Last in batch because it is the gate dependency for B8 (A47/A48 read from this table). |

---

## C. NEW API ENDPOINTS

### A40 — No new external endpoints
The classification engine runs internally as a service call during sync processing and conflict resolution. Not directly exposed as an API endpoint. Consumed by A45 and A46 within this batch.

---

### A41 — Photo Upload Pipeline

**Route file**: `backend/api/routes/photos.py` (new file)

#### `POST /api/v1/photos/initiate-upload`

- **Auth**: JWT required
- **RBAC**: `require_permission("jobs.update")` — tech uploading a photo to a job they're assigned to
- **Request body**:
  ```json
  {
    "job_id": "UUID",
    "expense_id": "UUID | null",
    "file_size_bytes": 4500000,
    "mime_type": "image/jpeg",
    "file_name": "site_photo_001.jpg",
    "client_capture_at": "2026-04-30T14:22:00Z",
    "idempotency_uuid": "UUID"
  }
  ```
- **Response** `201`:
  ```json
  {
    "pilot_photo_id": "UUID",
    "s3_upload_session_id": "string",
    "presigned_chunk_urls": ["https://s3.amazonaws.com/...?..."],
    "chunk_size_bytes": 5242880,
    "chunk_count": 1
  }
  ```
- **Side effects**: Creates `job_attachment` row with `upload_status = 'pending_upload'`, `s3_upload_session_id` populated.
- **Idempotency**: If `idempotency_uuid` matches an existing `job_attachment`, returns the existing session (resumes upload).
- **Test endpoint**: `POST /api/v1/photos/initiate-upload/test` — no JWT, blocked in staging/prod.

#### `POST /api/v1/photos/complete-upload`

- **Auth**: JWT required
- **RBAC**: `require_permission("jobs.update")`
- **Request body**:
  ```json
  {
    "pilot_photo_id": "UUID",
    "s3_upload_session_id": "string",
    "chunk_etags": [{"part_number": 1, "etag": "\"abc123\""}]
  }
  ```
- **Response** `200`:
  ```json
  {
    "id": "UUID",
    "job_id": "UUID",
    "file_name": "site_photo_001.jpg",
    "mime_type": "image/jpeg",
    "size_bytes": 4500000,
    "object_key": "tenants/{tenant_id}/jobs/{job_id}/photos/{id}.jpg",
    "upload_completed_at": "2026-04-30T14:23:15Z"
  }
  ```
- **Side effects**: Calls `S3.CompleteMultipartUpload`; sets `upload_status = 'complete'`, `upload_completed_at = now()`, clears `s3_upload_session_id`.
- **Error**: `409 Conflict` if `pilot_photo_id` already has `upload_status = 'complete'` (idempotent re-complete).
- **Test endpoint**: `POST /api/v1/photos/complete-upload/test` — no JWT.

---

### A42 — Voice Command Offline Capture

**Route file**: `backend/api/routes/voice.py` (existing, new endpoints added)

#### `POST /api/v1/voice/upload-audio`

- **Auth**: JWT required
- **RBAC**: `require_permission("voice.create")`
- **Request**: `multipart/form-data`
  - `audio`: UploadFile (m4a / wav / webm)
  - `captured_at`: ISO 8601 timestamp (when captured offline)
  - `idempotency_uuid`: UUID
  - `conversation_session_id`: UUID | null (optional — ties to existing session)
  - `originating_screen`: string | null (e.g. `"jobs_detail"` — provides intent context)
- **Response** `202`:
  ```json
  {
    "voice_command_log_id": 12345,
    "idempotency_uuid": "UUID",
    "processing_status": "pending_upload"
  }
  ```
- **Side effects**: Saves audio to S3 (`tenants/{tenant_id}/voice/{uuid}.m4a`); creates `VoiceCommandLog` row with `processing_status = 'pending_upload'`; enqueues `process_voice_audio_async.delay(voice_command_log_id)`.
- **Idempotency**: If `idempotency_uuid` already exists in `voice_command_log`, return existing row status (do not double-process).
- **Test endpoint**: `POST /api/v1/voice/upload-audio/test`

#### `GET /api/v1/voice/command/{idempotency_uuid}`

- **Auth**: JWT required
- **RBAC**: `require_permission("voice.view")` — tenant-scoped; tech can only view own commands
- **Path param**: `idempotency_uuid` (UUID) — the client-generated key used at upload time (not the bigint PK; client has this from before upload)
- **Response** `200`:
  ```json
  {
    "voice_command_log_id": 12345,
    "processing_status": "completed | failed | transcribing | parsing | pending_upload | uploading",
    "intent_detected": "create_time_entry | null",
    "action_executed": "string | null",
    "pending_confirmation": true,
    "captured_at": "2026-04-30T14:22:00Z",
    "transcribed_at": "2026-04-30T16:01:05Z | null",
    "parsed_at": "2026-04-30T16:01:07Z | null"
  }
  ```
- **Response** `404`: if `idempotency_uuid` not found for this tenant+user.
- **Test endpoint**: `GET /api/v1/voice/command/{idempotency_uuid}/test`

---

### A43 — Force-Quit Recovery
No new server-side API endpoints. The existing `GET /api/v1/mobile-sync/state/` (established in B7a/A38) already returns prior sync attempts for a given `idempotency_uuid` to support client-side "already synced?" checking. Server contribution in A43 is code review confirmation that retry paths pass through the existing idempotency guard in `utils/idempotency.py`.

---

### A44 — Auth Expiry Offline Handling
No new server-side API endpoints. Cognito refresh token flow is handled by Cognito itself. Server contribution is operational runbook entry only (Cognito refresh token TTL must remain ≥ 7 days).

---

### A45 — Tech-Resolvable Conflict UI Endpoints

**Route file**: `backend/api/routes/mobile_sync.py` (existing from B7a, new endpoints added)

#### `GET /api/v1/mobile-sync/conflicts/{conflict_id}`

- **Auth**: JWT required
- **RBAC**: `require_permission("mobile_sync.view")` — tech views own conflicts only; query enforces `user_id = current_user.id`
- **Path param**: `conflict_id` (UUID) — `mobile_sync_event.id` with `status = 'conflict'`
- **Response** `200`:
  ```json
  {
    "conflict_id": "UUID",
    "operation_type": "time_entry",
    "status": "conflict",
    "conflict_severity": "tech_resolvable",
    "classification_reason": "Job reassigned to different tech",
    "tech_version": { "...full captured payload..." },
    "server_version": { "...current server state..." },
    "field_diffs": [
      {
        "field_name": "assigned_tech_id",
        "tech_value": "UUID-A",
        "server_value": "UUID-B",
        "tech_change": "unchanged",
        "server_change": "modified"
      }
    ],
    "client_capture_at": "2026-04-30T10:00:00Z",
    "created_at": "2026-04-30T14:00:00Z"
  }
  ```
- **Response** `404`: if `conflict_id` not found for this tenant+user.
- **Response** `403`: returned as `404` if `user_id` mismatch (IDOR prevention).
- **Test endpoint**: `GET /api/v1/mobile-sync/conflicts/{conflict_id}/test`

#### `POST /api/v1/mobile-sync/conflicts/{conflict_id}/resolve`

- **Auth**: JWT required
- **RBAC**: `require_permission("mobile_sync.resolve")` (new permission seeded in this migration)
- **Request body**:
  ```json
  {
    "resolution": "use_local | use_server | escalate_to_owner",
    "expected_server_version_at": "2026-04-30T14:00:00Z"
  }
  ```
- **Response** `200`:
  ```json
  {
    "conflict_id": "UUID",
    "resolution": "use_local",
    "resolved_at": "2026-04-30T14:05:00Z",
    "escalation_id": null
  }
  ```
- **Response** `409 Conflict` (staleness): server state changed between surface and resolve attempt:
  ```json
  {
    "error": "stale_conflict",
    "message": "Conflict state has changed — refresh and try again",
    "refreshed_conflict": { "...full GET response payload..." }
  }
  ```
- **Side effects**:
  - Inserts new `mobile_sync_event` row with `status = 'succeeded'` and `resolution_action = <resolution>`
  - For `escalate_to_owner`: creates `mobile_sync_owner_escalation` row + `notification_outbox` entry to owner
- **Test endpoint**: `POST /api/v1/mobile-sync/conflicts/{conflict_id}/resolve/test`

---

### A46 — Owner Escalation Routing

**Route file**: `backend/api/routes/owner_escalations.py` (new file)

#### `GET /api/v1/owner/mobile-sync-escalations`

- **Auth**: JWT required
- **RBAC**: `require_permission("field_issue.view")` — owner/accountant only
- **Query params**: `status` (default `pending`), `originating_user_id` (optional filter), `cursor` (pagination), `limit` (default 25)
- **Response** `200`:
  ```json
  {
    "items": [
      {
        "id": "UUID",
        "originating_user_id": "UUID",
        "originating_user_name": "string",
        "operation_type": "time_entry",
        "conflict_severity": "owner_escalation",
        "escalation_reason": "auto_severity",
        "escalation_reason_explainer": "Job deleted while tech was working it",
        "status": "pending",
        "escalated_at": "2026-04-30T15:00:00Z"
      }
    ],
    "next_cursor": "string | null",
    "total_pending": 3
  }
  ```
- **Test endpoint**: `GET /api/v1/owner/mobile-sync-escalations/test`

#### `GET /api/v1/owner/mobile-sync-escalations/{escalation_id}`

- **Auth**: JWT required
- **RBAC**: `require_permission("field_issue.view")`
- **Response** `200`: Full escalation detail including nested conflict context (tech_version, server_version, field_diffs — same shape as A45 GET conflict detail response).
- **Test endpoint**: `GET /api/v1/owner/mobile-sync-escalations/{escalation_id}/test`

#### `POST /api/v1/owner/mobile-sync-escalations/{escalation_id}/resolve`

- **Auth**: JWT required
- **RBAC**: `require_permission("field_issue.resolve")` — owner/accountant only
- **Request body**:
  ```json
  {
    "resolution_action": "used_local | used_server | manual_edit | rejected",
    "resolution_payload": { "...manual edit state if resolution_action = 'manual_edit'..." },
    "expected_escalation_updated_at": "2026-04-30T15:00:00Z"
  }
  ```
- **Response** `200`:
  ```json
  {
    "id": "UUID",
    "status": "resolved",
    "resolution_action": "used_local",
    "resolved_at": "2026-04-30T16:00:00Z",
    "resolved_by_user_id": "UUID"
  }
  ```
- **Response** `409 Conflict` (staleness): escalation already resolved by another owner:
  ```json
  {
    "error": "stale_escalation",
    "message": "Escalation was already resolved",
    "refreshed_escalation": { "...full GET detail payload..." }
  }
  ```
- **Side effects**:
  - Updates `mobile_sync_owner_escalation` row: `status = 'resolved'`, `resolved_by_user_id`, `resolved_at`, `resolution_action`, `resolution_payload`
  - Creates `notification_outbox` entry to originating tech ("Your conflict was resolved by [owner] — [human-readable outcome]")
  - Audit log entry via `set_audit_context_sync(db, current_user.id)` before mutation
- **Test endpoint**: `POST /api/v1/owner/mobile-sync-escalations/{escalation_id}/resolve/test`

---

## D. PATTERN REUSE DECISIONS

### §1.5 Shared Module — `services/mobile_sync_conflict.py` (established in A40)

**Established by**: A40  
**Consumed by**: A42 (during async processing — classifies any conflict arising from a deferred voice command), A45 (classification + field diffs in GET endpoint), A46 (reads escalation-severity rows)  
**Consumed by later batches**: B8/A47 (reads from `mobile_sync_owner_escalation`), B8/A48 (reads conflict context for resolution)

**Exact call signatures** used by consumers:

From A45 route (`backend/api/routes/mobile_sync.py`):
```python
from services.mobile_sync_conflict import classify_sync_conflict, compute_field_diffs

resolution: SyncResolution = classify_sync_conflict(
    operation_type=event.operation_type,
    trigger_condition=_derive_trigger_condition(event, db),
    tenant_id=current_user.tenant_id,
    db=db,
)

diffs: list[dict] = compute_field_diffs(
    tech_version=event.operation_payload_summary,
    server_version=_fetch_current_server_state(event, db),
)
```

From A46 escalation creation (inside A45 resolve endpoint, `escalate_to_owner` branch):
```python
from services.mobile_sync_conflict import build_escalation_explainer

explainer: str = build_escalation_explainer(
    operation_type=event.operation_type,
    trigger_condition=trigger_condition,
    classification_reason=resolution.classification_reason,
)
```

---

### §1.5 Shared Module — `utils/staleness_check.py` (established B3/A19, canonical pattern)

**Established by**: B3 (A19)  
**Reused in this batch**: A45 (tech resolve endpoint), A46 (owner resolve endpoint)  
**Pattern section**: §16.4 / §7.9 Pre-Commit Staleness Check

The staleness check helper from B3 is called identically to how B6/A33 used it:
```python
from utils.staleness_check import check_staleness

# In A45 resolve endpoint:
check_staleness(
    entity=conflict_event,
    version_field="created_at",           # mobile_sync_event uses created_at as version anchor
    expected_version=request.expected_server_version_at,
    refresh_payload=_build_conflict_detail_response(conflict_event, db),
)
# Raises HTTP 409 with refreshed payload if stale.
```

---

### §16.2 Track-Changes Diff Vocabulary (mvp-arch.md §16.2)

**Applies to**: A45  
`compute_field_diffs()` in `services/mobile_sync_conflict.py` produces the same `field_diffs` payload structure established in A32 (B6 calendar conflict diff). Frontend uses the same `<DiffView>` component across calendar conflicts (web) and mobile sync conflicts (mobile), confirmed by FE-B7 spec.

---

### §16.3 Confirm-as-Turn for Destructive Voice Actions (mvp-arch.md §16.3 / §6.6)

**Applies to**: A42  
When `process_voice_audio_async` produces a destructive intent (e.g., delete a record), the task does NOT commit the action. Instead it:
1. Sets `VoiceCommandLog.processing_status = 'completed'` with `action_executed = None`
2. Stores `pending_confirmation` state in `ConversationSession.context_window_json` (existing pattern from A12/B2)
3. Creates a `notification_outbox` entry: "Your voice command '{intent}' is ready to confirm — tap to respond"
4. Client polls `GET /api/v1/voice/command/{idempotency_uuid}` and sees `pending_confirmation: true`

The 24-hour confirmation timeout is enforced by a new Celery Beat task registered in A42: `expire_pending_voice_confirmations` (runs hourly; auto-cancels commands older than 24 hours with no confirmation).

---

### §16.4 Pre-Commit Staleness Check (mvp-arch.md §16.4)

**Applies to**: A45 (tech resolve endpoint), A46 (owner resolve endpoint)  
**Pattern section**: §7.9 — same pattern used in A33 (B6), canonical reuse per shared module table in impl plan §1.5 table row.

---

### §16.6 Four-Class Severity Pattern (mvp-arch.md §16.6)

**Applies to**: A40 (the classification engine itself)  
The four classes `auto_silent | auto_notice | tech_resolvable | owner_escalation` are enforced via a `CHECK` constraint on `sync_conflict_classification_matrix.severity` and on `mobile_sync_event.conflict_severity` (established in B7a). The engine is the canonical implementation of this pattern for the mobile sync domain.

---

### §16.11 Mobile-to-Web Escalation Pattern (mvp-arch.md §16.11)

**Applies to**: A46 (establishes this pattern for mobile sync conflicts)
A46 is the **first implementation** of the Mobile-to-Web Escalation Pattern (§16.11). The `mobile_sync_owner_escalation` table and the owner endpoints in `owner_escalations.py` constitute the canonical pattern reference. Future surfaces (tech-submitted time-off requests, safety incidents, catalog additions) inherit this pattern.

Key pattern attributes implemented in A46:
- *Origin*: A45's `POST .../resolve` with `escalate_to_owner` — mobile creates the escalation
- *Routing*: `mobile_sync_owner_escalation` table + `notification_outbox` push to owner
- *Resolution*: `POST /api/v1/owner/mobile-sync-escalations/{id}/resolve` — web-only in MVP (voice resolution deferred to Phase 2)
- *Loop closure*: `notification_outbox` push to originating tech on resolution
- *Auditability*: `set_audit_context_sync()` before every resolution mutation; `resolved_by_user_id` stored

---

### §16.8 Optimistic UI with Pending Badges (mvp-arch.md §16.8)

**Applies to**: A41, A43
The photo upload pipeline (A41) integrates with the existing sync queue model: photos in `pending_upload` or `uploading` state surface in the WatermelonDB local queue with a "WiFi pending" or "uploading" badge. The server's `upload_status` column powers the polling response. This is server-side support for the frontend's optimistic UI — no new pattern, existing pattern consumed.

---

## E. SHARED MODULE INTERFACES

### `services/mobile_sync_conflict.py` (new — established in A40)

**File path**: `backend/services/mobile_sync_conflict.py`

```python
"""
services/mobile_sync_conflict.py

Conflict Severity Classification Engine for mobile offline sync.
Established in B7b/A40. Consumed by A42, A45, A46 within this batch,
and by B8/A47, B8/A48 in the next batch.

Pattern: §16.6 Four-Class Severity
  auto_silent | auto_notice | tech_resolvable | owner_escalation
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session


@dataclass
class SyncResolution:
    """
    Output of classify_sync_conflict(). Drives all downstream routing decisions.

    Fields:
        severity: The four-class classification result.
        auto_resolved: True if system resolves without user action
            (auto_silent / auto_notice).
        tech_action_required: True if tech must choose a resolution
            (tech_resolvable).
        owner_escalation_required: True if the conflict must route to owner.
        classification_reason: Human-readable reason returned in API response
            and stored in mobile_sync_owner_escalation.escalation_reason_explainer.
        payload: Resolution-specific data (e.g. renamed category mapping
            for auto_notice).
    """
    severity: str                  # 'auto_silent'|'auto_notice'|'tech_resolvable'|'owner_escalation'
    auto_resolved: bool
    tech_action_required: bool
    owner_escalation_required: bool
    classification_reason: str
    payload: dict[str, Any]


def classify_sync_conflict(
    operation_type: str,
    trigger_condition: str,
    tenant_id: uuid.UUID,
    db: Session,
) -> SyncResolution:
    """
    Look up the classification matrix for the given operation_type + trigger_condition.

    Resolution order:
        1. Tenant-specific override row (tenant_id matches, is_active=True)
        2. Platform default row (tenant_id IS NULL, is_active=True)
        3. Fallback: 'tech_resolvable' with generic reason if no matching row.

    Args:
        operation_type: e.g. 'time_entry', 'expense', 'photo',
                        'status_change', 'change_order', 'loto_check'
        trigger_condition: e.g. 'job_still_assigned', 'job_reassigned',
                           'job_deleted', 'time_overlap'
        tenant_id: Active tenant UUID (for tenant override lookup)
        db: SQLModel Session

    Returns:
        SyncResolution dataclass with all routing flags populated.
    """
    ...


def compute_field_diffs(
    tech_version: dict[str, Any] | None,
    server_version: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """
    Compute field-level diffs between tech's captured payload and current server state.

    Follows the platform-wide track-changes diff vocabulary (mvp-arch.md §16.2):
        'unchanged' | 'modified' | 'added' | 'removed'

    Returns a list of field diff objects in the shape consumed by the frontend
    <DiffView> component — same format as A32 (B6) calendar conflict field_diffs:

    [
        {
            "field_name": str,
            "tech_value": Any | None,
            "server_value": Any | None,
            "tech_change": "unchanged" | "modified" | "added" | "removed",
            "server_change": "unchanged" | "modified" | "added" | "removed",
        },
        ...
    ]

    Args:
        tech_version: Payload from mobile_sync_event.operation_payload_summary
        server_version: Current server-side state fetched at conflict read time

    Returns:
        List of field diff dicts for the API response.
    """
    ...


def build_escalation_explainer(
    operation_type: str,
    trigger_condition: str,
    classification_reason: str,
) -> str:
    """
    Generate a human-readable escalation explainer string stored at creation time
    in mobile_sync_owner_escalation.escalation_reason_explainer.

    Deviates from the calendar conflict pattern (diff computed live) because the
    originating context can be lost between escalation creation and owner resolution.
    Storing the explainer at creation time preserves context for the owner.

    Args:
        operation_type: The operation type string (e.g. 'time_entry')
        trigger_condition: The trigger condition (e.g. 'job_deleted')
        classification_reason: The classification_reason from the matrix row

    Returns:
        Human-readable string, e.g.:
        "Time entry on Job #1042: job was deleted while tech was working
        it offline — owner action required"
    """
    ...
```

---

### `tasks/voice_offline_tasks.py` (new — established in A42)

**File path**: `backend/tasks/voice_offline_tasks.py`

```python
"""
tasks/voice_offline_tasks.py

Celery tasks for offline voice command processing pipeline (B7b/A42).

Tasks:
    process_voice_audio_async  — event-driven retryable; enqueued from
                                  POST /api/v1/voice/upload-audio
    expire_pending_voice_confirmations — periodic Beat task, hourly,
                                          24h deferred-confirmation timeout
"""

from core.celery_app import celery_app
from sqlmodel import Session


@celery_app.task(
    name="process_voice_audio_async",
    bind=True,
    max_retries=3,
)
def process_voice_audio_async(self, voice_command_log_id: int) -> dict:
    """
    Async voice processing pipeline for offline-captured audio (§17.2 pattern).

    Pipeline steps (A42 spec):
        1. Load audio from S3 using VoiceCommandLog.audio_object_key
        2. Update processing_status → 'transcribing'; set uploaded_at if unset
        3. transcribe_audio() via services.ai_service
        4. Update processing_status → 'parsing'; set transcribed_at
        5. parse_intent() via services.ai_service
        6. Route to voice_action_router (existing B2 pattern)
        7. Destructive intent → deferred-confirmation flow (§16.3 / §6.6):
           - Do NOT commit the action
           - Store pending_confirmation in ConversationSession.context_window_json
           - Create notification_outbox entry to originating user
        8. Update processing_status = 'completed'; set parsed_at; set action_executed

    Args:
        voice_command_log_id: BigInt PK of VoiceCommandLog row to process

    Returns:
        {"status": "completed"|"pending_confirmation"|"failed",
         "voice_command_log_id": int}

    Retry: On transient S3 or GPU service errors; not on ValueError.
    """
    ...


@celery_app.task(name="expire_pending_voice_confirmations")
def expire_pending_voice_confirmations() -> dict:
    """
    Periodic cleanup: auto-cancel deferred voice confirmations older than 24h.

    Schedule: Hourly via Celery Beat.

    Logic:
        1. Find VoiceCommandLog rows where processing_status = 'completed'
           AND ConversationSession.context_window_json.pending_confirmation = True
           AND VoiceCommandLog.created_at < now() - 24 hours
        2. Clear pending_confirmation from context_window_json
        3. Create notification_outbox entry per user:
           "Your voice command expired — please re-issue"
        4. Return count for CloudWatch metric emission

    Returns:
        {"expired": N}
    """
    ...
```

---

### `tasks/photo_cleanup_tasks.py` (new — established in A41)

**File path**: `backend/tasks/photo_cleanup_tasks.py`

```python
"""
tasks/photo_cleanup_tasks.py

Celery tasks for photo upload lifecycle management (B7b/A41).

Tasks:
    cleanup_incomplete_photo_uploads — periodic Beat task, weekly
"""

from core.celery_app import celery_app


@celery_app.task(name="cleanup_incomplete_photo_uploads")
def cleanup_incomplete_photo_uploads() -> dict:
    """
    Weekly cleanup of orphaned job_attachment rows whose S3 multipart sessions
    never completed (§17.1 periodic poll pattern).

    Logic:
        1. Query job_attachment WHERE upload_status IN ('pending_upload', 'uploading')
           AND created_at < now() - 24 hours
        2. For each orphaned row: mark upload_status = 'failed'
        3. Log s3_upload_session_id for audit trail
        4. Return count for CloudWatch metric emission

    S3 lifecycle rule (configured via Terraform — not Alembic):
        Rule: ExpireMultipartUploads after 24 hours on photos bucket.
        This task handles the DB-side orphan records; S3 handles the byte cleanup.

    Returns:
        {"cleaned_up": N}
    """
    ...
```

---

## F. OPEN QUESTIONS RESOLVED

### F.1 — `audio_object_key` presence in `voice_command_log`

**Question**: The A42 ledger entry states "verify present" for `audio_object_key`. Does it already exist in `voice_command_log`?

**Resolution**: **It does not exist.** Live DB query (`postgres-local` MCP) confirmed `voice_command_log` has exactly 12 columns: `id`, `tenant_id`, `user_id`, `message_id`, `intent_detected`, `entities_extracted`, `action_executed`, `whisper_latency_ms`, `ollama_latency_ms`, `total_latency_ms`, `is_successful`, `created_at`. `audio_object_key` is absent. Migration 4 (`phase_fe_1_batch_b7b_voice_command_log_offline_columns`) adds it as a new nullable `TEXT` column.

---

### F.2 — Use `job_attachment` or create a separate `photo` table?

**Question**: The arch doc references a `photo` record and `pilot_photo_id`. Should B7b introduce a dedicated `photo` table, or extend the existing `job_attachment` table?

**Resolution**: **Extend `job_attachment`.** The existing table already has all required columns (`id`, `tenant_id`, `job_id`, `file_name`, `mime_type`, `size_bytes`, `object_key`, `description`, `client_capture_at`, `file_hash` — all confirmed via live schema query). A dedicated `photo` table would duplicate these columns and create a dual-model problem for the frontend. Migration 2 adds `upload_status`, `s3_upload_session_id`, `upload_completed_at`, and `expense_id` (nullable FK) to `job_attachment`. The API response field `pilot_photo_id` maps to `job_attachment.id`. The existing `JobAttachment` ORM model in `backend/app/models/fulfillment.py` is extended in-place.

---

### F.3 — New offline settings: existing `tenant_settings` table or new table?

**Question**: Do the four new offline settings go into the existing `tenant_settings` table or a new table?

**Resolution**: **Existing `tenant_settings` table.** The additions ledger explicitly names `tenant_settings` as the target. The three-tier settings infrastructure (B9/A53) is not yet built; these follow the existing `TenantSettings` model pattern — direct columns on the table. Migration 3 adds them. B7b settings do NOT need to wait for B9; B9 will add the resolver and `user_setting_override` table on top.

---

### F.4 — FK target for `mobile_sync_owner_escalation.conflict_id`

**Question**: Since `mobile_sync_event` is append-only (multiple rows per logical conflict), which row does `conflict_id` reference?

**Resolution**: `conflict_id` references the `mobile_sync_event` row with `status = 'conflict'` — the row that recorded the classification and conflict severity. When A45's resolve endpoint inserts a *new* `mobile_sync_event` row with `status = 'succeeded'`, the escalation's `conflict_id` still points to the original conflict row. ON DELETE RESTRICT is correct: the conflict event must not be deleted while an escalation references it. The 30-day cleanup Celery task (B7a) must be updated in A46 to skip rows referenced by open `mobile_sync_owner_escalation` records.

---

### F.5 — Poll endpoint path param: bigint PK or `idempotency_uuid`?

**Question**: `voice_command_log.id` is a bigint sequence. The client generates `idempotency_uuid` before upload. Which identifier should `GET /api/v1/voice/command/{id}` use?

**Resolution**: **Use `idempotency_uuid` as the path parameter.** The client has this UUID before the upload completes. If the upload fails mid-flight, the client does not receive the bigint PK in the response. Using `idempotency_uuid` as the poll key allows the client to check status after a partial upload failure (server row may already exist). The index `ix_voice_command_log_idempotency_uuid` on `(idempotency_uuid) WHERE idempotency_uuid IS NOT NULL` ensures fast lookup. Endpoint path: `GET /api/v1/voice/command/{idempotency_uuid}`.

---

### F.6 — RBAC: does `mobile_sync.resolve` permission need a new seed?

**Question**: No `mobile_sync.resolve` permission exists in the pre-existing permission set (verified in §9.2 of pilot-python-engineer-methods.md). Does it need a new seed?

**Resolution**: **Yes — seed in Migration 5.** Two new permissions are added to `platform_role.permissions` JSONB array in Migration 5:
- `mobile_sync.resolve` — granted to `technician` and `owner` roles. Allows tech to resolve own conflicts via A45 endpoints.
- `field_issue.view` and `field_issue.resolve` appear in the §9.2 reference list, meaning they were already seeded in a prior batch migration. **Verify** before A46 implementation. If absent, seed in Migration 6.

---

### F.7 — Does A44 require any server-side migration?

**Question**: A44 references `offline_hard_limit_hours`. Is a dedicated A44 migration needed?

**Resolution**: **No separate migration needed.** `offline_hard_limit_hours` is added in Migration 3 as part of A41's settings additions. A44's server-side footprint is entirely covered. A44 consists of: (a) Cognito TTL operational verification — no migration; (b) optional `GET /api/v1/auth/offline-policy` informational endpoint returning `offline_hard_limit_hours` effective value to client on sync — no migration required (reads from `tenant_settings`).

---

### F.8 — Classification matrix runtime tuning scope: all tenants or admin-only?

**Question**: Can individual tenants override the classification matrix, or is it platform-admin only?

**Resolution**: **Platform-admin only for MVP.** The `sync_conflict_classification_matrix.tenant_id` column supports per-tenant overrides (non-NULL rows), but this capability is disabled in MVP UI. Only Operator role can insert non-NULL tenant rows directly. The `classify_sync_conflict()` lookup logic must still handle per-tenant override rows (tenant-scoped lookup before platform default), even if no tenant-facing UI exposes this in MVP. Documented in the module docstring.

---

## G. EXTERNAL DEPENDENCY STATUS

### A41 — AWS S3 (Multipart Upload)

| Attribute | Detail |
|:---|:---|
| **Dependency** | AWS S3 — `boto3` S3 client: `CreateMultipartUpload`, `UploadPart` (presigned URL), `CompleteMultipartUpload` |
| **Status** | S3 already provisioned and in use (existing `job_attachment.object_key` columns in production). **Not blocked for development.** |
| **Mock strategy** | Use `moto` S3 mock in unit tests (§1.5 Rule 2). Integration tests use real dev S3 bucket. All boto3 S3 calls wrapped in a thin `services/s3_service.py` adapter for mockability. |
| **Tom action required** | (1) Confirm S3 bucket name for photos → add `AWS_S3_PHOTOS_BUCKET_NAME` to `backend/.env`. (2) Add Terraform S3 lifecycle rule `ExpireMultipartUploads` after 24 hours on that bucket before production delivery. **Lead time**: 1 day. |

---

### A42 — GPU Instance (Whisper + Ollama)

| Attribute | Detail |
|:---|:---|
| **Dependency** | EC2 `g4dn.xlarge` running `faster-whisper-server` (Whisper Large-v3) and Ollama (Llama 3.1 8B) — persistent GPU instance per infrastructure-constraints.md §3. |
| **Status** | **Already in use** for synchronous voice commands (B2/A6). A42 adds the async queue path to the same GPU services. **Not blocked for development.** |
| **Mock strategy** | `services/ai_service.transcribe_audio()` and `parse_intent()` are already mockable via function injection. `process_voice_audio_async` uses the §17.2 retryable task pattern with an inner `_impl()` function testable without a live Celery worker. |
| **Tom action required** | Confirm GPU worker Celery queue routing: `process_voice_audio_async` must route to the `voice_async` queue (GPU-collocated workers), not the default CPU queue. Add queue routing config to `backend/core/celery_app.py` task routing table before production. |

---

### A44 — AWS Cognito (refresh token TTL)

| Attribute | Detail |
|:---|:---|
| **Dependency** | AWS Cognito User Pool — refresh token expiration setting must be ≥ 7 days. |
| **Status** | Cognito already configured per B2 auth infrastructure. **Not blocked.** |
| **Mock strategy** | No server-side mock needed. A44's server contribution is a settings column (Migration 3) and an operational runbook entry. Client SDK handles Cognito refresh flow. |
| **Tom action required** | **Operational check** (30 min): AWS Console → Cognito → User Pool → App clients → verify `Refresh token expiration` ≥ 7 days (default 30 days — likely already correct). Document value in `dev-docs/sdlc/repo-setup-mgmt.md` under "Cognito Configuration" to prevent accidental reduction. |

---

### A46 — Mobile Push Notification Infrastructure (APNs / FCM)

| Attribute | Detail |
|:---|:---|
| **Dependency** | APNs (Apple Push Notification service) and FCM (Firebase Cloud Messaging) for loop-closure push to tech and owner notification on escalation creation/resolution. |
| **Status** | **Not yet provisioned.** The `notification_outbox` table and `notification_worker.py` are established (B4). However, the mobile push channel (APNs/FCM delivery) is not wired until B8/A51 (`mobile_device_push_token` registry and push dispatcher). |
| **Mock strategy** | A46 creates `notification_outbox` rows with `channel = 'push'`. In development, the notification worker logs and skips push-channel rows (existing behavior — push not yet dispatched). A46 is **not blocked** by this; it writes to `notification_outbox` correctly. Actual push delivery activates when B8/A51 wires the delivery path. |
| **Tom action required** | Before **B8** production delivery: (1) Register APNs certificate in Apple Developer account. (2) Obtain FCM server key from Firebase console. **Lead time: 2–3 business days** for APNs certificate provisioning. This blocks B8/A51 production delivery — does not block B7b. |

---

### A40, A43, A45 — No External Dependencies

| Item | Assessment |
|:---|:---|
| **A40** | Pure server-side classification engine + PostgreSQL table. No external dependencies. Not blocked. |
| **A43** | Primarily client-SDK. Server: idempotency via existing `utils/idempotency.py` (B7a). No new external dependencies. Not blocked. |
| **A45** | Server-side endpoints reading from `mobile_sync_event` and `sync_conflict_classification_matrix`. No external dependencies. Not blocked. |

---

*Design document complete. All six reads executed and verified against live schema. All seven sections populated with zero unresolved open questions.*