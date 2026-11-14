# Batch B16 Design Document — Help System (AI Agent, RAG, Feedback)

**Batch**: B16  
**Items**: A85, A84, A86, A87, A88  
**Estimated effort**: 16–20 days  
**Prerequisite batches**: B2 (Ollama + session infrastructure), B10 (notification/SendGrid infrastructure)  
**Test subfolder**: `tests/batch_b16/`  
**Migration prefix**: `phase_fe_1_batch_b16_`  
**Design doc created**: 2026-05-03  
**Status**: ☐ Pending

---

## A. MIGRATION PLAN

### New Tables

#### 1. `help_article`

**Mixin**: `MachineLogMixin` — automated system management; articles are created and updated only by the embedding pipeline Celery task, never mutated by users. Only `created_at` is needed; no user-authored audit trail required.

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `article_id` | `TEXT` | NOT NULL | — | Primary key; slug e.g. `setup-quickbooks-integration` |
| `s3_path` | `TEXT` | NOT NULL | — | Full S3 path `s3://pilot-help-content/{lang}/{cat}/{id}.md` |
| `title` | `TEXT` | NOT NULL | — | Human-readable title from frontmatter |
| `category` | `TEXT` | NOT NULL | — | Top-level grouping (integrations, voice-ai, settings, billing, onboarding, etc.) |
| `frontmatter_metadata` | `JSONB` | NOT NULL | `'{}'::jsonb` | Full frontmatter: related_concepts, ui_surfaces, related_articles, last_updated, audience |
| `last_content_hash` | `TEXT` | NOT NULL | — | SHA-256 of content body; change-detection gate |
| `last_processed_at` | `TIMESTAMPTZ` | NOT NULL | — | When embedding pipeline last processed this article |
| `last_updated` | `DATE` | NOT NULL | — | ISO date from frontmatter |
| `audience` | `TEXT[]` | NOT NULL | `'{}'::text[]` | Role names this article targets, e.g. `{owner, accountant}` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | MachineLogMixin field |

**Primary key**: `article_id`  
**Indexes**:
- `ix_help_article_category` → `USING btree (category)`
- GIN index `ix_help_article_audience` → `USING gin (audience)` (for `@>` array containment filter)

**Triggers** (MachineLogMixin):
- `audit_help_article_changes` — `AFTER INSERT OR DELETE OR UPDATE EXECUTE FUNCTION audit.log_changes()`

**Migration name**: `phase_fe_1_batch_b16_help_article_table`

---

#### 2. `help_article_chunk`

**Mixin**: `MachineLogMixin` — automated system event; chunks are created/replaced by the embedding pipeline only. `created_at` only needed.

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `chunk_id` | `UUID` | NOT NULL | `gen_random_uuid()` | Primary key |
| `article_id` | `TEXT` | NOT NULL | — | FK → `help_article.article_id` ON DELETE CASCADE |
| `chunk_order` | `INTEGER` | NOT NULL | — | Section order within article (0-based) |
| `section_title` | `TEXT` | NOT NULL | — | The `##` heading that opened this chunk |
| `chunk_text` | `TEXT` | NOT NULL | — | Raw markdown content of chunk |
| `chunk_text_with_metadata` | `TEXT` | NOT NULL | — | Frontmatter header + section + content; what gets embedded |
| `embedding` | `vector(1536)` | NOT NULL | — | OpenAI text-embedding-3-small output |
| `token_count` | `INTEGER` | NOT NULL | — | Token count of `chunk_text_with_metadata` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | MachineLogMixin field |

**Primary key**: `chunk_id`  
**Indexes**:
- `ix_help_article_chunk_article_id` → `USING btree (article_id)`
- `help_article_chunk_embedding_hnsw_idx` → `USING hnsw (embedding vector_cosine_ops)` — critical for sub-millisecond retrieval; **must be created after table is populated with at least one row**

**Foreign keys**:
- `fk_help_article_chunk_article_id` → `help_article(article_id)` ON DELETE CASCADE

**Triggers** (MachineLogMixin):
- `audit_help_article_chunk_changes` — `AFTER INSERT OR DELETE OR UPDATE EXECUTE FUNCTION audit.log_changes()`

**Migration name**: `phase_fe_1_batch_b16_help_article_chunk_table`  
> This is a separate migration from `help_article` because the HNSW index creation requires the `vector` extension and may take time on large datasets.

---

#### 3. `help_chat_session`

**Mixin**: `StandardAuditMixin` — user-owned mutable record; `outcome`, `title`, `last_activity_at`, and `message_count` are updated throughout the session lifecycle. Requires `created_at`, `updated_at`, `created_by`, `updated_by` + 3-trigger set.

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `session_id` | `UUID` | NOT NULL | `gen_random_uuid()` | Primary key |
| `tenant_id` | `UUID` | NOT NULL | — | FK → `tenant.id` |
| `user_id` | `UUID` | NOT NULL | — | FK → `user.id` |
| `started_at` | `TIMESTAMPTZ` | NOT NULL | — | When the session was first created |
| `last_activity_at` | `TIMESTAMPTZ` | NOT NULL | — | Updated on every message exchange |
| `title` | `TEXT` | NULL | `NULL` | Auto-generated via A11/Ollama pattern after first turn |
| `outcome` | `TEXT` | NULL | `NULL` | `resolved \| escalated \| abandoned` — set when session closes |
| `message_count` | `INTEGER` | NOT NULL | `0` | Incremented on each message; redundant but useful for quick scans |
| `anonymized_at` | `TIMESTAMPTZ` | NULL | `NULL` | Set by A88 pipeline when session is anonymized + deleted |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | — | StandardAuditMixin |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | — | StandardAuditMixin |
| `created_by` | `UUID` | NULL | `NULL` | StandardAuditMixin |
| `updated_by` | `UUID` | NULL | `NULL` | StandardAuditMixin |

**Check constraints**:
- `help_chat_session_outcome_chk`: `outcome IN ('resolved', 'escalated', 'abandoned')`

