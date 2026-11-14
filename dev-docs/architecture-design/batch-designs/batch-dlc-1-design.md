# Batch DLC-1 Design — 10DLC Compliance Engineering

**Batch code**: DLC-1  
**Date**: 2026-07-05  
**Architect**: Pilot Architect  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P1 — 10DLC Compliance Engineering  
**DLC spec**: `dev-docs/analysis/pilot-dlc-tasks-for-registration.md`  
**Status**: READY FOR IMPLEMENTATION  
**Engineers**: Python Engineer (Part A — runs first) → React Engineer (Part B)

---

## A. Input Read Summary

| Input | File | Key Finding |
|---|---|---|
| DLC spec | `dev-docs/analysis/pilot-dlc-tasks-for-registration.md` | Defines 4 engineering items: tenant business profile, offline consent attestation UI, double opt-in flow, keyword handler expansion |
| `customer` table (MCP) | Live DB | Has `sms_opted_out`, `sms_opt_in_consent`, `sms_opt_in_at`, `sms_opt_in_source` — **NO** attestation audit columns; constraint `sms_opt_in_source IN ('explicit_checkbox','inbound_initiated','verbal_captured')` already present |
| `tenant` table (MCP) | Live DB | Has `id, name, is_active, current_subscription_tier_id, trial_started_at, trial_ends_at, stripe_customer_id, mfa_grace_period_started_at` — **NO** 10DLC business profile fields |
| Existing keyword handlers | `backend/api/routes/webhooks_sms.py` | `_STOP_KEYWORDS`, `_OPTIN_KEYWORDS`, `_HELP_KEYWORDS` already defined and routing correctly. `handle_sms_opt_out()`, `handle_sms_opt_in()`, `handle_sms_help()` exist in `customer_communication_threading.py` |
| SMS threading service | `backend/services/customer_communication_threading.py` | `handle_sms_opt_out()` sets `sms_opted_out=True`; `handle_sms_opt_in()` sets `sms_opt_in_consent=True`. HELP handler exists. Need to verify confirmation message text matches DLC spec. |
| Existing SMS carrier | `backend/services/telnyx_sms_carrier.py` | Telnyx v2 SDK. `send_message(from_number, to_number, body)` is the outbound send method. |
| Alembic head | MCP `alembic_version` | `9b3f7ea49606` (MKT-B9 — waitlist state/notes) |
| No existing consent audit table | MCP search | Zero rows for any `sms_consent_audit`, `tenant_10dlc_profile`, or similar table |
| `TenantEmailBranding` pattern | `backend/app/models/core.py` | PK = `tenant_id`, single-row-per-tenant upsert — canonical pattern for tenant profile tables |
| CRM `Customer` model | `backend/app/models/crm.py` | `sms_opt_in_source` has DB check constraint with valid values including `'explicit_checkbox'` |

---

## B. Migration Plan

### Pre-migration DB state (MCP-verified)
- `tenant` table: 13 columns — no `10dlc` or business profile fields
- `customer` table: 26 columns — existing SMS consent fields: `sms_opted_out`, `sms_opt_out_at`, `sms_opt_in_consent`, `sms_opt_in_at`, `sms_opt_in_source`
- No `tenant_10dlc_profile` table exists
- No `customer_sms_consent_audit` table exists
- Alembic head: `9b3f7ea49606`

### Migration 1 — `tenant_10dlc_profile` table (new table)

```sql
-- upgrade()
CREATE TABLE tenant_10dlc_profile (
    created_at       TIMESTAMPTZ NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL,
    created_by       UUID REFERENCES "user"(id) ON DELETE RESTRICT,
    updated_by       UUID REFERENCES "user"(id) ON DELETE RESTRICT,
    tenant_id        UUID PRIMARY KEY REFERENCES tenant(id) ON DELETE RESTRICT,
    legal_business_name TEXT NOT NULL,
    dba_name         TEXT,
    ein              TEXT,            -- stored encrypted application-side; nullable (may not have yet)
    hq_address_line1 TEXT,
    hq_address_line2 TEXT,
    hq_city          TEXT,
    hq_state         TEXT,            -- 2-char state code
    hq_postal_code   TEXT,
    hq_country       TEXT NOT NULL DEFAULT 'US',
    support_email    TEXT,
    support_phone    TEXT             -- E.164
);
CREATE TRIGGER set_updated_at_tenant_10dlc_profile
    BEFORE UPDATE ON tenant_10dlc_profile
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

> **EIN storage note**: EIN is stored as plain TEXT in this MVP. Encryption with `core.encryption` is deferred to P2 — EIN is accessed only by the tenant owner who enters it, not shared externally.

### Migration 2 — `customer` new columns

Add 3 new nullable columns — **3-part pattern NOT required** (all nullable, no NOT NULL addition):

```sql
-- upgrade()
ALTER TABLE customer ADD COLUMN sms_consent_attested_by UUID REFERENCES "user"(id) ON DELETE RESTRICT;
ALTER TABLE customer ADD COLUMN sms_consent_attested_at TIMESTAMPTZ;
ALTER TABLE customer ADD COLUMN sms_consent_ip_address  TEXT;
ALTER TABLE customer ADD COLUMN sms_verification_status TEXT
    DEFAULT 'unverified'
    CHECK (sms_verification_status IN ('unverified','pending_verification','verified','opted_out'));
