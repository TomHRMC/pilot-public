"""
SIGNUP-C — Signup Step 3 "Stay Informed" Tests (identity_access domain)
======================================================================
Tests for the rewritten step 3 (phone required, phone_skipped removed):
  - Missing phone_number → 422 (RFC 7807 Problem Details).
  - sms_consent=True enqueues the platform double-opt-in task (.delay called).
  - /step3/test works with the new shape.
  - /phone/consent/test + /phone/send-optin/test endpoints.

Domain: identity_access (PRD §3.5)
"""

import hashlib
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlmodel import select

from app.models.core import Tenant, User
from app.models.signup import TenantSignup

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


@pytest.fixture
def signup_tenant_step3(db_session):
    """Create a tenant + signup record advanced to step3_phone + an owner user."""
    from app.models.auth import TenantUser
    from app.models.subscription import SubscriptionTier

    trial_tier = db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
    ).first()

    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"SignupC Test Tenant {uuid.uuid4().hex[:8]}",
        is_active=True,
        current_subscription_tier_id=trial_tier.tier_id if trial_tier else None,
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
        # ALPHA-FIX-1: set to step2_legal so destination is step3_phone (which
        # processes phone data). Under the old origin-keyed dispatch this
        # fixture set step3_phone and tests passed "step3_phone" — which under
        # the new contract would dispatch to step4_tier (wrong branch).
        signup_state="step2_legal",
        signup_started_at=datetime.now(UTC),
        business_name="SignupC Electric",
        trade="electrical",
        business_size="solo",
        zip="10001",
        time_zone="America/New_York",
    )
    db_session.add(signup)
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(owner)
    db_session.refresh(signup)
    return tenant, owner, signup


class TestStep3PhoneRequired:
    def test_missing_phone_returns_422(self, db_session, signup_tenant_step3):
        """SIGNUP-C: step3 with no phone_number → 422 RFC 7807."""
        from fastapi import HTTPException

        from services.tenant_signup import advance_wizard_step

        tenant, owner, _signup = signup_tenant_step3

        with pytest.raises(HTTPException) as exc_info:
            advance_wizard_step(
                db_session,
                tenant.id,
                "step2_legal",
                {"user_id": owner.id},
            )
        assert exc_info.value.status_code == 422
        # RFC 7807 Problem Details dict shape
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail["status"] == 422
        assert "phone_number" in detail["detail"]

    def test_consent_true_enqueues_platform_task(self, db_session, signup_tenant_step3):
        """SIGNUP-C: sms_consent=True → send_platform_double_optin_sms.delay called."""
        from services.tenant_signup import advance_wizard_step

        tenant, owner, _signup = signup_tenant_step3

        with patch(
            "tasks.sms_compliance_platform.send_platform_double_optin_sms"
        ) as mock_task:
            result = advance_wizard_step(
                db_session,
                tenant.id,
                "step2_legal",
                {
                    "phone_number": "+15125550999",
                    "sms_consent": True,
                    "disclosure_hash": hashlib.sha256(b"disclosure").hexdigest(),
                    "user_id": owner.id,
                },
            )

        assert result["signup_state"] == "step3_phone"
        mock_task.delay.assert_called_once_with(str(owner.id), str(tenant.id))

    def test_consent_false_does_not_enqueue(self, db_session, signup_tenant_step3):
        """SIGNUP-C: sms_consent=False → no task enqueued; phone still stored."""
        from services.tenant_signup import advance_wizard_step

        tenant, owner, _signup = signup_tenant_step3

        with patch(
            "tasks.sms_compliance_platform.send_platform_double_optin_sms"
        ) as mock_task:
            result = advance_wizard_step(
                db_session,
                tenant.id,
                "step2_legal",
                {
                    "phone_number": "+15125550998",
                    "sms_consent": False,
                    "disclosure_hash": hashlib.sha256(b"d").hexdigest(),
                    "user_id": owner.id,
                },
            )

        assert result["signup_state"] == "step3_phone"
        mock_task.delay.assert_not_called()

        # Phone still mirrored on user
        db_session.refresh(owner)
        assert owner.phone_number == "+15125550998"


class TestStep3DirectService:
    def test_step3_advances_with_phone_and_no_consent(
        self, db_session, signup_tenant_step3
    ):
        """Direct service call: step3 with phone_number (no consent) → step3_phone.

        Mirrors what the /step3/test endpoint does internally. The test endpoint
        path resolves the owner via TenantUser lookup; this test supplies
        user_id directly (as the authenticated route does).
        """
        from services.tenant_signup import advance_wizard_step

        tenant, owner, _signup = signup_tenant_step3

        with patch(
            "tasks.sms_compliance_platform.send_platform_double_optin_sms"
        ) as mock_task:
            result = advance_wizard_step(
                db_session,
                tenant.id,
                "step2_legal",
                {
                    "phone_number": "+15125550777",
                    "sms_consent": False,
                    "disclosure_hash": hashlib.sha256(b"d").hexdigest(),
                    "user_id": owner.id,
                },
            )
        assert result["signup_state"] == "step3_phone"
        mock_task.delay.assert_not_called()


class TestPhoneConsentTestEndpoint:
    def test_phone_consent_test_creates_endpoint(self, client, test_tenant, test_user):
        """POST /signup/{tenant_id}/phone/consent/test creates the sms endpoint."""
        disclosure = hashlib.sha256(b"disclosure text").hexdigest()
        resp = client.post(
            f"/api/v1/signup/{test_tenant.id}/phone/consent/test",
            json={
                "phone_number": "+15125550888",
                "sms_consent": True,
                "disclosure_hash": disclosure,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "user_endpoint_id" in data
        assert data["verification_status"] == "pending"


class TestSendOptinTestEndpoint:
    def test_send_optin_test_enqueues_task(self, client, test_tenant, test_user):
        """POST /signup/{tenant_id}/phone/send-optin/test enqueues the platform task."""
        # First create the endpoint via consent
        disclosure = hashlib.sha256(b"disclosure text").hexdigest()
        consent_resp = client.post(
            f"/api/v1/signup/{test_tenant.id}/phone/consent/test",
            json={
                "phone_number": "+15125550889",
                "sms_consent": True,
                "disclosure_hash": disclosure,
            },
        )
        assert consent_resp.status_code == 201
        endpoint_id = consent_resp.json()["user_endpoint_id"]

        # Now request the opt-in send
        with patch(
            "tasks.sms_compliance_platform.send_platform_double_optin_sms"
        ) as mock_task:
            resp = client.post(
                f"/api/v1/signup/{test_tenant.id}/phone/send-optin/test",
                json={"user_endpoint_id": endpoint_id},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"
        mock_task.delay.assert_called_once()
