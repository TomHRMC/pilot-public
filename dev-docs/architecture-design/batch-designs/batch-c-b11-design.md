# C-B11 — Operator Cohort Dashboard + Silent Extension Control + Cohort Close

**Batch**: C-B11
**Mode**: Pilot Python Engineer (Part A) → Pilot Web UI Designer → Pilot React Engineer (Part B)
**Prerequisite**: C-B4 ✅ (Stripe subscription lifecycle + webhook handlers)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §8 (Operator Tooling), §4.4 (Silent Extension), §4.3 (Cohort Close)
**Status**: Design — Tom approved Path A (standalone page, no platform shell, no impersonation) 2026-08-06
**Date**: August 6, 2026

> **Scope decision (Tom, 2026-08-06)**: **Path A — Minimum viable.** C-B11 Part B builds a standalone `/operator/cohort` page with its own minimal layout (no tenant shell, no nav sidebar). No tenant impersonation — deferred to a future **C-B15 (Platform Shell + Tenant Impersonation)** batch. The platform user login flow (redirect to `/operator/cohort` after auth) is handled by a new `GET /api/v1/auth/me` endpoint that returns the user type (platform vs tenant). This endpoint is included in C-B11 Part A.

---

## Overview

C-B11 builds the Pilot operator's Charter cohort management dashboard — a platform-level (not tenant-scoped) screen that shows all Charter members in a single table with tripwire alerts, and provides three operator actions:

1. **Cohort Dashboard** — one screen, up to 12 rows (Charter cap), showing each member's status, free-period countdown, Stripe status, 10DLC status, customer/invoice counts, days since last job (the activation tripwire), and last operator contact.
2. **Silent Extension Control** — inline action to extend a member's free period by setting `tenant_tier_override.override_free_period_ends_at` + `override_reason`, then calling `stripe.Subscription.modify(trial_end=...)`. Rejects if the Stripe subscription is not in `trialing` status. **No customer notification** (D16).
3. **Cohort Close** — single operator action that archives `price_charter_monthly` in Stripe (`active=false`), confirms `subscription_tier.charter.is_active = false`, and activates `trial`/`starter`/`teams` tiers. Manual — Tom controls timing.

This is a **mixed batch** (Python + React). Part A (Python Engineer) builds the platform auth dependency, the cohort data aggregation service, 3 API endpoints, and the Stripe extension/close service functions. Part B (React Engineer) builds the operator dashboard page — but only after a UI design spec is authored by the pilot-web-ui-designer and Tom-approved.

### Key Design Decision: Platform-Level Auth

The existing `get_current_user()` dependency (in `core/auth.py`) is **tenant-scoped** — it requires a `tenant_user` row and raises 403 if none exists. Platform users (`is_platform_user=True`, `platform_role_code` set) have **no tenant membership** (enforced by a DB trigger). They cannot authenticate via `get_current_user()`.

C-B11 introduces a new **`get_platform_user()`** dependency in `core/auth.py` that:
1. Validates the Cognito JWT (reuses `verify_cognito_jwt`)
2. Looks up the user by email
3. Checks `is_platform_user=True` + `platform_role_code IS NOT NULL`
4. Loads the `platform_role.permissions` JSON (structure: `{write: [...], read_all: bool, ...}`)
5. Returns a `PlatformUser` context object (no `tenant_id` — platform-level access)

The cohort dashboard endpoints use `get_platform_user()` instead of `get_current_user()`. Permission check: `platform_role.permissions.read_all == true` (the `owner` and `support` roles have this; `accountant` does too). Write actions (extension, close) require `platform_role.permissions.write` to include `"tenants"` or `"billing"` (the `owner` role has both; `support` has `"tenants"` + `"billing"`).

---

## A. Input Read Summary

