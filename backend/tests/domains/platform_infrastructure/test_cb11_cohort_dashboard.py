"""Tests for C-B11 — Operator Cohort Dashboard.

Domain: platform_infrastructure (PRD §3.8)

Covers:
    - PlatformUser + get_platform_user() auth dependency
    - get_cohort_overview() aggregation service
    - extend_free_period() silent extension service
    - close_cohort() cohort close service
    - 4 API endpoints (GET /cohort, POST /extend, POST /close, GET /auth/me)
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _create_platform_user(
    db_session, email="platform-test@pilot.local", role_code="owner"
):
    """Create a platform user + platform role for testing."""
    from app.models.core import PlatformRole, User

    role = db_session.exec(
        select(PlatformRole).where(PlatformRole.code == role_code)
    ).first()
    if not role:
        role = PlatformRole(
            code=role_code,
            name=f"Test {role_code}",
            permissions={
                "write": ["tenants", "users", "billing", "plans"],
                "read_all": True,
            },
            is_active=True,
        )
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    user = User(
        id=uuid.uuid4(),
        email=email,
        is_platform_user=True,
        platform_role_code=role_code,
        is_active=True,
        mfa_enforced=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _mock_platform_jwt(mock_cognito_jwt_verify, platform_user):
    """Configure mock_cognito_jwt_verify to return a platform user's email."""
    mock_cognito_jwt_verify.return_value = {
        "sub": str(platform_user.id),
        "email": platform_user.email,
    }
    return f"Bearer mock_token_{uuid.uuid4()}"


def _create_charter_tenant(db_session, name="Charter Test Co", member_number=None):
    """Create a Charter-eligible tenant for testing."""
    from app.models.core import Tenant

    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"{name} {uuid.uuid4().hex[:8]}",
        charter_eligible=True,
        charter_member_number=member_number,
        free_period_ends_at=datetime.now(UTC) + timedelta(days=90),
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


def _create_subscription(
    db_session, tenant_id, status_code="trialing", psp_sub_id=None
):
    """Create a subscription row for a tenant."""
    from app.models.billing import Subscription, SubscriptionStatus

    status = db_session.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == status_code)
    ).first()

    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_plan_code="charter_plan",
        status_id=status.id,
        psp_provider="stripe",
        psp_subscription_id=psp_sub_id or f"sub_test_{uuid.uuid4().hex[:8]}",
        psp_customer_id=f"cus_test_{uuid.uuid4().hex[:8]}",
        is_active=True,
        trial_ends_at=datetime.now(UTC) + timedelta(days=90),
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


def _create_job(db_session, tenant_id, days_ago=0):
    """Create a Job with the required Customer + Site + JobStatus chain."""
    from app.models.crm import Customer, Site
    from app.models.fulfillment import Job, JobStatus

    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        display_name=f"Test Customer {uuid.uuid4().hex[:8]}",
        type="person",
        is_active=True,
        preferred_contact_channel="email",
        sms_opted_out=False,
        sms_opt_in_consent=False,
        card_required=False,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    site = Site(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_type="residential",
        is_active=True,
    )
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)

    # Get or create a draft job status
    status = db_session.exec(select(JobStatus).where(JobStatus.code == "draft")).first()
    if not status:
        status = JobStatus(
            id=uuid.uuid4(),
            code="draft",
            name="Draft",
            is_terminal=False,
            is_default=True,
            is_active=True,
        )
        db_session.add(status)
        db_session.commit()
        db_session.refresh(status)

    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_id=site.id,
        status_id=status.id,
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
        is_active=True,
        version=1,
        job_number=f"JOB-{uuid.uuid4().hex[:10].upper()}",
        priority="standard",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


