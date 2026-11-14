"""
C-B14 §11.3 — Entitlement Scenarios (5 tests)
==============================================
Domain: subscriptions_usage (PRD §3.11)

Covers the 5 entitlement enforcement scenarios from spec §11.3.
Scenarios 3-5 use @pytest.mark.skip_mock_entitlement_allowed to test real
entitlement enforcement (bypassing the autouse mock_entitlement_allowed fixture).

Scenarios:
  1. test_charter_data_export_succeeds — Charter (active) data export → succeeds (D11)
  2. test_charter_teams_only_feature_blocked — Charter attempts Teams-only feature → blocked
  3. test_paused_sms_blocked — Paused tenant sends SMS → Blocked (402) [C-B7 override]
  4. test_paused_job_creation_blocked — Paused tenant creates job → billing-active=False
  5. test_paused_data_export_succeeds — Paused tenant exports data → succeeds

Key correction (Tom, 2026-08-05, C-B7 override): spec §9.3 SMS exception
OVERRIDDEN — when paused → ALL services including SMS blocked, no exceptions.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_status_id(db_session, code: str) -> uuid.UUID:
    """Look up a platform SubscriptionStatus row by code (tenant_id IS NULL)."""
    from app.models.billing import SubscriptionStatus

    row = db_session.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == code)
    ).first()
    assert row is not None, f"SubscriptionStatus code='{code}' not seeded"
    return row.id


def _create_subscription(
    db_session, tenant_id, status_code="active", product_plan_code="charter_plan"
):
    """Insert a subscription row scoped to this test (rolled back after test)."""
    from app.models.billing import Subscription

    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_plan_code=product_plan_code,
        status_id=_get_status_id(db_session, status_code),
        quantity_seats=1,
        billing_interval="monthly",
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


def _create_test_user_for_tenant(db_session, tenant_id):
    """Create a real User row so FK constraints on created_by are satisfied."""
    from app.models.core import User

    user = User(
        id=uuid.uuid4(),
        email=f"cb14-ent-{uuid.uuid4()}@test.pilotfortrades.com",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_sms_customer(db_session, tenant_id):
    """Create a customer with mobile_phone + sms preference for SMS tests."""
    from app.models.crm import Customer

    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        display_name=f"C-B14 Ent Customer {uuid.uuid4()}",
        first_name="Cee",
        last_name="Bee",
        mobile_phone="+15125557777",
        email=f"cb14-ent-{uuid.uuid4()}@example.com",
        preferred_contact_channel="sms",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


# ---------------------------------------------------------------------------
# Scenario 1 — Charter data export succeeds
# ---------------------------------------------------------------------------


class TestEntitlementScenarios:
    """C-B14 §11.3 — Entitlement enforcement scenarios."""

    def test_charter_data_export_succeeds(self, db_session, second_tenant):
        """Scenario 1: Charter tenant (active) requests data export → succeeds.

        D11 — data export is available on all plans, including Charter.
        The data export endpoint uses require_permission("account.data_export.request")
        with no feature_code, so the entitlement check is RBAC-only.
        """
        from api.routes.account_security import _create_data_export_impl
        from core.test_context import TestUserContext

        # Create active Charter subscription
        _create_subscription(db_session, second_tenant.id, status_code="active")
        user = _create_test_user_for_tenant(db_session, second_tenant.id)

        ctx = TestUserContext(
            tenant_id=second_tenant.id,
            id=user.id,
        )

        response = _create_data_export_impl(ctx, db_session)

        assert response.status == "pending"
        assert response.export_id is not None
        assert response.requested_at is not None

    # -------------------------------------------------------------------
    # Scenario 2 — Charter Teams-only feature blocked
    # -------------------------------------------------------------------

    def test_charter_teams_only_feature_blocked(self, db_session, second_tenant):
        """Scenario 2: Charter tenant attempts Teams-only feature → blocked.

        Calls check_entitlement() directly (not through get_cached_entitlement,
        so the autouse mock does not affect it). Inserts a teams-only feature
        (product_plan_product_feature_version for teams_plan only, not
        charter_plan). The Charter tenant's check_entitlement() should return
        is_allowed=False with reason="feature_not_in_plan".
        """
        from sqlalchemy import text

        from services.entitlement_service import check_entitlement

        # Create active Charter subscription
        _create_subscription(db_session, second_tenant.id, status_code="active")

        # Insert a teams-only feature (not on charter_plan)
        feature_code = f"teams_only_{uuid.uuid4().hex[:8]}"
        db_session.execute(
            text("""
                INSERT INTO product_feature (code, name, unit, is_active,
                    created_at, updated_at)
                VALUES (:code, 'Teams Only Feature', 'count', TRUE, NOW(), NOW())
                ON CONFLICT (code) DO NOTHING
            """),
            {"code": feature_code},
        )
        db_session.execute(
            text("""
                INSERT INTO product_plan_product_feature_version
                    (product_plan_code, product_feature_code, limit_quantity,
                     included_quantity, valid_period, limit_enforcement,
                     created_at)
                VALUES
                    ('teams_plan', :code, 10, 10,
                     tstzrange('-infinity', 'infinity', '[]'), 'block', NOW())
            """),
            {"code": feature_code},
        )
        db_session.flush()

        result = check_entitlement(
            tenant_id=second_tenant.id,
            feature_code=feature_code,
            db=db_session,
        )

        assert result.is_allowed is False
        assert result.reason == "feature_not_in_plan"

    # -------------------------------------------------------------------
    # Scenario 3 — Paused SMS blocked (C-B7 override)
    # -------------------------------------------------------------------

    @pytest.mark.skip_mock_entitlement_allowed
    def test_paused_sms_blocked(self, db_session, second_tenant):
        """Scenario 3: Paused tenant sends SMS → Blocked (402 RFC 7807).

        ⚠️ Corrected per Tom decision 2026-08-05 (C-B7 override):
        spec §9.3 SMS exception OVERRIDDEN — when paused → ALL services
        including SMS blocked, no exceptions.

        _send_communication_impl calls is_subscription_billing_active()
        directly (not through get_cached_entitlement), so the autouse mock
        does not affect this check. skip_mock_entitlement_allowed is applied
        per design doc for consistency with the real-enforcement test group.
        """
        from fastapi import HTTPException

        from api.routes.communications import (
            CommunicationSendRequest,
            _send_communication_impl,
        )
        from core.test_context import TestUserContext

        # Create paused subscription
        _create_subscription(db_session, second_tenant.id, status_code="paused")
        customer = _create_sms_customer(db_session, second_tenant.id)
        user = _create_test_user_for_tenant(db_session, second_tenant.id)

        ctx = TestUserContext(
            tenant_id=second_tenant.id,
            id=user.id,
        )
        req = CommunicationSendRequest(
            customer_id=customer.id,
            template_code="arrived",
            variables={},
        )

        with pytest.raises(HTTPException) as exc_info:
            _send_communication_impl(req, db_session, ctx)

        assert exc_info.value.status_code == 402
        detail = exc_info.value.detail
        assert detail["status"] == 402
        assert "subscription-paused" in detail["type"]

    # -------------------------------------------------------------------
    # Scenario 4 — Paused job creation blocked
    # -------------------------------------------------------------------

    @pytest.mark.skip_mock_entitlement_allowed
    def test_paused_job_creation_blocked(self, db_session, second_tenant):
        """Scenario 4: Paused tenant creates a job → billing-active=False.

        The billing-active gate (is_subscription_billing_active) returns False
        for paused tenants. This is the mechanism that blocks job creation
        when the subscription is paused. The job creation endpoint uses
        require_permission("jobs.create") with no feature_code, so the
        entitlement check is RBAC-only. The billing-active check is enforced
        at the service layer via is_subscription_billing_active().

        This test verifies the billing-active gate returns False for a paused
        tenant, which is the gate that blocks job creation.
        """
        from services.entitlement_service import is_subscription_billing_active

        # Create paused subscription
        _create_subscription(db_session, second_tenant.id, status_code="paused")

        result = is_subscription_billing_active(db_session, second_tenant.id)
        assert result is False

    # -------------------------------------------------------------------
    # Scenario 5 — Paused data export succeeds
    # -------------------------------------------------------------------

    @pytest.mark.skip_mock_entitlement_allowed
    def test_paused_data_export_succeeds(self, db_session, second_tenant):
        """Scenario 5: Paused tenant exports data → succeeds.

        Data export is allowed even when the subscription is paused. The data
        export endpoint uses require_permission("account.data_export.request")
        with no feature_code, so the entitlement check is RBAC-only. There is
        no billing-active check in the data export flow.

        This test verifies that _create_data_export_impl succeeds even when
        the subscription is paused.
        """
        from api.routes.account_security import _create_data_export_impl
        from core.test_context import TestUserContext

        # Create paused subscription
        _create_subscription(db_session, second_tenant.id, status_code="paused")
        user = _create_test_user_for_tenant(db_session, second_tenant.id)

        ctx = TestUserContext(
            tenant_id=second_tenant.id,
            id=user.id,
        )

        response = _create_data_export_impl(ctx, db_session)

        assert response.status == "pending"
        assert response.export_id is not None
        assert response.requested_at is not None
