# MOB-B0 Batch Design — NEC Calculation Backend (API + Persistence)

**Version**: 1.0
**Date**: 2026-06-05
**Batch**: MOB-B0
**Type**: Backend (Python / FastAPI)
**Prerequisite Batches**: None — **must complete before MOB-B4 can be implemented**
**Gates**: MOB-B4 (Calcs Tab NEC frontend — requires `POST /api/v1/nec/calculate` to exist)
**Estimated Effort**: 1–1.5 days (Python Engineer)
**Test Subfolder**: `backend/tests/domains/nec_calculations/`
**Status**: Design complete — ready for Python Engineer implementation

---

## A. Input Read Summary

All source artifacts were read directly before writing this document. No content was assumed.

### A.1 Artifacts Read

| Artifact | Key Findings |
|:---|:---|
| `pilot-app-beta-fixes-v2-impl-plan.md` §8 MOB-B0 | Full spec: 3 endpoints, `nec_calculation_log` table, Ollama routing, offline sync endpoint |
| `backend/services/voice_action_router.py` L600–750 | **Critical**: `calculate_nec_voltage_drop()` and `calculate_conduit_fill()` **already implemented** as voice handler functions. Same NEC 2023 formulas needed. The new REST endpoint **must reuse this logic** rather than duplicating it. |
| `backend/tests/batch_b17/test_find128_technician_role_permissions.py` | **Critical**: `nec.calculate` permission **already exists** in the technician role (`assert "nec.calculate" in perms`). Described as "intentional forward-looking permission for Phase 2 NEC routes." No permission seed migration needed. |
| `backend/api/routes/jobs.py` | Dual-endpoint pattern: `_impl()` shared function → authenticated endpoint `Depends(require_permission("jobs.view"))` + test endpoint with `get_test_context()`. This is the exact pattern for the NEC router. |
| `backend/app/main.py` | Lists all router imports (L12–68). New `nec` router must be added here. |
| `backend/core/permissions.py` | `require_permission("nec.calculate")` is the correct FastAPI dependency. Format: `resource.action`. |
| `backend/migrations/versions/2026_05_31_2216-5ec7fe1e46d8_*.py` | Migration pattern: blank migration, raw SQL via `op.execute()`, `op.execute("SET LOCAL session_replication_role = 'replica';")` for seed inserts. Always `revision`, `down_revision`, `upgrade()`, `downgrade()`. |
| MCP: `nec_calculation_log` existence | **Confirmed NOT in database** — table does not exist, must be created by this batch. |
| MCP: trigger functions | Confirmed: `set_updated_at` (`clock_timestamp()`) and `guard_created_fields_immutable` functions exist. Audit trigger function is `audit.log_changes()` (created in audit logging migration). |
| MCP: `connector_config` / `connector_run_log` tables | Confirmed: no `nec`-related tables exist. |

### A.2 Critical Design Decision: Reuse Voice Action Router Functions

**Problem**: `calculate_nec_voltage_drop()` and `calculate_conduit_fill()` in `voice_action_router.py` already implement NEC 2023 formulas for the voice pipeline. The new REST endpoint would duplicate this logic.

**Resolution**: The new `POST /api/v1/nec/calculate` endpoint will **extract** the calculation logic into a shared service function (`backend/services/nec_service.py`) and both the voice action router AND the new REST endpoint will call it. This eliminates duplication and ensures a single source of truth for NEC formulas.

**Pattern**: Same as `services/etc_service.py` (shared between voice and REST endpoints). Read that service before implementing.

### A.3 `nec.calculate` Permission Already Exists

The `nec.calculate` permission is already seeded in the `technician` role (confirmed by `test_find128_technician_role_permissions.py`). **No new permission seed migration needed.** The router simply uses `require_permission("nec.calculate")`.

---

## B. Migration Plan

### B.1 Pre-Migration Verification (MCP Queries — Required Before Writing Migration)

