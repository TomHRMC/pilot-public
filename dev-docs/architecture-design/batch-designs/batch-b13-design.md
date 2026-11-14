# Batch B13 Design Document — Account Security & Data Export

**Batch**: B13  
**Items**: A72, A68, A69, A70, A71  
**Prerequisite**: B9 (settings resolver), B10 (notification infrastructure)  
**Gates**: None  
**Estimated Effort**: 19–24 days  
**Test Subfolder**: `tests/batch_b13/`  
**Design Date**: 2026-05-02

---

> ### ✅ IMPLEMENTATION STATUS: COMPLETE
>
> Batch B13 was implemented as designed and is **fully complete** as of 2026-05-03. All five items (A72, A68, A69, A70, A71), all eight migrations, all API endpoints, both Celery tasks, and both new service modules have been delivered against this document's original intent.
>
> **One design doc gap was discovered post-implementation**: the migration table specifications in §A omitted mixin assignments (`StandardAuditMixin` / `AppendOnlyMixin`) and their corresponding triggers. The implementation engineer made the correct decision given the incomplete spec — attaching only the `audit.log_changes()` trigger to each table rather than applying the standard 3-trigger set to tables that lacked `created_at`/`updated_at` columns. This is not a regression; it is a schema gap that requires remediation migrations.
>
> **See §H — Post-Implementation Corrections** for the complete remediation plan.

---

## A. MIGRATION PLAN

> All six new tables confirmed absent via `information_schema` query (MCP returned `[]`). All `tenant_settings` MFA columns confirmed absent. All `tenant` subscription columns confirmed absent. No pre-existing collision.

### Migration 1 — `phase_fe_1_batch_b13_user_session_history` (A72)

**New table: `user_session_history`**

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `tenant_id` | UUID | NOT NULL | — | FK → `tenant.id` |
| `user_id` | UUID | NOT NULL | — | FK → `user.id` |
| `first_login_at` | TIMESTAMPTZ | NOT NULL | — | Set only on row creation |
| `total_session_count` | INTEGER | NOT NULL | `0` | Incremented every login |
| `last_login_at` | TIMESTAMPTZ | NOT NULL | — | Updated every login |

**Mixin**: `StandardAuditMixin` — adds `created_at TIMESTAMPTZ NOT NULL`, `updated_at TIMESTAMPTZ NOT NULL`, `created_by UUID NULL`, `updated_by UUID NULL`
**PK**: composite `(tenant_id, user_id)`
**Unique constraint**: `(tenant_id, user_id)` (natural PK — no separate unique needed)
**Indexes**: `ix_user_session_history_tenant_id`, `ix_user_session_history_user_id`
**Triggers**: `audit_user_session_history_changes`, `trg_user_session_history_guard_created_immutable`, `trg_user_session_history_set_updated_at`

```sql
-- upgrade
CREATE TABLE user_session_history (
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID NULL,
    updated_by UUID NULL,
    tenant_id UUID NOT NULL REFERENCES tenant(id),
    user_id   UUID NOT NULL REFERENCES "user"(id),
    first_login_at TIMESTAMPTZ NOT NULL,
    total_session_count INTEGER NOT NULL DEFAULT 0,
    last_login_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, user_id)
);
CREATE INDEX ix_user_session_history_tenant_id ON user_session_history(tenant_id);
CREATE INDEX ix_user_session_history_user_id   ON user_session_history(user_id);
```

---

### Migration 2 — `phase_fe_1_batch_b13_mfa_policy_settings` (A68)

**Column additions to `tenant_settings`** (confirmed absent via MCP):

| Column | Type | Nullable | Default |
|:---|:---|:---|:---|
| `tenant_mfa_required` | BOOLEAN | NOT NULL | `false` |
| `tenant_mfa_required_grace_period_starts_at` | TIMESTAMPTZ | YES | `NULL` |
| `tenant_mfa_grace_period_days` | INTEGER | NOT NULL | `7` |

Uses 3-part additive pattern (add nullable → backfill → constrain):
- `tenant_mfa_required`: add nullable → backfill `false` → set `NOT NULL DEFAULT false`
- `tenant_mfa_grace_period_days`: add nullable → backfill `7` → set `NOT NULL DEFAULT 7`
- `tenant_mfa_required_grace_period_starts_at`: stays nullable (NULL = policy never activated)

---

### Migration 3 — `phase_fe_1_batch_b13_mfa_grace_period_tracking` (A68)

**New table: `mfa_grace_period_tracking`**

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `tenant_id` | UUID | NOT NULL | — | FK → `tenant.id` |
| `user_id` | UUID | NOT NULL | — | FK → `user.id` |
| `grace_started_at` | TIMESTAMPTZ | NOT NULL | — | When tenant policy activated |
| `enrolled_at` | TIMESTAMPTZ | YES | `NULL` | Set when user completes enrollment |
| `enforcement_activated_at` | TIMESTAMPTZ | YES | `NULL` | Set when user logs in mid-grace |

**PK**: composite `(tenant_id, user_id)`  
**Unique constraint**: `(tenant_id, user_id)` (natural PK)  
**Indexes**: `ix_mfa_grace_period_tracking_tenant_id`, `ix_mfa_grace_period_tracking_user_id`

---

### Migration 4 — `phase_fe_1_batch_b13_user_mfa_method` (A69)

