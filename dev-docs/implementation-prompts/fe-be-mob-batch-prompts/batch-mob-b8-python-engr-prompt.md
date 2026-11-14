# Implementation Prompt: MOB-B8 Part A — Background Sync: Silent Push Celery Task + Policy Endpoint

**Mode**: Pilot Python Engineer  
**Batch**: MOB-B8 Part A (Background-Sync-B1 — Backend)  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — Batch 9 (Background-Sync-B1)  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b8-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: MOB-B8 Part B — React Native Engineer (runs after `python export_openapi_json.py` is confirmed)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: No Alembic migrations are needed. All required tables (`mobile_device_push_token`, `mobile_push_rate_limit`, `mobile_sync_session`) and all 4 background sync settings already exist in the DB. Run MCP pre-work queries to confirm before writing anything.
- **Rule 2**: Before implementing the push token endpoint, grep `backend/openapi_schema_map.md` for "push-tokens" or "push_token". If an endpoint already exists → **skip Task 2 entirely** and document the skip in your Completion Summary.
- **Rule 3**: All new Celery tasks MUST use the two-layer pattern: `_impl(params, db: Session)` for business logic + `@celery_app.task` wrapper that creates its own session. Never put business logic in the Celery entry point.
- **Rule 4**: The `send_background_sync_push` Celery task dispatches individual per-device pushes via the **Expo Push Notification API** (`https://exp.host/--/api/v2/push/send`). Read `backend/tasks/notification_worker.py` to understand the existing Expo push delivery pattern — **reuse it, do not reinvent it**.
- **Rule 5**: Never use `db.get()` on tenant-scoped models. Always use `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 6**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before the first DB write.
- **Rule 7**: All API error responses MUST follow RFC 7807 Problem Details format.
- **Rule 8**: If ANY test fails during your work — even pre-existing — **you must fix it before declaring done**. No exceptions.
- **Rule 9**: `postgres-local` MCP is **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current unit-only test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing: do NOT proceed until you confirm the failure with Tom or fix it. You may not start implementation while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm push token table — verify all required columns exist
SELECT column_name, data_type, is_nullable FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'mobile_device_push_token' 
ORDER BY ordinal_position;

-- 2. Confirm rate limit table columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'mobile_push_rate_limit' 
ORDER BY ordinal_position;

-- 3. Confirm mobile_sync_session has triggered_by column
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'mobile_sync_session' 
AND column_name = 'triggered_by';

-- 4. Confirm all 4 background sync settings exist in catalog
SELECT key, value_type FROM public.platform_setting_catalog 
WHERE key IN ('background_sync_enabled', 'background_sync_wifi_only',
              'background_sync_battery_floor_pct', 'background_sync_push_interval_minutes')
ORDER BY key;

-- 5. Confirm current alembic head (should be f7f30492c3e4 from B20)
SELECT version_num FROM public.alembic_version;
```

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code or Alembic migrations.

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/tasks/notification_worker.py          ← WHY: understand existing Expo push delivery pattern to reuse
backend/app/models/notifications.py          ← WHY: understand MobileDevicePushToken model (if it exists)
backend/api/routes/settings.py               ← WHY: understand get_effective_setting() usage + route structure
backend/core/celery_app.py                   ← WHY: understand Beat schedule format + task module imports list
backend/openapi_schema_map.md                ← WHY: grep for "push-tokens" to know if registration endpoint exists
backend/services/tier_limit_enforcer.py      ← WHY: reference for get_effective_setting() service function
backend/db_models_map.md                     ← WHY: confirm MobileDevicePushToken and MobilePushRateLimit model names
```

Also run:
```bash
# Find push-token related files
grep -rn "push_token\|push-token\|MobileDevicePushToken" backend/ --include="*.py" -l

# Find existing Expo push delivery in notification_worker
grep -n "exp.host\|ExpoNotification\|expo_push" backend/tasks/notification_worker.py | head -20

