# Batch C-B2 — Schema: Charter Entitlement Fields + `tenant_messaging_registration` Table

**Batch code**: C-B2
**Design doc owner**: Pilot Architect
**Created**: August 4, 2026
**Status**: ✅ Complete — Python Engineer implementation done 2026-08-04 (see completion summary)
**Plan link**: `pilot-launch-plan.md`
**Batch type**: Backend only (Python Engineer)
**Engineer**: Pilot Python Engineer
**Prerequisite**: C-B1 ✅
**Source of truth**: `pilot-tech-impl-spec-v1.md` §3 (Data Model), §4 (Field Semantics)

---

## Problem Statement

The Commercial Implementation Spec §3 defines 4 new columns on `subscription_tier`, 3 new columns on `tenant`, 1 new column on `tenant_tier_override`, and a new `tenant_messaging_registration` table. These fields implement the Charter program lifecycle: free period tracking, signup cap enforcement, price lock, payment-method gating, and 10DLC provisioning state.

**Critical**: The spec §3.1-3.2 was written against a hypothetical schema. The Architect has verified the real columns via MCP (see §A below) and this design uses the **actual** column names. The spec's `ALTER TABLE` statements must be corrected against the real schema during implementation.

Additionally, the Charter tier's pricing needs updating: C-B1 renamed `founders`→`charter` but left the price at $0. Per GTM §5.2, Charter is $49/mo flat (billed monthly at the annual rate). This batch updates the tier seed data.

---

## A. Input Read Summary

| Input | Section(s) read | What it established |
|---|---|---|
| `pilot-tech-impl-spec-v1.md` | §3.1 (`subscription_tier` cols), §3.2 (tier seed), §3.3 (`tenant` cols), §3.4 (`tenant_tier_override`), §3.5 (`tenant_messaging_registration`), §4 (field semantics) | The 4+3+1 new columns + 1 new table. Field semantics and trigger points for each column. |
| `pilot-gtm-strategy-v3.md` | §5.2 (The Plans table), §6.2 (Program Mechanics) | Charter = $49/mo flat, 90 days free, 5 lanes, 90 Voice AI min, 100 SMS, no card, price locked, cap 12. Trial = 14 days, $0, hard cap, no card. Starter = $49/mo annual / $58.80 monthly, card required. Teams = $149/mo annual / $178.80 monthly, card required. |
| `postgres-local` MCP | `subscription_tier` columns (17 cols) | Real schema: `tier_name` (not `code`), `display_label` (not `display_name`), `annual_price_cents`/`monthly_price_cents` (not `price_cents`), `product_plan_code`, `schedule_lanes`, `trial_duration_days`, `display_order`, `stripe_price_id_monthly/annual`. None of the 4 proposed new columns exist yet. |
| `postgres-local` MCP | `tenant` columns (14 cols) | Real schema: `id` (PK, uuid), `name`, `is_active`, `current_subscription_tier_id` (FK), `trial_started_at`, `trial_ends_at`, `trial_length_days_override`, `stripe_customer_id`, `mfa_grace_period_started_at`, `stripe_connect_account_id`. None of the 3 proposed new columns exist yet. `trial_ends_at` exists but is a different concept from `free_period_ends_at` (trial vs. Charter free period). |
| `postgres-local` MCP | `tenant_tier_override` columns (10 cols) | Real schema: `tenant_id`, `override_tier_id`, `override_trial_length_days`, `override_reason`, `set_by_operator_user_id`, `set_at`. The proposed `override_free_period_ends_at` does not exist yet. |
| `postgres-local` MCP | `tenant_messaging_registration` table | Does NOT exist — safe to create. |
| `postgres-local` MCP | Current tier data (post-C-B1) | `charter` (active, $0 annual/$0 monthly, 5 lanes, `charter_plan`), `trial` (inactive, $0, 14-day, `starter_plan`), `starter` (inactive, $588 annual/$59 monthly, 5 lanes, `starter_plan`), `teams` (inactive, $1788 annual/$179 monthly, 20 lanes, `teams_plan`). Charter price needs updating to $49/mo. |

