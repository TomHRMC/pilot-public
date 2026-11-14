"""
ALPHA-FIX-1 — Signup wizard contract regression tests (identity_access domain).

Locks in the corrected destination-state dispatch contract (design §D/§F.1/§F.2):

  1. Full wizard chain step1→step5 with per-step payloads → final state
     ``complete``, ``signup_completed_at`` set.
  2. The production failure case: origin ``step3_phone`` + ``{"selected_tier_id": ...}``
     → advances to ``step4_tier`` and sets ``tenant.current_subscription_tier_id``
     (no more 422).
  3. Origin ``step2_legal`` + phone payload → SMS ``user_endpoint`` row persisted
     for the inserted user (scope assertions by inserted IDs — never row counts).
  4. Origin ``step2_legal`` **without** ``phone_number`` → 422 (SIGNUP-C guard
     intact).
  5. Step5 replay when already ``complete`` → 200, and ``activate_trial`` /
     ``ensure_checklist_exists`` are NOT re-invoked (mock call counts).
  6. Non-terminal replay (step4 payload when already past ``step3_phone``) → 409
     unchanged.

Domain: identity_access (PRD §3.5)
"""

import hashlib
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlmodel import select

from app.models.auth import TenantUser
from app.models.core import Tenant, User, UserEndpoint
from app.models.signup import TenantSignup
from app.models.subscription import SubscriptionTier
from services.tenant_signup import advance_wizard_step

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


# ==================== FIXTURES ====================


def _make_charter_tier(db_session) -> SubscriptionTier:
    """Insert a fresh Charter-like tier row for this test (ID-scoped)."""
    tier = SubscriptionTier(
        tier_id=uuid.uuid4(),
        tier_name="charter",
        display_label=f"AlphaFix1 Charter {uuid.uuid4().hex[:8]}",
        annual_price_cents=58800,
        monthly_price_cents=4900,
        is_trial=False,
        is_active=True,
        display_order=99,
        free_period_days=90,
        requires_payment_method=False,
        signup_cap=12,
        price_locked=True,
    )
    db_session.add(tier)
    db_session.flush()
    return tier


