"""
B14/A73 — Tenant signup wizard state machine service.
Used by: signup.py routes (A73).

SIGNUP-GA-1: ``initiate_signup()`` is now resolve-or-attach by email (ADR-0011).
The Post-Confirmation Lambda (Path 3) creates the tenant + owner user; this
function attaches the wizard to that tenant, overwrites the placeholder name,
and persists owner identity. If the Lambda hasn't fired yet (client raced
ahead of Cognito confirmation), it creates a pending-credential signup keyed
by owner_email.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlmodel import Session, select

from app.models.auth import TenantUser
from app.models.core import Tenant, User
from app.models.signup import TenantSignup
from app.models.subscription import SubscriptionTier

logger = logging.getLogger(__name__)

VALID_STATE_TRANSITIONS = {
    "step1_account": "step2_legal",
    "step2_legal": "step3_phone",
    "step3_phone": "step4_tier",
    "step4_tier": "step5_confirm",
    "step5_confirm": "complete",
}


def initiate_signup(
    db: Session,
    business_name: str,
    trade: str,
    business_size: str,
    zip_code: str,
    time_zone: str,
    owner_email: str,
    owner_first_name: str,
    owner_last_name: str,
    request: Request | None = None,
) -> dict:
    """
    Step 1: Resolve-or-attach by email (ADR-0011, design §F).

    SELF-SERVE flow:
      1. Look up an existing owner ``user`` by ``owner_email`` (created by the
         Post-Confirmation Lambda Path 3 after Cognito SignUp confirmation).
      2. If found: attach/return a ``TenantSignup(step1_account)`` for that
         tenant, persist business fields + owner_email/names, and OVERWRITE
         ``tenant.name`` with the real ``business_name``. Idempotent.
      3. If not found (client raced ahead of confirmation): create a
         pending-credential ``TenantSignup`` keyed by ``owner_email``,
         reconciled when the Lambda fires. Returns ``credential_pending=True``.

    MUST NOT create a second tenant when the Lambda already made one for this
    email. Race-safe: on a concurrent-insert anomaly, re-select and attach
    rather than raising.

    Returns:
        dict with tenant_id, signup_state, owner_email, credential_pending
    """
    normalized_email = owner_email.strip().lower()

    # --- Resolve-or-attach: look up an existing owner user by email ---
    existing_user = db.exec(select(User).where(User.email == normalized_email)).first()

    if existing_user:
        # The Lambda (Path 3) already created the tenant + owner user.
        # Find the tenant via tenant_user.
        tenant_user = db.exec(
            select(TenantUser).where(TenantUser.user_id == existing_user.id)
        ).first()

        if tenant_user:
            tenant_id = tenant_user.tenant_id
            # Check for an existing signup record (idempotent resume).
            existing_signup = db.exec(
                select(TenantSignup).where(TenantSignup.tenant_id == tenant_id)
            ).first()

            if existing_signup:
                # If already past step1_account, this is a resume conflict.
                if existing_signup.signup_state != "step1_account":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "type": "https://pilotfortrades.com/errors/signup-state-conflict",
                            "title": "Signup State Conflict",
                            "status": 409,
                            "detail": (
                                f"Email '{normalized_email}' maps to a tenant "
                                f"already past step1_account "
                                f"(state='{existing_signup.signup_state}'). "
                                "Please resume from the current state."
                            ),
                            "current_state": existing_signup.signup_state,
                        },
                    )
                # Idempotent: same step1_account state — return existing.
                return {
                    "tenant_id": str(tenant_id),
                    "signup_state": existing_signup.signup_state,
                    "owner_email": normalized_email,
                    "credential_pending": False,
                }

            # No signup record yet — create one and attach to the
            # Lambda-created tenant. Overwrite the placeholder name.
            tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
            if tenant:
                tenant.name = business_name
                db.add(tenant)

            signup = TenantSignup(
                tenant_id=tenant_id,
                signup_state="step1_account",
                signup_started_at=datetime.now(UTC),
                business_name=business_name,
                trade=trade,
                business_size=business_size,
                zip=zip_code,
                time_zone=time_zone,
                owner_email=normalized_email,
                owner_first_name=owner_first_name,
                owner_last_name=owner_last_name,
            )
            db.add(signup)
            db.commit()
            db.refresh(signup)

            logger.info(
                "Signup attached to Lambda-created tenant %s for %s",
                tenant_id,
                normalized_email,
            )
            return {
                "tenant_id": str(tenant_id),
                "signup_state": signup.signup_state,
                "owner_email": normalized_email,
                "credential_pending": False,
            }

    # --- Credential pending: client raced ahead of Cognito confirmation ---
    # Check if a pending-credential signup already exists for this email.
    existing_pending = db.exec(
        select(TenantSignup).where(TenantSignup.owner_email == normalized_email)
    ).first()

    if existing_pending:
        # Idempotent — return the existing pending signup.
        return {
            "tenant_id": str(existing_pending.tenant_id),
            "signup_state": existing_pending.signup_state,
            "owner_email": normalized_email,
            "credential_pending": True,
        }

    # Create a pending-credential tenant + signup (no user yet — the Lambda
    # will create the user when Cognito confirms). The tenant name is the
    # real business_name (no unique constraint — ADR-0012).
    import uuid as _uuid

    tenant = Tenant(
        id=_uuid.uuid4(),
        name=business_name,
        is_active=True,
    )
    db.add(tenant)
    db.flush()

    signup = TenantSignup(
        tenant_id=tenant.id,
        signup_state="step1_account",
        signup_started_at=datetime.now(UTC),
        business_name=business_name,
        trade=trade,
        business_size=business_size,
        zip=zip_code,
        time_zone=time_zone,
        owner_email=normalized_email,
        owner_first_name=owner_first_name,
        owner_last_name=owner_last_name,
    )
    db.add(signup)
    db.commit()
    db.refresh(tenant)
    db.refresh(signup)

    logger.info(
        "Pending-credential signup created for tenant %s (%s) — awaiting "
        "Cognito confirmation for %s",
        tenant.id,
        business_name,
        normalized_email,
    )

    return {
        "tenant_id": str(tenant.id),
        "signup_state": signup.signup_state,
        "owner_email": normalized_email,
        "credential_pending": True,
    }


def advance_wizard_step(
    db: Session,
    tenant_id: UUID,
    current_state: str,
    step_data: dict,
    request: Request | None = None,
) -> dict:
    """
    Advance wizard from current_state to next state.

    Args:
        db:            Active DB session
        tenant_id:     Target tenant
        current_state: Expected current state (validated against DB — staleness guard)
        step_data:     Step-specific payload (varies by step)
        request:       FastAPI Request (for IP, User-Agent capture in A74)

    Returns:
        dict with tenant_id, signup_state, next_step

    Raises:
        HTTPException(409): If current DB state != current_state (resumability conflict)
        HTTPException(422): If step_data is invalid for the current step
        HTTPException(404): If signup record not found
    """
    signup = db.exec(
        select(TenantSignup).where(TenantSignup.tenant_id == tenant_id)
    ).first()

    if not signup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Signup record not found",
                "status": 404,
                "detail": f"No signup record found for tenant {tenant_id}.",
            },
        )

    # ALPHA-FIX-1: forward-idempotent replay for the terminal step only.
    # Paid-tier flow PUTs step5 twice (plan page + ready page); a retry of a
    # completed step5 must converge, not 409. All other steps keep the strict
    # 409 staleness guard below (a repeated earlier step is a genuine resume
    # conflict the frontend handles by redirect).
    if current_state == "step4_tier" and signup.signup_state in (
        "step5_confirm",
        "complete",
    ):
        return {
            "tenant_id": str(tenant_id),
            "signup_state": signup.signup_state,
            "next_step": None,
        }

    # Staleness guard — verify the DB state matches expected
    if signup.signup_state != current_state:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://pilotfortrades.com/errors/signup-state-conflict",
                "title": "Signup State Conflict",
                "status": 409,
                "detail": f"Expected state '{current_state}' but current state is '{signup.signup_state}'. "
                "Please resume from the current state.",
                "current_state": signup.signup_state,
            },
        )

    # Validate transition
    next_state = VALID_STATE_TRANSITIONS.get(current_state)
    if not next_state:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"No valid transition from state '{current_state}'",
        )

    # ALPHA-FIX-1: process the data of the step being SUBMITTED (destination
    # state), not the origin state. Frontend contract: PUT /stepN submits step
    # N's data. The _process_step_data branches were always written against
    # destination-step data; only the dispatch key was wrong.
    _process_step_data(db, tenant_id, next_state, step_data, signup, request)

    # ALPHA-FIX-1: step5 processing completes the wizard in the same
    # transaction (no route advances step5_confirm → complete; step5_confirm is
    # transient and never rests in the DB). All other steps advance to
    # next_state as before.
    if next_state == "step5_confirm":
        signup.signup_state = "complete"
        signup.signup_completed_at = datetime.now(UTC)
    else:
        signup.signup_state = next_state

    db.add(signup)
    db.commit()
    db.refresh(signup)

    logger.info(
        f"Signup for tenant {tenant_id}: {current_state} → {signup.signup_state}"
    )

    return {
        "tenant_id": str(tenant_id),
        "signup_state": signup.signup_state,
        "next_step": VALID_STATE_TRANSITIONS.get(signup.signup_state),
    }


def _process_step_data(
    db: Session,
    tenant_id: UUID,
    current_state: str,
    step_data: dict,
    signup: TenantSignup,
    request: Request | None,
) -> None:
    """Handle step-specific side effects."""
    if current_state == "step2_legal":
        # Legal acceptance handled separately via POST /legal/accept (A74)
        # Step 2 advance just confirms the legal step was done
        pass

    elif current_state == "step3_phone":
        # SIGNUP-C: "Stay Informed" — phone is REQUIRED (phone_skipped removed).
        # Records the owner's mobile on user_endpoint (channel=sms) + the
        # attestation audit row; enqueues the platform double-opt-in SMS when
        # sms_consent is True. The consent checkbox is unchecked by default;
        # the reply-YES double-opt-in is the authoritative consent.
        phone_number = step_data.get("phone_number")
        if not phone_number:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "type": "https://errors.pilotfortrades.com/validation-error",
                    "title": "Validation Error",
                    "status": 422,
                    "detail": "phone_number is required for step 3.",
                },
            )

        sms_consent = bool(step_data.get("sms_consent", False))
        disclosure_hash = step_data.get("disclosure_hash") or ""
        user_id = step_data.get("user_id")

        # Resolve the owner user. The authenticated route injects user_id;
        # the /test counterpart uses the canonical test user.
        if user_id is None:
            from app.models.auth import TenantUser

            tenant_user = db.exec(
                select(TenantUser).where(TenantUser.tenant_id == tenant_id)
            ).first()
            if tenant_user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "type": "https://errors.pilotfortrades.com/not-found",
                        "title": "Owner user not found",
                        "status": 404,
                        "detail": "No owner user found for this tenant.",
                    },
                )
            user_id = tenant_user.user_id

        client_ip = None
        if request is not None and request.client is not None:
            client_ip = request.client.host

        from services.notification_endpoints import upsert_owner_sms_endpoint

        upsert_owner_sms_endpoint(
            db,
            user_id=user_id,
            tenant_id=tenant_id,
            phone=phone_number,
            consent=sms_consent,
            ip=client_ip,
            disclosure_hash=disclosure_hash,
        )

        # Enqueue the platform double-opt-in SMS only when the owner opted in.
        if sms_consent:
            from tasks.sms_compliance_platform import send_platform_double_optin_sms

            send_platform_double_optin_sms.delay(str(user_id), str(tenant_id))

    elif current_state == "step4_tier":
        # C-B5: Tier selection with cohort cap enforcement + Stripe creation.
        # Locks the tier row (SELECT ... FOR UPDATE) to prevent concurrent
        # signup_cap violations, assigns charter_member_number (idempotent),
        # computes free_period_ends_at (idempotent), and creates the Stripe
        # Customer + Charter Subscription (non-blocking on failure).
        selected_tier_id = step_data.get("selected_tier_id")
        if not selected_tier_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "type": "https://errors.pilotfortrades.com/validation-error",
                    "title": "Validation Error",
                    "status": 422,
                    "detail": "selected_tier_id is required for step 4.",
                },
            )

        # Lock the tier row for the cohort cap transaction (sync SQLAlchemy).
        tier = db.exec(
            select(SubscriptionTier)
            .where(SubscriptionTier.tier_id == selected_tier_id)
            .with_for_update()
        ).first()

        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://errors.pilotfortrades.com/not-found",
                    "title": "Tier not found",
                    "status": 404,
                    "detail": "Selected tier not found.",
                },
            )

        # C-B5: Only enforce the is_active gate for capped tiers (e.g. Charter).
        # Uncapped tiers (trial, starter, teams) may have is_active=false for
        # marketing reasons (MKT-B11) but remain valid selectable tiers at
        # signup — the old step4 handler did not filter by is_active.
        if not tier.is_active and tier.signup_cap is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "type": "https://pilotfortrades.com/errors/tier-closed",
                    "title": "Tier no longer available",
                    "status": 409,
                    "detail": (
                        "This tier has reached its signup cap and is no "
                        "longer accepting new members."
                    ),
                },
            )

        tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://errors.pilotfortrades.com/not-found",
                    "title": "Tenant not found",
                    "status": 404,
                    "detail": "Tenant not found.",
                },
            )

        # Set tier on tenant
        tenant.current_subscription_tier_id = tier.tier_id

        # Compute free_period_ends_at (idempotent — only if not already set)
        if tier.free_period_days and not tenant.free_period_ends_at:
            from datetime import timedelta

            tenant.free_period_ends_at = datetime.now(UTC) + timedelta(
                days=tier.free_period_days
            )

        # Assign charter_member_number (idempotent — only for charter tier,
        # only if not already assigned). Enforce signup_cap with is_active flip.
        if tier.tier_name == "charter" and not tenant.charter_member_number:
            from sqlalchemy import func

            existing_count = db.exec(
                select(func.count(Tenant.id)).where(
                    Tenant.charter_member_number.isnot(None)
                )
            ).one()
            tenant.charter_member_number = existing_count + 1

            # Flip is_active if the cap is reached (same transaction).
            if tier.signup_cap and tenant.charter_member_number >= tier.signup_cap:
                tier.is_active = False
                db.add(tier)

        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        db.refresh(tier)

        # Create Stripe Customer + Charter Subscription (idempotent + non-blocking).
        # These functions commit internally, so they run AFTER the cohort cap
        # transaction above. Failures are logged and do not block the wizard.
        if not tenant.stripe_customer_id:
            billing_email = signup.owner_email or ""
            try:
                from services.stripe_subscriptions import (
                    create_charter_subscription,
                    create_stripe_customer,
                )

                stripe_customer_id = create_stripe_customer(
                    db, tenant_id, billing_email
                )
                # Reload tenant to pick up the stripe_customer_id set by
                # create_stripe_customer (it commits internally).
                db.refresh(tenant)

                # Create Charter subscription (charter tier only, with trial).
                if (
                    tier.tier_name == "charter"
                    and tenant.free_period_ends_at
                    and stripe_customer_id
                ):
                    create_charter_subscription(
                        db=db,
                        tenant_id=tenant_id,
                        stripe_customer_id=stripe_customer_id,
                        free_period_ends_at=tenant.free_period_ends_at,
                        charter_member_number=tenant.charter_member_number,
                    )
            except Exception as e:
                # Non-blocking — wizard still advances. Tom can create the
                # Stripe resources manually later.
                logger.error(
                    "C-B5 step4_tier: Stripe creation failed for tenant %s: %s. "
                    "Wizard advancing; Stripe resources must be created manually.",
                    tenant_id,
                    e,
                )

    elif current_state == "step5_confirm":
        # C-B5: Branch on requires_payment_method.
        # Charter (requires_payment_method=false): skip activate_trial() —
        #   the Stripe trial (trial_end) handles the free period. Just mark
        #   the onboarding checklist tier_selected=true.
        # Non-Charter (requires_payment_method=true): keep existing
        #   activate_trial() behavior.
        if step_data.get("confirmed"):
            tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
            if tenant and tenant.current_subscription_tier_id:
                tier = db.exec(
                    select(SubscriptionTier).where(
                        SubscriptionTier.tier_id == tenant.current_subscription_tier_id
                    )
                ).first()

                if tier and tier.requires_payment_method:
                    # Non-Charter: activate trial (old behavior)
                    user_id = step_data.get("user_id")
                    if user_id:
                        from services.trial_management import activate_trial

                        activate_trial(db, tenant_id, user_id)
                else:
                    # Charter: trial handled by Stripe (trial_end). Just mark
                    # the onboarding checklist tier_selected=true.
                    from services.onboarding_service import ensure_checklist_exists

                    ensure_checklist_exists(db, tenant_id)


def get_signup_state(db: Session, tenant_id: UUID) -> dict:
    """Return current signup state and collected wizard data for resumability."""
    signup = db.exec(
        select(TenantSignup).where(TenantSignup.tenant_id == tenant_id)
    ).first()

    if not signup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signup record not found for this tenant",
        )

    # C-B5: Load tenant + tier to surface Charter lifecycle fields.
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    tier = None
    if tenant and tenant.current_subscription_tier_id:
        tier = db.exec(
            select(SubscriptionTier).where(
                SubscriptionTier.tier_id == tenant.current_subscription_tier_id
            )
        ).first()

    # PLATFORM-SMS-B1 / SIGNUP-C-FU3: Derive sms_consent_status from the
    # owner's SMS user_endpoint. The frontend phone page polls
    # collected_data.sms_consent_status === "opted_in" to know when to advance
    # past "Check your phone". The value is derived from verification_status
    # (the YES-reply terminal state), NOT from consent_status (which flips at
    # checkbox attestation, before YES confirmation).
    #   - "opted_in"  → endpoint exists AND verification_status == "verified"
    #   - "pending"   → endpoint exists but verification_status != "verified"
    #   - None        → no sms endpoint for the owner
    sms_consent_status = None
    owner_tenant_user = db.exec(
        select(TenantUser).where(
            TenantUser.tenant_id == tenant_id,
            TenantUser.role_code == "owner",
        )
    ).first()
    if owner_tenant_user is not None:
        from services.notification_endpoints import get_owner_sms_endpoint

        owner_sms_endpoint = get_owner_sms_endpoint(
            db, user_id=owner_tenant_user.user_id
        )
        if owner_sms_endpoint is not None:
            if owner_sms_endpoint.verification_status == "verified":
                sms_consent_status = "opted_in"
            else:
                sms_consent_status = "pending"

    return {
        "tenant_id": str(tenant_id),
        "signup_state": signup.signup_state,
        "collected_data": {
            "business_name": signup.business_name,
            "trade": signup.trade,
            "business_size": signup.business_size,
            "zip": signup.zip,
            "time_zone": signup.time_zone,
            "owner_first_name": signup.owner_first_name,
            "owner_last_name": signup.owner_last_name,
            "tier_selected": signup.signup_state
            in ("step4_tier", "step5_confirm", "complete"),
            "free_period_ends_at": (
                tenant.free_period_ends_at.isoformat()
                if tenant and tenant.free_period_ends_at
                else None
            ),
            "requires_payment_method": (tier.requires_payment_method if tier else True),
            "charter_member_number": (
                tenant.charter_member_number
                if tenant and tenant.charter_member_number
                else None
            ),
            "sms_consent_status": sms_consent_status,
        },
    }


# ==================== SIGNUP-GA-1: ABANDONED SIGNUP CLEANUP HELPER ====================


def list_abandoned_signups(db: Session, older_than_days: int) -> list[dict]:
    """
    Identify abandoned self-serve signups by ``signup_state`` (design §F).

    Returns signups where:
      - ``signup_state != 'complete'`` (never finished the wizard)
      - ``tenant.created_at < now() - older_than_days`` (stale)

    This helper REPORTS/IDENTIFIES only — it does NOT auto-delete. Actual
    deletion is a separate, guarded operation (not in this batch). The
    ``"...'s Company"`` name pattern is a human hint only, never the reaping
    key (a real contractor could legitimately be named "Dave's Company").

    Args:
        db: Active DB session.
        older_than_days: Age threshold in days.

    Returns:
        List of dicts with tenant_id, owner_email, signup_state, created_at.
    """
    from sqlalchemy import text

    sql = text(
        """
        SELECT t.id, ts.owner_email, ts.signup_state, t.created_at
        FROM public.tenant t
        JOIN public.tenant_signup ts ON ts.tenant_id = t.id
        WHERE ts.signup_state <> 'complete'
          AND t.created_at < now() - (:days || ' days')::interval
        ORDER BY t.created_at ASC
        """
    )
    result = db.execute(sql, {"days": older_than_days})
    return [
        {
            "tenant_id": str(row.id),
            "owner_email": row.owner_email,
            "signup_state": row.signup_state,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in result
    ]
