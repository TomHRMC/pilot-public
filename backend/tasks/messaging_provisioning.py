"""
Messaging Provisioning Celery Tasks — C-B9
==========================================
Three Celery tasks for the 10DLC provisioning lifecycle:

  1. provision_brand       — post-checkout: create Telnyx brand, poll for verification/rejection
  2. provision_campaign    — post-brand-verified: create Telnyx campaign, poll for approval
  3. check_otp_timeout     — hourly: find registrations in awaiting_otp > 18h → alert; > 24h → quoting

Pattern: Two-layer approach (_impl + @celery_app.task wrapper).
Parameters use str UUIDs — Celery does not serialize UUID objects.
"""

import logging
import uuid

from sqlmodel import Session, select

from app.models.sms import TenantMessagingRegistration
from core.celery_app import celery_app
from core.db import get_db
from services.messaging_provisioning import (
    _build_campaign_payload,
    check_otp_timeouts,
    poll_brand_status,
    poll_campaign_status,
    transition_status,
)
from services.sms_carrier import get_sms_carrier

logger = logging.getLogger(__name__)


# ── Task 1: provision_brand ─────────────────────────────────────────────────


def _provision_brand_impl(db: Session, registration_id: str) -> dict:
    """Inner implementation — create Telnyx brand, poll for verification/rejection.

    Called after checkout.session.completed transitions to 'brand_submitted'.
    1. Load registration + profile
    2. Call carrier.create_brand() with brand data from profile
    3. Store telnyx_brand_id on registration
    4. Poll brand status (carrier.get_brand) — transition on verified/rejected
    """
    reg_id = uuid.UUID(registration_id)

    registration = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.id == reg_id
        )
    ).first()

    if not registration:
        logger.warning("provision_brand: registration %s not found", registration_id)
        return {"status": "not_found"}

    if registration.status != "brand_submitted":
        logger.info(
            "provision_brand: registration %s in status %s, skipping",
            registration_id,
            registration.status,
        )
        return {"status": "skipped", "current_status": registration.status}

    # Load the tenant's 10DLC profile for brand data
    from app.models.core import Tenant10DlcProfile

    profile = db.exec(
        select(Tenant10DlcProfile).where(
            Tenant10DlcProfile.tenant_id == registration.tenant_id
        )
    ).first()

    if not profile:
        logger.error(
            "provision_brand: no 10DLC profile for tenant %s",
            registration.tenant_id,
        )
        return {"status": "error", "reason": "no_profile"}

    # Build brand data from profile
    brand_data = {
        "entity_type": registration.entity_type,
        "legal_business_name": profile.legal_business_name,
        "dba_name": profile.dba_name,
        "ein": profile.ein,
        "hq_address_line1": profile.hq_address_line1,
        "hq_city": profile.hq_city,
        "hq_state": profile.hq_state,
        "hq_postal_code": profile.hq_postal_code,
        "hq_country": profile.hq_country,
        "support_email": profile.support_email,
        "support_phone": profile.support_phone,
        "website": profile.website,
        "stock_symbol": profile.stock_symbol,
        "vertical": profile.vertical,
    }

    # Create brand via carrier
    carrier = get_sms_carrier()
    result = carrier.create_brand(brand_data)

    # Store brand ID on registration
    registration.telnyx_brand_id = result.brand_id
    db.add(registration)
    db.commit()
    db.refresh(registration)

    logger.info(
        "provision_brand: created brand %s for registration %s (status=%s)",
        result.brand_id,
        registration_id,
        result.status,
    )

    # Poll brand status
    poll_brand_status(db, reg_id)

    return {
        "status": "completed",
        "brand_id": result.brand_id,
        "brand_status": result.status,
    }


