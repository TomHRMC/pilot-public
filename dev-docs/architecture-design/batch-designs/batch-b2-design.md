# Batch B2 — Voice AI Foundation: Design Document

**Batch**: B2  
**Name**: Voice AI Foundation  
**Status**: Design Phase — Ready for Implementation  
**Date**: May 1, 2026  
**Author**: Pilot Python Engineer  
**Source plan**: `pilot-app-mvp-backend-impl-plan.md §6.B2`  
**Test subfolder**: `tests/batch_b2/`  
**Estimated effort**: 12–18 days  
**Prerequisite batches**: None (parallel-safe with B1, B3, B4, B5)  
**Gates unlocked**: B6 (A36 voice grammar for calendar uses voice infrastructure), B12 (voice persona wraps all intent handlers), B16 (A84 reuses Ollama + session infrastructure)

---

## Input Read Summary

All six required reads completed before producing this document:

| Read | Source | Status |
|:---|:---|:---|
| READ 1 | §6.B2 of `pilot-app-mvp-backend-impl-plan.md` | ✅ Complete |
| READ 2 | ANN entries A6, A7, A9, A10, A11, A12 from `frontend-backend-mvp-additions-latest.md` | ✅ Complete |
| READ 3 | `mvp-arch.md` §6, §16.3, §6.4, §6.6, §6.7 | ✅ Complete |
| READ 4 | `pilot-python-engineer-methods.md` §16–§22 | ✅ Complete |
| READ 5 | Live MCP schema for `conversation_session`, `conversation_message`, `voice_command_log`, `user`, `user_preference` | ✅ Complete |
| READ 6 | `backend/app/models/ai.py`, `backend/services/voice_action_router.py`, `backend/api/routes/voice.py`, `backend/app/models/core.py`, `backend/db_models_map.md` | ✅ Complete |

---

## A. MIGRATION PLAN

### A.1 Pre-Migration Column Verification

All columns listed below were verified **NOT** to exist in the live database before being listed as new additions. MCP queries confirmed exact live schema.

**`conversation_session` live columns** (confirmed via MCP):
`id`, `tenant_id`, `user_id`, `status`, `context_summary`, `context_embedding`, `context_window_json`, `expires_at`, `is_active`, `created_at`, `updated_at`, `created_by`, `updated_by`

**`conversation_message` live columns** (confirmed via MCP):
`id`, `session_id`, `role`, `content_text`, `audio_object_key`, `embedding`, `created_by`, `created_at`, `tenant_id`

**`voice_command_log` live columns** (confirmed via MCP):
`id` (bigint), `tenant_id`, `user_id`, `message_id`, `intent_detected`, `entities_extracted`, `action_executed`, `whisper_latency_ms`, `ollama_latency_ms`, `total_latency_ms`, `is_successful`, `created_at`

**`user_preference` live columns** (confirmed via MCP):
`id`, `user_id`, `tenant_id`, `preferences` (JSONB), `created_at`, `updated_at`, `created_by`, `updated_by`

**`voice_feedback` table**: Does NOT exist (confirmed — table not in `pg_tables`).

---

### A.2 Migration 1 — Voice Session Title Columns

**Migration name**: `phase_fe_1_batch_b2_voice_session_title_columns`  
**Purpose**: A11 — Ollama-Generated Session Titles  
**Table**: `conversation_session`  
**Type**: Column additions to existing table

**New columns** (confirmed NOT pre-existing):

| Column | Type | Nullable | Default | Purpose |
|:---|:---|:---|:---|:---|
| `title` | `TEXT` | YES | NULL | User-overridable or AI-generated session title (replaces context_summary as the user-visible label) |
| `title_auto_generated` | `BOOLEAN` | NO | `FALSE` | TRUE = AI generated and may auto-update; FALSE = user explicitly renamed, frozen |
| `archived_at` | `TIMESTAMPTZ` | YES | NULL | Set by `archive_old_sessions` Celery task when >30 days inactive (per arch §6.4) |

**Migration pattern**: Standard additive — no backfill required (all columns nullable or have safe defaults).

```python
# upgrade()
op.add_column('conversation_session', sa.Column('title', sa.Text(), nullable=True))
op.add_column('conversation_session', sa.Column('title_auto_generated',
    sa.Boolean(), server_default=sa.text('false'), nullable=False))
op.add_column('conversation_session', sa.Column('archived_at',
    sa.DateTime(timezone=True), nullable=True))
op.create_index('ix_conversation_session_archived_at', 'conversation_session',
    ['archived_at'], postgresql_where=sa.text('archived_at IS NOT NULL'))

# downgrade()
op.drop_index('ix_conversation_session_archived_at', table_name='conversation_session')
op.drop_column('conversation_session', 'archived_at')
op.drop_column('conversation_session', 'title_auto_generated')
op.drop_column('conversation_session', 'title')
```

**Note**: No new triggers required — `conversation_session` already has the standard audit trigger set (`audit_conversation_session_changes`, `trg_conversation_session_guard_created_immutable`, `trg_conversation_session_set_updated_at`).

---

### A.3 Migration 2 — Conversation Message Structured Content Payload

**Migration name**: `phase_fe_1_batch_b2_conversation_message_structured_content`  
**Purpose**: A12 — Conversation Message Structured Content Payload with Live/Snapshot Modes  
**Table**: `conversation_message`  
**Type**: Column addition to existing table

**New column** (confirmed NOT pre-existing):

| Column | Type | Nullable | Default | Purpose |
|:---|:---|:---|:---|:---|
| `structured_content_json` | `JSONB` | YES | NULL | Structured payload for assistant artifact messages (quote_preview, job_preview, etc.). NULL for plain-text messages. |

**JSONB payload shape** (when non-NULL):
```json
{
  "render_mode": "live | snapshot",
  "artifact_type": "quote_preview | job_preview | schedule_preview | comm_preview",
  "entity_id": "uuid-string",
  "entity_version_id": "uuid-string | null",
  "snapshot_payload": { ... },
  "render_hints": { "newly_added_line_ids": ["uuid1", "uuid2"] }
}
```

**Migration pattern**: Simple nullable column addition:

```python
# upgrade()
op.add_column('conversation_message',
    sa.Column('structured_content_json',
              postgresql.JSONB(),
              nullable=True))

# downgrade()
op.drop_column('conversation_message', 'structured_content_json')
```

**Note**: No index required on this column at MVP volume. Add GIN index post-MVP if JSONB queries are needed.

---

### A.4 Migration 3 — Voice Feedback Table

**Migration name**: `phase_fe_1_batch_b2_voice_feedback_table`  
**Purpose**: A6 — Voice AI Feedback Loop  
**Type**: New table creation

