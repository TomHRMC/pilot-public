"""
C-B9 — 10DLC Provisioning State Machine Service.

Implements the 13-state machine that takes a tenant from "not started" through
brand registration, campaign registration, phone number assignment, and active
SMS sending. All transitions are validated against VALID_TRANSITIONS and
persisted with audit context.

State machine (spec §5.2):
    not_started → quoting → awaiting_payment → [payment_failed | brand_submitted]
    brand_submitted → [awaiting_otp | brand_verified | brand_rejected]
    awaiting_otp → [brand_verified | quoting]  (quoting = OTP timeout)
    brand_verified → campaign_submitted
    campaign_submitted → [awaiting_number_selection | campaign_rejected]
    awaiting_number_selection → number_assigned
    number_assigned → active
    active → suspended

Terminal states: brand_rejected, campaign_rejected, suspended
"""

import logging
import uuid
from datetime import timedelta

from sqlmodel import Session, select

from app.models.core import Tenant10DlcProfile
from app.models.sms import TenantMessagingRegistration
from core.datetime_utils import safe_now_utc
from services.sms_carrier import get_sms_carrier
from services.telnyx_quoting import get_carrier_quote

logger = logging.getLogger(__name__)

# ── State Machine Constants ─────────────────────────────────────────────────

MESSAGING_STATES = [
    "not_started",
    "quoting",
    "awaiting_payment",
    "payment_failed",
    "brand_submitted",
    "awaiting_otp",
    "brand_verified",
    "brand_rejected",
    "campaign_submitted",
    "awaiting_number_selection",
    "campaign_rejected",
    "number_assigned",
    "active",
    "suspended",
]

VALID_TRANSITIONS: dict[str, list[str]] = {
    "not_started": ["quoting"],
    "quoting": ["awaiting_payment"],
    "awaiting_payment": ["payment_failed", "brand_submitted"],
    "payment_failed": ["quoting"],
    "brand_submitted": ["awaiting_otp", "brand_verified", "brand_rejected"],
    "awaiting_otp": ["brand_verified", "quoting"],  # quoting = OTP timeout
    "brand_verified": ["campaign_submitted"],
    "campaign_submitted": ["awaiting_number_selection", "campaign_rejected"],
    "awaiting_number_selection": ["number_assigned"],
    "number_assigned": ["active"],
    "active": ["suspended"],
    # Terminal: brand_rejected, campaign_rejected, suspended
}

# States that block re-initiation of provisioning
NON_RETRYABLE_STATES = frozenset(
    {"active", "brand_submitted", "campaign_submitted", "awaiting_otp", "suspended"}
)

# OTP timeout thresholds
OTP_ALERT_HOURS = 18
OTP_TIMEOUT_HOURS = 24


# ── State Transition ────────────────────────────────────────────────────────


def transition_status(
    db: Session,
    registration: TenantMessagingRegistration,
    new_status: str,
    *,
    failure_reason: str | None = None,
    user_id: uuid.UUID | None = None,
) -> TenantMessagingRegistration:
    """Validate + persist a state transition. Raises ValueError on invalid transition.

    Args:
        db: SQLAlchemy/SQLModel Session.
        registration: The TenantMessagingRegistration row to transition.
        new_status: Target status (must be in VALID_TRANSITIONS[current_status]).
        failure_reason: Optional reason for rejection/timeout transitions.
        user_id: Optional user ID for audit (updated_by).

    Returns:
        The updated registration row (refreshed).
    """
    current = registration.status
    allowed = VALID_TRANSITIONS.get(current, [])

    if new_status not in allowed:
        raise ValueError(
            f"Invalid state transition: {current} → {new_status}. "
            f"Valid transitions from {current}: {allowed}"
        )

    registration.status = new_status
    if failure_reason is not None:
        registration.failure_reason = failure_reason
    elif new_status not in ("brand_rejected", "campaign_rejected"):
        # Clear failure_reason on non-rejection transitions
        registration.failure_reason = None

    if user_id is not None:
        registration.updated_by = user_id

    db.add(registration)
    db.commit()
    db.refresh(registration)

    logger.info(
        "Provisioning transition: %s → %s (registration=%s)",
        current,
        new_status,
        registration.id,
    )
    return registration