| Input | Source | Key findings |
|---|---|---|
| Spec §8.1 — Cohort Dashboard | `pilot-tech-impl-spec-v1.md` §8.1 | One screen, 12 rows. Columns: Member #/business name, Days remaining (`free_period_ends_at`), Stripe status (webhook-synced: trialing/active/paused), Payment method on file (Stripe customer), 10DLC status (`tenant_messaging_registration.status`), Real customers/real invoices (counts — Stage 1 gate D33), Days since last job created (`job.created_at` — the activation tripwire), Last contact (operator-logged). Two visual alerts: Red = days_since_last_job > 7; Amber = free_period_ends_at within 14 days. |
| Spec §8.2 — Silent Extension | Same, §8.2 | Inline on the dashboard. Sets `override_free_period_ends_at` + required `override_reason`, calls Stripe, writes audit. Rejects if subscription status is not `trialing`. No customer notification (D16). |
| Spec §4.4 — Override mechanism | Same, §4.4 | Operator sets `override_free_period_ends_at` + `override_reason` → service recomputes `tenant.free_period_ends_at` → `stripe.Subscription.modify(sub_id, trial_end=<new_ts>)` → audit log entry → NO customer notification. Hard constraint: subscription must be `trialing`. |
| Spec §8.3 — Cohort Close | Same, §8.3 | Single operator action: archive `price_charter_monthly` in Stripe (`active=false`), confirm `subscription_tier.charter.is_active = false`, activate `trial`/`starter`/`teams`. Manual, not automatic — Tom controls timing. |
| Spec §4.3 — Cohort Cap | Same, §4.3 | `signup_cap` enforcement: `SELECT count(*) ... FOR UPDATE` on tier row, assign `charter_member_number = count + 1`. If `count + 1 >= signup_cap`, set `is_active = false` in same transaction. |
| Live DB — `user` table | MCP (this session) | Has `is_platform_user` (BOOLEAN, NOT NULL, default false) + `platform_role_code` (VARCHAR, nullable, FK to `platform_role.code`). Platform users have NO `tenant_user` row (DB trigger prevents it). |
| Live DB — `platform_role` table | MCP (this session) | 3 rows: `owner` (read_all=true, write=[tenants,users,suppliers,billing,jwks,plans,notifications], impersonate_tenant=true), `accountant` (read_all=true, write=[], manage_jwks=false), `support` (read_all=true, write=[tenants,users,billing,notifications], impersonate_tenant=true). All `is_active=true`. |
| Live DB — `tenant` table | MCP (this session) | Has `id`, `name`, `free_period_ends_at` (TIMESTAMPTZ, nullable), `charter_member_number` (INTEGER, nullable), `charter_eligible` (BOOLEAN, NOT NULL), `current_subscription_tier_id` (UUID, FK), `stripe_customer_id` (TEXT, nullable). |
| Live DB — `tenant_tier_override` table | MCP (this session) | 11 columns: `tenant_id` (PK), `override_tier_id`, `override_trial_length_days`, `override_reason` (NOT NULL), `set_by_operator_user_id` (NOT NULL), `set_at` (NOT NULL), `override_free_period_ends_at` (TIMESTAMPTZ, nullable), + 4 audit. |
| Live DB — `subscription` table | MCP (this session) | Has `psp_subscription_id` (VARCHAR, nullable), `psp_customer_id` (VARCHAR, nullable), `status_id` (UUID FK → `subscription_status`), `is_active` (BOOLEAN), `trial_ends_at` (TIMESTAMPTZ, nullable), `tenant_id` (UUID FK). |
| Live DB — `subscription_status` table | MCP (this session) | 6 rows: `active`, `canceled`, `past_due`, `paused`, `trialing`, `unpaid`. Each has `code`, `name`, `is_billing_active` (BOOLEAN). |
| Live DB — `subscription_tier` table | MCP (this session, C-B2) | Has `is_active` (BOOLEAN), `signup_cap` (INTEGER), `tier_name` (VARCHAR), `price_locked` (BOOLEAN). Charter tier: `is_active=true`, `signup_cap=12`. |
| Existing code — `get_current_user()` | `core/auth.py` | Tenant-scoped auth. Requires `tenant_user` row (line 244: raises 403 if none). Platform users cannot use this. C-B11 adds `get_platform_user()`. |
| Existing code — `require_permission()` | `core/permissions.py` | Tenant-scoped permission decorator. Uses `AuthenticatedUser.permissions` (list of strings from `tenant_user_role`). Not applicable to platform users — they use `platform_role.permissions` JSON (different structure). |
| Existing code — `stripe_subscriptions.py` | `backend/services/stripe_subscriptions.py` | `_get_stripe_client()` singleton. `create_charter_subscription()` at line 531. `resume_subscription()` at line 615. C-B11 adds `extend_free_period()` + `close_cohort()`. |
| Existing code — `stripe_config.py` | `backend/core/stripe_config.py` | `get_stripe_ids()` returns dict with `products` + `meters` + `prices`. `price_charter_monthly` key holds the Charter price ID. |
| mvp-arch §16 | `mvp-arch.md` §16 | Platform patterns: optimistic UI (§16.6), always-preview-before-send (§16.7). The cohort dashboard is operator-internal — these patterns apply to the extension action (preview the new date before applying). |

