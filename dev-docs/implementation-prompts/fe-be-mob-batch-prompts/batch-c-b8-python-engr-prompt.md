# Implementation Prompt: C-B8 — Telnyx Quoting Adapter + carrier_fee_schedule Config Table

**Mode**: Pilot Python Engineer  
**Batch**: C-B8  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14m  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b8-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: C-B9 (10DLC provisioning — depends on C-B8)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document

Critical rules for this batch:

- **Rule 1**: Never guess column names. Use `postgres-local` MCP to verify.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md`.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py`.
- **Rule 4**: All Alembic migrations must be **blank** migrations. Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 11**: If ANY test fails — fix it before declaring done.
- **Rule 12 (sync)**: All DB-touching code is `def` — never `async def`.
- **Rule 15 (audit mixins)**: New table inherits `StandardAuditMixin` — all 4 audit columns.
- **Rule 16 (verify)**: Query `information_schema.columns` for every table you touch.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

---

## Pre-Work: Run MCP Verification Queries

```sql
-- 1. Verify tenant_messaging_registration columns (entity_type, quoted_setup_cents, quoted_monthly_cents)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_messaging_registration'
ORDER BY ordinal_position;

-- 2. Verify tenant_10dlc_profile columns (entity_type, legal_business_name, ein)
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_10dlc_profile'
ORDER BY ordinal_position;

-- 3. Verify carrier_fee_schedule does NOT exist yet
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'carrier_fee_schedule';

-- 4. Verify current alembic head
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Read These Source Files

```
backend/services/telnyx_sms_carrier.py        ← why: Telnyx SDK adapter pattern
backend/services/sms_carrier.py               ← why: SmsCarrier ABC + factory
backend/app/models/sms.py                     ← why: TenantMessagingRegistration model (C-B2)
backend/app/models/core.py                    ← why: Tenant10DlcProfile model (DLC-1)
backend/app/models/billing.py                 ← why: where to add CarrierFeeSchedule model
backend/app/models/mixins.py                  ← why: StandardAuditMixin
backend/migrations/scripts/seed_platform.py   ← why: where to add carrier_fee_schedule seed
backend/api/routes/tenant_10dlc_profile.py    ← why: existing 10DLC route pattern
backend/tests/conftest.py                     ← why: available fixtures
backend/db_models_map.md                      ← why: confirm model names
```

---

## Background / Context

C-B8 builds the Telnyx 10DLC cost quoting system. Q#1 resolved: Telnyx has **no public API for pre-transaction pricing** — only post-transaction cost endpoints. Therefore, carrier fees are stored in an operator-maintained `carrier_fee_schedule` config table.

**Key principles (spec §5.1):**
1. **Charge before provisioning** — payment first, then provision, then refund on failure
2. **Quote live, never hardcode** — costs are read from the config table at quote time
3. **Pass through at cost, zero markup** — displayed as itemized lines

**Secondary task**: Research the Telnyx brand/campaign registration API to document the required input fields for C-B9.

---

## Task 1 — Alembic Migration: Create `carrier_fee_schedule` Table + Seed

Create a blank migration:

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "c_b8_create_carrier_fee_schedule"
```

**Migration content:**
1. `SET LOCAL session_replication_role = 'replica'`
2. `CREATE TABLE carrier_fee_schedule` with all columns from design doc §B (including 4 audit columns: `created_at`, `updated_at`, `created_by`, `updated_by`)
3. Create audit trigger (`audit_carrier_fee_schedule_changes`)
4. Create `set_updated_at` trigger
5. Seed initial fee rows (8 rows from design doc §B table)
6. `SET LOCAL session_replication_role = 'origin'`

**Downgrade**: drop triggers + drop table.

