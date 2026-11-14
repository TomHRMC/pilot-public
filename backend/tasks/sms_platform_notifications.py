"""
Platform Account-Notification SMS Tasks — PLATFORM-SMS-B1 / Pathway C
=====================================================================
Celery task for sending Pilot→owner platform account-notification SMS
(e.g. payment-failed alerts).

Pathway C (design §F): Pilot is the genuine sender of account, billing &
security alerts to tenant owners. The FROM number is Pilot's ONE shared
platform number (config: ``PILOT_PLATFORM_SMS_NUMBER``). Messages are sent
directly via ``get_sms_carrier()`` — NOT through ``notification_outbox``
(the worker's sms branch resolves tenant/sandbox FROM numbers and applies
per-user category preference gating, neither of which applies to Pathway C).

Consent gate: sends only to owner ``user_endpoint`` rows with
``consent_status='opted_in'`` AND ``verification_status='verified'`` (the
TCPA gate — owners who completed the double-opt-in by replying YES).

Pattern: Two-layer approach (``_impl`` + ``@celery_app.task`` wrapper),
mirroring ``tasks/sms_compliance_platform.py``. Parameters use str UUIDs —
Celery does not serialize UUID objects.

Sync ``def`` throughout (Rule 21).
"""

import logging
import uuid as _uuid
from typing import Any

from sqlmodel import Session

from core.celery_app import celery_app
from services.notification_endpoints import (
    get_verified_owner_sms_endpoints,
    get_verified_user_sms_endpoints,
)
from services.platform_sms_templates import get_platform_sms_body
from services.sms_carrier import get_sms_carrier
from services.template_renderer import render_template

logger = logging.getLogger(__name__)


def _send_platform_account_notification_sms_impl(
    tenant_id: str,
    type_code: str,
    template_context: dict[str, str] | None = None,
    recipient_user_id: str | None = None,
) -> dict[str, Any]:
    """
    Core implementation — separated for testability (called without ``.delay()``).

    Send a Pathway C account-notification SMS to verified+opted-in endpoints.

    PLP-FIX-8 (INV-BUG-4): recipient selection is now mode-dependent:

      - ``recipient_user_id`` is not None → **user-scoped** resolution: only
        the authenticated user's verified+opted-in SMS endpoints receive
        (``get_verified_user_sms_endpoints``). Used by the Post-Authentication
        new-device alert so the *authenticating* user is texted, not the
        tenant owner.

      - ``recipient_user_id`` is None (default) → **legacy owner fan-out**:
        all verified+opted-in owner endpoints of the tenant receive
        (``get_verified_owner_sms_endpoints``). Unchanged behavior for the
        two existing callers (``broadcast_maintenance_sms``,
        ``stripe_subscriptions.handle_invoice_payment_failed``).

    The additive kwarg is safe for in-flight messages enqueued by an older
    Lambda (they lack the kwarg → default None → owner fan-out).

    FROM = ``settings.PILOT_PLATFORM_SMS_NUMBER``.
    Body = ``get_platform_sms_body(db, type_code)`` (fail-loud).

    PLATFORM-SMS-B2: When ``template_context`` is supplied (not None), the
    loaded body is rendered through Jinja2 (``render_template``) before the
    carrier fan-out. This supports Sample 4 (``platform_maintenance_broadcast``)
    whose stored body contains ``{{ maint_date }}`` / ``{{ maint_window }}``
    placeholders. When ``template_context`` is None (the default), the body is
    used verbatim — preserving B1 behavior for the static templates
    (e.g. ``platform_payment_failed``, ``platform_security_new_device``).

    ``template_context`` values MUST be strings only (Celery-serializable).
    Callers are responsible for validating values against an allowlist before
    enqueueing (see ``scripts/broadcast_maintenance_sms.py``).

    Skip conditions (return ``{"status": "skipped", "reason": ...}``):
      - No verified+opted-in endpoints for this tenant/user.
      - ``PILOT_PLATFORM_SMS_NUMBER`` not configured.

    Returns:
        dict with 'status' key: 'sent', 'skipped', or 'failed', plus
        'sent_count' and per-endpoint details.
    """
    from core.config import settings
    from core.db import engine

    with Session(engine) as db:
        # 1. Resolve the platform FROM number from config.
        from_number = settings.PILOT_PLATFORM_SMS_NUMBER
        if not from_number:
            logger.error(
                "send_platform_account_notification_sms: "
                "PILOT_PLATFORM_SMS_NUMBER not configured — cannot send "
                "platform SMS (tenant=%s, type_code=%s)",
                tenant_id,
                type_code,
            )
            return {
                "status": "skipped",
                "reason": "no_platform_from_number",
                "sent_count": 0,
            }

        # 2. Load the campaign-locked body from the single DB content path.
        #    Fail-loud: a missing row raises PlatformSmsTemplateMissingError.
        body = get_platform_sms_body(db, type_code)

        # 2b. PLATFORM-SMS-B2: render only when a context is supplied.
        #     None preserves B1 behavior exactly (static bodies used verbatim).
        if template_context is not None:
            body = render_template(body, template_context)

        # 3. Resolve recipients — user-scoped or legacy owner fan-out.
        if recipient_user_id is not None:
            endpoints = get_verified_user_sms_endpoints(
                db,
                tenant_id=_uuid.UUID(tenant_id),
                user_id=_uuid.UUID(recipient_user_id),
            )
            logger.info(
                "send_platform_account_notification_sms: recipient=user "
                "user_id=%s tenant=%s type_code=%s — resolved %d endpoint(s)",
                recipient_user_id,
                tenant_id,
                type_code,
                len(endpoints),
            )
        else:
            endpoints = get_verified_owner_sms_endpoints(
                db, tenant_id=_uuid.UUID(tenant_id)
            )
            logger.info(
                "send_platform_account_notification_sms: recipient=owners "
                "tenant=%s type_code=%s — resolved %d endpoint(s)",
                tenant_id,
                type_code,
                len(endpoints),
            )

        if not endpoints:
            logger.info(
                "send_platform_account_notification_sms: no verified+opted-in "
                "sms endpoints for tenant %s (type_code=%s, "
                "recipient_user_id=%s) — skipping",
                tenant_id,
                type_code,
                recipient_user_id,
            )
            return {
                "status": "skipped",
                "reason": "no_verified_endpoints",
                "sent_count": 0,
            }

        # 4. Send to each endpoint. Log per-send; collect results.
        carrier = get_sms_carrier()
        sent_count = 0
        failed_count = 0
        results: list[dict[str, Any]] = []

        for endpoint in endpoints:
            try:
                result = carrier.send_message(
                    from_number=from_number,
                    to_number=endpoint.value,
                    body=body,
                )

                if result.status == "sent":
                    sent_count += 1
                    logger.info(
                        "send_platform_account_notification_sms: sent to "
                        "user %s at %s (tenant=%s, type_code=%s, "
                        "carrier_message_id=%s)",
                        endpoint.user_id,
                        endpoint.value,
                        tenant_id,
                        type_code,
                        result.carrier_message_id,
                    )
                    results.append(
                        {
                            "user_id": str(endpoint.user_id),
                            "status": "sent",
                            "carrier_message_id": result.carrier_message_id,
                        }
                    )
                else:
                    failed_count += 1
                    logger.warning(
                        "send_platform_account_notification_sms: send failed "
                        "for user %s at %s (tenant=%s, type_code=%s): %s",
                        endpoint.user_id,
                        endpoint.value,
                        tenant_id,
                        type_code,
                        result.error_message,
                    )
                    results.append(
                        {
                            "user_id": str(endpoint.user_id),
                            "status": "failed",
                            "error": result.error_message,
                            "retryable": result.retryable,
                        }
                    )
            except Exception as exc:
                failed_count += 1
                logger.error(
                    "send_platform_account_notification_sms: exception sending "
                    "to user %s at %s (tenant=%s, type_code=%s): %s",
                    endpoint.user_id,
                    endpoint.value,
                    tenant_id,
                    type_code,
                    exc,
                    exc_info=True,
                )
                results.append(
                    {
                        "user_id": str(endpoint.user_id),
                        "status": "failed",
                        "error": str(exc),
                        "retryable": False,
                    }
                )

        overall_status = "sent" if failed_count == 0 else "failed"
        return {
            "status": overall_status,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "results": results,
        }


