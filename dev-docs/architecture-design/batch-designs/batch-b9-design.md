# Batch B9 Design Document — Settings Infrastructure

**Batch**: B9  
**Theme**: Settings Infrastructure  
**Items**: A53, A52, A54, A55  
**Estimated effort**: 8–11 days  
**Test subfolder**: `tests/batch_b9/`  
**Prerequisite batches**: None (parallel-safe; best started after B8)  
**Gates**: B10 (notification preference gate uses three-tier resolver), B12 (voice persona uses three-tier resolver), B13 (MFA policy reads settings resolver)  
**Author**: Pilot Architect  
**Date**: 2026-05-02

---

## Table of Contents

- [A. Migration Plan](#a-migration-plan)
- [B. Execution Order](#b-execution-order)
- [C. New API Endpoints](#c-new-api-endpoints)
- [D. Pattern Reuse Decisions](#d-pattern-reuse-decisions)
- [E. Shared Module Interfaces](#e-shared-module-interfaces)
- [F. Open Questions Resolved](#f-open-questions-resolved)
- [G. External Dependency Status](#g-external-dependency-status)

---

## A. Migration Plan

### Pre-Migration Schema Verification

**Confirmed via `postgres-local` MCP before writing this document:**

| Table | Status | Notes |
|:---|:---|:---|
| `tenant_settings` | ✅ EXISTS — 38 columns | Flat single-row-per-tenant table; all existing settings stored as typed columns |
| `tenant_setting` (singular) | ❌ Does NOT exist | Row-per-key pattern not yet in DB |
| `user_setting_override` | ❌ Does NOT exist | New table required by A53 |
| `system_config` | ❌ Does NOT exist | System defaults will be Python constants, not a DB table |
| `setting_catalog` / `platform_setting` | ❌ Do NOT exist | Catalog will be a Python registry, not a DB table |

**Confirmed pre-existing columns on `tenant_settings`** (none of the following need to be added — they are already present):

All 38 columns including: `default_labor_rate_cents`, `default_billable_labor_rate_cents`, `default_quote_validity_days`, `default_invoice_terms_days`, `require_approval_for_tech_quotes`, `max_discount_pct_owner`, `tech_color_palette`, `report_chart_threshold`, `etc_variance_owner_notify_pct`, `etc_variance_note_required_pct`, `margin_bucket_boundaries`, `margin_target_pct`, `calendar_conflict_auto_expire_enabled`, `calendar_conflict_auto_expire_days`, `calendar_conflict_pre_warning_days`, `photo_upload_wifi_only`, `photo_local_retention_days`, `offline_hard_limit_hours`, `voice_offline_audio_storage_limit_mb`, `qb_auto_expire_customer_enabled`, `qb_auto_expire_customer_direction`, `qb_auto_expire_quote_enabled`, `qb_auto_expire_quote_direction`, `qb_auto_expire_invoice_enabled`, `qb_auto_expire_invoice_direction`, `qb_auto_expire_expense_enabled`, `qb_auto_expire_expense_direction`, `qb_auto_expire_days`, `qb_pre_warning_days`, `background_sync_enabled`, `background_sync_wifi_only`, `background_sync_battery_floor_pct`, `background_sync_push_interval_minutes`, plus the standard audit columns (`created_at`, `updated_at`, `created_by`, `updated_by`).

---

### Migration 1 — `user_setting_override` Table

**Migration name**: `phase_fe_1_batch_b9_user_setting_override`

**Rationale**: A53 introduces per-user setting overrides as the first tier of the three-tier resolution chain. This is the only new table in B9; the catalog uses a Python registry, and tenant settings write against the existing `tenant_settings` columnar table.

```python
# migrations/versions/<rev>_phase_fe_1_batch_b9_user_setting_override.py

def upgrade() -> None:
    op.create_table(
        "user_setting_override",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("setting_key", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_user_setting_override_tenant"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE", name="fk_user_setting_override_user"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="RESTRICT", name="fk_user_setting_override_created_by"),
        sa.ForeignKeyConstraint(["updated_by"], ["user.id"], ondelete="RESTRICT", name="fk_user_setting_override_updated_by"),
        sa.PrimaryKeyConstraint("tenant_id", "user_id", "setting_key", name="pk_user_setting_override"),
    )
    op.create_index("ix_user_setting_override_tenant_user", "user_setting_override", ["tenant_id", "user_id"])
    op.create_index("ix_user_setting_override_tenant_key", "user_setting_override", ["tenant_id", "setting_key"])

    # Mandatory triggers (per §13.4 migration standards)
    op.execute("""
        CREATE TRIGGER audit_user_setting_override_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.user_setting_override
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_user_setting_override_guard_created_immutable
        BEFORE UPDATE ON public.user_setting_override
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_user_setting_override_set_updated_at
        BEFORE UPDATE ON public.user_setting_override
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_user_setting_override_changes ON public.user_setting_override;")
    op.execute("DROP TRIGGER IF EXISTS trg_user_setting_override_guard_created_immutable ON public.user_setting_override;")
    op.execute("DROP TRIGGER IF EXISTS trg_user_setting_override_set_updated_at ON public.user_setting_override;")
    op.drop_index("ix_user_setting_override_tenant_key", table_name="user_setting_override")
    op.drop_index("ix_user_setting_override_tenant_user", table_name="user_setting_override")
    op.drop_table("user_setting_override")
```

**Schema summary** — `user_setting_override`:

| Column | Type | Nullable | Notes |
|:---|:---|:---|:---|
| `tenant_id` | UUID | NOT NULL | PK part 1; FK → `tenant.id` |
| `user_id` | UUID | NOT NULL | PK part 2; FK → `user.id` ON DELETE CASCADE |
| `setting_key` | TEXT | NOT NULL | PK part 3; matches a registered key in the Python catalog |
| `value` | JSONB | NOT NULL | Override value; shape validated against catalog `data_type` |
| `created_at` | TIMESTAMPTZ | NOT NULL | Auto-set by mixin trigger |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Auto-set by `set_updated_at()` trigger |
| `created_by` | UUID | NULL | FK → `user.id` RESTRICT |
| `updated_by` | UUID | NULL | FK → `user.id` RESTRICT |

**Indexes**: `ix_user_setting_override_tenant_user (tenant_id, user_id)`, `ix_user_setting_override_tenant_key (tenant_id, setting_key)`

---

### No Additional Migrations in B9

- **No migration for the settings catalog** — catalog is a static Python registry in `backend/core/setting_catalog.py` (see §E).
- **No migration for system defaults** — system defaults live in `backend/core/system_defaults.py` (see §E).
- **No migration for `tenant_settings`** — all 38 settings columns already exist. B9's write endpoints (`PUT /api/v1/settings/{key}`) update columns in the existing `tenant_settings` table via `setattr()` + `db.commit()`. No structural schema change required.

---

## B. Execution Order

| Position | Item | One-Line Rationale |
|:---:|:---|:---|
| 1 | **A53** — Effective-Value Resolution Endpoint | Foundation: creates `user_setting_override` table, `services/setting_resolver.py`, and `core/system_defaults.py` — every other item in the batch calls these. Also delivers the `GET /api/v1/settings/{key}/effective` endpoint consumed by all settings UIs. |
| 2 | **A52** — Settings Catalog Endpoint | Depends on A53: catalog endpoint calls `get_effective_setting_for_user()` to populate `current_effective_value` and `current_scope` per entry. Also requires `core/setting_catalog.py` to be stable before catalog response shapes are tested. |
| 3 | **A54** — Tenant Settings Write Endpoints | Depends on A53: response body of every write includes `effective_value` and `scope` (computed via resolver after the write commits). Special-case `require_approval_for_tech_quotes` toggle also queries resolver state. |
| 4 | **A55** — Per-User Override Write Endpoints | Depends on A53 (writes to `user_setting_override`; response computed via `get_effective_setting_for_user()`) and A54 (borrows the same per-setting validation registry used in tenant writes). Thin wrapper; can be parallelized with A54 after A53 completes. |

---

## C. New API Endpoints

All endpoints use prefix `/api/v1/settings`. All return RFC 7807 errors on failure. All require valid Cognito JWT (RS256). All support `Idempotency-Key` header on mutating methods.

---

### A53 — GET /api/v1/settings/{key}/effective

```
GET /api/v1/settings/{key}/effective?user_id={user_id_optional}
```

**Auth**: JWT required — any authenticated role  
**RBAC permission**: `settings.read` (all roles inherit)  
**Purpose**: Returns the resolved effective value for a single setting key, with scope annotation.

**Path parameter**:
- `key` — setting key string (must exist in the catalog; 404 if not found)

**Query parameter**:
- `user_id` — optional UUID; if omitted, resolves for the requesting user

**Request body**: none

**Response 200**:
```json
{
  "key": "background_sync_push_interval_minutes",
  "value": 5,
  "scope": "system",
  "tenant_override_exists": false,
  "user_override_exists": false,
  "allows_user_override": true
}
```

**Response 404**: setting key not found in catalog  
**Response 403**: requesting `user_id` for another user without owner/accountant role

---

### A52 — GET /api/v1/settings/catalog

```
GET /api/v1/settings/catalog
```

**Auth**: JWT required — any authenticated role  
**RBAC permission**: `settings.read` (all roles inherit; catalog entries with `requires_role` are filtered out for callers without that role)  
**Purpose**: Returns the full tenant-scoped catalog of all settings with metadata and resolved effective values. Cached per tenant; invalidated on settings write.

**Request body**: none

**Response 200**:
```json
{
  "settings": [
    {
      "key": "require_approval_for_tech_quotes",
      "label": "Require approval for tech quotes",
      "description": "When enabled, quotes created by technicians must be reviewed and approved by an owner or accountant before sending.",
      "sub_surface_path": "/settings/quotes/approval",
      "data_type": "boolean",
      "validation_rules": {},
      "system_default": true,
      "current_effective_value": true,
      "current_scope": "tenant",
      "revertible": true,
      "requires_role": "owner",
      "allows_user_override": false
    },
    {
      "key": "background_sync_push_interval_minutes",
      "label": "Background sync push interval",
      "description": "How often (in minutes) the server sends a silent push to trigger background sync on mobile devices.",
      "sub_surface_path": "/settings/mobile/background-sync",
      "data_type": "integer",
      "validation_rules": {"min": 1, "max": 60},
      "system_default": 5,
      "current_effective_value": 5,
      "current_scope": "system",
      "revertible": false,
      "requires_role": "owner",
      "allows_user_override": false
    }
  ]
}
```

**Cache strategy**: cached in Redis keyed by `settings_catalog:{tenant_id}:{user_id}` for the requesting user's role-filtered view. Invalidated when any settings write completes (A54 write endpoint calls `_invalidate_settings_catalog_cache(tenant_id)` after commit).

---

### A54 — PUT /api/v1/settings/{key}

```
PUT /api/v1/settings/{key}
```

**Auth**: JWT required  
**RBAC permission**: `settings.tenant.write` (owner, accountant only)  
**Purpose**: Write a tenant-level setting override. Creates or updates the value in the `tenant_settings` row for the requesting user's tenant.

**Request body**:
```json
{
  "value": <setting-typed>,
  "expected_updated_at": "2026-05-01T12:00:00Z"
}
```
- `value`: required; type matches catalog `data_type` for the key
- `expected_updated_at`: optional; if provided, triggers pre-commit staleness check on `tenant_settings.updated_at` (returns 409 if stale, per `utils/staleness_check.py::assert_not_stale()`)

**Response 200**:
```json
{
  "key": "etc_variance_owner_notify_pct",
  "value": 40,
  "effective_value": 40,
  "scope": "tenant",
  "updated_at": "2026-05-02T13:00:00Z"
}
```

**Special-case response for `require_approval_for_tech_quotes` toggle OFF** (includes count to surface confirmation dialog in UI):
```json
{
  "key": "require_approval_for_tech_quotes",
  "value": false,
  "effective_value": false,
  "scope": "tenant",
  "updated_at": "2026-05-02T13:00:00Z",
  "pending_quote_count": 3
}
```

**Response 404**: setting key not in catalog  
**Response 403**: caller lacks `settings.tenant.write` permission  
**Response 409**: staleness check fired — returns refreshed `tenant_settings` snapshot  
**Response 422**: per-setting validation failure — returns structured validation error with violated rule

**Audit log entry** (written on every 200):
- `audit_event` row via `set_audit_context_sync()` + `audit.log_changes()` trigger on `tenant_settings`
- The trigger captures `OLD` → `NEW` snapshots for the column being changed

---

### A54 — DELETE /api/v1/settings/{key}

```
DELETE /api/v1/settings/{key}
```

**Auth**: JWT required  
**RBAC permission**: `settings.tenant.write` (owner, accountant only)  
**Purpose**: Revert a tenant setting to its system default. For nullable columns, sets the column to `NULL`. For non-nullable columns, sets to the system default constant from `core/system_defaults.py`.

**Request body**: none

**Response 200**:
```json
{
  "key": "calendar_conflict_auto_expire_days",
  "value": null,
  "effective_value": 30,
  "scope": "system",
  "updated_at": "2026-05-02T13:00:00Z"
}
```

**Response 404**: setting key not in catalog  
**Response 400**: setting is `revertible: false` in the catalog (e.g., `require_approval_for_tech_quotes` always has an explicit tenant value after initial setup)

---

### A55 — PUT /api/v1/settings/{key}/user-override

```
PUT /api/v1/settings/{key}/user-override
```

**Auth**: JWT required — any authenticated role  
**RBAC permission**: `settings.user_override.write` (all roles for own overrides)  
**Purpose**: Write a user-level override for a setting that allows per-user overrides. Only writes for the requesting user (no admin write-on-behalf-of-user in MVP).

**Request body**:
```json
{
  "value": <setting-typed>
}
```

**Response 200**:
```json
{
  "key": "background_sync_enabled",
  "value": false,
  "effective_value": false,
  "scope": "user",
  "updated_at": "2026-05-02T13:00:00Z"
}
```

**Response 403**: tenant does not allow per-user override for this setting (`allows_user_override: false`)  
**Response 404**: setting key not in catalog  
**Response 422**: value fails per-setting validation

**Audit log entry**: `set_audit_context_sync()` + insert into `user_setting_override` fires `audit.log_changes()` trigger

---

### A55 — DELETE /api/v1/settings/{key}/user-override

```
DELETE /api/v1/settings/{key}/user-override
```

**Auth**: JWT required — any authenticated role  
**RBAC permission**: `settings.user_override.write` (own overrides only)  
**Purpose**: Revert user's override — removes the row from `user_setting_override`. Requesting user falls back to tenant or system default.

**Request body**: none

**Response 200**:
```json
{
  "key": "background_sync_enabled",
  "value": null,
  "effective_value": true,
  "scope": "tenant",
  "updated_at": "2026-05-02T13:00:00Z"
}
```

**Response 404**: no active override exists for this user+key (idempotent — not an error in practice, but 404 for discoverability)

---

## D. Pattern Reuse Decisions

### §21 (pilot-python-engineer-methods.md) — Three-Tier Settings Resolver

**Section reference**: `pilot-python-engineer-methods.md §21`

This is the **primary pattern for B9**. The entire batch exists to establish this pattern as a shared service module consumed by B10 (notification preferences), B12 (voice persona tone), B13 (MFA policy), and B14 (subscription limits).

**Mapping to batch items**:

| Pattern Function | Used By |
|:---|:---|
| `get_effective_setting(db, tenant_id, setting_key, fallback)` | A52 (catalog response), A54 (response body after write), A55 (response body after write) |
| `get_effective_setting_for_user(db, tenant_id, user_id, setting_key, fallback)` | A52 (per-user catalog), A53 (effective endpoint with `user_id`), A55 (response after user override write) |

**Implementation deviation from the §21 template**: The `§21` template imports from `app.models.settings` (`TenantSetting`, `SystemConfig`) — new models in a new file. However, given that the **live DB already has `tenant_settings`** (a flat 38-column table, confirmed via MCP query), B9 does NOT create a new row-per-key `tenant_setting` table. Instead:

- `get_effective_setting()` reads the tenant's setting value via `getattr(tenant_settings_row, setting_key, None)` against the existing `TenantSettings` SQLModel
- System defaults are a Python `dict` in `backend/core/system_defaults.py` (no DB table required)
- User-level overrides read from the new `user_setting_override` table (the only new DB table)

This avoids a destructive migration of the existing `tenant_settings` columnar schema while meeting the three-tier contract.

---

### §20 (pilot-python-engineer-methods.md) — Pre-Commit Staleness Check

**Section reference**: `pilot-python-engineer-methods.md §20`

**Used by**: A54 `PUT /api/v1/settings/{key}` — accepts optional `expected_updated_at` timestamp; calls `assert_not_stale()` from `utils/staleness_check.py` (established in B3/A19) before updating `tenant_settings`.

```python
# Inside PUT /api/v1/settings/{key} handler (A54)
from utils.staleness_check import assert_not_stale

settings_row = db.exec(
    select(TenantSettings)
    .where(TenantSettings.tenant_id == current_user.tenant_id)
).first()

assert_not_stale(
    expected_updated_at=payload.expected_updated_at,
    actual_updated_at=settings_row.updated_at,
    refreshed_payload=_settings_row_to_dict(settings_row),
    entity_label="tenant settings",
)
```

---

### §16.5 (mvp-arch.md) — System Default + Tenant Override Two-Tier Configuration

**Section reference**: `mvp-arch.md §16.5`

B9 **establishes the implementation** of the two-tier (and three-tier extension) resolver that `§16.5` documents architecturally. All subsequent batches that reference `§16.5` (B10, B12, B13, B14) call `get_effective_setting()` from `services/setting_resolver.py`.

**Setting keys using this pattern** (all already have tenant-side columns in `tenant_settings`):
- `calendar_conflict_auto_expire_days` / system default 30
- `calendar_conflict_pre_warning_days` / system default 7
- `qb_auto_expire_days` / system default 60
- `qb_pre_warning_days` / system default 14
- `background_sync_push_interval_minutes` / system default 5
- `etc_variance_owner_notify_pct` / system default 50
- `etc_variance_note_required_pct` / system default 10
- `margin_target_pct` / system default 20
- `offline_hard_limit_hours` / system default 72

---

### §16.1 (mvp-arch.md) — Optimistic UI with Pending Badges

**Section reference**: `mvp-arch.md §16.1`

A54 write endpoints return `200` with the new effective value immediately so the settings UI can confirm the change optimistically without a follow-up `GET /api/v1/settings/catalog`. Cache invalidation runs asynchronously after the response returns.

---

### §13.4 (pilot-python-engineer-methods.md) — Strict Schema Naming & Triggers

**Section reference**: `pilot-python-engineer-methods.md §13.4`

All three mandatory triggers (audit, immutable guard, updated_at sync) are included in the `user_setting_override` migration as specified above. Constraint names follow `fk_table_column` convention.

---

### Existing TODO_B9_RESOLVER Refactor (mobile_background_sync.py)

**File**: `backend/services/mobile_background_sync.py`

This file contains inline comments flagging replacement with the B9 resolver:
```python
# TODO_B9_RESOLVER: replace with get_effective_setting()
SYSTEM_BG_SYNC_PUSH_INTERVAL_MINUTES = 5
```

After A53 ships, the Python engineer must:
1. Replace `SYSTEM_BG_SYNC_PUSH_INTERVAL_MINUTES` constant with a call to `get_effective_setting(db, tenant_id, "background_sync_push_interval_minutes", fallback=5)`
2. Remove the inline two-tier resolver function (`_get_push_interval()`) from lines ~157–167 in the same file
3. Write a regression test confirming behavior is unchanged for the default case

This refactor is part of A53's **Definition of Done** checklist.

---

## E. Shared Module Interfaces

### Module 1 — `services/setting_resolver.py` (NEW — established in A53)

**File path**: `backend/services/setting_resolver.py`

```python
"""
Three-tier settings resolver for Pilot for Trades.

Resolution chain:
  User override (if tenant allows) → Tenant override → System default → Fallback constant

Established in B9/A53. Consumed by B10 (notification preferences), B12 (voice persona),
B13 (MFA policy), B14 (subscription tier limits), and all settings API endpoints.
"""
from typing import Any
from uuid import UUID

from sqlmodel import Session, select
from app.models.core import TenantSettings
from app.models.settings import UserSettingOverride  # new model added in B9
from core.system_defaults import SYSTEM_DEFAULTS


def get_effective_setting(
    db: Session,
    tenant_id: UUID,
    setting_key: str,
    fallback: Any = None,
) -> tuple[Any, str]:
    """
    Two-tier resolver: tenant override → system default → fallback constant.

    Reads the tenant's value from the existing TenantSettings flat table using
    getattr(). System defaults are Python constants in core/system_defaults.py.

    Args:
        db:           Active SQLModel session.
        tenant_id:    Tenant whose settings to resolve.
        setting_key:  Must match both a TenantSettings column name and a key in
                      core/setting_catalog.SETTING_CATALOG.
        fallback:     Value to return if neither tenant nor system default exists.

    Returns:
        (value, scope) where scope is 'tenant' | 'system' | 'fallback'
    """
    settings_row = db.exec(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
    ).first()

    # Tier 1: tenant override (None = not set; use system default)
    if settings_row is not None:
        tenant_value = getattr(settings_row, setting_key, None)
        if tenant_value is not None:
            return tenant_value, "tenant"

    # Tier 2: system default from Python constants
    system_value = SYSTEM_DEFAULTS.get(setting_key)
    if system_value is not None:
        return system_value, "system"

    # Tier 3: fallback constant from calling code
    return fallback, "fallback"


def get_effective_setting_for_user(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    setting_key: str,
    fallback: Any = None,
) -> tuple[Any, str]:
    """
    Three-tier resolver: user override → tenant override → system default → fallback.

    Only applies the user tier when the setting catalog marks allows_user_override=True
    AND the tenant has not disabled per-user overrides for this key.

    Args:
        db:           Active SQLModel session.
        tenant_id:    Tenant whose settings and policies to resolve.
        user_id:      User whose overrides to check in tier 1.
        setting_key:  Must exist in core/setting_catalog.SETTING_CATALOG.
        fallback:     Value to return if no tier resolves.

    Returns:
        (value, scope) where scope is 'user' | 'tenant' | 'system' | 'fallback'
    """
    from core.setting_catalog import SETTING_CATALOG  # avoid circular import

    catalog_entry = SETTING_CATALOG.get(setting_key)
    if catalog_entry is None:
        return fallback, "fallback"

    allows_user_override = catalog_entry.get("allows_user_override", False)

    if allows_user_override:
        user_override = db.exec(
            select(UserSettingOverride)
            .where(UserSettingOverride.tenant_id == tenant_id)
            .where(UserSettingOverride.user_id == user_id)
            .where(UserSettingOverride.setting_key == setting_key)
        ).first()

        if user_override is not None:
            return user_override.value, "user"

    return get_effective_setting(db, tenant_id, setting_key, fallback)


def setting_allows_user_override_for_tenant(
    db: Session,
    tenant_id: UUID,
    setting_key: str,
) -> bool:
    """
    Returns True if the tenant allows per-user overrides for this setting.

    Checks:
    1. catalog entry has allows_user_override=True
    2. No tenant-level disable (currently: catalog flag is definitive; per-setting
       meta-toggles like voice_persona_tone_user_override_allowed are handled in B12)

    Args:
        db:           Active SQLModel session.
        tenant_id:    Tenant whose policy to check.
        setting_key:  Setting key to check.

    Returns:
        bool — True if user overrides are allowed
    """
    from core.setting_catalog import SETTING_CATALOG

    entry = SETTING_CATALOG.get(setting_key)
    if entry is None:
        return False
    return bool(entry.get("allows_user_override", False))
```

---

### Module 2 — `core/system_defaults.py` (NEW — established in A53)

**File path**: `backend/core/system_defaults.py`

```python
"""
System-level default values for all tenant settings.

These are the "Tier 2" values in the three-tier resolver (user → tenant → system → fallback).
When a tenant has not set a value (column is NULL or uses the NOT NULL server_default),
the resolver falls back to these constants.

Distinct from server_default in TenantSettings (which is the DB-level default for new tenants).
server_defaults are written to the row at tenant creation; SYSTEM_DEFAULTS here serve
as the authoritative reference for UI display and resolver logic.
"""

SYSTEM_DEFAULTS: dict[str, any] = {
    # Quote & approval settings
    "default_quote_validity_days": 30,
    "default_invoice_terms_days": 0,
    "require_approval_for_tech_quotes": True,
    "max_discount_pct_owner": 15.0,

    # Labor & cost settings
    "default_labor_rate_cents": 8500,
    "default_billable_labor_rate_cents": 15000,

    # ETC variance thresholds
    "etc_variance_owner_notify_pct": 50,
    "etc_variance_note_required_pct": 10,

    # Profitability margin settings
    "margin_target_pct": 20,
    "margin_bucket_boundaries": [10, 20, 30],
    "report_chart_threshold": 8,

    # Calendar conflict auto-expiry
    "calendar_conflict_auto_expire_days": 30,
    "calendar_conflict_pre_warning_days": 7,
    "calendar_conflict_auto_expire_enabled": True,

    # QuickBooks conflict auto-expiry
    "qb_auto_expire_days": 60,
    "qb_pre_warning_days": 14,
    # Per-entity expiry defaults are OFF — not listed here; fallback is False
    # qb_auto_expire_*_enabled defaults are False (hardcoded fallback in calling code)

    # Photo upload & retention
    "photo_upload_wifi_only": True,
    "photo_local_retention_days": 7,

    # Offline operations
    "offline_hard_limit_hours": 72,
    "voice_offline_audio_storage_limit_mb": 500,

    # Background sync
    "background_sync_enabled": True,
    "background_sync_wifi_only": False,
    "background_sync_battery_floor_pct": 20,
    "background_sync_push_interval_minutes": 5,

    # Sync indicator threshold (used in B10 / §16.13)
    "tenant_sync_indicator_pending_amber_threshold": 5,
}
```

---

### Module 3 — `core/setting_catalog.py` (NEW — established in A52)

**File path**: `backend/core/setting_catalog.py`

```python
"""
Static settings catalog registry for Pilot for Trades.

Each entry defines the metadata for one configurable setting.
The GET /api/v1/settings/catalog endpoint renders this registry + resolves
current effective values from the DB.

No DB table — this is authoritative static code. Add a new entry here when
a new setting is introduced (alongside the TenantSettings column migration).

Key conventions:
- 'key' must match the TenantSettings column name exactly for tenant-level settings
- 'allows_user_override' = True means user_setting_override table is consulted in tier 1
- 'requires_role' = None means any authenticated role can read the setting
- 'revertible' = True means DELETE /api/v1/settings/{key} is allowed
"""
from typing import Any

SettingCatalogEntry = dict[str, Any]

SETTING_CATALOG: dict[str, SettingCatalogEntry] = {
    # -----------------------------------------------------------------
    # QUOTE & APPROVAL
    # -----------------------------------------------------------------
    "require_approval_for_tech_quotes": {
        "label": "Require approval for tech quotes",
        "description": "When ON, quotes created by technicians require owner/accountant approval before sending.",
        "sub_surface_path": "/settings/quotes/approval",
        "data_type": "boolean",
        "validation_rules": {},
        "system_default": True,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "max_discount_pct_owner": {
        "label": "Maximum discount percentage",
        "description": "Maximum discount an owner/accountant can apply to a quote before requiring explicit override.",
        "sub_surface_path": "/settings/quotes/discounts",
        "data_type": "decimal",
        "validation_rules": {"min": 0, "max": 100},
        "system_default": 15.0,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "default_quote_validity_days": {
        "label": "Default quote validity (days)",
        "description": "How many days a new quote is valid before expiring.",
        "sub_surface_path": "/settings/quotes/defaults",
        "data_type": "integer",
        "validation_rules": {"min": 1, "max": 365},
        "system_default": 30,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "default_invoice_terms_days": {
        "label": "Default invoice terms (days)",
        "description": "Default net-payment terms on new invoices (0 = due on receipt).",
        "sub_surface_path": "/settings/invoices/defaults",
        "data_type": "integer",
        "validation_rules": {"min": 0, "max": 120},
        "system_default": 0,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    # -----------------------------------------------------------------
    # LABOR & COST
    # -----------------------------------------------------------------
    "default_labor_rate_cents": {
        "label": "Default labor rate (cents/hour)",
        "description": "Default internal cost rate for labor hours.",
        "sub_surface_path": "/settings/catalog/labor",
        "data_type": "integer",
        "validation_rules": {"min": 100},
        "system_default": 8500,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "default_billable_labor_rate_cents": {
        "label": "Default billable labor rate (cents/hour)",
        "description": "Default customer-facing billable rate for labor.",
        "sub_surface_path": "/settings/catalog/labor",
        "data_type": "integer",
        "validation_rules": {"min": 100},
        "system_default": 15000,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    # -----------------------------------------------------------------
    # ETC VARIANCE
    # -----------------------------------------------------------------
    "etc_variance_owner_notify_pct": {
        "label": "ETC variance owner notify threshold (%)",
        "description": "Notify owner when projected cost exceeds quoted by this percentage.",
        "sub_surface_path": "/settings/jobs/etc",
        "data_type": "integer",
        "validation_rules": {"min": 1, "max": 500},
        "system_default": 50,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "etc_variance_note_required_pct": {
        "label": "ETC variance note required threshold (%)",
        "description": "Require tech to provide a note when ETC increases projected hours by this percentage.",
        "sub_surface_path": "/settings/jobs/etc",
        "data_type": "integer",
        "validation_rules": {"min": 1, "max": 200},
        "system_default": 10,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    # -----------------------------------------------------------------
    # PROFITABILITY
    # -----------------------------------------------------------------
    "margin_target_pct": {
        "label": "Margin target (%)",
        "description": "Jobs below this margin % receive a visual indicator on the profitability dashboard.",
        "sub_surface_path": "/settings/profitability",
        "data_type": "integer",
        "validation_rules": {"min": 0, "max": 100},
        "system_default": 20,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "margin_bucket_boundaries": {
        "label": "Margin bucket boundaries",
        "description": "Three ascending integers defining four margin buckets for the profitability report chart.",
        "sub_surface_path": "/settings/profitability",
        "data_type": "jsonb_int_array",
        "validation_rules": {"length": 3, "monotonic_ascending": True, "min": 0, "max": 100},
        "system_default": [10, 20, 30],
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    # -----------------------------------------------------------------
    # CALENDAR CONFLICT AUTO-EXPIRY
    # -----------------------------------------------------------------
    "calendar_conflict_auto_expire_enabled": {
        "label": "Calendar conflict auto-expiry enabled",
        "description": "When ON, unresolved calendar sync conflicts are auto-resolved after the expiry period.",
        "sub_surface_path": "/settings/integrations/calendar",
        "data_type": "boolean",
        "validation_rules": {},
        "system_default": True,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "calendar_conflict_auto_expire_days": {
        "label": "Calendar conflict auto-expiry period (days)",
        "description": "Days before an unresolved calendar conflict is auto-accepted (using Pilot version). NULL inherits system default of 30 days.",
        "sub_surface_path": "/settings/integrations/calendar",
        "data_type": "integer",
        "validation_rules": {"min": 1, "max": 365},
        "system_default": 30,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "calendar_conflict_pre_warning_days": {
        "label": "Calendar conflict pre-warning (days)",
        "description": "Days before auto-expiry to send a pre-warning notification. Must be < auto_expire_days.",
        "sub_surface_path": "/settings/integrations/calendar",
        "data_type": "integer",
        "validation_rules": {"min": 1, "max": 30, "cross_field": {"less_than": "calendar_conflict_auto_expire_days"}},
        "system_default": 7,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    # -----------------------------------------------------------------
    # QUICKBOOKS CONFLICT AUTO-EXPIRY
    # -----------------------------------------------------------------
    "qb_auto_expire_days": {
        "label": "QuickBooks conflict auto-expiry period (days)",
        "description": "Days before a QB sync conflict is auto-resolved (when per-entity expiry is ON). NULL inherits system default of 60 days.",
        "sub_surface_path": "/settings/integrations/quickbooks",
        "data_type": "integer",
        "validation_rules": {"min": 1, "max": 365},
        "system_default": 60,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "qb_pre_warning_days": {
        "label": "QuickBooks conflict pre-warning (days)",
        "description": "Days before QB conflict auto-expiry to send a pre-warning. Must be < qb_auto_expire_days.",
        "sub_surface_path": "/settings/integrations/quickbooks",
        "data_type": "integer",
        "validation_rules": {"min": 1, "max": 60, "cross_field": {"less_than": "qb_auto_expire_days"}},
        "system_default": 14,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    # QB per-entity enable+direction pairs — all revertible to False/None
    "qb_auto_expire_customer_enabled": {
        "label": "QB customer conflict auto-expiry enabled",
        "description": "When ON, QB customer conflicts auto-resolve after the expiry period.",
        "sub_surface_path": "/settings/integrations/quickbooks",
        "data_type": "boolean",
        "validation_rules": {"save_on_group_complete": ["qb_auto_expire_customer_direction"]},
        "system_default": False,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    # (additional qb_auto_expire_* entries follow the same pattern — omitted for brevity)
    # -----------------------------------------------------------------
    # PHOTO UPLOAD & RETENTION
    # -----------------------------------------------------------------
    "photo_upload_wifi_only": {
        "label": "Upload photos on WiFi only",
        "description": "When ON, photo uploads are deferred until a WiFi connection is available.",
        "sub_surface_path": "/settings/mobile/photos",
        "data_type": "boolean",
        "validation_rules": {},
        "system_default": True,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "photo_local_retention_days": {
        "label": "Photo local retention (days)",
        "description": "Days a synced photo remains on the device before auto-purge.",
        "sub_surface_path": "/settings/mobile/photos",
        "data_type": "integer",
        "validation_rules": {"min": 1, "max": 30},
        "system_default": 7,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    # -----------------------------------------------------------------
    # OFFLINE OPERATIONS
    # -----------------------------------------------------------------
    "offline_hard_limit_hours": {
        "label": "Offline hard limit (hours)",
        "description": "Hours before the app blocks new offline captures. NULL = unlimited.",
        "sub_surface_path": "/settings/mobile/offline",
        "data_type": "integer",
        "validation_rules": {"min": 1, "nullable": True},
        "system_default": 72,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "voice_offline_audio_storage_limit_mb": {
        "label": "Voice audio offline storage limit (MB)",
        "description": "Maximum on-device storage for offline-captured voice audio.",
        "sub_surface_path": "/settings/mobile/offline",
        "data_type": "integer",
        "validation_rules": {"min": 50, "max": 2000},
        "system_default": 500,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    # -----------------------------------------------------------------
    # BACKGROUND SYNC
    # -----------------------------------------------------------------
    "background_sync_enabled": {
        "label": "Background sync enabled",
        "description": "When ON, the server sends silent pushes to trigger background sync on mobile devices.",
        "sub_surface_path": "/settings/mobile/background-sync",
        "data_type": "boolean",
        "validation_rules": {},
        "system_default": True,
        "requires_role": "owner",
        "allows_user_override": True,   # User can disable on their own device (A55)
        "revertible": True,
    },
    "background_sync_wifi_only": {
        "label": "Background sync on WiFi only",
        "description": "When ON, background sync only runs over WiFi (saves mobile data).",
        "sub_surface_path": "/settings/mobile/background-sync",
        "data_type": "boolean",
        "validation_rules": {},
        "system_default": False,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "background_sync_battery_floor_pct": {
        "label": "Background sync battery floor (%)",
        "description": "Background sync will not run if battery is below this percentage.",
        "sub_surface_path": "/settings/mobile/background-sync",
        "data_type": "integer",
        "validation_rules": {"min": 5, "max": 50},
        "system_default": 20,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
    "background_sync_push_interval_minutes": {
        "label": "Background sync push interval (minutes)",
        "description": "How often the server sends a silent push to trigger background sync. NULL inherits system default of 5 minutes.",
        "sub_surface_path": "/settings/mobile/background-sync",
        "data_type": "integer",
        "validation_rules": {"min": 1, "max": 60},
        "system_default": 5,
        "requires_role": "owner",
        "allows_user_override": False,
        "revertible": True,
    },
}
```

---

### Module 4 — `app/models/settings.py` (NEW — established in A53)

**File path**: `backend/app/models/settings.py`

Contains the `UserSettingOverride` SQLModel for the new `user_setting_override` table.

```python
import uuid
from typing import Any, Dict, Optional
from pydantic import AwareDatetime
from sqlalchemy import DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import StandardAuditMixin


class UserSettingOverride(StandardAuditMixin, SQLModel, table=True):
    """
    User-level setting override — Tier 1 of the three-tier resolver.
    One row per (tenant_id, user_id, setting_key).

    Established in B9/A53. Used by services/setting_resolver.py.
    """
    __tablename__ = "user_setting_override"

    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", primary_key=True, nullable=False)
    user_id: uuid.UUID = Field(
        primary_key=True,
        nullable=False,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="CASCADE")),
    )
    setting_key: str = Field(primary_key=True, sa_column=Column(Text, nullable=False))
    value: Dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False)
    )

    # Phase 6.0.1: Override audit FK constraints
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
```

---

### Module 5 — `api/routes/settings.py` (NEW — established in A52/A53/A54/A55)

**File path**: `backend/api/routes/settings.py`

New route file. Register in `backend/app/main.py` with:
```python
from api.routes import settings as settings_router
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
```

All four items (A52, A53, A54, A55) live in this single route file. The dual-endpoint architecture (authenticated + `/test`) applies per `pilot-python-engineer-methods.md §8.2`.

---

### RBAC Permissions to Add (migration seeded in A53)

The following permissions must be seeded in the B9 migration (not in the original role seed migration):

| Permission String | Assigned Roles | Purpose |
|:---|:---|:---|
| `settings.read` | All roles (`"*"` covers owner; explicit for tech, office_staff, accountant) | Read catalog and effective values |
| `settings.tenant.write` | owner, accountant | Write tenant-level settings (A54) |
| `settings.user_override.write` | All roles | Write own user overrides (A55) |

---

## F. Open Questions Resolved

### Q1 — Row-per-key vs. columnar `tenant_settings` for tenant write endpoints

**Question**: The `pilot-python-engineer-methods.md §21` template imports from `app.models.settings` with a `TenantSetting` class implying a new row-per-key table. But the live DB has `tenant_settings` (flat 38-column table). Which design does B9 use?

**Decision**: **Use the existing `tenant_settings` columnar table for tenant-level settings.** Do NOT create a new `tenant_setting` row-per-key table.

**Rationale**:
1. The live DB (confirmed via MCP query) has `tenant_settings` with 38 typed columns and proper defaults — a migration to row-per-key would require destructive conversion.
2. All consuming code in B6, B7b, B8 (calendar, offline, QB settings) already reads directly from `TenantSettings` model fields.
3. The `mobile_background_sync.py::TODO_B9_RESOLVER` comment shows the expected pattern is `getattr(tenant_settings, key, None)` — confirming the columnar approach.
4. A row-per-key pattern's flexibility is not needed at this scale (settings catalog is static code, not dynamic).

**Impact**: `app.models.settings` contains only `UserSettingOverride` (not a `TenantSetting` model). `get_effective_setting()` uses `getattr()` against `TenantSettings`.

---

### Q2 — Where do system defaults live (DB table vs. Python constants)?

**Question**: The arch doc §16.5 references `platform_setting` as a DB table. The live DB has no such table. Where do system defaults live?

**Decision**: **System defaults are Python constants in `core/system_defaults.py`.** No DB table.

**Rationale**:
1. System defaults change only on code deploy (they're platform design decisions, not runtime config).
2. A DB table for system defaults adds operational complexity (seeding, migration syncing) with no runtime benefit.
3. The existing `TenantSettings` server_defaults already encode the same values at the DB level for new tenants; `SYSTEM_DEFAULTS` mirrors these for the resolver's tier-2 lookup.
4. The `platform_setting` table mentioned in arch doc §16.5 is deferred to Phase 2 (when operator UI needs runtime-configurable platform-level settings).

---

### Q3 — Where does the settings catalog live (DB table vs. Python registry)?

**Question**: A52 specifies `GET /api/v1/settings/catalog` returns a catalog. Should it be DB-stored or code-stored?

**Decision**: **Static Python registry in `core/setting_catalog.py`.** No DB table.

**Rationale**:
1. The catalog is a design-time artifact that changes only when new settings are added (accompanied by a migration).
2. A DB-based catalog would require a migration and seeding script for every new setting — twice the work.
3. The Python registry is version-controlled alongside the code change that adds the setting — consistency guaranteed.
4. A DB-backed catalog is deferred to Phase 2 if the operator admin UI needs runtime catalog edits.

---

### Q4 — How does `DELETE /api/v1/settings/{key}` handle non-nullable columns?

**Question**: `tenant_settings` has 22+ NOT NULL columns with server_defaults. If a tenant "reverts" one to the system default, we can't just SET NULL — there's a NOT NULL constraint.

**Decision**: For non-nullable columns, the DELETE endpoint **sets the column to the system default value from `SYSTEM_DEFAULTS`** (not NULL). For nullable columns (e.g., `calendar_conflict_auto_expire_days`, `qb_auto_expire_days`), it sets to NULL. The catalog entry's `revertible: True/False` flag indicates whether the endpoint accepts DELETE for that key.

**Implementation**: In `DELETE /api/v1/settings/{key}`, the handler:
1. Looks up `SYSTEM_DEFAULTS.get(key)` to get the revert value
2. For nullable columns (e.g., `calendar_conflict_auto_expire_days`): calls `setattr(settings_row, key, None)` → DB resolves effective value from system default at read time via the resolver
3. For NOT NULL columns (e.g., `etc_variance_owner_notify_pct`): calls `setattr(settings_row, key, SYSTEM_DEFAULTS[key])` → DB constraint satisfied; response `scope` returns `'system'`
4. Commits — the NOT NULL constraint is never violated because `SYSTEM_DEFAULTS` holds a valid value for every non-nullable key

The distinction between "set NULL" and "set to system default value" is transparent to the caller — both result in `scope: 'system'` in the response.

---

### Q5 — Should the A52 catalog cache use Redis or in-process cache?

**Question**: The catalog response is tenant+role-scoped and must be invalidated on settings write. Should the cache be in-process (fast, no Redis latency) or in Redis (shared across ECS task replicas)?

**Decision**: **Redis cache** keyed as `settings_catalog:{tenant_id}:{role_code}` with a 1-hour TTL safety net.

**Rationale**: In-process cache is unsafe in ECS Fargate multi-task deployments — if task A writes a setting, task B's in-process cache is stale until its next request. Redis is already in the stack (used for Celery broker and rate limiting) at zero additional infrastructure cost.

**Invalidation**: `PUT /api/v1/settings/{key}` and `DELETE /api/v1/settings/{key}` call `redis_client.delete(f"settings_catalog:{tenant_id}:*")` immediately after the DB commit (pattern-delete across all role-code variants). A55 user-override writes invalidate only `settings_catalog:{tenant_id}:{user_id}:*` for the writing user's role-filtered key.

---

### Q6 — Do save-on-group-complete QB per-entity settings need a special endpoint?

**Question**: `qb_auto_expire_customer_enabled` and `qb_auto_expire_customer_direction` must be saved atomically (per Tier 1 #2 Decision 9). Should a special group-write endpoint be added?

**Decision**: **Add `PUT /api/v1/settings/bulk`** — accepts `{ "values": { key: value, ... } }` and writes multiple settings in a single DB commit. The single-key `PUT /api/v1/settings/{key}` remains for simple writes; `PUT /api/v1/settings/bulk` is the surface for group-complete patterns.

When the catalog entry for `qb_auto_expire_customer_enabled` includes `"save_on_group_complete": ["qb_auto_expire_customer_direction"]`, a single-key PUT that sets `enabled: true` without providing the direction field returns `422` with a message directing the caller to use `/bulk` with both keys. The bulk endpoint validates all keys atomically — partial writes within a group are rejected.

---

### Q7 — Does the `require_approval_for_tech_quotes` OFF toggle with pending quotes block or warn?

**Question**: When an owner disables `require_approval_for_tech_quotes` with N pending-approval quotes, the spec says include `pending_quote_count` in the response. Does the write succeed or block?

**Decision**: **The write succeeds (200).** The `pending_quote_count` field is informational only — it signals to the frontend to surface a post-write confirmation dialog ("You have 3 quotes awaiting approval. They will remain in pending state and must be manually approved or rejected."). The backend does not block the setting change.

**Rationale**: The owner made a deliberate policy decision; blocking it would be paternalistic. The pending quotes are surfaced so the owner knows to clean them up. Quotes in `submitted_for_approval` state can still be approved or rejected via existing `POST /api/v1/quotes/{id}/approve` and `POST /api/v1/quotes/{id}/reject` endpoints regardless of the setting toggle.

---

## G. External Dependency Status

### B9 — No External Dependencies

B9 is a pure internal infrastructure batch. All four items (A53, A52, A54, A55) operate exclusively against:
- The existing PostgreSQL database (`tenant_settings` table + new `user_setting_override` table)
- Redis (for settings catalog caching — already in stack)
- Python in-process code (static catalog and defaults registries)

**No Stripe, Telnyx, SendGrid, OpenAI, Cognito write-path, or any other external API is called from any B9 endpoint.**

| Item | External Dependency | Mock Strategy | Tom Action Required |
|:---|:---|:---|:---|
| A53 — Three-tier resolver | None | N/A | None |
| A52 — Settings catalog | Redis (read-through cache) | Redis available in local Docker stack (`pilot_redis`); no mock needed | None |
| A54 — Tenant write endpoints | None | N/A | None |
| A55 — Per-user override writes | None | N/A | None |
| `PUT /api/v1/settings/bulk` | None | N/A | None |

---

### B9 Has No External Pre-Conditions

Unlike B11 (Telnyx 10DLC — 4–6 week approval lead time) or B14 (Stripe account + Products/Prices configuration), B9 has zero external pre-conditions. It can be started and completed immediately in parallel with or immediately after B8.

---

### Downstream Batches Unblocked by B9 — External Dependency Notes

B9's three-tier resolver is a prerequisite for batches that DO have external dependencies. Completing B9 opens the critical path to:

| Downstream Batch | External Dependency Now Unblocked | Lead Time | Tom Action |
|:---|:---|:---|:---|
| **B10** — Notification System | None external; B9 resolver used for preference defaults and per-user channels | None | Start immediately after B9 |
| **B12** — Voice Persona Tone | None external; `voice_persona_tone` user override reads `user_setting_override` | None | Start immediately after B9 |
| **B13** — Account Security & MFA | **Cognito MFA API** (TOTP, SMS OTP, Email OTP method types) | ~1–2 weeks for Cognito MFA config in AWS Console; no external vendor approval needed | Tom must enable MFA methods in the Cognito User Pool settings (AWS Console) before A69 enrollment flows work in any environment beyond `dev` |
| **B14** — Onboarding & Subscription | **Stripe** (Products, Prices, webhook endpoint, test-mode keys) | ~1 week setup; no approval needed for test mode; production requires Stripe account verification | Tom must create Stripe Products/Prices for each subscription tier and configure `STRIPE_WEBHOOK_SECRET` in `backend/.env` before A76 (Stripe integration) is functional; mock strategy: `MockStripeClient` wrapping `stripe-mock` container in dev |

---

### Mock Strategy for Downstream External Dependencies

Per `pilot-python-engineer-methods.md §1.5 Rule 2`, all external-dependency-blocked items use a mock implementation until the production credential is available:

**Cognito MFA (B13/A69)**:
- `MockCognitoMfaClient` wrapping Cognito SDK calls — returns canned challenge IDs and accepts any 6-digit code as valid in dev/test environments
- `COGNITO_MFA_MOCK=true` env var activates the mock
- Real Cognito MFA calls activate when `ENVIRONMENT=staging` or `ENVIRONMENT=production`

**Stripe (B14/A76)**:
- `stripe-mock` Docker container (official Stripe mock server) added to `docker-compose.yml` at `port 12111`
- `STRIPE_API_BASE=http://localhost:12111` overrides real Stripe endpoint in dev
- `MockStripeWebhookClient` for the webhook handler test path (injects test events directly without real HTTP)
- Tom must supply real `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, and `STRIPE_WEBHOOK_SECRET` for staging/production

---

## Appendix — `db_models_map.md` Update Required After B9

After the Python engineer completes A53, `backend/db_models_map.md` must be updated to add:

```markdown
### `models/settings.py`
- UserSettingOverride
```

And `backend/app_model_imports.md` must include:

```python
from app.models.settings import UserSettingOverride
```

This is part of A53's Definition of Done checklist (per `pilot-python-engineer-methods.md §16.5`).

---

## Appendix — Golden Master JSON Update Required After B9

After running the B9 migration (`phase_fe_1_batch_b9_user_setting_override`), update `dev-docs/db-design/pilot-db-schema-v2.6h.json` with the `user_setting_override` table entry following the golden template format in `pilot-python-engineer-methods.md §16.3`:

```json
"user_setting_override": {
  "comment": "Per-user setting overrides — Tier 1 of the three-tier settings resolver (B9/A53). One row per (tenant_id, user_id, setting_key). Consumed by services/setting_resolver.py.",
  "columns": {
    "tenant_id": { "type": "uuid", "nullable": false },
    "user_id": { "type": "uuid", "nullable": false },
    "setting_key": { "type": "text", "nullable": false },
    "value": { "type": "jsonb", "nullable": false },
    "created_at": { "type": "timestamp with time zone", "nullable": false },
    "updated_at": { "type": "timestamp with time zone", "nullable": false },
    "created_by": { "type": "uuid", "nullable": true },
    "updated_by": { "type": "uuid", "nullable": true }
  },
  "primary_key": ["tenant_id", "user_id", "setting_key"],
  "unique": [],
  "indexes": [
    {
      "name": "ix_user_setting_override_tenant_user",
      "definition": "CREATE INDEX ix_user_setting_override_tenant_user ON public.user_setting_override USING btree (tenant_id, user_id)"
    },
    {
      "name": "ix_user_setting_override_tenant_key",
      "definition": "CREATE INDEX ix_user_setting_override_tenant_key ON public.user_setting_override USING btree (tenant_id, setting_key)"
    }
  ],
  "check_constraints": [],
  "foreign_keys": [
    {
      "name": "fk_user_setting_override_tenant",
      "columns": ["tenant_id"],
      "ref_table": "tenant",
      "ref_columns": ["id"],
      "on_delete": "RESTRICT"
    },
    {
      "name": "fk_user_setting_override_user",
      "columns": ["user_id"],
      "ref_table": "user",
      "ref_columns": ["id"],
      "on_delete": "CASCADE"
    },
    {
      "name": "fk_user_setting_override_created_by",
      "columns": ["created_by"],
      "ref_table": "user",
      "ref_columns": ["id"],
      "on_delete": "RESTRICT"
    },
    {
      "name": "fk_user_setting_override_updated_by",
      "columns": ["updated_by"],
      "ref_table": "user",
      "ref_columns": ["id"],
      "on_delete": "RESTRICT"
    }
  ],
  "triggers": [
    {
      "name": "audit_user_setting_override_changes",
      "definition": "CREATE TRIGGER audit_user_setting_override_changes AFTER INSERT OR DELETE OR UPDATE ON public.user_setting_override FOR EACH ROW EXECUTE FUNCTION audit.log_changes()"
    },
    {
      "name": "trg_user_setting_override_guard_created_immutable",
      "definition": "CREATE TRIGGER trg_user_setting_override_guard_created_immutable BEFORE UPDATE ON public.user_setting_override FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()"
    },
    {
      "name": "trg_user_setting_override_set_updated_at",
      "definition": "CREATE TRIGGER trg_user_setting_override_set_updated_at BEFORE UPDATE ON public.user_setting_override FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()"
    }
  ]
}
```

After updating the JSON, run `python schema_diff.py --group-by environment` from `dev-docs/db-design/` and confirm **zero discrepancies** before marking B9 complete.