**New table: `user_mfa_method`**

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `mfa_method_id` | UUID | NOT NULL | `gen_random_uuid()` | PK |
| `tenant_id` | UUID | NOT NULL | — | FK → `tenant.id` |
| `user_id` | UUID | NOT NULL | — | FK → `user.id` |
| `method_type` | TEXT | NOT NULL | — | `totp \| sms \| email` |
| `enrolled_at` | TIMESTAMPTZ | NOT NULL | — | |
| `last_used_at` | TIMESTAMPTZ | YES | `NULL` | |
| `cognito_method_id` | TEXT | NOT NULL | — | Cognito's reference for this method |
| `verification_status` | TEXT | NOT NULL | `'verified'` | `verified \| needs_reverification` |
| `metadata` | JSONB | YES | `NULL` | e.g., last 4 digits of phone |

**PK**: `mfa_method_id`  
**Unique constraint**: `(tenant_id, user_id, method_type)` — one method type per user  
**Indexes**: `ix_user_mfa_method_tenant_id`, `ix_user_mfa_method_user_id`

---

### Migration 5 — `phase_fe_1_batch_b13_user_mfa_recovery_code` (A69)

**New table: `user_mfa_recovery_code`**

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `code_id` | UUID | NOT NULL | `gen_random_uuid()` | PK |
| `tenant_id` | UUID | NOT NULL | — | FK → `tenant.id` |
| `user_id` | UUID | NOT NULL | — | FK → `user.id` |
| `code_hash` | TEXT | NOT NULL | — | bcrypt-hashed; plaintext never stored |
| `generated_at` | TIMESTAMPTZ | NOT NULL | — | |
| `used_at` | TIMESTAMPTZ | YES | `NULL` | Set on redemption |
| `set_id` | UUID | NOT NULL | — | Groups 10 codes generated together |

**PK**: `code_id`  
**Indexes**: `ix_user_mfa_recovery_code_tenant_id`, `ix_user_mfa_recovery_code_user_id`, `ix_user_mfa_recovery_code_set_id`

---

### Migration 6 — `phase_fe_1_batch_b13_user_session_metadata` (A70)

**New table: `user_session_metadata`**

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `session_id` | UUID | NOT NULL | `gen_random_uuid()` | PK |
| `tenant_id` | UUID | NOT NULL | — | FK → `tenant.id` |
| `user_id` | UUID | NOT NULL | — | FK → `user.id` |
| `device_fingerprint` | TEXT | NOT NULL | — | User-Agent + characteristics |
| `display_label` | TEXT | NOT NULL | — | e.g., "Chrome on macOS" |
| `ip_address` | INET | NOT NULL | — | |
| `geolocation` | TEXT | YES | `NULL` | City/state from IP lookup |
| `created_at` | TIMESTAMPTZ | NOT NULL | `now()` | |
| `last_active_at` | TIMESTAMPTZ | NOT NULL | — | Updated on token refresh |
| `revoked_at` | TIMESTAMPTZ | YES | `NULL` | Set on revocation |

**PK**: `session_id`  
**Indexes**: `ix_user_session_metadata_tenant_id`, `ix_user_session_metadata_user_id`, `ix_user_session_metadata_user_id_revoked_at` (composite for "active sessions for user" query)

**Cross-reference to `auth_refresh_token`**: The `user_session_metadata` row is keyed by `session_id`, which is stored as a column on `auth_refresh_token` via a migration in A70. This creates the link that allows session revocation to cascade to token invalidation. See §E for the `SessionRevokeService` interface.

---

### Migration 7 — `phase_fe_1_batch_b13_auth_refresh_token_session_id` (A70)

**Column addition to `auth_refresh_token`** (confirmed absent via MCP — current columns: `id, user_id, tenant_id, jti, rotated_from_jti, issued_at, expires_at, revoked_at, revoked_reason, ip, user_agent`):

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `session_id` | UUID | YES | `NULL` | FK → `user_session_metadata.session_id`; NULL for tokens issued before B13 |

Uses 3-part pattern: add nullable (stays nullable — pre-B13 tokens legitimately have no session_id).

---

### Migration 8 — `phase_fe_1_batch_b13_data_export_request` (A71)

**New table: `data_export_request`**

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `export_id` | UUID | NOT NULL | `gen_random_uuid()` | PK |
| `tenant_id` | UUID | NOT NULL | — | FK → `tenant.id` |
| `user_id` | UUID | NOT NULL | — | FK → `user.id` |
| `requested_at` | TIMESTAMPTZ | NOT NULL | `now()` | |
| `status` | TEXT | NOT NULL | `'pending'` | `pending \| processing \| ready \| expired \| failed` |
| `s3_path` | TEXT | YES | `NULL` | Set when ready |
| `signed_url` | TEXT | YES | `NULL` | 7-day signed S3 URL; set when ready |
| `expires_at` | TIMESTAMPTZ | YES | `NULL` | 7 days after `ready` status |
| `data_scope` | TEXT | NOT NULL | — | `full_tenant` (owner) or `user_specific` (technician) |
| `failure_reason` | TEXT | YES | `NULL` | Set on failure |

**PK**: `export_id`  
**Indexes**: `ix_data_export_request_tenant_id`, `ix_data_export_request_user_id`, `ix_data_export_request_status`

---

### Migration Naming Summary

| Order | Migration Name | Item | Logical Unit |
|:---|:---|:---|:---|
| 1 | `phase_fe_1_batch_b13_user_session_history` | A72 | New table |
| 2 | `phase_fe_1_batch_b13_mfa_policy_settings` | A68 | `tenant_settings` columns |
| 3 | `phase_fe_1_batch_b13_mfa_grace_period_tracking` | A68 | New table |
| 4 | `phase_fe_1_batch_b13_user_mfa_method` | A69 | New table |
| 5 | `phase_fe_1_batch_b13_user_mfa_recovery_code` | A69 | New table |
| 6 | `phase_fe_1_batch_b13_user_session_metadata` | A70 | New table |
| 7 | `phase_fe_1_batch_b13_auth_refresh_token_session_id` | A70 | FK column on existing table |
| 8 | `phase_fe_1_batch_b13_data_export_request` | A71 | New table |

