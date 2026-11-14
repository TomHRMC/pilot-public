"""
tasks/background_sync_push.py

MOB-B8/Background-Sync-B1: Server-side silent push dispatcher for background sync.

Two tasks:
  1. send_background_sync_push(tenant_id, device_id)
     Per-device task: verifies setting enabled, rate limit, dispatches silent push
     via Expo Push API using the existing expo_push_service pattern.

  2. scan_and_dispatch_background_sync_pushes()
     Beat task (every 60s): scans all active push tokens, dispatches per-device tasks.

Two-layer pattern per §Rule 3:
  - _impl() functions contain business logic (injected db session, unit testable)
  - @celery_app.task wrappers open their own session and call _impl()

Rule compliance:
  - Never calls db.get() on tenant-scoped models (Rule 5)
  - Does not raise on push failure — background task must never crash (Rule 3 / design doc §D3)
  - No audit context required (no DB mutation of user data — only rate limit updates)
"""

from datetime import UTC, datetime

from celery.utils.log import get_task_logger
from sqlmodel import Session, select

from app.models.sync import MobileDevicePushToken, MobilePushRateLimit
from core.celery_app import celery_app
from core.db import get_db
from services.setting_resolver import get_effective_setting

logger = get_task_logger(__name__)

# ---------------------------------------------------------------------------
# Expo push delivery (reuses expo_push_service pattern from notification_worker.py)
# ---------------------------------------------------------------------------


