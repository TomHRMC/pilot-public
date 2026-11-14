# Implementation Prompt: MOB-B0 — NEC Calculation Backend (API + Persistence)

**Mode**: Pilot Python Engineer
**Batch**: MOB-B0
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v2-impl-plan.md` §8 MOB-B0
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b0-design.md`
**Estimated session**: 1–1.5 days
**Platform**: Backend only (`backend/`)
**Frontend companion**: MOB-B4 (Calcs Tab — depends on this batch being complete)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:
- **`dev-docs/architecture-design/batch-designs/batch-mob-b0-design.md`** — every section (A–H)
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Workflow)

Critical rules for this batch:
- **Rule A**: Never guess table names, column names, or trigger function names. Use MCP queries first.
- **Rule B**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()`.
- **Rule C**: All Alembic migrations must be **blank** (never autogenerate). Raw SQL via `op.execute()`.
- **Rule D**: Read every source file before editing it. Never assume contents.
- **Rule E**: Zero regressions in existing `test_task_1e3_nec_calculations.py` — voice pipeline tests must still pass after `nec_service.py` extraction.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
python -m pytest --tb=no -q 2>&1 | tail -5
```

Record the exact count: `X passed, Y failed` (1 known pre-existing failure: `test_a57_preference_matrix`). Do not proceed if regression count is higher.

---

## Pre-Work: Run MCP Verification Queries

Before writing any code, run these MCP queries:

```sql
-- 1. Confirm nec_calculation_log does NOT exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'nec_calculation_log';

-- 2. Confirm set_updated_at function exists
SELECT proname FROM pg_proc WHERE proname = 'set_updated_at';

-- 3. Confirm guard_created_fields_immutable function exists
SELECT proname FROM pg_proc WHERE proname = 'guard_created_fields_immutable';

-- 4. Check if audit.log_changes function exists (determines whether audit trigger can be added)
SELECT proname FROM pg_proc
WHERE proname = 'log_changes'
AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'audit');
```

**If any expected result is missing, STOP and report.**

---

## Pre-Work: Read These Source Files

```bash
# NEC calculation functions to extract into nec_service.py
# Read the full voltage_drop and conduit_fill handler functions
grep -n "calculate_nec_voltage_drop\|calculate_conduit_fill\|NecVoltageDropArgs\|NecConduitFillArgs\|_AWG_CIRCULAR_MILS\|_normalize_gauge" backend/services/voice_action_router.py

# Understand shared service extraction pattern
cat backend/services/etc_service.py

# Existing field operations models (where NecCalculationLog goes)
cat backend/app/models/field_operations.py

# Model __init__.py to find where to add export
cat backend/app/models/__init__.py

# main.py router registrations (to add nec router)
cat backend/app/main.py

# Idempotency utility (use for dedup pattern)
cat backend/utils/idempotency.py

# Most recent migration (pattern reference)
cat backend/migrations/versions/2026_05_31_2216-5ec7fe1e46d8_seed_communication_template_gap_fill.py

# Existing nec tests (MUST NOT REGRESS)
cat backend/tests/batch_1e/test_task_1e3_nec_calculations.py

# Permission check pattern from jobs.py
head -120 backend/api/routes/jobs.py
```

---

## Context: What This Batch Does

Adds the NEC calculation persistence layer and REST API. This unblocks MOB-B4 (Calcs Tab).

| Item | Change |
|---|---|
| New migration | `nec_calculation_log` table with all triggers |
| New model | `NecCalculationLog` in `app/models/field_operations.py` |
| **New service** | `services/nec_service.py` — extracted from `voice_action_router.py` |
| **Refactor** | `voice_action_router.py` delegates to `nec_service.py` (no logic change) |
| New schemas | `api/schemas/nec.py` |
| New router | `api/routes/nec.py` with 4 endpoints |
| Register router | `app/main.py` |
| New tests | `backend/tests/domains/nec_calculations/test_nec_endpoints.py` |

---

## Step 1: Alembic Migration — `nec_calculation_log`

```bash
cd <repo>/backend
alembic revision -m "mob_b0_nec_calculation_log"
```

Edit the generated file. Use the exact SQL from design doc §B.2. Key requirements:

