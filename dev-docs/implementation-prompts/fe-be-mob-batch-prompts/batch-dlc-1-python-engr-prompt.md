# Implementation Prompt: DLC-1 — 10DLC Compliance Engineering (Backend)

**Mode**: Pilot Python Engineer  
**Batch**: DLC-1  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P1 — 10DLC Compliance Engineering  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-dlc-1-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: DLC-1 React Engineer prompt (`batch-dlc-1-react-engr-prompt.md`) — runs after this batch completes and `python export_openapi_json.py` is run

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py`.
- **Rule 3**: After all endpoint changes → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`). This is the **handoff signal** to the React Engineer.
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Write raw `op.execute()` SQL. Chain migrations in order.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with explicit `WHERE tenant_id = :tid`.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never INSERT, UPDATE, or DELETE via MCP.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format (`{"type": "https://...", "title": "...", "status": N, "detail": "..."}`).
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before committing.
- **Rule 11**: If ANY test fails during your work — even one that appears to be a pre-existing failure — **fix it before declaring the batch done**.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT proceed. Either confirm with Tom that the failure is known and accepted, or fix it first. You may NOT start implementation while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never INSERT, UPDATE, or DELETE via MCP.

```sql
-- 1. Confirm current alembic head
SELECT version_num FROM public.alembic_version;
-- Expected: 9b3f7ea49606

-- 2. Confirm tenant table has NO 10DLC business profile columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
ORDER BY ordinal_position;
-- Expected: 13 columns — id, name, is_active, current_subscription_tier_id, trial_started_at,
-- trial_ends_at, trial_length_days_override, stripe_customer_id, mfa_grace_period_started_at,
-- created_at, updated_at, created_by, updated_by
-- NO legal_business_name, NO ein — confirm these are absent

-- 3. Confirm customer table current SMS columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer'
  AND column_name LIKE '%sms%'
ORDER BY ordinal_position;
-- Expected: sms_opted_out, sms_opt_out_at, sms_opt_in_consent, sms_opt_in_at, sms_opt_in_source
-- Confirm sms_consent_attested_by, sms_consent_attested_at, sms_consent_ip_address,
-- sms_verification_status do NOT exist yet

-- 4. Confirm neither target table exists yet
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('tenant_10dlc_profile', 'customer_sms_consent_audit');
-- Expected: zero rows (empty result)

-- 5. Confirm the sms_opt_in_source CHECK constraint on customer
SELECT conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.customer'::regclass
  AND contype = 'c';
-- Look for customer_sms_opt_in_source_chk:
-- sms_opt_in_source IN ('explicit_checkbox', 'inbound_initiated', 'verbal_captured')
-- This constraint already exists — confirm before designing Migration 2

-- 6. Confirm AppendOnlyMixin exists in codebase
-- (Run as grep in terminal, not MCP)
-- grep -n "class AppendOnlyMixin" backend/app/models/mixins.py
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/core.py                         ← TenantEmailBranding pattern (PK=tenant_id, single-row upsert)
backend/app/models/crm.py                          ← Customer model + existing SMS consent fields
backend/app/models/sms.py                          ← TenantPhoneNumber model
backend/app/models/mixins.py                       ← StandardAuditMixin + AppendOnlyMixin definitions
backend/api/routes/tenant_email_branding.py        ← GET/PUT single-row-per-tenant upsert route pattern
backend/api/routes/webhooks_sms.py                 ← Existing TCPA keyword handlers
backend/services/customer_communication_threading.py ← handle_sms_opt_out(), handle_sms_opt_in(), handle_sms_help()
backend/services/telnyx_sms_carrier.py             ← send_message() signature: (from_number, to_number, body)
backend/services/sms_carrier.py                    ← get_sms_carrier() factory + SendResult dataclass
backend/api/routes/customers.py                    ← create_customer() + update_customer() to understand injection points
backend/api/schemas/customers.py                   ← CustomerCreate + CustomerUpdate Pydantic schemas
backend/core/celery_app.py                         ← Celery imports list — you must add new task module here
backend/tasks/marketing_notifications.py           ← Two-layer Celery task pattern reference
backend/migrations/versions/                       ← Read the most recent migration for format reference
backend/db_models_map.md                           ← Confirm existing model names before adding new ones
```