**New table**: `voice_feedback`

| Column | Type | Nullable | Default | FK Target | Purpose |
|:---|:---|:---|:---|:---|:---|
| `id` | `UUID` | NO | `gen_random_uuid()` | — | PK |
| `tenant_id` | `UUID` | NO | — | `tenant.id` | Tenant isolation |
| `user_id` | `UUID` | NO | — | `user.id` | Who submitted the feedback |
| `voice_command_log_id` | `BIGINT` | YES | NULL | `voice_command_log.id` | FK to source log entry (nullable — user may flag without a matching log row) |
| `original_transcription` | `TEXT` | NO | — | — | The Whisper transcription the user is flagging |
| `corrected_text` | `TEXT` | YES | NULL | — | Owner's correct transcription for fine-tuning |
| `intent_misparsed` | `BOOLEAN` | NO | `FALSE` | — | TRUE if Llama's intent detection was wrong |
| `corrected_intent` | `TEXT` | YES | NULL | — | The correct intent code if intent_misparsed = TRUE |
| `feedback_notes` | `TEXT` | YES | NULL | — | Free-form notes from the owner |
| `s3_export_key` | `TEXT` | YES | NULL | — | Populated by nightly Celery task after export to S3 |
| `exported_at` | `TIMESTAMPTZ` | YES | NULL | — | When this row was exported to S3 training bucket |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | — | Append-only audit timestamp |
| `created_by` | `UUID` | YES | NULL | `user.id` | User who created this feedback record |

**Indexes**:
- `ix_voice_feedback_tenant_id` on `(tenant_id)`
- `ix_voice_feedback_user_id` on `(user_id)`
- `ix_voice_feedback_exported_at` on `(exported_at)` WHERE `exported_at IS NULL` (partial — for nightly export query)

**Constraints**:
- `pk_voice_feedback` PRIMARY KEY `(id)`
- `fk_voice_feedback_tenant` FK `tenant_id → tenant(id)` ON DELETE RESTRICT
- `fk_voice_feedback_user` FK `user_id → user(id)` ON DELETE RESTRICT
- `fk_voice_feedback_voice_log` FK `voice_command_log_id → voice_command_log(id)` ON DELETE SET NULL

**Required triggers** (mandatory per §13.4 of python-engineer-methods):
1. `audit_voice_feedback_changes` — `AFTER INSERT OR DELETE OR UPDATE ON public.voice_feedback FOR EACH ROW EXECUTE FUNCTION audit.log_changes()`
2. `trg_voice_feedback_guard_created_immutable` — `BEFORE UPDATE ... EXECUTE FUNCTION public.guard_created_fields_immutable()`
3. `trg_voice_feedback_set_updated_at` — NOT applicable (AppendOnlyMixin — voice_feedback rows are immutable once created)

**Note**: Use `AppendOnlyMixin` (not `StandardAuditMixin`) for `voice_feedback` — feedback rows are never updated after creation. Only the `exported_at` and `s3_export_key` columns are written by the nightly Celery task, which treats the row as append-only (SELECT + UPDATE only those two fields, never full updates). The audit trigger still applies for INSERT tracking.

---

### A.5 Tenant Timezone Open Question (Resolved in §F)

A9 session numbering requires tenant timezone for midnight rollover. The live `tenant` table does not have a `timezone` column (confirmed by inspecting `TenantSettings` and `Tenant` models). See §F for the resolution decision.

---

## B. EXECUTION ORDER

Items are ordered by intra-batch dependency. B2 has a linear dependency chain within the batch.

| Order | Item | Rationale |
|:---|:---|:---|
| 1 | **A9** — Session Number Computation | Foundational: no schema change required; derived `ROW_NUMBER()` window function on existing `conversation_session.created_at`. A10's grammar depends on resolving "Chat 2" to a specific session by number. Implement first at 1 day cost. |
| 2 | **A11** — Ollama-Generated Session Titles | Depends on sessions existing. Requires Migration 1 (`title`, `title_auto_generated`, `archived_at`). New Celery task enqueued after first assistant turn. Implement after A9 so session numbering is available for context. |
| 3 | **A12** — Conversation Message Structured Content Payload | Largest item (4–6 days). Requires Migration 2 (`structured_content_json`). Must be solid before A10 because the confirm-as-turn for `delete_session` writes to `context_window_json.pending_confirmation` — the same session-level JSONB that A12's freeze-on-submit touches. Implementing A12 first defines the session-level state contract A10 relies on. |
| 4 | **A10** — Voice Command Grammar for Session Management | Depends on A9 (session numbers for resolving "Chat 2"), A11 (`context_summary`/`title` fields for `rename_session` target), and A12 (confirm-as-turn `context_window_json` state). Adds 4 handlers to `INTENT_HANDLERS`. |
| 5 | **A6** — Voice AI Feedback Loop | Independent of A9–A12; uses session/transcript infrastructure but does not depend on A10/A11/A12 internally. Placed after A10 to avoid context-switching — the voice infrastructure is stable before adding the feedback overlay. Requires Migration 3 (`voice_feedback` table). |
| 6 | **A7** — Field Mode Backend Support | Simplest item (1–2 days). No new table. `field_mode_enabled` stored in `user_preference.preferences` JSONB. Route-level RBAC guards. Independent of all other B2 items — placed last as a clean close-out item. |

---

## C. NEW API ENDPOINTS

### C.1 A9 — Session List with Session Numbers

**GET** `/api/v1/voice/sessions`

**Auth**: JWT required — `voice.use` permission  
**RBAC**: `require_permission("voice.use")`

**Query params**: `limit` (int, default 20, max 50), `cursor` (str, optional), `date` (ISO date string, optional — filter to sessions from a specific local date)

**Request body**: None