```python
"""mob_b0_nec_calculation_log

Adds nec_calculation_log table for tracking NEC calculation results.
Unblocks MOB-B4 (Calcs Tab frontend) which requires POST /api/v1/nec/calculate.

Table: nec_calculation_log
  - Tenant-scoped (nec calculations are tenant-specific)
  - Optional job_id linkage (calc may be done outside job context)
  - inputs_json + result_json JSONB for flexible calc-type storage
  - is_offline_calc flag distinguishes client-side vs server-side
  - idempotency_key UUID for offline sync dedup (UNIQUE constraint)
  - Triggers: set_updated_at, guard_created_fields_immutable

Permission: nec.calculate (already in technician role — no new seed needed)

Revision ID: <generated>
Revises: 5ec7fe1e46d8
"""
```

> **Verify `down_revision`** — must equal the revision ID of the LAST migration. Run:
> ```bash
> alembic current 2>&1 | head -5
> ```

**Table creation SQL** (per design doc §B.2):
```sql
CREATE TABLE nec_calculation_log (
    created_at         TIMESTAMPTZ     NOT NULL DEFAULT clock_timestamp(),
    updated_at         TIMESTAMPTZ     NOT NULL DEFAULT clock_timestamp(),
    created_by         UUID            REFERENCES "user"(id) ON DELETE RESTRICT,
    updated_by         UUID            REFERENCES "user"(id) ON DELETE RESTRICT,
    id                 UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID            NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
    user_id            UUID            NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
    job_id             UUID            NULL REFERENCES job(id) ON DELETE SET NULL,
    calc_type          VARCHAR(50)     NOT NULL,
    nec_guide_version  VARCHAR(20)     NOT NULL DEFAULT '2023',
    inputs_json        JSONB           NOT NULL DEFAULT '{}',
    result_json        JSONB           NOT NULL DEFAULT '{}',
    is_offline_calc    BOOLEAN         NOT NULL DEFAULT FALSE,
    idempotency_key    UUID            NULL UNIQUE,
    client_capture_at  TIMESTAMPTZ     NULL,
    CONSTRAINT ck_nec_calc_type CHECK (
        calc_type IN ('voltage_drop', 'conduit_fill', 'ampacity')
    )
);
```

After table, add indexes and triggers (per design doc §B.2).

**Verify migration runs cleanly**:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

---

## Step 2: `NecCalculationLog` SQLModel

**File**: `backend/app/models/field_operations.py`

Read the file first. Add `NecCalculationLog` using `StandardAuditMixin` (same as existing models in that file). Per design doc §B.3.

After adding the model, add it to `backend/app/models/__init__.py` (find the existing import block for field_operations models and add to it).

---

## Step 3: Extract NEC Logic into `nec_service.py`

**File**: `backend/services/nec_service.py` (new)

Read `backend/services/voice_action_router.py` — specifically:
1. `_AWG_CIRCULAR_MILS` lookup dict (L~550–580 approximate — search for it)
2. `_normalize_gauge()` function
3. `NecVoltageDropArgs`, `NecVoltageDropResult` dataclasses (if defined there)
4. `calculate_nec_voltage_drop()` core formula (L609–760 approximate)
5. `calculate_conduit_fill()` core formula (search for it after L760)

Extract the **pure calculation logic** (no DB, no session context updates, no `current_user`) into `nec_service.py`. The service returns a `NecCalcResult` dataclass.