Also run:
```bash
grep -rn "AppendOnlyMixin" backend/app/models/ --include="*.py"
grep -rn "handle_sms_opt_in\|handle_sms_opt_out\|handle_sms_help" backend/ --include="*.py"
grep -rn "from tasks\." backend/core/celery_app.py
```

---

## Background / Context

This batch implements 10DLC carrier compliance engineering required before Telnyx SMS registration. Carriers manually vet the **product UI** during TCR campaign review — the attestation checkbox (Task 3) and keyword handlers (Task 4) must be live in the app before Tom submits Step 2 (sub-brand + campaign submission) or the campaign will be rejected.

The batch adds:
1. **`Tenant10DlcProfile`** — a single-row-per-tenant table capturing business registration data needed to provision each tenant's Telnyx sub-brand
2. **3 new columns on `customer`** — `sms_consent_attested_by`, `sms_consent_attested_at`, `sms_consent_ip_address`, `sms_verification_status` — supporting the offline consent audit trail
3. **`CustomerSmsConsentAudit`** — append-only audit table logging each consent lifecycle event
4. **Celery task `send_double_optin_sms`** — sends the opt-in confirmation SMS when a customer is created/updated with a phone + attestation
5. **TCPA keyword handler updates** — ensures `handle_sms_opt_in()` sets `sms_verification_status='verified'` and writes an audit row; ensures HELP reply text matches DLC spec §2.4

---

## Task 1 — Three Alembic Migrations

**Read the design doc §B before writing any migration.**

Create three chained blank migrations in this order:

### Migration 1-A: `tenant_10dlc_profile` table

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "dlc1_create_tenant_10dlc_profile"
```

`upgrade()`:
```python
def upgrade() -> None:
    op.execute("""
        CREATE TABLE tenant_10dlc_profile (
            created_at          TIMESTAMPTZ NOT NULL,
            updated_at          TIMESTAMPTZ NOT NULL,
            created_by          UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by          UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            tenant_id           UUID PRIMARY KEY REFERENCES tenant(id) ON DELETE RESTRICT,
            legal_business_name TEXT NOT NULL,
            dba_name            TEXT,
            ein                 TEXT,
            hq_address_line1    TEXT,
            hq_address_line2    TEXT,
            hq_city             TEXT,
            hq_state            TEXT,
            hq_postal_code      TEXT,
            hq_country          TEXT NOT NULL DEFAULT 'US',
            support_email       TEXT,
            support_phone       TEXT
        )
    """)
    op.execute("""
        CREATE TRIGGER set_updated_at_tenant_10dlc_profile
            BEFORE UPDATE ON tenant_10dlc_profile
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)
```

`downgrade()`:
```python
def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_10dlc_profile CASCADE")
```

### Migration 1-B: 4 new columns on `customer`

Set `down_revision` to Migration 1-A's revision ID.

```bash
alembic revision -m "dlc1_add_customer_sms_consent_columns"
```

`upgrade()`:
```python
def upgrade() -> None:
    # All columns nullable — no 3-part pattern required
    op.execute("""
        ALTER TABLE customer
            ADD COLUMN IF NOT EXISTS sms_consent_attested_by UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            ADD COLUMN IF NOT EXISTS sms_consent_attested_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS sms_consent_ip_address  TEXT,
            ADD COLUMN IF NOT EXISTS sms_verification_status TEXT
                DEFAULT 'unverified'
                CHECK (sms_verification_status IN ('unverified','pending_verification','verified','opted_out'))
    """)
```

`downgrade()`:
```python
def downgrade() -> None:
    op.execute("""
        ALTER TABLE customer
            DROP COLUMN IF EXISTS sms_consent_attested_by,
            DROP COLUMN IF EXISTS sms_consent_attested_at,
            DROP COLUMN IF EXISTS sms_consent_ip_address,
            DROP COLUMN IF EXISTS sms_verification_status
    """)
```

### Migration 1-C: `customer_sms_consent_audit` table

Set `down_revision` to Migration 1-B's revision ID.

```bash
alembic revision -m "dlc1_create_customer_sms_consent_audit"
```

`upgrade()`:
```python
def upgrade() -> None:
    op.execute("""
        CREATE TABLE customer_sms_consent_audit (
            id                  UUID PRIMARY KEY,
            created_at          TIMESTAMPTZ NOT NULL,
            tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
            customer_id         UUID NOT NULL REFERENCES customer(id) ON DELETE RESTRICT,
            attested_by         UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            ip_address          TEXT NOT NULL,
            attested_at         TIMESTAMPTZ NOT NULL,
            consent_text_hash   TEXT NOT NULL,
            action              TEXT NOT NULL,
            CONSTRAINT customer_sms_consent_audit_action_chk
                CHECK (action IN ('attested','double_opt_in_sent','double_opt_in_confirmed','opted_out'))
        )
    """)
    op.execute("""
        CREATE INDEX idx_customer_sms_consent_audit_customer
            ON customer_sms_consent_audit(customer_id)
    """)
    op.execute("""
        CREATE INDEX idx_customer_sms_consent_audit_tenant
            ON customer_sms_consent_audit(tenant_id)
    """)
```

`downgrade()`:
```python
def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS customer_sms_consent_audit CASCADE")
```

### Run and verify all three migrations:

```bash
alembic upgrade head
alembic downgrade -3
alembic upgrade head
alembic current   # must show the Migration 1-C revision ID
```

---

## Task 2 — SQLModel Classes

### 2-A: `Tenant10DlcProfile` in `app/models/core.py`

Add after the `TenantEmailBranding` class (same file, same single-row-per-tenant pattern).

```python
class Tenant10DlcProfile(StandardAuditMixin, SQLModel, table=True):
    """
    10DLC business registration data for a tenant.
    Required to provision Telnyx sub-brand per tenant for SMS campaign registration.
    Single row per tenant (PK = tenant_id). DLC-1.
    """

    __tablename__ = "tenant_10dlc_profile"

    tenant_id: uuid.UUID = Field(
        primary_key=True,
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    legal_business_name: str = Field(sa_column=Column(Text, nullable=False))
    dba_name: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    ein: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    hq_address_line1: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    hq_address_line2: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    hq_city: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    hq_state: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    hq_postal_code: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    hq_country: str = Field(
        default="US",
        sa_column=Column(Text, server_default=text("'US'"), nullable=False),
    )
    support_email: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    support_phone: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    # StandardAuditMixin provides created_at, updated_at; override FK audit fields:
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
```

### 2-B: `CustomerSmsConsentAudit` in `app/models/crm.py`

Add after the `Customer` class.

```python
class CustomerSmsConsentAudit(AppendOnlyMixin, SQLModel, table=True):
    """
    Append-only audit log for SMS consent lifecycle events per customer.
    Written on: attestation, double opt-in send, double opt-in confirmed, opt-out.
    Never mutated — no updated_at, no updated_by. DLC-1.
    """

    __tablename__ = "customer_sms_consent_audit"
    __table_args__ = (
        CheckConstraint(
            "action IN ('attested','double_opt_in_sent','double_opt_in_confirmed','opted_out')",
            name="customer_sms_consent_audit_action_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # created_at provided by AppendOnlyMixin
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    customer_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("customer.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    attested_by: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    ip_address: str = Field(sa_column=Column(Text, nullable=False))
    attested_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    consent_text_hash: str = Field(sa_column=Column(Text, nullable=False))
    action: str = Field(sa_column=Column(Text, nullable=False))
```

> **Read `app/models/mixins.py` first** to confirm the exact field names provided by `AppendOnlyMixin` (likely `created_at` and `created_by`). Import `AppendOnlyMixin` at the top of `crm.py` if not already imported.

### 2-C: Update `Customer` model in `app/models/crm.py`

Add 4 new fields to `Customer` after the existing `sms_opt_in_source` field:

```python
    # DLC-1: Offline consent attestation audit fields
    sms_consent_attested_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    sms_consent_attested_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    sms_consent_ip_address: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    # DLC-1: Double opt-in state tracker
    # 'unverified' → 'pending_verification' (attestation) → 'verified' (YES reply) | 'opted_out' (STOP)
    sms_verification_status: str = Field(
        default="unverified",
        sa_column=Column(Text, server_default=text("'unverified'"), nullable=False),
    )
```

Also add the check constraint for `sms_verification_status` to `__table_args__`:
```python
CheckConstraint(
    "sms_verification_status IN ('unverified','pending_verification','verified','opted_out')",
    name="customer_sms_verification_status_chk",
),
```

> **Read the full `Customer.__table_args__` tuple before modifying it** to avoid replacing existing constraints. Add the new constraint to the existing tuple — do not replace the tuple.

After model changes → regenerate:
```bash
python generate_db_model_map.py
```

---

## Task 3 — Pydantic Schemas

### 3-A: New file `api/schemas/dlc.py`

```python
"""
DLC-1 Pydantic schemas for 10DLC profile endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class Tenant10DlcProfileRequest(BaseModel):
    legal_business_name: str
    dba_name: str | None = None
    ein: str | None = None
    hq_address_line1: str | None = None
    hq_address_line2: str | None = None
    hq_city: str | None = None
    hq_state: str | None = None
    hq_postal_code: str | None = None
    hq_country: str = "US"
    support_email: str | None = None
    support_phone: str | None = None

    @field_validator("legal_business_name")
    @classmethod
    def legal_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("legal_business_name cannot be blank")
        return v.strip()


class Tenant10DlcProfileResponse(BaseModel):
    tenant_id: uuid.UUID
    legal_business_name: str
    dba_name: str | None
    ein_masked: str | None    # "**-***XXXX" or None
    hq_address_line1: str | None
    hq_address_line2: str | None
    hq_city: str | None
    hq_state: str | None
    hq_postal_code: str | None
    hq_country: str
    support_email: str | None
    support_phone: str | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}