---

## B. EXECUTION ORDER

| # | Item | Rationale |
|:---|:---|:---|
| 1 | **A72** — First-Session Detection | Simplest item; login-hook integration is straightforward. Establishes the session-history table before A70 extends the login flow with heavier concerns. |
| 2 | **A68** — Tenant MFA Policy + Grace Period | Requires B9 settings resolver for reading `tenant_mfa_required`. Must be implemented before A69 because the grace period tracking table records enrollment state that A69 updates on successful enrollment. |
| 3 | **A69** — Multi-Method MFA Enrollment + Recovery Codes | Depends on A68 (grace period tracking row updated on enrollment completion). Largest item. Must exist before A70 because A70's session context exists "post-MFA" — the sessions table is populated after full login including MFA challenge. |
| 4 | **A70** — Active Sessions List + Revoke | Depends on A69 (session context post-MFA). Also wraps the password-change integration hook (G3/cross-check). Provides the `SessionRevokeService.revoke_others()` shared function consumed by the password-change hook. |
| 5 | **A71** — Data Export Request Pipeline | Independent of A68–A70 (no MFA/session dependency). Last because it requires S3 service integration and the streaming Celery task pattern is the most complex piece in the batch. Placing it last ensures no unresolved dependencies block it. |

---

## C. NEW API ENDPOINTS

> Auth requirement: all endpoints require JWT unless noted. RBAC via `require_permission()` from `backend/core/permissions.py`.

### A72 — Session History

| Method | Path | Auth | Permission | Request | Response |
|:---|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/users/me/session-history` | JWT | `account.session.view_own` (any role) | — | `{ first_login_at: datetime, total_session_count: int, last_login_at: datetime }` |

**Side effect on login**: On every successful login, upsert `user_session_history`. If row does not exist: `INSERT` with `first_login_at = now()`, `total_session_count = 1`. If row exists: `UPDATE SET total_session_count = total_session_count + 1, last_login_at = now()`.

---

### A68 — MFA Policy

| Method | Path | Auth | Permission | Request | Response |
|:---|:---|:---|:---|:---|:---|
| `PUT` | `/api/v1/settings/tenant/mfa-required` | JWT | `mfa.policy.edit` (owner only) | `{ enabled: bool, grace_period_days: int \| None }` | `{ tenant_mfa_required: bool, grace_period_starts_at: datetime \| None, grace_period_days: int }` |
| `GET` | `/api/v1/users/me/mfa-status` | JWT | any authenticated | — | `{ enrolled_methods: list[MethodType], tenant_policy_required: bool, grace_period_active: bool, grace_ends_at: datetime \| None, enforcement_activated: bool }` |

**Login endpoint extension**: Existing login response extended with `enrollment_required: bool` field. When `tenant_mfa_required = true` AND user has no enrolled methods AND user is within grace period (or grace expired), return `enrollment_required: true` with `403 enrollment_required` body. Frontend uses this to route to MFA enrollment wizard. Existing sessions are unaffected until next login.

---

### A69 — MFA Enrollment & Login Challenge

| Method | Path | Auth | Permission | Request | Response |
|:---|:---|:---|:---|:---|:---|
| `POST` | `/api/v1/users/me/mfa/methods/{method_type}/enroll-start` | JWT | `mfa.enroll_self` (all) | `{}` | TOTP: `{ qr_code_uri: str, secret: str }` / SMS+Email: `{ destination_masked: str }` |
| `POST` | `/api/v1/users/me/mfa/methods/{method_type}/enroll-confirm` | JWT | `mfa.enroll_self` (all) | `{ code: str }` | `{ method_id: uuid, enrolled_at: datetime }` |
| `DELETE` | `/api/v1/users/me/mfa/methods/{method_id}` | JWT | `mfa.reset_self` (all) | — | `204 No Content` |
| `POST` | `/api/v1/users/me/mfa/recovery-codes/generate` | JWT | `mfa.enroll_self` (all) | — | `{ codes: list[str], set_id: uuid }` (plaintext — only time visible) |
| `GET` | `/api/v1/users/me/mfa/recovery-codes/status` | JWT | any authenticated | — | `{ unused_code_count: int, last_generated_at: datetime \| None }` |
| `POST` | `/api/v1/users/me/mfa/login-challenge/initiate` | Partially-authed (post-password, pre-MFA) | n/a | `{}` | `{ available_methods: list[MethodType] }` |
| `POST` | `/api/v1/users/me/mfa/login-challenge/verify` | Partially-authed | n/a | `{ method_type: str, code: str }` | `{ access_token: str, session_id: uuid }` |
| `POST` | `/api/v1/admin/users/{user_id}/mfa/reset` | JWT | `mfa.reset_user` (owner only) | — | `204 No Content` |

**Safeguards on DELETE method**:
- Cannot delete last enrolled method when `tenant_mfa_required = true` (returns `409 Conflict` with `last_method_required` code)
- Password re-verification required for self-reset of own MFA (pass current password in body)
- Owner reset of other user's MFA sends notification to that user via `notification_outbox`

---

### A70 — Active Sessions

| Method | Path | Auth | Permission | Request | Response |
|:---|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/users/me/sessions` | JWT | `account.session.revoke_own` (all) | — | `list[{ session_id: uuid, display_label: str, ip_address: str, geolocation: str\|None, created_at: datetime, last_active_at: datetime, is_current: bool }]` |
| `DELETE` | `/api/v1/users/me/sessions/{session_id}` | JWT | `account.session.revoke_own` (all) | — | `204 No Content` |
| `POST` | `/api/v1/users/me/sessions/revoke-others` | JWT | `account.session.revoke_own` (all) | — | `{ revoked_count: int }` |

