# Batch MOB-B8 Design — Background Sync: Server-Initiated Silent Push + OS-Scheduled Fallback

**Batch**: MOB-B8 (Mixed — Python Engineer then React Native Engineer)  
**Launch Plan Name**: Background-Sync-B1  
**Date**: 2026-07-12  
**Author**: Pilot Architect  
**Status**: DESIGN COMPLETE — Ready for implementation  
**Reference**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch 9 · PRD §3.15 · GAP-M17  
**Prerequisites**: MOB-B7 complete ✅, all backend batches through B20 complete ✅

---

## Overview

MOB-B8 implements **background sync** for the mobile app. When a field tech's device is closed (app not in foreground), the platform must still push pending data to the server. This closes the last major gap in the offline-first mobile architecture.

**Two-mechanism strategy (PRD §3.15 §4.1)**:
1. **Primary**: Server-initiated silent push (FCM for Android, APNs for iOS) — server wakes the app via a data-only (silent) push notification when a device's queue is likely non-empty or the push interval has elapsed
2. **Fallback**: OS-scheduled opportunistic execution (BGAppRefreshTask on iOS, WorkManager periodic on Android) — fires when OS decides to allocate background time regardless of push delivery

**Background sync scope (PRD §3.15)**:
- ✅ Data sync queue (clock-in/out, time entries, expenses, LOTO, job status changes, notes, change orders)
- ❌ Photo uploads — foreground-only (battery/bandwidth concern)
- ❌ Voice audio uploads — foreground-only
- ❌ Tech-resolvable conflicts — defer to foreground (requires user input)
- ✅ `auto_silent` and `auto_notice` conflict auto-resolution only

**Part A (Python Engineer)**: Celery task to dispatch silent push per device, Beat schedule to periodically scan eligible devices, push token registration/update endpoint, background sync policy endpoint.

**Part B (React Native Engineer)**: Push token registration hook, BGAppRefreshTask + WorkManager registration, background task handler that calls the existing sync orchestrator, background sync settings UI section.

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| PRD §3.15 | Background Sync trigger spec | Primary = silent push; fallback = OS-scheduled; data queue only; auto-resolve only |
| PRD §3.15 | Background Sync Settings | 4 settings: `background_sync_enabled`, `background_sync_wifi_only`, `background_sync_battery_floor_pct`, `background_sync_push_interval_minutes` |
| MCP — `mobile_device_push_token` | Columns verified | `id, tenant_id, user_id, device_id, platform, push_token, app_version, os_version, registered_at, last_seen_at, notification_permission_granted, revoked_at, created_at, updated_at` |
| MCP — `mobile_push_rate_limit` | Columns verified | `id, tenant_id, device_id, last_push_sent_at, push_count_current_window, window_start_at, created_at, updated_at` |
| MCP — `mobile_sync_session` | Columns verified | `id, tenant_id, user_id, device_id, triggered_by, started_at, completed_at, outcome, items_attempted, items_committed, items_deferred, items_failed, failure_reason, created_at` |
| MCP — `platform_setting_catalog` | Keys verified | All 4 background sync settings already exist in catalog: `background_sync_enabled`, `background_sync_wifi_only`, `background_sync_battery_floor_pct`, `background_sync_push_interval_minutes` |
| MCP — `alembic_version` | Current head | `f7f30492c3e4` (B20) — **no new migrations needed**: all required tables and settings are already in the DB |
| `backend/tasks/` directory listing | Existing tasks | `mobile_sync_cleanup.py`, `notification_worker.py`, `voice_offline_tasks.py` — confirm background task patterns exist |
| MOB-B6 design | Mobile sync pattern | WatermelonDB sync orchestrator at `database/sync/orchestrator.ts`; manual trigger exists |
| MOB-B7 design | Push token context | Notification permission flow already present; `expo-notifications` already used |

---

## B. Migration Plan

### No Alembic migrations required

