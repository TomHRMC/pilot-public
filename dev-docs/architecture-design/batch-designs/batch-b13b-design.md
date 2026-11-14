# Batch B13b Design Document — Mixin Audit Remediation (B8/B11)

**Batch**: B13b  
**Prerequisite**: B13 (audit was triggered by B13 post-implementation review)  
**Gates**: B14 (schema must be clean before B14 starts)  
**Estimated Effort**: 1–2 days  
**Test Subfolder**: `tests/batch_b13b/`  
**Design Date**: 2026-05-03  

---

> ### Context — Why This Batch Exists
>
> After B13 completed, an audit of all B1–B12 new tables revealed that 6 tables added in B8 and B11 were missing standard ORM mixin columns (`created_by`, `updated_by`, and in two cases `created_at`/`created_by`). The architect design prompt did not require mixin assignments per table at the time — that gap has since been fixed in both:
> - `dev-docs/implementation-prompts/pilot-app-backend-additions-architect-prompt.md`
> - `dev-docs/architecture-design/pilot-python-engineer-methods.md` §16.2 Step 1
>
> B13b contains **no new product features**. All 6 migrations are additive `ADD COLUMN` operations on existing tables. Full audit findings are at `dev-docs/architecture-design/batch-designs/batch-b1-b12-mixin-audit.md`.

---

## READ 1 — Batch Plan Reference

Section `§6.B13b` of `dev-docs/analysis/pilot-app-mvp-backend-impl-plan.md`.

## READ 5 — Live DB Schema (verified via postgres-local MCP, 2026-05-03)

All 6 tables confirmed present with their current column shapes. Key findings:

| Table | Has `created_at` | Has `updated_at` | Has `created_by` | Has `updated_by` | Notes |
|:---|:---:|:---:|:---:|:---:|:---|
| `customer_communication_message` | ✅ | ✅ | ❌ | ❌ | Has `audit_user_id` (domain column; NOT a substitute for `created_by`) |
| `customer_communication_message_read_state` | ❌ | ❌ | ❌ | ❌ | Only has `read_at TIMESTAMPTZ NOT NULL DEFAULT now()` |
| `customer_communication_unrouted` | ✅ | ✅ | ❌ | ❌ | Has `resolved_by UUID NULL` (domain column; NOT a substitute for `created_by`) |
| `sms_quota_period` | ✅ | ✅ | ❌ | ❌ | |
| `mobile_push_rate_limit` | ✅ | ✅ | ❌ | ❌ | |
| `mobile_sync_event_audit` | ❌ | ❌ | ❌ | ❌ | Only has `resolved_at TIMESTAMPTZ NOT NULL DEFAULT now()` |

## READ 6 — Existing Backend Code

Model file locations (from `backend/db_models_map.md`):

| Table | Model Class | File |
|:---|:---|:---|
| `customer_communication_message` | `CustomerCommunicationMessage` | `backend/app/models/sms.py` |
| `customer_communication_message_read_state` | `CustomerCommunicationMessageReadState` | `backend/app/models/sms.py` |
| `customer_communication_unrouted` | `CustomerCommunicationUnrouted` | `backend/app/models/sms.py` |
| `sms_quota_period` | `SmsQuotaPeriod` | `backend/app/models/sms.py` |
| `mobile_push_rate_limit` | `MobilePushRateLimit` | `backend/app/models/sync.py` |
| `mobile_sync_event_audit` | `MobileSyncEventAudit` | `backend/app/models/sync.py` |

Import paths from `backend/app_model_imports.md`:
- B11 models: `from app.models.sms import CustomerCommunicationMessage` (etc.)
- B8 models: `from app.models.sync import MobilePushRateLimit, MobileSyncEventAudit`

Mixin definitions: `backend/app/models/mixins.py`

---

## A. MIGRATION PLAN

> **Migration type**: All 6 migrations are additive (`ADD COLUMN`). No existing data is removed or changed. No FK constraints are added to new columns (matches established project convention — `created_by`/`updated_by` do not carry FK constraints in the existing schema). All columns nullable.

### Gap Type Classification

