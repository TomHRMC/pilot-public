import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.models.system import NotificationDeliveryAttempt, NotificationOutbox
from core.celery_app import celery_app
from core.config import settings
from core.db import get_db
from services.email_service import send_email
from services.sms_carrier import get_sms_carrier
from services.template_renderer import render_subject, render_template

logger = logging.getLogger(__name__)


def calculate_next_retry(attempt_count: int) -> datetime | None:
    """
    Calculate next retry time using exponential backoff.

    Args:
        attempt_count: The current number of attempts

    Returns:
        Datetime for next attempt or None if max retries exceeded (dead letter).
    """
    if attempt_count >= len(settings.NOTIFICATION_RETRY_DELAYS):
        return None  # Dead letter - no more retries

    delay_seconds = settings.NOTIFICATION_RETRY_DELAYS[attempt_count]
    return datetime.now(UTC) + timedelta(seconds=delay_seconds)


def _send_via_channel(
    channel: str,
    to_address: str,
    subject: str | None,
    body: str,
    tenant_id: UUID,
    notification: "NotificationOutbox | None" = None,
) -> dict[str, Any]:
    """
    Route notification to appropriate service based on channel.
    """
    if channel == "email":
        return send_email(to=to_address, subject=subject or "Notification", body=body)
    elif channel == "sms":
        # B11/A59: Route SMS through carrier adapter (Telnyx/Mock) instead of direct Twilio
        carrier = get_sms_carrier()
        # In production, outbound SMS uses the tenant's provisioned TenantPhoneNumber.
        # This fallback is used only for notification_outbox-initiated SMS (no tenant context).
        from_number = (
            getattr(settings, "TELNYX_SANDBOX_FROM_NUMBER", None) or "+18005550000"
        )
        send_result = carrier.send_message(
            from_number=from_number,
            to_number=to_address,
            body=body,
        )
        # Convert SmsCarrier.SendResult to notification_worker result format
        return {
            "status": "sent" if send_result.status == "sent" else "error",
            "details": {"carrier_message_id": send_result.carrier_message_id}
            if send_result.carrier_message_id
            else {},
            "error_message": send_result.error_message,
            "http_status": send_result.http_status,
            "retryable": send_result.retryable,
        }
    elif channel == "in_app":
        # In-app notifications are delivered just by being in the database for the frontend to fetch
        return {
            "status": "sent",
            "details": {"message": "In-app delivery complete"},
            "error_message": None,
            "http_status": 200,
            "retryable": False,
        }
    elif channel == "push":
        # B20/A93: Real Expo Push Notifications API dispatch
        from sqlmodel import select as sqlmodel_select

        from app.models.sync import MobileDevicePushToken
        from services.expo_push_service import (
            ExpoDeviceNotRegisteredError,
            ExpoInvalidCredentialsError,
            ExpoMessageRateExceededError,
            send_expo_push,
        )

        # notification parameter is required for push delivery
        if not notification or not notification.recipient_user_id:
            return {
                "status": "error",
                "details": {},
                "error_message": "Push delivery requires recipient_user_id",
                "http_status": 400,
                "retryable": False,
            }

        # Get database session from context (passed via notification object's session)
        # We need to query for tokens — re-acquire db session reference
        from core.db import get_db

        db = next(get_db())
        try:
            # Look up all active tokens for this user
            tokens = db.exec(
                sqlmodel_select(MobileDevicePushToken)
                .where(MobileDevicePushToken.user_id == notification.recipient_user_id)
                .where(MobileDevicePushToken.tenant_id == notification.tenant_id)
                .where(MobileDevicePushToken.revoked_at == None)
                .where(MobileDevicePushToken.notification_permission_granted == True)
            ).all()

            if not tokens:
                # No registered device — skip gracefully, do not fail or retry
                return {
                    "status": "sent",  # treat as delivered (no-op); avoids dead-letter
                    "details": {"skipped": True, "reason": "no_active_push_token"},
                    "error_message": None,
                    "http_status": 200,
                    "retryable": False,
                }

            # deep_link_target comes from contextdata
            deep_link = (notification.contextdata or {}).get("deep_link_target")
            data_payload = {"deep_link_target": deep_link} if deep_link else None

            # Dispatch to all active devices; collect results
            all_sent = True
            last_error = None
            for token_row in tokens:
                try:
                    result = send_expo_push(
                        expo_token=token_row.push_token,
                        title=subject,  # rendered subject (may be None)
                        body=body,  # rendered body
                        data=data_payload,
                        access_token=getattr(settings, "EXPO_ACCESS_TOKEN", None)
                        or None,
                    )
                    if result.status != "sent":
                        all_sent = False
                        last_error = result.error_message
                except ExpoDeviceNotRegisteredError:
                    # Stale token — delete it and continue
                    db.delete(token_row)
                    db.commit()
                    logger.info(
                        f"Expo DeviceNotRegistered — stale token removed: device={token_row.device_id}"
                    )
                except ExpoMessageRateExceededError:
                    # Retryable — propagate as retryable result
                    return {
                        "status": "error",
                        "details": {},
                        "error_message": "Expo MessageRateExceeded",
                        "http_status": 429,
                        "retryable": True,
                    }
                except ExpoInvalidCredentialsError:
                    # Operator alert — hard fail, not retryable
                    logger.error(
                        "EXPO_ACCESS_TOKEN rejected by Expo API — operator intervention required"
                    )
                    return {
                        "status": "error",
                        "details": {},
                        "error_message": "Expo InvalidCredentials — check EXPO_ACCESS_TOKEN",
                        "http_status": 401,
                        "retryable": False,
                    }

            return {
                "status": "sent" if all_sent else "error",
                "details": {},
                "error_message": last_error,
                "http_status": 200 if all_sent else 500,
                "retryable": False,
            }
        finally:
            db.close()
    else:
        return {
            "status": "failed",
            "details": {},
            "error_message": f"Unknown channel: {channel}",
            "http_status": 400,
            "retryable": False,
        }