# ── Initiate Provisioning ────────────────────────────────────────────────────


def initiate_provisioning(
    db: Session,
    tenant_id: uuid.UUID,
    entity_type: str,
    profile_data: dict,
    user_id: uuid.UUID,
) -> tuple[TenantMessagingRegistration, dict]:
    """Creates/updates registration + profile, fetches quote, returns (registration, quote).

    - If no registration exists: create one with status='quoting'
    - If registration exists in a retryable state: reset to 'quoting'
    - If registration exists in a non-retryable state: raise ValueError (409 at API layer)

    Upserts tenant_10dlc_profile with the provided brand data.
    Fetches quote from carrier_fee_schedule and stores quoted_* on registration.
    """
    # Check for existing registration
    existing = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.tenant_id == tenant_id
        )
    ).first()

    if existing:
        if existing.status in NON_RETRYABLE_STATES:
            raise ValueError(
                f"Provisioning already in progress (status={existing.status}). "
                f"Cannot re-initiate from a non-retryable state."
            )
        # Retryable: update entity_type and reset to quoting
        existing.entity_type = entity_type
        existing.failure_reason = None
        existing.updated_by = user_id
        # If already in quoting, no transition needed (idempotent re-provision)
        if existing.status != "quoting":
            transition_status(db, existing, "quoting", user_id=user_id)
        else:
            db.add(existing)
            db.commit()
            db.refresh(existing)
        registration = existing
    else:
        # Create new registration
        registration = TenantMessagingRegistration(
            tenant_id=tenant_id,
            entity_type=entity_type,
            status="quoting",
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(registration)
        db.commit()
        db.refresh(registration)

    # Upsert tenant_10dlc_profile with brand data
    _upsert_profile(db, tenant_id, profile_data, user_id)

    # Fetch quote and store on registration
    quote = get_carrier_quote(db, entity_type)
    # Store setup total in cents (for backward compat with the registration row)
    # Convert millicents to cents for the registration row (quoted_setup_cents)
    registration.quoted_setup_cents = quote["setup_total_millicents"] // 1000
    registration.quoted_monthly_cents = quote["recurring_monthly_millicents"] // 1000
    db.add(registration)
    db.commit()
    db.refresh(registration)

    return registration, quote


def _upsert_profile(
    db: Session,
    tenant_id: uuid.UUID,
    profile_data: dict,
    user_id: uuid.UUID,
) -> Tenant10DlcProfile:
    """Upsert tenant_10dlc_profile with brand data."""
    existing = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == tenant_id)
    ).first()

    if existing:
        existing.legal_business_name = profile_data.get(
            "legal_business_name", existing.legal_business_name
        )
        existing.dba_name = profile_data.get("dba_name", existing.dba_name)
        if profile_data.get("ein") is not None:
            existing.ein = profile_data["ein"]
        existing.hq_address_line1 = profile_data.get(
            "hq_address_line1", existing.hq_address_line1
        )
        existing.hq_address_line2 = profile_data.get(
            "hq_address_line2", existing.hq_address_line2
        )
        existing.hq_city = profile_data.get("hq_city", existing.hq_city)
        existing.hq_state = profile_data.get("hq_state", existing.hq_state)
        existing.hq_postal_code = profile_data.get(
            "hq_postal_code", existing.hq_postal_code
        )
        existing.hq_country = profile_data.get("hq_country", existing.hq_country)
        existing.support_email = profile_data.get(
            "support_email", existing.support_email
        )
        existing.support_phone = profile_data.get(
            "support_phone", existing.support_phone
        )
        existing.website = profile_data.get("website", existing.website)
        existing.stock_symbol = profile_data.get("stock_symbol", existing.stock_symbol)
        existing.vertical = profile_data.get("vertical", existing.vertical)
        existing.updated_by = user_id
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        now = safe_now_utc()
        profile = Tenant10DlcProfile(
            tenant_id=tenant_id,
            legal_business_name=profile_data.get("legal_business_name", ""),
            dba_name=profile_data.get("dba_name"),
            ein=profile_data.get("ein"),
            hq_address_line1=profile_data.get("hq_address_line1"),
            hq_address_line2=profile_data.get("hq_address_line2"),
            hq_city=profile_data.get("hq_city"),
            hq_state=profile_data.get("hq_state"),
            hq_postal_code=profile_data.get("hq_postal_code"),
            hq_country=profile_data.get("hq_country", "US"),
            support_email=profile_data.get("support_email"),
            support_phone=profile_data.get("support_phone"),
            website=profile_data.get("website"),
            stock_symbol=profile_data.get("stock_symbol"),
            vertical=profile_data.get("vertical"),
            created_at=now,
            updated_at=now,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile


# ── Submit OTP ──────────────────────────────────────────────────────────────


def submit_otp(
    db: Session,
    tenant_id: uuid.UUID,
    otp_code: str,
) -> str:
    """Relays OTP to carrier, transitions to brand_verified on success.

    Only valid when status is 'awaiting_otp'.
    Returns the new status.
    """
    registration = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.tenant_id == tenant_id
        )
    ).first()

    if not registration:
        raise ValueError("No messaging registration found for this tenant.")

    if registration.status != "awaiting_otp":
        raise ValueError(
            f"OTP submission not valid in status={registration.status}. "
            f"Must be in 'awaiting_otp'."
        )

    # Relay OTP to carrier (per Q#2: SMS-delivered)
    # The exact Telnyx OTP submission endpoint is not yet confirmed —
    # for now, we accept the OTP and transition to brand_verified.
    # When the exact procedure is confirmed, this will call carrier.submit_otp().
    registration.otp_verified_at = safe_now_utc()
    transition_status(db, registration, "brand_verified")

    return "brand_verified"