**Test the full cycle:**
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current
```

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 2 — Create `CarrierFeeSchedule` SQLModel

Add to `backend/app/models/billing.py` (or `app/models/sms.py` — follow existing placement conventions):

```python
class CarrierFeeSchedule(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "carrier_fee_schedule"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fee_code: str = Field(nullable=False)
    entity_type: str = Field(nullable=False)  # "standard" | "sole_proprietor"
    amount_cents: int = Field(nullable=False)
    description: str = Field(nullable=False)
    is_active: bool = Field(default=True, sa_column=Column(Boolean, server_default=text("true"), nullable=False))
```

Add to `app/models/__init__.py` barrel export if needed.

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 3 — Create `services/telnyx_quoting.py`

Create `backend/services/telnyx_quoting.py` with `get_carrier_quote(db, entity_type)` function from design doc §F.

**Key implementation details:**
- Query `carrier_fee_schedule` where `entity_type = :entity_type` AND `is_active = true`
- Classify fees as setup (one-time) vs recurring (contains "quarterly" or "monthly" in `fee_code`)
- Convert quarterly to monthly equivalent for display (`amount_cents // 3`)
- Return dict with `setup_total_cents`, `recurring_monthly_cents`, `setup_items`, `recurring_items`

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 4 — Create API Endpoint: `GET /messaging/quote`

Create the quote endpoint + `/test` twin. Follow the existing `tenant_10dlc_profile.py` route pattern.

**Route**: `GET /api/v1/tenants/{tenant_id}/messaging/quote` + `/test`

**Logic:**
1. Load tenant's `entity_type` from `tenant_messaging_registration` (or `tenant_10dlc_profile` if messaging registration doesn't have it yet)
2. Call `get_carrier_quote(db, entity_type)`
3. Return `CarrierQuoteResponse`

**RBAC**: `require_permission("settings.view")` for authenticated route; `get_test_context()` for `/test`.

**Schemas**: `CarrierQuoteLineItem` + `CarrierQuoteResponse` (from design doc §D).

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 5 — Update `seed_platform.py`

Add `carrier_fee_schedule` seed block to `backend/migrations/scripts/seed_platform.py`. Follow the existing pattern (idempotent `INSERT ... ON CONFLICT DO NOTHING`). Include all 8 initial fee rows from the design doc.

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 6 — Research Telnyx Brand/Campaign Registration API

**Research task** (no code — documentation only):

Search the Telnyx API docs for brand and campaign registration endpoints. Document the required input fields for:
- Brand registration: business legal name, EIN, address, contact phone, website URL, email, stock symbol, use case
- Campaign registration: campaign name, use case, sample messages, opt-in keywords, opt-out keywords

Add findings as a comment block at the top of `services/telnyx_quoting.py` or in a separate research note. These fields inform C-B9's brand registration form design.

**Key Telnyx API endpoints to research:**
- `POST /v2/10dlc/brands` — brand registration
- `POST /v2/10dlc/campaigns` — campaign registration
- `GET /v2/10dlc/brands` — list brands
- `GET /v2/10dlc/campaigns` — list campaigns

Use web search if needed to find the Telnyx API reference.

---

## Task 7 — Write Tests

**Domain folder**: `backend/tests/domains/subscriptions_usage/`

**Test file**: `test_cb8_carrier_quote.py`

| Test | Description |
|---|---|
| 1 | `get_carrier_quote()` returns setup + recurring items for `standard` entity type |
| 2 | `get_carrier_quote()` returns setup + recurring items for `sole_proprietor` entity type |
| 3 | `get_carrier_quote()` returns correct `setup_total_cents` (sum of one-time fees) |
| 4 | `get_carrier_quote()` converts quarterly to monthly equivalent |
| 5 | `GET /messaging/quote/test` returns 200 with quote data |
| 6 | `GET /messaging/quote/test` returns 404 when no entity_type set |

**Mocking**: Use `db_session` fixture with direct inserts into `carrier_fee_schedule`.

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 8 — Regenerate OpenAPI + Model Map

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
python generate_db_model_map.py app > db_models_map.md
```

---

## Final Verification Gate

### Phase 1 — Unit Tests
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Ruff + Full Suite
```bash
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi
python -m pytest --tb=short -q 2>&1 | tail -10
```

---

## Definition of Done

- [ ] Alembic migration created + tested (upgrade/downgrade/upgrade cycle)
- [ ] `CarrierFeeSchedule` model created with `StandardAuditMixin`
- [ ] `services/telnyx_quoting.py` created — `get_carrier_quote()` reads from config table
- [ ] `GET /messaging/quote` + `/test` endpoint created
- [ ] `seed_platform.py` updated with `carrier_fee_schedule` seed rows
- [ ] Telnyx brand/campaign registration API fields documented (research task)
- [ ] 6 unit tests pass
- [ ] `python export_openapi_json.py` + `python generate_db_model_map.py app > db_models_map.md` run
- [ ] Ruff clean on all changed files
- [ ] Full test suite passes

---

## Completion Summary

When done, append a completion summary to `dev-docs/analysis/pilot-launch-plan.md` Appendix B. Also add a one-row entry to Appendix A and mark C-B8 as ✅ in §2.0.

**Important**: Include the Telnyx brand/campaign registration API field research findings in the completion summary — C-B9 depends on this.
