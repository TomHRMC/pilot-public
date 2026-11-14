# C-B8 — Telnyx Quoting Adapter + `carrier_fee_schedule` Config Table

**Batch**: C-B8
**Mode**: Pilot Python Engineer
**Prerequisite**: C-B2 ✅ (`tenant_messaging_registration` table with `quoted_setup_cents`, `quoted_monthly_cents`)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §5.1-5.5, Q#1 resolution
**Status**: ✅ Implementation complete 2026-08-05 (migration `025ac61ea0a6`, +6 unit tests, 4338→4344 passed)
**Date**: August 5, 2026

---

## Overview

C-B8 builds the Telnyx 10DLC cost quoting adapter and the `carrier_fee_schedule` operator-maintained config table. Q#1 resolved: Telnyx has **no public API for pre-transaction pricing rates** — only post-transaction cost endpoints (Detail Records API, Usage Reports API). Therefore, carrier fees are stored in a config-backed table that an operator can update without a deploy.

**Secondary task**: Explore the Telnyx brand/campaign registration API to enumerate the exact input fields required for C-B9's brand registration form.

**Backend-only batch** — one migration (new table) + one service + one API endpoint.

---

## A. Input Read Summary

| Input | Sections read | Key takeaways |
|---|---|---|
| `pilot-tech-impl-spec-v1.md` | §5.1 (principles), §5.2 (state machine), §5.3 (entity types), §5.4 (quoting adapter), §5.5 (carrier_fee_schedule) | Charge before provisioning. Quote live, never hardcode. Pass through at cost, zero markup. `get_carrier_quote(entity_type)` returns itemized setup + recurring costs. If Telnyx has no fee-schedule endpoint → config-backed table. |
| Q#1 resolution | Spec appendix | **Operator-maintained.** Telnyx has no public API for pre-transaction pricing. Two endpoints exist for post-transaction costs only (Detail Records API, Usage Reports API). `carrier_fee_schedule` must be operator-maintained. |
| `tenant_messaging_registration` | C-B2 migration | `quoted_setup_cents` (INTEGER), `quoted_monthly_cents` (INTEGER) — stores the quote at checkout time. `status` (TEXT) — state machine. `stripe_checkout_id` (TEXT). |
| `tenant_10dlc_profile` | DLC-1 migration | `legal_business_name`, `dba_name`, `ein`, `entity_type` (already exists for brand registration data). |
| `telnyx_sms_carrier.py` | Full file | Telnyx v2 SDK adapter. All Telnyx SDK calls confined to this class. Lazy import. |
| `sms_carrier.py` | Full file | `SmsCarrier` ABC + `MockSmsCarrier` + `get_sms_carrier()` factory. |
| Live DB — `tenant_messaging_registration` | MCP (C-B4 session) | 18 columns incl. `quoted_setup_cents`, `quoted_monthly_cents`, `status`, `entity_type`. |

---

## B. Migration Plan

**One migration required** — create `carrier_fee_schedule` config table.

### Migration: Create `carrier_fee_schedule`

```sql
CREATE TABLE carrier_fee_schedule (
    id              UUID        NOT NULL DEFAULT gen_random_uuid(),
    fee_code        TEXT        NOT NULL,        -- e.g. 'brand_registration', 'campaign_registration_3mo', 'phone_number', 'campaign_quarterly'
    entity_type     TEXT        NOT NULL,        -- 'standard' | 'sole_proprietor'
    amount_cents    INTEGER     NOT NULL,        -- cost in cents
    description     TEXT        NOT NULL,        -- human-readable label for Stripe Checkout line item
    is_active       BOOLEAN     NOT NULL DEFAULT true,
    -- Audit mixin (all 4 columns)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
    updated_by      UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
    CONSTRAINT pk_carrier_fee_schedule PRIMARY KEY (id),
    CONSTRAINT uq_carrier_fee_schedule_code_entity UNIQUE (fee_code, entity_type)
);
```

