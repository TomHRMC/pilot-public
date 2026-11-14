# Implementation Prompt: C-B11 (Part A — Python Engineer) — Operator Cohort Dashboard + Silent Extension + Cohort Close

**Mode**: Pilot Python Engineer
**Batch**: C-B11 (Part A — Python Engineer runs FIRST)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14p, §2.1a C-5
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b11-design.md`
**Estimated session**: 3–4 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: C-B11 Part B (React Engineer) — **gated on a UI design spec from pilot-web-ui-designer + Tom approval**. Do NOT start Part B until the UI spec is approved. After Part A closes, run `python export_openapi_json.py` + `pnpm sync-api-types` as the handoff signal.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py app > db_models_map.md`.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before committing.
- **Rule 11**: If ANY test fails during your work — even one that appears to be a pre-existing failure — **you must fix it before declaring the batch done**.
- **Rule 12 (sync routes)**: This app is **synchronous by design**. Every DB-touching route and `_impl()` is a plain `def`. **Never convert a handler that touches the sync `Session` to `async def`**.
- **Rule 13 (Pydantic v2)**: Use v2 idioms only. Banned v1 carryover: `class Config`, `@validator`, `.dict()`, `.json()`, `.parse_obj()`. Use `model_config = ConfigDict(...)`, `@field_validator` / `@model_validator`, `.model_dump()`, `.model_validate()`. Every route needs `response_model`. Money is always integer cents.
- **Rule 14 (Ruff)**: Run ruff **only against the files you changed** — `git diff --name-only HEAD -- '*.py'` to get the list, then `ruff check --fix <files> && ruff format <files>`. Fix ALL errors in those files.
- **Rule 16 (verify, don't assume)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either:
> (a) Confirm with Tom that this is a known, accepted failure with a documented reason before proceeding, OR
> (b) Fix the failure before touching any batch files.
>
> You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

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

-- 3. Verify subscription_tier has is_active + signup_cap + tier_name + price_locked
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

-- 8. Verify subscription table has psp_subscription_id + status_id + tenant_id + is_active + trial_ends_at
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name IN ('psp_subscription_id', 'status_id', 'tenant_id', 'is_active', 'trial_ends_at')
ORDER BY ordinal_position;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/core/auth.py                               ← why: get_current_user() pattern + AuthenticatedUser model — add PlatformUser + get_platform_user()
backend/core/permissions.py                        ← why: require_permission() pattern — understand how permissions work (tenant-scoped; platform uses different structure)
backend/core/stripe_config.py                      ← why: get_stripe_ids() — load price_charter_monthly for cohort close
backend/services/stripe_subscriptions.py           ← why: _get_stripe_client() + create_charter_subscription() + resume_subscription() — understand Stripe patterns
backend/app/models/core.py                          ← why: Tenant + User + PlatformRole + SubscriptionTier models
backend/app/models/billing.py                       ← why: Subscription + SubscriptionStatus + CarrierFeeSchedule models
backend/app/models/sms.py                           ← why: TenantMessagingRegistration model (10DLC status)
backend/api/routes/tenant_subscription.py          ← why: existing subscription/tier override patterns — understand how overrides work
backend/api/schemas/dlc.py                          ← why: existing schema patterns for the messaging domain
backend/app/main.py                                 ← why: router registration pattern
backend/db_models_map.md                            ← why: confirm model names and table mappings
backend/tests/conftest.py                           ← why: available fixtures — especially test_platform_role_staff + test_platform_role_superadmin
```

Also run these grep commands to find related files:

```bash
grep -rn "is_platform_user\|platform_role_code\|PlatformRole" backend/app/models/ --include="*.py" -l
grep -rn "get_current_user\|AuthenticatedUser" backend/core/ --include="*.py"
grep -rn "tenant_tier_override\|TenantTierOverride" backend/ --include="*.py" -l
```

---

## Background / Context

C-B11 builds the Pilot operator's Charter cohort management dashboard — a **platform-level** (not tenant-scoped) screen. This is Part A (Python Engineer): the backend that provides the cohort data API and 3 operator actions.

**Key design decision — Platform-Level Auth**: The existing `get_current_user()` dependency is tenant-scoped (requires a `tenant_user` row). Platform users (`is_platform_user=True`) have no tenant membership (DB trigger prevents it). C-B11 introduces a new `get_platform_user()` dependency that validates the JWT, checks `is_platform_user=True`, loads `platform_role.permissions` JSON, and returns a `PlatformUser` context object (no `tenant_id`).

**Three endpoints**:
1. `GET /api/v1/operator/cohort` — cohort overview (all Charter members with tripwire alerts)
2. `POST /api/v1/operator/cohort/{tenant_id}/extend` — silent free-period extension (D16)
3. `POST /api/v1/operator/cohort/close` — cohort close (archive price, deactivate tier, activate others)

**No migration** — all required columns already exist from C-B2.

---

## Task 1 — Platform Auth Dependency: `PlatformUser` + `get_platform_user()`

In `backend/core/auth.py`, add the `PlatformUser` model and `get_platform_user()` dependency.

**Full implementation** (from design doc §J.1):

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
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Platform access required",
                "status": 403,
                "detail": "User is not a platform user. Operator endpoints require platform-level access.",
            },
        )
    
    platform_role = db.exec(
        select(PlatformRole).where(PlatformRole.code == user.platform_role_code)
        .where(PlatformRole.is_active == True)
    ).first()
    if not platform_role:
        raise HTTPException(
            status_code=403,
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Platform role inactive",
                "status": 403,
                "detail": f"Platform role '{user.platform_role_code}' not found or inactive.",
            },
        )
    
    return PlatformUser(
        user=user,
        platform_role_code=user.platform_role_code,
        permissions=platform_role.permissions or {},
    )
```

**Important**: Import `PlatformRole` from `app.models.core`. The `permissions` field on `PlatformRole` is a JSON column — it returns a Python dict. Verify the column type via MCP before coding.

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 2 — Cohort Data Service: `services/cohort_dashboard.py` (NEW)

Create `backend/services/cohort_dashboard.py` with `get_cohort_overview()`.

**Key logic** (from design doc §J.2):

```python
def get_cohort_overview(db: Session) -> dict:
    """Returns all Charter members with tripwire alert data."""
    # 1. Get Charter tier metadata
    charter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()
    
    if not charter_tier:
        return {"cohort_tier_name": "Charter", "cohort_is_active": False, "signup_cap": 0, "members": []}
    
    # 2. Get all Charter-eligible tenants, ordered by member number
    tenants = db.exec(
        select(Tenant).where(Tenant.charter_eligible == True)
        .order_by(Tenant.charter_member_number)
    ).all()
    
    members = []
    now = safe_now_utc()
    
    for tenant in tenants:
        # Get subscription status
        sub_row = db.exec(
            select(Subscription)
            .where(Subscription.tenant_id == tenant.id)
            .where(Subscription.is_active == True)
        ).first()
        
        stripe_status = "unknown"
        if sub_row:
            status = db.exec(
                select(SubscriptionStatus).where(SubscriptionStatus.id == sub_row.status_id)
            ).first()
            stripe_status = status.code if status else "unknown"
        
        # Get messaging status
        msg_reg = db.exec(
            select(TenantMessagingRegistration)
            .where(TenantMessagingRegistration.tenant_id == tenant.id)
        ).first()
        messaging_status = msg_reg.status if msg_reg else "not_started"
        
        # Get customer count
        customer_count = db.exec(
            select(func.count(Customer.id)).where(Customer.tenant_id == tenant.id)
        ).one()
        
        # Get invoice count
        invoice_count = db.exec(
            select(func.count(Invoice.id)).where(Invoice.tenant_id == tenant.id)
        ).one()
        
        # Get last job created_at
        last_job = db.exec(
            select(func.max(Job.created_at)).where(Job.tenant_id == tenant.id)
        ).one()
        
        days_since_last_job = None
        if last_job:
            days_since_last_job = (now - last_job).days
        
        # Compute days remaining
        days_remaining = None
        if tenant.free_period_ends_at:
            days_remaining = (tenant.free_period_ends_at - now).days
        
        # Compute alert level
        alert_level = "none"
        if days_since_last_job is None or days_since_last_job > 7:
            alert_level = "red"
        elif tenant.free_period_ends_at and days_remaining is not None and days_remaining <= 14:
            alert_level = "amber"
        
        members.append({
            "tenant_id": str(tenant.id),
            "business_name": tenant.name,
            "charter_member_number": tenant.charter_member_number,
            "free_period_ends_at": tenant.free_period_ends_at.isoformat() if tenant.free_period_ends_at else None,
            "days_remaining": days_remaining,
            "stripe_status": stripe_status,
            "has_payment_method": False,  # TODO: check Stripe customer for PM — defer to lazy load
            "messaging_status": messaging_status,
            "customer_count": customer_count,
            "invoice_count": invoice_count,
            "days_since_last_job": days_since_last_job,
            "last_contact": None,  # deferred — no operator contact log table yet
            "alert_level": alert_level,
        })
    
    return {
        "cohort_tier_name": charter_tier.tier_name,
        "cohort_is_active": charter_tier.is_active,
        "signup_cap": charter_tier.signup_cap,
        "members": members,
    }
```

**Note on `has_payment_method`**: For MVP, this is always `false` in the aggregation query. Checking Stripe for each tenant's payment method would require N Stripe API calls. A future optimization can batch this or cache it. The frontend can show "Unknown" for this column until a future batch adds the Stripe PM check.

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 3 — Extension Service: `extend_free_period()`

In `backend/services/cohort_dashboard.py`, add `extend_free_period()`.

```python
def extend_free_period(
    db: Session,
    tenant_id: uuid.UUID,
    new_end_date: datetime,
    reason: str,
    operator_user_id: uuid.UUID,
) -> dict:
    """Extends a Charter member's free period silently (D16).
    
    1. Validate: tenant is Charter (charter_eligible=True), subscription is 'trialing'
    2. Upsert tenant_tier_override (override_free_period_ends_at + override_reason + set_by_operator_user_id)
    3. Update tenant.free_period_ends_at = new_end_date
    4. stripe.Subscription.modify(sub_id, trial_end=int(new_end_date.timestamp()))
    5. Audit log entry (via set_audit_context_sync)
    6. NO customer notification
    
    Raises:
        ValueError: Tenant not found, not Charter, subscription not trialing,
            new date is before current date.
    """
    # 1. Load tenant
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    if not tenant.charter_eligible:
        raise ValueError(f"Tenant {tenant_id} is not a Charter member")
    
    # 2. Validate new date is after current
    if tenant.free_period_ends_at and new_end_date <= tenant.free_period_ends_at:
        raise ValueError(
            f"New free period end date {new_end_date} must be after current {tenant.free_period_ends_at}"
        )
    
    # 3. Find active subscription + check status is 'trialing'
    sub_row = db.exec(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)
        .where(Subscription.psp_provider == "stripe")
    ).first()
    
    if not sub_row or not sub_row.psp_subscription_id:
        raise ValueError(f"No active Stripe subscription found for tenant {tenant_id}")
    
    status = db.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.id == sub_row.status_id)
    ).first()
    
    if not status or status.code != "trialing":
        raise ValueError(
            f"Subscription status is '{status.code if status else 'unknown'}', must be 'trialing' to extend. "
            f"Use the resume flow instead."
        )
    
    # 4. Upsert tenant_tier_override
    existing_override = db.exec(
        select(TenantTierOverride).where(TenantTierOverride.tenant_id == tenant_id)
    ).first()
    
    previous_end = tenant.free_period_ends_at
    
    if existing_override:
        existing_override.override_free_period_ends_at = new_end_date
        existing_override.override_reason = reason
        existing_override.set_by_operator_user_id = operator_user_id
        existing_override.set_at = safe_now_utc()
        db.add(existing_override)
    else:
        override = TenantTierOverride(
            tenant_id=tenant_id,
            override_free_period_ends_at=new_end_date,
            override_reason=reason,
            set_by_operator_user_id=operator_user_id,
            set_at=safe_now_utc(),
        )
        db.add(override)
    
    # 5. Update tenant.free_period_ends_at
    tenant.free_period_ends_at = new_end_date
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    # 6. Call Stripe to update trial_end
    from services.stripe_subscriptions import _get_stripe_client
    stripe = _get_stripe_client()
    
    stripe.Subscription.modify(
        sub_row.psp_subscription_id,
        trial_end=int(new_end_date.timestamp()),
    )
    
    logger.info(
        "Extended free period for tenant %s: %s → %s (reason: %s, operator: %s)",
        tenant_id, previous_end, new_end_date, reason, operator_user_id,
    )
    
    return {
        "previous_free_period_ends_at": previous_end.isoformat() if previous_end else None,
        "new_free_period_ends_at": new_end_date.isoformat(),
        "stripe_subscription_id": sub_row.psp_subscription_id,
        "stripe_trial_end_updated": True,
    }
```

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 4 — Cohort Close Service: `close_cohort()`

In `backend/services/cohort_dashboard.py`, add `close_cohort()`.

```python
def close_cohort(db: Session, operator_user_id: uuid.UUID) -> dict:
    """Closes the Charter cohort — archives price, deactivates tier, activates others.
    
    1. stripe.Price.modify(price_charter_monthly_id, active=false) — archive, never delete
    2. UPDATE subscription_tier SET is_active=false WHERE tier_name='charter'
    3. UPDATE subscription_tier SET is_active=true WHERE tier_name IN ('trial', 'starter', 'teams')
    4. Audit log entry
    
    Raises:
        ValueError: Cohort already closed (charter tier is_active=false)
    """
    # 1. Check Charter tier is still active
    charter_tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()
    
    if not charter_tier:
        raise ValueError("Charter tier not found")
    
    if not charter_tier.is_active:
        raise ValueError("Cohort already closed — Charter tier is already inactive")
    
    # 2. Archive the Charter price in Stripe
    from core.stripe_config import get_stripe_ids
    from services.stripe_subscriptions import _get_stripe_client
    
    stripe_ids = get_stripe_ids()
    charter_price_id = stripe_ids.get("prices", {}).get("price_charter_monthly")
    
    if charter_price_id:
        stripe = _get_stripe_client()
        stripe.Price.modify(charter_price_id, active=False)
        logger.info("Archived Charter price %s in Stripe", charter_price_id)
    
    # 3. Deactivate Charter tier
    charter_tier.is_active = False
    db.add(charter_tier)
    
    # 4. Activate other tiers
    activated_tiers = []
    other_tiers = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name.in_(["trial", "starter", "teams"]))
    ).all()
    
    for tier in other_tiers:
        if not tier.is_active:
            tier.is_active = True
            db.add(tier)
            activated_tiers.append(tier.tier_name)
    
    db.commit()
    
    logger.info(
        "Cohort closed by operator %s: Charter price archived, tier deactivated, %d tiers activated",
        operator_user_id, len(activated_tiers),
    )
    
    return {
        "charter_price_archived": bool(charter_price_id),
        "charter_tier_deactivated": True,
        "activated_tiers": activated_tiers,
    }
```

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 5 — API Schemas: `api/schemas/cohort.py` (NEW)

Create `backend/api/schemas/cohort.py` with the Pydantic schemas.

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CohortMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tenant_id: UUID
    business_name: str
    charter_member_number: int | None
    free_period_ends_at: datetime | None
    days_remaining: int | None
    stripe_status: str
    has_payment_method: bool
    messaging_status: str
    customer_count: int
    invoice_count: int
    days_since_last_job: int | None
    last_contact: datetime | None
    alert_level: str  # "red" | "amber" | "none"


class CohortOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    cohort_tier_name: str
    cohort_is_active: bool
    signup_cap: int
    members: list[CohortMemberResponse]


class ExtendFreePeriodRequest(BaseModel):
    new_free_period_ends_at: datetime
    override_reason: str


class ExtendFreePeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tenant_id: UUID
    previous_free_period_ends_at: datetime | None
    new_free_period_ends_at: datetime
    stripe_subscription_id: str
    stripe_trial_end_updated: bool


class CloseCohortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    charter_price_archived: bool
    charter_tier_deactivated: bool
    activated_tiers: list[str]
```

---

## Task 6 — API Routes: `api/routes/cohort_dashboard.py` (NEW)

Create `backend/api/routes/cohort_dashboard.py` with 3 endpoints.

```python
"""C-B11 — Operator Cohort Dashboard routes.

Platform-level endpoints (not tenant-scoped). Uses get_platform_user() for auth.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from api.schemas.cohort import (
    CloseCohortResponse,
    CohortOverviewResponse,
    ExtendFreePeriodRequest,
    ExtendFreePeriodResponse,
)
from core.auth import get_platform_user, PlatformUser
from core.db import get_db, set_audit_context_sync
from services.cohort_dashboard import close_cohort, extend_free_period, get_cohort_overview

router = APIRouter(prefix="/api/v1/operator", tags=["operator"])


@router.get("/cohort", response_model=CohortOverviewResponse)
def get_cohort(
    platform_user: PlatformUser = Depends(get_platform_user),
    db: Session = Depends(get_db),
):
    """Get the Charter cohort overview — all members with tripwire alerts.
    
    Requires: platform_role.permissions.read_all == true
    """
    if not platform_user.can_read_all():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Insufficient permissions",
                "status": 403,
                "detail": "Platform role does not have read_all permission.",
            },
        )
    
    return get_cohort_overview(db)


@router.post("/cohort/{tenant_id}/extend", response_model=ExtendFreePeriodResponse)
def extend_member_free_period(
    tenant_id: uuid.UUID,
    request: ExtendFreePeriodRequest,
    platform_user: PlatformUser = Depends(get_platform_user),
    db: Session = Depends(get_db),
):
    """Silently extend a Charter member's free period (D16).
    
    Requires: platform_role.permissions.write contains 'tenants' or 'billing'
    Rejects if Stripe subscription is not 'trialing'.
    """
    if not (platform_user.can_write("tenants") or platform_user.can_write("billing")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Insufficient permissions",
                "status": 403,
                "detail": "Platform role does not have write permission for 'tenants' or 'billing'.",
            },
        )
    
    set_audit_context_sync(db, user_id=platform_user.id)
    
    try:
        result = extend_free_period(
            db=db,
            tenant_id=tenant_id,
            new_end_date=request.new_free_period_ends_at,
            reason=request.override_reason,
            operator_user_id=platform_user.id,
        )
    except ValueError as exc:
        # Determine status code from error message
        msg = str(exc)
        if "not found" in msg.lower() or "not a charter" in msg.lower():
            code = status.HTTP_404_NOT_FOUND
        elif "must be after" in msg.lower():
            code = status.HTTP_422_UNPROCESSABLE_ENTITY
        elif "must be 'trialing'" in msg.lower() or "use the resume flow" in msg.lower():
            code = status.HTTP_409_CONFLICT
        else:
            code = status.HTTP_400_BAD_REQUEST
        
        raise HTTPException(
            status_code=code,
            detail={
                "type": "https://errors.pilotfortrades.com/cohort-extension-error",
                "title": "Free period extension failed",
                "status": code,
                "detail": msg,
            },
        )
    
    result["tenant_id"] = tenant_id
    return result


@router.post("/cohort/close", response_model=CloseCohortResponse)
def close_charter_cohort(
    platform_user: PlatformUser = Depends(get_platform_user),
    db: Session = Depends(get_db),
):
    """Close the Charter cohort — archive price, deactivate tier, activate others.
    
    Requires: platform_role.permissions.write contains 'billing'
    """
    if not platform_user.can_write("billing"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://errors.pilotfortrades.com/forbidden",
                "title": "Insufficient permissions",
                "status": 403,
                "detail": "Platform role does not have write permission for 'billing'.",
            },
        )
    
    set_audit_context_sync(db, user_id=platform_user.id)
    
    try:
        return close_cohort(db=db, operator_user_id=platform_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://errors.pilotfortrades.com/cohort-close-error",
                "title": "Cohort close failed",
                "status": 409,
                "detail": str(exc),
            },
        )
```

---

## Task 6.5 — Auth Me Endpoint: `GET /api/v1/auth/me`

This endpoint is the login routing mechanism. The frontend calls it immediately after Cognito authentication to determine whether the user is a platform user (redirect to `/operator/cohort`) or a tenant user (redirect to `/dashboard`).

**Implementation**: Add to `backend/api/routes/cohort_dashboard.py` or a new `api/routes/auth_me.py` — your choice. The endpoint tries `get_current_user()` first; on 403 (no tenant_user row), it falls back to `get_platform_user()`.

```python
@router.get("/api/v1/auth/me", response_model=AuthMeResponse)
def get_auth_me(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Returns user type + redirect target after login.
    
    Tries tenant auth first; on 403 falls back to platform auth.
    Returns discriminated union: platform user or tenant user.
    """
    try:
        # Try tenant user auth
        from core.auth import get_current_user
        tenant_user = get_current_user(request, credentials, db)
        return AuthMeResponse(
            user_type="tenant",
            user_id=tenant_user.id,
            email=tenant_user.user.email,
            first_name=tenant_user.user.first_name,
            last_name=tenant_user.user.last_name,
            tenant_id=tenant_user.tenant_id,
            role_code=tenant_user.role_code,
            redirect_to="/dashboard",
        )
    except HTTPException as exc:
        if exc.status_code != 403:
            raise  # Re-raise 401, 404, etc.
        
        # Fall back to platform user auth
        platform_user = get_platform_user(request, credentials, db)
        return AuthMeResponse(
            user_type="platform",
            user_id=platform_user.id,
            email=platform_user.user.email,
            first_name=platform_user.user.first_name,
            last_name=platform_user.user.last_name,
            platform_role_code=platform_user.platform_role_code,
            redirect_to="/operator/cohort",
        )
```

**Schema** (add to `api/schemas/cohort.py`):

```python
class AuthMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_type: str  # "platform" | "tenant"
    user_id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    # Platform user fields (null for tenant users)
    platform_role_code: str | None = None
    # Tenant user fields (null for platform users)
    tenant_id: UUID | None = None
    role_code: str | None = None
    # Redirect target
    redirect_to: str
```

**Note**: The `get_current_user()` and `get_platform_user()` functions both call `verify_cognito_jwt()` — the JWT is validated twice in the fallback path. This is acceptable for MVP (the JWT validation is fast, and this endpoint is called once per login). A future optimization can extract the JWT validation to a shared step.

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 7 — Register Router in `app/main.py`

In `backend/app/main.py`, add the cohort dashboard router:

```python
from api.routes import cohort_dashboard
app.include_router(cohort_dashboard.router)
```

Follow the existing router registration pattern. Add it near the other operator/admin routes if any exist, or with the other API routers.

**Intermediate unit test run**: `pytest -m unit --tb=short -q | tail -5`

---

## Task 8 — Regenerate OpenAPI

After all tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify the 3 new endpoints appear:

```bash
grep -A 5 "operator/cohort" backend/openapi_schema_map.md
```

---

## Task 9 — Regenerate DB Model Map + Import Map

```bash
cd <repo>/backend && source .venv/bin/activate
python generate_db_model_map.py app > db_models_map.md
python generate_app_import_map.py tests > app_model_imports.md
```

---

## Task 10 — Write Tests

Create `backend/tests/domains/platform_infrastructure/test_cb11_cohort_dashboard.py`.

### Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Every new test file MUST:**
- Declare `pytestmark` with both domain marker and `pytest.mark.unit`:
  ```python
  pytestmark = [
      pytest.mark.domain_platform_infrastructure,
      pytest.mark.unit,
  ]
  ```
- Use the `client` fixture (never module-level `TestClient`)
- Use `test_tenant` and `test_user` fixtures (never hardcoded UUIDs)
- Scope assertions by inserted IDs — never `assert len(all_rows) == N`
- Be placed in `backend/tests/domains/platform_infrastructure/`

**Test Resilience Rule (MANDATORY):**
- Never UPDATE or DELETE rows you did not INSERT in the current test.
- Never assert on total row counts for a table.
- The `db_session` fixture is the correct isolation mechanism (transaction rollback).

**Mock pattern for this batch**: Mock `stripe.Subscription.modify` and `stripe.Price.modify` to return fake objects. Mock `_get_stripe_client()` and `get_stripe_ids()`. Use the `db_session` fixture for direct DB access.

**For platform user auth tests**: Use the `test_platform_role_staff` or `test_platform_role_superadmin` fixtures from `conftest.py`. Create a platform user with `is_platform_user=True` + `platform_role_code` set. Mock `verify_cognito_jwt` to return the platform user's email.

### Required Tests (minimum 16)

| Test | Description |
|---|---|
| `test_get_platform_user_valid` | Platform user with valid JWT + `is_platform_user=True` → returns `PlatformUser` with permissions. |
| `test_get_platform_user_tenant_user_rejected` | Tenant user (not platform) → 403. |
| `test_cohort_overview_empty` | No Charter members → empty list, tier metadata returned. |
| `test_cohort_overview_with_members` | 2 Charter members → correct aggregation (status, counts, days_since_last_job). |
| `test_cohort_alert_red` | Member with `days_since_last_job > 7` → `alert_level="red"`. |
| `test_cohort_alert_amber` | Member with `free_period_ends_at` within 14 days → `alert_level="amber"`. |
| `test_cohort_alert_red_takes_precedence` | Member with both conditions → `alert_level="red"`. |
| `test_cohort_alert_no_jobs` | Member with no jobs → `days_since_last_job=null`, `alert_level="red"`. |
| `test_extend_free_period_happy_path` | Valid extension → override set, `tenant.free_period_ends_at` updated, Stripe `Subscription.modify` called. |
| `test_extend_free_period_not_trialing` | Subscription status is `paused` → 409 error. |
| `test_extend_free_period_past_date` | `new_free_period_ends_at` before current → 422 error. |
| `test_extend_free_period_non_charter` | Tenant is not Charter → 404 error. |
| `test_close_cohort_happy_path` | Close → price archived, tier deactivated, other tiers activated. |
| `test_close_cohort_already_closed` | `is_active` already false → 409 error. |
| `test_endpoint_auth_tenant_user_blocked` | Tenant user JWT on `/operator/cohort` → 403. |
| `test_endpoint_auth_platform_user_allowed` | Platform user JWT on `/operator/cohort` → 200. |

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

python -m pytest --tb=short -q 2>&1 | tail -10

python -m pytest tests/domains/platform_infrastructure/ -v 2>&1 | tail -20

grep -A 5 "operator/cohort" backend/openapi_schema_map.md

echo "=== C-B11 PART A FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` must report no remaining issues in your changed files.

> **Any failure in either phase must be fixed before the batch is declared done.**

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All MCP pre-work queries run — all 8 queries confirmed expected results
- [ ] All mandatory source files read before writing any code
- [ ] `PlatformUser` model + `get_platform_user()` dependency added to `core/auth.py`
- [ ] `services/cohort_dashboard.py` created with `get_cohort_overview()` + `extend_free_period()` + `close_cohort()`
- [ ] `api/schemas/cohort.py` created with 5 Pydantic schemas
- [ ] `api/routes/cohort_dashboard.py` created with 3 endpoints (all using `get_platform_user()`)
- [ ] `app/main.py` updated with router registration
- [ ] OpenAPI regenerated (3 new endpoints)
- [ ] `db_models_map.md` + `app_model_imports.md` regenerated
- [ ] All new test files use `pytestmark` with `domain_platform_infrastructure` + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All new tests use `test_tenant` and `test_user` fixtures (no hardcoded UUIDs)
- [ ] All API errors follow RFC 7807 Problem Details format
- [ ] All mutation endpoints call `set_audit_context_sync()` before committing
- [ ] All DB-touching routes/`_impl()` are sync `def` — no `async def` on the blocking `Session`
- [ ] Only Pydantic v2 idioms used; every route has `response_model`
- [ ] `ruff check --fix && ruff format` run on changed files only — zero remaining issues
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` Appendix B using the format below.
2. **Handoff**: Run `python export_openapi_json.py` (already done in Task 8). The React Engineer (Part B) is gated on a UI design spec from pilot-web-ui-designer + Tom approval. Do NOT start Part B until the UI spec is approved.

```markdown
### C-B11 (Part A — Python Engineer) — Operator Cohort Dashboard: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Source design doc**: `batch-c-b11-design.md`
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description of key change 1]
- [Brief description of key change 2]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/path/to/file.py` | Created / Updated — [what changed] |
| ... | ... |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/platform_infrastructure/test_cb11_cohort_dashboard.py` | `platform_infrastructure` | N | ✅ |
```

---

## After This Task — Next Step

**Part A is complete.** The React Engineer (Part B) is gated on:
1. A UI design spec from the pilot-web-ui-designer (must be Tom-approved before the React prompt is authored)
2. `pnpm sync-api-types` to regenerate TypeScript types from the new OpenAPI spec

Return to Pilot Architect mode to coordinate the UI design spec + React Engineer prompt.