```python
# backend/services/nec_service.py

"""
NEC 2023 Calculation Service

Pure calculation functions for NEC electrical code compliance checks.
Used by:
  - POST /api/v1/nec/calculate (REST endpoint — MOB-B0)
  - voice_action_router.py calculate_nec_voltage_drop handler (existing voice pipeline)

NEC 2023 references:
  - Voltage Drop: NEC 210.19(A)(1) Informational Note 4
  - Conduit Fill: NEC Annex C
  - Ampacity: NEC Table 310.12
"""

from dataclasses import dataclass, field as dc_field

# AWG circular mils lookup (NEC 2023 Chapter 9, Table 8)
_AWG_CIRCULAR_MILS: dict[str, float] = {
    # Copy from voice_action_router.py — do NOT re-invent
}

def _normalize_gauge(wire_gauge: str) -> str:
    # Copy from voice_action_router.py
    ...

@dataclass
class NecCalcResult:
    calc_type: str
    is_compliant: bool
    nec_article: str
    nec_citation: str
    details: dict = dc_field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "calc_type": self.calc_type,
            "is_compliant": self.is_compliant,
            "nec_article": self.nec_article,
            "nec_citation": self.nec_citation,
            **self.details,
        }

def calculate(calc_type: str, inputs: dict) -> NecCalcResult:
    """Route to appropriate NEC formula. Raises ValueError on invalid calc_type."""
    if calc_type == "voltage_drop":
        return _calc_voltage_drop(inputs)
    elif calc_type == "conduit_fill":
        return _calc_conduit_fill(inputs)
    elif calc_type == "ampacity":
        return _calc_ampacity(inputs)
    raise ValueError(f"Unsupported calc_type: {calc_type!r}")

def _calc_voltage_drop(inputs: dict) -> NecCalcResult:
    # Extracted from voice_action_router.calculate_nec_voltage_drop()
    # Same formulas, same AWG table, same 3% compliance check
    ...

def _calc_conduit_fill(inputs: dict) -> NecCalcResult:
    # Extracted from voice_action_router.calculate_conduit_fill()
    ...

def _calc_ampacity(inputs: dict) -> NecCalcResult:
    # NEC Table 310.12 — implement per design doc §G.3
    # Inputs: wire_material, wire_gauge, temp_rating_c, conductor_count, ambient_temp_c
    ...
```

---

## Step 4: Update `voice_action_router.py` to Delegate to `nec_service`

**File**: `backend/services/voice_action_router.py`

After creating `nec_service.py`, update the existing `calculate_nec_voltage_drop()` and `calculate_conduit_fill()` handler functions to call `nec_service.calculate()` instead of duplicating the formula.

**Pattern** (do NOT change the function signature or return shape — voice tests depend on them):

```python
from services import nec_service

async def calculate_nec_voltage_drop(
    entities: dict,
    current_user: AuthenticatedUser | TestUserContext,
    db: Session,
    session: ConversationSession,
) -> dict:
    """
    ... (existing docstring unchanged)
    Now delegates pure formula to nec_service.calculate().
    Session context update logic remains here (voice-specific).
    """
    try:
        result = nec_service.calculate("voltage_drop", entities)
    except ValueError as e:
        return {
            "action": "calculate_voltage_drop",
            "success": False,
            "error": str(e),
            "message": "Please provide valid inputs.",
            "next_prompts": ["Try again with wire specs"],
        }

    # Session context update — voice-specific, stays here
    ctx = ContextWindowSchema.from_jsonb(session.context_window_json)
    ctx.current_technical_context.update({ ... })  # same as before
    ...
```

**Run existing voice NEC tests immediately after this change**:
```bash
cd <repo>/backend
python -m pytest backend/tests/batch_1e/test_task_1e3_nec_calculations.py -v 2>&1 | tail -20
```

**Zero failures required before proceeding.**

---

## Step 5: Create `api/schemas/nec.py`

**File**: `backend/api/schemas/nec.py` (new)

Per design doc §F.2:

```python
# backend/api/schemas/nec.py

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class NecCalculateRequest(BaseModel):
    calc_type: str = Field(..., description="'voltage_drop' | 'conduit_fill' | 'ampacity'")
    inputs: dict = Field(..., description="Inputs — keys depend on calc_type")
    job_id: uuid.UUID | None = None
    idempotency_key: uuid.UUID | None = None


class NecCalculateResponse(BaseModel):
    log_id: uuid.UUID
    calc_type: str
    result: dict              # NecCalcResult.to_dict() output
    nec_guide_version: str
    nec_citation: str


class NecCalcLogCreate(BaseModel):
    """Offline sync endpoint request body."""
    calc_type: str
    inputs: dict
    result: dict
    nec_guide_version: str = "2023"
    is_offline_calc: bool = True
    client_capture_at: datetime | None = None
    idempotency_key: uuid.UUID | None = None
    job_id: uuid.UUID | None = None


class NecCalcLogResponse(BaseModel):
    id: uuid.UUID
    calc_type: str
    nec_guide_version: str
    inputs_json: dict
    result_json: dict
    is_offline_calc: bool
    client_capture_at: datetime | None
    job_id: uuid.UUID | None
    created_at: datetime
```