**Password-change integration hook (G3)**: Existing password change endpoint (confirmed at `backend/api/routes/auth.py`) is extended in B13 to call `SessionRevokeService.revoke_others(db, tenant_id, user_id, current_session_id)` on successful password change. This invalidates all refresh tokens except the current session's.

---

### A71 — Data Export

| Method | Path | Auth | Permission | Request | Response |
|:---|:---|:---|:---|:---|:---|
| `POST` | `/api/v1/users/me/data-exports` | JWT | `account.data_export.request` (all) | — | `{ export_id: uuid, status: "pending", requested_at: datetime }` |
| `GET` | `/api/v1/users/me/data-exports` | JWT | `account.data_export.request` (all) | — | `list[DataExportStatus]` |
| `GET` | `/api/v1/users/me/data-exports/{export_id}` | JWT | `account.data_export.request` (all) | — | `DataExportStatus` |

**`DataExportStatus` response shape**:
```json
{
  "export_id": "uuid",
  "status": "pending|processing|ready|expired|failed",
  "requested_at": "datetime",
  "expires_at": "datetime|null",
  "signed_url": "string|null",
  "data_scope": "full_tenant|user_specific",
  "failure_reason": "string|null"
}
```

**Frequency limit**: `POST` returns `429 Too Many Requests` if user has a `pending` or `processing` export, or a `ready`/`failed` export within the past 24 hours.

---

## D. PATTERN REUSE DECISIONS

### §1.5 Shared Modules — Established or Consumed

| Module | Established | Consumed by |
|:---|:---|:---|
| `services/setting_resolver.py::get_effective_setting()` (B9) | B9 | A68 (reads `tenant_mfa_required`), A68 (reads `tenant_mfa_grace_period_days`) |
| `services/notification_resolver.py` (B10) | B10 | A68 (MFA grace reminders dispatched via `notification_outbox`) |
| `services/session_revoke_service.py` (new in B13) | **B13 (A70)** | A70 routes; A70 password-change hook |
| `services/data_export_compiler.py` (new in B13) | **B13 (A71)** | A71 Celery task |
| `tasks/mfa_grace_reminders.py` (new in B13) | **B13 (A68)** | Celery Beat daily 9 AM |
| `tasks/data_export_pipeline.py` (new in B13) | **B13 (A71)** | A71 POST endpoint via `.delay()` |

### Python Engineer Methods — Applicable Patterns

| Section | Pattern | Applied to |
|:---|:---|:---|
| **§16.2 Step 2** | Manual Alembic migration (never `--autogenerate`); naming convention `phase_fe_1_batch_b13_{description}` | All 8 migrations in this batch |
| **§16.2 Step 2** | 3-part additive column migration (nullable → backfill → constrain) | Migration 2 (`tenant_settings` MFA columns), Migration 7 (`auth_refresh_token.session_id`) |
| **§16.3** | Tenant-scoped `select()` queries — no bare `db.get(Model, id)` | All new routes in `mfa.py`, `sessions.py`, `data_exports.py` |
| **§17.1** | Periodic poll task (`@celery_app.task`, no bind, no retry) | `tasks/mfa_grace_reminders.py::notify_mfa_grace_period_reminders` — runs daily |
| **§17.2** | Event-driven retryable task (`bind=True, max_retries=3`) | `tasks/data_export_pipeline.py::process_data_export` — enqueued on POST |
| **§17.3** | Register new tasks in `core/celery_app.py` `imports` + `beat_schedule` | Both new tasks |
| **§17.4** | Test `_impl()` function directly, not Celery wrapper | `_process_data_export_impl()` in `tasks/data_export_pipeline.py` |
| **§16.5** | Definition of Done checklist (schema diff = ZERO required) | End of each item |

### Setting Resolver Reuse (A68)

`get_effective_setting()` from `backend/services/setting_resolver.py` is called in the MFA enforcement middleware:

```python
mfa_required, scope = get_effective_setting(
    db=db,
    tenant_id=current_user.tenant_id,
    setting_key="tenant_mfa_required",
    fallback=False,
)
```

The `setting_key` value `"tenant_mfa_required"` must match both the `TenantSettings` column name (added in Migration 2) and a key in `core/system_defaults.py`. The system default is `False`.

### Notification Outbox Reuse (A68)

MFA grace period reminders are dispatched via the `notification_outbox` table (confirmed shape via MCP: `category_id`, `sub_trigger_id`, `recipient_user_id`, `channel`, `body`, `priority`, etc.). The `notify_mfa_grace_period_reminders` task constructs outbox rows with:
- `category_id = "system_announcements"`
- `sub_trigger_id = "mfa_grace_day_7"` (forced-minimum push per arch doc §4.5)
- `priority = 1` (critical) on day 7; `priority = 5` (standard) days 0–6

---

## E. SHARED MODULE INTERFACES

### `services/session_revoke_service.py` (new — A70)