---

## B. Migration Plan

### B.1 — DB Changes

**No migration needed.** All required columns already exist:
- `tenant.free_period_ends_at` — from C-B2
- `tenant.charter_member_number` — from C-B2
- `tenant.charter_eligible` — from C-B2
- `tenant_tier_override.override_free_period_ends_at` — from C-B2
- `tenant_tier_override.override_reason` — from C-B2
- `tenant_tier_override.set_by_operator_user_id` — from C-B2
- `subscription_tier.is_active` — from C-B2
- `subscription_tier.signup_cap` — from C-B2

**No new table.** The cohort dashboard is a read-only aggregation query + 3 write actions that use existing tables.

### B.2 — MCP Verification Queries (pre-implementation)

```sql
-- 1. Verify tenant has Charter-related columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name IN ('free_period_ends_at', 'charter_member_number', 'charter_eligible', 'current_subscription_tier_id', 'stripe_customer_id')
ORDER BY ordinal_position;

-- 2. Verify tenant_tier_override has override_free_period_ends_at + override_reason + set_by_operator_user_id
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_tier_override'
ORDER BY ordinal_position;

-- 3. Verify subscription_tier has is_active + signup_cap
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
  AND column_name IN ('is_active', 'signup_cap', 'tier_name', 'price_locked')
ORDER BY ordinal_position;

-- 4. Verify subscription_status codes
SELECT code, name, is_billing_active FROM subscription_status ORDER BY code;

-- 5. Verify user table has is_platform_user + platform_role_code
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user'
  AND column_name IN ('is_platform_user', 'platform_role_code', 'is_active', 'email')
ORDER BY ordinal_position;

-- 6. Verify platform_role permissions structure
SELECT code, name, permissions, is_active FROM platform_role ORDER BY code;

-- 7. Verify job table has created_at + tenant_id for the tripwire query
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
  AND column_name IN ('id', 'tenant_id', 'created_at')
ORDER BY ordinal_position;
```

### B.3 — Pre-Implementation State

- `tenant`: has all Charter columns from C-B2
- `tenant_tier_override`: has `override_free_period_ends_at` + `override_reason` + `set_by_operator_user_id` from C-B2
- `subscription_tier`: Charter tier `is_active=true`, `signup_cap=12`
- `platform_role`: 3 rows (owner, accountant, support) with `permissions` JSON
- `user`: has `is_platform_user` + `platform_role_code` columns
- No existing platform-level auth dependency in `core/auth.py`

### B.4 — 3-Part NOT NULL Pattern

Not applicable — no new columns.

### B.5 — Audit Columns

Not applicable — no new table.

### B.6 — Seed Data Rollout

Not applicable — no new seed data. The `platform_role` rows already exist.

---

## C. Execution Order