---

## Step 6: Create `api/routes/nec.py`

**File**: `backend/api/routes/nec.py` (new)

Read `backend/api/routes/jobs.py` first — follow its dual-endpoint pattern exactly.

Key implementation notes:

### `_nec_calculate_impl()`:
```python
def _nec_calculate_impl(
    calc_in: NecCalculateRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> NecCalculateResponse:
    # 1. Check idempotency — if idempotency_key provided and already exists, return existing
    if calc_in.idempotency_key:
        existing = db.exec(
            select(NecCalculationLog)
            .where(NecCalculationLog.idempotency_key == calc_in.idempotency_key)
            .where(NecCalculationLog.tenant_id == user_context.tenant_id)
        ).first()
        if existing:
            result_dict = existing.result_json
            return NecCalculateResponse(
                log_id=existing.id,
                calc_type=existing.calc_type,
                result=result_dict,
                nec_guide_version=existing.nec_guide_version,
                nec_citation=result_dict.get("nec_citation", ""),
            )

    # 2. Run calculation
    try:
        calc_result = nec_service.calculate(calc_in.calc_type, calc_in.inputs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. Save to DB
    log = NecCalculationLog(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        job_id=calc_in.job_id,
        calc_type=calc_in.calc_type,
        nec_guide_version="2023",
        inputs_json=calc_in.inputs,
        result_json=calc_result.to_dict(),
        is_offline_calc=False,
        idempotency_key=calc_in.idempotency_key,
        created_by=user_context.id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return NecCalculateResponse(
        log_id=log.id,
        calc_type=calc_in.calc_type,
        result=calc_result.to_dict(),
        nec_guide_version="2023",
        nec_citation=calc_result.nec_citation,
    )
```

### `_nec_calc_log_create_impl()` (offline sync):
```python
def _nec_calc_log_create_impl(
    log_in: NecCalcLogCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    # Idempotent — if key already saved, return existing log_id with 200
    if log_in.idempotency_key:
        existing = db.exec(
            select(NecCalculationLog)
            .where(NecCalculationLog.idempotency_key == log_in.idempotency_key)
            .where(NecCalculationLog.tenant_id == user_context.tenant_id)
        ).first()
        if existing:
            return {"log_id": existing.id}

    log = NecCalculationLog(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        job_id=log_in.job_id,
        calc_type=log_in.calc_type,
        nec_guide_version=log_in.nec_guide_version,
        inputs_json=log_in.inputs,
        result_json=log_in.result,
        is_offline_calc=True,
        idempotency_key=log_in.idempotency_key,
        client_capture_at=log_in.client_capture_at,
        created_by=user_context.id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"log_id": log.id}
```

### `_list_nec_calc_logs_impl()`:
```python
def _list_nec_calc_logs_impl(
    job_id: UUID | None,
    limit: int,
    offset: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[NecCalcLogResponse]:
    stmt = (
        select(NecCalculationLog)
        .where(NecCalculationLog.tenant_id == user_context.tenant_id)
        .order_by(NecCalculationLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if job_id:
        stmt = stmt.where(NecCalculationLog.job_id == job_id)

    logs = db.exec(stmt).all()
    return [
        NecCalcLogResponse(
            id=log.id,
            calc_type=log.calc_type,
            nec_guide_version=log.nec_guide_version,
            inputs_json=log.inputs_json,
            result_json=log.result_json,
            is_offline_calc=log.is_offline_calc,
            client_capture_at=log.client_capture_at,
            job_id=log.job_id,
            created_at=log.created_at,
        )
        for log in logs
    ]
```

### Authenticated endpoints:
```python
@router.post("/calculate", status_code=201)
async def nec_calculate(
    calc_in: NecCalculateRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("nec.calculate")),
) -> NecCalculateResponse:
    """Calculate NEC value and persist result. RBAC: nec.calculate."""
    return _nec_calculate_impl(calc_in, db, current_user)

@router.post("/calc-logs", status_code=201)
async def create_nec_calc_log(
    log_in: NecCalcLogCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("nec.calculate")),
) -> dict:
    """Save offline calculation result. RBAC: nec.calculate."""
    return _nec_calc_log_create_impl(log_in, db, current_user)

@router.get("/calc-logs")
async def list_nec_calc_logs(
    job_id: UUID | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("nec.calculate")),
) -> list[NecCalcLogResponse]:
    """List NEC calc logs for current tenant. RBAC: nec.calculate."""
    return _list_nec_calc_logs_impl(job_id, limit, offset, db, current_user)
```