**Primary key**: `session_id`  
**Indexes**:
- `ix_help_chat_session_tenant_id` → `USING btree (tenant_id)`
- `ix_help_chat_session_user_id` → `USING btree (user_id)`
- `ix_help_chat_session_last_activity_at` → `USING btree (last_activity_at)` — used by A88 anonymization pipeline date filter
- Partial index `ix_help_chat_session_pending_anonymization` → `USING btree (last_activity_at) WHERE anonymized_at IS NULL` — speeds up A88 daily scan

**Foreign keys**:
- `fk_help_chat_session_tenant_id` → `tenant(id)` ON DELETE RESTRICT
- `fk_help_chat_session_user_id` → `user(id)` ON DELETE RESTRICT

**Triggers** (StandardAuditMixin — 3 triggers):
- `audit_help_chat_session_changes` — `AFTER INSERT OR DELETE OR UPDATE EXECUTE FUNCTION audit.log_changes()`
- `guard_help_chat_session_created_immutable` — guards `created_at`, `created_by`
- `set_help_chat_session_updated_at` — sets `updated_at` on UPDATE

**Migration name**: `phase_fe_1_batch_b16_help_chat_session_table`

---

#### 4. `help_chat_message`

**Mixin**: `AppendOnlyMixin` — immutable ledger record; messages are never edited after creation (mirrors `conversation_message` design in B2). Adds `created_at`, `created_by` + 2-trigger set (`audit_changes`, `guard_created_immutable`).

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `message_id` | `UUID` | NOT NULL | `gen_random_uuid()` | Primary key |
| `session_id` | `UUID` | NOT NULL | — | FK → `help_chat_session.session_id` ON DELETE CASCADE |
| `role` | `TEXT` | NOT NULL | — | `user \| assistant` |
| `content` | `TEXT` | NOT NULL | — | Message text content |
| `context_payload` | `JSONB` | NULL | `NULL` | User messages only: surface context at time of question (route, entity_type, recent_actions, user_role, tenant_metadata) |
| `retrieved_chunks` | `JSONB` | NULL | `NULL` | Assistant messages only: which chunk_ids + scores drove RAG context (for debugging and training) |
| `voice_used` | `BOOLEAN` | NOT NULL | `FALSE` | Whether voice input/output was used for this turn |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | — | AppendOnlyMixin |
| `created_by` | `UUID` | NULL | `NULL` | AppendOnlyMixin |

**Check constraints**:
- `help_chat_message_role_chk`: `role IN ('user', 'assistant')`

**Primary key**: `message_id`  
**Indexes**:
- `ix_help_chat_message_session_id` → `USING btree (session_id)`

**Foreign keys**:
- `fk_help_chat_message_session_id` → `help_chat_session(session_id)` ON DELETE CASCADE

**Triggers** (AppendOnlyMixin — 2 triggers):
- `audit_help_chat_message_changes` — `AFTER INSERT OR DELETE OR UPDATE EXECUTE FUNCTION audit.log_changes()`
- `guard_help_chat_message_created_immutable` — guards `created_at`, `created_by`

**Migration name**: `phase_fe_1_batch_b16_help_chat_message_table`

---

#### 5. `feedback_submission`

**Mixin**: `AppendOnlyMixin` — submissions are never edited after creation; the record is a write-once audit trail of user feedback. Adds `created_at`, `created_by` + 2-trigger set.

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `submission_id` | `UUID` | NOT NULL | `gen_random_uuid()` | Primary key |
| `tenant_id` | `UUID` | NOT NULL | — | FK → `tenant.id` |
| `user_id` | `UUID` | NOT NULL | — | FK → `user.id` |
| `category` | `TEXT` | NOT NULL | — | `bug \| feature_request \| question \| general` |
| `body` | `TEXT` | NOT NULL | — | Full feedback text |
| `from_help_chat_session_id` | `UUID` | NULL | `NULL` | FK → `help_chat_session.session_id` — populated when escalated from help chat |
| `email_sent_to` | `TEXT` | NOT NULL | — | Support email address that received this submission |
| `email_message_id` | `TEXT` | NULL | `NULL` | SendGrid message ID for delivery tracking |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | — | AppendOnlyMixin |
| `created_by` | `UUID` | NULL | `NULL` | AppendOnlyMixin |

**Check constraints**:
- `feedback_submission_category_chk`: `category IN ('bug', 'feature_request', 'question', 'general')`

**Primary key**: `submission_id`  
**Indexes**:
- `ix_feedback_submission_tenant_id` → `USING btree (tenant_id)`
- `ix_feedback_submission_user_id` → `USING btree (user_id)`
- `ix_feedback_submission_from_session_id` → `USING btree (from_help_chat_session_id) WHERE from_help_chat_session_id IS NOT NULL`

**Foreign keys**:
- `fk_feedback_submission_tenant_id` → `tenant(id)` ON DELETE RESTRICT
- `fk_feedback_submission_user_id` → `user(id)` ON DELETE RESTRICT
- `fk_feedback_submission_session_id` → `help_chat_session(session_id)` ON DELETE SET NULL

**Triggers** (AppendOnlyMixin — 2 triggers):
- `audit_feedback_submission_changes` — `AFTER INSERT OR DELETE OR UPDATE EXECUTE FUNCTION audit.log_changes()`
- `guard_feedback_submission_created_immutable` — guards `created_at`, `created_by`

**Migration name**: `phase_fe_1_batch_b16_feedback_submission_table`

---

#### 6. `help_training_corpus`