```python
"""
Session revocation service for Pilot for Trades.

Provides shared revocation logic used by:
- DELETE /api/v1/users/me/sessions/{session_id}  (A70 route)
- POST /api/v1/users/me/sessions/revoke-others   (A70 route)
- Password-change endpoint hook (G3 / arch doc §4.8.1)
"""
from typing import Optional
from uuid import UUID
from sqlmodel import Session, select
from app.models.security import UserSessionMetadata
from app.models.auth import AuthRefreshToken


def revoke_session(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    session_id: UUID,
    reason: str = "user_revoked",
) -> bool:
    """
    Revoke a single session by session_id.

    Sets user_session_metadata.revoked_at and invalidates the associated
    auth_refresh_token via revoked_at + revoked_reason.

    Args:
        db:         Active SQLModel session.
        tenant_id:  Tenant scope (prevents cross-tenant access).
        user_id:    Owner of the session (prevents cross-user access).
        session_id: The session to revoke.
        reason:     Revocation reason stored on the token record.

    Returns:
        True if session was found and revoked; False if not found.

    Raises:
        Nothing — missing session returns False (caller handles 404).
    """
    ...


def revoke_others(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    current_session_id: UUID,
    reason: str = "revoke_others",
) -> int:
    """
    Revoke all sessions for user_id except current_session_id.

    Used by:
    - POST /api/v1/users/me/sessions/revoke-others
    - Password change hook (G3) — called with reason="password_changed"

    Args:
        db:                 Active SQLModel session.
        tenant_id:          Tenant scope.
        user_id:            User whose other sessions are revoked.
        current_session_id: Session to preserve.
        reason:             Revocation reason for audit trail.

    Returns:
        Count of sessions revoked.
    """
    ...
```

**File path**: `backend/services/session_revoke_service.py`

---

### `services/data_export_compiler.py` (new — A71)

```python
"""
Data export compilation service for Pilot for Trades.

Generates per-entity CSV files and bundles them into a ZIP with MANIFEST.json.
Streams to S3 using boto3 multipart upload to avoid in-memory bloat for large tenants.
"""
from typing import Generator
from uuid import UUID
from sqlmodel import Session


def stream_export_to_s3(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    data_scope: str,
    export_id: UUID,
) -> tuple[str, str]:
    """
    Stream tenant/user data to S3 as a ZIP archive.

    Data scope controls what is included:
    - "full_tenant" (owner): customers, jobs, quotes, invoices,
      time_entries, expenses, communications, contacts
    - "user_specific" (technician): own jobs, own time_entries,
      own expenses, own communications only

    Uses Python generators + boto3 multipart upload to avoid
    loading large datasets into memory.

    Args:
        db:         Active SQLModel session.
        tenant_id:  Tenant whose data to export.
        user_id:    Requesting user (used for scope + MANIFEST.json).
        data_scope: "full_tenant" or "user_specific".
        export_id:  UUID of the data_export_request row (for naming).

    Returns:
        (s3_path, signed_url) — s3_path is the key in S3;
        signed_url is a 7-day presigned GET URL.

    Raises:
        ExportScopeError: If data_scope is not a valid value.
        boto3.exceptions.S3UploadFailedError: On S3 upload failure.
    """
    ...


def _iter_entity_csv_rows(
    db: Session,
    entity_name: str,
    tenant_id: UUID,
    user_id: Optional[UUID],
    data_scope: str,
) -> Generator[dict, None, None]:
    """
    Yield dicts for a single entity type, scoped per data_scope.
    Caller feeds rows into the CSV writer without loading all rows at once.
    """
    ...
```

**File path**: `backend/services/data_export_compiler.py`

---

### `tasks/mfa_grace_reminders.py` (new — A68)

```python
"""
Celery task: daily MFA grace period reminder notifications.

Registered in core/celery_app.py as:
    "notify_mfa_grace_period_reminders"
    schedule: crontab(hour=9, minute=0)  # 9 AM UTC daily
"""
from typing import Dict
from core.celery_app import celery_app
from core.db import get_db
from sqlmodel import Session


@celery_app.task(name="notify_mfa_grace_period_reminders")
def notify_mfa_grace_period_reminders() -> Dict[str, int]:
    """
    Identifies tenants with active MFA grace periods. For each such tenant,
    finds unenrolled users and dispatches escalating reminder notifications
    via notification_outbox.

    Escalation schedule:
      Days 0-3: gentle copy, priority=5 (standard)
      Days 4-6: urgent copy, priority=3
      Day 7:    critical copy, priority=1 (forced-minimum push)

    Returns: {"tenants_processed": N, "notifications_dispatched": M}
    """
    ...


def _notify_mfa_grace_period_reminders_impl(db: Session) -> Dict[str, int]:
    """Inner implementation — separated for testability without Celery."""
    ...
```

**File path**: `backend/tasks/mfa_grace_reminders.py`

---

### `tasks/data_export_pipeline.py` (new — A71)

```python
"""
Celery task: process a pending data export request.

Registered in core/celery_app.py as event-driven (no Beat schedule).
Enqueued via .delay() from POST /api/v1/users/me/data-exports.
"""
from typing import Any, Dict
from core.celery_app import celery_app
from core.db import get_db
from sqlmodel import Session


@celery_app.task(
    name="process_data_export",
    bind=True,
    max_retries=3,
)
def process_data_export(self, export_id: str) -> Dict[str, Any]:
    """
    Process a pending data_export_request row.

    Steps:
      1. Load export_request, set status="processing"
      2. Call data_export_compiler.stream_export_to_s3()
      3. Set status="ready", s3_path, signed_url, expires_at
      4. Dispatch email via existing email_service.py
      5. On failure: set status="failed", failure_reason

    Args:
        export_id: UUID string of the data_export_request.

    Retries: up to 3 times with 60-second countdown on transient errors.
    """
    ...


def _process_data_export_impl(export_id: str, db: Session) -> Dict[str, Any]:
    """Inner implementation — separated for testability without Celery."""
    ...
```

**File path**: `backend/tasks/data_export_pipeline.py`

---

## F. OPEN QUESTIONS RESOLVED

### F1 — Where do new B13 models live in the model file structure?

**Question**: `backend/app/models/auth.py` already contains `AuthMfaOtp` (existing OTP table), `AuthRefreshToken`, and other auth models. Should B13's new MFA models go there, or in a new `security.py`?