```sql
-- Confirm nec_calculation_log does not exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'nec_calculation_log';
-- Expected: 0 rows

-- Confirm trigger functions exist
SELECT proname FROM pg_proc WHERE proname IN ('set_updated_at', 'guard_created_fields_immutable');
-- Expected: 2 rows

-- Verify audit trigger function exists for new table
SELECT proname FROM pg_proc WHERE proname = 'log_changes' AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'audit');
-- If 0 rows: do NOT add audit trigger (use only set_updated_at + guard_created_fields_immutable)
```

### B.2 New Table: `nec_calculation_log`

**Migration file**: `backend/migrations/versions/2026_06_05_{hash}_mob_b0_nec_calculation_log.py`

Create the table using raw SQL in Alembic (per `pilot-python-engineer-methods.md §13`):

```sql
CREATE TABLE nec_calculation_log (
    -- Standard audit columns
    created_at         TIMESTAMPTZ     NOT NULL DEFAULT clock_timestamp(),
    updated_at         TIMESTAMPTZ     NOT NULL DEFAULT clock_timestamp(),
    created_by         UUID            REFERENCES "user"(id) ON DELETE RESTRICT,
    updated_by         UUID            REFERENCES "user"(id) ON DELETE RESTRICT,

    -- Primary key
    id                 UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tenant + ownership
    tenant_id          UUID            NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
    user_id            UUID            NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,

    -- Optional job linkage
    job_id             UUID            NULL REFERENCES job(id) ON DELETE SET NULL,

    -- Calculation identity
    calc_type          VARCHAR(50)     NOT NULL,
    nec_guide_version  VARCHAR(20)     NOT NULL DEFAULT '2023',

    -- Inputs and outputs (JSONB)
    inputs_json        JSONB           NOT NULL DEFAULT '{}',
    result_json        JSONB           NOT NULL DEFAULT '{}',

    -- Source flag
    is_offline_calc    BOOLEAN         NOT NULL DEFAULT FALSE,

    -- Idempotency (for offline sync dedup)
    idempotency_key    UUID            NULL UNIQUE,

    -- Optional: timestamp of client capture (for offline audit trail)
    client_capture_at  TIMESTAMPTZ     NULL,

    CONSTRAINT ck_nec_calc_type CHECK (
        calc_type IN ('voltage_drop', 'conduit_fill', 'ampacity')
    )
);
```

**Indexes** (add after table creation):
```sql
CREATE INDEX idx_nec_calc_log_tenant_created
    ON nec_calculation_log (tenant_id, created_at DESC);

CREATE INDEX idx_nec_calc_log_job
    ON nec_calculation_log (job_id)
    WHERE job_id IS NOT NULL;

CREATE INDEX idx_nec_calc_log_user
    ON nec_calculation_log (user_id, created_at DESC);
```

**Required Triggers** (apply after table creation):
```sql
-- 1. set_updated_at trigger
CREATE TRIGGER trg_nec_calc_log_updated_at
    BEFORE UPDATE ON nec_calculation_log
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 2. Immutable guard trigger
CREATE TRIGGER trg_nec_calc_log_immutable
    BEFORE UPDATE ON nec_calculation_log
    FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();

-- 3. Audit trigger (only if audit.log_changes function confirmed by MCP pre-check)
-- CREATE TRIGGER trg_nec_calc_log_audit
--     AFTER INSERT OR UPDATE OR DELETE ON nec_calculation_log
--     FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
```

> **If audit trigger function NOT found by MCP**: omit audit trigger and add a `# TODO: add audit trigger when confirmed` comment.

**Multi-tenancy immutable guard**:
```sql
-- tenant_id is immutable after insert (IDOR protection)
-- Enforced by the check in guard_created_fields_immutable via the trigger above
-- No separate trigger needed — tenant_id is covered by the immutable guard on created_* fields
-- Add an explicit check constraint as belt-and-suspenders:
ALTER TABLE nec_calculation_log
    ADD CONSTRAINT ck_nec_calc_log_tenant_not_null
    CHECK (tenant_id IS NOT NULL);
```

