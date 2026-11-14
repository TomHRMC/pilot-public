# Batch Design: BE-UI-NAV-S1 — Settings Navigation Backend (Avatar Upload + Tenant Notification Defaults)

**Batch code**: `BE-UI-NAV-S1`  
**Type**: Backend only (`backend/`) — Python Engineer  
**Frontend companion**: `FE-UI-NAV-S1` — depends on this batch for real endpoints; stubs with MSW until this lands  
**Design spec**: `batch-ui-nav-s1-ui-design-spec.md` §21, §25–§29  
**Estimated effort**: 2–3 hours  
**Date**: 2026-07-21  

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| UI design spec | §21 (avatar upload), §29 (notification arch) | Avatar: presigned S3 URL → crop → upload → store key. Tenant defaults: separate page, owner-only |
| `user_profile.py` | Full file | Already has `PATCH /api/v1/users/me/profile` accepting `profile_photo_s3_key`; returns `profile_photo_s3_key` raw (no signed URL) |
| `notification_preferences.py` | Full file (search results) | Already has `PUT/DELETE /api/v1/notifications/tenant-policy/{category_id}/{channel}` and `GET /api/v1/notifications/preferences` |
| `notification_categories.py` | Search results | Already has `GET /api/v1/notifications/categories` with tenant-level resolution |
| Live DB — `user` table | MCP query | `profile_photo_s3_key TEXT NULL` already exists — **no migration needed** |
| Live DB — `notification_default_policy` | MCP query | `(tenant_id UUID NULL, category_id TEXT, channel TEXT, enabled BOOL)` — already exists |
| Live DB — `notification_category` | MCP query | `(code, display_label, description, category_group_id, display_order)` — no `id` PK; `code` is the PK |
| Live DB — `notification_preference` | MCP query | `(tenant_id, user_id NULL, category_id, channel, enabled)` |

---

## B. Migration Plan

**No database migrations required for this batch.**

All required tables already exist:
- `user.profile_photo_s3_key TEXT NULL` ✅
- `notification_default_policy(tenant_id UUID NULL, category_id TEXT, channel TEXT, enabled BOOL)` ✅

---

## C. Execution Order

| # | Task | Endpoint(s) | Notes |
|---|---|---|---|
| 1 | Add `profile_photo_url` to `UserProfileResponse` | `GET /api/v1/users/me/profile` | Generate signed S3 GET URL from `profile_photo_s3_key`; NULL-safe |
| 2 | Avatar presigned upload URL endpoint | `POST /api/v1/users/me/avatar/presigned-url` | Returns `{ upload_url, s3_key }` — client uploads blob directly to S3 |
| 3 | Avatar delete endpoint | `DELETE /api/v1/users/me/avatar` | Sets `user.profile_photo_s3_key = None`; optionally deletes S3 object |
| 4 | Bulk tenant notification defaults GET | `GET /api/v1/notifications/tenant-policy` | Returns all tenant policy rows for requesting tenant |
| 5 | Bulk tenant notification defaults reset | `DELETE /api/v1/notifications/tenant-policy` | Deletes all `notification_default_policy` rows where `tenant_id = requesting tenant` |
| 6 | Regenerate OpenAPI + run tests | — | `python export_openapi_json.py` after all changes |

---

## D. New API Endpoints

### D.1 — `GET /api/v1/users/me/profile` (MODIFIED — add `profile_photo_url`)

**File**: `backend/api/routes/user_profile.py`  
**Change**: Add `profile_photo_url: str | None` to `UserProfileResponse`; populate in both `_update_profile_impl` and `_get_profile_impl` by calling `generate_presigned_url(user.profile_photo_s3_key)` when the key is not None.

```python
class UserProfileResponse(BaseModel):
    first_name: str | None
    last_name: str | None
    phone_number: str | None
    time_zone: str | None
    profile_photo_s3_key: str | None      # raw key (kept for backward compat)
    profile_photo_url: str | None         # ← NEW: signed S3 GET URL (1hr TTL)
    language_preference: str
```

**Signed URL generation** (add helper):
```python
import boto3
from core.config import settings as app_settings

def _generate_avatar_url(s3_key: str | None) -> str | None:
    """Generate a 1-hour presigned GET URL for the profile photo."""
    if not s3_key:
        return None
    s3 = boto3.client("s3", region_name=app_settings.AWS_REGION)
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": app_settings.S3_BUCKET_PHOTOS, "Key": s3_key},
        ExpiresIn=3600,
    )
```

> **MCP verification required**: Confirm `S3_BUCKET_PHOTOS` is the correct settings attribute name for the photos bucket before using it. Run `grep -n "S3_BUCKET\|PHOTOS" backend/core/config.py` before writing.