**Gap Type 1** — Table has `created_at` + `updated_at` but missing `created_by` + `updated_by`.  
**Pattern**: `ADD COLUMN created_by UUID NULL` + `ADD COLUMN updated_by UUID NULL`. No trigger changes (the `set_updated_at` trigger is already installed; no new triggers needed).  
**Tables**: `customer_communication_message`, `customer_communication_unrouted`, `sms_quota_period`, `mobile_push_rate_limit`

**Gap Type 2** — Table has NO audit columns at all. Needs full `AppendOnlyMixin` addition.  
**Pattern**: Add `created_at TIMESTAMPTZ NOT NULL` (backfill from domain timestamp) + `created_by UUID NULL`. Install `audit_changes` + `guard_created_immutable` triggers.  
**Tables**: `customer_communication_message_read_state`, `mobile_sync_event_audit`

---

### Migration 1 — `phase_fe_1_batch_b13b_fix_customer_communication_message_audit_mixin`

**Table**: `customer_communication_message`  
**Gap Type**: 1  
**Mixin**: `StandardAuditMixin` (already has `created_at`, `updated_at` — adding the actor columns)

**Columns to add** (confirmed absent via MCP):

| Column | Type | Nullable | Notes |
|:---|:---|:---|:---|
| `created_by` | UUID | YES | Actor who created the message. Outbound messages: populated with `sender_user_id` equivalent. Inbound: NULL (system-received). |
| `updated_by` | UUID | YES | Actor who last updated. Machine updates (status changes): NULL. |

**No trigger changes needed** — `set_updated_at` and `audit_log_changes` triggers already installed from B11.

```python
def upgrade() -> None:
    op.add_column('customer_communication_message',
        sa.Column('created_by', sa.UUID(), nullable=True))
    op.add_column('customer_communication_message',
        sa.Column('updated_by', sa.UUID(), nullable=True))

def downgrade() -> None:
    op.drop_column('customer_communication_message', 'updated_by')
    op.drop_column('customer_communication_message', 'created_by')
```

---

### Migration 2 — `phase_fe_1_batch_b13b_fix_customer_communication_unrouted_audit_mixin`

**Table**: `customer_communication_unrouted`  
**Gap Type**: 1  
**Mixin**: `StandardAuditMixin` (already has `created_at`, `updated_at`)

**Note**: `resolved_by UUID NULL` is a domain column recording who resolved the unrouted message — it is NOT a substitute for `created_by`.

| Column | Type | Nullable | Notes |
|:---|:---|:---|:---|
| `created_by` | UUID | YES | System-created on inbound receipt; always NULL at runtime. |
| `updated_by` | UUID | YES | Updated when resolved; always NULL at runtime (system operation). |

```python
def upgrade() -> None:
    op.add_column('customer_communication_unrouted',
        sa.Column('created_by', sa.UUID(), nullable=True))
    op.add_column('customer_communication_unrouted',
        sa.Column('updated_by', sa.UUID(), nullable=True))

def downgrade() -> None:
    op.drop_column('customer_communication_unrouted', 'updated_by')
    op.drop_column('customer_communication_unrouted', 'created_by')
```

---

### Migration 3 — `phase_fe_1_batch_b13b_fix_sms_quota_period_audit_mixin`

**Table**: `sms_quota_period`  
**Gap Type**: 1  
**Mixin**: `StandardAuditMixin` (already has `created_at`, `updated_at`)

| Column | Type | Nullable | Notes |
|:---|:---|:---|:---|
| `created_by` | UUID | YES | Created by Celery task `rollover_sms_quota_periods`; always NULL at runtime. |
| `updated_by` | UUID | YES | Updated by quota consumption tasks; always NULL at runtime. |

```python
def upgrade() -> None:
    op.add_column('sms_quota_period',
        sa.Column('created_by', sa.UUID(), nullable=True))
    op.add_column('sms_quota_period',
        sa.Column('updated_by', sa.UUID(), nullable=True))

def downgrade() -> None:
    op.drop_column('sms_quota_period', 'updated_by')
    op.drop_column('sms_quota_period', 'created_by')
```

---