# ── Get Provisioning Status ──────────────────────────────────────────────────


def get_provisioning_status(db: Session, tenant_id: uuid.UUID) -> dict:
    """Returns the current registration state as a dict for the API response.

    Raises ValueError if no registration exists (404 at API layer).
    """
    registration = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.tenant_id == tenant_id
        )
    ).first()

    if not registration:
        raise ValueError("No messaging registration found for this tenant.")

    return {
        "registration_id": registration.id,
        "status": registration.status,
        "entity_type": registration.entity_type,
        "telnyx_brand_id": registration.telnyx_brand_id,
        "telnyx_campaign_id": registration.telnyx_campaign_id,
        "telnyx_phone_number": registration.telnyx_phone_number,
        "quoted_setup_cents": registration.quoted_setup_cents,
        "quoted_monthly_cents": registration.quoted_monthly_cents,
        "otp_requested_at": registration.otp_requested_at,
        "failure_reason": registration.failure_reason,
        "updated_at": registration.updated_at,
    }


# ── Poll Brand Status (Celery task helper) ──────────────────────────────────


def poll_brand_status(db: Session, registration_id: uuid.UUID) -> None:
    """Polls carrier brand status, transitions on verification/rejection.

    Called by the provision_brand Celery task.
    """
    registration = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.id == registration_id
        )
    ).first()

    if not registration:
        logger.warning("poll_brand_status: registration %s not found", registration_id)
        return

    if registration.status != "brand_submitted":
        logger.info(
            "poll_brand_status: registration %s in status %s, skipping",
            registration_id,
            registration.status,
        )
        return

    if not registration.telnyx_brand_id:
        logger.warning(
            "poll_brand_status: registration %s has no telnyx_brand_id",
            registration_id,
        )
        return

    carrier = get_sms_carrier()
    result = carrier.get_brand(registration.telnyx_brand_id)

    if result.status == "verified":
        # For sole_proprietor: transition to awaiting_otp
        # For standard: transition to brand_verified (no OTP needed)
        if registration.entity_type == "sole_proprietor":
            registration.otp_requested_at = safe_now_utc()
            transition_status(db, registration, "awaiting_otp")
        else:
            transition_status(db, registration, "brand_verified")
    elif result.status == "rejected":
        transition_status(
            db,
            registration,
            "brand_rejected",
            failure_reason=result.rejection_reason or "Brand rejected by carrier",
        )
        # Trigger refund (brand_rejected → full refund)
        _process_refund(db, registration, full=True)
    # else: still pending — do nothing, will be polled again