| # | Task | Files | Description |
|---|---|---|---|
| 1 | Platform auth dependency | `backend/core/auth.py` | Add `PlatformUser` model + `get_platform_user()` dependency. Validates JWT, checks `is_platform_user=True`, loads `platform_role.permissions`. |
| 2 | Cohort data service | `backend/services/cohort_dashboard.py` (NEW) | `get_cohort_overview(db) -> list[CohortMember]` — aggregates tenant + subscription + messaging + job data for all Charter members. |
| 3 | Extension service | `backend/services/cohort_dashboard.py` | `extend_free_period(db, tenant_id, new_end_date, reason, operator_user_id) -> dict` — sets override, updates `tenant.free_period_ends_at`, calls Stripe `Subscription.modify(trial_end=...)`. |
| 4 | Cohort close service | `backend/services/cohort_dashboard.py` | `close_cohort(db, operator_user_id) -> dict` — archives `price_charter_monthly` in Stripe, sets `subscription_tier.is_active=false`, activates other tiers. |
| 5 | API routes | `backend/api/routes/cohort_dashboard.py` (NEW) | 3 endpoints: `GET /api/v1/operator/cohort`, `POST /api/v1/operator/cohort/{tenant_id}/extend`, `POST /api/v1/operator/cohort/close`. All use `get_platform_user()`. |
| 6 | Router registration | `backend/app/main.py` | Register `cohort_dashboard` router. |
| 7 | Schemas | `backend/api/schemas/cohort.py` (NEW) | `CohortMemberResponse`, `CohortOverviewResponse`, `ExtendFreePeriodRequest`, `ExtendFreePeriodResponse`, `CloseCohortResponse`. |
| 8 | OpenAPI regen | — | `python export_openapi_json.py` — 3 new endpoints. |
| 9 | Tests | `backend/tests/domains/platform_infrastructure/test_cb11_cohort_dashboard.py` (NEW) | Unit tests for service functions + endpoint tests. |
| 10 | Schema JSON | — | No schema changes — no new columns/tables. |

---

## D. New API Endpoints

### D.1 — `GET /api/v1/operator/cohort`

**Auth**: `get_platform_user()` (platform-level, not tenant-scoped)
**Permission**: `platform_role.permissions.read_all == true`
**Response**: `CohortOverviewResponse`

```json
{
  "cohort_tier_name": "Charter",
  "cohort_is_active": true,
  "signup_cap": 12,
  "members": [
    {
      "tenant_id": "uuid",
      "business_name": "Acme Electric",
      "charter_member_number": 1,
      "free_period_ends_at": "2026-11-04T00:00:00Z",
      "days_remaining": 90,
      "stripe_status": "trialing",
      "has_payment_method": false,
      "messaging_status": "not_started",
      "customer_count": 3,
      "invoice_count": 2,
      "days_since_last_job": 5,
      "last_contact": null,
      "alert_level": "none"
    }
  ]
}
```

**`alert_level`** computation:
- `"red"` — `days_since_last_job > 7` (activation tripwire)
- `"amber"` — `free_period_ends_at` within 14 days (extension window)
- `"red"` takes precedence over `"amber"` if both are true
- `"none"` — neither condition met

### D.2 — `POST /api/v1/operator/cohort/{tenant_id}/extend`

**Auth**: `get_platform_user()`
**Permission**: `platform_role.permissions.write` contains `"tenants"` or `"billing"`
**Request**: `ExtendFreePeriodRequest`

```json
{
  "new_free_period_ends_at": "2026-12-04T00:00:00Z",
  "override_reason": "Customer needs more time to evaluate — agreed verbally"
}
```

**Response**: `ExtendFreePeriodResponse`

```json
{
  "tenant_id": "uuid",
  "previous_free_period_ends_at": "2026-11-04T00:00:00Z",
  "new_free_period_ends_at": "2026-12-04T00:00:00Z",
  "stripe_subscription_id": "sub_...",
  "stripe_trial_end_updated": true
}
```

**Errors**:
- `409` — Stripe subscription is not in `trialing` status (cannot extend after pause). RFC 7807.
- `404` — Tenant not found or not a Charter member.
- `422` — `new_free_period_ends_at` is in the past or before the current `free_period_ends_at`.

### D.3 — `POST /api/v1/operator/cohort/close`

**Auth**: `get_platform_user()`
**Permission**: `platform_role.permissions.write` contains `"billing"` (owner only — `support` does not have `"plans"` but has `"billing"`)
**Request**: empty body
**Response**: `CloseCohortResponse`

```json
{
  "charter_price_archived": true,
  "charter_tier_deactivated": true,
  "activated_tiers": ["trial", "starter", "teams"]
}
```

**Errors**:
- `409` — Cohort already closed (`subscription_tier.charter.is_active` is already `false`).

### D.4 — `GET /api/v1/auth/me`

**Auth**: `get_current_user()` OR `get_platform_user()` — this endpoint works for both user types. It tries tenant auth first; if that fails with 403 (no tenant_user row), it falls back to platform auth.

**Response**: `AuthMeResponse`