# Check if push token registration endpoint already exists
grep -i "push.token\|push-token" backend/openapi_schema_map.md | head -10
```

---

## Background / Context

**What this batch does and why:**

The mobile app needs to sync data even when it's closed. When a tech clocks out or captures an expense with no signal, that data sits in WatermelonDB's offline queue. Currently only foreground triggers flush that queue. This batch adds the **server-side half** of background sync:

1. A Celery task that sends **silent push notifications** to mobile devices, waking them up to drain their sync queues
2. A Beat-scheduled scanner that periodically finds devices eligible for a background push
3. An endpoint the mobile app calls on startup to **register/update its push token** (so the server knows where to send pushes)
4. A settings endpoint that returns the background sync policy (interval, WiFi-only flag, battery floor) so the mobile app can enforce the correct behavior

The mobile side (Part B) registers OS background tasks (BGAppRefreshTask on iOS, WorkManager on Android) and wires the task handler to call the existing WatermelonDB sync orchestrator.

---

## Task 1 — Verify / Implement Push Token Registration Endpoint

### Step 1A — Check if endpoint already exists

```bash
grep -i "push.token\|push-token\|register.*token\|token.*register" backend/openapi_schema_map.md
grep -rn "push_token\|push-token" backend/api/routes/ --include="*.py" | head -20
```

**If the endpoint exists**: Skip to Task 2. Document the skip in your Completion Summary with the existing endpoint path.

**If the endpoint does NOT exist**: Implement per §D1 in the design doc.

### Step 1B — Implement push token registration (only if Step 1A = endpoint missing)

Locate the `MobileDevicePushToken` model in `backend/app/models/notifications.py` (or wherever `db_models_map.md` shows it). Confirm the exact table/column names match what MCP returned.

Create `backend/api/routes/mobile_push_tokens.py`:

```python
# backend/api/routes/mobile_push_tokens.py
# Standard route file pattern — read api/routes/settings.py for the header/import pattern

from sqlmodel import Session, select
from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from datetime import datetime, UTC
from typing import Literal

from core.db import get_db, set_audit_context_sync
from core.auth import get_current_user, AuthenticatedUser
from core.test_context import TestUserContext, get_test_context
from app.models.notifications import MobileDevicePushToken  # confirm exact import path

router = APIRouter(prefix="/mobile/push-tokens", tags=["mobile_push_tokens"])


class PushTokenRegisterRequest(BaseModel):
    device_id: str          # client-generated stable UUID stored in SecureStore
    platform: Literal["ios", "android"]
    push_token: str         # Expo push token or raw FCM token
    app_version: str | None = None
    os_version: str | None = None


class PushTokenRegisterResponse(BaseModel):
    id: str
    device_id: str
    registered_at: datetime
    last_seen_at: datetime