```

### 3-B: Update `api/schemas/customers.py`

**Read the file first.** Add two fields to `CustomerCreate` and `CustomerUpdate`:

```python
# In CustomerCreate and CustomerUpdate — add these fields:
sms_attestation_checked: bool = False
    # When True and mobile_phone is provided: triggers consent audit + double opt-in SMS.
    # Frontend must set True only when the checkbox was explicitly checked.
sms_consent_ip_address: str | None = None
    # Client IP captured by the frontend — passed through to the audit log.
    # Optional; backend will use "unknown" if not provided.
```

> **Do NOT change any other field** in the customer schemas. Read the current file carefully before modifying.

---

## Task 4 — New Route File: `api/routes/tenant_10dlc_profile.py`

```python
"""
10DLC Business Profile Routes — DLC-1
======================================
GET  /api/v1/settings/10dlc-profile       — view profile (settings.view)
PUT  /api/v1/settings/10dlc-profile       — upsert profile (settings.manage)
GET  /api/v1/settings/10dlc-profile/test  — test endpoint (no auth)
PUT  /api/v1/settings/10dlc-profile/test  — test endpoint (no auth)

Single-row-per-tenant upsert pattern (same as TenantEmailBranding).
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from api.schemas.dlc import Tenant10DlcProfileRequest, Tenant10DlcProfileResponse
from app.models.core import Tenant10DlcProfile
from core.auth import AuthenticatedUser, get_current_user
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


def _mask_ein(ein: str | None) -> str | None:
    """Mask EIN to last 4 digits: **-***1234"""
    if not ein:
        return None
    clean = ein.replace("-", "").strip()
    if len(clean) < 4:
        return "**-***" + clean
    return "**-***" + clean[-4:]


def _to_response(profile: Tenant10DlcProfile) -> Tenant10DlcProfileResponse:
    return Tenant10DlcProfileResponse(
        tenant_id=profile.tenant_id,
        legal_business_name=profile.legal_business_name,
        dba_name=profile.dba_name,
        ein_masked=_mask_ein(profile.ein),
        hq_address_line1=profile.hq_address_line1,
        hq_address_line2=profile.hq_address_line2,
        hq_city=profile.hq_city,
        hq_state=profile.hq_state,
        hq_postal_code=profile.hq_postal_code,
        hq_country=profile.hq_country,
        support_email=profile.support_email,
        support_phone=profile.support_phone,
        updated_at=profile.updated_at,
    )


def _upsert_10dlc_profile_impl(
    payload: Tenant10DlcProfileRequest,
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Tenant10DlcProfileResponse:
    """Shared upsert logic — called by both authenticated and test endpoints."""
    now = datetime.now(UTC)

    existing = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == tenant_id)
    ).first()

    if existing:
        existing.legal_business_name = payload.legal_business_name
        existing.dba_name = payload.dba_name
        if payload.ein is not None:
            existing.ein = payload.ein   # only overwrite if explicitly provided
        existing.hq_address_line1 = payload.hq_address_line1
        existing.hq_address_line2 = payload.hq_address_line2
        existing.hq_city = payload.hq_city
        existing.hq_state = payload.hq_state
        existing.hq_postal_code = payload.hq_postal_code
        existing.hq_country = payload.hq_country
        existing.support_email = payload.support_email
        existing.support_phone = payload.support_phone
        existing.updated_by = user_id
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return _to_response(existing)
    else:
        profile = Tenant10DlcProfile(
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
            created_by=user_id,
            updated_by=user_id,
            **payload.model_dump(exclude={"ein"} if payload.ein is None else set()),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return _to_response(profile)


# ── TEST ENDPOINTS FIRST (per §8.2 dual-endpoint pattern) ───────────────────

@router.get(
    "/10dlc-profile/test",
    response_model=Tenant10DlcProfileResponse,
    summary="[TEST] Get 10DLC profile — no auth",
    tags=["settings"],
)
def get_10dlc_profile_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    profile = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == ctx.tenant_id)
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "10DLC profile not configured",
                "status": 404,
                "detail": "No 10DLC business profile has been saved for this tenant.",
            },
        )
    return _to_response(profile)


@router.put(
    "/10dlc-profile/test",
    response_model=Tenant10DlcProfileResponse,
    summary="[TEST] Upsert 10DLC profile — no auth",
    tags=["settings"],
)
def put_10dlc_profile_test(
    payload: Tenant10DlcProfileRequest,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _upsert_10dlc_profile_impl(payload, db, ctx.tenant_id, ctx.user_id)


# ── AUTHENTICATED ENDPOINTS ──────────────────────────────────────────────────

@router.get(
    "/10dlc-profile",
    response_model=Tenant10DlcProfileResponse,
    summary="Get 10DLC business profile",
    tags=["settings"],
)
def get_10dlc_profile(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    profile = db.exec(
        select(Tenant10DlcProfile).where(
            Tenant10DlcProfile.tenant_id == current_user.tenant_id
        )
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "10DLC profile not configured",
                "status": 404,
                "detail": "No 10DLC business profile has been saved for this tenant yet.",
            },
        )
    return _to_response(profile)


@router.put(
    "/10dlc-profile",
    response_model=Tenant10DlcProfileResponse,
    summary="Create or update 10DLC business profile",
    tags=["settings"],
)
def put_10dlc_profile(
    payload: Tenant10DlcProfileRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    set_audit_context_sync(db, user_id=current_user.id)
    return _upsert_10dlc_profile_impl(payload, db, current_user.tenant_id, current_user.id)
```

---

## Task 5 — Update `customers.py` Routes

**Read `api/routes/customers.py` first** (especially `create_customer()` and `update_customer()`).

In both `_create_customer_impl()` (or equivalent shared logic) and `_update_customer_impl()`:

When `customer_in.mobile_phone` is provided AND `customer_in.sms_attestation_checked is True`:

```python
from datetime import UTC, datetime
import hashlib, uuid as _uuid

from app.models.crm import CustomerSmsConsentAudit

# After setting customer.mobile_phone:
if customer_in.mobile_phone and getattr(customer_in, "sms_attestation_checked", False):
    now = datetime.now(UTC)
    customer.sms_opt_in_source = "explicit_checkbox"
    customer.sms_consent_attested_by = current_user.id   # or ctx.user_id for test endpoint
    customer.sms_consent_attested_at = now
    customer.sms_consent_ip_address = getattr(customer_in, "sms_consent_ip_address", None) or "unknown"
    customer.sms_verification_status = "pending_verification"

    # Commit customer first so audit FK resolves
    db.add(customer)
    db.commit()
    db.refresh(customer)

    # Write audit row
    CONSENT_TEXT = (
        "I confirm that I have received explicit, documented consent from this customer "
        "to send them SMS notifications regarding their service."
    )
    audit_row = CustomerSmsConsentAudit(
        id=_uuid.uuid4(),
        created_at=now,
        tenant_id=customer.tenant_id,
        customer_id=customer.id,
        attested_by=current_user.id,
        ip_address=customer.sms_consent_ip_address,
        attested_at=now,
        consent_text_hash=hashlib.sha256(CONSENT_TEXT.encode()).hexdigest(),
        action="attested",
    )
    db.add(audit_row)
    db.commit()

    # Enqueue double opt-in SMS (background)
    from tasks.sms_compliance import send_double_optin_sms
    send_double_optin_sms.delay(
        customer_id=str(customer.id),
        tenant_id=str(customer.tenant_id),
    )
```

> **Important**: Only trigger this flow if `sms_attestation_checked=True` AND `mobile_phone` is non-empty. If `sms_attestation_checked=False` (the default), do nothing — the form did not include an attested phone number. The customer save still succeeds normally.

---

## Task 6 — New Celery Task: `tasks/sms_compliance.py`

Create new file. Use the two-layer pattern per inclusion file §12.

The full implementation is specified in design doc §F1. Key points:
- Task name: `send_double_optin_sms`
- Parameters: `customer_id: str`, `tenant_id: str` (string UUIDs — Celery does not serialize UUID objects)
- `max_retries=3`, `default_retry_delay=60`
- Opt-in message template: `"Hi {first_name}, {business_name} uses Pilot for Trades for service updates. Reply YES to confirm you want to receive texts. Reply STOP to cancel."`
- Fallback: `first_name = customer.first_name or "there"`, `business_name` from `Tenant10DlcProfile.legal_business_name` or `"your service provider"` if no profile exists
- Writes `CustomerSmsConsentAudit` row with `action='double_opt_in_sent'` after every send attempt (success or failure)
- Only retry on `result.retryable == True` from `SendResult`

Register in `core/celery_app.py` imports list:
```python
"tasks.sms_compliance",
```

---

## Task 7 — Update `customer_communication_threading.py`

**Read the full file first** before modifying.

### 7-A: Update `handle_sms_opt_in()`

When a customer replies YES/START/UNSTOP:
1. Set `customer.sms_verification_status = "verified"` (new field)
2. Keep existing: `customer.sms_opt_in_consent = True`, `customer.sms_opted_out = False`, `customer.sms_opt_in_at = now`
3. Write `CustomerSmsConsentAudit` row with `action='double_opt_in_confirmed'`
4. Send confirmation: `"You have been resubscribed to updates from {tenant_business_name}."` — look up tenant name from `Tenant10DlcProfile` if available, otherwise use tenant.name

### 7-B: Verify/update `handle_sms_opt_out()` confirmation text

Carrier-required text per DLC spec §2.4:  
`"You have been unsubscribed. No more messages will be sent."`

Read the current implementation. If it already sends this exact text, no change needed. If it sends something different, update it.

Also set `customer.sms_verification_status = "opted_out"` on STOP.

### 7-C: Verify/update `handle_sms_help()` auto-reply text

Carrier-required format per DLC spec §2.4:  
`"Pilot for Trades alerts for {Tenant Business Name}. Reply STOP to cancel. Msg&Data rates apply. Contact {Tenant Phone} for help."`

Read the current implementation. If it sends this format, no change needed.

If it sends a generic message without the tenant's business name, update it to:
1. Look up `TenantPhoneNumber` from `inbound.to_number` to get `tenant_id`
2. Look up `Tenant10DlcProfile` for `legal_business_name` — fallback to `"your service provider"` if no profile
3. Look up `TenantPhoneNumber.phone_number` for the support phone
4. Format and send the DLC-spec message

---

## Task 8 — Register New Route in `app/main.py`

**Read `app/main.py` first** to understand where settings routes are mounted.

```python
from api.routes import tenant_10dlc_profile

app.include_router(
    tenant_10dlc_profile.router,
    prefix="/api/v1/settings",
    tags=["settings"],
)
```

---

## Task 9 — Tests

**Domain**: `notifications_comms/` (SMS consent is a communications domain concern)

Create file: `backend/tests/domains/notifications_comms/test_dlc1_sms_compliance.py`

```python
"""
DLC-1 SMS Compliance Tests
===========================
Tests for:
  - Tenant10DlcProfile GET/PUT via test endpoints
  - Customer attestation flow: checkbox → audit row → sms_verification_status
  - handle_sms_opt_in() sets sms_verification_status='verified'
  - handle_sms_opt_out() sets sms_verification_status='opted_out'
  - send_double_optin_sms Celery task (_impl layer — not .delay())