# ─────────────────────────────────────────────────────────────────────────────
# PlatformUser + get_platform_user() tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPlatformUserAuth:
    """Tests for the PlatformUser model + get_platform_user() dependency."""

    def test_get_platform_user_valid(self, client, db_session, mock_cognito_jwt_verify):
        """Platform user with valid JWT + is_platform_user=True → 200 on /cohort."""
        platform_user = _create_platform_user(db_session)
        token = _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        client.headers.update({"Authorization": token})

        resp = client.get("/api/v1/operator/cohort")
        assert resp.status_code == 200
        data = resp.json()
        assert "members" in data
        assert "cohort_tier_name" in data

    def test_get_platform_user_tenant_user_rejected(
        self, client, db_session, mock_cognito_jwt, test_user
    ):
        """Tenant user (not platform) → 403 on /cohort."""
        mock_cognito_jwt(test_user)

        resp = client.get("/api/v1/operator/cohort")
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# get_cohort_overview() tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCohortOverview:
    """Tests for the get_cohort_overview() aggregation service."""

    def test_cohort_overview_empty(self, db_session):
        """No Charter members → empty list, tier metadata returned."""
        from services.cohort_dashboard import get_cohort_overview

        result = get_cohort_overview(db_session)
        assert result["cohort_tier_name"] == "charter"
        assert result["cohort_is_active"] is True
        assert result["signup_cap"] == 12
        assert isinstance(result["members"], list)

    def test_cohort_overview_with_members(self, db_session):
        """2 Charter members → correct aggregation."""
        from services.cohort_dashboard import get_cohort_overview

        t1 = _create_charter_tenant(db_session, "Member One", member_number=100)
        t2 = _create_charter_tenant(db_session, "Member Two", member_number=101)
        _create_subscription(db_session, t1.id, status_code="trialing")
        _create_subscription(db_session, t2.id, status_code="active")

        result = get_cohort_overview(db_session)
        member_ids = {m["tenant_id"] for m in result["members"]}
        assert str(t1.id) in member_ids
        assert str(t2.id) in member_ids

        for m in result["members"]:
            if m["tenant_id"] == str(t1.id):
                assert m["stripe_status"] == "trialing"
                assert m["business_name"] == t1.name
            if m["tenant_id"] == str(t2.id):
                assert m["stripe_status"] == "active"

    def test_cohort_alert_red(self, db_session):
        """Member with days_since_last_job > 7 → alert_level='red'."""
        from services.cohort_dashboard import get_cohort_overview

        tenant = _create_charter_tenant(db_session, "Red Alert Co", member_number=200)
        _create_job(db_session, tenant.id, days_ago=10)

        result = get_cohort_overview(db_session)
        member = next(m for m in result["members"] if m["tenant_id"] == str(tenant.id))
        assert member["alert_level"] == "red"
        assert member["days_since_last_job"] == 10

    def test_cohort_alert_amber(self, db_session):
        """Member with free_period_ends_at within 14 days → alert_level='amber'."""
        from app.models.core import Tenant
        from services.cohort_dashboard import get_cohort_overview

        tenant = Tenant(
            id=uuid.uuid4(),
            name=f"Amber Co {uuid.uuid4().hex[:8]}",
            charter_eligible=True,
            charter_member_number=300,
            free_period_ends_at=datetime.now(UTC) + timedelta(days=10),
        )
        db_session.add(tenant)
        db_session.commit()
        # Recent job (within 7 days) so red doesn't trigger
        _create_job(db_session, tenant.id, days_ago=3)

        result = get_cohort_overview(db_session)
        member = next(m for m in result["members"] if m["tenant_id"] == str(tenant.id))
        assert member["alert_level"] == "amber"
        assert member["days_remaining"] <= 14

    def test_cohort_alert_red_takes_precedence(self, db_session):
        """Member with both conditions → alert_level='red'."""
        from app.models.core import Tenant
        from services.cohort_dashboard import get_cohort_overview

        tenant = Tenant(
            id=uuid.uuid4(),
            name=f"Both Co {uuid.uuid4().hex[:8]}",
            charter_eligible=True,
            charter_member_number=400,
            free_period_ends_at=datetime.now(UTC) + timedelta(days=5),
        )
        db_session.add(tenant)
        db_session.commit()
        # Old job (> 7 days) + free period ending soon
        _create_job(db_session, tenant.id, days_ago=10)

        result = get_cohort_overview(db_session)
        member = next(m for m in result["members"] if m["tenant_id"] == str(tenant.id))
        assert member["alert_level"] == "red"

    def test_cohort_alert_no_jobs(self, db_session):
        """Member with no jobs → days_since_last_job=null, alert_level='red'."""
        from services.cohort_dashboard import get_cohort_overview

        tenant = _create_charter_tenant(db_session, "No Jobs Co", member_number=500)

        result = get_cohort_overview(db_session)
        member = next(m for m in result["members"] if m["tenant_id"] == str(tenant.id))
        assert member["days_since_last_job"] is None
        assert member["alert_level"] == "red"