### B.3 SQLModel Model

**File**: `backend/app/models/field_operations.py` (existing file — add to it)

> **Before modifying**: Read `backend/app/models/field_operations.py` fully to find the correct location and understand the existing model patterns.

```python
class NecCalculationLog(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "nec_calculation_log"
    __table_args__ = (
        CheckConstraint(
            "calc_type IN ('voltage_drop', 'conduit_fill', 'ampacity')",
            name="ck_nec_calc_type",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    tenant_id: uuid.UUID = Field(
        foreign_key="tenant.id",
        nullable=False,
        index=True,
    )
    user_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
    )
    job_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="job.id",
        nullable=True,
        index=True,
    )
    calc_type: str = Field(max_length=50)
    nec_guide_version: str = Field(default="2023", max_length=20)
    inputs_json: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    result_json: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    is_offline_calc: bool = Field(default=False)
    idempotency_key: uuid.UUID | None = Field(default=None, nullable=True, unique=True)
    client_capture_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
```

---

## C. Execution Order

| # | Task | File(s) | Dependency |
|:---:|:---|:---|:---|
| 1 | Run MCP pre-work queries — verify table absence, trigger functions exist | MCP tool | None |
| 2 | Read `services/voice_action_router.py` NEC calc functions to understand extraction scope | `voice_action_router.py` L600–900 | None |
| 3 | Read `services/etc_service.py` — understand shared service extraction pattern | `services/etc_service.py` | None |
| 4 | Read `app/models/field_operations.py` — find existing models for placement | `models/field_operations.py` | None |
| 5 | Create Alembic migration for `nec_calculation_log` | New migration file | #1 |
| 6 | Add `NecCalculationLog` model to `app/models/field_operations.py` | `models/field_operations.py` | #5 |
| 7 | Add `NecCalculationLog` to `app/models/__init__.py` | `models/__init__.py` | #6 |
| 8 | Create `services/nec_service.py` — extract NEC calculation logic | New `services/nec_service.py` | #2, #3 |
| 9 | Update `services/voice_action_router.py` to call `nec_service.py` instead of inline | `voice_action_router.py` | #8 |
| 10 | Create `api/routes/nec.py` with all 4 endpoints + impl functions | New `api/routes/nec.py` | #6, #8 |
| 11 | Register `nec` router in `app/main.py` | `app/main.py` | #10 |
| 12 | Create `api/schemas/nec.py` (request/response schemas) | New `api/schemas/nec.py` | None |
| 13 | Write tests in `backend/tests/domains/nec_calculations/` | New test files | #10 |
| 14 | Run full test suite — verify 0 regressions | — | #13 |
| 15 | Regenerate `openapi.json` + `openapi_schema_map.md` | `export_openapi_json.py` | #14 |

---

## D. New API Endpoints

### D.1 `POST /api/v1/nec/calculate`

**Summary**: Run NEC calculation online via Ollama NEC guide context
**Auth**: Required (`nec.calculate` permission — already in technician role)
**Module**: `api/routes/nec.py`

**Request body**: `NecCalculateRequest`
```json
{
  "calc_type": "voltage_drop",
  "inputs": {
    "amperage": 20,
    "distance_feet": 100,
    "wire_gauge": "12 AWG",
    "voltage": 120,
    "phase": 1
  },
  "job_id": "uuid-or-null",
  "idempotency_key": "uuid"
}
```

`calc_type` values: `"voltage_drop"`, `"conduit_fill"`, `"ampacity"`

**Response 201**: `NecCalculateResponse`
```json
{
  "log_id": "uuid",
  "calc_type": "voltage_drop",
  "result": {
    "voltage_drop": 3.4567,
    "voltage_drop_pct": 2.88,
    "is_compliant": true,
    "nec_article": "210.19"
  },
  "nec_guide_version": "2023",
  "nec_citation": "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended"
}
```