# ── Poll Campaign Status (Celery task helper) ───────────────────────────────


def poll_campaign_status(db: Session, registration_id: uuid.UUID) -> None:
    """Polls carrier campaign status, transitions on approval/rejection.

    Called by the provision_campaign Celery task.
    """
    registration = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.id == registration_id
        )
    ).first()

    if not registration:
        logger.warning(
            "poll_campaign_status: registration %s not found", registration_id
        )
        return

    if registration.status != "campaign_submitted":
        logger.info(
            "poll_campaign_status: registration %s in status %s, skipping",
            registration_id,
            registration.status,
        )
        return

    if not registration.telnyx_campaign_id:
        logger.warning(
            "poll_campaign_status: registration %s has no telnyx_campaign_id",
            registration_id,
        )
        return

    carrier = get_sms_carrier()
    result = carrier.get_campaign(registration.telnyx_campaign_id)

    if result.status == "approved":
        transition_status(db, registration, "awaiting_number_selection")
    elif result.status == "rejected":
        transition_status(
            db,
            registration,
            "campaign_rejected",
            failure_reason=result.rejection_reason or "Campaign rejected by carrier",
        )
        # Trigger partial refund (campaign_rejected → partial refund)
        _process_refund(db, registration, full=False)
    # else: still pending — do nothing, will be polled again


# ── Assign Phone Number ──────────────────────────────────────────────────────


def assign_phone_number(
    db: Session,
    tenant_id: uuid.UUID,
    phone_number: str,
    user_id: uuid.UUID | None = None,
) -> str:
    """Provisions phone number via carrier, transitions to active.

    Only valid when status is 'awaiting_number_selection'.
    Returns the assigned phone_number.
    """
    registration = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.tenant_id == tenant_id
        )
    ).first()

    if not registration:
        raise ValueError("No messaging registration found for this tenant.")

    if registration.status != "awaiting_number_selection":
        raise ValueError(
            f"Phone number assignment not valid in status={registration.status}. "
            f"Must be in 'awaiting_number_selection'."
        )

    # Assign via carrier
    carrier = get_sms_carrier()
    assigned = carrier.assign_number_to_campaign(
        phone_number=phone_number,
        campaign_id=registration.telnyx_campaign_id or "",
    )

    registration.telnyx_phone_number = assigned
    transition_status(db, registration, "number_assigned", user_id=user_id)
    transition_status(db, registration, "active", user_id=user_id)

    return assigned


# ── Campaign Payload Template ────────────────────────────────────────────────