**Seed data** (initial carrier fees — operator can update without deploy):

| fee_code | entity_type | amount_cents | description |
|---|---|---|---|
| `brand_registration` | `standard` | 400 | Brand registration |
| `brand_registration` | `sole_proprietor` | 400 | Brand registration |
| `campaign_registration_3mo` | `standard` | 1500 | Campaign registration (3 months prepaid) |
| `campaign_registration_3mo` | `sole_proprietor` | 1000 | Campaign registration (3 months prepaid) |
| `phone_number` | `standard` | 100 | Phone number assignment |
| `phone_number` | `sole_proprietor` | 100 | Phone number assignment |
| `campaign_quarterly` | `standard` | 1500 | Campaign quarterly recurring |
| `campaign_quarterly` | `sole_proprietor` | 1000 | Campaign quarterly recurring |

> **Note**: These are initial estimates. Tom will verify against actual Telnyx fees and update the table via the operator API. The table exists so fee changes never require an engineering ticket.

### Seed Data Rollout

- **Layer 1 (core/platform)**: Add `carrier_fee_schedule` seed to `seed_platform.py`. Idempotent (`INSERT ... ON CONFLICT DO NOTHING`).
- **Layer 2 (scenario)**: No scenario seed — carrier fees are platform-level config, not tenant data.

---

## C. Execution Order

| # | Task | File(s) |
|---|---|---|
| 1 | Alembic migration: create `carrier_fee_schedule` table + seed initial fee rows | `backend/migrations/versions/` |
| 2 | Create `CarrierFeeSchedule` SQLModel in `app/models/billing.py` (or `app/models/sms.py`) | `backend/app/models/` |
| 3 | Create `services/telnyx_quoting.py` — `get_carrier_quote(entity_type)` reads from `carrier_fee_schedule` | `backend/services/telnyx_quoting.py` |
| 4 | Create API endpoint: `GET /api/v1/tenants/{tenant_id}/messaging/quote` + `/test` twin | `backend/api/routes/` (new file or existing messaging route) |
| 5 | Update `seed_platform.py` with `carrier_fee_schedule` seed rows | `backend/migrations/scripts/seed_platform.py` |
| 6 | Write unit tests for quoting service + endpoint | `backend/tests/domains/subscriptions_usage/` |
| 7 | Run `python export_openapi_json.py` + `python generate_db_model_map.py app > db_models_map.md` | — |
| 8 | Run ruff + full test suite (Phase 2) | — |

---

## D. New API Endpoints

### GET /api/v1/tenants/{tenant_id}/messaging/quote

Returns the itemized 10DLC carrier cost quote for the tenant's entity type.

| Field | Value |
|---|---|
| **Path** | `/api/v1/tenants/{tenant_id}/messaging/quote` |
| **Method** | GET |
| **Auth** | `require_permission("settings.view")` |
| **Response** | `CarrierQuoteResponse` (see below) |
| **Test twin** | `GET /api/v1/tenants/{tenant_id}/messaging/quote/test` |

```python
class CarrierQuoteLineItem(BaseModel):
    fee_code: str        # e.g. "brand_registration"
    description: str     # e.g. "Brand registration"
    amount_cents: int    # e.g. 400

class CarrierQuoteResponse(BaseModel):
    entity_type: str     # "standard" | "sole_proprietor"
    setup_total_cents: int   # sum of one-time fees
    recurring_monthly_cents: int  # sum of recurring fees (monthly equivalent)
    setup_items: list[CarrierQuoteLineItem]
    recurring_items: list[CarrierQuoteLineItem]
```

The endpoint reads the tenant's `entity_type` from `tenant_messaging_registration` (or `tenant_10dlc_profile`), queries `carrier_fee_schedule` for that entity type, and returns the itemized quote.

---

## E. Pattern Reuse Decisions