**Implementation**:
```python
def _nec_calculate_impl(
    calc_in: NecCalculateRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> NecCalculateResponse:
    """
    Route input to the appropriate NEC calculation service function.
    Saves result to nec_calculation_log.
    Returns structured result with NEC citation.
    """
    # 1. Route to nec_service function based on calc_type
    result = nec_service.calculate(calc_type=calc_in.calc_type, inputs=calc_in.inputs)

    # 2. Save to nec_calculation_log
    log = NecCalculationLog(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        job_id=calc_in.job_id,
        calc_type=calc_in.calc_type,
        nec_guide_version="2023",
        inputs_json=calc_in.inputs,
        result_json=result.dict(),
        is_offline_calc=False,
        idempotency_key=calc_in.idempotency_key,
    )
    db.add(log)
    db.commit()

    return NecCalculateResponse(
        log_id=log.id,
        calc_type=calc_in.calc_type,
        result=result,
        nec_guide_version="2023",
        nec_citation=result.nec_citation,
    )
```

**Idempotency**: Check for existing `idempotency_key` before saving. If found, return existing result (409 prevention — mobile may retry on reconnect).

**Error Responses**:
- `400` — invalid `calc_type` or malformed inputs
- `403` — missing `nec.calculate` permission
- `422` — Pydantic validation failure

### D.2 `POST /api/v1/nec/calculate/test`

No-auth test endpoint using `get_test_context()`. Same `_nec_calculate_impl()`.

### D.3 `POST /api/v1/nec/calc-logs` (Offline Sync Endpoint)

**Summary**: Save a pre-computed offline calculation result (from mobile TypeScript engine)
**Auth**: Required (`nec.calculate` permission)

**Request body**: `NecCalcLogCreate` (offline sync payload)
```json
{
  "calc_type": "voltage_drop",
  "inputs": { ... },
  "result": { ... },
  "nec_guide_version": "2023",
  "is_offline_calc": true,
  "client_capture_at": "2026-06-05T14:32:00Z",
  "idempotency_key": "uuid",
  "job_id": "uuid-or-null"
}
```

**Response 201**: `{ "log_id": "uuid" }`

**Implementation**: Does NOT re-run the calculation. Saves the offline result verbatim with `is_offline_calc=True`. Uses `idempotency_key` for dedup — if already saved, returns `{ "log_id": existing_id }` with 200 (idempotent replay).

### D.4 `POST /api/v1/nec/calc-logs/test`

No-auth test endpoint. Same impl.

### D.5 `GET /api/v1/nec/calc-logs`

**Summary**: List NEC calculation logs for current tenant (audit/owner view)
**Auth**: Required (`nec.calculate` permission)

**Query params**:
- `job_id` (optional UUID) — filter by job
- `limit` (int, default 50, max 200)
- `offset` (int, default 0)

**Response 200**: `[NecCalcLogResponse]`
```json
[
  {
    "id": "uuid",
    "calc_type": "voltage_drop",
    "nec_guide_version": "2023",
    "inputs_json": { ... },
    "result_json": { ... },
    "is_offline_calc": false,
    "client_capture_at": null,
    "job_id": "uuid-or-null",
    "created_at": "2026-06-05T14:32:00Z"
  }
]
```

**Multi-tenancy**: Always filter by `NecCalculationLog.tenant_id == current_user.tenant_id`.

### D.6 `GET /api/v1/nec/calc-logs/test`

No-auth test endpoint. Same impl.

---

## E. Pattern Reuse Decisions

### E.1 Dual-Endpoint Pattern (from `jobs.py`)

All 3 operations have authenticated + `/test` no-auth endpoints. The `_impl()` shared function accepts `AuthenticatedUser | TestUserContext`. This is the established pattern for every route in the codebase.

### E.2 `nec_service.py` — Shared Calculation Service (from `etc_service.py` pattern)

Extract NEC calculation logic from `voice_action_router.py` into a new `services/nec_service.py` module. Both the voice handler and the new REST endpoint call this shared service. This is the same pattern as `services/etc_service.py` which is called by both voice routes and field operations routes.