### Schema drift corrections (spec §3 → real DB)

| Spec §3 says | Real DB column | Correction |
|---|---|---|
| `ALTER TABLE subscription_tier ADD COLUMN ...` | 17 existing columns | All 4 new columns are safe to add — none conflict |
| `code` | `tier_name` | Spec's seed data table uses `code` — must use `tier_name` |
| `display_name` | `display_label` | Spec's seed data table uses `display_name` — must use `display_label` |
| `price_cents` | `annual_price_cents` + `monthly_price_cents` | Spec's seed data table uses `price_cents` — must use the two real columns |
| `ALTER TABLE tenant ADD COLUMN ...` | 14 existing columns | All 3 new columns are safe to add — `trial_ends_at` exists but is a different concept |
| `ALTER TABLE tenant_tier_override ADD COLUMN ...` | 10 existing columns | The 1 new column is safe to add |

---

## B. Migration Plan

### B.1 — DB changes

One new Alembic migration (blank, raw `op.execute()`). This is a DDL migration (new columns + new table) plus a data UPDATE (tier pricing).

**Pre-migration state** (verified via MCP 2026-08-04):
- `subscription_tier`: 4 rows — `charter` (active, $0/$0), `trial` (inactive, $0, 14-day), `starter` (inactive, $588/$59), `teams` (inactive, $1788/$179)
- `tenant`: 14 columns, no `free_period_ends_at`/`charter_member_number`/`charter_eligible`
- `tenant_tier_override`: 10 columns, no `override_free_period_ends_at`
- `tenant_messaging_registration`: does not exist

**Migration SQL** (all column names verified via MCP):

```sql
-- ═══════════════════════════════════════════════════════════════
-- Part 1: New columns on subscription_tier (4 cols)
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE public.subscription_tier
  ADD COLUMN free_period_days INTEGER,
  ADD COLUMN requires_payment_method BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN signup_cap INTEGER,
  ADD COLUMN price_locked BOOLEAN NOT NULL DEFAULT FALSE;

-- ═══════════════════════════════════════════════════════════════
-- Part 2: New columns on tenant (3 cols)
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE public.tenant
  ADD COLUMN free_period_ends_at TIMESTAMPTZ,
  ADD COLUMN charter_member_number INTEGER,
  ADD COLUMN charter_eligible BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX ix_tenant_free_period_ends_at
  ON public.tenant (free_period_ends_at)
  WHERE free_period_ends_at IS NOT NULL;

CREATE UNIQUE INDEX ix_tenant_charter_member_number
  ON public.tenant (charter_member_number)
  WHERE charter_member_number IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════
-- Part 3: New column on tenant_tier_override (1 col)
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE public.tenant_tier_override
  ADD COLUMN override_free_period_ends_at TIMESTAMPTZ;

-- ═══════════════════════════════════════════════════════════════
-- Part 4: New table — tenant_messaging_registration
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE public.tenant_messaging_registration (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id               UUID NOT NULL REFERENCES public.tenant(id),
  entity_type             TEXT NOT NULL,
  status                  TEXT NOT NULL,
  telnyx_brand_id         TEXT,
  telnyx_campaign_id      TEXT,
  telnyx_phone_number     TEXT,
  quoted_setup_cents      INTEGER,
  quoted_monthly_cents    INTEGER,
  stripe_checkout_id      TEXT,
  stripe_payment_intent   TEXT,
  otp_requested_at        TIMESTAMPTZ,
  otp_verified_at         TIMESTAMPTZ,
  failure_reason          TEXT,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by              UUID,
  updated_by              UUID,
  CONSTRAINT uq_tenant_messaging_registration_tenant UNIQUE (tenant_id)
);

-- ═══════════════════════════════════════════════════════════════
-- Part 5: Update tier seed data (Charter pricing + new fields)
-- ═══════════════════════════════════════════════════════════════
SET LOCAL session_replication_role = replica;

-- Charter: $49/mo flat (annual rate billed monthly), 90 days free, no card, cap 12, price locked
UPDATE public.subscription_tier SET
  monthly_price_cents = 4900,
  annual_price_cents = 58800,
  free_period_days = 90,
  requires_payment_method = FALSE,
  signup_cap = 12,
  price_locked = TRUE
WHERE tier_name = 'charter';

-- Trial: 14 days, $0, no card, no cap, not locked, hard cap (no overages)
UPDATE public.subscription_tier SET
  free_period_days = 14,
  requires_payment_method = FALSE,
  signup_cap = NULL,
  price_locked = FALSE
WHERE tier_name = 'trial';

-- Starter: no free period, card required, no cap, not locked
UPDATE public.subscription_tier SET
  free_period_days = NULL,
  requires_payment_method = TRUE,
  signup_cap = NULL,
  price_locked = FALSE
WHERE tier_name = 'starter';

-- Teams: no free period, card required, no cap, not locked
UPDATE public.subscription_tier SET
  free_period_days = NULL,
  requires_payment_method = TRUE,
  signup_cap = NULL,
  price_locked = FALSE
WHERE tier_name = 'teams';

SET LOCAL session_replication_role = origin;
```