def _send_notification_impl(notification_id: str, db: Session) -> dict[str, Any]:
    """
    Internal implementation with dependency injection for testing.

    Args:
        notification_id: UUID string of notification_outbox record
        db: Database session

    Returns:
        Dict with delivery status and metadata
    """
    try:
        notification_uuid = UUID(notification_id)
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid notification_id format: {notification_id} - {e}")
        raise ValueError(f"Invalid notification_id format: {notification_id}")

    # 1. Load notification_outbox record with row lock
    notification = db.exec(
        select(NotificationOutbox)
        .where(NotificationOutbox.id == notification_uuid)
        .with_for_update()
    ).first()

    if not notification:
        logger.error(f"Notification not found: {notification_id}")
        raise ValueError(f"Notification not found: {notification_id}")

    # 2. Check if already sent or max attempts reached
    if notification.status in ["sent", "failed", "suppressed_by_preferences"]:
        logger.info(
            f"Notification {notification_id} already processed (status: {notification.status})"
        )
        return {"status": "skipped", "reason": f"Already {notification.status}"}

    logger.info(f"Sending notification {notification_id} via {notification.channel}")

    # 2b. B10/A58: Preference gate — check if delivery should be suppressed
    if notification.recipient_user_id and notification.category_id:
        from services.notification_resolver import should_deliver

        deliver = should_deliver(
            db=db,
            tenant_id=notification.tenant_id,
            user_id=notification.recipient_user_id,
            category_id=notification.category_id,
            channel=notification.channel,
            sub_trigger_id=notification.sub_trigger_id,
            recipient_user_id_originating=notification.recipient_user_id_originating,
            pref_cache=None,  # per-task caching is poll-loop level; single dispatch has no cache
        )
        if not deliver:
            notification.status = "suppressed_by_preferences"
            db.add(notification)
            db.commit()
            logger.info(
                f"Notification {notification.id} suppressed by preferences "
                f"(user={notification.recipient_user_id}, "
                f"category={notification.category_id}, channel={notification.channel})"
            )
            return {"status": "suppressed", "reason": "user_preferences"}

    # 2c. C-B7: Billing-active gate — block SMS dispatch when the subscription
    #     is paused/unpaid/canceled. Tom override 2026-08-05: spec §9.3 SMS
    #     exception is overridden; when paused → everything blocked, including
    #     SMS. This is the safety net for system-generated SMS that bypass the
    #     API endpoint gate in communications.py.
    if notification.channel == "sms":
        from services.entitlement_service import is_subscription_billing_active

        if not is_subscription_billing_active(db, notification.tenant_id):
            notification.status = "failed"
            notification.last_error = "subscription_paused"
            db.add(notification)
            db.commit()
            logger.info(
                f"Notification {notification.id} blocked: subscription not "
                f"billing-active (tenant={notification.tenant_id})"
            )
            return {"status": "blocked", "reason": "subscription_paused"}

    # Render template with context data
    context = notification.contextdata or {}
    try:
        rendered_body = render_template(notification.body, context)
        rendered_subject = (
            render_subject(notification.subject or "", context)
            if notification.subject
            else None
        )
    except ValueError as e:
        # Template error is permanent
        error_msg = str(e)
        logger.error(error_msg)
        notification.status = "failed"
        notification.last_error = error_msg
        db.add(notification)
        db.commit()
        return {"status": "failed", "reason": "Template render error"}

    # Route to appropriate channel
    to_address = notification.to_address
    if not to_address:
        # If no explicit to_address, this is an error unless in_app or push
        # push delivery is stub/carrier-based (no to_address needed)
        if notification.channel not in ("in_app", "push"):
            error_msg = f"No to_address provided for channel {notification.channel}"
            logger.error(error_msg)
            notification.status = "failed"
            notification.last_error = error_msg
            db.add(notification)
            db.commit()
            return {"status": "failed", "reason": "No recipient address"}
        to_address = notification.channel  # "in_app" or "push"

    # Send via provider
    result = _send_via_channel(
        channel=notification.channel,
        to_address=to_address,
        subject=rendered_subject,
        body=rendered_body,
        tenant_id=notification.tenant_id,
        notification=notification,
    )

    # Determine attempt-level retryability from provider result.
    # Services (email_service, sms_service) set retryable=True for 429/5xx
    # and retryable=False for 4xx terminal errors (invalid address, hard bounce).
    is_retryable: bool = result.get("retryable", False)
    http_status_code: int | None = result.get("http_status")

    # Calculate next_attempt_after for retryable failures (exponential backoff).
    next_attempt_after_ts = None
    if result["status"] != "sent" and is_retryable:
        next_attempt_after_ts = calculate_next_retry(notification.attempt_count + 1)

    # Create delivery attempt record — map all provider result fields.
    # B20/A93: Provider is now dynamic based on SMS_CARRIER setting (telnyx|mock) and "expo" for push
    if notification.channel == "in_app":
        provider = "system"
    elif notification.channel == "email":
        provider = "sendgrid"
    elif notification.channel == "sms":
        provider = getattr(settings, "SMS_CARRIER", "mock")
    elif notification.channel == "push":
        provider = "expo"
    else:
        provider = "unknown"

    attempt = NotificationDeliveryAttempt(
        notification_outbox_id=notification.id,
        tenant_id=notification.tenant_id,
        attempt_no=notification.attempt_count + 1,
        status="delivered" if result["status"] == "sent" else result["status"],
        provider=provider,
        details=result.get("details"),
        error_message=result.get("error_message"),
        http_status=http_status_code,
        retryable=is_retryable,
        next_attempt_after=next_attempt_after_ts,
    )
    db.add(attempt)

    # Update notification_outbox status
    notification.attempt_count += 1

    if result["status"] == "sent":
        notification.status = "sent"
        notification.last_error = None
        notification.next_attempt_at = None
        # We might want to store provider message id if it exists in response
        if result.get("details"):
            if "sid" in result["details"]:  # Twilio
                notification.provider_message_id = result["details"]["sid"]
    else:
        notification.last_error = result.get("error_message")

        if is_retryable:
            # Calculate backoff based on updated attempt count
            next_attempt = calculate_next_retry(notification.attempt_count)
            if next_attempt:
                notification.status = "pending"  # Keep as pending with retry scheduled
                notification.next_attempt_at = next_attempt
                logger.info(
                    f"Notification {notification_id} failed (http={http_status_code}), "
                    f"retrying at {next_attempt}"
                )
            else:
                notification.status = "failed"
                logger.warning(
                    f"Notification {notification_id} failed, dead letter (max retries exceeded)"
                )
        else:
            # Permanent / terminal failure — hard bounce, invalid destination, auth error
            notification.status = "failed"
            logger.warning(
                f"Notification {notification_id} failed permanently "
                f"(non-retryable, http={http_status_code})"
            )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Return result dict
    final_result = {
        "notification_id": str(notification.id),
        "status": notification.status,
        "attempt_count": notification.attempt_count,
        "channel": notification.channel,
    }

    if notification.status == "pending" and notification.next_attempt_at:
        # Raise exception for retryable errors to leverage celery retry mechanism
        # if the caller is the celery task. We'll handle this in the celery task wrapper.
        pass

    return final_result