"""

import pytest

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]
```

**Required test cases** (minimum 8):

| # | Test | What it verifies |
|---|---|---|
| 1 | `test_put_10dlc_profile_creates_new_row` | PUT `/settings/10dlc-profile/test` with `legal_business_name` → 200, row in DB |
| 2 | `test_put_10dlc_profile_upserts_existing` | Second PUT → updates existing row, does NOT create duplicate |
| 3 | `test_get_10dlc_profile_returns_masked_ein` | PUT with EIN `"12-3456789"` → GET returns `ein_masked="**-***6789"` |
| 4 | `test_get_10dlc_profile_404_when_not_configured` | GET on tenant with no profile → 404 RFC 7807 |
| 5 | `test_customer_attestation_sets_verification_status` | `POST /customers/test` with `sms_attestation_checked=True` + `mobile_phone` → `sms_verification_status='pending_verification'`, audit row written |
| 6 | `test_customer_no_attestation_no_audit_row` | `POST /customers/test` with `sms_attestation_checked=False` + `mobile_phone` → no audit row, `sms_verification_status='unverified'` |
| 7 | `test_handle_sms_opt_in_sets_verified` | Call `handle_sms_opt_in(db, customer_id, inbound)` → `sms_verification_status='verified'`, `sms_opt_in_consent=True`, audit row with `action='double_opt_in_confirmed'` |
| 8 | `test_handle_sms_opt_out_sets_opted_out` | Call `handle_sms_opt_out(db, customer_id, inbound)` → `sms_verification_status='opted_out'`, `sms_opted_out=True` |
| 9 | `test_send_double_optin_sms_impl_uses_fallback_business_name` | Call `_send_double_optin_sms_impl()` on tenant with no 10DLC profile → message body contains `"your service provider"` |
| 10 | `test_send_double_optin_sms_impl_skips_opted_out_customer` | Customer with `sms_opted_out=True` → returns `{"status": "skipped", "reason": "already_opted_out"}` |

**Test rules (per inclusion file §6)**:
- Use `client` fixture (never module-level `TestClient`)
- Use `test_tenant`, `test_user` fixtures (no hardcoded UUIDs)
- Use `second_tenant` for "empty profile" state tests (test_tenant may have seeded rows)
- Scope assertions by inserted IDs — never assert on total row counts
- Mock `send_double_optin_sms.delay` in customer creation tests: `@patch("tasks.sms_compliance.send_double_optin_sms.delay")`
- Mock `get_sms_carrier()` in Celery task `_impl` tests: use `MockSmsCarrier` from `services.sms_carrier`

---

## Intermediate Verification (after Task 9)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before proceeding to Final Verification.

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full Suite + OpenAPI Regeneration

```bash
cd <repo>/backend
source .venv/bin/activate

# Full suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Spot check new tests
python -m pytest tests/domains/notifications_comms/test_dlc1_sms_compliance.py -v 2>&1 | tail -20

# Regenerate OpenAPI → required for React Engineer handoff
python export_openapi_json.py

# Verify new endpoints appear
grep -A 3 "10dlc-profile" backend/openapi_schema_map.md

# Verify DB model map updated
grep "Tenant10DlcProfile\|CustomerSmsConsentAudit" backend/db_models_map.md

# Verify schema JSON updated
python schema_manager.py --diff

echo "=== DLC-1 BACKEND FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

Update `dev-docs/analysis/pilot-launch-plan.md` §P1 DLC-1 when each item is done:

- [ ] Pre-modification regression baseline captured (`X passed` using `pytest -m unit`)
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] All MCP pre-work queries run and confirmed (no unexpected results)
- [ ] All mandatory source files read before writing any code
- [ ] Migration 1-A: `tenant_10dlc_profile` table created — upgrade/downgrade verified
- [ ] Migration 1-B: 4 new `customer` columns — upgrade/downgrade verified
- [ ] Migration 1-C: `customer_sms_consent_audit` table created — upgrade/downgrade verified
- [ ] `alembic upgrade head` → `alembic downgrade -3` → `alembic upgrade head` cycle passes
- [ ] `Tenant10DlcProfile` SQLModel class added to `app/models/core.py`
- [ ] `CustomerSmsConsentAudit` SQLModel class added to `app/models/crm.py`
- [ ] `Customer` model updated with 4 new fields + check constraint
- [ ] `python generate_db_model_map.py` run — `db_models_map.md` shows new models
- [ ] `api/schemas/dlc.py` created with `Tenant10DlcProfileRequest` + `Tenant10DlcProfileResponse`
- [ ] `api/schemas/customers.py` updated with `sms_attestation_checked` + `sms_consent_ip_address`
- [ ] `api/routes/tenant_10dlc_profile.py` created — GET/PUT + test counterparts
- [ ] `set_audit_context_sync()` called in `put_10dlc_profile()` before DB write
- [ ] All new API errors follow RFC 7807 Problem Details format
- [ ] `customers.py` updated — attestation flow triggers on `sms_attestation_checked=True`
- [ ] `CustomerSmsConsentAudit` row written on attestation with `action='attested'`
- [ ] `send_double_optin_sms.delay()` enqueued on attestation
- [ ] `tasks/sms_compliance.py` created — `_send_double_optin_sms_impl()` + `@celery_app.task` wrapper
- [ ] `tasks.sms_compliance` added to `core/celery_app.py` imports list
- [ ] `tenant_10dlc_profile.router` registered in `app/main.py`
- [ ] `handle_sms_opt_in()` sets `sms_verification_status='verified'` + writes audit row
- [ ] `handle_sms_opt_out()` confirmation text matches DLC spec §2.4 + sets `sms_verification_status='opted_out'`
- [ ] `handle_sms_help()` auto-reply uses tenant business name from `Tenant10DlcProfile`
- [ ] All new test files use `pytestmark` with `domain_notifications_comms` + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All new tests use `test_tenant`/`test_user` fixtures (no hardcoded UUIDs)
- [ ] `send_double_optin_sms.delay` mocked in customer attestation tests
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] `python export_openapi_json.py` run — `openapi.json` + `openapi_schema_map.md` updated
- [ ] `GET /api/v1/settings/10dlc-profile` visible in `openapi_schema_map.md`
- [ ] `PUT /api/v1/settings/10dlc-profile` visible in `openapi_schema_map.md`
- [ ] `python schema_manager.py --diff` shows only DLC-1 additions
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §DLC-1

---

## Handoff Instructions (After This Batch)

1. Run `python export_openapi_json.py` — verify `10dlc-profile` endpoints appear in `openapi_schema_map.md`
2. Commit all changes with message: `feat(dlc-1): 10DLC compliance backend — tenant profile + consent audit + double opt-in`
3. Notify React Engineer: **DLC-1 backend is complete. Run `pnpm sync-api-types` before starting.**
4. React Engineer prompt: `dev-docs/implementation-prompts/fe-be-mob-batch-prompts/batch-dlc-1-react-engr-prompt.md`

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` §DLC-1 using this format:

```markdown
### DLC-1 Backend — 10DLC Compliance Engineering: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y deselected
**Final**: X+N passed, Y deselected (+N new tests)

#### What Was Accomplished
- [...]

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/app/models/core.py` | Updated — Tenant10DlcProfile model added |
| ... | ... |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/notifications_comms/test_dlc1_sms_compliance.py` | `domain_notifications_comms` | N | ✅ |
```