**Mixin**: `MachineLogMixin` — automated system event; corpus entries are written entirely by the `anonymize_help_sessions` Celery task with no human authorship. Only `created_at` needed.

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `corpus_id` | `UUID` | NOT NULL | `gen_random_uuid()` | Primary key |
| `original_session_id_hash` | `TEXT` | NOT NULL | — | One-way SHA-256 hash of original session UUID; allows tracking lineage without reversibility |
| `anonymized_message_history` | `JSONB` | NOT NULL | — | Array of `{role, content, retrieved_chunks_summary}` objects with PII replaced |
| `anonymized_context_payload` | `JSONB` | NULL | `NULL` | Context payload with PII stripped |
| `category_inferred` | `TEXT` | NULL | `NULL` | AI-classified topic for training data filtering |
| `outcome` | `TEXT` | NOT NULL | — | Copied from original session outcome field |
| `anonymized_at` | `TIMESTAMPTZ` | NOT NULL | — | When the anonymization pipeline ran |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | MachineLogMixin field |

**Primary key**: `corpus_id`  
**Indexes**:
- `ix_help_training_corpus_original_session_id_hash` → `USING btree (original_session_id_hash)` — dedup check before inserting
- `ix_help_training_corpus_category_inferred` → `USING btree (category_inferred)`

**Triggers** (MachineLogMixin):
- `audit_help_training_corpus_changes` — `AFTER INSERT OR DELETE OR UPDATE EXECUTE FUNCTION audit.log_changes()`

**Migration name**: `phase_fe_1_batch_b16_help_training_corpus_table`

---

### New Columns on Existing Tables

**MCP query result**: `SELECT column_name FROM information_schema.columns WHERE table_name IN ('help_article','help_article_chunk','help_chat_session','help_chat_message','help_training_corpus','feedback_submission')` → **returned empty result set**. All six tables confirmed as non-existent. No pre-existing columns to check.

No columns are being added to any existing table in B16. All schema work is net-new tables.

---

### Migration Summary (in execution order)

| # | Migration Name | Content |
|:---|:---|:---|
| 1 | `phase_fe_1_batch_b16_help_article_table` | Creates `help_article`, GIN index on audience, B-tree on category, MachineLogMixin trigger |
| 2 | `phase_fe_1_batch_b16_help_article_chunk_table` | Creates `help_article_chunk`, HNSW index on embedding, B-tree on article_id, MachineLogMixin trigger |
| 3 | `phase_fe_1_batch_b16_help_chat_session_table` | Creates `help_chat_session`, all indexes including partial pending-anonymization, StandardAuditMixin 3-trigger set |
| 4 | `phase_fe_1_batch_b16_help_chat_message_table` | Creates `help_chat_message`, AppendOnlyMixin 2-trigger set |
| 5 | `phase_fe_1_batch_b16_feedback_submission_table` | Creates `feedback_submission`, AppendOnlyMixin 2-trigger set |
| 6 | `phase_fe_1_batch_b16_help_training_corpus_table` | Creates `help_training_corpus`, MachineLogMixin trigger |

---

## B. EXECUTION ORDER

| # | Item | Migration(s) | Rationale |
|:---|:---|:---|:---|
| 1 | **A85** — Markdown Corpus + Embedding Pipeline + S3 Storage | `b16_help_article_table`, `b16_help_article_chunk_table` | Foundation item: `help_article` and `help_article_chunk` tables must exist before A84 can call the retrieval service. The `POST /api/v1/help/retrieve` endpoint established here is consumed by A84's chat handler. Embedding pipeline Celery task `process_help_article` is also defined here. |
| 2 | **A84** — Help AI Agent + RAG + Chat Session Management | `b16_help_chat_session_table`, `b16_help_chat_message_table` | Depends on A85 (calls `help_retrieval.py::retrieve_chunks()` at query time). Chat session tables must exist before voice intent handlers and the chat endpoint can be wired. Session title generation (A11 pattern reuse) is also wired here. |
| 3 | **A86** — Contextual Help Anchor Metadata + Opener Context Payload | *(code-only — no migration)* | Depends on A84: the `context_payload` column already exists on `help_chat_message` from A84's migration. A86 is documentation of the payload contract and voice-action-router wiring only; no DDL required. |
| 4 | **A87** — Feedback Submission Endpoint with Email Intake | `b16_feedback_submission_table` | Depends on B10 notification infrastructure (SendGrid path already exists). The `from_help_chat_session_id` FK requires `help_chat_session` to exist (A84). Placed after A84 to honour FK dependency order. |
| 5 | **A88** — Anonymization Pipeline for Training Data Capture | `b16_help_training_corpus_table` | Depends on A84 (`help_chat_session` + `help_chat_message` tables exist). Pipeline is purely read-from + write-to help session tables — no schema on those tables changes in A88. Placed last because it is a cleanup/training harness with no consumer dependencies. |

---

## C. NEW API ENDPOINTS

### A85 — Corpus & Article Delivery

---

**`POST /api/v1/help/retrieve`** — Internal RAG retrieval (used by A84 chat handler only)

- **Auth**: JWT required (`help_chat.send_message`)
- **RBAC permission**: `help_chat.send_message` (all authenticated users)
- **Request body**:
```json
{
  "query_embedding": [0.012, -0.043, ...],
  "role": "owner",
  "category_hint": "integrations",
  "k": 5
}
```
- **Response**:
```json
{
  "chunks": [
    {
      "chunk_id": "uuid",
      "article_id": "setup-quickbooks-integration",
      "section_title": "Connecting Your Account",
      "chunk_text": "...",
      "score": 0.923
    }
  ]
}
```
- **Behaviour**: Audience filtering applied (`article.audience @> ARRAY[role]`). Optional category filter via `category_hint`. pgvector cosine similarity search with HNSW index. Top-K results returned ordered by descending score.

---

**`GET /api/v1/help/articles/{article_id}`** — Deliver full article markdown for "Read full article"

- **Auth**: JWT required
- **RBAC permission**: `help_chat.send_message` (all authenticated users — audience filtering done in handler)
- **Path params**: `article_id: str`
- **Request body**: none
- **Response**:
```json
{
  "article_id": "setup-quickbooks-integration",
  "title": "Connect QuickBooks Online to Pilot",
  "category": "integrations",
  "content_markdown": "# Connect QuickBooks...",
  "audience": ["owner", "accountant"],
  "last_updated": "2026-04-27"
}
```
- **Behaviour**: Returns 403 if requesting user's role is not in `article.audience`. Fetches markdown from S3 on demand (not cached in DB).

