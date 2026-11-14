# Implementation Prompt: BE-UI-NAV-S1 — Settings Navigation Backend (Avatar Upload + Tenant Notification Defaults)

**Mode**: Pilot Python Engineer  
**Batch**: `BE-UI-NAV-S1`  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 Active Dev Work Queue  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-be-ui-nav-s1-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: `FE-UI-NAV-S1` — React Engineer starts after this batch and OpenAPI regen are committed  

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names or S3 bucket settings names. Verify with MCP and `grep` before use. If MCP returns unexpected results → **STOP and ask Tom**.
- **Rule 2**: After endpoint changes → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 3**: After model file changes → run `python generate_db_model_map.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with explicit `WHERE tenant_id = :tid`.
- **Rule 8**: All API errors MUST follow RFC 7807 Problem Details format — `{"type": "...", "title": "...", "status": N, "detail": "..."}`. Never use plain string `detail`.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before any `db.add()` or `db.commit()`.
- **Rule 11**: If ANY test fails — even pre-existing — fix it before declaring the batch done.

**⚠️ No Alembic migrations in this batch.** All required DB columns already exist:
- `user.profile_photo_s3_key TEXT NULL` ✅ (verified via MCP before designing)
- `notification_default_policy(tenant_id UUID NULL, category_id TEXT, channel TEXT, enabled BOOL)` ✅

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count. If any tests are already failing → confirm with Tom before proceeding.

---

## Pre-Work: Run MCP Verification Queries

Run all of these via `postgres-local` MCP before writing any code. If unexpected results → **STOP and ask Tom**.

```sql
-- 1. Verify user.profile_photo_s3_key exists with correct type
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user'
  AND column_name = 'profile_photo_s3_key';

-- 2. Verify notification_default_policy table and columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'notification_default_policy'
ORDER BY ordinal_position;

-- 3. Verify no existing bulk tenant-policy GET endpoint collision
-- (confirm what routes already exist in the file)
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'notification_default_policy';

-- 4. Check current alembic head (no migration expected, but confirm state)
SELECT version_num FROM public.alembic_version;
```

> **MCP Usage Rule**: Read-only verification only. Never INSERT, UPDATE, or DELETE via MCP.

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/api/routes/user_profile.py           ← understand existing PATCH /me/profile endpoint + UserProfileResponse schema
backend/api/routes/notification_preferences.py ← understand existing per-category tenant-policy endpoints (PUT/DELETE /tenant-policy/{cat}/{chan})
backend/api/routes/public_invoices.py         ← understand existing S3 presigned URL generation pattern (boto3 client, bucket settings)
backend/core/config.py                        ← find exact S3 bucket settings attribute names
backend/api/schemas/schemas.py                ← understand existing Pydantic schema patterns
backend/tests/conftest.py                     ← understand available fixtures
backend/db_models_map.md                      ← confirm NotificationDefaultPolicy model name
```

Also run:

```bash
# Confirm S3 bucket settings attribute names
grep -n "S3_BUCKET\|PHOTOS\|BUCKET" backend/core/config.py

# Confirm NotificationDefaultPolicy model location
grep -rn "NotificationDefaultPolicy\|notification_default_policy" backend/app/models/ -l

# Confirm existing notification_preferences router structure
grep -n "@router\|def " backend/api/routes/notification_preferences.py | head -40
```

---

## Background / Context

This batch adds 5 new or modified endpoints to enable the FE-UI-NAV-S1 frontend batch:

1. **`profile_photo_url`** field added to `UserProfileResponse` — generates a signed S3 GET URL from `profile_photo_s3_key`
2. **Avatar presigned upload URL** — client calls this, gets a PUT URL + S3 key, uploads blob directly to S3, then calls `PATCH /me/profile` with the key
3. **Avatar delete** — clears `profile_photo_s3_key` from the user record
4. **Bulk tenant policy GET** — returns all tenant-override rows from `notification_default_policy` (frontend matrix pre-population)
5. **Bulk tenant policy reset (DELETE)** — removes all tenant-override rows (reverts to system defaults)

**No migrations. No new models.** All DB schema already exists.

---

## Task 1 — Add `profile_photo_url` to `UserProfileResponse`

**File**: `backend/api/routes/user_profile.py`

**Step 1a** — Read the file in full before editing.

**Step 1b** — Add a helper function for generating signed GET URLs. Read `public_invoices.py` first to find the exact boto3 pattern used in the codebase. Replicate the same pattern; do not invent a new one.