### Test (no-auth) endpoints — same `_impl()` functions:
```python
@router.post("/calculate/test", status_code=201)
async def nec_calculate_test(...):
    test_context = get_test_context()
    return _nec_calculate_impl(calc_in, db, test_context)

@router.post("/calc-logs/test", status_code=201)
async def create_nec_calc_log_test(...): ...

@router.get("/calc-logs/test")
async def list_nec_calc_logs_test(...): ...
```

---

## Step 7: Register Router in `app/main.py`

Read `backend/app/main.py` first. Add:

```python
# In imports (alphabetically ordered with other routes):
from api.routes import nec as nec_routes

# In app.include_router calls (find the existing block — add alphabetically):
app.include_router(nec_routes.router, prefix="/api/v1/nec", tags=["nec"])
```

---

## Step 8: Write Tests

**File**: `backend/tests/domains/nec_calculations/test_nec_endpoints.py`

Create `backend/tests/domains/nec_calculations/__init__.py` first.

```python
"""
NEC Calculation API Tests — MOB-B0

Tests for POST /api/v1/nec/calculate/test
         POST /api/v1/nec/calc-logs/test
         GET /api/v1/nec/calc-logs/test

Per design doc batch-mob-b0-design.md §H.
"""
import pytest
from fastapi.testclient import TestClient
```

**Required test classes**:

```python
class TestNecCalculateEndpoint:
    """POST /api/v1/nec/calculate/test"""

    def test_voltage_drop_returns_201_with_log_id(self, client, db_session, test_tenant):
        """Basic voltage drop calculation returns 201 and saves to DB."""

    def test_conduit_fill_returns_result(self, client, db_session, test_tenant):
        """Conduit fill calc returns result with fill_pct and is_compliant."""

    def test_ampacity_returns_result(self, client, db_session, test_tenant):
        """Ampacity calc returns adjusted_ampacity."""

    def test_invalid_calc_type_returns_400(self, client, db_session, test_tenant):
        """calc_type='unknown' → 400."""

    def test_result_saved_to_db(self, client, db_session, test_tenant):
        """After POST, row exists in nec_calculation_log with correct tenant_id."""

    def test_idempotency_key_dedup(self, client, db_session, test_tenant):
        """Same idempotency_key twice → second call returns same log_id, 200."""

    def test_tenant_isolation(self, client, db_session, test_tenant):
        """Saved log has tenant_id = test_tenant.id."""


class TestNecCalcLogsCreate:
    """POST /api/v1/nec/calc-logs/test (offline sync)"""

    def test_offline_calc_saved(self, client, db_session, test_tenant):
        """Offline result saved with is_offline_calc=True."""

    def test_idempotency_replay(self, client, db_session, test_tenant):
        """Same idempotency_key → returns 200 with existing log_id."""


class TestNecCalcLogsList:
    """GET /api/v1/nec/calc-logs/test"""

    def test_list_returns_logs(self, client, db_session, test_tenant):
        """After creating 2 logs, list returns 2 items."""

    def test_job_id_filter(self, client, db_session, test_tenant):
        """?job_id= filter returns only matching logs."""

    def test_tenant_isolation(self, client, db_session, test_tenant):
        """Only this tenant's logs returned."""

    def test_limit_and_offset(self, client, db_session, test_tenant):
        """limit=1 returns 1 item; offset=1 skips first."""


class TestNecCalcLogTable:
    """Database schema verification."""

    def test_table_exists(self, db_session):
        """nec_calculation_log table exists."""

    def test_required_columns_exist(self, db_session):
        """All required columns present."""

    def test_ck_nec_calc_type_enforced(self, db_session, test_tenant, test_user):
        """calc_type constraint rejects unknown values."""

    def test_updated_at_trigger(self, db_session, test_tenant, test_user):
        """updated_at changes on UPDATE."""

    def test_created_at_immutable(self, db_session, test_tenant, test_user):
        """created_at cannot be changed after insert."""


class TestNecServiceUnit:
    """Pure nec_service.calculate() unit tests."""

    def test_voltage_drop_copper_12awg(self):
        """12 AWG, 100ft, 20A, 120V → voltage_drop_pct ≈ 6.59%, not compliant (> 3%)."""

    def test_voltage_drop_three_phase(self):
        """√3 factor applied correctly for phase=3."""

    def test_voltage_drop_over_3pct_not_compliant(self):
        """High distance + current → is_compliant=False."""

    def test_conduit_fill_emt_half_inch(self):
        """EMT ½", 3× #12 → correct fill and pass/fail."""

    def test_conduit_fill_over_40pct_fails(self):
        """Fill >40% for 3+ wires → is_compliant=False."""

    def test_invalid_calc_type_raises(self):
        """ValueError raised for unsupported calc_type."""
```

