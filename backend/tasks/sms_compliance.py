"""
SMS Compliance Tasks — DLC-1
==============================
Celery tasks for 10DLC double opt-in flow.

Tasks:
  send_double_optin_sms — sends double opt-in confirmation SMS when a customer
                          is created/updated with a phone + attestation checkbox.

Pattern: Two-layer approach (_impl + @celery_app.task wrapper).
Parameters use str UUIDs — Celery does not serialize UUID objects.
"""

import logging
import uuid as _uuid
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session

from core.celery_app import celery_app

logger = logging.getLogger(__name__)

# DLC-spec consent text template (playbook §8 — double opt-in; highest-scrutiny message)
# DLC-B4: Prefixed with "Pilot for Trades: " so platform is the perceived sender per
# 10DLC campaign CXXXXXX resubmission requirement. "Pilot for Trades" appears twice:
# leading prefix = sender ID; inline mention = program description (correct per Telnyx guidance).
_DOUBLE_OPTIN_TEMPLATE = (
    "Pilot for Trades: Hi {first_name}, {business_name} uses Pilot for Trades for service updates. "
    "Reply YES to confirm you want to receive texts. "
    "Msg freq varies. Msg & data rates may apply. "
    "Reply HELP for help, STOP to cancel."
)


def _send_double_optin_sms_impl(
    customer_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Core implementation — separated for testability (called without .delay()).

    Looks up customer + tenant 10DLC profile, sends double opt-in SMS,
    writes CustomerSmsConsentAudit row with action='double_opt_in_sent'.

    Returns:
        dict with 'status' key: 'sent', 'skipped', or 'failed'
    """
    import hashlib

    from sqlmodel import select

    from app.models.core import Tenant10DlcProfile
    from app.models.crm import Customer, CustomerSmsConsentAudit

    # Resolve tenant_phone (from_ number) from tenant's active phone number
    from app.models.sms import TenantPhoneNumber
    from core.db import engine
    from services.sms_carrier import get_sms_carrier

    with Session(engine) as db:
        # Load customer
        customer = db.exec(
            select(Customer).where(Customer.id == _uuid.UUID(customer_id))
        ).first()

        if not customer:
            logger.warning(f"send_double_optin_sms: customer {customer_id} not found")
            return {"status": "skipped", "reason": "customer_not_found"}

        if customer.sms_opted_out:
            logger.info(
                f"send_double_optin_sms: customer {customer_id} already opted out — skipping"
            )
            return {"status": "skipped", "reason": "already_opted_out"}

        if not customer.mobile_phone:
            logger.warning(
                f"send_double_optin_sms: customer {customer_id} has no mobile_phone — skipping"
            )
            return {"status": "skipped", "reason": "no_mobile_phone"}

        # Resolve business name from Tenant10DlcProfile
        profile = db.exec(
            select(Tenant10DlcProfile).where(
                Tenant10DlcProfile.tenant_id == customer.tenant_id
            )
        ).first()
        business_name = (
            profile.legal_business_name if profile else "your service provider"
        )

        # Resolve first_name fallback
        first_name = customer.first_name or "there"

        # Build message
        body = _DOUBLE_OPTIN_TEMPLATE.format(
            first_name=first_name,
            business_name=business_name,
        )

        # Resolve outbound from_number (tenant's active phone number)
        tenant_phone = db.exec(
            select(TenantPhoneNumber).where(
                TenantPhoneNumber.tenant_id == customer.tenant_id,
                TenantPhoneNumber.status == "active",
            )
        ).first()

        if not tenant_phone:
            logger.warning(
                f"send_double_optin_sms: no active TenantPhoneNumber for tenant "
                f"{tenant_id} — skipping send"
            )
            return {"status": "skipped", "reason": "no_tenant_phone_number"}

        # Send the SMS
        carrier = get_sms_carrier()
        result = carrier.send_message(
            from_number=tenant_phone.phone_number,
            to_number=customer.mobile_phone,
            body=body,
        )

        now = datetime.now(UTC)

        # Write audit row regardless of success/failure
        consent_text = body
        audit_row = CustomerSmsConsentAudit(
            id=_uuid.uuid4(),
            created_at=now,
            tenant_id=customer.tenant_id,
            customer_id=customer.id,
            attested_by=customer.sms_consent_attested_by
            or customer.created_by
            or customer.id,
            ip_address=customer.sms_consent_ip_address or "system",
            attested_at=now,
            consent_text_hash=hashlib.sha256(consent_text.encode()).hexdigest(),
            action="double_opt_in_sent",
        )
        db.add(audit_row)
        db.commit()

        if result.status == "sent":
            logger.info(
                f"send_double_optin_sms: sent to customer {customer_id}, "
                f"carrier_message_id={result.carrier_message_id}"
            )
            return {
                "status": "sent",
                "carrier_message_id": result.carrier_message_id,
            }
        else:
            logger.warning(
                f"send_double_optin_sms: send failed for customer {customer_id}: "
                f"{result.error_message}"
            )
            return {
                "status": "failed",
                "retryable": result.retryable,
                "error": result.error_message,
            }


@celery_app.task(
    name="send_double_optin_sms",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_double_optin_sms(
    self,
    customer_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Celery task: Send double opt-in confirmation SMS to a customer.

    Parameters (str UUIDs — Celery does not serialize UUID objects):
        customer_id: Customer UUID string
        tenant_id:   Tenant UUID string

    Triggered by: POST/PATCH /customers when sms_attestation_checked=True.
    Max retries: 3 (only on retryable carrier errors).
    """
    try:
        result = _send_double_optin_sms_impl(customer_id, tenant_id)

        # Only retry on retryable carrier failure
        if result.get("status") == "failed" and result.get("retryable"):
            raise self.retry(
                exc=Exception(result.get("error", "retryable carrier failure")),
                countdown=self.default_retry_delay,
            )

        return result

    except self.MaxRetriesExceededError:
        logger.error(
            f"send_double_optin_sms: max retries exceeded for customer {customer_id}"
        )
        return {"status": "failed", "reason": "max_retries_exceeded"}
    except Exception as exc:
        logger.error(
            f"send_double_optin_sms: unexpected error for customer {customer_id}: {exc}",
            exc_info=True,
        )
        raise self.retry(exc=exc)