**Decision**: New models go in **`backend/app/models/security.py`** (new file). Rationale: `auth.py` currently has 30 classes and is approaching unwieldy length. B13 adds 5 more models (`UserSessionHistory`, `MfaGracePeriodTracking`, `UserMfaMethod`, `UserMfaRecoveryCode`, `UserSessionMetadata`, `DataExportRequest`) plus updates to `TenantSettings`. Splitting at this boundary keeps `auth.py` for authentication mechanics (tokens, OTP, password) and `security.py` for account security features (MFA enrollment, sessions, exports). The new model file must be added to `backend/db_models_map.md` after the batch.

### F2 — Does `auth_mfa_otp` (existing table) conflict with A69's new `user_mfa_method` design?

**Question**: The live DB already has `auth_mfa_otp` (confirmed via MCP: channel, code_hash, expires_at, attempt_count). Does B13 use this table or replace it?

**Decision**: These are **different concerns**. `auth_mfa_otp` is a transient OTP-code-challenge store (codes sent during login and MFA-enrollment confirmation, expire in minutes). `user_mfa_method` is a persistent enrollment record (which methods the user has configured). B13 uses `auth_mfa_otp` for the short-lived verification codes sent during `enroll-confirm` and `login-challenge/verify` — no conflict. No migration changes to `auth_mfa_otp` are needed.

### F3 — How does `user_session_metadata` link to `auth_refresh_token` for revocation?

**Question**: A70 revokes sessions by invalidating refresh tokens. But `user_session_metadata` is a new table. What is the join key?

**Decision**: Migration 7 adds `auth_refresh_token.session_id UUID NULL FK → user_session_metadata.session_id`. On login (after MFA if applicable), a `user_session_metadata` row is created and its `session_id` is stored on the corresponding `auth_refresh_token` row. Revocation flow: find `user_session_metadata` row → get all `auth_refresh_token` rows where `session_id = that_id` AND `revoked_at IS NULL` → set `revoked_at = now()`, `revoked_reason = reason`. Pre-B13 tokens have `session_id = NULL` and cannot be revoked via this path (acceptable: they expire naturally per 30-day TTL).

### F4 — Which `notification_category` is used for MFA grace period reminders?

**Question**: Should grace reminders use `"system_announcements"` or a new category?

**Decision**: Use the existing `"system_announcements"` category (already seeded in B10). Sub-trigger IDs to register: `mfa_grace_reminder_gentle`, `mfa_grace_reminder_urgent`, `mfa_grace_reminder_critical`. Day-7 critical sub-trigger must be marked as forced-minimum push per arch doc §4.5. These sub-trigger rows are seeded in the `phase_fe_1_batch_b13_mfa_policy_settings` migration as `INSERT INTO notification_category_sub_trigger` rows.

### F5 — G2/G3: Do profile and password-change endpoints pre-exist?

**Question**: Cross-check findings G2/G3 ask whether `PATCH /api/v1/users/me/profile` and `POST /api/v1/users/me/change-password` already exist.

**Decision**: Inspection of `backend/api/routes/` shows `auth.py`, `user_preferences.py`, `user_color.py` — **no `profile.py` or `password.py`**. Profile editing (name, email, timezone) and password change are **not pre-existing** as B13-spec endpoints. However, these are outside the strict B13 item list (A68–A72). **Resolution**: B13 scope includes:
- The password-change integration hook required by G3 (calling `SessionRevokeService.revoke_others()` on success) — this can only be wired once the password-change endpoint exists, so B13 must also implement `POST /api/v1/users/me/change-password` as a prerequisite hook target. Estimated 0.5 day added to A70 scope.
- Profile editing (`PATCH /api/v1/users/me/profile`) is deferred to B13 cleanup as a gap-fill (G2), added as a 1.5-day sub-item in A70's implementation block. It requires no new migrations (all columns exist on `user` table: `first_name`, `last_name`, `email_verified_at`, `preferred_mfa_channel`, etc.).

### F6 — Data export S3 bucket: use existing bucket or new one?

**Question**: A71 streams exports to S3. Is there a pre-existing export bucket?

**Decision**: Per arch doc §4.8.2, the module is `tasks/data_export_pipeline.py`. A new S3 bucket `pilot-data-exports-{env}` should be created via Terraform. The existing `backend/services/s3_service.py` provides the S3 client wrapper — reuse `s3_service.py`'s presigned URL generation. The bucket name is injected via `config.py` env var `DATA_EXPORT_S3_BUCKET`. This is a **Tom action** (see §G).

### F7 — bcrypt vs. existing code_hash pattern for recovery codes?

**Question**: `auth_mfa_otp` uses `code_hash` (VARCHAR). A69 specifies bcrypt for recovery codes. Should recovery codes use the same hashing pattern?

**Decision**: Recovery codes use **bcrypt** (via `passlib.hash.bcrypt` — already in requirements per `auth_password_history` usage). Rationale: OTP codes are 6-digit (small search space, short-lived — SHA256 adequate); recovery codes are 10-character (larger search space, long-lived, high-value — bcrypt correct). `code_hash` column is TEXT (not VARCHAR) to accommodate bcrypt's 60-character output. This matches `auth_password_history.password_hash` pattern.

---

## G. EXTERNAL DEPENDENCY STATUS

### AWS Cognito — A68, A69