```

> **`sms_verification_status`** tracks double opt-in state separately from the existing `sms_opt_in_consent` boolean (which is preserved for backward compat). On attestation: `pending_verification`. On YES reply: `verified`. On STOP: `opted_out`.

### Migration 3 — `customer_sms_consent_audit` table (new append-only table)

```sql
-- upgrade()
CREATE TABLE customer_sms_consent_audit (
    id               UUID PRIMARY KEY,
    created_at       TIMESTAMPTZ NOT NULL,
    tenant_id        UUID NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
    customer_id      UUID NOT NULL REFERENCES customer(id) ON DELETE RESTRICT,
    attested_by      UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
    ip_address       TEXT NOT NULL,
    attested_at      TIMESTAMPTZ NOT NULL,
    consent_text_hash TEXT NOT NULL,   -- SHA-256 of the legal text shown; proves which version was accepted
    action           TEXT NOT NULL     -- 'attested' | 'double_opt_in_sent' | 'double_opt_in_confirmed' | 'opted_out'
    CHECK (action IN ('attested','double_opt_in_sent','double_opt_in_confirmed','opted_out'))
);
CREATE INDEX idx_customer_sms_consent_audit_customer ON customer_sms_consent_audit(customer_id);
CREATE INDEX idx_customer_sms_consent_audit_tenant ON customer_sms_consent_audit(tenant_id);
```

> **AppendOnly** — no `updated_at`, no `updated_by`. Audit rows are never mutated.

### Migration order and naming

| # | Migration name | Alembic parent |
|---|---|---|
| 1 | `dlc1_create_tenant_10dlc_profile` | `9b3f7ea49606` |
| 2 | `dlc1_add_customer_sms_consent_columns` | migration 1 rev |
| 3 | `dlc1_create_customer_sms_consent_audit` | migration 2 rev |

All three are chained. Run `alembic upgrade head` once to apply all three.

---

## C. Execution Order

| Step | Engineer | What | File(s) |
|---|---|---|---|
| 1 | Python | Migration 1: `tenant_10dlc_profile` table | new migration file |
| 2 | Python | Migration 2: 4 new columns on `customer` | new migration file |
| 3 | Python | Migration 3: `customer_sms_consent_audit` table | new migration file |
| 4 | Python | `Tenant10DlcProfile` SQLModel | `app/models/core.py` |
| 5 | Python | `CustomerSmsConsentAudit` SQLModel (AppendOnly) | `app/models/crm.py` |
| 6 | Python | Update `Customer` model with 4 new fields + updated check constraint | `app/models/crm.py` |
| 7 | Python | Pydantic schemas: `Tenant10DlcProfileRequest/Response` | `api/schemas/settings.py` (or new `api/schemas/dlc.py`) |
| 8 | Python | Pydantic schemas: update `CustomerCreate`/`CustomerUpdate` with `sms_attestation_checked`, `sms_consent_ip_address` | `api/schemas/customers.py` |
| 9 | Python | New route file `api/routes/tenant_10dlc_profile.py` — GET/PUT `/api/v1/settings/10dlc-profile` | new file |
| 10 | Python | Update `create_customer` + `update_customer` to write consent audit on attestation | `api/routes/customers.py` |
| 11 | Python | New Celery task `send_double_optin_sms` in `tasks/sms_compliance.py` | new file |
| 12 | Python | Update `handle_sms_opt_in()` to set `sms_verification_status='verified'` and write audit row | `services/customer_communication_threading.py` |
| 13 | Python | Verify/update confirmation message text in `handle_sms_opt_out()` and `handle_sms_help()` | `services/customer_communication_threading.py` |
| 14 | Python | Register new route + task in `app/main.py` + `core/celery_app.py` | both files |
| 15 | Python | Tests (8–10 unit tests) | `tests/domains/notifications_comms/` |
| 16 | Python | `python export_openapi_json.py` → handoff to React Engineer | — |
| 17 | React | `pnpm sync-api-types` | — |
| 18 | React | Add `Tenant10DlcProfileForm` component + settings page | `apps/web/src/features/settings/` |
| 19 | React | Add attestation checkbox to `CreateCustomerForm` + `EditCustomerForm` | `apps/web/src/features/crm/` |
| 20 | React | MSW handlers for new endpoints | `apps/web/src/mocks/handlers/` |
| 21 | React | Unit + integration tests | `apps/web/src/__tests__/batch_dlc_1/` |

---

## D. New API Endpoints

### D1. GET `/api/v1/settings/10dlc-profile`

| Field | Value |
|---|---|
| Method | GET |
| Path | `/api/v1/settings/10dlc-profile` |
| Auth | JWT required |
| RBAC | `require_permission("settings.view")` |
| Response 200 | `Tenant10DlcProfileResponse` (all fields; `ein` masked to last 4 if present: `"**-***XXXX"`) |
| Response 404 | RFC 7807 — profile not yet configured |

```python
class Tenant10DlcProfileResponse(BaseModel):
    tenant_id: UUID
    legal_business_name: str | None
    dba_name: str | None
    ein_masked: str | None          # "**-***1234" or None
    hq_address_line1: str | None
    hq_address_line2: str | None
    hq_city: str | None
    hq_state: str | None
    hq_postal_code: str | None
    hq_country: str
    support_email: str | None
    support_phone: str | None
    updated_at: datetime | None