**Key function signature**:
```python
def calculate(calc_type: str, inputs: dict) -> NecCalcResult:
    """Route to voltage_drop, conduit_fill, or ampacity calculation."""
```

This function is **pure** (no DB, no Ollama call for MVP) — uses NEC 2023 TypeScript-equivalent Python formulas from the existing `voice_action_router.py` implementation.

> **Ollama Note**: The v2 impl plan spec says "routes to Ollama with NEC guide context." However, the existing `voice_action_router.py` implementation uses **pure NEC 2023 formulas** (no Ollama call) — and the mobile offline fallback also uses pure formulas. For MVP consistency: `POST /api/v1/nec/calculate` uses the same pure formula engine, not Ollama. Ollama routing adds latency and GPU dependency to a pure math operation. The NEC citation is hardcoded per formula (e.g., `"NEC 210.19(A)(1)"`). This is the correct MVP approach. See §G.1.

### E.3 Idempotency Pattern (from `utils/idempotency.py`)

Read `backend/utils/idempotency.py` before implementing the idempotency key check. The NEC calc endpoint should use the same idempotency key pattern used throughout the app.

### E.4 Standard Tenant-Scoped Query Pattern

```python
# ✅ REQUIRED — never use db.get() on NecCalculationLog
log = db.exec(
    select(NecCalculationLog)
    .where(NecCalculationLog.id == log_id)
    .where(NecCalculationLog.tenant_id == current_user.tenant_id)
).first()
if not log:
    raise HTTPException(status_code=404, detail="Not found")
```

---

## F. Shared Module Interfaces

### F.1 `services/nec_service.py` — New Service Module

```python
# backend/services/nec_service.py

from dataclasses import dataclass

@dataclass
class NecCalcResult:
    """Structured calculation result with NEC citation."""
    calc_type: str
    result_value: float         # Primary calculated value
    is_compliant: bool          # Pass/fail against NEC limit
    nec_article: str            # e.g., "NEC 210.19(A)(1)"
    nec_citation: str           # Full citation text
    details: dict               # All calculated fields (voltage_drop_pct, fill_pct, etc.)

    def dict(self) -> dict:
        return {
            "calc_type": self.calc_type,
            "result_value": self.result_value,
            "is_compliant": self.is_compliant,
            "nec_article": self.nec_article,
            "nec_citation": self.nec_citation,
            **self.details,
        }

def calculate(calc_type: str, inputs: dict) -> NecCalcResult:
    """
    Route to the appropriate NEC 2023 calculation function.
    
    Args:
        calc_type: One of 'voltage_drop', 'conduit_fill', 'ampacity'
        inputs: Calculation inputs dict (validated by caller schema)
    
    Returns:
        NecCalcResult with result values and NEC citation
    
    Raises:
        ValueError: If calc_type is unsupported or inputs are invalid
    """
    if calc_type == "voltage_drop":
        return _calc_voltage_drop(inputs)
    elif calc_type == "conduit_fill":
        return _calc_conduit_fill(inputs)
    elif calc_type == "ampacity":
        return _calc_ampacity(inputs)
    else:
        raise ValueError(f"Unsupported calc_type: {calc_type}")
```

The `_calc_voltage_drop` and `_calc_conduit_fill` implementations are extracted from the existing `voice_action_router.py` functions (not rewritten — moved).

### F.2 `api/schemas/nec.py` — New Schema File