@celery_app.task(
    name="send_notification", bind=True, max_retries=settings.NOTIFICATION_MAX_RETRIES
)
def send_notification(self, notification_id: str) -> dict[str, Any]:
    """
    Send a single notification via email or SMS.

    Args:
        notification_id: UUID string of notification_outbox record

    Returns:
        dict with delivery status and metadata
    """
    db: Session = next(get_db())

    try:
        result = _send_notification_impl(notification_id, db)

        # If the implementation returned retrying, we should trigger a celery retry
        # to ensure it stays in the queue.
        # However, the implementation already updated next_attempt_at.
        # We'll just return the result, and rely on the polling task OR trigger a scheduled task.
        # A better approach for immediate retries without polling:
        if result.get("status") == "pending" and result.get("next_attempt_at"):
            notification = db.exec(
                select(NotificationOutbox).where(
                    NotificationOutbox.id == UUID(notification_id)
                )
            ).first()
            if notification and notification.next_attempt_at:
                # Re-schedule this task using celery countdown
                countdown = (
                    notification.next_attempt_at - datetime.now(UTC)
                ).total_seconds()
                if countdown > 0:
                    raise self.retry(countdown=countdown)

        return result

    except ValueError:
        # Don't retry validation errors
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing notification {notification_id}: {e}")
        # Retry on unexpected DB or system errors
        raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