```json
{
  "user_type": "platform",
  "user_id": "uuid",
  "email": "tom@pilotfortrades.com",
  "first_name": "Tom",
  "last_name": "Lang",
  "platform_role_code": "owner",
  "redirect_to": "/operator/cohort"
}
```

For a tenant user:
```json
{
  "user_type": "tenant",
  "user_id": "uuid",
  "email": "dev@pilot.local",
  "first_name": "Dev",
  "last_name": "User",
  "tenant_id": "uuid",
  "role_code": "owner",
  "redirect_to": "/dashboard"
}
```

**Purpose**: The frontend calls this immediately after Cognito authentication to determine:
1. Whether the user is a platform user or a tenant user
2. Where to redirect after login (`/operator/cohort` for platform, `/dashboard` for tenant)
3. What navigation to render (operator-only items for platform users)

**Implementation**: A single endpoint that attempts `get_current_user()` in a try/except, and on 403 falls back to `get_platform_user()`. Returns a discriminated union response. This avoids requiring the frontend to make two API calls.

---

## E. Pattern Reuse Decisions

| Pattern | Source | How it applies |
|---|---|---|
| **`_get_stripe_client()`** | C-B4 `stripe_subscriptions.py` | Reuse for `Subscription.modify()` (extension) + `Price.modify(active=false)` (close). |
| **`get_stripe_ids()`** | C-B4 `core/stripe_config.py` | Load `price_charter_monthly` ID for the cohort close action. |
| **`set_audit_context_sync()`** | Standard pattern | Called on all 3 endpoints (the operator user is the actor). |
| **RFC 7807 errors** | Standard pattern | All error responses use Problem Details format. |
| **Always-preview-before-send** (§16.7) | mvp-arch §16.7 | The extension action shows the new date + reason before the operator confirms. The React UI renders a confirmation modal. |
| **`safe_now_utc()`** | `core/datetime_utils` | Used for date computations (days_remaining, days_since_last_job). |

---

## F. Shared Module Interfaces

### F.1 — `core/auth.py` additions

```python
class PlatformUser(BaseModel):
    """Platform-level authenticated user (no tenant context).
    
    Created by get_platform_user() after validating JWT + checking is_platform_user.
    Has platform_role.permissions JSON for authorization checks.
    """
    model_config = {"arbitrary_types_allowed": True}
    user: User
    platform_role_code: str
    permissions: dict  # platform_role.permissions JSON

    @property
    def id(self) -> uuid.UUID:
        return self.user.id

    def can_read_all(self) -> bool:
        return self.permissions.get("read_all", False)

    def can_write(self, resource: str) -> bool:
        return resource in (self.permissions.get("write") or [])


def get_platform_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> PlatformUser:
    """FastAPI dependency for platform-level operator endpoints.
    
    Validates JWT, checks is_platform_user=True, loads platform_role.permissions.
    Raises 403 if user is not a platform user or platform_role is inactive.
    """
```

### F.2 — `services/cohort_dashboard.py` (NEW)

```python
def get_cohort_overview(db: Session) -> dict:
    """Returns all Charter members with tripwire alert data.
    
    Queries:
    - subscription_tier WHERE tier_name='charter' (cohort metadata)
    - tenant WHERE charter_eligible=true (all Charter members)
    - subscription JOIN subscription_status (Stripe status)
    - tenant_messaging_registration (10DLC status)
    - COUNT(DISTINCT customer) + COUNT(DISTINCT invoice) per tenant
    - MAX(job.created_at) per tenant (days since last job)
    
    Returns: {"cohort_tier_name", "cohort_is_active", "signup_cap", "members": [...]}
    """

def extend_free_period(
    db: Session,
    tenant_id: uuid.UUID,
    new_end_date: datetime,
    reason: str,
    operator_user_id: uuid.UUID,
) -> dict:
    """Extends a Charter member's free period silently (D16).
    
    1. Validate: tenant is Charter, subscription is 'trialing'
    2. Upsert tenant_tier_override (override_free_period_ends_at + override_reason + set_by_operator_user_id)
    3. Update tenant.free_period_ends_at = new_end_date
    4. stripe.Subscription.modify(sub_id, trial_end=int(new_end_date.timestamp()))
    5. Audit log entry
    6. NO customer notification
    
    Returns: {"previous_free_period_ends_at", "new_free_period_ends_at", "stripe_subscription_id", "stripe_trial_end_updated"}
    """

def close_cohort(db: Session, operator_user_id: uuid.UUID) -> dict:
    """Closes the Charter cohort — archives price, deactivates tier, activates others.
    
    1. stripe.Price.modify(price_charter_monthly_id, active=false) — archive, never delete
    2. UPDATE subscription_tier SET is_active=false WHERE tier_name='charter'
    3. UPDATE subscription_tier SET is_active=true WHERE tier_name IN ('trial', 'starter', 'teams')
    4. Audit log entry
    
    Returns: {"charter_price_archived", "charter_tier_deactivated", "activated_tiers"}
    """
```