### Migration 4 — `phase_fe_1_batch_b13b_fix_mobile_push_rate_limit_audit_mixin`

**Table**: `mobile_push_rate_limit`  
**Gap Type**: 1  
**Mixin**: `StandardAuditMixin` (already has `created_at`, `updated_at`)

| Column | Type | Nullable | Notes |
|:---|:---|:---|:---|
| `created_by` | UUID | YES | Machine-managed by push dispatcher; always NULL at runtime. |
| `updated_by` | UUID | YES | Machine-managed by push dispatcher; always NULL at runtime. |

```python
def upgrade() -> None:
    op.add_column('mobile_push_rate_limit',
        sa.Column('created_by', sa.UUID(), nullable=True))
    op.add_column('mobile_push_rate_limit',
        sa.Column('updated_by', sa.UUID(), nullable=True))

def downgrade() -> None:
    op.drop_column('mobile_push_rate_limit', 'updated_by')
    op.drop_column('mobile_push_rate_limit', 'created_by')
```

---

### Migration 5 — `phase_fe_1_batch_b13b_fix_customer_communication_message_read_state_audit_mixin`

**Table**: `customer_communication_message_read_state`  
**Gap Type**: 2 (no audit columns at all)  
**Mixin**: `AppendOnlyMixin` (`created_at` + `created_by` only — records are never updated; `read_at` is a domain alias)

**Columns to add**:

| Column | Type | Nullable | Notes |
|:---|:---|:---|:---|
| `created_at` | TIMESTAMPTZ | NOT NULL | Backfilled from `read_at` (they are semantically identical — the row is created when the message is read) |
| `created_by` | UUID | YES | The user who marked the message as read; populated in application code |

**Triggers to install** (AppendOnly set — 2 triggers):
- `audit_customer_communication_message_read_state_changes` (calls `audit.log_changes()`)
- `trg_customer_communication_message_read_state_guard_created_immutable` (calls `guard_created_fields_immutable()`)

No `set_updated_at` trigger (AppendOnly tables are never updated).

```python
def upgrade() -> None:
    # Part 1: Add as nullable
    op.add_column('customer_communication_message_read_state',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('customer_communication_message_read_state',
        sa.Column('created_by', sa.UUID(), nullable=True))

    # Part 2: Backfill from read_at (semantically identical)
    op.execute("""
        UPDATE customer_communication_message_read_state
        SET created_at = read_at
    """)

    # Part 3: Lock NOT NULL
    op.alter_column('customer_communication_message_read_state',
        'created_at', nullable=False)

    # Part 4: Install AppendOnly triggers
    op.execute("""
        CREATE TRIGGER audit_customer_communication_message_read_state_changes
        AFTER INSERT OR UPDATE OR DELETE ON customer_communication_message_read_state
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_customer_communication_message_read_state_guard_created_immutable
        BEFORE UPDATE ON customer_communication_message_read_state
        FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
    """)

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_customer_communication_message_read_state_guard_created_immutable ON customer_communication_message_read_state;")
    op.execute("DROP TRIGGER IF EXISTS audit_customer_communication_message_read_state_changes ON customer_communication_message_read_state;")
    op.drop_column('customer_communication_message_read_state', 'created_by')
    op.drop_column('customer_communication_message_read_state', 'created_at')
```

---

### Migration 6 — `phase_fe_1_batch_b13b_fix_mobile_sync_event_audit_audit_mixin`

**Table**: `mobile_sync_event_audit`  
**Gap Type**: 2 (no audit columns at all)  
**Mixin**: `AppendOnlyMixin` (`created_at` + `created_by` only — audit records are never updated)

**Note**: `resolved_at TIMESTAMPTZ NOT NULL DEFAULT now()` is the domain timestamp recording when the escalation was resolved. It serves as the semantic equivalent of `created_at` for this record — the row IS created at the moment of resolution. Backfill `created_at` from `resolved_at`.

**Columns to add**:

