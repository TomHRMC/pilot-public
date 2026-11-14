"""
SMS Number Provisioning Service — B11/A61
=========================================
Handles tenant Telnyx phone number provisioning lifecycle:
  - provision_for_tenant(): acquire a new number from carrier, persist to DB
  - get_active_number_for_tenant(): look up the active provisioned number
  - release_number_for_tenant(): release back to carrier

Always call get_sms_carrier() — never import Telnyx directly.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.sms import TenantPhoneNumber
from services.sms_carrier import get_sms_carrier

logger = logging.getLogger(__name__)


@dataclass
class ProvisioningResult:
    """Result of a number provisioning attempt."""

    success: bool
    tenant_phone_number_id: UUID | None
    phone_number: str | None
    error: str | None
    suggested_area_codes: list[str] = field(default_factory=list)


def provision_for_tenant(
    db: Session,
    tenant_id: UUID,
    area_code: str | None = None,
    requested_by_user_id: UUID | None = None,
) -> ProvisioningResult:
    """
    Provision a Telnyx phone number for a tenant at first SMS send.

    Steps:
    1. Check if tenant already has an active number (return 409-class result)
    2. If area_code is None: default to '512' for MVP (derives from tenant address in future)
    3. Call get_sms_carrier().provision_number(area_code, tenant_id)
    4. Persist TenantPhoneNumber row with status='active'
    5. On carrier failure: persist with status='provisioning_failed'

    Returns ProvisioningResult with success=True and phone_number on success.
    Returns ProvisioningResult with success=False and error on failure.
    """
    # Check for existing active number
    existing = get_active_number_for_tenant(db, tenant_id)
    if existing:
        return ProvisioningResult(
            success=False,
            tenant_phone_number_id=existing.id,
            phone_number=existing.phone_number,
            error="Tenant already has an active provisioned number",
        )

    # Default area_code for MVP
    resolved_area_code = area_code or "512"

    carrier = get_sms_carrier()

    try:
        provisioned = carrier.provision_number(resolved_area_code, tenant_id)

        record = TenantPhoneNumber(
            tenant_id=tenant_id,
            phone_number=provisioned.phone_number,
            area_code=resolved_area_code,
            carrier="telnyx",
            carrier_provisioning_id=provisioned.carrier_provisioning_id,
            monthly_fee_cents=provisioned.monthly_fee_cents,
            status="active",
            provisioned_at=datetime.now(UTC),
            created_by=requested_by_user_id,
            updated_by=requested_by_user_id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(
            f"Provisioned number {provisioned.phone_number} for tenant {tenant_id}"
        )
        return ProvisioningResult(
            success=True,
            tenant_phone_number_id=record.id,
            phone_number=record.phone_number,
            error=None,
        )

    except Exception as exc:
        db.rollback()
        logger.error(
            f"Provisioning failed for tenant {tenant_id} area_code={resolved_area_code}: {exc}"
        )

        # Persist failed record for audit visibility
        try:
            failed_record = TenantPhoneNumber(
                tenant_id=tenant_id,
                phone_number="",
                area_code=resolved_area_code,
                carrier="telnyx",
                status="provisioning_failed",
                created_by=requested_by_user_id,
                updated_by=requested_by_user_id,
            )
            db.add(failed_record)
            db.commit()
        except Exception:
            db.rollback()

        # Suggest nearby area codes on failure
        suggested = _suggest_nearby_area_codes(resolved_area_code)
        return ProvisioningResult(
            success=False,
            tenant_phone_number_id=None,
            phone_number=None,
            error=str(exc),
            suggested_area_codes=suggested,
        )


def get_active_number_for_tenant(
    db: Session,
    tenant_id: UUID,
) -> TenantPhoneNumber | None:
    """
    Return the active TenantPhoneNumber for this tenant, or None.
    Does not raise — caller decides whether to trigger provisioning.
    """
    return db.exec(
        select(TenantPhoneNumber).where(
            TenantPhoneNumber.tenant_id == tenant_id,
            TenantPhoneNumber.status == "active",
        )
    ).first()


def release_number_for_tenant(
    db: Session,
    tenant_id: UUID,
    updated_by_user_id: UUID | None = None,
) -> bool:
    """
    Release the active phone number for a tenant back to the carrier.
    Sets status='released' and released_at=now().
    Returns True on success, False if no active number found.
    """
    record = get_active_number_for_tenant(db, tenant_id)
    if not record:
        logger.warning(f"No active number to release for tenant {tenant_id}")
        return False

    carrier = get_sms_carrier()
    try:
        carrier.release_number(record.phone_number)
    except Exception as exc:
        logger.error(f"Carrier release_number failed for {record.phone_number}: {exc}")
        # Continue to mark as released in DB even if carrier fails

    record.status = "released"
    record.released_at = datetime.now(UTC)
    record.updated_by = updated_by_user_id
    db.add(record)
    db.commit()
    logger.info(f"Released number {record.phone_number} for tenant {tenant_id}")
    return True


def _suggest_nearby_area_codes(failed_area_code: str) -> list[str]:
    """
    Return up to 3 alternative area codes when provisioning fails.
    MVP: hardcoded Texas alternatives for the 512 default.
    """
    fallback_map = {
        "512": ["737", "830", "361"],
        "737": ["512", "830", "361"],
        "214": ["972", "469", "817"],
        "972": ["214", "469", "817"],
        "713": ["281", "832", "346"],
        "281": ["713", "832", "346"],
    }
    return fallback_map.get(failed_area_code, ["888", "877", "866"])