---

### D.2 — `POST /api/v1/users/me/avatar/presigned-url` (NEW)

**File**: `backend/api/routes/user_profile.py` (add to existing router)  
**Auth**: JWT required, `mfa.enroll_self` permission (same as PATCH profile)  
**RBAC**: Any authenticated role (all users can upload their own avatar)

```
POST /api/v1/users/me/avatar/presigned-url
POST /api/v1/users/me/avatar/presigned-url/test  ← test variant
```

**Request**: no body (or optional `content_type: str = "image/jpeg"`)

**Response** `201`:
```python
class AvatarPresignedUrlResponse(BaseModel):
    upload_url: str     # S3 presigned PUT URL (15-minute TTL)
    s3_key: str         # key to pass back in PATCH /api/v1/users/me/profile
```

**Implementation logic**:
```python
# Generate a unique S3 key for this user's avatar
s3_key = f"avatars/{user.tenant_id}/{user.id}/avatar.jpg"

s3 = boto3.client("s3", region_name=app_settings.AWS_REGION)
upload_url = s3.generate_presigned_url(
    "put_object",
    Params={
        "Bucket": app_settings.S3_BUCKET_PHOTOS,
        "Key": s3_key,
        "ContentType": "image/jpeg",
    },
    ExpiresIn=900,  # 15 minutes
)
return AvatarPresignedUrlResponse(upload_url=upload_url, s3_key=s3_key)
```

**Error codes**:
| Code | Condition |
|---|---|
| `500` | S3 client error generating presigned URL — RFC 7807 |

---

### D.3 — `DELETE /api/v1/users/me/avatar` (NEW)

**File**: `backend/api/routes/user_profile.py`  
**Auth**: JWT required  
**RBAC**: `mfa.enroll_self` (same as profile PATCH)

```
DELETE /api/v1/users/me/avatar
DELETE /api/v1/users/me/avatar/test  ← test variant
```

**Request**: no body

**Response** `200`:
```python
class AvatarDeleteResponse(BaseModel):
    success: bool = True
```

**Implementation logic**:
```python
# 1. Set profile_photo_s3_key = None
set_audit_context_sync(db, user_id=user.id)
user.profile_photo_s3_key = None
db.add(user)
db.commit()

# 2. Optionally delete from S3 (best-effort; do NOT fail the endpoint if S3 delete fails)
# Pattern: try/except around s3.delete_object(); log warning if error
```

**Error codes**:
| Code | Condition |
|---|---|
| `404` | User not found (should not occur for authenticated user) |

---

### D.4 — `GET /api/v1/notifications/tenant-policy` (NEW)

**File**: `backend/api/routes/notification_preferences.py` (add to existing router)  
**Auth**: JWT required  
**Permission**: `notification_preference.tenant_default.edit` (owner/operator only)

```
GET /api/v1/notifications/tenant-policy
GET /api/v1/notifications/tenant-policy/test  ← test variant
```

**Request**: no params

**Response** `200`:
```python
class TenantPolicyEntry(BaseModel):
    category_id: str
    channel: str
    enabled: bool

class TenantPolicyListResponse(BaseModel):
    policies: list[TenantPolicyEntry]
```

**Implementation logic**:
```python
rows = db.exec(
    select(NotificationDefaultPolicy).where(
        NotificationDefaultPolicy.tenant_id == current_user.tenant_id
    )
).all()
return TenantPolicyListResponse(
    policies=[TenantPolicyEntry(category_id=r.category_id, channel=r.channel, enabled=r.enabled) for r in rows]
)
```

This returns only the **tenant-override** rows. If the list is empty, the tenant has not overridden any defaults (all defaults come from system rows where `tenant_id IS NULL`). The frontend uses this to pre-populate the matrix.

---

### D.5 — `DELETE /api/v1/notifications/tenant-policy` (NEW — bulk reset)

**File**: `backend/api/routes/notification_preferences.py`  
**Auth**: JWT required  
**Permission**: `notification_preference.tenant_default.edit` (owner/operator only)

```
DELETE /api/v1/notifications/tenant-policy
DELETE /api/v1/notifications/tenant-policy/test  ← test variant
```

**Request**: no body

**Response** `200`:
```python
class TenantPolicyResetResponse(BaseModel):
    deleted_count: int  # how many rows were removed
```

**Implementation logic**:
```python
set_audit_context_sync(db, user_id=current_user.id)
rows = db.exec(
    select(NotificationDefaultPolicy).where(
        NotificationDefaultPolicy.tenant_id == current_user.tenant_id
    )
).all()
deleted_count = len(rows)
for row in rows:
    db.delete(row)
db.commit()
return TenantPolicyResetResponse(deleted_count=deleted_count)
```