def _make_tenant_signup_owner(
    db_session, *, tier_id, state="step1_account"
) -> tuple[Tenant, TenantSignup, User]:
    """Insert a tenant + tenant_signup + owner user at the given state."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"AlphaFix1 Test {uuid.uuid4().hex[:8]}",
        is_active=True,
        current_subscription_tier_id=tier_id,
    )
    db_session.add(tenant)
    db_session.flush()

    owner = User(
        id=uuid.uuid4(),
        email=f"owner-{uuid.uuid4().hex[:8]}@test.local",
        first_name="Owner",
        last_name="Test",
        is_active=True,
    )
    db_session.add(owner)
    db_session.flush()

    # Attach owner to tenant (role_code + status_id NOT NULL — MCP-verified).
    db_session.add(
        TenantUser(
            tenant_id=tenant.id,
            user_id=owner.id,
            role_code="owner",
            status_id="5b67cfd3-ef42-4311-9516-a4eec8642628",
            is_active=True,
        )
    )

    signup = TenantSignup(
        tenant_id=tenant.id,
        signup_state=state,
        signup_started_at=datetime.now(UTC),
        business_name="AlphaFix1 Electric",
        trade="electrical",
        business_size="solo",
        zip="10001",
        time_zone="America/New_York",
        owner_email=owner.email,
        owner_first_name="Owner",
        owner_last_name="Test",
    )
    db_session.add(signup)
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(owner)
    db_session.refresh(signup)
    return tenant, signup, owner


# ==================== TESTS ====================


class TestAlphaFix1WizardContract:
    """ALPHA-FIX-1 — destination-state dispatch + step5 auto-complete + replay."""

    def test_full_wizard_chain_reaches_complete(self, db_session):
        """Case 1: step1→step5 with per-step payloads → complete + completed_at set."""
        tier = _make_charter_tier(db_session)
        tenant, signup, owner = _make_tenant_signup_owner(
            db_session, tier_id=tier.tier_id, state="step1_account"
        )

        with (
            patch("services.stripe_subscriptions.create_stripe_customer") as mock_cust,
            patch(
                "services.stripe_subscriptions.create_charter_subscription"
            ) as mock_sub,
            patch("tasks.sms_compliance_platform.send_platform_double_optin_sms"),
            patch("services.trial_management.activate_trial"),
            patch("services.onboarding_service.ensure_checklist_exists"),
        ):
            mock_cust.return_value = f"cus_full_{uuid.uuid4().hex[:8]}"
            mock_sub.return_value = f"sub_full_{uuid.uuid4().hex[:8]}"

            # step1 → step2 (legal: no-op branch, documents_accepted ignored)
            r1 = advance_wizard_step(db_session, tenant.id, "step1_account", {})
            assert r1["signup_state"] == "step2_legal"

            # step2 → step3 (phone payload processed by step3_phone branch)
            r2 = advance_wizard_step(
                db_session,
                tenant.id,
                "step2_legal",
                {
                    "phone_number": "+15125550001",
                    "sms_consent": False,
                    "disclosure_hash": hashlib.sha256(b"d").hexdigest(),
                    "user_id": owner.id,
                },
            )
            assert r2["signup_state"] == "step3_phone"

            # step3 → step4 (tier payload processed by step4_tier branch)
            r3 = advance_wizard_step(
                db_session,
                tenant.id,
                "step3_phone",
                {"selected_tier_id": str(tier.tier_id)},
            )
            assert r3["signup_state"] == "step4_tier"

            # step4 → step5 → complete (confirm payload; auto-complete in one tx)
            r4 = advance_wizard_step(
                db_session,
                tenant.id,
                "step4_tier",
                {"confirmed": True, "user_id": str(owner.id)},
            )
            assert r4["signup_state"] == "complete"
            assert r4["next_step"] is None

        # signup_completed_at set on the terminal transition
        db_session.refresh(signup)
        assert signup.signup_state == "complete"
        assert signup.signup_completed_at is not None

    def test_step4_tier_payload_advances_without_422(self, db_session):
        """Case 2: the production failure — origin step3_phone + tier payload.

        Before ALPHA-FIX-1 this raised 422 "phone_number is required for step 3."
        because the origin-keyed dispatch ran the step3_phone branch. Now the
        destination-state dispatch runs the step4_tier branch and sets
        tenant.current_subscription_tier_id.
        """
        tier = _make_charter_tier(db_session)
        tenant, _signup, _owner = _make_tenant_signup_owner(
            db_session, tier_id=tier.tier_id, state="step3_phone"
        )

        with (
            patch("services.stripe_subscriptions.create_stripe_customer") as mock_cust,
            patch("services.stripe_subscriptions.create_charter_subscription"),
        ):
            mock_cust.return_value = f"cus_prod_{uuid.uuid4().hex[:8]}"

            result = advance_wizard_step(
                db_session,
                tenant.id,
                "step3_phone",
                {"selected_tier_id": str(tier.tier_id)},
            )

        assert result["signup_state"] == "step4_tier"
        db_session.refresh(tenant)
        assert tenant.current_subscription_tier_id == tier.tier_id

    def test_step3_phone_payload_persists_sms_endpoint(self, db_session):
        """Case 3: origin step2_legal + phone payload → SMS user_endpoint row.

        Scoped by the inserted user_id — never a row-count assertion.
        """
        tier = _make_charter_tier(db_session)
        tenant, _signup, owner = _make_tenant_signup_owner(
            db_session, tier_id=tier.tier_id, state="step2_legal"
        )

        phone = "+15125550002"
        with patch("tasks.sms_compliance_platform.send_platform_double_optin_sms"):
            advance_wizard_step(
                db_session,
                tenant.id,
                "step2_legal",
                {
                    "phone_number": phone,
                    "sms_consent": False,
                    "disclosure_hash": hashlib.sha256(b"d").hexdigest(),
                    "user_id": owner.id,
                },
            )

        # Scoped by the inserted user_id — resilient to any other data.
        endpoint = db_session.exec(
            select(UserEndpoint).where(
                UserEndpoint.user_id == owner.id,
                UserEndpoint.channel == "sms",
                UserEndpoint.value == phone,
            )
        ).first()
        assert endpoint is not None
        assert endpoint.verification_status == "pending"

    def test_step3_without_phone_returns_422(self, db_session):
        """Case 4: origin step2_legal without phone_number → 422 (SIGNUP-C intact)."""
        from fastapi import HTTPException

        tier = _make_charter_tier(db_session)
        tenant, _signup, owner = _make_tenant_signup_owner(
            db_session, tier_id=tier.tier_id, state="step2_legal"
        )

        with pytest.raises(HTTPException) as exc_info:
            advance_wizard_step(
                db_session,
                tenant.id,
                "step2_legal",
                {"user_id": owner.id},
            )
        assert exc_info.value.status_code == 422
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail["status"] == 422
        assert "phone_number" in detail["detail"]

    def test_step5_replay_when_complete_returns_200_no_side_effects(self, db_session):
        """Case 5: step5 replay when already complete → 200, no re-activation.

        The paid-tier flow PUTs step5 twice (plan page + ready page); a retry of
        a completed step5 must converge, not 409, and must NOT re-run
        activate_trial / ensure_checklist_exists.
        """
        tier = _make_charter_tier(db_session)
        tenant, signup, owner = _make_tenant_signup_owner(
            db_session, tier_id=tier.tier_id, state="step4_tier"
        )

        with (
            patch("services.stripe_subscriptions.create_stripe_customer") as mock_cust,
            patch("services.stripe_subscriptions.create_charter_subscription"),
            patch("services.trial_management.activate_trial") as mock_trial,
            patch(
                "services.onboarding_service.ensure_checklist_exists"
            ) as mock_checklist,
        ):
            mock_cust.return_value = f"cus_replay_{uuid.uuid4().hex[:8]}"

            # First step5 → complete
            r1 = advance_wizard_step(
                db_session,
                tenant.id,
                "step4_tier",
                {"confirmed": True, "user_id": str(owner.id)},
            )
            assert r1["signup_state"] == "complete"

            # Replay step5 (origin step4_tier, DB now complete) → 200 idempotent
            r2 = advance_wizard_step(
                db_session,
                tenant.id,
                "step4_tier",
                {"confirmed": True, "user_id": str(owner.id)},
            )
            assert r2["signup_state"] == "complete"
            assert r2["next_step"] is None

        # activate_trial / ensure_checklist_exists called exactly once (first
        # step5 only — the replay must not re-invoke them).
        # Note: for charter tier (requires_payment_method=False) the step5
        # branch calls ensure_checklist_exists, not activate_trial.
        mock_trial.assert_not_called()
        mock_checklist.assert_called_once()

        # State unchanged by the replay
        db_session.refresh(signup)
        assert signup.signup_state == "complete"
        assert signup.signup_completed_at is not None

    def test_non_terminal_replay_returns_409(self, db_session):
        """Case 6: step4 payload when already past step3_phone → 409 unchanged.

        The step5 forward-idempotency exception applies ONLY to the terminal
        step. A replay of an earlier step (e.g. step4 when the DB is already at
        step4_tier or beyond, but the caller claims step3_phone) is a genuine
        resume conflict → 409.
        """
        from fastapi import HTTPException

        tier = _make_charter_tier(db_session)
        tenant, _signup, _owner = _make_tenant_signup_owner(
            db_session, tier_id=tier.tier_id, state="step4_tier"
        )

        # DB is at step4_tier; caller claims step3_phone (a step4 PUT replay).
        # This is NOT the terminal step → strict 409 staleness guard applies.
        with pytest.raises(HTTPException) as exc_info:
            advance_wizard_step(
                db_session,
                tenant.id,
                "step3_phone",
                {"selected_tier_id": str(tier.tier_id)},
            )
        assert exc_info.value.status_code == 409
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail["status"] == 409