```python
# Add near top of user_profile.py (after imports)
def _generate_avatar_url(s3_key: str | None) -> str | None:
    """Generate a 1-hour presigned GET URL for the profile photo. Gracefully returns None on error."""
    if not s3_key:
        return None
    try:
        import boto3
        from core.config import settings as app_settings
        s3 = boto3.client("s3", region_name=app_settings.AWS_REGION)
        return s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": app_settings.S3_BUCKET_PHOTOS,   # ← verify exact name from config.py
                "Key": s3_key,
            },
            ExpiresIn=3600,
        )
    except Exception:
        return None  # Graceful degradation — no URL, no crash
```

> **Before writing**: Run `grep -n "S3_BUCKET\|PHOTOS" backend/core/config.py` to confirm the exact attribute name for the photos S3 bucket. Use whatever the codebase actually has.

**Step 1c** — Add `profile_photo_url: str | None` to `UserProfileResponse`:

```python
class UserProfileResponse(BaseModel):
    first_name: str | None
    last_name: str | None
    phone_number: str | None
    time_zone: str | None
    profile_photo_s3_key: str | None
    profile_photo_url: str | None  # ← NEW
    language_preference: str
```

**Step 1d** — Update `_update_profile_impl` and `_get_profile_impl` to populate the new field:

```python
return UserProfileResponse(
    # ... existing fields ...
    profile_photo_s3_key=user.profile_photo_s3_key,
    profile_photo_url=_generate_avatar_url(user.profile_photo_s3_key),  # ← NEW
    language_preference=user.language_preference or "en",
)
```

**Intermediate verification:**
```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

---

## Task 2 — Avatar Presigned Upload URL Endpoint

**File**: `backend/api/routes/user_profile.py` (add to same file/router)

Add these schemas and endpoints. Read the file structure first — follow the existing dual-endpoint pattern exactly.

**New schemas** (add to `user_profile.py`):

```python
class AvatarPresignedUrlResponse(BaseModel):
    upload_url: str   # S3 presigned PUT URL (15-min TTL)
    s3_key: str       # key to pass back in PATCH /api/v1/users/me/profile

class AvatarDeleteResponse(BaseModel):
    success: bool = True
```

**Shared implementation**:

```python
def _generate_avatar_presigned_url_impl(
    user_context: AuthenticatedUser | TestUserContext,
) -> AvatarPresignedUrlResponse:
    """Generate a presigned PUT URL for avatar upload. No DB write here — key stored via PATCH /me/profile."""
    import boto3
    from core.config import settings as app_settings

    s3_key = f"avatars/{user_context.tenant_id}/{user_context.id}/avatar.jpg"
    try:
        s3 = boto3.client("s3", region_name=app_settings.AWS_REGION)
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": app_settings.S3_BUCKET_PHOTOS,  # ← verify from config.py
                "Key": s3_key,
                "ContentType": "image/jpeg",
            },
            ExpiresIn=900,  # 15 minutes
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "https://errors.pilotfortrades.com/s3-error",
                "title": "S3 presigned URL generation failed",
                "status": 500,
                "detail": f"Could not generate upload URL: {exc}",
            },
        )
    return AvatarPresignedUrlResponse(upload_url=upload_url, s3_key=s3_key)
```

**Endpoints** (add after existing profile endpoints):

```python
@router.post("/me/avatar/presigned-url/test", response_model=AvatarPresignedUrlResponse, status_code=201)
def get_avatar_presigned_url_test(
    db: Session = Depends(get_db),
):
    """[TEST] Generate avatar presigned upload URL — no auth."""
    test_context = get_test_context()
    return _generate_avatar_presigned_url_impl(test_context)