---

**`POST /api/v1/admin/help/articles/{article_id}/reprocess`** — Admin trigger to re-embed a single article

- **Auth**: JWT required
- **RBAC permission**: `admin.manage` (admin-only)
- **Response**: `{"status": "queued", "article_id": "..."}`
- **Behaviour**: Enqueues `process_help_article.delay(article_id=article_id)`.

---

### A84 — Help AI Chat

---

**`POST /api/v1/help/chat`** — Send a message in a help conversation

- **Auth**: JWT required
- **RBAC permission**: `help_chat.send_message`
- **Request body**:
```json
{
  "session_id": "uuid or null",
  "message": "How do I connect QuickBooks?",
  "context_payload": {
    "route": "/settings/integrations/quickbooks",
    "entity_type": null,
    "recent_actions": ["opened_settings", "viewed_qb_conflict"],
    "user_role": "owner",
    "tenant_metadata": {"size": "small", "trade": "electrical"}
  }
}
```
- **Response** (non-streamed MVP):
```json
{
  "session_id": "uuid",
  "message_id": "uuid",
  "role": "assistant",
  "content": "To connect QuickBooks, go to Settings > Integrations...",
  "retrieved_article_ids": ["setup-quickbooks-integration"],
  "session_title": null
}
```
- **Behaviour**: If `session_id` is null, creates a new `help_chat_session`. Retrieves top-5 relevant chunks via `help_retrieval.retrieve_chunks()`. Constructs prompt with system template + RAG context + conversation history + user message. Calls Ollama via `generate_text_sync()`. Persists user message and assistant message to `help_chat_message`. Increments `session.message_count`. Updates `session.last_activity_at`. After first turn, enqueues `generate_help_session_title.delay()` if `title` is null.

---

**`GET /api/v1/help/sessions`** — List user's recent help sessions

- **Auth**: JWT required
- **RBAC permission**: `help_chat.view_history`
- **Query params**: `limit: int = 20`, `offset: int = 0`
- **Response**:
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "title": "QuickBooks setup question",
      "outcome": null,
      "message_count": 4,
      "last_activity_at": "2026-05-03T20:10:00Z",
      "started_at": "2026-05-03T20:05:00Z"
    }
  ],
  "total": 12
}
```
- **Behaviour**: Returns sessions for `current_user.id` + `current_user.tenant_id` only. Excludes sessions where `anonymized_at IS NOT NULL` (already anonymized; original rows deleted). Ordered by `last_activity_at DESC`.

---

**`GET /api/v1/help/sessions/{session_id}`** — Full message history for a session

- **Auth**: JWT required
- **RBAC permission**: `help_chat.view_history`
- **Response**:
```json
{
  "session_id": "uuid",
  "title": "QuickBooks setup question",
  "outcome": null,
  "messages": [
    {
      "message_id": "uuid",
      "role": "user",
      "content": "How do I connect QuickBooks?",
      "created_at": "2026-05-03T20:05:00Z",
      "voice_used": false
    }
  ]
}
```
- **Behaviour**: Tenant-scoped + user-scoped query. 404 if session belongs to another user.

---

**`POST /api/v1/help/sessions/{session_id}/feedback`** — Capture inline session feedback signal

- **Auth**: JWT required
- **RBAC permission**: `help_chat.send_message`
- **Request body**:
```json
{
  "signal": "resolved"
}
```
- **Response**: `{"session_id": "uuid", "outcome": "resolved"}`
- **Behaviour**: Validates `signal` in `['resolved', 'escalated', 'abandoned']`. Updates `help_chat_session.outcome`. Tenant + user ownership check.

---

**`POST /api/v1/help/sessions/delete-all`** — Phase 2 stub — deletes all help sessions for requesting user

- **Auth**: JWT required
- **RBAC permission**: `help_chat.delete_own_history`
- **Request body**: none
- **Response**: `{"status": "not_implemented", "detail": "Self-service deletion is a Phase 2 feature."}`
- **Behaviour**: Returns 501 Not Implemented in MVP. Stub exists for Phase 2 frontend to target.

---

### A87 — Feedback Submission

---

**`POST /api/v1/feedback`** — Submit user feedback

- **Auth**: JWT required
- **RBAC permission**: `feedback.submit`
- **Request body**:
```json
{
  "category": "question",
  "body": "I can't figure out how to set up recurring jobs.",
  "from_help_chat_session_id": "uuid or null"
}
```
- **Response**:
```json
{
  "submission_id": "uuid",
  "category": "question",
  "submitted_at": "2026-05-03T20:15:00Z",
  "confirmation_message": "Thanks for your feedback! We'll follow up at your email address."
}
```
- **Behaviour**: Validates `category` enum. Creates `feedback_submission` row. Dispatches `send_feedback_email.delay(submission_id)` — Celery task sends via `email_service.py` (SendGrid) to `settings.SUPPORT_EMAIL_ADDRESS`. `reply-to` set to submitting user's email so Tom can reply directly. `email_message_id` column updated on send confirmation.

---

## D. PATTERN REUSE DECISIONS

### §16.2 — Standard 4-Step Execution Loop

All five B16 items follow the mandatory execution loop:
1. ORM model update (new `backend/app/models/help.py`)
2. Manual Alembic migration (6 migrations, named per convention)
3. Master JSON blueprint sync (`pilot-db-schema-v2.6h.json`)
4. Regression testing + new test coverage in `tests/batch_b16/`

### §17.1 — Periodic Poll Task Pattern (A88)

`anonymize_help_sessions` uses the §17.1 no-bind, no-retry pattern — it runs daily, processes a batch of expired sessions, and errors are logged + raised for Celery Beat to reschedule:

```python
# tasks/help_corpus.py
@celery_app.task(name="anonymize_help_sessions")
def anonymize_help_sessions() -> Dict[str, int]:
    """
    Daily task: anonymize help sessions >= 90 days old.
    Applies PII detection, writes to help_training_corpus, deletes originals.
    """
    db: Session = next(get_db())
    anonymized = 0
    try:
        cutoff = datetime.now(UTC) - timedelta(days=90)
        sessions = db.exec(
            select(HelpChatSession)
            .where(HelpChatSession.last_activity_at <= cutoff)
            .where(HelpChatSession.anonymized_at == None)
            .limit(200)
        ).all()
        for session in sessions:
            _anonymize_session_impl(session, db)
            anonymized += 1
        db.commit()
        return {"anonymized": anonymized}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in anonymize_help_sessions: {e}")
        raise
    finally:
        db.close()