All required DB tables and settings already exist:
- `mobile_device_push_token` ✅ (has all required columns including `platform`, `push_token`, `device_id`)
- `mobile_push_rate_limit` ✅ (has `last_push_sent_at`, `push_count_current_window`, `window_start_at`)
- `mobile_sync_session` ✅ (has `triggered_by` — can store `'background_push'` or `'background_os'`)
- `platform_setting_catalog`: all 4 background sync settings ✅

### Pre-work verification the engineer must run

```sql
-- 1. Confirm push token table columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'mobile_device_push_token' ORDER BY ordinal_position;

-- 2. Confirm rate limit table columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'mobile_push_rate_limit' ORDER BY ordinal_position;

-- 3. Confirm all 4 background sync settings exist
SELECT key, value_type FROM public.platform_setting_catalog 
WHERE key IN ('background_sync_enabled','background_sync_wifi_only',
              'background_sync_battery_floor_pct','background_sync_push_interval_minutes');

-- 4. Confirm mobile_sync_session triggered_by column accepts text values
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'mobile_sync_session' AND column_name = 'triggered_by';

-- 5. Verify push token registration endpoint existence
-- (Python Engineer checks openapi_schema_map.md for existing /api/v1/mobile/push-tokens endpoints)
```

---

## C. Execution Order

### Part A — Python Engineer (runs first)

| # | Task | File(s) | Dependency |
|---|---|---|---|
| A1 | Verify: does `POST /api/v1/mobile/push-tokens/register` already exist? | `backend/openapi_schema_map.md` grep | Pre-work |
| A2 | If A1 = NO: add `MobileDevicePushToken` SQLModel + push token registration endpoint | `app/models/notifications.py`, `api/routes/mobile_push_tokens.py` | A1 |
| A3 | Create `backend/tasks/background_sync_push.py` — `send_background_sync_push_impl()` + Celery task | New file | A2 |
| A4 | Create `_scan_eligible_devices_impl()` in same file + `scan_and_dispatch_background_sync_pushes` Beat task | Same file | A3 |
| A5 | Register task module in `backend/core/celery_app.py` imports + Beat schedule | `core/celery_app.py` | A4 |
| A6 | Add `GET /api/v1/settings/background-sync-policy` endpoint | `api/routes/settings.py` or new `api/routes/mobile_settings.py` | A5 |
| A7 | Run `python -m pytest -m unit --tb=short -q` — fix any failures | — | A6 |
| A8 | Run `python export_openapi_json.py` → handoff to React Native Engineer | — | A7 |

### Part B — React Native Engineer (runs after A8 + `pnpm sync-api-types`)

| # | Task | File(s) | Dependency |
|---|---|---|---|
| B1 | `pnpm sync-api-types` — pick up new push token registration endpoint types | — | A8 handoff |
| B2 | Verify `expo-notifications`, `expo-task-manager`, `expo-background-fetch` in `apps/mobile/package.json` | `package.json` | Pre-work |
| B3 | If not installed: `pnpm --filter mobile add expo-task-manager expo-background-fetch` | `package.json` | B2 |
| B4 | Add BGAppRefresh (iOS) + BACKGROUND_FETCH (Android) permissions to `app.json` | `app.json` | B3 |
| B5 | Create `hooks/usePushTokenRegistration.ts` — register/update device push token on app start | New file | B1 |
| B6 | Wire `usePushTokenRegistration` into app root (`app/_layout.tsx`) | `app/_layout.tsx` | B5 |
| B7 | Create `lib/backgroundSync.ts` — `BACKGROUND_SYNC_TASK_NAME` constant + task handler that calls `sync()` from orchestrator | New file | B4 |
| B8 | Register background task in `app/_layout.tsx` with `TaskManager.defineTask` | `app/_layout.tsx` | B7 |
| B9 | Register `BackgroundFetch.registerTaskAsync` in `app/_layout.tsx` | `app/_layout.tsx` | B8 |
| B10 | Add background sync settings section to Settings screen (`useSyncPolicy` hook + display) | `features/settings/` | B1 |
| B11 | Create MSW handlers for new endpoints | `mocks/handlers/backgroundSyncHandlers.ts` + register in `index.ts` | B1 |
| B12 | Write tests + full verification | `__tests__/batch_mob_b8/` | All |