def _register_push_token_impl(
    req: PushTokenRegisterRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> PushTokenRegisterResponse:
    # Upsert: ON CONFLICT (user_id, device_id) → UPDATE token fields
    # Use raw select + update pattern (not db.get — must be tenant-scoped)
    existing = db.exec(
        select(MobileDevicePushToken)
        .where(MobileDevicePushToken.user_id == user_context.user_id)
        .where(MobileDevicePushToken.tenant_id == user_context.tenant_id)
        .where(MobileDevicePushToken.device_id == req.device_id)
    ).first()

    now_utc = datetime.now(UTC)
    if existing:
        existing.push_token = req.push_token
        existing.platform = req.platform
        existing.last_seen_at = now_utc
        if req.app_version:
            existing.app_version = req.app_version
        if req.os_version:
            existing.os_version = req.os_version
        existing.notification_permission_granted = True
        existing.revoked_at = None   # re-activate if previously revoked
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return PushTokenRegisterResponse(
            id=str(existing.id),
            device_id=str(existing.device_id),
            registered_at=existing.registered_at,
            last_seen_at=existing.last_seen_at,
        )
    else:
        row = MobileDevicePushToken(
            tenant_id=user_context.tenant_id,
            user_id=user_context.user_id,
            device_id=req.device_id,
            platform=req.platform,
            push_token=req.push_token,
            app_version=req.app_version,
            os_version=req.os_version,
            registered_at=now_utc,
            last_seen_at=now_utc,
            notification_permission_granted=True,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return PushTokenRegisterResponse(
            id=str(row.id),
            device_id=str(row.device_id),
            registered_at=row.registered_at,
            last_seen_at=row.last_seen_at,
        )


@router.post("/register", response_model=PushTokenRegisterResponse, status_code=200)
def register_push_token(
    req: PushTokenRegisterRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> PushTokenRegisterResponse:
    set_audit_context_sync(db, user_id=current_user.id)
    return _register_push_token_impl(req, db, current_user)


@router.post("/register/test", response_model=PushTokenRegisterResponse, status_code=200)
def register_push_token_test(
    req: PushTokenRegisterRequest,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> PushTokenRegisterResponse:
    """Test-only endpoint — bypasses JWT."""
    return _register_push_token_impl(req, db, ctx)
```

Register the router in `backend/app/main.py` at `/api/v1`.

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Add Background Sync Policy Endpoint

Add to `backend/api/routes/settings.py` (or a thin new file if settings.py is very large):

```python
# Add to existing settings.py router (read the file first for exact pattern)

class BackgroundSyncPolicyResponse(BaseModel):
    background_sync_enabled: bool
    background_sync_wifi_only: bool
    background_sync_battery_floor_pct: int
    background_sync_push_interval_minutes: int


@router.get("/background-sync-policy", response_model=BackgroundSyncPolicyResponse)
def get_background_sync_policy(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BackgroundSyncPolicyResponse:
    """Returns effective background sync policy for the authenticated user's tenant."""
    def _get(key: str, fallback):
        val, _ = get_effective_setting(db, current_user.tenant_id, key, fallback=fallback)
        return val

    return BackgroundSyncPolicyResponse(
        background_sync_enabled=bool(_get("background_sync_enabled", True)),
        background_sync_wifi_only=bool(_get("background_sync_wifi_only", False)),
        background_sync_battery_floor_pct=int(_get("background_sync_battery_floor_pct", 20)),
        background_sync_push_interval_minutes=int(_get("background_sync_push_interval_minutes", 5)),
    )
```

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 3 — Create Background Sync Push Celery Task

Create `backend/tasks/background_sync_push.py`. Read `notification_worker.py` first to understand:
- How Expo push tokens are validated/sent
- The `httpx` or `requests` call pattern to `https://exp.host/--/api/v2/push/send`
- Any existing `_send_expo_push()` helper to reuse

```python
# backend/tasks/background_sync_push.py
# Two-layer Celery task pattern per python-engr-std-prompt-inclusions.md §12

from datetime import datetime, UTC
from sqlmodel import Session, select
from celery.utils.log import get_task_logger

from core.celery_app import celery_app
from core.db import get_db
from app.models.notifications import MobileDevicePushToken, MobilePushRateLimit
# Import get_effective_setting from services (confirm exact import path)

logger = get_task_logger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def _dispatch_expo_silent_push(push_token: str, platform: str) -> bool:
    """
    Send a silent (data-only) push notification via Expo Push API.
    iOS: content-available=1, no title/body → wakes app silently
    Android: priority=high, data-only → wakes app via FCM high-priority
    
    Read notification_worker.py for the existing Expo API call pattern.
    Reuse the same httpx/requests client and error handling.
    """
    payload = {
        "to": push_token,
        "data": {"type": "background_sync"},
    }
    if platform == "ios":
        payload["_contentAvailable"] = True    # APNs content-available = 1
    elif platform == "android":
        payload["priority"] = "high"            # FCM high priority
    
    # Use the same HTTP call pattern as notification_worker.py
    # Return True on 200 with no errors, False otherwise
    # Do NOT raise exceptions — background task must not crash on push failure
    ...  # implement using notification_worker.py pattern


def _upsert_rate_limit(
    db: Session, tenant_id: str, device_id: str, now_utc: datetime
) -> None:
    """Update or create rate limit record for the device."""
    rate_row = db.exec(
        select(MobilePushRateLimit)
        .where(MobilePushRateLimit.device_id == device_id)
        .where(MobilePushRateLimit.tenant_id == tenant_id)
    ).first()
    if rate_row:
        rate_row.last_push_sent_at = now_utc
        rate_row.push_count_current_window += 1
        db.add(rate_row)
    else:
        rate_row = MobilePushRateLimit(
            tenant_id=tenant_id,
            device_id=device_id,
            last_push_sent_at=now_utc,
            push_count_current_window=1,
            window_start_at=now_utc,
        )
        db.add(rate_row)
    db.commit()


def _send_background_sync_push_impl(
    tenant_id: str,
    device_id: str,
    db: Session,
) -> dict:
    """
    Send a silent push to one device, respecting background_sync_enabled
    setting and mobile_push_rate_limit rate limiting.
    Returns {"sent": bool, "reason": str}
    """
    # 1. Check background sync enabled for tenant
    enabled, _ = get_effective_setting(db, tenant_id, "background_sync_enabled", fallback=True)
    if not enabled:
        return {"sent": False, "reason": "background_sync_disabled"}

    # 2. Load push interval
    interval_minutes, _ = get_effective_setting(
        db, tenant_id, "background_sync_push_interval_minutes", fallback=5
    )

    # 3. Load active push token (tenant-scoped, not revoked)
    token_row = db.exec(
        select(MobileDevicePushToken)
        .where(MobileDevicePushToken.device_id == device_id)
        .where(MobileDevicePushToken.tenant_id == tenant_id)
        .where(MobileDevicePushToken.revoked_at == None)  # noqa: E711
        .where(MobileDevicePushToken.notification_permission_granted == True)  # noqa: E712
    ).first()
    if not token_row:
        return {"sent": False, "reason": "no_active_token"}

    # 4. Rate limit check
    now_utc = datetime.now(UTC)
    rate_row = db.exec(
        select(MobilePushRateLimit)
        .where(MobilePushRateLimit.device_id == device_id)
        .where(MobilePushRateLimit.tenant_id == tenant_id)
    ).first()
    if rate_row:
        elapsed_minutes = (now_utc - rate_row.last_push_sent_at).total_seconds() / 60
        if elapsed_minutes < interval_minutes:
            return {"sent": False, "reason": f"rate_limited_{elapsed_minutes:.1f}m_of_{interval_minutes}m"}

    # 5. Dispatch push
    success = _dispatch_expo_silent_push(token_row.push_token, token_row.platform)

    # 6. Update rate limit record (regardless of push success — prevent spam retries)
    _upsert_rate_limit(db, tenant_id, device_id, now_utc)

    logger.info(
        "background_sync_push device=%s tenant=%s success=%s",
        device_id, tenant_id, success
    )
    return {"sent": success, "reason": "ok" if success else "push_api_error"}


@celery_app.task(name="tasks.background_sync_push.send_background_sync_push")
def send_background_sync_push(tenant_id: str, device_id: str) -> dict:
    """Celery task — sends silent push to one device. Entry point only."""
    with next(get_db()) as db:
        return _send_background_sync_push_impl(tenant_id, device_id, db)


def _scan_and_dispatch_impl(db: Session) -> dict:
    """
    Scan active push tokens and dispatch send_background_sync_push for each
    device that is due for a background sync push.
    
    Eligible devices:
    - notification_permission_granted = TRUE
    - revoked_at IS NULL
    - Either: no rate limit row exists, OR last_push_sent_at is older than
      the tenant's background_sync_push_interval_minutes setting
    
    This is a best-effort scan. Use a LEFT JOIN between mobile_device_push_token
    and mobile_push_rate_limit on (device_id, tenant_id).
    Filter to devices where:
      rate_limit.last_push_sent_at IS NULL
      OR rate_limit.last_push_sent_at < NOW() - INTERVAL '<interval> minutes'
    
    For simplicity: scan all active tokens, dispatch the per-device task
    (per-device rate limiting is enforced inside send_background_sync_push_impl).
    Cap at 500 devices per scan to prevent memory issues.
    """
    now_utc = datetime.now(UTC)
    active_tokens = db.exec(
        select(MobileDevicePushToken)
        .where(MobileDevicePushToken.revoked_at == None)  # noqa: E711
        .where(MobileDevicePushToken.notification_permission_granted == True)  # noqa: E712
        .limit(500)
    ).all()

    dispatched = 0
    for token in active_tokens:
        send_background_sync_push.delay(
            str(token.tenant_id),
            str(token.device_id),
        )
        dispatched += 1

    logger.info("background_sync_scan dispatched=%d", dispatched)
    return {"dispatched": dispatched, "scanned_at": now_utc.isoformat()}


@celery_app.task(name="tasks.background_sync_push.scan_and_dispatch_background_sync_pushes")
def scan_and_dispatch_background_sync_pushes() -> dict:
    """Beat task — runs every 60 seconds; dispatches per-device push tasks."""
    with next(get_db()) as db:
        return _scan_and_dispatch_impl(db)
```

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 4 — Register Task + Beat Schedule in celery_app.py

Open `backend/core/celery_app.py`. Add:

1. To the `imports` list: `"tasks.background_sync_push"`
2. To the Beat `beat_schedule` dict:

```python
"scan-background-sync-pushes": {
    "task": "tasks.background_sync_push.scan_and_dispatch_background_sync_pushes",
    "schedule": 60.0,  # every 60 seconds
},
```

Read `celery_app.py` first to understand the exact Beat schedule format already in use.

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 5 — Write Tests

Create test files in the correct domain folders.

### Test file 1: `backend/tests/domains/mobile_offline/test_mob_b8_push_registration.py`

```python
pytestmark = [
    pytest.mark.domain_mobile_offline,
    pytest.mark.unit,
]
```

Tests (6–8 total):
1. `test_register_new_push_token` — POST to `/register/test` creates row with correct tenant/user/device
2. `test_register_updates_existing_token` — calling `/register/test` twice with same device_id updates `push_token`, `last_seen_at`
3. `test_register_revived_revoked_token` — device with `revoked_at` set gets re-activated (revoked_at = None) on re-register
4. `test_register_invalid_platform` — platform=`"web"` returns 422
5. `test_register_empty_push_token` — empty `push_token` string returns 422

### Test file 2: `backend/tests/domains/mobile_offline/test_mob_b8_sync_policy.py`

```python
pytestmark = [
    pytest.mark.domain_mobile_offline,
    pytest.mark.unit,
]
```

Tests (4 total):
1. `test_sync_policy_returns_defaults` — GET `/api/v1/settings/background-sync-policy` returns the 4 default values when no tenant override
2. `test_sync_policy_returns_correct_types` — all 4 fields have correct Python types (bool, bool, int, int)
3. `test_sync_policy_requires_auth` — unauthenticated request returns 401
4. `test_sync_policy_tenant_isolation` — tenant_a cannot see tenant_b's settings

### Test file 3: `backend/tests/domains/mobile_offline/test_mob_b8_celery_push.py`

```python
pytestmark = [
    pytest.mark.domain_mobile_offline,
    pytest.mark.unit,
]
```

Tests (5 total — test `_impl` functions directly, never call `.delay()`):
1. `test_send_push_disabled_by_setting` — when `background_sync_enabled=false`, `_send_background_sync_push_impl` returns `{"sent": False, "reason": "background_sync_disabled"}`
2. `test_send_push_no_active_token` — device with no token row returns `{"sent": False, "reason": "no_active_token"}`
3. `test_send_push_rate_limited` — device pushed <1 min ago (with 5-min interval) returns `{"sent": False, "reason": starts with "rate_limited_"}`
4. `test_send_push_revoked_token_skipped` — device with `revoked_at` set returns `no_active_token`
5. `test_scan_dispatches_active_tokens` — `_scan_and_dispatch_impl()` with 2 active tokens returns `{"dispatched": 2, ...}`; mock `send_background_sync_push.delay` to capture calls

> **Note on test 5**: Use `unittest.mock.patch` to mock `send_background_sync_push.delay` — never call the actual Celery task or Expo API in unit tests.

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

- Domain for all 3 test files: `mobile_offline` → folder `tests/domains/mobile_offline/`
- `pytestmark = [pytest.mark.domain_mobile_offline, pytest.mark.unit]`
- Use `client` fixture (never module-level `TestClient`)
- Use `test_tenant` and `test_user` fixtures (no hardcoded UUIDs)
- Use `second_tenant` for tenant-isolation tests
- Never assert on total row counts — always scope by inserted ID
- `mock_entitlement_allowed` autouse applies — add `@pytest.mark.skip_mock_entitlement_allowed` only if a test exercises entitlement gating (none in this batch)

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

Fix any failure before proceeding to Phase 2.

### Phase 2 — Full Suite + Export

```bash
cd <repo>/backend
source .venv/bin/activate

# Full suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Domain-specific check
python -m pytest tests/domains/mobile_offline/ -v 2>&1 | tail -20

# Regenerate OpenAPI (new endpoints added)
python export_openapi_json.py

# Verify new endpoints appear
grep -A 5 "background-sync-policy" backend/openapi_schema_map.md
grep -A 5 "push-tokens" backend/openapi_schema_map.md

# Regenerate DB model map if any model files changed
python generate_db_model_map.py

echo "=== MOB-B8-PART-A FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before declaring done.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [ ] All MCP pre-work queries run — `mobile_device_push_token`, `mobile_push_rate_limit`, `mobile_sync_session` columns confirmed; all 4 background sync settings confirmed in catalog
- [ ] All mandatory source files read before writing code (`notification_worker.py`, `settings.py`, `celery_app.py`, `db_models_map.md`, `openapi_schema_map.md`)
- [ ] **Task 1**: Push token registration endpoint — either confirmed-existing (skipped) OR `POST /api/v1/mobile/push-tokens/register` + `/test` implemented and registered in `main.py`
- [ ] **Task 2**: `GET /api/v1/settings/background-sync-policy` endpoint added to `settings.py` returning all 4 typed fields
- [ ] **Task 3**: `backend/tasks/background_sync_push.py` created — `_send_background_sync_push_impl`, `send_background_sync_push` task, `_scan_and_dispatch_impl`, `scan_and_dispatch_background_sync_pushes` Beat task — all using two-layer pattern
- [ ] **Task 4**: `core/celery_app.py` updated — `tasks.background_sync_push` in imports; `scan-background-sync-pushes` in beat_schedule at 60s
- [ ] `set_audit_context_sync()` called in push token registration endpoint
- [ ] All new API errors follow RFC 7807 Problem Details format
- [ ] All 3 new test files created in `tests/domains/mobile_offline/`
- [ ] All test files use `pytestmark` with `domain_mobile_offline` + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] `db.get()` not used on any tenant-scoped model
- [ ] `python export_openapi_json.py` run — `openapi.json` and `openapi_schema_map.md` updated
- [ ] `python generate_db_model_map.py` run if any model files changed
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures including integration
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §Phase 1 Batch 9

---

## Handoff Instructions (After Part A is Done)

After all Definition of Done items are complete:

1. Run `python export_openapi_json.py` — confirm `openapi.json` and `openapi_schema_map.md` are updated
2. Commit all changes
3. **Notify the React Native Engineer that MOB-B8 Part B is unblocked**
4. The React Native Engineer's first step is `pnpm sync-api-types` in the `frontend/` directory

---

## Completion Summary

After all Definition of Done items are complete, add a Completion Summary to `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch 9 — Background-Sync-B1 using the format below:

```markdown
### MOB-B8 Part A — Background Sync Backend: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Push token endpoint: created or skipped (state which)]
- [background-sync-policy endpoint added to settings.py]
- [background_sync_push.py Celery task created]
- [Beat schedule registered at 60s]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/tasks/background_sync_push.py` | Created |
| `backend/api/routes/settings.py` | Updated — background-sync-policy endpoint |
| `backend/core/celery_app.py` | Updated — task registered + Beat schedule |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/mobile_offline/test_mob_b8_push_registration.py` | `domain_mobile_offline` | N | ✅ |
| `tests/domains/mobile_offline/test_mob_b8_sync_policy.py` | `domain_mobile_offline` | N | ✅ |
| `tests/domains/mobile_offline/test_mob_b8_celery_push.py` | `domain_mobile_offline` | N | ✅ |
```