```

Registered in `core/celery_app.py` `beat_schedule` as `"anonymize-help-sessions-daily"` at `crontab(hour=3, minute=0)` (3 AM UTC, low-traffic window).

### §17.2 — Event-Driven Retryable Task Pattern (A85)

`process_help_article` uses the §17.2 bind=True, max_retries=3 pattern — triggered from S3 event → SQS → Celery, retries on OpenAI API transient failures:

```python
# tasks/help_corpus.py
@celery_app.task(
    name="process_help_article",
    bind=True,
    max_retries=3,
)
def process_help_article(self, article_id: str, s3_path: str) -> Dict[str, Any]:
    """
    Embed a help article into pgvector.
    Triggered by S3 event on article upload/update, or manual admin trigger.
    Retries on OpenAI API or S3 transient failures with 60-second countdown.
    """
    db: Session = next(get_db())
    try:
        result = _process_help_article_impl(article_id, s3_path, db)
        return result
    except ValueError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing article {article_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()
```

Also registered as weekly scheduled fallback: `"process-help-articles-weekly-resync"` at `crontab(hour=2, minute=0, day_of_week=0)` to catch any S3 event misses.

### §21 — Three-Tier Settings Resolver Pattern (A84)

Used by A84 to resolve `voice_persona_tone` for the help agent prompt variant. Imports from `services/setting_resolver.py` (established in B9/A53):

```python
from services.setting_resolver import get_effective_setting_for_user

# Inside help_agent.py::build_prompt()
tone, _ = get_effective_setting_for_user(
    db=db,
    tenant_id=current_user.tenant_id,
    user_id=current_user.id,
    setting_key="voice_persona_tone",
    fallback="balanced",
)
# tone determines which prompt template variant is loaded:
# help_agent_conservative.md | help_agent_balanced.md | help_agent_playful.md
```

### A11 Session Title Pattern (A84)

The help session title auto-generation reuses the exact `generate_text_sync()` pattern established in B2/A11. After the first assistant turn, a Celery task enqueues Ollama to generate a 3–5 word title:

```python
# tasks/help_corpus.py::generate_help_session_title (new task)
from services.ai_service import generate_text_sync

def _generate_help_session_title_impl(session_id: str, first_user_message: str, db: Session) -> None:
    prompt = (
        f"Generate a 3-5 word title for a help conversation that started with: "
        f"'{first_user_message}'. Return ONLY the title, no quotes."
    )
    title = generate_text_sync(prompt=prompt, max_tokens=20)
    session = db.exec(select(HelpChatSession).where(HelpChatSession.session_id == uuid.UUID(session_id))).first()
    if session and not session.title:
        session.title = title.strip()
        db.add(session)
        db.commit()
```

### B2 Ollama Infrastructure Reuse (A84)

A84 calls the existing `generate_text_sync()` function from `backend/services/ai_service.py` (added in B2). This function uses `asyncio.run()` to call Ollama's `/chat` endpoint synchronously — correct for use inside Celery tasks and synchronous FastAPI route handlers.

The new `help_agent.py` service wraps this with the RAG-injected prompt:

```python
# services/help_agent.py (new file — A84)
from services.ai_service import generate_text_sync

def generate_help_response(
    user_message: str,
    retrieved_chunks: list[dict],
    conversation_history: list[dict],
    context_payload: dict | None,
    tone: str,
) -> str:
    """
    Construct help agent prompt with RAG context and call Ollama.
    
    Args:
        user_message: Current user question
        retrieved_chunks: Top-K chunks from help_retrieval.retrieve_chunks()
        conversation_history: Prior {role, content} pairs from this session
        context_payload: Surface context from client (route, recent_actions, etc.)
        tone: 'conservative' | 'balanced' | 'playful'
    
    Returns:
        AI-generated help response text
    """
    prompt_template = _load_prompt_template(tone)
    prompt = _render_prompt(prompt_template, user_message, retrieved_chunks, conversation_history, context_payload)
    return generate_text_sync(prompt=prompt, max_tokens=512)
```

### B10 SendGrid Infrastructure Reuse (A87)

A87 dispatches feedback emails via the same `email_service.py` path used by the notification system (established in B10). The Celery task `send_feedback_email` calls:

```python
from services.email_service import send_email

# tasks/help_corpus.py::_send_feedback_email_impl (inner impl for testability)
def _send_feedback_email_impl(submission_id: str, db: Session) -> Dict[str, Any]:
    submission = db.exec(select(FeedbackSubmission).where(FeedbackSubmission.submission_id == uuid.UUID(submission_id))).first()
    user = db.get(User, submission.user_id)
    
    result = send_email(
        to=settings.SUPPORT_EMAIL_ADDRESS,
        reply_to=user.email,
        subject=f"[Pilot Feedback - {submission.category.replace('_', ' ').title()}] {submission.body[:60]}",
        body=_render_feedback_email_body(submission, user),
    )
    submission.email_message_id = result.get("message_id")
    db.add(submission)
    db.commit()
    return {"status": "sent", "message_id": submission.email_message_id}
```

### Patterns NOT Applicable to B16

| Pattern | §Section | Why Not Applicable |
|:---|:---|:---|
| Pre-Commit Staleness Check | §20 | Help chat is append-only; no concurrent edit scenarios requiring 409 guards |
| SSE Endpoint | §18 | Help uses HTTP request-response (or streaming response); not a live-update feed requiring SSE |
| Carrier-Agnostic Adapter | §22 | SMS-specific; B16 has no carrier integration |
| Webhook Handler | §19 | B16 has no inbound webhooks; S3 events go through SQS→Celery, not HTTP webhooks to our API |

---

## E. SHARED MODULE INTERFACES

### `backend/services/help_agent.py` (new — A84)

```python
"""
Help AI agent service.

Responsible for:
- Loading tone-specific prompt templates from prompts/help/
- Constructing the full RAG-injected prompt
- Calling Ollama via generate_text_sync()
"""
from typing import Any


def generate_help_response(
    user_message: str,
    retrieved_chunks: list[dict[str, Any]],
    conversation_history: list[dict[str, str]],
    context_payload: dict[str, Any] | None,
    tone: str,
) -> str:
    """
    Build help agent prompt and generate AI response via Ollama.

    Args:
        user_message:          The user's current question text.
        retrieved_chunks:      Top-K chunks from help_retrieval.retrieve_chunks().
                               Each dict has keys: article_id, section_title, chunk_text, score.
        conversation_history:  Prior turns as [{"role": "user"|"assistant", "content": str}, ...].
                               Used to maintain conversational context.
        context_payload:       Surface context from client (route, recent_actions, user_role,
                               tenant_metadata). May be None for voice-only help invocations.
        tone:                  'conservative' | 'balanced' | 'playful'. Selects prompt template
                               variant from prompts/help/help_agent_{tone}.md.

    Returns:
        The AI assistant's response text. Callers are responsible for persisting
        to help_chat_message.

    Raises:
        ValueError: If tone is not one of the three allowed values.
        httpx.HTTPError: If the Ollama API is unavailable (propagates for caller to handle).
    """
    ...


def _load_prompt_template(tone: str) -> str:
    """
    Load the help agent prompt template for the given tone.

    Template files live at backend/prompts/help/help_agent_{tone}.md.
    Raises ValueError if tone is unrecognised.
    """
    ...


def _render_prompt(
    template: str,
    user_message: str,
    chunks: list[dict[str, Any]],
    history: list[dict[str, str]],
    context: dict[str, Any] | None,
) -> str:
    """
    Fill the template with RAG chunks, history, and context payload.
    Returns the fully assembled prompt string ready for generate_text_sync().
    """
    ...
```

---

### `backend/services/help_retrieval.py` (new — A85)

```python
"""
RAG retrieval service for help corpus.

Responsible for:
- Embedding user queries via OpenAI text-embedding-3-small (or mock in dev)
- Running pgvector cosine similarity search with audience filtering
- Returning top-K chunks with metadata
"""
from typing import Any
from uuid import UUID

from sqlmodel import Session


def retrieve_chunks(
    db: Session,
    query_text: str,
    user_role: str,
    category_hint: str | None = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """
    Embed the query and retrieve the most relevant help article chunks.

    Args:
        db:             Active database session.
        query_text:     The user's question text. Will be embedded via OpenAI API.
        user_role:      Requesting user's role ('owner' | 'accountant' | 'technician').
                        Used to filter chunks to audience-appropriate articles only.
        category_hint:  Optional category slug to narrow the search (e.g. 'integrations').
                        If None, searches across all categories.
        k:              Number of top chunks to return. Default 5.

    Returns:
        List of up to k chunk dicts, ordered by descending cosine similarity score.
        Each dict contains: chunk_id, article_id, section_title, chunk_text, score.

    Raises:
        httpx.HTTPError: If the OpenAI embedding API call fails.
    """
    ...


def _embed_query(query_text: str) -> list[float]:
    """
    Embed a query string via OpenAI text-embedding-3-small.
    Returns a 1536-dimensional vector.

    Note: In dev/test, OPENAI_API_KEY may be unset — callers should catch
    and use a mock vector (all-zeros) for unit test environments.
    """
    ...
```

---

### `backend/services/help_corpus.py` (new — A85)

```python
"""
Help corpus management service.

Responsible for:
- Fetching and parsing article markdown from S3
- Chunking at section boundaries
- Delegating embedding to help_retrieval
- Upserting chunks in pgvector
"""
from sqlmodel import Session


def process_article(
    article_id: str,
    s3_path: str,
    db: Session,
) -> dict:
    """
    Full pipeline: fetch → parse → chunk → hash-check → embed → store.

    Called by the process_help_article Celery task.

    Args:
        article_id:  Article slug matching help_article.article_id.
        s3_path:     Full S3 path of the markdown file.
        db:          Active database session.

    Returns:
        Dict with keys: article_id, chunks_embedded, chunks_skipped, hash_unchanged (bool).

    Raises:
        ValueError:        If frontmatter is missing required fields.
        botocore.exceptions.BotoCoreError: If S3 read fails (propagates for Celery retry).
        httpx.HTTPError:   If OpenAI embedding API fails (propagates for Celery retry).
    """
    ...


def chunk_article(
    markdown_content: str,
    frontmatter: dict,
    article_id: str,
) -> list[dict]:
    """
    Split markdown into chunks at ## section boundaries.

    Rules:
    - Minimum chunk size: 100 tokens (short sections merged with next)
    - Maximum chunk size: 800 tokens (long sections split at paragraph boundaries)
    - Each chunk's chunk_text_with_metadata prepends article frontmatter as context header

    Returns:
        List of chunk dicts with: chunk_order, section_title, chunk_text,
        chunk_text_with_metadata, token_count.
    """
    ...
```

---

### `backend/services/pii_anonymizer.py` (new — A88)

```python
"""
PII detection and replacement utility for the anonymization pipeline.

Used exclusively by anonymize_help_sessions Celery task.
Conservative approach: when uncertain, strip rather than preserve.
"""


def anonymize_text(text: str) -> str:
    """
    Detect and replace PII in a text string.

    Replacement map:
    - Email addresses      → [email]     (regex: [\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,})
    - US phone numbers     → [phone]     (regex: various US formats)
    - UUID/account numbers → [id]        (regex: 8-4-4-4-12 hex pattern + long alphanum)
    - Addresses            → [address]   (street number + word + street suffix)

    Note: NER-based name/business detection is deferred — the initial set
    uses regex only to keep the dependency footprint minimal for MVP.
    NER (spaCy or similar) can be added in Phase 2 when false-positive/negative
    tuning data exists from actual corpus usage.

    Args:
        text: Raw message content possibly containing PII.

    Returns:
        Anonymized text with PII replaced by bracketed placeholders.
    """
    ...


def anonymize_context_payload(payload: dict) -> dict:
    """
    Strip any PII from a context payload dict.

    Context payloads contain only action-type labels per §19.5 privacy boundary,
    but tenant_metadata.size / tenant_metadata.trade fields are safe to retain.
    This function is a safety pass to ensure no entity contents slipped through.

    Args:
        payload: Context payload dict from help_chat_message.context_payload.

    Returns:
        Sanitized copy of the payload dict.
    """
    ...
```

---

## F. OPEN QUESTIONS RESOLVED

### F.1 — Embedding dimension: `vector(1536)` vs `vector(768)`

**Question**: The impl plan notes the embedding dimension decision should be made before A85 starts — changing it after data is embedded requires re-embedding everything.

**Recommended decision**: Use `vector(1536)` for OpenAI `text-embedding-3-small`. Rationale: (a) the existing `ai_service.py::get_embedding()` already calls Ollama's embedding endpoint; a parallel `_embed_query()` function in `help_retrieval.py` will call OpenAI's embedding API for help corpus queries — these are different embedding spaces and different models; (b) `vector(1536)` is the exact dimension for `text-embedding-3-small` (confirmed in arch doc §19.3); (c) if the team later switches to an open-source model, re-embedding a 60-article corpus is a one-off Celery task — the schema supports it with a simple migration to change dimension. **Do not use `vector(768)` — it is incompatible with OpenAI embeddings.**

### F.2 — Should `help_chat_message` carry `tenant_id`?

**Question**: `conversation_message` has an explicit `tenant_id` column (confirmed via MCP query). Should `help_chat_message` follow the same pattern?

**Recommended decision**: Yes — add `tenant_id` to `help_chat_message` even though it is derivable via `session_id → help_chat_session.tenant_id`. Rationale: (a) matches `conversation_message` precedent; (b) simplifies tenant-isolation queries in the anonymization pipeline where joining through `session` adds unnecessary complexity; (c) cost is one UUID column. Include it in the `phase_fe_1_batch_b16_help_chat_message_table` migration with a backfill-style 3-part pattern (add nullable → backfill from session → NOT NULL). Since this is a new table with no existing rows, the 3-part pattern reduces to a simple NOT NULL column definition.

**Updated `help_chat_message` schema**: add `tenant_id UUID NOT NULL` with FK → `tenant(id)` and `ix_help_chat_message_tenant_id` index.

### F.3 — Where does `help.py` model file live?

**Question**: The `db_models_map.md` shows no `help.py` model file. Should new help models go into `ai.py` (since help sessions are AI-related) or a new dedicated file?

**Recommended decision**: Create a new `backend/app/models/help.py` file. Rationale: `ai.py` already contains voice AI models (`ConversationSession`, `ConversationMessage`, `VoiceFeedback`, `VoiceCommandLog`). Adding 6 new models would make the file unwieldy. Help system is a distinct domain. `feedback_submission` is not AI-specific. A dedicated `help.py` keeps domain boundaries clean and matches the project's one-domain-per-file convention.

### F.4 — Does A86 require any migration?

**Question**: A86 is described as "mostly client-side" but references `context_payload` on `help_chat_message`. Is this already covered by A84?

**Recommended decision**: Yes — `context_payload JSONB NULL` is included in the `help_chat_message` table created in A84's migration. A86 is a pure code-and-documentation item (voice action router wiring + context payload contract). **A86 has no migration of its own.** This is confirmed by the impl plan which states: "context payload column on help_chat_message is the only schema addition (already included in A84's schema)."

### F.5 — Which RBAC permissions are needed and do they pre-exist?

**Question**: `SELECT permission_key FROM permission WHERE permission_key LIKE 'help%'` → table does not exist. Permissions are seeded data, not a DB table. Need to confirm what new permissions B16 must seed.

**Recommended decision**: Add the following permissions to the RBAC permission seeder (in `migrations/seed_test_data.py` or the relevant permission seed migration):

| Permission key | Default roles | Source addition |
|:---|:---|:---|
| `help_chat.send_message` | owner, accountant, technician | A84 |
| `help_chat.view_history` | owner, accountant, technician | A84 |
| `help_chat.delete_own_history` | owner, accountant, technician | A88 stub |
| `feedback.submit` | owner, accountant, technician | A87 |
| `admin.help.reprocess_corpus` | platform admin | A85 admin trigger |

These do not conflict with any existing permission keys confirmed from the ledger (`public_link.revoke` = A80, `feedback.submit` appears in the ledger at line 1615 — **`feedback.submit` already exists in the ledger as A87's permission**). Confirm before seeding to avoid duplicate key errors.

### F.6 — PII detection: regex-only or NER for MVP?

**Question**: The impl plan flags "PII detection is the riskiest piece" and recommends a conservative approach.

**Recommended decision**: Regex-only for MVP. No NER dependency (no `spaCy` or similar in the requirements). Rationale: NER adds a significant ML model dependency, memory footprint, and false-positive/negative risk. The training corpus is for future model improvement, not real-time use — quantity of retained training data matters less than quality of anonymization. Regex handles the highest-risk PII (emails, phones, UUIDs, addresses). Name anonymization is deferred to Phase 2 when real corpus data can be used to tune NER accuracy. **This is explicitly consistent with the arch doc §19.9 which says "NER model or simple capitalized-word heuristic."** For MVP, use regex only and document the Phase 2 upgrade path.

### F.7 — Should `process_help_article` and `anonymize_help_sessions` live in the same task file?

**Question**: The arch doc §19.10 shows both tasks in `tasks/help_corpus.py`. Is this the right structure?

**Recommended decision**: Yes — both tasks are corpus-lifecycle concerns and belong together in `tasks/help_corpus.py`. Adding a third task (`generate_help_session_title`) to the same file is also appropriate since it operates on `HelpChatSession`. This mirrors how `tasks/calendar_sync.py` groups all calendar lifecycle tasks together.

---

## G. EXTERNAL DEPENDENCY STATUS

### OpenAI `text-embedding-3-small` API (A85)

| Item | Detail |
|:---|:---|
| **Required for** | A85 `process_help_article` Celery task (corpus embedding) and A84 `help_retrieval.py::_embed_query()` (query-time embedding) |
| **Mock strategy** | `OPENAI_API_KEY` env var unset in dev → `help_retrieval.py::_embed_query()` returns all-zeros vector `[0.0] * 1536`. Article processing task returns early with `{"status": "skipped_no_api_key"}`. Tests patch `help_retrieval._embed_query` to return deterministic test vectors. |
| **Production delivery** | Tom must provision an OpenAI API key and set `OPENAI_API_KEY` env var in ECS task definition before production deployment. |
| **Cost** | ~$0.60 one-time for 60-article corpus embedding + ~$0.10/month for query embeddings at moderate usage (per arch doc §19.3 cost estimate). Well within MVP budget. |
| **Lead time** | Zero — OpenAI API keys are instant. |
| **Tom action** | Create OpenAI account (or use existing), generate API key, add to AWS Secrets Manager as `pilot/prod/OPENAI_API_KEY`, reference in ECS task definition environment. |

---

### S3 Bucket `pilot-help-content` (A85)

| Item | Detail |
|:---|:---|
| **Required for** | A85 article storage and `process_help_article` task (reads article markdown from S3). A85 `GET /api/v1/help/articles/{id}` (fetches markdown on demand). |
| **Mock strategy** | Unit tests mock `boto3.client('s3').get_object()` using `unittest.mock.patch`. Per B2 precedent, add `sys.modules["boto3"] = MagicMock()` guard in test files that import the corpus task. `HELP_CONTENT_BUCKET` env var guard in task — return early if unset (mirrors `VOICE_TRAINING_BUCKET` guard in `tasks/calendar_sync.py`). |
| **Production delivery** | Bucket must be created via Terraform before first production article upload. |
| **Tom action** | Create S3 bucket `pilot-help-content` (or `pilot-help-content-prod`) with versioning enabled and public read disabled. Add IAM policy granting Celery worker ECS task role `s3:GetObject` on `pilot-help-content/*`. Begin authoring ~60 help articles in the S3 structure `s3://pilot-help-content/en/{category}/{article_id}.md`. |
| **Content lead time** | Article authoring (~60 articles) is a content project estimated at 3–4 weeks. Should start in parallel with B16 engineering work. |

---

### S3 Event → SQS → Celery Pipeline (A85)

| Item | Detail |
|:---|:---|
| **Required for** | Triggering `process_help_article` automatically when Tom uploads or updates a help article |
| **Mock strategy** | S3 event trigger is infrastructure-only. In dev/staging, the admin endpoint `POST /api/v1/admin/help/articles/{article_id}/reprocess` serves as the manual trigger substitute. |
| **Production delivery** | Terraform configuration: S3 event notification → SQS queue → Celery worker polling SQS. This is the same event pattern as the QuickBooks webhook SQS queue. |
| **Tom action** | Ensure Terraform DevOps work includes S3 event notification rule and SQS queue for `pilot-help-content` bucket before production launch. |

---

### SendGrid (A87)

| Item | Detail |
|:---|:---|
| **Required for** | A87 `send_feedback_email` Celery task — dispatches feedback to `SUPPORT_EMAIL_ADDRESS` |
| **Mock strategy** | `email_service.py` already has a mock path used across B10/B15. The `send_email()` function returns `{"message_id": "mock-id"}` when `SENDGRID_API_KEY` is unset (per existing mock behavior confirmed in B15). Unit tests mock `send_email` at the `services.email_service` module boundary. |
| **Production delivery** | SendGrid sender domain (`pilotfortrades.com`) SPF/DKIM/DMARC setup is a pre-existing B15 Tom action. A87 inherits the same infrastructure. |
| **Tom action** | Set `SUPPORT_EMAIL_ADDRESS` env var to the appropriate support inbox (e.g. `support@pilotfortrades.com`) in ECS task definition. No additional SendGrid provisioning needed beyond what B15 requires. |

---

### Ollama / Llama 3.x on GPU Instance (A84)

| Item | Detail |
|:---|:---|
| **Required for** | A84 `help_agent.py::generate_help_response()` — calls `generate_text_sync()` which POSTs to Ollama `/chat` |
| **Mock strategy** | `generate_text_sync()` was added to `ai_service.py` in B2. Unit tests for A84 mock `services.help_agent.generate_help_response` directly (do not call through to Ollama). Integration tests require the local Ollama instance (same as B2 tests). |
| **Production delivery** | Existing GPU instance (EC2 `g4dn.xlarge`) running Ollama already serves voice intents (B2). A84 adds a new prompt template — no new model download required. Capacity shared per arch doc §19.1 "same Llama 3.x infrastructure." |
| **Tom action** | None beyond existing B2 GPU provisioning. Verify GPU instance has sufficient VRAM headroom for concurrent help + voice intent requests. Per scaling-logic.md, one `g4dn.xlarge` handles up to 500 customers before needing a second instance. |

---

*All six reads complete. Design frozen. Batch B16 is ready for Python Engineer implementation.*