# ─────────────────────────────────────────────────────────────────────────────
# extend_free_period() tests
# ─────────────────────────────────────────────────────────────────────────────


class TestExtendFreePeriod:
    """Tests for the extend_free_period() service."""

    def test_extend_free_period_happy_path(self, db_session):
        """Valid extension → override set, tenant.free_period_ends_at updated,
        Stripe Subscription.modify called."""
        from services.cohort_dashboard import extend_free_period

        tenant = _create_charter_tenant(db_session, "Extend Co", member_number=600)
        sub = _create_subscription(db_session, tenant.id, status_code="trialing")

        # Create a real platform user for the FK constraint
        operator = _create_platform_user(
            db_session, email="operator-extend@pilot.local"
        )
        operator_id = operator.id
        new_end = datetime.now(UTC) + timedelta(days=120)

        with patch("services.stripe_subscriptions._get_stripe_client") as mock_stripe:
            mock_client = MagicMock()
            mock_stripe.return_value = mock_client

            result = extend_free_period(
                db=db_session,
                tenant_id=tenant.id,
                new_end_date=new_end,
                reason="Customer needs more time",
                operator_user_id=operator_id,
            )

        assert result["stripe_trial_end_updated"] is True
        assert result["stripe_subscription_id"] == sub.psp_subscription_id
        mock_client.Subscription.modify.assert_called_once()

        # Verify tenant was updated
        db_session.refresh(tenant)
        assert tenant.free_period_ends_at is not None

        # Verify override was created
        from app.models.subscription import TenantTierOverride

        override = db_session.exec(
            select(TenantTierOverride).where(TenantTierOverride.tenant_id == tenant.id)
        ).first()
        assert override is not None
        assert override.override_reason == "Customer needs more time"

    def test_extend_free_period_not_trialing(self, db_session):
        """Subscription status is 'paused' → ValueError (409 at endpoint)."""
        from services.cohort_dashboard import extend_free_period

        tenant = _create_charter_tenant(db_session, "Paused Co", member_number=700)
        _create_subscription(db_session, tenant.id, status_code="paused")

        with pytest.raises(ValueError, match="trialing"):
            extend_free_period(
                db=db_session,
                tenant_id=tenant.id,
                new_end_date=datetime.now(UTC) + timedelta(days=120),
                reason="test",
                operator_user_id=uuid.uuid4(),
            )

    def test_extend_free_period_past_date(self, db_session):
        """new_free_period_ends_at before current → ValueError (422)."""
        from services.cohort_dashboard import extend_free_period

        tenant = _create_charter_tenant(db_session, "Past Date Co", member_number=800)
        _create_subscription(db_session, tenant.id, status_code="trialing")

        with pytest.raises(ValueError, match="must be after"):
            extend_free_period(
                db=db_session,
                tenant_id=tenant.id,
                new_end_date=datetime.now(UTC) - timedelta(days=10),
                reason="test",
                operator_user_id=uuid.uuid4(),
            )

    def test_extend_free_period_non_charter(self, db_session):
        """Tenant is not Charter → ValueError (404)."""
        from app.models.core import Tenant
        from services.cohort_dashboard import extend_free_period

        tenant = Tenant(
            id=uuid.uuid4(),
            name=f"Non-Charter {uuid.uuid4().hex[:8]}",
            charter_eligible=False,
        )
        db_session.add(tenant)
        db_session.commit()

        with pytest.raises(ValueError, match="not a Charter"):
            extend_free_period(
                db=db_session,
                tenant_id=tenant.id,
                new_end_date=datetime.now(UTC) + timedelta(days=120),
                reason="test",
                operator_user_id=uuid.uuid4(),
            )

    def test_extend_free_period_operator_not_found(self, db_session):
        """C-B14-FIX Task 5: operator_user_id that doesn't exist in the user
        table → ValueError("... not found ...") before the override upsert.
        No tenant_tier_override row written; tenant.free_period_ends_at unchanged."""
        from app.models.subscription import TenantTierOverride
        from services.cohort_dashboard import extend_free_period

        tenant = _create_charter_tenant(
            db_session, "OperatorNotFound Co", member_number=900
        )
        _create_subscription(db_session, tenant.id, status_code="trialing")

        original_free_period = tenant.free_period_ends_at
        fake_operator_id = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            extend_free_period(
                db=db_session,
                tenant_id=tenant.id,
                new_end_date=datetime.now(UTC) + timedelta(days=120),
                reason="test",
                operator_user_id=fake_operator_id,
            )

        # No override row written for this tenant
        override = db_session.exec(
            select(TenantTierOverride).where(TenantTierOverride.tenant_id == tenant.id)
        ).first()
        assert override is None

        # tenant.free_period_ends_at unchanged
        db_session.refresh(tenant)
        assert tenant.free_period_ends_at == original_free_period