@router.post("/me/avatar/presigned-url", response_model=AvatarPresignedUrlResponse, status_code=201)
def get_avatar_presigned_url(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    POST /api/v1/users/me/avatar/presigned-url

    Generate a presigned S3 PUT URL for uploading a profile photo.
    Client flow:
      1. Call this endpoint → receive upload_url + s3_key
      2. PUT cropped JPEG blob to upload_url directly (S3, not through API)
      3. Call PATCH /api/v1/users/me/profile with { profile_photo_s3_key: s3_key }
    """
    require_permission(user.permissions, "mfa.enroll_self")
    return _generate_avatar_presigned_url_impl(user)
```

---

## Task 3 — Avatar Delete Endpoint

**File**: `backend/api/routes/user_profile.py` (same router)

```python
def _delete_avatar_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> AvatarDeleteResponse:
    """Clear profile_photo_s3_key from the user record. Best-effort S3 delete."""
    user = db.exec(
        select(User)
        .where(User.id == user_context.id)
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "User not found",
                "status": 404,
                "detail": "User record not found.",
            },
        )

    old_key = user.profile_photo_s3_key
    user.profile_photo_s3_key = None
    db.add(user)
    db.commit()

    # Best-effort S3 delete — never fail the endpoint if S3 delete errors
    if old_key:
        try:
            import boto3
            from core.config import settings as app_settings
            s3 = boto3.client("s3", region_name=app_settings.AWS_REGION)
            s3.delete_object(Bucket=app_settings.S3_BUCKET_PHOTOS, Key=old_key)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Failed to delete avatar from S3 (key=%s): %s", old_key, exc)

    return AvatarDeleteResponse(success=True)


@router.delete("/me/avatar/test", response_model=AvatarDeleteResponse)
def delete_avatar_test(
    db: Session = Depends(get_db),
):
    """[TEST] Delete avatar — no auth."""
    test_context = get_test_context()
    return _delete_avatar_impl(test_context, db)


@router.delete("/me/avatar", response_model=AvatarDeleteResponse)
def delete_avatar(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    DELETE /api/v1/users/me/avatar

    Remove profile photo. Clears profile_photo_s3_key on user record.
    Best-effort S3 object deletion (logged on failure, endpoint always succeeds).
    """
    require_permission(user.permissions, "mfa.enroll_self")
    set_audit_context_sync(db, user_id=user.id)
    return _delete_avatar_impl(user, db)
```

**Intermediate verification:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

---

## Task 4 — Bulk Tenant Policy GET

**File**: `backend/api/routes/notification_preferences.py`

Read this file completely before adding. Find where to insert the new endpoint — after the existing per-category `PUT/DELETE /tenant-policy/{category_id}/{channel}` endpoints.

**New schemas** (add to `notification_preferences.py` or `schemas.py` — follow existing conventions in the file):

```python
class TenantPolicyEntry(BaseModel):
    category_id: str
    channel: str
    enabled: bool

class TenantPolicyListResponse(BaseModel):
    policies: list[TenantPolicyEntry]

class TenantPolicyResetResponse(BaseModel):
    deleted_count: int
```

**New endpoints**:

```python
def _get_tenant_policy_impl(
    tenant_id: UUID,
    db: Session,
) -> TenantPolicyListResponse:
    """Return all tenant-override policy rows for this tenant (tenant_id IS NOT NULL)."""
    rows = db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == tenant_id
        )
    ).all()
    return TenantPolicyListResponse(
        policies=[
            TenantPolicyEntry(
                category_id=r.category_id,
                channel=r.channel,
                enabled=r.enabled,
            )
            for r in rows
        ]
    )


@router.get("/tenant-policy/test", response_model=TenantPolicyListResponse)
def get_tenant_policy_test(
    db: Session = Depends(get_db),
):
    """[TEST] Get all tenant notification policy overrides — no auth."""
    ctx = get_test_context()
    return _get_tenant_policy_impl(ctx.tenant_id, db)


@router.get("/tenant-policy", response_model=TenantPolicyListResponse)
def get_tenant_policy(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.tenant_default.edit")
    ),
) -> TenantPolicyListResponse:
    """
    GET /api/v1/notifications/tenant-policy

    Return all tenant-level notification default policy rows for the requesting tenant.
    Empty list = no overrides (all defaults come from system rows where tenant_id IS NULL).
    Used by the frontend to pre-populate the team notification defaults matrix.

    Permission: notification_preference.tenant_default.edit (owner/operator only)
    """
    return _get_tenant_policy_impl(current_user.tenant_id, db)
```

---

## Task 5 — Bulk Tenant Policy Reset (DELETE)

**File**: `backend/api/routes/notification_preferences.py` (same router)

```python
def _reset_tenant_policy_impl(
    tenant_id: UUID,
    db: Session,
    user_id: UUID | None = None,
) -> TenantPolicyResetResponse:
    """Delete all tenant-override rows. System defaults (tenant_id=NULL) are never touched."""
    if user_id:
        set_audit_context_sync(db, user_id=user_id)

    rows = db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == tenant_id
        )
    ).all()
    deleted_count = len(rows)
    for row in rows:
        db.delete(row)
    db.commit()
    return TenantPolicyResetResponse(deleted_count=deleted_count)