```

### D2. PUT `/api/v1/settings/10dlc-profile`

| Field | Value |
|---|---|
| Method | PUT |
| Path | `/api/v1/settings/10dlc-profile` |
| Auth | JWT required |
| RBAC | `require_permission("settings.manage")` |
| Idempotency | Natural key: `tenant_id` — upsert pattern |
| Request | `Tenant10DlcProfileRequest` |
| Response 200 | `Tenant10DlcProfileResponse` |
| Audit | `set_audit_context_sync()` required |

```python
class Tenant10DlcProfileRequest(BaseModel):
    legal_business_name: str                    # required
    dba_name: str | None = None
    ein: str | None = None                      # raw EIN from form (stored as-is, MVP)
    hq_address_line1: str | None = None
    hq_address_line2: str | None = None
    hq_city: str | None = None
    hq_state: str | None = None                 # 2-char e.g. "CO"
    hq_postal_code: str | None = None
    hq_country: str = "US"
    support_email: str | None = None
    support_phone: str | None = None            # E.164 preferred, not enforced at MVP
```

### D3. GET/PUT `/api/v1/settings/10dlc-profile/test`

Unauthenticated test counterparts (same pattern as every settings route). GET returns the profile for `test_tenant`; PUT upserts it.

### D4. Customer mutation — attestation fields added to existing schemas

**No new endpoints** — the attestation data flows through the existing:
- `POST /api/v1/customers/` (`CustomerCreate` gains `sms_attestation_checked: bool = False`, `sms_consent_ip_address: str | None = None`)
- `PATCH /api/v1/customers/{id}` (`CustomerUpdate` gains same two fields)
- `POST /api/v1/customers/test` / `PATCH /api/v1/customers/{id}/test`

When `mobile_phone` is provided AND `sms_attestation_checked=True`:
1. Set `customer.sms_opt_in_source = 'explicit_checkbox'`
2. Set `customer.sms_consent_attested_by = current_user.id`
3. Set `customer.sms_consent_attested_at = utcnow()`
4. Set `customer.sms_consent_ip_address = ip_address` (from request)
5. Set `customer.sms_verification_status = 'pending_verification'`
6. Write `CustomerSmsConsentAudit` row with `action='attested'`
7. Enqueue `send_double_optin_sms.delay(customer_id=..., tenant_id=...)`

When `mobile_phone` is provided WITHOUT `sms_attestation_checked`, **do not** block the save — the checkbox is only mandatory when actually submitting the form with a phone number present. The block-on-submit logic lives in the React frontend (UI validation, not API validation). The API does NOT reject saves without attestation — it simply does not trigger the opt-in flow.

> **Rationale**: Carriers require the UI to enforce attestation, not the API. Making the API reject is over-engineering and breaks test fixtures that create customers with phone numbers for other test scenarios.

---

## E. Pattern Reuse Decisions

| Pattern | `mvp-arch.md` §16 Ref | Application |
|---|---|---|
| Single-row-per-tenant upsert | `TenantEmailBranding` pattern | `Tenant10DlcProfile` GET/PUT |
| Append-only audit table | `AppendOnlyMixin` | `CustomerSmsConsentAudit` |
| Two-layer Celery task | `_impl(param, db) + @celery_app.task` | `send_double_optin_sms` |
| Tenant-scoped `select()` | §7.1 — `db.get()` ban | All customer queries |
| `set_audit_context_sync()` | §10 Audit | All mutation endpoints |
| RFC 7807 errors | §13 | All new endpoints |
| `/test` endpoint pattern | §11 | `10dlc-profile/test` |

---

## F. Shared Module Interfaces

### F1. New Celery task — `tasks/sms_compliance.py`

```python
# tasks/sms_compliance.py