---

## D. New API Endpoints (Part A)

### D1. Push Token Registration — `POST /api/v1/mobile/push-tokens/register`

> **Pre-work gate**: Python Engineer MUST grep `openapi_schema_map.md` for "push-tokens" before implementing. If this endpoint already exists from prior work, skip to D2.

```
POST /api/v1/mobile/push-tokens/register
Auth: Cognito JWT required
Permission: authenticated (any role with jobs.view covers this)
Idempotency: natural-key upsert on (user_id, device_id) — no Idempotency-Key header needed

Request:
{
  "device_id": "uuid",           # Client-generated stable UUID (stored in SecureStore)
  "platform": "ios" | "android",
  "push_token": "ExponentPushToken[...]" or FCM token string,
  "app_version": "1.0.0",        # optional
  "os_version": "17.4"           # optional
}

Response 200:
{
  "id": "uuid",
  "device_id": "uuid",
  "registered_at": "2026-07-12T...",
  "last_seen_at": "2026-07-12T..."
}

Errors:
  422: invalid platform value (not 'ios' | 'android')
  422: push_token is empty string
```

**Implementation**: Upsert into `mobile_device_push_token` ON CONFLICT `(user_id, device_id)` → UPDATE `push_token, last_seen_at, app_version, os_version`. Sets `notification_permission_granted = true`.

Also add `/api/v1/mobile/push-tokens/register/test` unauthenticated test endpoint.

---

### D2. Background Sync Policy — `GET /api/v1/settings/background-sync-policy`

```
GET /api/v1/settings/background-sync-policy
Auth: Cognito JWT required
Permission: any authenticated user (settings are tenant-effective)

Response 200:
{
  "background_sync_enabled": true,
  "background_sync_wifi_only": false,
  "background_sync_battery_floor_pct": 20,
  "background_sync_push_interval_minutes": 5
}

Errors:
  401: unauthenticated
```

**Implementation**: Uses `get_effective_setting(db, tenant_id, key, fallback=...)` for each of the 4 keys. Returns typed response — not a generic key/value map.

---

## E. Celery Task Design (Part A)

### E1. `backend/tasks/background_sync_push.py`

```python
# Two-layer pattern per python-engr-std-prompt-inclusions.md §12

def _send_background_sync_push_impl(
    tenant_id: str,
    device_id: str,
    db: Session,
) -> dict:
    """
    Send a silent push notification to one device.
    Respects rate limit from mobile_push_rate_limit.
    Returns {"sent": bool, "reason": str}
    """
    # 1. Load effective push interval setting
    interval_minutes, _ = get_effective_setting(
        db, tenant_id, "background_sync_push_interval_minutes", fallback=5
    )
    enabled, _ = get_effective_setting(
        db, tenant_id, "background_sync_enabled", fallback=True
    )
    if not enabled:
        return {"sent": False, "reason": "background_sync_disabled"}

    # 2. Load push token (skip if revoked or no token)
    token_row = db.exec(
        select(MobileDevicePushToken)
        .where(MobileDevicePushToken.device_id == device_id)
        .where(MobileDevicePushToken.tenant_id == tenant_id)
        .where(MobileDevicePushToken.revoked_at == None)
    ).first()
    if not token_row:
        return {"sent": False, "reason": "no_active_token"}

    # 3. Rate limit check against mobile_push_rate_limit
    now_utc = datetime.now(UTC)
    rate_row = db.exec(
        select(MobilePushRateLimit)
        .where(MobilePushRateLimit.device_id == device_id)
        .where(MobilePushRateLimit.tenant_id == tenant_id)
    ).first()
    if rate_row:
        elapsed = (now_utc - rate_row.last_push_sent_at).total_seconds() / 60
        if elapsed < interval_minutes:
            return {"sent": False, "reason": f"rate_limited ({elapsed:.1f}m < {interval_minutes}m)"}

    # 4. Send silent push via Expo Push Notification API (MVP: Expo Notifications)
    #    - iOS: content-available=1, no alert/sound (silent push)
    #    - Android: priority=high, data-only (no notification body)
    success = _dispatch_expo_silent_push(token_row.push_token, token_row.platform)

    # 5. Update rate limit record
    _upsert_rate_limit(db, tenant_id, device_id, now_utc)

    return {"sent": success, "reason": "ok" if success else "push_api_error"}


@celery_app.task
def send_background_sync_push(tenant_id: str, device_id: str) -> dict:
    """Celery entry point — sends silent push to one device."""
    with next(get_db()) as db:
        return _send_background_sync_push_impl(tenant_id, device_id, db)


def _scan_and_dispatch_background_sync_pushes_impl(db: Session) -> dict:
    """
    Periodic Beat task: scan active push tokens where push is overdue.
    Dispatches send_background_sync_push.delay() for each eligible device.
    """
    # Query: devices with notification_permission_granted=true AND revoked_at IS NULL
    # that have not been pushed within their tenant's interval
    # Use a JOIN to mobile_push_rate_limit to check last_push_sent_at
    # For devices with no rate limit row: treat as never pushed (eligible immediately)
    # ...
    return {"dispatched": dispatched_count}


@celery_app.task
def scan_and_dispatch_background_sync_pushes() -> dict:
    """Beat task — runs every 1 minute; dispatches per-device push tasks."""
    with next(get_db()) as db:
        return _scan_and_dispatch_background_sync_pushes_impl(db)
```

