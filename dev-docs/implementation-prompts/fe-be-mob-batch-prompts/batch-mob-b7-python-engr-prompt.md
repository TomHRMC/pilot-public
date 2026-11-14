# Implementation Prompt: MOB-B7 Part A — LOTO Policy Endpoint

**Mode**: Pilot Python Engineer  
**Batch**: MOB-B7 Part A (Backend)  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — MOB-B7  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b7-design.md`  
**Estimated session**: 30–60 minutes (small batch — one endpoint or confirm existing)  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: MOB-B7 Part B (React Native Engineer) — runs after this batch + `pnpm sync-api-types`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document

**Critical rules for this batch:**

- **Rule 1**: Before writing ANY endpoint, verify what already exists. The generic `GET /api/v1/settings/{key}` endpoint may already work — check FIRST before adding a new endpoint.
- **Rule 2**: Use `get_effective_setting()` service (not raw DB query) for reading tenant settings. This ensures proper three-tier resolution (user → tenant → system default).
- **Rule 3**: All errors follow RFC 7807 Problem Details format.
- **Rule 4**: Never use `db.get()` on tenant-scoped models. Always use tenant-scoped `select()`.
- **Rule 5**: After any endpoint change → run `python export_openapi_json.py`.
- **Rule 6**: If ANY test fails → fix it before declaring done.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record exact count. Fix pre-existing failures before proceeding.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: Read-only verification only. Never INSERT/UPDATE/DELETE.

```sql
-- 1. Verify loto_confirmation_required exists in platform_setting_catalog
SELECT key, value_type, default_value, description
FROM public.platform_setting_catalog
WHERE key = 'loto_confirmation_required';

-- 2. Check if a system-level default exists in platform_setting
SELECT key, value FROM public.platform_setting
WHERE key = 'loto_confirmation_required';

-- 3. Check what platform_setting tables look like (for get_effective_setting reference)
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE '%setting%'
ORDER BY table_name;
```

---

## Pre-Work: Read These Source Files

```
backend/api/routes/settings.py lines 1–100   ← understand existing settings endpoints
backend/services/setting_resolver.py         ← understand get_effective_setting() signature
backend/app/main.py (grep settings)          ← confirm settings router prefix
```

Run this check:
```bash
# Check if GET /api/v1/settings/{key} already works for loto_confirmation_required
python3 -c "
import json
spec = json.load(open('openapi.json'))
setting_paths = [p for p in spec['paths'] if 'settings' in p and '{key}' in p]
print('Settings paths with {key}:', setting_paths)
for p in setting_paths:
    methods = list(spec['paths'][p].keys())
    print(f'  {p}: {methods}')
"
```

---

## Task A1 — Verify Existing Settings Endpoint

Read `backend/api/routes/settings.py` fully. Check if:

1. `GET /api/v1/settings/{key}` or `GET /api/v1/settings/loto_confirmation_required` already exists
2. If yes: **does it return the tenant-effective value** (not just the platform default)?
3. If yes to both: **Part A requires NO new code** — just verify the endpoint returns the correct shape and document it for the React Native Engineer.

**If the generic endpoint works**, add a comment in the file and skip to Task A4 (run export only).

**If no existing endpoint works for this setting**, proceed to Task A2.

---

## Task A2 — Add `GET /api/v1/settings/loto-policy` (only if A1 finds no existing endpoint)

**File**: `backend/api/routes/settings.py`

```python
class LotoPolicyResponse(BaseModel):
    loto_confirmation_required: bool

@router.get("/loto-policy", response_model=LotoPolicyResponse)
def get_loto_policy(
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
    db: Session = Depends(get_db),
) -> LotoPolicyResponse:
    """
    Returns the tenant-effective LOTO policy.
    All roles with jobs.view can read this (techs need it at clock-in).
    Default = false (LOTO section is optional, not required).
    """
    value, _ = get_effective_setting(
        db, current_user.tenant_id, "loto_confirmation_required", fallback=False
    )
    return LotoPolicyResponse(loto_confirmation_required=bool(value))


@router.get("/loto-policy/test", response_model=LotoPolicyResponse)
def get_loto_policy_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> LotoPolicyResponse:
    """Test endpoint — no JWT required."""
    value, _ = get_effective_setting(
        db, ctx.tenant_id, "loto_confirmation_required", fallback=False
    )
    return LotoPolicyResponse(loto_confirmation_required=bool(value))
```

RFC 7807 error on any unexpected failure:
```python
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail={
        "type": "https://errors.pilotfortrades.com/internal",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "Failed to resolve LOTO policy",
    },
)
```

---

## Task A3 — Add Unit Test

**File**: `tests/domains/platform_infrastructure/test_loto_policy_mob_b7.py`

```python
pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]

def test_loto_policy_returns_false_by_default(client, test_tenant, mock_cognito_jwt):
    """Default: loto_confirmation_required = false."""
    resp = client.get("/api/v1/settings/loto-policy/test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["loto_confirmation_required"] is False
```

Test resilience rule: scope by inserted IDs; never count all tenant rows.

---

## Task A4 — Regenerate OpenAPI

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py

# Verify endpoint appears
grep "loto-policy" openapi_schema_map.md | head -5
```

---

## Final Verification

```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
python -m pytest --tb=short -q 2>&1 | tail -5
echo "=== MOB-B7 PART A FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MOB-B7 Part A

- [ ] Regression baseline captured
- [ ] MCP pre-work queries run — `loto_confirmation_required` setting confirmed in DB
- [ ] Existing settings endpoint checked — determined whether new endpoint needed
- [ ] Either: generic endpoint confirmed to work OR new `GET /api/v1/settings/loto-policy` added
- [ ] `/test` mirror endpoint added (if new endpoint created)
- [ ] Unit test in `platform_infrastructure/` passes
- [ ] RFC 7807 error format used
- [ ] `python export_openapi_json.py` run — endpoint visible in `openapi_schema_map.md`
- [ ] Phase 1 + Phase 2 tests pass
- [ ] Completion Summary added to impl plan

---

## Handoff Instructions

When done:
1. Run `python export_openapi_json.py`
2. Commit: `feat(mob-b7-be): LOTO policy endpoint (MOB-B7 Part A)`
3. Notify React Native Engineer: **"MOB-B7 Part A complete. Run `cd frontend && pnpm sync-api-types` then proceed with `batch-mob-b7-react-native-engr-prompt.md`."**
