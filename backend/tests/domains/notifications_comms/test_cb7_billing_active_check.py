"""
C-B7: Paused-State Service Block — billing-active gate for SMS.
Domain: notifications_comms

Covers:
  1. is_subscription_billing_active() returns True when status is 'active'
  2. is_subscription_billing_active() returns False when status is 'paused'
  3. is_subscription_billing_active() returns False when no active subscription exists
  4. SMS send via API is blocked (402) when subscription is paused
  5. SMS send via API is allowed (201) when subscription is active

Design decision (Tom, 2026-08-05): spec §9.3 SMS exception is OVERRIDDEN.
When a subscription is paused → ALL services including SMS are blocked.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_status_id(db_session, code: str) -> uuid.UUID:
    """Look up a platform SubscriptionStatus row by code (tenant_id IS NULL)."""
    from app.models.billing import SubscriptionStatus

    row = db_session.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == code)
    ).first()
    assert row is not None, f"SubscriptionStatus code='{code}' not seeded"
    return row.id


def _create_subscription(db_session, tenant_id, status_code="active"):
    """Insert a subscription row scoped to this test (rolled back after test)."""
    from app.models.billing import Subscription

    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_plan_code="starter_plan",
        status_id=_get_status_id(db_session, status_code),
        quantity_seats=1,
        billing_interval="monthly",
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


def _create_sms_customer(db_session, tenant_id):
    """Create a customer with mobile_phone + sms preference for SMS tests."""
    from app.models.crm import Customer

    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        display_name=f"C-B7 Customer {uuid.uuid4()}",
        first_name="Cee",
        last_name="Bee",
        mobile_phone="+15125557777",
        email=f"cb7-{uuid.uuid4()}@example.com",
        preferred_contact_channel="sms",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def _create_test_user_for_tenant(db_session, tenant_id):
    """Create a real User row so FK constraints on created_by are satisfied."""
    from app.models.core import User

    user = User(
        id=uuid.uuid4(),
        email=f"cb7-user-{uuid.uuid4()}@test.pilotfortrades.com",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── Unit tests for is_subscription_billing_active() ──────────────────────────


class TestIsSubscriptionBillingActive:
    """Direct unit tests for entitlement_service.is_subscription_billing_active()."""

    def test_returns_true_when_status_active(self, db_session, second_tenant):
        """Returns True when subscription status is 'active' (is_billing_active=true)."""
        from services.entitlement_service import is_subscription_billing_active

        _create_subscription(db_session, second_tenant.id, status_code="active")

        result = is_subscription_billing_active(db_session, second_tenant.id)
        assert result is True

    def test_returns_false_when_status_paused(self, db_session, second_tenant):
        """Returns False when subscription status is 'paused' (is_billing_active=false)."""
        from services.entitlement_service import is_subscription_billing_active

        _create_subscription(db_session, second_tenant.id, status_code="paused")

        result = is_subscription_billing_active(db_session, second_tenant.id)
        assert result is False

    def test_returns_false_when_no_active_subscription(self, db_session, second_tenant):
        """Returns False when no active subscription exists for the tenant."""
        from services.entitlement_service import is_subscription_billing_active

        # second_tenant has no subscription at all
        result = is_subscription_billing_active(db_session, second_tenant.id)
        assert result is False


# ── Integration tests for the SMS send gate ──────────────────────────────────


class TestSmsSendBillingActiveGate:
    """
    Integration tests: POST /api/v1/communications/send/test blocks SMS when
    the subscription is not billing-active.

    Uses second_tenant to avoid the seeded test_tenant subscription state.
    The /test endpoint uses get_test_context() which resolves to the canonical
    test tenant (0001), so we cannot redirect it to second_tenant. Instead we
    test the gate via the _send_communication_impl directly with a
    TestUserContext built for second_tenant.
    """

    def test_sms_blocked_when_subscription_paused(self, db_session, second_tenant):
        """SMS send is blocked (402) when subscription is paused."""
        from fastapi import HTTPException

        from api.routes.communications import (
            CommunicationSendRequest,
            _send_communication_impl,
        )
        from core.test_context import TestUserContext

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

    def test_sms_allowed_when_subscription_active(self, db_session, second_tenant):
        """SMS send is allowed (returns response) when subscription is active."""
        from api.routes.communications import (
            CommunicationSendRequest,
            _send_communication_impl,
        )
        from core.test_context import TestUserContext

        _create_subscription(db_session, second_tenant.id, status_code="active")
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

        response = _send_communication_impl(req, db_session, ctx)
        assert response.actual_channel == "sms"
        assert response.status == "pending"