| Pattern | How it applies |
|---|---|
| **Config-backed table** (spec §5.5) | `carrier_fee_schedule` is operator-maintained — fee changes never require a deploy or engineering ticket. The quoting adapter reads from this table, not from constants. |
| **Pass through at cost** (spec §5.1) | The quote amounts are exactly what the carrier charges — zero markup. The Stripe Checkout line items display these amounts with description "Passed through from the carrier at cost." |
| **Sync routes** (Rule §21) | All new code is `def` — never `async def`. |
| **Audit mixin** (Rule 15) | `carrier_fee_schedule` uses `StandardAuditMixin` — all 4 audit columns. |

---

## F. Shared Module Interfaces

### services/telnyx_quoting.py

```python
"""
C-B8 — Telnyx 10DLC cost quoting adapter.
Reads carrier fees from the operator-maintained carrier_fee_schedule table.
NEVER hardcode fee amounts — carrier fees change (D25).
"""

def get_carrier_quote(db: Session, entity_type: str) -> dict:
    """
    Returns itemized setup + recurring costs for 10DLC provisioning.

    Args:
        entity_type: "standard" | "sole_proprietor"

    Returns:
        {
            "entity_type": str,
            "setup_total_cents": int,
            "recurring_monthly_cents": int,
            "setup_items": [{"fee_code": str, "description": str, "amount_cents": int}],
            "recurring_items": [{"fee_code": str, "description": str, "amount_cents": int}],
        }
    """
    from app.models.billing import CarrierFeeSchedule  # or wherever the model lives

    # Query active fee rows for this entity type
    fees = db.exec(
        select(CarrierFeeSchedule)
        .where(CarrierFeeSchedule.entity_type == entity_type)
        .where(CarrierFeeSchedule.is_active == True)
    ).all()

    # Classify as setup (one-time) vs recurring
    setup_items = []
    recurring_items = []

    for fee in fees:
        item = {
            "fee_code": fee.fee_code,
            "description": fee.description,
            "amount_cents": fee.amount_cents,
        }
        if "quarterly" in fee.fee_code or "monthly" in fee.fee_code:
            # Convert quarterly to monthly equivalent for display
            if "quarterly" in fee.fee_code:
                item["amount_cents"] = fee.amount_cents // 3
            recurring_items.append(item)
        else:
            setup_items.append(item)

    return {
        "entity_type": entity_type,
        "setup_total_cents": sum(i["amount_cents"] for i in setup_items),
        "recurring_monthly_cents": sum(i["amount_cents"] for i in recurring_items),
        "setup_items": setup_items,
        "recurring_items": recurring_items,
    }
```

### Operator CRUD for carrier_fee_schedule (future — not in this batch)

The operator can update `carrier_fee_schedule` via the existing admin tenant override pattern (similar to `admin_tenants.py` for product feature overrides). This is NOT part of C-B8 — it's a future operator tooling batch. For now, fees are seeded and can be updated via SQL.

---

## G. Open Questions Resolved

| Question | Resolution | Source |
|---|---|---|
| **Q#1: Telnyx fee-schedule API** | **Operator-maintained.** Telnyx has no public API for pre-transaction pricing. `carrier_fee_schedule` config table is operator-maintained. | Spec Q#1 resolution |
| **Initial fee amounts** | Estimates based on spec §5.4 example. Tom will verify against actual Telnyx fees and update the table. | Spec §5.4 |
| **Entity type source** | The tenant's `entity_type` is stored on `tenant_messaging_registration` (C-B2) or `tenant_10dlc_profile` (DLC-1). The quote endpoint reads from whichever is set. | Spec §5.3 |
| **Telnyx brand/campaign registration API fields** | **Research task** — the engineer should search the Telnyx API docs for brand/campaign registration endpoints and document the required input fields. These inform C-B9's brand registration form. Key fields to look for: business legal name, EIN, address, contact phone, website URL, email, stock symbol, use case. | Launch plan C-B8 card |
| **Recurring fee display** | Quarterly fees are converted to monthly equivalent for display (amount // 3). The actual Stripe Checkout charges the full quarterly amount. | Design decision |