import hashlib
import uuid
from datetime import UTC, datetime

from core.celery_app import celery_app
from core.db import get_db
from sqlmodel import Session, select


DOUBLE_OPTIN_TEXT_VERSION = "v1-2026-07-05"
DOUBLE_OPTIN_TEXT_TEMPLATE = (
    "Hi {first_name}, {business_name} uses Pilot for Trades for service updates. "
    "Reply YES to confirm you want to receive texts. Reply STOP to cancel."
)


def _send_double_optin_sms_impl(customer_id: uuid.UUID, tenant_id: uuid.UUID, db: Session) -> dict:
    """
    1. Load customer + tenant phone number + tenant 10DLC profile
    2. Format opt-in message using tenant business name
    3. Send via SmsCarrier adapter
    4. Write CustomerSmsConsentAudit row with action='double_opt_in_sent'
    Returns {"status": "sent" | "skipped" | "error", ...}
    """
    from app.models.crm import Customer, CustomerSmsConsentAudit
    from app.models.sms import TenantPhoneNumber
    from app.models.core import Tenant10DlcProfile
    from services.sms_carrier import get_sms_carrier

    customer = db.exec(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
            Customer.is_active.is_(True),
        )
    ).first()

    if not customer or not customer.mobile_phone:
        return {"status": "skipped", "reason": "customer_not_found_or_no_phone"}

    if customer.sms_opted_out:
        return {"status": "skipped", "reason": "already_opted_out"}

    # Resolve outbound number
    tenant_phone = db.exec(
        select(TenantPhoneNumber).where(
            TenantPhoneNumber.tenant_id == tenant_id,
            TenantPhoneNumber.status == "active",
        )
    ).first()

    if not tenant_phone:
        return {"status": "error", "reason": "no_active_tenant_phone_number"}

    # Resolve business name from 10DLC profile or fallback
    profile = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == tenant_id)
    ).first()
    business_name = profile.legal_business_name if profile else "your service provider"
    first_name = customer.first_name or "there"

    body = DOUBLE_OPTIN_TEXT_TEMPLATE.format(
        first_name=first_name,
        business_name=business_name,
    )

    carrier = get_sms_carrier()
    result = carrier.send_message(
        from_number=tenant_phone.phone_number,
        to_number=customer.mobile_phone,
        body=body,
    )

    # Write audit row regardless of send result
    consent_hash = hashlib.sha256(body.encode()).hexdigest()
    audit_row = CustomerSmsConsentAudit(
        id=uuid.uuid4(),
        created_at=datetime.now(UTC),
        tenant_id=tenant_id,
        customer_id=customer_id,
        attested_by=customer.sms_consent_attested_by,   # the user who clicked attestation
        ip_address=customer.sms_consent_ip_address or "system",
        attested_at=datetime.now(UTC),
        consent_text_hash=consent_hash,
        action="double_opt_in_sent",
    )
    db.add(audit_row)
    db.commit()

    return {"status": result.status}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_double_optin_sms(self, customer_id: str, tenant_id: str) -> dict:
    """Celery entry point. Retries up to 3 times on retryable errors."""
    with next(get_db()) as db:
        result = _send_double_optin_sms_impl(
            uuid.UUID(customer_id), uuid.UUID(tenant_id), db
        )
        if result.get("status") == "error" and result.get("retryable", False):
            raise self.retry()
        return result