**Beat schedule**: Every 1 minute (the scanner is fast; per-device rate limiting is enforced inside `send_background_sync_push`).

**Push delivery**: Use the **Expo Push Notification API** (`https://exp.host/--/api/v2/push/send`) — this is already the push delivery mechanism used by `notification_worker.py`. Silent push payload:
- iOS: `{"to": token, "data": {"type": "background_sync"}, "_contentAvailable": true}` (no `title`/`body` → silent)
- Android: `{"to": token, "data": {"type": "background_sync"}, "priority": "high"}` (no `title`/`body` → data-only)

---

## F. Pattern Reuse Decisions

| Pattern | Applied in MOB-B8 |
|---|---|
| Two-layer Celery task (`_impl` + `@celery_app.task`) | `send_background_sync_push` + `scan_and_dispatch_background_sync_pushes` both use this pattern |
| `get_effective_setting()` for 4 background sync settings | Python Engineer uses same service function as `get_loto_policy` (MOB-B7 Part A) |
| Expo Push Notification API | Reuses `notification_worker.py`'s Expo push delivery pattern — **do not reinvent push delivery** |
| `usePushTokenRegistration` → `POST /api/v1/mobile/push-tokens/register` | On-mount hook in `app/_layout.tsx`, runs once per app open; idempotent upsert safe to call repeatedly |
| `expo-task-manager` + `expo-background-fetch` | Standard Expo background task pattern for iOS BGAppRefreshTask + Android WorkManager |
| `triggered_by` on `mobile_sync_session` | Background task handler writes `triggered_by: 'background_push'` or `triggered_by: 'background_os'` to distinguish push-initiated vs OS-scheduled syncs |
| Auto-resolve only in background | Background sync orchestrator skips items with `sync_conflict_severity = 'tech_resolvable'` or `'owner_escalation'` — defers to foreground |

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **Does push token registration endpoint already exist?** | **Python Engineer must verify in pre-work** — grep `openapi_schema_map.md` for "push-tokens". If yes: skip D1, only add D2. If no: implement D1 upsert pattern. The `mobile_device_push_token` table already exists so the endpoint may have been added earlier. |
| **Which push delivery service for silent push?** | Expo Push Notification API — already used in `notification_worker.py`. Do NOT add a new FCM/APNs SDK. Expo handles the platform routing. |
| **Should background sync run on WiFi-only?** | React Native Engineer: check `background_sync_wifi_only` setting from `useSyncPolicy` hook. If `true` AND device is on cellular: skip the sync and return early from the background task handler. Use `@react-native-community/netinfo` (already installed from foreground sync). |
| **Battery floor enforcement — client or server?** | Client-side in the background task handler. Read `background_sync_battery_floor_pct` from policy response. Use `expo-battery` (or `react-native-device-info` — check what's installed) to get battery level. If below floor: skip sync and return early. |
| **What does the background task handler actually do?** | It calls the existing `sync()` function from `database/sync/orchestrator.ts`. The orchestrator already handles all conflict classification and WatermelonDB sync. The handler just provides a background entry point. It must complete within 30 seconds (iOS BGAppRefreshTask time limit). |
| **Does the background task run photos/voice?** | No. Per PRD §3.15: background sync scope = data queue only. Photos and voice audio are foreground-only. The background task calls the sync orchestrator but the orchestrator already separates data sync from photo/audio upload queues. Confirm the orchestrator does NOT auto-upload photos in the background sync path. |
| **User-level override for `background_sync_enabled`?** | PRD says user override of master toggle is allowed on mobile. This means the Settings screen has an editable toggle for `background_sync_enabled` (user override). The Python engineer does NOT need to implement user-level setting override storage — PRD says platform_setting supports tenant override; user override is purely a client-side preference for MVP (stored in AsyncStorage/SecureStore on device). Post-MVP: can be persisted to server. |
| **Does `expo-task-manager` require Tom approval (like `expo-location`)?** | Per rules-pilot-architect §9.8: native Expo dependencies require Tom approval. **Flag this explicitly in both prompts.** Tom must approve `expo-task-manager` and `expo-background-fetch` before the React Native Engineer installs them. These are listed in the batch scope — approval gate in the prompt. |

---

## H. Surface Mockup Reference

**Platform**: Mobile only (`apps/mobile`) for Part B.

### H.1 Background Sync Policy in Settings

```
Settings > General > Background Sync
┌─────────────────────────────────────────────────────────────┐
│  Background Sync                                            │
│  ─────────────────────────────────────────────────────────  │
│  Keep your data current even when the app is closed.        │
│                                                             │
│  Background Sync     [● ON]   (user-editable toggle)        │
│                                                             │
│  WiFi Only           [OFF]    (read-only — set by owner)    │
│  Battery Floor       20%      (read-only — set by owner)    │
│  Sync Interval       5 min    (read-only — set by owner)    │
│                                                             │
│  Note: WiFi and battery settings are controlled by your     │
│  account owner.                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## I. Component Manifest

| Component / File | Path | New or Modify | Engineer |
|---|---|---|---|
| `background_sync_push.py` | `backend/tasks/background_sync_push.py` | **New** | Python |
| Push token endpoint | `backend/api/routes/mobile_push_tokens.py` (or existing route) | **New or skip** (pre-work gate) | Python |
| `GET /api/v1/settings/background-sync-policy` | `backend/api/routes/settings.py` | **New endpoint in existing file** | Python |
| `celery_app.py` | `backend/core/celery_app.py` | **Modify** — register task module + Beat schedule | Python |
| `usePushTokenRegistration` | `frontend/apps/mobile/hooks/usePushTokenRegistration.ts` | **New** | React Native |
| `lib/backgroundSync.ts` | `frontend/apps/mobile/lib/backgroundSync.ts` | **New** — task name + handler | React Native |
| `app/_layout.tsx` | `frontend/apps/mobile/app/_layout.tsx` | **Modify** — wire hook + register task | React Native |
| `BackgroundSyncSettingsSection` | `frontend/apps/mobile/features/settings/components/BackgroundSyncSettingsSection.tsx` | **New** | React Native |
| `useSyncPolicy` | `frontend/apps/mobile/features/settings/hooks/useSyncPolicy.ts` | **New** — calls background-sync-policy endpoint | React Native |
| `backgroundSyncHandlers.ts` | `frontend/apps/mobile/mocks/handlers/backgroundSyncHandlers.ts` | **New** | React Native |
| `mocks/handlers/index.ts` | `frontend/apps/mobile/mocks/handlers/index.ts` | **Modify** — register handlers | React Native |
| `app.json` | `frontend/apps/mobile/app.json` | **Modify** — background permissions | React Native |