@router.delete("/tenant-policy/test", response_model=TenantPolicyResetResponse)
def reset_tenant_policy_test(
    db: Session = Depends(get_db),
):
    """[TEST] Reset all tenant notification policy overrides — no auth."""
    ctx = get_test_context()
    return _reset_tenant_policy_impl(ctx.tenant_id, db)


@router.delete("/tenant-policy", response_model=TenantPolicyResetResponse)
def reset_tenant_policy(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.tenant_default.edit")
    ),
) -> TenantPolicyResetResponse:
    """
    DELETE /api/v1/notifications/tenant-policy

    Remove all tenant-level notification default policy overrides.
    Reverts the tenant to system defaults (notification_default_policy rows where tenant_id IS NULL).
    System default rows are NEVER deleted by this endpoint.

    Permission: notification_preference.tenant_default.edit (owner/operator only)
    """
    set_audit_context_sync(db, user_id=current_user.id)
    return _reset_tenant_policy_impl(current_user.tenant_id, db, user_id=current_user.id)
```

---

## Task 6 — OpenAPI Regeneration

After all endpoints are implemented and tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify new endpoints appear:
```bash
grep -A 3 "avatar" backend/openapi_schema_map.md
grep -A 3 "tenant-policy" backend/openapi_schema_map.md
```

Expected new paths:
- `POST /api/v1/users/me/avatar/presigned-url`
- `DELETE /api/v1/users/me/avatar`
- `GET /api/v1/notifications/tenant-policy`
- `DELETE /api/v1/notifications/tenant-policy`
- `profile_photo_url` field in `UserProfileResponse`

---

## Test Requirements

### Test file 1 — Avatar endpoints

**File**: `backend/tests/domains/identity_access/test_be_ui_nav_s1_avatar.py`

```python
pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]
```

**Required test cases:**

1. `test_get_profile_includes_photo_url_when_key_set` — mock S3 `generate_presigned_url`; PATCH profile with s3_key; GET profile; assert `profile_photo_url` is not None
2. `test_get_profile_photo_url_none_when_no_key` — GET profile with no s3_key; assert `profile_photo_url` is None
3. `test_avatar_presigned_url_test_endpoint_returns_upload_url` — mock boto3 S3 client; call test endpoint; assert `upload_url` and `s3_key` in response
4. `test_delete_avatar_clears_s3_key` — set s3_key on test user; call DELETE /test; GET profile; assert `profile_photo_s3_key` is None
5. `test_delete_avatar_no_key_succeeds` — delete when no key set; assert 200

**Mocking S3** — mock at boto3 level:
```python
from unittest.mock import patch, MagicMock

@patch("boto3.client")
def test_avatar_presigned_url_test_endpoint_returns_upload_url(mock_boto3, client, test_tenant):
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned-url"

    resp = client.post("/api/v1/users/me/avatar/presigned-url/test")
    assert resp.status_code == 201
    data = resp.json()
    assert "upload_url" in data
    assert "s3_key" in data