---

## G. Open Questions Resolved

| # | Question | Resolution |
|---|---|---|
| 1 | **How do platform users authenticate?** The existing `get_current_user()` requires a `tenant_user` row, which platform users don't have. | **New `get_platform_user()` dependency.** Same JWT validation (`verify_cognito_jwt`), but checks `is_platform_user=True` + `platform_role_code IS NOT NULL` instead of looking up `tenant_user`. Returns `PlatformUser` (no `tenant_id`). |
| 2 | **What permission structure do platform roles use?** The `platform_role.permissions` is a JSON object (`{write: [...], read_all: bool, ...}`), not a flat list like `tenant_user_role.permissions`. | **Use the JSON structure directly.** `can_read_all()` checks `permissions.read_all`. `can_write(resource)` checks `resource in permissions.write`. The cohort dashboard GET requires `read_all=true`; extension requires `write` containing `"tenants"` or `"billing"`; close requires `write` containing `"billing"`. |
| 3 | **Where does "last contact" come from?** The spec says "operator-logged" but there's no existing table for operator contact logs. | **Defer to a future batch.** For C-B11, `last_contact` is always `null` in the response. A future batch can add an operator contact log table. The column is in the response schema for forward compatibility. |
| 4 | **How to compute "days since last job"?** The spec says `job.created_at`. | **`MAX(job.created_at) WHERE tenant_id = :tid` → `now() - max_created_at` in days.** If no jobs exist, `days_since_last_job = null` (not 0 — null means "never created a job", which is worse than "created one 8 days ago"). The alert logic: `null` → red (no job ever = highest concern). |
| 5 | **Should the cohort close action also handle existing Charter subscriptions?** | **No.** Per spec §6.6, archived prices continue billing existing subscriptions at the locked rate. The close action only prevents NEW Charter signups. Existing Charter members keep their rate. |
| 6 | **What about the `override_trial_length_days` column on `tenant_tier_override`?** | **Not used by C-B11.** C-B11 uses `override_free_period_ends_at` (absolute timestamp), not `override_trial_length_days` (relative days). The absolute timestamp is what Stripe's `trial_end` needs. The `override_trial_length_days` column is for a different override mechanism (tier-level trial length, not per-tenant extension). |
| 7 | **Should the extension action validate that `new_free_period_ends_at` is after the current `free_period_ends_at`?** | **Yes.** Reject with 422 if the new date is before or equal to the current date. Extensions only go forward, never backward. (A future "shorten free period" feature would be a separate action with different safeguards.) |

---

## H. Surface Mockup Reference

**Frontend batch**: Part B (React Engineer) — requires a UI design spec from the pilot-web-ui-designer before the React prompt is authored.

**Surface**: Operator cohort dashboard at `/operator/cohort` (new route, **not under `(authed)`** — this is a platform-level route, not tenant-scoped).

**Path A scope (Tom decision 2026-08-06)**: This is a **standalone page** with its own minimal layout — no tenant shell, no nav sidebar, no tenant-scoped data. The page has:
- A simple header with "Pilot Operator — Charter Cohort" title
- The cohort table (up to 12 rows)
- The extension modal (triggered per-row)
- The cohort close button (top-right, with confirmation)
- No sidebar, no tenant selector, no impersonation — those are deferred to **C-B15 (Platform Shell + Tenant Impersonation)**

**Login flow**: After Cognito authentication, the frontend calls `GET /api/v1/auth/me` (new endpoint in Part A). If the response indicates `user_type: "platform"`, the frontend redirects to `/operator/cohort`. If `user_type: "tenant"`, the existing redirect to `/dashboard` applies. This is the only routing change — no platform shell, no operator nav.

