"""
B14/A73 — Tenant Signup State Machine tests.

Test focus cases:
1. initiate_signup creates tenant + tenant_signup record with step1_account state
2. advance_wizard_step transitions step1 → step2 → ... correctly
3. advance_wizard_step 409 if current_state doesn't match DB state
4. advance_wizard_step validates step3 phone data (verified or skipped required)
5. advance_wizard_step updates tenant.current_subscription_tier_id on step4
6. GET /signup/{id}/state/test returns current state + collected data
7. POST /signup/test creates signup
8. PUT /signup/{id}/step{N}/test advances state
9. trial expiration check: check_trial_expired returns True after trial_ends_at
10. compute_trial_end_date uses operator override when set
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

from app.models.core import Tenant
from app.models.signup import TenantSignup
from app.models.subscription import SubscriptionTier

# ==================== FIXTURES ====================


@pytest.fixture
def trial_tier(db_session):
    """Return trial tier (is_trial=True). Note: is_active=False post MKT-B11 but
    still a valid selectable tier at signup — step4 no longer filters by is_active."""
    return db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
    ).first()


@pytest.fixture
def signup_tenant(db_session, trial_tier):
    """Create a tenant + signup record in step1_account state."""
    t = Tenant(
        id=uuid.uuid4(),
        name=f"Signup Test Tenant {uuid.uuid4().hex[:8]}",
        is_active=True,
        current_subscription_tier_id=trial_tier.tier_id,
    )
    db_session.add(t)
    db_session.flush()

    s = TenantSignup(
        tenant_id=t.id,
        signup_state="step1_account",
        signup_started_at=datetime.now(UTC),
        business_name="Johnson Electric",
        trade="electrical",
        business_size="2-5",
        zip="10001",
        time_zone="America/New_York",
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(t)
    db_session.refresh(s)
    return t, s


# ==================== SERVICE LAYER TESTS ====================


class TestInitiateSignup:
    """Test case 1: initiate_signup."""

    def test_initiate_creates_tenant_and_signup(self, db_session):
        from services.tenant_signup import initiate_signup

        result = initiate_signup(
            db=db_session,
            business_name="Test Electric",
            trade="electrical",
            business_size="solo",
            zip_code="90210",
            time_zone="America/Los_Angeles",
            owner_email="test@example.com",
            owner_first_name="Tom",
            owner_last_name="Test",
        )

        assert "tenant_id" in result
        assert result["signup_state"] == "step1_account"
        assert result["owner_email"] == "test@example.com"

        # Verify DB rows exist
        tenant_id = uuid.UUID(result["tenant_id"])
        tenant = db_session.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
        assert tenant is not None
        assert tenant.name == "Test Electric"

        signup = db_session.exec(
            select(TenantSignup).where(TenantSignup.tenant_id == tenant_id)
        ).first()
        assert signup is not None
        assert signup.signup_state == "step1_account"


class TestWizardStateTransitions:
    """Test cases 2-5: State machine transitions."""

    def test_step1_to_step2_transition(self, db_session, signup_tenant):
        from services.tenant_signup import advance_wizard_step

        tenant, _signup = signup_tenant
        result = advance_wizard_step(db_session, tenant.id, "step1_account", {})
        assert result["signup_state"] == "step2_legal"

    def test_step2_to_step3_transition(self, db_session, signup_tenant):
        from unittest.mock import patch

        from app.models.core import User
        from services.tenant_signup import advance_wizard_step

        tenant, signup = signup_tenant
        # Manually advance to step2
        signup.signup_state = "step2_legal"
        db_session.add(signup)
        db_session.commit()

        # ALPHA-FIX-1: destination-state dispatch — advancing from step2_legal
        # processes step3_phone data (phone_number required).
        owner = User(
            id=uuid.uuid4(),
            email=f"owner-{uuid.uuid4().hex[:8]}@test.local",
            first_name="Owner",
            last_name="Test",
            is_active=True,
        )
        db_session.add(owner)
        db_session.flush()

        with patch(
            "tasks.sms_compliance_platform.send_platform_double_optin_sms"
        ) as mock_task:
            result = advance_wizard_step(
                db_session,
                tenant.id,
                "step2_legal",
                {
                    "phone_number": "+15125550100",
                    "sms_consent": False,
                    "disclosure_hash": "a" * 64,
                    "user_id": owner.id,
                },
            )
        assert result["signup_state"] == "step3_phone"
        mock_task.delay.assert_not_called()

    def test_step3_requires_phone_number(self, db_session, signup_tenant):
        """SIGNUP-C: step3 now requires phone_number (phone_skipped removed)."""
        from fastapi import HTTPException

        from services.tenant_signup import advance_wizard_step

        tenant, signup = signup_tenant
        # ALPHA-FIX-1: set to step2_legal so destination is step3_phone (which
        # requires phone_number). Under the old origin-keyed dispatch this test
        # set step3_phone and passed step3_phone — which under the new contract
        # would dispatch to step4_tier (wrong branch).
        signup.signup_state = "step2_legal"
        db_session.add(signup)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            advance_wizard_step(db_session, tenant.id, "step2_legal", {})
        assert exc_info.value.status_code == 422

    def test_step3_accepts_phone_number_no_consent(self, db_session, signup_tenant):
        """SIGNUP-C: phone_number without sms_consent advances; no SMS sent."""
        from unittest.mock import patch

        from app.models.core import User
        from services.tenant_signup import advance_wizard_step

        tenant, signup = signup_tenant
        # ALPHA-FIX-1: set to step2_legal so destination is step3_phone (which
        # processes phone data). Under the old origin-keyed dispatch this test
        # set step3_phone and passed step3_phone — which under the new contract
        # would dispatch to step4_tier (wrong branch).
        signup.signup_state = "step2_legal"
        db_session.add(signup)
        db_session.commit()

        # Create an owner user for this tenant (the authenticated route injects
        # user_id; the direct-service test must supply it in step_data).
        owner = User(
            id=uuid.uuid4(),
            email=f"owner-{uuid.uuid4().hex[:8]}@test.local",
            first_name="Owner",
            last_name="Test",
            is_active=True,
        )
        db_session.add(owner)
        db_session.flush()

        # Patch the platform task so .delay is never called when consent is False.
        # The import is local inside _process_step_data, so patch at source.
        with patch(
            "tasks.sms_compliance_platform.send_platform_double_optin_sms"
        ) as mock_task:
            result = advance_wizard_step(
                db_session,
                tenant.id,
                "step2_legal",
                {
                    "phone_number": "+15125550100",
                    "sms_consent": False,
                    "disclosure_hash": "a" * 64,
                    "user_id": owner.id,
                },
            )
        assert result["signup_state"] == "step3_phone"
        mock_task.delay.assert_not_called()

    def test_step4_updates_subscription_tier(
        self, db_session, signup_tenant, trial_tier
    ):
        from services.tenant_signup import advance_wizard_step

        tenant, signup = signup_tenant
        # ALPHA-FIX-1: set to step3_phone so destination is step4_tier (which
        # processes tier data). Under the old origin-keyed dispatch this test
        # set step4_tier and passed step4_tier — which under the new contract
        # would dispatch to step5_confirm (wrong branch).
        signup.signup_state = "step3_phone"
        db_session.add(signup)
        db_session.commit()

        result = advance_wizard_step(
            db_session,
            tenant.id,
            "step3_phone",
            {"selected_tier_id": str(trial_tier.tier_id)},
        )
        assert result["signup_state"] == "step4_tier"

        # Verify tier was updated on tenant
        db_session.refresh(tenant)
        assert tenant.current_subscription_tier_id == trial_tier.tier_id

    def test_conflict_409_when_state_mismatch(self, db_session, signup_tenant):
        from fastapi import HTTPException

        from services.tenant_signup import advance_wizard_step

        tenant, _signup = signup_tenant
        # Signup is in step1_account, but we claim step2_legal

        with pytest.raises(HTTPException) as exc_info:
            advance_wizard_step(db_session, tenant.id, "step2_legal", {})
        assert exc_info.value.status_code == 409


class TestGetSignupState:
    """Test case 6: get_signup_state."""

    def test_returns_current_state_and_data(self, db_session, signup_tenant):
        from services.tenant_signup import get_signup_state

        tenant, _signup = signup_tenant
        result = get_signup_state(db_session, tenant.id)

        assert result["tenant_id"] == str(tenant.id)
        assert result["signup_state"] == "step1_account"
        assert result["collected_data"]["business_name"] == "Johnson Electric"
        assert result["collected_data"]["trade"] == "electrical"


class TestSignupEndpoints:
    """Test cases 7-8: API endpoints."""

    def test_post_signup_test_creates_record(self, client, test_tenant):
        response = client.post(
            "/api/v1/signup/test",
            json={
                "business_name": "API Test Electric",
                "trade": "electrical",
                "business_size": "solo",
                "zip": "10001",
                "time_zone": "America/New_York",
                "owner_email": "api@test.com",
                "owner_first_name": "Api",
                "owner_last_name": "Test",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "tenant_id" in data
        assert data["signup_state"] == "step1_account"

    def test_get_signup_state_test(self, client, test_tenant, db_session):
        from services.tenant_signup import initiate_signup

        result = initiate_signup(
            db=db_session,
            business_name="State Test",
            trade="electrical",
            business_size="solo",
            zip_code="10001",
            time_zone="UTC",
            owner_email="state@test.com",
            owner_first_name="S",
            owner_last_name="T",
        )
        tenant_id = result["tenant_id"]

        response = client.get(f"/api/v1/signup/{tenant_id}/state/test")
        assert response.status_code == 200
        data = response.json()
        assert data["signup_state"] == "step1_account"
        assert data["collected_data"]["business_name"] == "State Test"


class TestTrialManagement:
    """Test cases 9-10: trial_management service."""

    def test_check_trial_expired_returns_false_before_expiry(
        self, db_session, signup_tenant, trial_tier
    ):
        from services.trial_management import check_trial_expired

        tenant, _ = signup_tenant
        tenant.trial_ends_at = datetime.now(UTC) + timedelta(days=7)
        db_session.add(tenant)
        db_session.commit()

        assert check_trial_expired(db_session, tenant.id) is False

    def test_check_trial_expired_returns_true_after_expiry(
        self, db_session, signup_tenant, trial_tier
    ):
        from services.trial_management import check_trial_expired

        tenant, _ = signup_tenant
        tenant.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        db_session.add(tenant)
        db_session.commit()

        assert check_trial_expired(db_session, tenant.id) is True

    def test_compute_trial_end_uses_operator_override(self, db_session, signup_tenant):
        from datetime import UTC

        from sqlalchemy import text

        from services.trial_management import compute_trial_end_date

        tenant, _ = signup_tenant
        trial_start = datetime.now(UTC)

        # Insert operator override with 30-day trial
        db_session.execute(text("SET LOCAL session_replication_role = 'replica'"))
        db_session.execute(
            text("""
                INSERT INTO tenant_tier_override
                    (tenant_id, override_trial_length_days, override_reason, set_by_operator_user_id, set_at, created_at, updated_at)
                VALUES
                    (:tid, 30, 'Test override — extended trial for signup state machine test', '00000000-0000-0000-0000-000000000002', now(), now(), now())
            """),
            {"tid": str(tenant.id)},
        )
        db_session.execute(text("SET LOCAL session_replication_role = 'origin'"))
        db_session.commit()

        end_date = compute_trial_end_date(db_session, tenant.id, trial_start)
        diff_days = (end_date - trial_start).days
        assert diff_days == 30

    def test_compute_trial_end_uses_tier_default(self, db_session, signup_tenant):
        from services.trial_management import compute_trial_end_date

        tenant, _ = signup_tenant
        trial_start = datetime.now(UTC)

        # No override — should use tier's trial_duration_days (14)
        end_date = compute_trial_end_date(db_session, tenant.id, trial_start)
        diff_days = (end_date - trial_start).days
        assert diff_days == 14