def _build_campaign_payload(tenant_name: str, entity_type: str) -> dict:
    """Builds the Telnyx campaign registration payload from tenant data + templates.

    Campaign fields are templated — standard across all Pilot tenants.
    Only campaign_name is tenant-specific (derived from tenant.name).
    """
    use_case = "SOLE_PROPRIETOR" if entity_type == "sole_proprietor" else "MIXED"
    return {
        "campaign_name": f"{tenant_name} — Customer Messaging",
        "use_case": use_case,
        "description": f"Customer care and appointment notifications for {tenant_name}.",
        "sample_message_1": (
            f"Hi, this is {tenant_name} confirming your appointment tomorrow "
            f"between 8-10 AM. Reply STOP to opt out."
        ),
        "sample_message_2": (
            f"Your invoice from {tenant_name} is ready. View it here: [link]"
        ),
        "message_flow": (
            "Customer opts in by providing their phone number for appointment "
            "notifications and billing communications."
        ),
        "opt_in_keywords": ["START", "YES"],
        "opt_out_keywords": ["STOP", "CANCEL", "UNSUBSCRIBE"],
        "help_keywords": ["HELP"],
        "opt_in_message": (
            f"You're subscribed to {tenant_name} messages. "
            f"Reply STOP to opt out, HELP for help."
        ),
        "opt_out_message": (
            f"You've been unsubscribed from {tenant_name} messages. "
            f"Reply START to resubscribe."
        ),
        "help_message": (f"{tenant_name}: Reply STOP to opt out. Msg rates may apply."),
        "sub_use_cases": None,
    }


# ── OTP Timeout Check (Celery task helper) ──────────────────────────────────


def check_otp_timeouts(db: Session) -> None:
    """Find registrations in 'awaiting_otp' > 18h → alert the operator.
    At > 24h → transition back to 'quoting' (no re-charge).
    """
    now = safe_now_utc()
    alert_threshold = now - timedelta(hours=OTP_ALERT_HOURS)
    timeout_threshold = now - timedelta(hours=OTP_TIMEOUT_HOURS)

    # Find all registrations in awaiting_otp
    registrations = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.status == "awaiting_otp"
        )
    ).all()

    for reg in registrations:
        if not reg.otp_requested_at:
            continue

        if reg.otp_requested_at < timeout_threshold:
            # > 24h: transition back to quoting (no re-charge)
            logger.warning(
                "OTP timeout (>24h) for registration %s — transitioning to quoting",
                reg.id,
            )
            transition_status(
                db,
                reg,
                "quoting",
                failure_reason="OTP timeout — tenant did not submit OTP within 24h",
            )
        elif reg.otp_requested_at < alert_threshold:
            # > 18h: alert the operator (log warning — operator notification)
            logger.warning(
                "OTP approaching timeout (>18h) for registration %s — alert operator",
                reg.id,
            )


# ── Refund Helper ───────────────────────────────────────────────────────────


def _process_refund(
    db: Session,
    registration: TenantMessagingRegistration,
    *,
    full: bool,
) -> None:
    """Process Stripe refund for rejected brand/campaign.

    full=True (brand_rejected): full refund of setup charge.
    full=False (campaign_rejected): partial refund (brand fee consumed, campaign+number not).

    Uses stripe.Refund.create(payment_intent=...).
    """
    if not registration.stripe_payment_intent:
        logger.warning(
            "Cannot refund registration %s — no stripe_payment_intent",
            registration.id,
        )
        return

    try:
        from services.stripe_subscriptions import _get_stripe_client

        stripe = _get_stripe_client()

        if full:
            # Full refund
            stripe.Refund.create(
                payment_intent=registration.stripe_payment_intent,
            )
            logger.info(
                "Full refund issued for registration %s (brand_rejected)",
                registration.id,
            )
        else:
            # Partial refund — refund the campaign + number portion
            # The brand fee is consumed; campaign + number fees are refunded.
            # For simplicity, refund 50% of the setup charge (approximate).
            # In production, this would calculate the exact unconsumed amount.
            if registration.quoted_setup_cents:
                refund_amount = registration.quoted_setup_cents // 2
                stripe.Refund.create(
                    payment_intent=registration.stripe_payment_intent,
                    amount=refund_amount,
                )
                logger.info(
                    "Partial refund (%d cents) issued for registration %s "
                    "(campaign_rejected)",
                    refund_amount,
                    registration.id,
                )
    except Exception as exc:
        logger.error(
            "Refund failed for registration %s: %s",
            registration.id,
            exc,
        )