@celery_app.task(
    name="send_platform_account_notification_sms",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_platform_account_notification_sms(
    self,
    tenant_id: str,
    type_code: str,
    template_context: dict[str, str] | None = None,
    recipient_user_id: str | None = None,
) -> dict[str, Any]:
    """
    Celery task: Send a Pathway C account-notification SMS to verified recipients.

    Parameters (str UUIDs — Celery does not serialize UUID objects):
        tenant_id:  The tenant UUID string.
        type_code: The ``notification_type.code`` (e.g.
                   ``"platform_payment_failed"``).
        template_context: Optional dict of string→string Jinja2 variables
                   for parameterized bodies (PLATFORM-SMS-B2). None (default)
                   preserves B1 behavior — the stored body is used verbatim.
                   Values MUST be strings only (Celery-serializable).
        recipient_user_id: Optional user UUID string. When set, the SMS is
                   sent only to that user's verified+opted-in SMS endpoints
                   (PLP-FIX-8 — user-scoped resolution). When None (default),
                   legacy owner fan-out applies. Additive kwarg — in-flight
                   messages from an older Lambda lack it and default to None.

    Triggered by: ``handle_invoice_payment_failed`` (Stripe webhook),
    ``broadcast_maintenance_sms`` (operator broadcast), and the
    Post-Authentication Lambda (new-device alert). Max retries: 3 (only on
    retryable carrier failures).
    """
    try:
        result = _send_platform_account_notification_sms_impl(
            tenant_id,
            type_code,
            template_context=template_context,
            recipient_user_id=recipient_user_id,
        )

        # Only retry on failed sends with retryable errors.
        if result.get("status") == "failed" and any(
            r.get("retryable") for r in result.get("results", [])
        ):
            raise self.retry(
                exc=Exception("retryable carrier failure"),
                countdown=self.default_retry_delay,
            )

        return result

    except self.MaxRetriesExceededError:
        logger.error(
            "send_platform_account_notification_sms: max retries exceeded "
            "for tenant %s (type_code=%s)",
            tenant_id,
            type_code,
        )
        return {
            "status": "failed",
            "reason": "max_retries_exceeded",
            "sent_count": 0,
        }
    except Exception as exc:
        logger.error(
            "send_platform_account_notification_sms: unexpected error for "
            "tenant %s (type_code=%s): %s",
            tenant_id,
            type_code,
            exc,
            exc_info=True,
        )
        raise self.retry(exc=exc)