```

### F2. Updated `handle_sms_opt_in()` signature (no signature change, internal update)

```python
# services/customer_communication_threading.py — update handle_sms_opt_in()

def handle_sms_opt_in(db: Session, customer_id: UUID, inbound: InboundMessage) -> None:
    """
    Process START/UNSTOP/YES from a customer.
    Sets sms_opt_in_consent=True, sms_opted_out=False,
    sms_verification_status='verified', writes audit row.
    """
    from app.models.crm import Customer, CustomerSmsConsentAudit
    import uuid, hashlib
    from datetime import UTC, datetime

    customer = db.exec(
        select(Customer).where(Customer.id == customer_id)
    ).first()
    if not customer:
        return

    customer.sms_opt_in_consent = True
    customer.sms_opted_out = False
    customer.sms_opt_in_at = datetime.now(UTC)
    customer.sms_verification_status = "verified"    # ← new field

    audit_row = CustomerSmsConsentAudit(
        id=uuid.uuid4(),
        created_at=datetime.now(UTC),
        tenant_id=customer.tenant_id,
        customer_id=customer.id,
        attested_by=customer.sms_consent_attested_by or customer.id,  # system if no attester
        ip_address="inbound_reply",
        attested_at=datetime.now(UTC),
        consent_text_hash=hashlib.sha256(inbound.body.encode()).hexdigest(),
        action="double_opt_in_confirmed",
    )
    db.add(audit_row)
    db.commit()

    # Send confirmation reply
    _send_opt_in_confirmation(customer, inbound)
```

### F3. Updated confirmation message text (DLC spec §2.4)

Current code in `handle_sms_opt_out()` must send:  
> `"You have been unsubscribed. No more messages will be sent."`

Current code in `handle_sms_help()` must send:  
> `"Pilot for Trades alerts for [Tenant Business Name]. Reply STOP to cancel. Msg&Data rates apply. Contact [Tenant Phone] for help."`

The Python Engineer must read the current confirmation text in `customer_communication_threading.py` and update it if it does not match verbatim. If the HELP handler currently uses a generic message without the tenant's business name, it must be updated to look up the `Tenant10DlcProfile` and the `TenantPhoneNumber` to compose the correct response.

---

## G. Open Questions Resolved

| Question | Decision |
|---|---|
| Should attestation block the API if checkbox not checked? | **No** — UI enforces the block. API does not reject saves without attestation. Makes test fixtures and seed data compatible. |
| Should EIN be encrypted? | **No** at MVP. Tenant owner enters their own EIN; it is not exposed to other users or tenants. Encryption deferred to P2. |
| Should `sms_verification_status` replace or extend `sms_opt_in_consent`? | **Extend** — `sms_opt_in_consent` boolean is preserved for backward compat with existing keyword handler code. `sms_verification_status` is additive. When `verified`, set both `sms_verification_status='verified'` AND `sms_opt_in_consent=True`. |
| Which table does `Tenant10DlcProfile` live in (which model file)? | `app/models/core.py` — alongside `TenantEmailBranding` (same single-row-per-tenant pattern, same file). |
| Where does `CustomerSmsConsentAudit` live? | `app/models/crm.py` — alongside `Customer`. Uses `AppendOnlyMixin` (no `updated_at`, no `updated_by`). |
| RBAC for 10DLC profile? | `settings.view` for GET, `settings.manage` for PUT — same as `TenantEmailBranding`. |
| Which React surfaces are affected? | (1) `/settings` page — new `10dlc-profile` tab/section; (2) Customer create + edit forms — attestation checkbox below `mobile_phone` field. |
| Do we need a new `PermissionKey` in `permissions.ts`? | No — reusing existing `settings.view` and `settings.manage` permission keys. |
| Should the double opt-in SMS be retried on failure? | Yes — Celery task with `max_retries=3`, `default_retry_delay=60s`. Only retries on `retryable=True` from `SendResult`. |
| What if tenant has no 10DLC profile when sending double opt-in? | Fall back to business name `"your service provider"` in the opt-in text. Task does NOT fail — it proceeds with the fallback. |