**§16 pattern consumption**:
- **Always-preview-before-send** (§16.7) — the extension action shows the new date + reason in a confirmation modal before the operator confirms.
- **Optimistic UI** (§16.6) — the dashboard can optimistically update the row after extension, with rollback on error.
- **Four-class severity** — the `alert_level` field drives row styling: red (tripwire), amber (extension window), none (healthy).

**Platform**: Web only (`apps/web`). No mobile surface — this is an operator-only tool.

**UI design spec output**: `dev-docs/architecture-design/batch-designs/batch-c-b11-ui-design-spec.md` (pilot-web-ui-designer authors, Tom approves before React prompt).

---

## I. Component Manifest

| Component | Destination | Purpose |
|---|---|---|
| `CohortDashboardPage` | `apps/web/src/app/operator/cohort/page.tsx` | Thin route |
| `CohortDashboardClient` | `apps/web/src/components/operator/cohort/CohortDashboardClient.tsx` | Orchestrator — fetches cohort data, renders table |
| `CohortMemberRow` | `apps/web/src/components/operator/cohort/CohortMemberRow.tsx` | Single row with alert-level styling |
| `ExtendFreePeriodModal` | `apps/web/src/components/operator/cohort/ExtendFreePeriodModal.tsx` | Confirmation modal (preview-before-send) |
| `CloseCohortButton` | `apps/web/src/components/operator/cohort/CloseCohortButton.tsx` | Cohort close action with confirmation |
| `useCohortOverview` | `apps/web/src/features/operator/hooks/useCohortOverview.ts` | TQ v5 hook — GET /operator/cohort |
| `useExtendFreePeriod` | `apps/web/src/features/operator/hooks/useExtendFreePeriod.ts` | TQ v5 mutation — POST /operator/cohort/{id}/extend |
| `useCloseCohort` | `apps/web/src/features/operator/hooks/useCloseCohort.ts` | TQ v5 mutation — POST /operator/cohort/close |
| `cohortProvisioningHandlers` | `apps/web/src/mocks/handlers/cohortDashboardHandlers.ts` | MSW handlers for 3 endpoints |

---

## J. Detailed Design — Platform Auth Dependency

### J.1 — `PlatformUser` model + `get_platform_user()`

```python
class PlatformUser(BaseModel):
    """Platform-level authenticated user (no tenant context)."""
    model_config = {"arbitrary_types_allowed": True}
    user: User
    platform_role_code: str
    permissions: dict  # platform_role.permissions JSON

    @property
    def id(self) -> uuid.UUID:
        return self.user.id

    def can_read_all(self) -> bool:
        return bool(self.permissions.get("read_all", False))

    def can_write(self, resource: str) -> bool:
        write_perms = self.permissions.get("write") or []
        return resource in write_perms


def get_platform_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> PlatformUser:
    """Platform-level auth — for operator endpoints (cohort dashboard, etc.).
    
    Flow:
    1. Validate JWT (same verify_cognito_jwt)
    2. Look up user by email
    3. Check is_platform_user=True + platform_role_code IS NOT NULL
    4. Load platform_role.permissions JSON
    5. Return PlatformUser
    
    Raises:
        401 — invalid/expired token
        404 — user not found or inactive
        403 — user is not a platform user, or platform_role is inactive
    """
    token = credentials.credentials
    payload = verify_cognito_jwt(token)
    
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Token does not contain email")
    
    user = db.exec(
        select(User).where(User.email == email).where(User.is_active == True)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found or inactive")
    
    if not user.is_platform_user or not user.platform_role_code:
        raise HTTPException(
            status_code=403,
            detail="User is not a platform user. Operator endpoints require platform-level access."
        )
    
    # Load platform role
    platform_role = db.exec(
        select(PlatformRole).where(PlatformRole.code == user.platform_role_code)
        .where(PlatformRole.is_active == True)
    ).first()
    if not platform_role:
        raise HTTPException(status_code=403, detail="Platform role not found or inactive")
    
    return PlatformUser(
        user=user,
        platform_role_code=user.platform_role_code,
        permissions=platform_role.permissions or {},
    )
```

### J.2 — Cohort Overview Query

The `get_cohort_overview()` function needs to efficiently aggregate data across multiple tables for all Charter members. Key query strategy:

```python
# 1. Get Charter tier metadata
charter_tier = db.exec(
    select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
).first()

# 2. Get all Charter-eligible tenants
tenants = db.exec(
    select(Tenant).where(Tenant.charter_eligible == True)
    .order_by(Tenant.charter_member_number)
).all()

# 3. For each tenant, aggregate:
#    - subscription status (JOIN subscription + subscription_status)
#    - messaging status (tenant_messaging_registration)
#    - customer count (COUNT customer WHERE tenant_id)
#    - invoice count (COUNT invoice WHERE tenant_id)
#    - last job date (MAX job.created_at WHERE tenant_id)
# 4. Check Stripe customer for payment method (lazy — only if needed for display)
```

**N+1 avoidance**: Use a single query with subqueries or batch-load the related data. For 12 rows max, even N+1 is acceptable, but the implementation should use `IN` clause batch-loads for customer/invoice/job counts.

---

## K. Test Plan

| Test | Type | Description |
|---|---|---|
| `test_get_platform_user_valid` | Unit | Platform user with valid JWT + `is_platform_user=True` → returns `PlatformUser` with permissions. |
| `test_get_platform_user_tenant_user_rejected` | Unit | Tenant user (not platform) → 403. |
| `test_cohort_overview_empty` | Unit | No Charter members → empty list, tier metadata returned. |
| `test_cohort_overview_with_members` | Unit | 2 Charter members → correct aggregation (status, counts, days_since_last_job). |
| `test_cohort_alert_red` | Unit | Member with `days_since_last_job > 7` → `alert_level="red"`. |
| `test_cohort_alert_amber` | Unit | Member with `free_period_ends_at` within 14 days → `alert_level="amber"`. |
| `test_cohort_alert_red_takes_precedence` | Unit | Member with both conditions → `alert_level="red"`. |
| `test_cohort_alert_no_jobs` | Unit | Member with no jobs → `days_since_last_job=null`, `alert_level="red"`. |
| `test_extend_free_period_happy_path` | Unit | Valid extension → override set, `tenant.free_period_ends_at` updated, Stripe `Subscription.modify` called. |
| `test_extend_free_period_not_trialing` | Unit | Subscription status is `paused` → 409 error. |
| `test_extend_free_period_past_date` | Unit | `new_free_period_ends_at` before current → 422 error. |
| `test_extend_free_period_non_charter` | Unit | Tenant is not Charter → 404 error. |
| `test_close_cohort_happy_path` | Unit | Close → price archived, tier deactivated, other tiers activated. |
| `test_close_cohort_already_closed` | Unit | `is_active` already false → 409 error. |
| `test_endpoint_auth_tenant_user_blocked` | Unit | Tenant user JWT on `/operator/cohort` → 403. |
| `test_endpoint_auth_platform_user_allowed` | Unit | Platform user JWT on `/operator/cohort` → 200. |

**Domain folder**: `tests/domains/platform_infrastructure/` (operator tooling is platform infrastructure).

---

## L. Cost Impact

**$0.** No new AWS services, no new infrastructure. The cohort dashboard is a read-heavy aggregation query that runs on the existing RDS instance. At 12 rows max, the query cost is negligible. The Stripe API calls (extension, close) are free.

---

## M. Definition of Done

- [ ] `PlatformUser` model + `get_platform_user()` dependency added to `core/auth.py`
- [ ] `services/cohort_dashboard.py` created with `get_cohort_overview()` + `extend_free_period()` + `close_cohort()`
- [ ] `api/routes/cohort_dashboard.py` created with 3 endpoints (all using `get_platform_user()`)
- [ ] `api/schemas/cohort.py` created with request/response schemas
- [ ] `app/main.py` updated with router registration
- [ ] OpenAPI regenerated (3 new endpoints)
- [ ] Unit tests written (16 tests minimum) — all passing
- [ ] `pytest -m unit` — 0 new failures
- [ ] Full suite — 0 new failures
- [ ] Ruff — 0 errors on changed/new files
- [ ] MCP-verified: all pre-implementation queries confirmed
- [ ] UI design spec authored by pilot-web-ui-designer (Part B prerequisite)
- [ ] React Engineer prompt authored (after UI spec approval)
