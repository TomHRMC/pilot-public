"""
SMS Compliance Tasks — Platform (Pathway C) — SIGNUP-C / PLATFORM-SMS-B1
==========================================================================
Celery task for the Pilot→owner platform double-opt-in SMS flow.

Pathway C (design §F / ADR-0013): Pilot is the genuine sender of account,
billing & security alerts to tenant owners. The FROM number is Pilot's ONE
shared platform number (config: ``PILOT_PLATFORM_SMS_NUMBER`` / Secrets
``pilot/prod/telnyx``) — NOT a per-tenant ``TenantPhoneNumber`` row. This is
the compliance-clean single-brand case Telnyx wants for the repurposed
``CXXXXXX`` campaign.

Pattern: Two-layer approach (``_impl`` + ``@celery_app.task`` wrapper),
mirroring ``tasks/sms_compliance.py`` (Pathway B) but with platform FROM
resolution. Parameters use str UUIDs — Celery does not serialize UUID objects.

PLATFORM-SMS-B1: The double-opt-in SMS body is now loaded from the single DB
content path (``notification_template`` system row, channel='sms') via
``services.platform_sms_templates.get_platform_sms_body()``. The old code
constant ``_PLATFORM_DOUBLE_OPTIN_TEMPLATE`` has been deleted — there is no
fallback. The §6↔§8 code-match rule (error 806) is enforced by the
verbatim-guardrail test in
``tests/domains/notifications_comms/test_platform_sms_b1_verbatim_guardrail.py``.
"""

import logging
import uuid as _uuid
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session

from app.models.communications import UserSmsConsentAudit
from core.celery_app import celery_app
from services.notification_endpoints import get_owner_sms_endpoint, hash_consent_text
from services.sms_carrier import get_sms_carrier

logger = logging.getLogger(__name__)


def _send_platform_double_optin_sms_impl(
    user_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Core implementation — separated for testability (called without ``.delay()``).

    Resolves the owner's ``sms`` ``user_endpoint`` (TO) and Pilot's platform
    number (FROM, from config), sends the double-opt-in SMS, and writes a
    ``user_sms_consent_audit`` row with ``action='double_opt_in_sent'``.

    Skip conditions (return ``{"status": "skipped", "reason": ...}``):
      - No ``sms`` ``user_endpoint`` for this user.
      - ``consent_status != 'opted_in'`` (owner did not check the box).
      - ``verification_status == 'verified'`` (already confirmed via YES reply).
      - Platform FROM number not configured.

    Returns:
        dict with 'status' key: 'sent', 'skipped', or 'failed'
    """
    from core.config import settings
    from core.db import engine

    with Session(engine) as db:
        # 1. Resolve the owner's sms endpoint (TO number).
        endpoint = get_owner_sms_endpoint(db, user_id=_uuid.UUID(user_id))

        if not endpoint:
            logger.warning(
                "send_platform_double_optin_sms: no sms endpoint for user %s — skipping",
                user_id,
            )
            return {"status": "skipped", "reason": "no_sms_endpoint"}

        if endpoint.consent_status != "opted_in":
            logger.info(
                "send_platform_double_optin_sms: user %s consent_status=%s — skipping "
                "(owner did not opt in)",
                user_id,
                endpoint.consent_status,
            )
            return {"status": "skipped", "reason": "not_opted_in"}

        if endpoint.verification_status == "verified":
            logger.info(
                "send_platform_double_optin_sms: user %s already verified — skipping",
                user_id,
            )
            return {"status": "skipped", "reason": "already_verified"}

        # 2. Resolve the platform FROM number from config (NOT TenantPhoneNumber).
        from_number = settings.PILOT_PLATFORM_SMS_NUMBER
        if not from_number:
            logger.error(
                "send_platform_double_optin_sms: PILOT_PLATFORM_SMS_NUMBER not "
                "configured — cannot send platform SMS"
            )
            return {"status": "skipped", "reason": "no_platform_from_number"}

        # 3. Send the SMS — body loaded from the single DB content path
        #    (notification_template system row, channel='sms'). Fail-loud:
        #    a missing campaign-locked row raises and sends nothing.
        from services.platform_sms_templates import get_platform_sms_body

        body = get_platform_sms_body(db, "platform_sms_double_optin")
        carrier = get_sms_carrier()
        result = carrier.send_message(
            from_number=from_number,
            to_number=endpoint.value,
            body=body,
        )

        # 4. Write the audit row (action='double_opt_in_sent') regardless of
        #    send success/failure — the attempt itself is an auditable event.
        now = datetime.now(UTC)
        audit_row = UserSmsConsentAudit(
            tenant_id=_uuid.UUID(tenant_id),
            user_id=_uuid.UUID(user_id),
            user_endpoint_id=endpoint.id,
            action="double_opt_in_sent",
            consent_text_hash=hash_consent_text(body),
            ip_address=None,  # webhook/task-driven — no request IP
            attested_at=now,
            created_at=now,
            created_by=_uuid.UUID(user_id),
        )
        db.add(audit_row)
        db.commit()

        if result.status == "sent":
            logger.info(
                "send_platform_double_optin_sms: sent to user %s at %s, "
                "carrier_message_id=%s",
                user_id,
                endpoint.value,
                result.carrier_message_id,
            )
            return {
                "status": "sent",
                "carrier_message_id": result.carrier_message_id,
            }
        else:
            logger.warning(
                "send_platform_double_optin_sms: send failed for user %s: %s",
                user_id,
                result.error_message,
            )
            return {
                "status": "failed",
                "retryable": result.retryable,
                "error": result.error_message,
            }


@celery_app.task(
    name="send_platform_double_optin_sms",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_platform_double_optin_sms(
    self,
    user_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Celery task: Send the Pilot→owner platform double-opt-in SMS.

    Parameters (str UUIDs — Celery does not serialize UUID objects):
        user_id:   The owner user UUID string.
        tenant_id: The tenant UUID string.

    Triggered by: signup step 3 when ``sms_consent`` is True (the owner checked
    the box). Max retries: 3 (only on retryable carrier errors).
    """
    try:
        result = _send_platform_double_optin_sms_impl(user_id, tenant_id)

        # Only retry on retryable carrier failure.
        if result.get("status") == "failed" and result.get("retryable"):
            raise self.retry(
                exc=Exception(result.get("error", "retryable carrier failure")),
                countdown=self.default_retry_delay,
            )

        return result

    except self.MaxRetriesExceededError:
        logger.error(
            "send_platform_double_optin_sms: max retries exceeded for user %s",
            user_id,
        )
        return {"status": "failed", "reason": "max_retries_exceeded"}
    except Exception as exc:
        logger.error(
            "send_platform_double_optin_sms: unexpected error for user %s: %s",
            user_id,
            exc,
            exc_info=True,
        )
        raise self.retry(exc=exc)