```

### Test file 2 — Tenant notification policy endpoints

**File**: `backend/tests/domains/notifications_comms/test_be_ui_nav_s1_tenant_policy.py`

```python
pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]
```

**Required test cases:**

1. `test_get_tenant_policy_test_endpoint_returns_list` — call GET /test; assert `policies` list in response (may be empty)
2. `test_reset_tenant_policy_deletes_only_tenant_rows` — insert 2 tenant rows + verify system rows (tenant_id=NULL) exist; call DELETE /test; assert 200 + `deleted_count=2`; confirm system rows with `tenant_id=NULL` are untouched
3. `test_reset_tenant_policy_empty_tenant_returns_zero` — no tenant rows; call DELETE /test; assert `deleted_count=0`
4. `test_get_tenant_policy_isolates_by_tenant` — insert rows for `tenant_a` and `tenant_b`; GET with `user_tenant_a` JWT; assert only `tenant_a` rows returned
5. `test_reset_tenant_policy_requires_owner_permission` — call DELETE with tech-role JWT; assert 403

> **Test rule**: For the system rows isolation test (#2), you must verify via direct SQL that `notification_default_policy` rows where `tenant_id IS NULL` still exist after the reset. Do NOT use `db.delete()` on those rows — use a SELECT to confirm they persist.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

Fix any failure before moving to the next task.

### Phase 2 — Full Suite (run once at the end before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Full suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Domain spot checks
python -m pytest tests/domains/identity_access/test_be_ui_nav_s1_avatar.py -v 2>&1 | tail -20
python -m pytest tests/domains/notifications_comms/test_be_ui_nav_s1_tenant_policy.py -v 2>&1 | tail -20

# Confirm new endpoints in OpenAPI map
grep -A 3 "avatar/presigned-url" backend/openapi_schema_map.md
grep -A 3 "tenant-policy" backend/openapi_schema_map.md

echo "=== BE-UI-NAV-S1 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

Update `dev-docs/analysis/pilot-launch-plan.md` §2 when each item is done:

- [ ] Pre-modification regression baseline captured (`pytest -m unit`) — zero pre-existing failures confirmed or cleared
- [ ] All MCP pre-work queries run — confirmed `profile_photo_s3_key` exists, `notification_default_policy` exists
- [ ] `grep "S3_BUCKET\|PHOTOS" backend/core/config.py` confirmed exact S3 settings attribute name
- [ ] All mandatory source files read before writing any code
- [ ] **TASK 1**: `profile_photo_url` added to `UserProfileResponse`; `_generate_avatar_url()` helper added; both `_get_profile_impl` and `_update_profile_impl` populate the field
- [ ] **TASK 2**: `POST /api/v1/users/me/avatar/presigned-url` (+ `/test`) — returns `{upload_url, s3_key}`
- [ ] **TASK 3**: `DELETE /api/v1/users/me/avatar` (+ `/test`) — clears key; best-effort S3 delete; audit context set
- [ ] **TASK 4**: `GET /api/v1/notifications/tenant-policy` (+ `/test`) — returns all tenant-override rows
- [ ] **TASK 5**: `DELETE /api/v1/notifications/tenant-policy` (+ `/test`) — deletes only tenant rows; system rows untouched; audit context set
- [ ] All new API errors follow RFC 7807 Problem Details format
- [ ] `set_audit_context_sync()` called on `DELETE /avatar` and `DELETE /tenant-policy`
- [ ] S3 boto3 calls mocked in tests — no real S3 calls in unit tests
- [ ] `test_be_ui_nav_s1_avatar.py` — 5 tests pass
- [ ] `test_be_ui_nav_s1_tenant_policy.py` — 5 tests pass
- [ ] `pytestmark` with domain marker + `pytest.mark.unit` on all new test files
- [ ] `python export_openapi_json.py` run — all 4 new paths appear in `openapi_schema_map.md`
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes — zero new failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B

---

## Handoff Instructions to React Engineer

After all Definition of Done items are complete:

1. Run `python export_openapi_json.py` and commit both `openapi.json` and `openapi_schema_map.md`
2. Notify the React Engineer that `BE-UI-NAV-S1` is complete
3. React Engineer must run `pnpm sync-api-types` as their first Pre-Work step before implementing `FE-UI-NAV-S1`
4. The React Engineer should remove MSW stubs for avatar and tenant-policy endpoints and wire the real hooks after `pnpm sync-api-types` delivers the types

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` Appendix B using this format:

```markdown
### BE-UI-NAV-S1 — Settings Navigation Backend: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Added `profile_photo_url` (signed S3 GET URL) to `UserProfileResponse`
- Added `POST /api/v1/users/me/avatar/presigned-url` — presigned S3 PUT URL for avatar upload
- Added `DELETE /api/v1/users/me/avatar` — clears profile photo; best-effort S3 delete
- Added `GET /api/v1/notifications/tenant-policy` — bulk fetch tenant notification overrides
- Added `DELETE /api/v1/notifications/tenant-policy` — bulk reset to system defaults

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/routes/user_profile.py` | Updated — `profile_photo_url` in response; 2 new endpoints (presigned-url, avatar delete) |
| `backend/api/routes/notification_preferences.py` | Updated — 2 new endpoints (bulk GET, bulk DELETE tenant-policy) |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/tests/domains/identity_access/test_be_ui_nav_s1_avatar.py` | Created — 5 tests |
| `backend/tests/domains/notifications_comms/test_be_ui_nav_s1_tenant_policy.py` | Created — 5 tests |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/identity_access/test_be_ui_nav_s1_avatar.py` | `domain_identity_access` | 5 | ✅ |
| `tests/domains/notifications_comms/test_be_ui_nav_s1_tenant_policy.py` | `domain_notifications_comms` | 5 | ✅ |
```