@celery_app.task(name="provision_brand", bind=True, max_retries=3)
def provision_brand(self, registration_id: str) -> dict:
    """Post-checkout: create Telnyx brand, poll for verification/rejection."""
    db: Session = next(get_db())
    try:
        result = _provision_brand_impl(db, registration_id)
        logger.info("provision_brand task complete: %s", result)
        return result
    except Exception as exc:
        db.rollback()
        logger.error("provision_brand failed for %s: %s", registration_id, exc)
        raise self.retry(exc=exc, countdown=60)


# ── Task 2: provision_campaign ──────────────────────────────────────────────


def _provision_campaign_impl(db: Session, registration_id: str) -> dict:
    """Inner implementation — create Telnyx campaign, poll for approval.

    Called after brand_verified transition.
    1. Load registration + tenant name
    2. Build campaign payload from template
    3. Call carrier.create_campaign()
    4. Store telnyx_campaign_id on registration
    5. Poll campaign status — transition on approved/rejected
    """
    reg_id = uuid.UUID(registration_id)

    registration = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.id == reg_id
        )
    ).first()

    if not registration:
        logger.warning("provision_campaign: registration %s not found", registration_id)
        return {"status": "not_found"}

    if registration.status != "brand_verified":
        logger.info(
            "provision_campaign: registration %s in status %s, skipping",
            registration_id,
            registration.status,
        )
        return {"status": "skipped", "current_status": registration.status}

    if not registration.telnyx_brand_id:
        logger.error(
            "provision_campaign: registration %s has no telnyx_brand_id",
            registration_id,
        )
        return {"status": "error", "reason": "no_brand_id"}

    # Load tenant name for campaign payload
    from app.models.core import Tenant

    tenant = db.exec(select(Tenant).where(Tenant.id == registration.tenant_id)).first()

    tenant_name = tenant.name if tenant else "Pilot Tenant"

    # Build campaign payload from template
    campaign_data = _build_campaign_payload(tenant_name, registration.entity_type)

    # Create campaign via carrier
    carrier = get_sms_carrier()
    result = carrier.create_campaign(registration.telnyx_brand_id, campaign_data)

    # Store campaign ID on registration
    registration.telnyx_campaign_id = result.campaign_id
    db.add(registration)
    db.commit()
    db.refresh(registration)

    logger.info(
        "provision_campaign: created campaign %s for registration %s (status=%s)",
        result.campaign_id,
        registration_id,
        result.status,
    )

    # Transition to campaign_submitted
    transition_status(db, registration, "campaign_submitted")

    # Poll campaign status
    poll_campaign_status(db, reg_id)

    return {
        "status": "completed",
        "campaign_id": result.campaign_id,
        "campaign_status": result.status,
    }


@celery_app.task(name="provision_campaign", bind=True, max_retries=3)
def provision_campaign(self, registration_id: str) -> dict:
    """Post-brand-verified: create Telnyx campaign, poll for approval."""
    db: Session = next(get_db())
    try:
        result = _provision_campaign_impl(db, registration_id)
        logger.info("provision_campaign task complete: %s", result)
        return result
    except Exception as exc:
        db.rollback()
        logger.error("provision_campaign failed for %s: %s", registration_id, exc)
        raise self.retry(exc=exc, countdown=60)


# ── Task 3: check_otp_timeout ───────────────────────────────────────────────


def _check_otp_timeout_impl(db: Session) -> dict[str, int]:
    """Inner implementation — find awaiting_otp registrations past timeout thresholds.

    > 18h: alert Tom (log warning)
    > 24h: transition back to 'quoting' (no re-charge)
    """
    check_otp_timeouts(db)
    return {"checked": 1}


@celery_app.task(name="check_otp_timeout")
def check_otp_timeout() -> dict[str, int]:
    """Hourly: find registrations in 'awaiting_otp' > 18h → alert Tom.
    At > 24h → transition back to 'quoting' (no re-charge).
    """
    db: Session = next(get_db())
    try:
        result = _check_otp_timeout_impl(db)
        logger.info("check_otp_timeout task complete: %s", result)
        return result
    except Exception as exc:
        db.rollback()
        logger.error("check_otp_timeout failed: %s", exc)
        raise