# ─────────────────────────────────────────────────────────────────────────────
# close_cohort() tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCloseCohort:
    """Tests for the close_cohort() service."""

    def test_close_cohort_happy_path(self, db_session):
        """Close → price archived, tier deactivated, other tiers activated."""
        from services.cohort_dashboard import close_cohort

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_stripe,
            patch("core.stripe_config.get_stripe_ids") as mock_ids,
        ):
            mock_client = MagicMock()
            mock_stripe.return_value = mock_client
            mock_ids.return_value = {
                "prices": {"price_charter_monthly": "price_test_charter"}
            }

            result = close_cohort(db=db_session, operator_user_id=uuid.uuid4())

        assert result["charter_price_archived"] is True
        assert result["charter_tier_deactivated"] is True
        assert "trial" in result["activated_tiers"]
        assert "starter" in result["activated_tiers"]
        assert "teams" in result["activated_tiers"]
        mock_client.Price.modify.assert_called_once_with(
            "price_test_charter", active=False
        )

    def test_close_cohort_already_closed(self, db_session):
        """is_active already false → ValueError (409)."""
        from app.models.subscription import SubscriptionTier
        from services.cohort_dashboard import close_cohort

        # Deactivate the charter tier
        charter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
        ).first()
        original_active = charter.is_active
        charter.is_active = False
        db_session.add(charter)
        db_session.commit()

        try:
            with pytest.raises(ValueError, match="already closed"):
                close_cohort(db=db_session, operator_user_id=uuid.uuid4())
        finally:
            charter.is_active = original_active
            db_session.add(charter)
            db_session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint auth tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEndpointAuth:
    """Tests for endpoint-level auth (platform vs tenant)."""

    def test_endpoint_auth_tenant_user_blocked(
        self, client, db_session, mock_cognito_jwt, test_user
    ):
        """Tenant user JWT on /operator/cohort → 403."""
        mock_cognito_jwt(test_user)

        resp = client.get("/api/v1/operator/cohort")
        assert resp.status_code == 403

    def test_endpoint_auth_platform_user_allowed(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """Platform user JWT on /operator/cohort → 200."""
        platform_user = _create_platform_user(db_session, email="auth-test@pilot.local")
        token = _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        client.headers.update({"Authorization": token})

        resp = client.get("/api/v1/operator/cohort")
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# /auth/me endpoint tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthMe:
    """Tests for GET /api/v1/auth/me — login routing discriminator."""

    def test_auth_me_tenant_user(self, client, db_session, mock_cognito_jwt, test_user):
        """Tenant user → user_type='tenant', redirect_to='/dashboard'."""
        mock_cognito_jwt(test_user)

        resp = client.get("/api/v1/operator/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_type"] == "tenant"
        assert data["redirect_to"] == "/dashboard"
        assert data["tenant_id"] is not None
        assert data["role_code"] is not None

    def test_auth_me_platform_user(self, client, db_session, mock_cognito_jwt_verify):
        """Platform user → user_type='platform', redirect_to='/operator/cohort'."""
        platform_user = _create_platform_user(
            db_session, email="me-platform@pilot.local"
        )
        token = _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        client.headers.update({"Authorization": token})

        resp = client.get("/api/v1/operator/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_type"] == "platform"
        assert data["redirect_to"] == "/operator/cohort"
        assert data["platform_role_code"] == "owner"
        assert data["tenant_id"] is None