def _dispatch_expo_silent_push(push_token: str, platform: str) -> bool:
    """
    Send a silent (data-only) push notification via Expo Push API.

    iOS:  _contentAvailable=True (APNs content-available=1) — wakes app silently
    Android: priority='high' (FCM high-priority data message) — wakes app

    Reuses services.expo_push_service.send_expo_push() — same client + error handling
    as notification_worker.py push channel.

    Returns:
        True  — push accepted by Expo (status == "sent")
        False — push failed or Expo returned an error (do NOT raise; caller handles)
    """
    from core.config import settings
    from services.expo_push_service import (
        ExpoDeviceNotRegisteredError,
        ExpoInvalidCredentialsError,
        ExpoMessageRateExceededError,
        send_expo_push,
    )

    # Build silent push payload
    # send_expo_push sends title + body; for silent push we pass empty strings
    # and add platform-specific wake-up fields via the data dict.
    data_payload: dict = {"type": "background_sync"}
    if platform == "ios":
        data_payload["_contentAvailable"] = True  # APNs content-available=1
    elif platform == "android":
        data_payload["priority"] = "high"  # FCM high-priority wake

    try:
        result = send_expo_push(
            expo_token=push_token,
            title=None,  # silent push — no visible title
            body="",  # silent push — no visible body
            data=data_payload,
            access_token=getattr(settings, "EXPO_ACCESS_TOKEN", None) or None,
        )
        return result.status == "sent"
    except ExpoDeviceNotRegisteredError:
        logger.info(
            "background_sync_push: DeviceNotRegistered token=%s…", push_token[:12]
        )
        return False
    except ExpoMessageRateExceededError:
        logger.warning(
            "background_sync_push: Expo MessageRateExceeded token=%s…", push_token[:12]
        )
        return False
    except ExpoInvalidCredentialsError:
        logger.error(
            "background_sync_push: EXPO_ACCESS_TOKEN rejected — operator intervention required"
        )
        return False
    except Exception as exc:
        logger.error("background_sync_push: unexpected push error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Rate limit helper
# ---------------------------------------------------------------------------


def _upsert_rate_limit(
    db: Session,
    tenant_id: str,
    device_id: str,
    now_utc: datetime,
) -> None:
    """
    Update or create rate limit record for the device.
    Updates last_push_sent_at regardless of push success — prevents spam retries
    on a device that consistently fails.
    """
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


# ---------------------------------------------------------------------------
# Per-device task implementation
# ---------------------------------------------------------------------------


def _send_background_sync_push_impl(
    tenant_id: str,
    device_id: str,
    db: Session,
) -> dict:
    """
    Business logic: send a silent push to one device.

    Steps:
      1. Check background_sync_enabled tenant setting
      2. Load push interval from tenant setting
      3. Load active (non-revoked) push token for device+tenant
      4. Rate limit check (elapsed < interval → skip)
      5. Dispatch silent push via Expo API
      6. Update rate limit record (regardless of push success)

    Returns:
        {"sent": bool, "reason": str}
    """
    # 1. Check background sync enabled for tenant
    enabled, _ = get_effective_setting(
        db, tenant_id, "background_sync_enabled", fallback=True
    )
    if not enabled:
        return {"sent": False, "reason": "background_sync_disabled"}

    # 2. Load push interval setting
    interval_minutes, _ = get_effective_setting(
        db, tenant_id, "background_sync_push_interval_minutes", fallback=5
    )
    try:
        interval_minutes = int(interval_minutes)
    except (TypeError, ValueError):
        interval_minutes = 5

    # 3. Load active push token (tenant-scoped, not revoked, permission granted)
    token_row = db.exec(
        select(MobileDevicePushToken)
        .where(MobileDevicePushToken.device_id == device_id)
        .where(MobileDevicePushToken.tenant_id == tenant_id)
        .where(MobileDevicePushToken.revoked_at == None)
        .where(MobileDevicePushToken.notification_permission_granted == True)
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

    if rate_row and rate_row.last_push_sent_at is not None:
        last_sent = rate_row.last_push_sent_at
        # Ensure timezone-aware comparison
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=UTC)
        elapsed_minutes = (now_utc - last_sent).total_seconds() / 60
        if elapsed_minutes < interval_minutes:
            return {
                "sent": False,
                "reason": f"rate_limited_{elapsed_minutes:.1f}m_of_{interval_minutes}m",
            }

    # 5. Dispatch silent push
    success = _dispatch_expo_silent_push(token_row.push_token, token_row.platform)

    # 6. Update rate limit record (regardless of push success — prevent spam retries)
    _upsert_rate_limit(db, tenant_id, device_id, now_utc)

    logger.info(
        "background_sync_push device=%s tenant=%s success=%s",
        device_id,
        tenant_id,
        success,
    )
    return {"sent": success, "reason": "ok" if success else "push_api_error"}


@celery_app.task(name="tasks.background_sync_push.send_background_sync_push")
def send_background_sync_push(tenant_id: str, device_id: str) -> dict:
    """
    Celery task — sends silent push to one device.

    Entry point only: opens its own DB session and delegates to _impl().
    Dispatched by scan_and_dispatch_background_sync_pushes for each eligible device.
    """
    db: Session = next(get_db())
    try:
        return _send_background_sync_push_impl(tenant_id, device_id, db)
    except Exception as exc:
        logger.error(
            "send_background_sync_push unhandled error tenant=%s device=%s: %s",
            tenant_id,
            device_id,
            exc,
        )
        return {"sent": False, "reason": f"unhandled_error: {exc}"}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Beat scanner implementation
# ---------------------------------------------------------------------------


def _scan_and_dispatch_impl(db: Session) -> dict:
    """
    Scan active push tokens and dispatch send_background_sync_push for each
    device that has a valid (non-revoked, permission-granted) token.

    Per-device rate limiting is enforced inside _send_background_sync_push_impl —
    the scan is intentionally coarse (dispatch all active tokens; let the per-device
    task gate on rate limit). This keeps the scan O(N) without per-tenant setting
    queries at scan time.

    Cap at 500 devices per scan to prevent memory issues.
    """
    now_utc = datetime.now(UTC)

    active_tokens = db.exec(
        select(MobileDevicePushToken)
        .where(MobileDevicePushToken.revoked_at == None)
        .where(MobileDevicePushToken.notification_permission_granted == True)
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


@celery_app.task(
    name="tasks.background_sync_push.scan_and_dispatch_background_sync_pushes"
)
def scan_and_dispatch_background_sync_pushes() -> dict:
    """
    Beat task — runs every 60 seconds.

    Scans all active push tokens and dispatches per-device send_background_sync_push
    tasks. Per-device rate limiting is enforced inside each dispatched task.
    """
    db: Session = next(get_db())
    try:
        return _scan_and_dispatch_impl(db)
    except Exception as exc:
        logger.error("scan_and_dispatch_background_sync_pushes error: %s", exc)
        return {"dispatched": 0, "error": str(exc)}
    finally:
        db.close()