**Downgrade**: Reverse all changes — drop the new table, drop the new columns, restore the old tier pricing (`charter` back to $0/$0).

### B.2 — MCP verification queries (pre-work for Python Engineer)

Before running the migration, verify:
```sql
SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'subscription_tier' AND column_name IN ('free_period_days', 'requires_payment_method', 'signup_cap', 'price_locked');
-- Should return 0 rows (columns don't exist yet)

SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'tenant' AND column_name IN ('free_period_ends_at', 'charter_member_number', 'charter_eligible');
-- Should return 0 rows

SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tenant_messaging_registration';
-- Should return 0 rows
```

After the migration, verify:
```sql
SELECT tier_name, monthly_price_cents, annual_price_cents, free_period_days, requires_payment_method, signup_cap, price_locked FROM subscription_tier ORDER BY display_order;
-- Should show charter with $49/mo, $588 annual, 90 days, false, 12, true
```

### B.3 — 3-Part NOT NULL pattern

The spec's `requires_payment_method` and `price_locked` are `NOT NULL DEFAULT ...` — they can be added in a single `ALTER TABLE` because they have defaults. No 3-part pattern needed (no backfill required — the DEFAULT applies to all existing rows immediately).

`free_period_ends_at`, `charter_member_number`, `override_free_period_ends_at` are nullable — no backfill needed.

`charter_eligible` is `NOT NULL DEFAULT TRUE` — single `ALTER TABLE` is safe.

---

## C. Execution Order

| Step | Task | Files |
|---|---|---|
| 1 | Create Alembic migration (DDL + data UPDATE per §B.1) | `backend/migrations/versions/2026_08_04_XXXX-XXXX_c_b2_charter_schema.py` |
| 2 | Add SQLModel fields to `subscription_tier` model | `backend/app/models/subscription.py` — add `free_period_days`, `requires_payment_method`, `signup_cap`, `price_locked` |
| 3 | Add SQLModel fields to `tenant` model | `backend/app/models/tenant.py` — add `free_period_ends_at`, `charter_member_number`, `charter_eligible` |
| 4 | Add SQLModel field to `tenant_tier_override` model | `backend/app/models/...` — add `override_free_period_ends_at` |
| 5 | Create `tenant_messaging_registration` SQLModel | `backend/app/models/messaging.py` (or appropriate domain file) — new model class |
| 6 | Update Pydantic response schemas | `backend/api/schemas/subscription.py` — add new fields to `SubscriptionTierResponse` |
| 7 | Update seed script | `backend/migrations/scripts/seed_platform.py` — add new columns to tier seed dict |
| 8 | Run migration + reseed + tests | `alembic upgrade head` → `python -m migrations.scripts.seed_platform --mode reset` → `pytest -m unit` |
| 9 | Regenerate `db_models_map.md` | `python generate_db_model_map.py app > db_models_map.md` |
| 10 | Update JSON schema | `schema_manager.py` — add new columns + new table to `pilot-db-schema-v2.6h.json` |
| 11 | Regenerate OpenAPI | `python export_openapi_json.py` — new fields in `SubscriptionTierResponse` |
| 12 | Update `README-seed-data.md` | Add new columns to the tier table description |