| Column | Type | Nullable | Notes |
|:---|:---|:---|:---|
| `created_at` | TIMESTAMPTZ | NOT NULL | Backfilled from `resolved_at`. Going forward, populated simultaneously with `resolved_at` in the resolver service. |
| `created_by` | UUID | YES | The user who resolved the escalation; `resolver_user_id` (domain column) already captures this — `created_by` provides standard audit trail. |

**Triggers to install** (AppendOnly set — 2 triggers):
- `audit_mobile_sync_event_audit_changes` (calls `audit.log_changes()`)
- `trg_mobile_sync_event_audit_guard_created_immutable` (calls `guard_created_fields_immutable()`)

```python
def upgrade() -> None:
    # Part 1: Add as nullable
    op.add_column('mobile_sync_event_audit',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('mobile_sync_event_audit',
        sa.Column('created_by', sa.UUID(), nullable=True))

    # Part 2: Backfill created_at from resolved_at
    op.execute("""
        UPDATE mobile_sync_event_audit
        SET created_at = resolved_at
    """)

    # Part 3: Lock NOT NULL
    op.alter_column('mobile_sync_event_audit', 'created_at', nullable=False)

    # Part 4: Install AppendOnly triggers
    op.execute("""
        CREATE TRIGGER audit_mobile_sync_event_audit_changes
        AFTER INSERT OR UPDATE OR DELETE ON mobile_sync_event_audit
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_mobile_sync_event_audit_guard_created_immutable
        BEFORE UPDATE ON mobile_sync_event_audit
        FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
    """)

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_mobile_sync_event_audit_guard_created_immutable ON mobile_sync_event_audit;")
    op.execute("DROP TRIGGER IF EXISTS audit_mobile_sync_event_audit_changes ON mobile_sync_event_audit;")
    op.drop_column('mobile_sync_event_audit', 'created_by')
    op.drop_column('mobile_sync_event_audit', 'created_at')
```

---

### Migration Summary

| # | Migration Name | Table | Gap Type | Columns Added |
|:---|:---|:---|:---|:---|
| 1 | `phase_fe_1_batch_b13b_fix_customer_communication_message_audit_mixin` | `customer_communication_message` | 1 | `created_by`, `updated_by` |
| 2 | `phase_fe_1_batch_b13b_fix_customer_communication_unrouted_audit_mixin` | `customer_communication_unrouted` | 1 | `created_by`, `updated_by` |
| 3 | `phase_fe_1_batch_b13b_fix_sms_quota_period_audit_mixin` | `sms_quota_period` | 1 | `created_by`, `updated_by` |
| 4 | `phase_fe_1_batch_b13b_fix_mobile_push_rate_limit_audit_mixin` | `mobile_push_rate_limit` | 1 | `created_by`, `updated_by` |
| 5 | `phase_fe_1_batch_b13b_fix_customer_communication_message_read_state_audit_mixin` | `customer_communication_message_read_state` | 2 | `created_at` (backfilled from `read_at`), `created_by` + 2 triggers |
| 6 | `phase_fe_1_batch_b13b_fix_mobile_sync_event_audit_audit_mixin` | `mobile_sync_event_audit` | 2 | `created_at` (backfilled from `resolved_at`), `created_by` + 2 triggers |

---

## B. EXECUTION ORDER

| # | Item | Rationale |
|:---|:---|:---|
| 1 | Migration 1 — `customer_communication_message` | Highest priority gap (messages ARE user-authored; `created_by` is functional, not just convention). Independent of all others. |
| 2 | Migration 5 — `customer_communication_message_read_state` | Second highest priority — missing ALL audit columns. No dependency on Migration 1 but logically grouped with the comms tables. |
| 3 | Migration 2 — `customer_communication_unrouted` | Comms table group — logically grouped for clean diff review. |
| 4 | Migration 3 — `sms_quota_period` | B11 table — independent; lowest priority within B11 tables. |
| 5 | Migration 4 — `mobile_push_rate_limit` | B8 table — independent. |
| 6 | Migration 6 — `mobile_sync_event_audit` | B8 table — last because it requires trigger installation (slightly more complex than Gap Type 1). |

---

## C. NEW API ENDPOINTS

None. This batch contains zero new endpoints. All changes are schema-only migrations and ORM model class declaration updates.