**Error codes**:
| Code | Condition |
|---|---|
| `403` | Non-owner role attempts reset |

---

## E. Pattern Reuse Decisions

| Pattern | Applied where |
|---|---|
| **Dual-endpoint (authenticated + `/test`)** | All 3 new endpoints (D.2, D.3, D.4, D.5) |
| **RFC 7807 error format** | All error responses |
| **`set_audit_context_sync()`** | `DELETE /avatar` and `DELETE /tenant-policy` (mutations) |
| **`require_permission()`** | `notification_preference.tenant_default.edit` on D.4 and D.5 |
| **S3 presigned URL pattern** | Already used in `public_invoices.py` — follow same boto3 client pattern |
| **Tenant-scoped SELECT** | D.4 and D.5 — always filter by `current_user.tenant_id` |

---

## F. Shared Module Interfaces

### F.1 — Avatar URL helper (add to `user_profile.py`)

```python
def _generate_avatar_url(s3_key: str | None) -> str | None:
    """Generate 1-hour presigned GET URL. Returns None if no key."""
    if not s3_key:
        return None
    try:
        s3 = boto3.client("s3", region_name=app_settings.AWS_REGION)
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": app_settings.S3_BUCKET_PHOTOS, "Key": s3_key},
            ExpiresIn=3600,
        )
    except Exception:
        return None  # Graceful degradation: no URL, no crash
```

> **Note to engineer**: Verify the exact S3 bucket settings attribute name and boto3 client pattern by reading `backend/api/routes/public_invoices.py` — it already generates presigned URLs for invoice attachments. Use the exact same pattern.

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does `user.profile_photo_s3_key` need a migration? | **No** — already exists as `TEXT NULL` in live DB |
| Does a tenant notification defaults table need to be created? | **No** — `notification_default_policy(tenant_id UUID NULL, ...)` already exists; `tenant_id=NULL` = system default, `tenant_id=UUID` = tenant override |
| Is there already a per-category tenant policy endpoint? | **Yes** — `PUT/DELETE /api/v1/notifications/tenant-policy/{category_id}/{channel}` already exist in `notification_preferences.py`. This batch adds only the **bulk GET** and **bulk DELETE (reset)** |
| What S3 bucket stores avatars? | Photos bucket — same one used for job photos. Key prefix: `avatars/{tenant_id}/{user_id}/avatar.jpg`. Verify bucket name via `grep "S3_BUCKET" backend/core/config.py` before implementing |
| Should S3 object be deleted when avatar is removed? | Best-effort delete — try but do NOT fail the DELETE endpoint if S3 deletion fails. Log a warning. |
| Does `profile_photo_url` need to be in the `GET /api/v1/users/me` endpoint? | No — the profile URL is fetched via `GET /api/v1/users/me/profile`. The `useAuth()` hook reads from Cognito/auth context, not from `/me/profile`. React Engineer notes: `profile_photo_url` is added to `PilotUser` type as optional and the frontend calls `GET /api/v1/users/me/profile` at mount to hydrate it. |
| Is `mfa.enroll_self` the right permission for avatar endpoints? | Yes — the existing `PATCH /api/v1/users/me/profile` already uses it. Use the same permission for D.2 and D.3. |

---

## H. Test Requirements Summary

New test files:

| Domain | File | Tests |
|---|---|---|
| `identity_access/` | `test_be_ui_nav_s1_avatar.py` | Presigned URL endpoint (mock S3), avatar delete (clears key), profile GET includes `profile_photo_url` when key set |
| `notifications_comms/` | `test_be_ui_nav_s1_tenant_policy.py` | Bulk GET returns tenant rows only, bulk DELETE removes all tenant rows (system rows untouched), non-owner gets 403 |

**Key test rules:**
- Mock `boto3.client("s3")` for all S3 interactions — never make real S3 calls in unit tests
- Use `second_tenant` for isolation tests (confirm system rows with `tenant_id=NULL` are NOT deleted by the bulk DELETE)
- Use `@pytest.mark.skip_mock_entitlement_allowed` where permission/entitlement is being tested

---

## I. Post-Batch Handoff

After this batch completes:
1. Run `python export_openapi_json.py`
2. Commit updated `openapi.json` + `openapi_schema_map.md`
3. Notify React Engineer to run `pnpm sync-api-types` before starting `FE-UI-NAV-S1`
4. The MSW stubs in `FE-UI-NAV-S1` for avatar and tenant-policy endpoints should be replaced with real hook calls once this batch merges
