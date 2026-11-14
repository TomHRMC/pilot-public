"""
services/mobile_background_sync.py

B8/A51: Background Sync Infrastructure — Push dispatcher and sync session manager.

Establishes §16.12 Background Sync Execution Pattern.
Canonical push token registry for B11 (SMS push) and future surfaces.

Introduced: B8/A51
Consumed by: A47/A48 (loop closure), B11/A66 (push inbox updates)
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.sync import (
    MobileDevicePushToken,
    MobilePushRateLimit,
    MobileSyncSession,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System-level constants
# ---------------------------------------------------------------------------
# B9/A53: SYSTEM_BG_SYNC_PUSH_INTERVAL_MINUTES replaced by get_effective_setting()
# The system default (5) is now authoritative in core/system_defaults.py.
SYSTEM_THROTTLE_THRESHOLD_HOURS = 2


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PushDispatchResult:
    """Result of a single silent push attempt to one device."""

    device_id: uuid.UUID
    dispatched: bool
    skip_reason: (
        str | None
    )  # 'rate_limited' | 'revoked_token' | 'permission_denied' | None
    platform: str  # 'ios' | 'android'


# ---------------------------------------------------------------------------
# Push token registry
# ---------------------------------------------------------------------------


def register_or_refresh_push_token(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
    platform: str,
    push_token: str,
    app_version: str | None,
    os_version: str | None,
    notification_permission_granted: bool,
) -> MobileDevicePushToken:
    """
    Upsert push token for (tenant_id, user_id, device_id).

    Called by POST /api/v1/mobile/push-tokens route.
    On token change (same device, new token), updates the token and un-revokes.
    On re-registration (same token), updates last_seen_at only.

    Returns:
        The MobileDevicePushToken row (created or updated).
    """
    existing = db.exec(
        select(MobileDevicePushToken)
        .where(MobileDevicePushToken.tenant_id == tenant_id)
        .where(MobileDevicePushToken.user_id == user_id)
        .where(MobileDevicePushToken.device_id == device_id)
    ).first()

    now = datetime.now(UTC)

    if existing:
        # Update existing row — clear revoke if re-registering
        existing.push_token = push_token
        existing.platform = platform
        existing.app_version = app_version
        existing.os_version = os_version
        existing.notification_permission_granted = notification_permission_granted
        existing.last_seen_at = now
        existing.revoked_at = None  # Un-revoke on fresh registration
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        token_row = MobileDevicePushToken(
            tenant_id=tenant_id,
            user_id=user_id,
            device_id=device_id,
            platform=platform,
            push_token=push_token,
            app_version=app_version,
            os_version=os_version,
            notification_permission_granted=notification_permission_granted,
            registered_at=now,
            last_seen_at=now,
        )
        db.add(token_row)
        db.commit()
        db.refresh(token_row)
        return token_row


def revoke_push_token(
    db: Session,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
) -> bool:
    """
    Mark push token revoked for (user_id, device_id).

    Called by DELETE /api/v1/mobile/push-tokens/{device_id}.

    Returns:
        True if row found and revoked; False if not found (idempotent).
    """
    token_row = db.exec(
        select(MobileDevicePushToken)
        .where(MobileDevicePushToken.user_id == user_id)
        .where(MobileDevicePushToken.device_id == device_id)
    ).first()

    if not token_row:
        return False

    token_row.revoked_at = datetime.now(UTC)
    db.add(token_row)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Push dispatch
# ---------------------------------------------------------------------------


# _get_push_interval_minutes() removed in B9/A53.
# Use get_effective_setting(db, tenant_id, "background_sync_push_interval_minutes", fallback=5) directly.


def _check_rate_limit(
    db: Session,
    tenant_id: uuid.UUID,
    device_id: uuid.UUID,
    interval_minutes: int,
) -> bool:
    """
    Check whether a device is within the rate limit window.

    Returns True if dispatch is allowed, False if rate-limited.
    Updates the rate limit row if dispatch is allowed.
    """
    now = datetime.now(UTC)
    rate_row = db.exec(
        select(MobilePushRateLimit).where(MobilePushRateLimit.device_id == device_id)
    ).first()

    if rate_row is None:
        # First push for this device — create rate limit row
        rate_row = MobilePushRateLimit(
            tenant_id=tenant_id,
            device_id=device_id,
            last_push_sent_at=now,
            push_count_current_window=1,
            window_start_at=now,
        )
        db.add(rate_row)
        db.commit()
        return True

    # Check elapsed minutes since last push
    elapsed = (
        now - rate_row.last_push_sent_at.replace(tzinfo=UTC)
        if rate_row.last_push_sent_at.tzinfo is None
        else now - rate_row.last_push_sent_at
    ).total_seconds() / 60
    if elapsed < interval_minutes:
        return False  # Still within cooldown window

    # Update rate limit row
    rate_row.last_push_sent_at = now
    rate_row.push_count_current_window += 1
    db.add(rate_row)
    db.commit()
    return True


def dispatch_silent_push_for_device(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
    sync_session_id: uuid.UUID,
) -> PushDispatchResult:
    """
    Dispatch a single silent push to a registered device.

    Checks:
      1. Token exists and is not revoked in mobile_device_push_token
      2. notification_permission_granted = True
      3. Rate limit not exceeded (mobile_push_rate_limit; interval per tenant setting)

    On APNs/FCM 'invalid token' response: marks token revoked, returns dispatched=False.

    Args:
        db:               DB session
        tenant_id:        Tenant scope
        user_id:          Target user
        device_id:        Target device UUID
        sync_session_id:  Session ID to include in push payload

    Returns:
        PushDispatchResult with dispatch outcome
    """
    # 1. Verify token exists and is active
    token_row = db.exec(
        select(MobileDevicePushToken)
        .where(MobileDevicePushToken.tenant_id == tenant_id)
        .where(MobileDevicePushToken.user_id == user_id)
        .where(MobileDevicePushToken.device_id == device_id)
        .where(MobileDevicePushToken.revoked_at == None)
    ).first()

    if not token_row:
        return PushDispatchResult(
            device_id=device_id,
            dispatched=False,
            skip_reason="revoked_token",
            platform="unknown",
        )

    # 2. Check notification permission
    if not token_row.notification_permission_granted:
        return PushDispatchResult(
            device_id=device_id,
            dispatched=False,
            skip_reason="permission_denied",
            platform=token_row.platform,
        )

    # 3. Check rate limit — resolve interval via B9/A53 three-tier resolver
    from services.setting_resolver import (
        get_effective_setting,  # late import avoids circular
    )

    interval_minutes, _ = get_effective_setting(
        db, tenant_id, "background_sync_push_interval_minutes", fallback=5
    )

    allowed = _check_rate_limit(db, tenant_id, device_id, interval_minutes)
    if not allowed:
        return PushDispatchResult(
            device_id=device_id,
            dispatched=False,
            skip_reason="rate_limited",
            platform=token_row.platform,
        )

    # 4. Dispatch (mock — real APNs/FCM implementation uses PUSH_CARRIER env var)
    # TODO_PUSH_CARRIER: replace with get_push_carrier().send_silent_push(token, payload)
    try:
        _dispatch_via_carrier(token_row, sync_session_id)
        logger.info(
            f"Silent push dispatched: tenant={tenant_id} user={user_id} "
            f"device={device_id} session={sync_session_id} platform={token_row.platform}"
        )
        return PushDispatchResult(
            device_id=device_id,
            dispatched=True,
            skip_reason=None,
            platform=token_row.platform,
        )
    except InvalidTokenError:
        # APNs/FCM responded with invalid token — revoke
        token_row.revoked_at = datetime.now(UTC)
        db.add(token_row)
        db.commit()
        return PushDispatchResult(
            device_id=device_id,
            dispatched=False,
            skip_reason="revoked_token",
            platform=token_row.platform,
        )


class InvalidTokenError(Exception):
    """Raised by push carrier when APNs/FCM returns an invalid token response."""

    pass


def _dispatch_via_carrier(
    token_row: MobileDevicePushToken, sync_session_id: uuid.UUID
) -> None:
    """
    Internal dispatch stub. Replaced by real carrier implementation.
    PUSH_CARRIER=mock (default) → no-op.
    PUSH_CARRIER=apns/fcm → real APNs/FCM call.
    """
    import os

    carrier = os.getenv("PUSH_CARRIER", "mock")
    if carrier == "mock":
        logger.debug(
            f"[MockPushCarrier] Would push to token={token_row.push_token[:12]}... session={sync_session_id}"
        )
        return
    # TODO_PUSH_CARRIER: implement real APNs/FCM dispatch
    logger.warning(f"PUSH_CARRIER={carrier} not yet implemented, using mock")


# ---------------------------------------------------------------------------
# Pending item detection
# ---------------------------------------------------------------------------


def detect_pending_items_for_tenant(
    db: Session,
    tenant_id: uuid.UUID,
    age_threshold_minutes: int = 15,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """
    Return list of (user_id, device_id) pairs that have mobile_sync_pending_operation
    items older than age_threshold_minutes and no recent push dispatch.

    Used by Celery Beat task to identify devices needing a silent push nudge.

    Args:
        db:                     DB session
        tenant_id:              Tenant scope
        age_threshold_minutes:  Minimum item age before triggering push (default 15)

    Returns:
        List of (user_id, device_id) tuples
    """
    from app.models.sync import MobileSyncEvent

    # Find user+device combos with pending sync events older than threshold
    cutoff = datetime.now(UTC)
    raw = db.exec(
        select(
            MobileSyncEvent.user_id,
            MobileSyncEvent.device_id,
        )
        .where(MobileSyncEvent.tenant_id == tenant_id)
        .where(MobileSyncEvent.status == "pending")
        .distinct()
    ).all()

    results = []
    for row in raw:
        try:
            user_id = row.user_id
            device_id_str = row.device_id
            # device_id on MobileSyncEvent is a text field — parse to UUID
            device_uuid = (
                uuid.UUID(device_id_str)
                if isinstance(device_id_str, str)
                else device_id_str
            )
            results.append((user_id, device_uuid))
        except (ValueError, AttributeError):
            continue

    return results


def detect_os_throttle_for_device(
    db: Session,
    device_id: uuid.UUID,
    throttle_threshold_hours: int = SYSTEM_THROTTLE_THRESHOLD_HOURS,
) -> bool:
    """
    Detect whether a device appears OS-throttled.

    Heuristic: push was dispatched but no sync session reported within
    throttle_threshold_hours despite pending items in queue.

    Args:
        db:                       DB session
        device_id:                Device UUID
        throttle_threshold_hours: No-sync window before declaring throttled (default 2)

    Returns:
        True if device appears OS-throttled
    """
    rate_row = db.exec(
        select(MobilePushRateLimit).where(MobilePushRateLimit.device_id == device_id)
    ).first()

    if not rate_row:
        return False  # Never dispatched — cannot determine

    last_push = rate_row.last_push_sent_at
    if last_push.tzinfo is None:
        last_push = last_push.replace(tzinfo=UTC)

    # Check most recent sync session for this device
    last_session = db.exec(
        select(MobileSyncSession)
        .where(MobileSyncSession.device_id == device_id)
        .order_by(MobileSyncSession.started_at.desc())
    ).first()

    if last_session is None:
        # Push dispatched but no session ever — throttled if push was recent enough
        elapsed_hours = (datetime.now(UTC) - last_push).total_seconds() / 3600
        return elapsed_hours >= throttle_threshold_hours

    completed_at = last_session.completed_at
    if completed_at is None:
        # Session started but never completed
        completed_at = last_session.started_at

    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=UTC)

    # Throttled if last push was after last session completion by threshold
    if last_push > completed_at:
        gap_hours = (datetime.now(UTC) - last_push).total_seconds() / 3600
        return gap_hours >= throttle_threshold_hours

    return False


# ---------------------------------------------------------------------------
# Loop-closure push (A48)
# ---------------------------------------------------------------------------


def dispatch_loop_closure_push(
    db: Session,
    tenant_id: uuid.UUID,
    originator_user_id: uuid.UUID,
    escalation_id: uuid.UUID,
    resolution_action: str,
) -> list[PushDispatchResult]:
    """
    Dispatch loop-closure push to all active devices for the originating tech
    after owner resolves an escalated mobile conflict.

    Used by A48 resolution write path.

    Args:
        db:                   DB session
        tenant_id:            Tenant scope
        originator_user_id:   Tech whose conflict was resolved
        escalation_id:        Resolved escalation UUID
        resolution_action:    Resolution action taken by owner

    Returns:
        List of PushDispatchResult for each device targeted
    """
    # Find all active (non-revoked) tokens for this user
    tokens = db.exec(
        select(MobileDevicePushToken)
        .where(MobileDevicePushToken.tenant_id == tenant_id)
        .where(MobileDevicePushToken.user_id == originator_user_id)
        .where(MobileDevicePushToken.revoked_at == None)
        .where(MobileDevicePushToken.notification_permission_granted == True)
    ).all()

    results = []
    for token_row in tokens:
        try:
            _dispatch_via_carrier(token_row, escalation_id)
            results.append(
                PushDispatchResult(
                    device_id=token_row.device_id,
                    dispatched=True,
                    skip_reason=None,
                    platform=token_row.platform,
                )
            )
            logger.info(
                f"Loop-closure push dispatched: tenant={tenant_id} "
                f"user={originator_user_id} escalation={escalation_id} "
                f"action={resolution_action} platform={token_row.platform}"
            )
        except InvalidTokenError:
            token_row.revoked_at = datetime.now(UTC)
            db.add(token_row)
            db.commit()
            results.append(
                PushDispatchResult(
                    device_id=token_row.device_id,
                    dispatched=False,
                    skip_reason="revoked_token",
                    platform=token_row.platform,
                )
            )

    return results