---

## D. PATTERN REUSE DECISIONS

| Pattern | Section | Applied to |
|:---|:---|:---|
| **Manual Alembic migration** — never `--autogenerate` | §16.2 Step 2 | All 6 migrations |
| **`ADD COLUMN` additive pattern** — no data risk, no downtime | §16.2 Step 2 | Gap Type 1 migrations (1–4) |
| **3-part additive pattern** — nullable → backfill → lock | §16.2 Step 2 | Gap Type 2 migrations (5–6) |
| **Mixin assignment** — `StandardAuditMixin` (Gap Type 1), `AppendOnlyMixin` (Gap Type 2) | §16.2 Step 1 (updated) | All 6 models in `sms.py` + `sync.py` |
| **Triple-verify migration** — `upgrade head` → `downgrade -1` → `upgrade head` | §16.2 Step 2 | All 6 migrations mandatory |

**ORM model changes required** (before migrations run):

All 6 model class declarations must be updated to inherit from the correct mixin. Current state has no mixin on these classes. Apply the pattern:

```python
# Before (current)
class CustomerCommunicationMessage(SQLModel, table=True):

# After (correct)
class CustomerCommunicationMessage(StandardAuditMixin, SQLModel, table=True):
```

| Model Class | File | Correct Mixin |
|:---|:---|:---|
| `CustomerCommunicationMessage` | `backend/app/models/sms.py` | `StandardAuditMixin` |
| `CustomerCommunicationUnrouted` | `backend/app/models/sms.py` | `StandardAuditMixin` |
| `SmsQuotaPeriod` | `backend/app/models/sms.py` | `StandardAuditMixin` |
| `CustomerCommunicationMessageReadState` | `backend/app/models/sms.py` | `AppendOnlyMixin` |
| `MobilePushRateLimit` | `backend/app/models/sync.py` | `StandardAuditMixin` |
| `MobileSyncEventAudit` | `backend/app/models/sync.py` | `AppendOnlyMixin` |

---

## E. SHARED MODULE INTERFACES

None. This batch establishes no new shared modules or services.

---

## F. OPEN QUESTIONS RESOLVED

### F1 — `customer_communication_message.audit_user_id` vs `created_by`

**Question**: The table already has `audit_user_id UUID NOT NULL` (a domain column). Is this a substitute for `created_by`?

**Decision**: No. `audit_user_id` is a domain column — its name, purpose, and nullability (`NOT NULL`) are specific to the SMS message domain. `created_by` is the standard mixin actor column and must be added separately. At the application layer, for outbound messages, `created_by` should be populated with the same value as `audit_user_id`. For inbound messages (system-received), `created_by` will be NULL.

### F2 — `customer_communication_message_read_state.read_at` vs `created_at`

**Question**: This table's `read_at` is semantically equivalent to `created_at`. Should we rename `read_at` or add a separate `created_at`?

**Decision**: Add a separate `created_at` column and backfill from `read_at`. Do not rename `read_at` — renaming would require all application code referencing `read_at` to be updated, which is outside B13b scope. Both columns will coexist; `read_at` remains the domain-specific name used in queries; `created_at` satisfies the mixin convention and trigger requirements.

### F3 — `mobile_sync_event_audit.resolved_at` vs `created_at`

**Decision**: Same resolution as F2. Add `created_at` backfilled from `resolved_at`. Both columns coexist. `resolved_at` is the semantically correct name for the business event; `created_at` satisfies mixin convention.

### F4 — Are triggers already installed on Gap Type 1 tables?

**Decision**: Yes — the B8 and B11 migrations installed `audit.log_changes()`, `set_updated_at`, and `guard_created_immutable` triggers on all tables that had `created_at`/`updated_at` at creation time. Adding `created_by`/`updated_by` columns does not require new triggers — the existing triggers already fire correctly on all column updates.

---

## G. EXTERNAL DEPENDENCY STATUS

None. All 6 migrations are pure PostgreSQL DDL operations. No external services (Stripe, Cognito, SendGrid, Telnyx, S3) are involved. No Tom actions required before or after this batch.