| Concern | Detail | Mock Strategy | Tom Action |
|:---|:---|:---|:---|
| **TOTP enrollment** (`AssociateSoftwareToken` + `VerifySoftwareToken`) | Cognito API for TOTP enrollment via QR code URI | `MockCognitoMfaClient` returning canned `{ secret_code, session }` | Cognito user pool must have software token MFA enabled in pool settings. Verify before A69 starts. |
| **SMS MFA enrollment** (`SetUserMFAPreference` + phone number verification) | Cognito's SMS MFA requires verified phone in Cognito user attributes | `MockCognitoMfaClient` returning success for any phone | Cognito user pool must have SMS MFA enabled + SNS sending role configured. |
| **Email OTP** | Cognito does not natively support email MFA — Pilot sends its own email OTP via `auth_mfa_otp` table + `email_service.py` | `MockEmailService` already used in tests | No Cognito action needed for email OTP; uses existing `auth_mfa_otp` flow. |
| **Login challenge** (`InitiateAuth` → `RespondToAuthChallenge`) | Existing Cognito auth flow extended with MFA challenge step | Existing `MockCognitoClient` extended | No new Cognito config needed if pool already configured for MFA. |

**Lead time**: TOTP + SMS MFA must be enabled in the AWS Cognito User Pool before A69 can be tested in any environment connected to Cognito. **Tom must enable these pool settings before A69 integration testing begins.** Dev can use `MockCognitoMfaClient` until then.

---

### SendGrid — A71

| Concern | Detail | Mock Strategy | Tom Action |
|:---|:---|:---|:---|
| **Data export ready email** | `tasks/data_export_pipeline.py` dispatches "Your data export is ready" email via `backend/services/email_service.py` using existing SendGrid integration (established in B4) | `MockEmailService` (already pattern-established in B4 tests) | No new SendGrid action required — existing API key and domain configuration covers this template. Tom must add the template subject/body to `email_service.py`'s template registry. |

---

### AWS S3 — A71

| Concern | Detail | Mock Strategy | Tom Action |
|:---|:---|:---|:---|
| **Export bucket** | `pilot-data-exports-{env}` S3 bucket for ZIP archive storage | `MockS3Service` wrapping `s3_service.py`; local dev uses MinIO or `moto` S3 mock | Tom must create bucket via Terraform before production deployment. 7-day object lifecycle policy on export files. `DATA_EXPORT_S3_BUCKET` env var must be added to ECS task definition. |

---

### MaxMind GeoLite2 — A70

| Concern | Detail | Mock Strategy | Tom Action |
|:---|:---|:---|:---|
| **IP geolocation** | City-level accuracy for `user_session_metadata.geolocation` field | Return `None` for geolocation in dev/test (field is nullable; UI shows "Unknown location") | Tom must download MaxMind GeoLite2 City database (free with registration at maxmind.com) and add to the Docker image or ECS task volume. Alternatively, use a lightweight API like `ip-api.com` (free tier: 45 req/min). **Recommendation**: use `ip-api.com` HTTP call for MVP simplicity; switch to GeoLite2 embedded DB for Scale tier if latency becomes a concern. |

---

### AWS Cognito — A70 (session revocation)

| Concern | Detail | Mock Strategy | Tom Action |
|:---|:---|:---|:---|
| **Refresh token invalidation** | `SessionRevokeService.revoke_session()` sets `auth_refresh_token.revoked_at` in Pilot's DB. This invalidates Pilot's own token validation logic, but does **not** call Cognito's `GlobalSignOut` (which would invalidate all devices). For MVP, Pilot-side token revocation is sufficient — the next API call from a revoked session returns 401 when Pilot's token validator checks `revoked_at`. | No Cognito action needed in dev/test | No Tom action required for MVP. Phase 2 evaluation: add `GlobalSignOut` call to revoke-others for full Cognito session termination. |

---

## H. POST-IMPLEMENTATION CORRECTIONS

> **Status**: Remediation required. Batch B13 is complete but the schema is missing standard audit mixin columns on all six new tables. This section defines the remediation work that must be performed as a follow-on task.

### Root Cause

The §A migration table specifications omitted mixin assignments. Every new table in the project uses one of three mixins (`backend/app/models/mixins.py`):

| Mixin | Columns added | Triggers |
|:---|:---|:---|
| `StandardAuditMixin` | `created_at TIMESTAMPTZ NOT NULL`, `updated_at TIMESTAMPTZ NOT NULL`, `created_by UUID NULL`, `updated_by UUID NULL` | `audit_{table}_changes`, `trg_{table}_guard_created_immutable`, `trg_{table}_set_updated_at` |
| `AppendOnlyMixin` | `created_at TIMESTAMPTZ NOT NULL`, `created_by UUID NULL` | `audit_{table}_changes`, `trg_{table}_guard_created_immutable` |
| `MachineLogMixin` | `created_at TIMESTAMPTZ NOT NULL` | `audit_{table}_changes` |

Because §A did not specify which mixin each B13 table uses, the implementation engineer correctly applied only `audit.log_changes()` — the only safe choice for tables without `created_at`/`updated_at` columns. This is not a regression; it is an incomplete schema that needs additive remediation migrations.

---

### Correct Mixin Assignment Per Table

| Table | Correct Mixin | Reasoning |
|:---|:---|:---|
| `user_session_history` | **`StandardAuditMixin`** | Row is upserted on every login — `updated_at` tracks last-write; `created_by`/`updated_by` for audit trail |
| `mfa_grace_period_tracking` | **`StandardAuditMixin`** | Mutable — `enrolled_at` and `enforcement_activated_at` are set post-creation; `updated_at` tracks state transitions |
| `user_mfa_method` | **`StandardAuditMixin`** | Mutable — `last_used_at` and `verification_status` change after creation; security-sensitive record warrants full audit trail |
| `user_mfa_recovery_code` | **`AppendOnlyMixin`** | Codes are generated once then only `used_at` (a domain column) changes. The record itself is never mutated post-creation |
| `user_session_metadata` | **`StandardAuditMixin`** | Already has `created_at DEFAULT now()` from implementation — missing `updated_at`, `created_by`, `updated_by`; `last_active_at` and `revoked_at` mutate the row |
| `data_export_request` | **`StandardAuditMixin`** | Status transitions through a lifecycle (`pending → processing → ready → failed`); full audit trail required |