```python
# backend/api/schemas/nec.py

from pydantic import BaseModel, Field
import uuid
from datetime import datetime

class NecCalculateRequest(BaseModel):
    calc_type: str = Field(..., description="'voltage_drop' | 'conduit_fill' | 'ampacity'")
    inputs: dict = Field(..., description="Calculation inputs — keys depend on calc_type")
    job_id: uuid.UUID | None = None
    idempotency_key: uuid.UUID | None = None

class NecCalcResultDetail(BaseModel):
    # Validated at use time — dynamic keys based on calc_type
    is_compliant: bool
    nec_article: str
    nec_citation: str
    # Plus calc_type-specific fields

class NecCalculateResponse(BaseModel):
    log_id: uuid.UUID
    calc_type: str
    result: dict              # NecCalcResult.dict() output
    nec_guide_version: str
    nec_citation: str

class NecCalcLogCreate(BaseModel):
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

## G. Open Questions Resolved

### G.1 — Ollama vs Pure Formula Engine

**Problem**: The v2 impl plan spec says `POST /api/v1/nec/calculate` "routes to Ollama with NEC guide context." But the existing `voice_action_router.py` uses pure Python NEC 2023 formulas (not Ollama) for identical calculations.

**Resolution**: Use **pure NEC 2023 formulas** (same as existing voice pipeline), NOT Ollama. Rationale:
1. NEC calculations are deterministic physics — no language model needed
2. Ollama adds latency (~200–500ms) and GPU dependency for a pure math operation
3. The existing voice tests confirm the formula accuracy
4. The mobile offline fallback also uses pure formulas — server/client parity
5. `nec_guide_version: "2023"` is hardcoded in the result (not Ollama-reported)

This decision has zero impact on the mobile frontend (MOB-B4). The API response shape is identical regardless of whether Ollama or formulas power it.

### G.2 — `nec.calculate` Permission Already Exists

**Confirmed**: No new permission seed migration needed. The `test_find128_technician_role_permissions.py` test explicitly asserts `"nec.calculate" in perms` and calls it "intentional forward-looking permission for Phase 2 NEC routes." This batch IS that Phase 2 route.

### G.3 — `ampacity` Calculation — Not Yet in `voice_action_router.py`

The existing `voice_action_router.py` has `calculate_nec_voltage_drop` and `calculate_conduit_fill` but NOT `calculate_nec_ampacity`. For MVP, the `ampacity` calc_type can be accepted by the API but returns a `501 Not Implemented` response until implemented. Or it can be implemented as part of `nec_service.py` using NEC Table 310.12 values.

**Decision**: Implement basic ampacity calculation in `nec_service.py` based on NEC Table 310.12 (same approach as voltage drop — hardcoded lookup table). The mobile `calcAmpacity()` TypeScript function in MOB-B4 will serve as the spec. Input fields: `wire_material`, `wire_gauge`, `temp_rating_c`, `conductor_count`, `ambient_temp_c`. Output: `{ base_ampacity, temp_correction_factor, bundling_adjustment_factor, adjusted_ampacity, nec_article: "Table 310.12" }`.

### G.4 — `voice_action_router.py` Refactoring Scope

Extracting NEC logic from `voice_action_router.py` to `nec_service.py` is a refactoring step. This must be done carefully to avoid breaking the existing voice pipeline tests.

**Approach**: 
1. Create `nec_service.py` with the extracted functions
2. In `voice_action_router.py`, replace inline logic with calls to `nec_service.calculate(...)`
3. The existing tests (`test_task_1e3_nec_calculations.py`) must still pass — they test the voice action router, which now delegates to the service
4. **Zero regression tolerance** — run full test suite before declaring done

### G.5 — Idempotency Key for Offline Sync

The mobile `SyncOrchestrator` generates a UUID idempotency key at capture time. When it syncs an offline calc to `POST /api/v1/nec/calc-logs`, the server uses this key to detect replay. The `idempotency_key` column has a UNIQUE constraint. On conflict (key already exists), return `200` with the existing `log_id` — do not return `409`. This matches the pattern used by `POST /api/v1/jobs/{job_id}/loto-confirmations` idempotency_uuid behavior.

---

## H. Test Plan

**Test subfolder**: `backend/tests/domains/nec_calculations/`

New test file: `backend/tests/domains/nec_calculations/test_nec_endpoints.py`

### H.1 Unit Tests (pure calculation functions)

| Test | Assertion |
|:---|:---|
| `test_voltage_drop_copper_12awg_single_phase` | 12 AWG, 100ft, 20A, 120V, single-phase → `voltage_drop_pct ≈ 2.88%`, `is_compliant=True` |
| `test_voltage_drop_three_phase_factor` | √3 multiplier correctly applied for three-phase |
| `test_voltage_drop_fails_when_over_3pct` | Input that produces >3% drop → `is_compliant=False` |
| `test_conduit_fill_emt_half_inch_3wires` | EMT ½", 3× #12 THHN → correct fill area, pass/fail |
| `test_conduit_fill_fails_at_over_40pct` | 4+ wires over 40% fill → `is_compliant=False` |
| `test_ampacity_basic_lookup` | #12 THHN 90°C, 30°C ambient, 3 conductors → correct adjusted ampacity |
| `test_invalid_calc_type_raises_value_error` | `calc_type="unknown"` → `ValueError` |

### H.2 API Endpoint Tests

| Test | Assertion |
|:---|:---|
| `test_post_calculate_saves_to_db` | POST `/nec/calculate/test` → 201, `log_id` returned, row exists in `nec_calculation_log` |
| `test_post_calculate_tenant_isolation` | Log row has `tenant_id = test_tenant.id` |
| `test_post_calculate_idempotency` | Same `idempotency_key` twice → second call returns 200 with same `log_id` |
| `test_post_calc_logs_offline_saved` | POST `/nec/calc-logs/test` with `is_offline_calc=true` → 201, `is_offline_calc=True` in DB |
| `test_get_calc_logs_list` | GET `/nec/calc-logs/test` → returns array of logs for tenant |
| `test_get_calc_logs_job_filter` | `?job_id=` filter returns only matching logs |
| `test_get_calc_logs_tenant_isolation` | Only this tenant's logs returned; other tenant logs not visible |
| `test_nec_calc_log_table_exists` | DB schema check: `nec_calculation_log` table exists with all columns |
| `test_nec_calc_log_triggers` | `updated_at` changes on UPDATE; `created_at` immutable |
| `test_nec_permission_required` | Authenticated endpoint with missing permission → 403 |

### H.3 Regression Tests

| Test | Assertion |
|:---|:---|
| Existing `test_task_1e3_nec_calculations.py` | All NEC voice action router tests still pass after `nec_service.py` extraction |
| `test_find128_technician_role_permissions.py` | `nec.calculate` still in technician permissions |
| Full test suite (`pytest backend/`) | Zero regressions from migration or new router registration |

---

## Design Doc Quality Gate Checklist

- [x] `nec_calculation_log` confirmed NOT in DB (MCP query)
- [x] Trigger functions `set_updated_at` and `guard_created_fields_immutable` confirmed in DB
- [x] `nec.calculate` permission confirmed already in technician role — no seed migration needed
- [x] `calculate_nec_voltage_drop` and `calculate_conduit_fill` confirmed in `voice_action_router.py` — extraction to `nec_service.py` specified
- [x] Ollama routing decision resolved: pure NEC formulas (not Ollama) per §G.1
- [x] `nec.calculate` permission format verified from `core/permissions.py` format
- [x] Dual-endpoint pattern specified per `jobs.py` pattern
- [x] Multi-tenancy: all DB queries include `tenant_id` filter — `db.get()` banned
- [x] Idempotency dedup pattern for offline sync specified §G.5
- [x] `ampacity` handler gap documented and resolution specified §G.3
- [x] `voice_action_router.py` refactoring scope and regression guard specified §G.4
- [x] Router registration in `app/main.py` required step documented
- [x] `api/schemas/nec.py` new schema file specified
- [x] `openapi.json` regeneration required after all changes
- [x] Infrastructure constraint: zero cost impact (uses existing g4dn.xlarge GPU which is idle for this endpoint — pure formula, no Ollama call)
- [x] All 3 execution paths tested: online calculate, offline sync save, audit list