---

## D. New API Endpoints

**None.** This batch adds schema fields but does not add new endpoints. The existing `GET /api/v1/subscription-tiers` endpoint will return the new fields in its response (the Pydantic schema is updated in Step 6). No new routes are created.

---

## E. Pattern Reuse Decisions

| Pattern | How it applies |
|---|---|
| **StandardAuditMixin** | The new `tenant_messaging_registration` table inherits `StandardAuditMixin` — which provides **all four** audit columns: `created_at`, `updated_at`, `created_by`, `updated_by`. The raw DDL in §B.1 must include all four (the SQLModel class inherits them automatically, but the migration DDL must match). **Never hand-declare only `created_at`/`updated_at` and omit `created_by`/`updated_by`** — every table in this project has all four (verified via MCP on `subscription_tier`, `tenant`, `tenant_tier_override`). See `backend/app/models/mixins.py` for the mixin definitions and `python-engr-std-prompt-inclusions.md` §1 Rule 15. |
| **Tenant-scoped model** | `tenant_messaging_registration` has `tenant_id` FK to `tenant(id)` — add explicitly (mixins don't provide it) |
| **Unique constraint** | `tenant_messaging_registration` has `UNIQUE (tenant_id)` — one registration per tenant |
| **Partial index** | `ix_tenant_free_period_ends_at` is a partial index (`WHERE free_period_ends_at IS NOT NULL`) — avoids indexing NULLs for non-Charter tenants |
| **Partial unique index** | `ix_tenant_charter_member_number` is a partial unique index (`WHERE charter_member_number IS NOT NULL`) — allows multiple NULLs (non-Charter tenants) while enforcing uniqueness on assigned numbers |

---

## F. Shared Module Interfaces

### F.1 — New SQLModel fields

**`subscription_tier`** (in `backend/app/models/subscription.py`):
```python
free_period_days: int | None = Field(default=None, description="Days at $0 from activation. NULL = no free period.")
requires_payment_method: bool = Field(default=True, description="Whether the signup wizard collects a card.")
signup_cap: int | None = Field(default=None, description="Max tenants that may activate on this tier. NULL = uncapped.")
price_locked: bool = Field(default=False, description="Excludes this tier from future price-migration jobs.")
```

**`tenant`** (in `backend/app/models/tenant.py`):
```python
free_period_ends_at: datetime | None = Field(default=None, description="App source of truth for free period end. Stripe trial_end mirrors this.")
charter_member_number: int | None = Field(default=None, description="1..12, NULL for non-Charter tenants.")
charter_eligible: bool = Field(default=True, description="Flips false permanently on cancellation or Teams upgrade.")
```

**`tenant_tier_override`**:
```python
override_free_period_ends_at: datetime | None = Field(default=None, description="Operator-set free period extension (case by case; not an advertised offer).")
```

### F.2 — New SQLModel class

**`TenantMessagingRegistration`** (in `backend/app/models/messaging.py` or appropriate domain):
```python
class TenantMessagingRegistration(StandardAuditMixin, table=True):
    __tablename__ = "tenant_messaging_registration"
    id: uuid.UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    entity_type: str = Field(nullable=False)  # 'sole_proprietor' | 'standard'
    status: str = Field(nullable=False)  # see state machine, spec §5.2
    telnyx_brand_id: str | None = Field(default=None)
    telnyx_campaign_id: str | None = Field(default=None)
    telnyx_phone_number: str | None = Field(default=None)
    quoted_setup_cents: int | None = Field(default=None)
    quoted_monthly_cents: int | None = Field(default=None)
    stripe_checkout_id: str | None = Field(default=None)
    stripe_payment_intent: str | None = Field(default=None)
    otp_requested_at: datetime | None = Field(default=None)
    otp_verified_at: datetime | None = Field(default=None)
    failure_reason: str | None = Field(default=None)
```

### F.3 — Pydantic schema update

**`SubscriptionTierResponse`** (in `backend/api/schemas/subscription.py`):
Add the 4 new fields to the response model so the frontend can consume them:
```python
free_period_days: int | None
requires_payment_method: bool
signup_cap: int | None
price_locked: bool
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Should `charter_member_number` be a column or a separate table? | **Column on `tenant`** — per spec §3.3. It's a simple 1..12 integer with a partial unique index. A separate table is over-engineering for 12 rows. |
| Should `free_period_ends_at` replace the existing `trial_ends_at`? | **No** — they are different concepts. `trial_ends_at` tracks the 14-day Trial tier period. `free_period_ends_at` tracks the 90-day Charter free period. A tenant is on one or the other, never both. Keeping them separate avoids conflating two different lifecycle concepts. |
| Should the `tenant_messaging_registration` table use `StandardAuditMixin` or `MachineLogMixin`? | **StandardAuditMixin** — it's a state-tracked entity that an operator may need to audit (who created it, when it was last updated). `MachineLogMixin` is for pure machine-generated logs (webhook deliveries, etc.). |
| What domain folder should the new model live in? | **`backend/app/models/messaging.py`** if it exists, or the appropriate domain. The Python Engineer should check existing model files for the right location. |
| Should the `SubscriptionTierResponse` schema include the new fields? | **Yes** — the frontend needs `requires_payment_method` to decide whether to show the Stripe Elements step in the wizard (spec §4.2, §7.1). The other fields (`free_period_days`, `signup_cap`, `price_locked`) are also useful for the frontend to display. |

---

## H. Surface Mockup Reference

**Not applicable.** This is a backend-only batch — no UI surfaces. The frontend will consume the new API fields in C-B5 (wizard conditional logic).

---

## I. Component Manifest

**Not applicable.** No frontend components in this batch.

---

## Estimate

- **1 Alembic migration** (DDL + data UPDATE): ~1 hour
- **4 SQLModel field additions** + **1 new SQLModel class**: ~1 hour
- **1 Pydantic schema update** + **seed script update** + **README update**: ~30 min
- **JSON schema update** via `schema_manager.py`: ~30 min
- **Tests**: ~1 hour (verify migration, verify new fields in API response, verify seed data)
- **Total**: 3–4 hours

---

## Definition of Done

### Phase 1 (unit tests only)

- [ ] Alembic migration created + runs successfully (`alembic upgrade head`)
- [ ] `alembic downgrade -1` + `alembic upgrade head` cycle tested
- [ ] 4 new columns on `subscription_tier` exist (verified via MCP)
- [ ] 3 new columns on `tenant` exist (verified via MCP)
- [ ] 1 new column on `tenant_tier_override` exists
- [ ] `tenant_messaging_registration` table exists with correct columns
- [ ] Charter tier has `monthly_price_cents=4900`, `annual_price_cents=58800`, `free_period_days=90`, `requires_payment_method=FALSE`, `signup_cap=12`, `price_locked=TRUE`
- [ ] Trial tier has `free_period_days=14`, `requires_payment_method=FALSE`
- [ ] Starter/Teams tiers have `requires_payment_method=TRUE`, `free_period_days=NULL`
- [ ] SQLModel classes updated with new fields
- [ ] `SubscriptionTierResponse` Pydantic schema includes 4 new fields
- [ ] `pytest -m unit --tb=no -q` passes with 0 failures

### Phase 2 (full suite)

- [ ] `db_models_map.md` regenerated
- [ ] `pilot-db-schema-v2.6h.json` updated via `schema_manager.py`
- [ ] `openapi.json` + `openapi_schema_map.md` regenerated
- [ ] `README-seed-data.md` updated with new columns
- [ ] `ruff check --fix && ruff format` on changed files — zero issues
- [ ] Full test suite passes (`pytest`) — zero failures
- [ ] `GET /api/v1/subscription-tiers/test` returns new fields in response

---

*End of batch design. Engineer prompt will be authored as `batch-c-b2-python-engr-prompt.md` after Tom approval.*