---

## Step 9: Regenerate OpenAPI

After all tests pass:

```bash
cd <repo>/backend
python export_openapi_json.py
```

Verify:
```bash
grep -A 5 "POST /api/v1/nec/calculate" backend/openapi_schema_map.md
grep -A 5 "GET /api/v1/nec/calc-logs" backend/openapi_schema_map.md
```

Both endpoints must appear in the schema map.

---

## Final Verification

```bash
cd <repo>/backend

# Run full test suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Run specifically the NEC voice tests (regression guard)
python -m pytest backend/tests/batch_1e/test_task_1e3_nec_calculations.py -v 2>&1 | tail -15

# Run new NEC endpoint tests
python -m pytest backend/tests/domains/nec_calculations/ -v 2>&1

echo "=== MOB-B0 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MOB-B0

Update `pilot-app-beta-fixes-v2-impl-plan.md` §9 Batch Completion Tracker:

- [ ] Pre-modification regression baseline captured
- [ ] All MCP pre-work queries run — `nec_calculation_log` absence confirmed, trigger functions confirmed
- [ ] Alembic migration created with `upgrade()` and `downgrade()` — `alembic upgrade head` runs cleanly
- [ ] Migration tested: `upgrade → downgrade → upgrade` cycle passes
- [ ] `NecCalculationLog` model added to `app/models/field_operations.py`
- [ ] `NecCalculationLog` exported from `app/models/__init__.py`
- [ ] `services/nec_service.py` created — `calculate()`, `_calc_voltage_drop()`, `_calc_conduit_fill()`, `_calc_ampacity()` all implemented
- [ ] `services/voice_action_router.py` updated to delegate to `nec_service.calculate()` — no formula duplication
- [ ] `backend/tests/batch_1e/test_task_1e3_nec_calculations.py` — all tests still pass (zero regressions from refactor)
- [ ] `backend/tests/batch_b17/test_find128_technician_role_permissions.py` — `nec.calculate` still present
- [ ] `api/schemas/nec.py` created with all 4 schema classes
- [ ] `api/routes/nec.py` created with 6 endpoints (3 auth + 3 test)
- [ ] All `_impl()` functions use tenant-scoped `select()` — `db.get()` not used anywhere
- [ ] Idempotency key dedup logic correct (returns existing log_id, not 409)
- [ ] Router registered in `app/main.py` under prefix `/api/v1/nec`
- [ ] `nec_calculation_log` table has `ck_nec_calc_type` constraint, all 3 triggers
- [ ] Unit tests pass for `nec_service.py` pure functions
- [ ] API endpoint tests pass (all 12 test classes)
- [ ] DB schema tests pass (table existence, columns, constraint, triggers)
- [ ] `python export_openapi_json.py` run — both `openapi.json` and `openapi_schema_map.md` updated
- [ ] `grep "nec/calculate" backend/openapi_schema_map.md` confirms endpoint present
- [ ] `grep "nec/calc-logs" backend/openapi_schema_map.md` confirms endpoint present
- [ ] Zero regressions in full test suite (only known `test_a57_preference_matrix` allowed)
- [ ] Final test count (before → after) documented in impl plan tracker
- [ ] Summary of work added to impl plan §9 as new sub-section after MOB-B0 row