def _build_recipient_list(notification: "NotificationOutbox") -> list:
    """
    Determine the list of user IDs to evaluate for delivery.

    B10 scope: single-recipient evaluation only.
    Phase 2 broadcast (all active users in tenant) is deferred.

    Returns:
        List of user UUIDs to evaluate preference gate against.
    """
    if notification.recipient_user_id:
        return [notification.recipient_user_id]
    return []


@celery_app.task(name="poll_pending_notifications")
def poll_pending_notifications() -> dict[str, int]:
    """
    Poll for notifications where status='pending'
    and next_attempt_at <= now()

    B10/A58: Allocates a per-poll-cycle pref_cache to avoid redundant DB lookups
    when multiple notifications share the same user x category x channel combination.
    The cache is an in-memory dict — it is discarded at task end. See arch §3.5.5.
    """
    db: Session = next(get_db())
    processed_count = 0

    try:
        now = datetime.now(UTC)
        # B10/A58: per-cycle in-memory preference cache
        # Key: (user_id, category_id, channel) → bool
        pref_cache: dict[tuple, bool] = {}

        # Find notifications needing processing
        # status in ('pending', 'retrying') AND (next_attempt_at IS NULL OR next_attempt_at <= now)
        notifications = db.exec(
            select(NotificationOutbox)
            .where(NotificationOutbox.status.in_(["pending", "retrying"]))
            .where(
                (NotificationOutbox.next_attempt_at == None)
                | (NotificationOutbox.next_attempt_at <= now)
            )
            .limit(100)  # Process in batches
        ).all()

        for notification in notifications:
            # B10/A58: Apply preference gate at poll-cycle level before enqueueing
            # This avoids enqueueing tasks that will immediately be suppressed.
            if notification.recipient_user_id and notification.category_id:
                from services.notification_resolver import should_deliver

                deliver = should_deliver(
                    db=db,
                    tenant_id=notification.tenant_id,
                    user_id=notification.recipient_user_id,
                    category_id=notification.category_id,
                    channel=notification.channel,
                    sub_trigger_id=notification.sub_trigger_id,
                    recipient_user_id_originating=notification.recipient_user_id_originating,
                    pref_cache=pref_cache,
                )
                if not deliver:
                    notification.status = "suppressed_by_preferences"
                    db.add(notification)
                    logger.info(
                        f"Poll: notification {notification.id} suppressed "
                        f"(user={notification.recipient_user_id}, "
                        f"category={notification.category_id}, channel={notification.channel})"
                    )
                    processed_count += 1
                    continue

            # We trigger the celery task for each one
            send_notification.delay(str(notification.id))
            processed_count += 1

        db.commit()
        return {"processed": processed_count}
    except Exception as e:
        db.rollback()
        logger.error(f"Error polling notifications: {e}")
        raise
    finally:
        db.close()