---

### Remediation Migrations Required

Six remediation migrations must be written, one per affected table. Migration naming convention:

```
phase_fe_1_batch_b13_fix_{table_name}_audit_mixin
```

#### Tables requiring `StandardAuditMixin` remediation (5 tables)

For each of `user_session_history`, `mfa_grace_period_tracking`, `user_mfa_method`, `user_session_metadata`, `data_export_request`:

```python
def upgrade() -> None:
    # Part 1: Add columns as nullable
    op.add_column('{table}', sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('{table}', sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('{table}', sa.Column('created_by', sa.UUID(), nullable=True))
    op.add_column('{table}', sa.Column('updated_by', sa.UUID(), nullable=True))

    # Part 2: Backfill existing rows
    op.execute("UPDATE {table} SET created_at = now(), updated_at = now()")

    # Part 3: Lock created_at NOT NULL (updated_at stays NOT NULL too for consistency)
    op.alter_column('{table}', 'created_at', nullable=False)
    op.alter_column('{table}', 'updated_at', nullable=False)

    # Part 4: Install triggers
    op.execute("""
        CREATE TRIGGER audit_{table}_changes
        AFTER INSERT OR UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_{table}_guard_created_immutable
        BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_{table}_set_updated_at
        BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_{table}_set_updated_at ON {table};")
    op.execute("DROP TRIGGER IF EXISTS trg_{table}_guard_created_immutable ON {table};")
    op.execute("DROP TRIGGER IF EXISTS audit_{table}_changes ON {table};")
    op.drop_column('{table}', 'updated_by')
    op.drop_column('{table}', 'created_by')
    op.drop_column('{table}', 'updated_at')
    op.drop_column('{table}', 'created_at')
```

**Exception for `user_session_metadata`**: `created_at` already exists (`DEFAULT now()`). Migration must skip the `created_at` add/backfill/lock steps and only add `updated_at`, `created_by`, `updated_by`.

#### Table requiring `AppendOnlyMixin` remediation (1 table)

For `user_mfa_recovery_code`:

```python
def upgrade() -> None:
    # Part 1: Add columns as nullable
    op.add_column('user_mfa_recovery_code', sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('user_mfa_recovery_code', sa.Column('created_by', sa.UUID(), nullable=True))

    # Part 2: Backfill
    op.execute("UPDATE user_mfa_recovery_code SET created_at = now()")

    # Part 3: Lock
    op.alter_column('user_mfa_recovery_code', 'created_at', nullable=False)

    # Part 4: Install triggers (AppendOnly = audit + immutable guard only; no set_updated_at)
    op.execute("""
        CREATE TRIGGER audit_user_mfa_recovery_code_changes
        AFTER INSERT OR UPDATE OR DELETE ON user_mfa_recovery_code
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_user_mfa_recovery_code_guard_created_immutable
        BEFORE UPDATE ON user_mfa_recovery_code
        FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
    """)

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_user_mfa_recovery_code_guard_created_immutable ON user_mfa_recovery_code;")
    op.execute("DROP TRIGGER IF EXISTS audit_user_mfa_recovery_code_changes ON user_mfa_recovery_code;")
    op.drop_column('user_mfa_recovery_code', 'created_by')
    op.drop_column('user_mfa_recovery_code', 'created_at')
```

---

### ORM Model Updates Required

The six B13 models in `backend/app/models/security.py` must have their class declarations updated to inherit from the correct mixin **before** the remediation migrations run:

```python
# Before (current — no mixin)
class UserSessionHistory(SQLModel, table=True):

# After (correct)
class UserSessionHistory(StandardAuditMixin, SQLModel, table=True):
```

Apply the same change to: `MfaGracePeriodTracking`, `UserMfaMethod`, `UserSessionMetadata`, `DataExportRequest` (→ `StandardAuditMixin`) and `UserMfaRecoveryCode` (→ `AppendOnlyMixin`).

---

### Migration Summary for Remediation Task

| Migration Name | Table | Mixin | Columns Added |
|:---|:---|:---|:---|
| `phase_fe_1_batch_b13_fix_user_session_history_audit_mixin` | `user_session_history` | `StandardAuditMixin` | `created_at, updated_at, created_by, updated_by` |
| `phase_fe_1_batch_b13_fix_mfa_grace_period_tracking_audit_mixin` | `mfa_grace_period_tracking` | `StandardAuditMixin` | `created_at, updated_at, created_by, updated_by` |
| `phase_fe_1_batch_b13_fix_user_mfa_method_audit_mixin` | `user_mfa_method` | `StandardAuditMixin` | `created_at, updated_at, created_by, updated_by` |
| `phase_fe_1_batch_b13_fix_user_mfa_recovery_code_audit_mixin` | `user_mfa_recovery_code` | `AppendOnlyMixin` | `created_at, created_by` |
| `phase_fe_1_batch_b13_fix_user_session_metadata_audit_mixin` | `user_session_metadata` | `StandardAuditMixin` | `updated_at, created_by, updated_by` (created_at already exists) |
| `phase_fe_1_batch_b13_fix_data_export_request_audit_mixin` | `data_export_request` | `StandardAuditMixin` | `created_at, updated_at, created_by, updated_by` |

Each migration must pass the mandatory triple-verify: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head`. Schema diff must be ZERO after all six run.