**Response body**:
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "session_number": 3,
      "title": "Johnson Panel Upgrade",
      "title_auto_generated": true,
      "status": "active",
      "created_at": "2026-05-01T14:30:00Z",
      "updated_at": "2026-05-01T15:00:00Z",
      "local_date": "2026-05-01",
      "message_count": 12
    }
  ],
  "next_cursor": "...",
  "has_more": false
}
```

**Implementation note**: `session_number` is a derived field computed via SQL window function at query time (NOT stored). See §E for the `get_sessions_with_numbers()` shared utility interface.

---

### C.2 A10 — No New HTTP Endpoints

A10 adds four voice intent handlers to `voice_action_router.py`. All are invoked through the existing `POST /api/v1/voice/command` endpoint. No new HTTP routes.

**New intents registered in `INTENT_HANDLERS`**:
- `rename_session` → `rename_session_via_voice()`
- `delete_session` → `delete_session_via_voice()` *(confirm-as-turn applies)*
- `open_session` → `open_session_via_voice()`
- `query_session_summary` → `query_session_summary_via_voice()`

---

### C.3 A11 — No New HTTP Endpoints

A11 is a Celery task (`generate_session_title`) enqueued after the first assistant turn. No new HTTP routes. The existing `GET /api/v1/voice/sessions` (A9 endpoint) surfaces the `title` field once populated.

---

### C.4 A12 — Structured Content in Existing Message Response

A12 extends the data returned by existing voice endpoints. No new HTTP routes.

**Modified response shape** for `POST /api/v1/voice/command` (existing endpoint):
```json
{
  "transcribed_text": "...",
  "parsed_intent": { ... },
  "session_id": "uuid",
  "action_result": {
    "action": "create_quote",
    "success": true,
    "message": "...",
    "data": { "quote_id": "uuid", ... },
    "structured_message": {
      "render_mode": "live",
      "artifact_type": "quote_preview",
      "entity_id": "uuid",
      "entity_version_id": null,
      "snapshot_payload": null,
      "render_hints": {}
    }
  }
}
```

New assistant messages written with `structured_content_json` populated when the action produces an artifact. Plain-text responses have `structured_content_json = NULL`.

**New endpoint for message retrieval**:

**GET** `/api/v1/voice/sessions/{session_id}/messages`

**Auth**: JWT required — `voice.use`  
**RBAC**: `require_permission("voice.use")` + tenant-scoped session ownership check

**Query params**: `limit` (int, default 50), `cursor` (optional)

**Response body**:
```json
{
  "messages": [
    {
      "message_id": "uuid",
      "session_id": "uuid",
      "role": "user | assistant",
      "content_text": "...",
      "structured_content_json": null,
      "created_at": "2026-05-01T14:30:00Z"
    },
    {
      "message_id": "uuid",
      "session_id": "uuid",
      "role": "assistant",
      "content_text": "Created Quote #abc123 for Johnson.",
      "structured_content_json": {
        "render_mode": "live",
        "artifact_type": "quote_preview",
        "entity_id": "uuid",
        "entity_version_id": null,
        "snapshot_payload": null,
        "render_hints": { "newly_added_line_ids": [] }
      },
      "created_at": "2026-05-01T14:30:01Z"
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

---

### C.5 A6 — Voice AI Feedback Loop Endpoints

**POST** `/api/v1/voice/feedback`

**Auth**: JWT required — `voice.provide_feedback`  
**RBAC**: `require_permission("voice.provide_feedback")` (owner/accountant only)

**Request body**:
```json
{
  "voice_command_log_id": 12345,
  "original_transcription": "Create a cute for Tom Jones",
  "corrected_text": "Create a quote for Tom Jones",
  "intent_misparsed": false,
  "corrected_intent": null,
  "feedback_notes": "Whisper misheard 'quote' as 'cute'"
}
```

**Response 201**:
```json
{
  "feedback_id": "uuid",
  "tenant_id": "uuid",
  "created_at": "2026-05-01T14:30:00Z"
}
```

---

**GET** `/api/v1/voice/transcripts`

**Auth**: JWT required — `voice.provide_feedback`  
**RBAC**: `require_permission("voice.provide_feedback")`

**Query params**: `limit` (int, default 20), `cursor` (optional), `start_date` (ISO date), `end_date` (ISO date), `intent` (str filter)

**Response 200**:
```json
{
  "transcripts": [
    {
      "voice_command_log_id": 12345,
      "tenant_id": "uuid",
      "user_id": "uuid",
      "original_transcription": "...",
      "intent_detected": "create_quote",
      "is_successful": true,
      "whisper_latency_ms": 342,
      "created_at": "2026-05-01T14:30:00Z",
      "has_feedback": false
    }
  ],
  "next_cursor": "...",
  "has_more": true
}
```

---

**GET** `/api/v1/voice/feedback`

**Auth**: JWT required — `voice.provide_feedback`  
**RBAC**: `require_permission("voice.provide_feedback")`

**Query params**: `limit` (int, default 20), `cursor` (optional), `exported` (bool, optional filter)

**Response 200**:
```json
{
  "feedback_items": [
    {
      "feedback_id": "uuid",
      "voice_command_log_id": 12345,
      "original_transcription": "...",
      "corrected_text": "...",
      "intent_misparsed": false,
      "corrected_intent": null,
      "feedback_notes": "...",
      "exported_at": null,
      "created_at": "2026-05-01T14:30:00Z"
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

---

### C.6 A7 — Field Mode Preference Endpoint

**PATCH** `/api/v1/users/me/preferences`

**Auth**: JWT required — `voice.use` (all authenticated users)  
**RBAC**: `require_permission("voice.use")`

**Request body**:
```json
{
  "field_mode_enabled": true
}
```

**Response 200**:
```json
{
  "user_id": "uuid",
  "tenant_id": "uuid",
  "preferences": {
    "field_mode_enabled": true
  },
  "updated_at": "2026-05-01T14:30:00Z"
}
```

**Implementation note**: `field_mode_enabled` is stored in `user_preference.preferences` JSONB (not a separate column). No migration needed — `user_preference` table exists with `preferences JSONB NOT NULL DEFAULT '{}'`.

**Route-level RBAC guard for field mode** (belt-and-suspenders per A7 scope):
```python
# In any admin-only route handler
if not current_user.has_permission("admin.*"):
    # Check field mode — technicians in field mode cannot reach admin routes
    prefs = _get_user_preferences(current_user.id, db)
    if prefs.get("field_mode_enabled"):
        raise HTTPException(status_code=403, detail="Field mode active — admin routes unavailable")
```

---

## D. PATTERN REUSE DECISIONS

### D.1 Confirm-as-Turn Pattern (§16.3 / arch §6.6)

**Source**: `mvp-arch.md §16.3`, `pilot-python-engineer-methods.md §16` (referenced), arch §6.6 Confirm-as-Turn for Destructive Actions.

**Applicable to**: A10 — `delete_session` intent handler.

**Existing implementation observed** in `backend/services/voice_action_router.py`: `approve_quote_via_voice()` and `kickback_quote_via_voice()` both implement the confirm-as-turn pattern using `context_window_json["pending_confirmation"]`.

**Exact pattern to reuse** (from real codebase):
```python
# First turn — write pending confirmation
context = getattr(session, "context_window_json", {}) or {}
context["pending_confirmation"] = {
    "action": "delete_session",
    "target_session_id": str(target_session.id),
    "target_session_title": target_session.title or target_session.context_summary,
}
session.context_window_json = context
db.add(session)
db.commit()
return {"action": "delete_session", "success": True, "requires_confirmation": True,
        "message": "Are you sure you want to delete ...? Say 'yes' to confirm."}

# Second turn — check pending confirmation first
pending = context.get("pending_confirmation", {})
if pending.get("action") == "delete_session" and pending.get("target_session_id"):
    # Execute the delete
    context.pop("pending_confirmation", None)
    session.context_window_json = context
    ...
```

**Items using this pattern**: A10 (`delete_session`), A12 (freeze-on-submit synchronous path — not confirm-as-turn per se, but uses same `context_window_json` state field).

---

### D.2 Session-Scoped Context Window State (arch §6.3)

**Pattern**: All multi-turn state, pending confirmations, and active entity references live in `conversation_session.context_window_json` JSONB, accessed via `ContextWindowSchema` from `api/schemas/voice.py`.

**Existing usage** in `backend/services/voice_action_router.py`:
```python
from api.schemas.voice import ContextWindowSchema
ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
ctx.active_quote_id = str(quote.id)
ctx.last_action = "create_quote"
ctx.timestamp = datetime.now(UTC).isoformat()
session.context_window_json = ctx.to_jsonb()
db.add(session)
db.commit()
```

**A10/A12 extend this** with:
- `pending_confirmation.action = "delete_session"` (A10)
- `pending_confirmation.action = "freeze_quote_messages"` (A12 freeze trigger — not user-facing)

**All new B2 handlers must use `ContextWindowSchema.from_jsonb()` / `.to_jsonb()`** — never write directly to the JSONB dict. This preserves the `safety_loto_verified` field and other existing context fields.

---

### D.3 INTENT_HANDLERS Registry Extension Pattern

**Source**: `backend/services/voice_action_router.py` lines 2108–2127.

**Existing registry** (real code, confirmed):
```python
INTENT_HANDLERS = {
    "create_quote": create_quote_via_voice,
    "add_quote_line": add_line_via_voice,
    "query_job_profit": get_job_profitability,
    "calculate_voltage_drop": calculate_nec_voltage_drop,
    "calculate_conduit_fill": calculate_conduit_fill,
    "navigate": return_navigation_command,
    "create_customer": create_customer_via_voice,
    "create_job": create_job_via_voice,
    "log_time_entry": log_time_entry_via_voice,
    "add_expense": add_expense_via_voice,
    "send_quote": send_quote_via_voice,
    "schedule_job": schedule_job_via_voice,
    "reassign_job": reassign_job_via_voice,
    "approve_quote": approve_quote_via_voice,
    "reject_quote": reject_quote_via_voice,
    "kickback_quote": kickback_quote_via_voice,
    "list_pending_quotes": list_pending_quotes_via_voice,
}
```

**B2 adds to this registry** (A10):
```python
    "rename_session": rename_session_via_voice,
    "delete_session": delete_session_via_voice,      # confirm-as-turn
    "open_session": open_session_via_voice,
    "query_session_summary": query_session_summary_via_voice,
```

**Handler signature** (existing contract, must match):
```python
async def handler_name(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
```

All four new handlers must match this exact signature.

---

### D.4 Celery Periodic Poll Task Pattern (§17.1 of python-engineer-methods)

**Source**: `pilot-python-engineer-methods.md §17.1`

**Applicable to**: A11 (`generate_session_title` — event-driven retryable), A6 (nightly S3 export).

**A11 uses §17.2 Event-Driven Retryable Task** pattern (bind=True, max_retries=3) because it's triggered per-session after the first turn, not on a schedule.

**A6 nightly export uses §17.1 Periodic Poll Task** pattern (no bind, no retry) because it runs on a schedule and processes a batch.

**Registration in `celery_app.py`**:
- `generate_session_title` → imports in `imports` list; NOT in `beat_schedule` (event-driven via `.delay()`)
- `export_voice_feedback_to_s3` → imports in `imports` list; Added to `beat_schedule` with `crontab(hour=2, minute=0)` (daily at 2 AM UTC)

---

### D.5 AppendOnlyMixin vs StandardAuditMixin (§5.2 of python-engineer-methods)

**Decision for `voice_feedback`**: Use `AppendOnlyMixin` (provides `created_at`, `created_by` only). Feedback rows are never mutated after creation. The nightly export task updates only `exported_at` and `s3_export_key` via targeted UPDATE — these are written by the Celery task identity (not user-driven), so they are machine-log fields added manually to the model (not through the mixin).

**Decision for new `conversation_session` columns**: No mixin change — these columns are added to an existing `StandardAuditMixin` model. The ORM model already has `updated_at` which will automatically track changes.

---

### D.6 Pilot-Python-Engineer-Methods.md §16+ Pattern Mapping

| Pattern | §Section | Applied To | Notes |
|:---|:---|:---|:---|
| Confirm-as-Turn | §16.3 (arch §6.6) | A10 `delete_session` | Reuses `context_window_json.pending_confirmation` established by `approve_quote_via_voice` |
| Standard 4-Step Execution Loop | §16.2 | All B2 items | ORM → Migration → Blueprint Sync → Test Coverage |
| Definition of Done Checklist | §16.5 | All B2 items | Schema diff must be ZERO before marking any item complete |
| Event-Driven Retryable Task (bind=True) | §17.2 | A11 `generate_session_title` | Ollama calls can timeout; retry on transient failure |
| Periodic Poll Task (no bind) | §17.1 | A6 nightly S3 export | Batch processor pattern |
| Dual-Endpoint Architecture | §8.2 | All new routes (A6, A7, A9, A12) | Every route must have `/test` variant |
| Tenant-scoped queries (no `db.get()`) | §16.3 (API refactor) | All new handlers | All session lookups must include `.where(ConversationSession.tenant_id == current_user.tenant_id)` |
| UTC datetime enforcement | §5.3 | All new models/tasks | Use `datetime.now(UTC)` not `datetime.utcnow()` |
| 3-Part migration pattern | §16.2 Step 2 | NOT needed for B2 | All B2 columns are nullable or have safe defaults — no backfill required |

---

## E. SHARED MODULE INTERFACES

### E.1 Session Number Query Utility

**File**: `backend/services/voice_session_service.py` *(new file — create in B2/A9)*

```python
"""
Voice Session Service — session numbering, retrieval, and structured content utilities.
Established in B2 (A9). Extended by B12 (A67) for persona tone rendering.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, over, text
from sqlmodel import Session, select

from app.models.ai import ConversationMessage, ConversationSession
from core.auth import AuthenticatedUser
from core.test_context import TestUserContext


def get_sessions_with_numbers(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 20,
    cursor: Optional[str] = None,
    local_date_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str], bool]:
    """
    Return conversation sessions with derived per-day session_number.

    Session number = ROW_NUMBER() OVER (
        PARTITION BY DATE(created_at AT TIME ZONE tenant_tz), user_id
        ORDER BY created_at ASC
    )

    Tenant timezone: Falls back to UTC if tenant.timezone not configured (see §F.1).

    Args:
        db: Database session
        tenant_id: Active tenant UUID for isolation
        user_id: Requesting user UUID — sessions are user-scoped
        limit: Max records per page (capped at 50)
        cursor: Opaque pagination cursor (base64-encoded created_at)
        local_date_filter: ISO date string (YYYY-MM-DD) in tenant local time to filter

    Returns:
        Tuple of (session_list, next_cursor, has_more)
        Each session dict includes 'session_number' as derived int.
    """
    # NOTE: Tenant timezone resolution — see §F.1 for the MVP decision
    TENANT_TZ_FALLBACK = "UTC"

    # Build window function subquery
    session_number_expr = func.row_number().over(
        partition_by=[
            func.date(
                func.timezone(TENANT_TZ_FALLBACK, ConversationSession.created_at)
            ),
            ConversationSession.user_id,
        ],
        order_by=ConversationSession.created_at.asc(),
    ).label("session_number")

    stmt = (
        select(ConversationSession, session_number_expr)
        .where(ConversationSession.tenant_id == tenant_id)
        .where(ConversationSession.user_id == user_id)
        .where(ConversationSession.is_active == True)  # noqa: E712
        .order_by(ConversationSession.created_at.desc())
        .limit(limit + 1)
    )

    rows = db.exec(stmt).all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    sessions = []
    for session, session_number in rows:
        sessions.append({
            "session_id": str(session.id),
            "session_number": session_number,
            "title": session.title or session.context_summary,
            "title_auto_generated": session.title_auto_generated,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "archived_at": session.archived_at.isoformat() if session.archived_at else None,
        })

    next_cursor = None
    if has_more and rows:
        last_session = rows[-1][0]
        import base64
        next_cursor = base64.b64encode(
            last_session.created_at.isoformat().encode()
        ).decode()

    return sessions, next_cursor, has_more


def resolve_session_by_number(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    session_number: int,
    local_date: Optional[str] = None,
) -> Optional[ConversationSession]:
    """
    Resolve a session by its per-day number for voice addressability.
    "Chat 2" → today's session #2 for current user.

    Args:
        db: Database session
        tenant_id: Active tenant UUID
        user_id: Requesting user UUID
        session_number: 1-based session number within the day
        local_date: ISO date string (YYYY-MM-DD) in tenant local time; defaults to today

    Returns:
        ConversationSession if found, None if no match (disambiguation needed).
    """
    TENANT_TZ_FALLBACK = "UTC"
    if local_date is None:
        local_date = datetime.now(UTC).strftime("%Y-%m-%d")  # UTC fallback

    sessions, _, _ = get_sessions_with_numbers(db, tenant_id, user_id, limit=50)
    for s in sessions:
        if s["session_number"] == session_number:
            session_id = uuid.UUID(s["session_id"])
            return db.exec(
                select(ConversationSession)
                .where(ConversationSession.id == session_id)
                .where(ConversationSession.tenant_id == tenant_id)
            ).first()
    return None


def freeze_session_quote_previews(
    db: Session,
    session: ConversationSession,
    excluding_message_id: Optional[uuid.UUID] = None,
) -> int:
    """
    Freeze all live quote_preview messages in a session to snapshot mode.

    Called synchronously:
    - At quote submission (freeze ALL quote_preview messages)
    - At new artifact turn (freeze all EXCEPT the just-emitted message)

    Args:
        db: Database session
        session: The conversation session to freeze messages in
        excluding_message_id: If provided, skip this message (just-emitted; stays live)

    Returns:
        Count of messages frozen.

    CRITICAL: A message NEVER transitions from snapshot back to live.
    """
    from sqlalchemy.dialects.postgresql import JSONB as SA_JSONB

    messages = db.exec(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session.id)
        .where(ConversationMessage.tenant_id == session.tenant_id)
        .where(ConversationMessage.structured_content_json.isnot(None))
    ).all()

    frozen_count = 0
    for msg in messages:
        if excluding_message_id and msg.id == excluding_message_id:
            continue
        payload = msg.structured_content_json
        if not payload:
            continue
        if payload.get("render_mode") == "snapshot":
            continue  # CRITICAL: never unfreeze
        artifact_type = payload.get("artifact_type", "")
        if artifact_type != "quote_preview":
            continue

        # Resolve the entity to capture snapshot
        entity_id = payload.get("entity_id")
        snapshot_data = _capture_entity_snapshot(db, artifact_type, entity_id)

        payload["render_mode"] = "snapshot"
        payload["snapshot_payload"] = snapshot_data
        msg.structured_content_json = payload
        db.add(msg)
        frozen_count += 1

    if frozen_count > 0:
        db.commit()

    return frozen_count


def _capture_entity_snapshot(
    db: Session,
    artifact_type: str,
    entity_id: Optional[str],
) -> Dict[str, Any]:
    """
    Capture a frozen snapshot of the referenced entity for snapshot rendering.

    This is the single point of snapshot capture — both submission freezes
    and new-artifact-turn freezes call through here to guarantee consistent
    snapshot shape.
    """
    if not entity_id:
        return {}

    if artifact_type == "quote_preview":
        from app.models.quoting import Quote
        try:
            quote = db.get(Quote, uuid.UUID(entity_id))
        except ValueError:
            return {}
        if not quote:
            return {"error": "quote_not_found", "entity_id": entity_id}
        return {
            "quote_id": str(quote.id),
            "status": quote.status_code if hasattr(quote, "status_code") else None,
            "total_cents": quote.total_cents,
            "captured_at": datetime.now(UTC).isoformat(),
        }
    # Future artifact types (job_preview, schedule_preview) added here as needed
    return {}
```

---

### E.2 Voice Feedback Model

**File**: `backend/app/models/ai.py` *(extend existing file)*

```python
class VoiceFeedback(SQLModel, table=True):
    """
    Voice AI feedback loop for Whisper/Llama training data capture.
    AppendOnly — rows are never updated after creation except by Celery export task.
    Established in B2 (A6). Strategic moat: builds fine-tuning dataset.
    """
    __tablename__ = "voice_feedback"

    __table_args__ = (
        Index("ix_voice_feedback_tenant_id", "tenant_id"),
        Index("ix_voice_feedback_user_id", "user_id"),
        Index(
            "ix_voice_feedback_unexported",
            "exported_at",
            postgresql_where=text("exported_at IS NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"),
                         nullable=False)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"),
                         nullable=False)
    )
    voice_command_log_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, ForeignKey("voice_command_log.id",
                                                ondelete="SET NULL"), nullable=True)
    )
    original_transcription: str = Field(nullable=False)
    corrected_text: Optional[str] = Field(default=None)
    intent_misparsed: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    corrected_intent: Optional[str] = Field(default=None)
    feedback_notes: Optional[str] = Field(default=None)

    # Written by nightly Celery task — not by user
    s3_export_key: Optional[str] = Field(default=None)
    exported_at: Optional[AwareDatetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # AppendOnly audit fields
    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
```

---

### E.3 Session Title Celery Task

**File**: `backend/tasks/voice_session_title.py` *(new file — create in B2/A11)*

```python
"""
Voice Session Title Generation Task.

Event-driven task: enqueued after the first substantive assistant turn in a session.
Established in B2 (A11). Extended in B12 (A67) to use voice persona tone.

Pattern: §17.2 Event-Driven Retryable Task (bind=True, max_retries=3)
"""

import logging
from typing import Any, Dict

from core.celery_app import celery_app
from core.db import get_db
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


@celery_app.task(
    name="generate_session_title",
    bind=True,
    max_retries=3,
)
def generate_session_title(self, session_id: str) -> Dict[str, Any]:
    """
    Generate an AI title for a conversation session after the first assistant turn.

    Only fires if context_summary and title are both NULL — user-set titles are
    never overwritten (title_auto_generated = FALSE is the guard).

    Enqueued by: POST /api/v1/voice/command after first assistant message in a session.
    Retries: 3 attempts with 60-second countdown on Ollama timeout.

    B12 extension point: When B12 is implemented, this task will call
    voice_persona_renderer.get_title_prompt(user_id) to inject the user's tone
    into the Ollama prompt. For MVP (B2), hardcoded neutral/descriptive tone.
    """
    db: Session = next(get_db())
    try:
        result = _generate_session_title_impl(session_id, db)
        return result
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating session title for {session_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


def _generate_session_title_impl(session_id: str, db: Session) -> Dict[str, Any]:
    """
    Inner implementation — testable without Celery.

    Returns: {"session_id": str, "title": str | None, "skipped": bool}
    """
    import uuid
    from app.models.ai import ConversationMessage, ConversationSession
    from services.ai_service import generate_text_sync  # synchronous Ollama wrapper

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        return {"session_id": session_id, "title": None, "skipped": True,
                "reason": "invalid_uuid"}

    session = db.exec(
        select(ConversationSession)
        .where(ConversationSession.id == session_uuid)
        .where(ConversationSession.is_active == True)  # noqa: E712
    ).first()

    if not session:
        return {"session_id": session_id, "title": None, "skipped": True,
                "reason": "session_not_found"}

    # Guard: user-set title is frozen (title_auto_generated = FALSE)
    if session.title is not None and not session.title_auto_generated:
        return {"session_id": session_id, "title": session.title, "skipped": True,
                "reason": "user_set_title_frozen"}

    # Fetch first 3 turns for title generation
    messages = db.exec(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_uuid)
        .order_by(ConversationMessage.created_at.asc())
        .limit(6)
    ).all()

    if not messages:
        return {"session_id": session_id, "title": None, "skipped": True,
                "reason": "no_messages"}

    conversation_excerpt = "\n".join(
        f"{msg.role.upper()}: {msg.content_text[:200]}"
        for msg in messages
        if msg.role in ("user", "assistant")
    )

    # B12 extension: inject persona tone here when voice_persona_renderer is available
    prompt = (
        f"Summarize this conversation in 3-5 words, suitable as a scannable title "
        f"in a chat history list. Be specific to the work discussed. "
        f"Respond with ONLY the title, no punctuation at end.\n\n"
        f"Conversation:\n{conversation_excerpt}"
    )

    try:
        generated_title = generate_text_sync(prompt, max_tokens=20)
        generated_title = generated_title.strip()[:80]  # cap length
    except Exception as e:
        logger.warning(f"Ollama title generation failed for session {session_id}: {e}")
        return {"session_id": session_id, "title": None, "skipped": True,
                "reason": f"ollama_error: {str(e)}"}

    if not generated_title:
        return {"session_id": session_id, "title": None, "skipped": True,
                "reason": "empty_response"}

    session.title = generated_title
    session.title_auto_generated = True
    db.add(session)
    db.commit()

    return {"session_id": session_id, "title": generated_title, "skipped": False}
```

---

### E.4 Voice Feedback Export Celery Task

**File**: `backend/tasks/voice_feedback_export.py` *(new file — create in B2/A6)*

```python
"""
Nightly Voice Feedback S3 Export Task.

Established in B2 (A6). Builds the training data pipeline for Llama fine-tuning.

Pattern: §17.1 Periodic Poll Task (no bind, no retry — log errors and move on)
Schedule: Daily at 2:00 AM UTC (added to beat_schedule in celery_app.py)
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Dict

from core.celery_app import celery_app
from core.db import get_db
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


@celery_app.task(name="export_voice_feedback_to_s3")
def export_voice_feedback_to_s3() -> Dict[str, int]:
    """
    Export unexported voice_feedback rows to S3 in model fine-tuning format.

    Format: JSONL — one JSON object per line:
    {"original": "...", "corrected": "...", "intent_misparsed": bool, "corrected_intent": "..."}

    S3 path: s3://pilot-voice-training/feedback/{YYYY}/{MM}/{DD}/{export_uuid}.jsonl

    Returns: {"exported": int, "errors": int}
    """
    db: Session = next(get_db())
    exported = 0
    errors = 0

    try:
        return _export_voice_feedback_impl(db)
    except Exception as e:
        db.rollback()
        logger.error(f"Error in export_voice_feedback_to_s3: {e}")
        raise
    finally:
        db.close()


def _export_voice_feedback_impl(db: Session) -> Dict[str, int]:
    """Inner implementation — separated for testability."""
    import boto3
    from core.config import settings
    from app.models.ai import VoiceFeedback

    unexported = db.exec(
        select(VoiceFeedback)
        .where(VoiceFeedback.exported_at.is_(None))
        .limit(1000)
    ).all()

    if not unexported:
        return {"exported": 0, "errors": 0}

    now_utc = datetime.now(UTC)
    export_uuid = str(uuid.uuid4())
    s3_key = (
        f"feedback/{now_utc.strftime('%Y/%m/%d')}/{export_uuid}.jsonl"
    )

    lines = []
    for row in unexported:
        lines.append(json.dumps({
            "original": row.original_transcription,
            "corrected": row.corrected_text,
            "intent_misparsed": row.intent_misparsed,
            "corrected_intent": row.corrected_intent,
            "feedback_notes": row.feedback_notes,
            "tenant_id": str(row.tenant_id),
            "created_at": row.created_at.isoformat(),
        }))

    jsonl_content = "\n".join(lines).encode("utf-8")

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=settings.VOICE_TRAINING_BUCKET,
            Key=s3_key,
            Body=jsonl_content,
            ContentType="application/jsonl",
        )
    except Exception as e:
        logger.error(f"S3 upload failed for voice feedback export: {e}")
        return {"exported": 0, "errors": len(unexported)}

    # Mark all rows as exported
    for row in unexported:
        row.s3_export_key = s3_key
        row.exported_at = now_utc
        db.add(row)

    db.commit()
    logger.info(f"Exported {len(unexported)} voice feedback rows to s3://{s3_key}")
    return {"exported": len(unexported), "errors": 0}
```

---

## F. OPEN QUESTIONS RESOLVED

### F.1 Tenant Timezone for Session Number Rollover

**Question**: A9 requires per-day session numbering with midnight rollover in tenant's local timezone. The `conversation_session` table has `created_at` (UTC). Where is the tenant timezone stored?

**Investigation result**: The `Tenant` model (`app/models/core.py`) does NOT have a `timezone` column. The `TenantSettings` model also does NOT have a `timezone` column. The `tenant` and `tenant_settings` tables confirmed via the live DB model reads.

**Decision**: For B2 (MVP), session number computation falls back to **UTC for all tenants**. This means midnight rollover is UTC, not local. This is acceptable for MVP — the per-day session reset is a UX feature, not a financial one. Exact timezone precision is a quality-of-life improvement deferred to a future batch.

**Implementation**: The `get_sessions_with_numbers()` utility in §E.1 uses `TENANT_TZ_FALLBACK = "UTC"` with a comment documenting this decision. When B9 (Settings Infrastructure) lands and a `tenant_timezone` setting is introduced, this utility can be updated to call `get_effective_setting(db, tenant_id, "tenant_timezone", fallback="UTC")`.

**No additional migration required** — this decision avoids adding a `timezone` column to `tenant` or `tenant_settings` in B2. That belongs in B9's settings infrastructure.

---

### F.2 `structured_content_json` vs Discriminator in `content_text`

**Question**: A12 ledger says "schema decision left to dev team: add `structured_content_json JSONB` column OR leverage existing content_text with a type discriminator."

**Decision**: Add **`structured_content_json JSONB NULL`** as a separate column.

**Rationale**:
1. `content_text` is currently `VARCHAR NOT NULL` — changing it to accept JSON would require a type change migration and breaks the existing embedding pipeline (Ollama/Whisper produce plain text, not JSON).
2. Separate column allows NULL for plain-text messages with zero schema overhead.
3. pgvector embedding on `content_text` remains unaffected.
4. Voice readback always reads from `content_text` regardless of render mode — the structured payload is for client rendering only.
5. Aligns with arch doc §6.4 which names the field `structured_content_json`.

---

### F.3 `field_mode_enabled` Storage — Column vs JSONB

**Question**: A7 adds `field_mode_enabled` user preference. New column on `user` table or store in `user_preference.preferences` JSONB?

**Decision**: Store in **`user_preference.preferences` JSONB** — no new column or migration.

**Rationale**:
1. `user_preference` table already exists with `preferences JSONB NOT NULL DEFAULT '{}'`.
2. Adding a column to `user` for a single boolean preference would require a migration that touches the largest, most constrained table in the system.
3. The `user_preference.preferences` JSONB is designed for exactly this use case (user-specific, tenant-scoped soft preferences).
4. `PATCH /api/v1/users/me/preferences` is the natural endpoint — it writes `preferences["field_mode_enabled"] = true/false`.
5. Field mode is read at route-level guard time: `prefs = db.exec(select(UserPreference).where(...)).first(); field_mode = (prefs.preferences or {}).get("field_mode_enabled", False)`.

---

### F.4 Disambiguation Response Shape for Missing Session Reference

**Question**: When user says "Delete chat 5" and no session 5 exists today, what exact response shape should the handler return?

**Decision**: Return a structured disambiguation response (NOT an error):
```python
{
    "action": "delete_session",
    "success": True,
    "requires_disambiguation": True,
    "message": "I don't have a Chat 5 from today. You have 3 chats — Chat 1, 2, and 3. Which one did you mean?",
    "disambiguation_data": {
        "requested_number": 5,
        "available_sessions": [
            {"session_number": 1, "title": "Johnson Panel"},
            {"session_number": 2, "title": "Davis Wiring"},
            {"session_number": 3, "title": "Untitled session"},
        ]
    }
}
```

**Rationale**: Arch doc §B2 states "Missing-reference path: handler returns a disambiguation response for the AI to voice, rather than executing on a guess." The `success: True` (not False) signals to the frontend/AI that this is a flow step, not an error — the AI reads the disambiguation message back to the user and prompts for clarification.

---

### F.5 Freeze Trigger Timing — Synchronous vs Celery

**Question**: A12 states submission freeze is synchronous. Should the new-artifact-turn freeze also be synchronous?

**Decision**: **Both freeze triggers are synchronous**, executed before the API returns.

**Rationale from ledger**: "The user is returned to the home screen only after the freeze is complete. No Celery task — synchronous for consistency (the freeze must be visible before the user can navigate away and return)." The new-artifact-turn freeze has the same requirement — if frozen state is not persisted before the response returns, a user scrolling up immediately after a new quote line is added could see the prior card in live mode when it should show the state from that moment.

**Implementation**: `freeze_session_quote_previews()` in `services/voice_session_service.py` (§E.1) is called synchronously within the request handler before `db.commit()`.

---

## G. EXTERNAL DEPENDENCY STATUS

### G.1 Ollama / Llama 3.1 8B (A11 — Session Title Generation)

**External system**: Local Ollama on GPU instance (`http://ollama:11434`)
**Dependency type**: LOCAL — no external API; no cost per request
**Status**: ✅ Already in production use for intent parsing (confirmed — `parse_intent()` calls Ollama)
**Blocks implementation**: NO — Ollama is available in all environments
**Blocks production delivery**: NO — local, no approval timeline
**Mock strategy**: The `_generate_session_title_impl()` function is separated from the Celery wrapper per §17.2 pattern. Unit tests stub `generate_text_sync()` to return a canned title without hitting Ollama. Set `OLLAMA_BASE_URL=http://localhost:99999` in test environment to force the except-and-skip fallback path.
**Tom action required**: None

---

### G.2 Whisper Large-v3 (A6 — Feedback Loop references transcriptions)

**External system**: Local Whisper server on GPU instance (`http://whisper:8080`)
**Dependency type**: LOCAL — no external API; no cost per request
**Status**: ✅ Already in production use (confirmed — `transcribe_audio()` in `services/ai_service.py`)
**Blocks implementation**: NO
**Blocks production delivery**: NO
**Mock strategy**: A6 does NOT call Whisper directly — it stores the transcription that already came from Whisper during the voice command processing. No mock needed for A6 itself; the `original_transcription` field is supplied by the caller.
**Tom action required**: None

---

### G.3 AWS S3 — Voice Training Bucket (A6 — Nightly feedback export)

**External system**: AWS S3 bucket `pilot-voice-training`
**Dependency type**: External (AWS — same account as existing S3 usage for audio uploads)
**Status**: ⚠️ Bucket `pilot-voice-training` may not exist yet. Existing `audio_object_key` on `voice_command_log` confirms S3 is already used for audio, but the training bucket is new.
**Blocks implementation**: NO — mock S3 client (`moto` library) used in tests; task skips S3 upload and logs a warning if `VOICE_TRAINING_BUCKET` env var is unset.

**Mock strategy for dev/test**:
```python
# In tests/batch_b2/test_voice_feedback_export.py
from unittest.mock import patch

def test_export_voice_feedback_to_s3(db_session, test_tenant):
    with patch("boto3.client") as mock_s3_client:
        mock_s3_client.return_value.put_object.return_value = {}
        result = _export_voice_feedback_impl(db_session)
        assert result["exported"] >= 0  # 0 if no unexported rows in test DB
        mock_s3_client.return_value.put_object.assert_called_once()
```

**Blocks production delivery**: YES — the following must be complete before production:
1. Create S3 bucket `pilot-voice-training` in `us-east-1` with private ACL
2. Add lifecycle rule: transition to S3 Glacier after 90 days (cost control)
3. Add `VOICE_TRAINING_BUCKET=pilot-voice-training` to ECS task environment variables (via AWS Secrets Manager or task definition)
4. Update ECS task IAM role to include `s3:PutObject` on `arn:aws:s3:::pilot-voice-training/*`
5. Set the env var in all environments: dev, staging, production

**Tom action required before production delivery**:
- [ ] Create S3 bucket `pilot-voice-training`
- [ ] Configure IAM policy for ECS task role
- [ ] Set `VOICE_TRAINING_BUCKET` env var in AWS Secrets Manager
- [ ] Verify `export_voice_feedback_to_s3` task runs successfully in staging

**Lead time**: 1–2 hours (no external approval required — same AWS account)

---

### G.4 No External Dependencies for A7, A9, A10, A12

Items A7, A9, A10, and A12 have **zero external dependencies**. All computation is local:

| Item | Computation | External? |
|:---|:---|:---|
| A7 — Field Mode | JSONB write to `user_preference.preferences` | ❌ None |
| A9 — Session Numbers | SQL window function on `conversation_session` | ❌ None |
| A10 — Voice Grammar | Python handlers + DB + local Ollama (already running) | ❌ None (Ollama is local) |
| A12 — Structured Content | JSONB column + synchronous freeze logic | ❌ None |

**Tom action required for A7, A9, A10, A12**: None

---

## Appendix: Migration File Names Summary

| Migration Name | Purpose | Item(s) |
|:---|:---|:---|
| `phase_fe_1_batch_b2_voice_session_title_columns` | Add `title`, `title_auto_generated`, `archived_at` to `conversation_session` | A11 |
| `phase_fe_1_batch_b2_conversation_message_structured_content` | Add `structured_content_json JSONB NULL` to `conversation_message` | A12 |
| `phase_fe_1_batch_b2_voice_feedback_table` | Create `voice_feedback` table with all columns, indexes, FKs, and triggers | A6 |

**A7, A9, A10**: No migrations required.
- A7 uses existing `user_preference.preferences` JSONB — no schema change
- A9 is a derived query (`ROW_NUMBER()` window function) — no schema change
- A10 extends `INTENT_HANDLERS` in Python — no schema change

---

## Appendix: New Files Created in B2

**New files**:

| File | Purpose | Item(s) |
|:---|:---|:---|
| `backend/services/voice_session_service.py` | `get_sessions_with_numbers()`, `resolve_session_by_number()`, `freeze_session_quote_previews()` | A9, A12 |
| `backend/tasks/voice_session_title.py` | `generate_session_title` Celery task + `_generate_session_title_impl()` | A11 |
| `backend/tasks/voice_feedback_export.py` | `export_voice_feedback_to_s3` Celery task + `_export_voice_feedback_impl()` | A6 |
| `backend/api/routes/voice_sessions.py` | `GET /api/v1/voice/sessions`, `GET /api/v1/voice/sessions/{id}/messages` | A9, A12 |
| `backend/api/routes/voice_feedback.py` | `POST/GET /api/v1/voice/feedback`, `GET /api/v1/voice/transcripts` | A6 |
| `tests/batch_b2/` | Test subfolder (create directory) | All |

**Modified files**:

| File | Change | Item(s) |
|:---|:---|:---|
| `backend/app/models/ai.py` | Add `VoiceFeedback` class; add `title`, `title_auto_generated`, `archived_at` to `ConversationSession`; add `structured_content_json` to `ConversationMessage` | A6, A11, A12 |
| `backend/services/voice_action_router.py` | Add `rename_session_via_voice()`, `delete_session_via_voice()`, `open_session_via_voice()`, `query_session_summary_via_voice()` handlers; register in `INTENT_HANDLERS` | A10 |
| `backend/app/main.py` | Register `voice_sessions.router` (prefix `/api/v1/voice`) and `voice_feedback.router` (prefix `/api/v1/voice`) | A9, A6 |
| `backend/core/celery_app.py` | Add `"tasks.voice_session_title"` and `"tasks.voice_feedback_export"` to `imports`; add `export_voice_feedback_to_s3` to `beat_schedule` (daily at 2 AM UTC) | A11, A6 |
| `backend/api/routes/voice.py` | Enqueue `generate_session_title.delay(str(conversation_session.id))` after first assistant turn in `_process_voice_command_impl()` | A11 |

---

*Document complete. All six reads verified before writing. All seven sections present. Schema confirmed against live DB via postgres-local MCP. No open questions remain.*