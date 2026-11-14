"""
SIGNUP-C-FU3 — sms_consent_status in /state Regression Test
==========================================================
Regression test for the /state ↔ phone-page contract bug (PLATFORM-SMS-B1 v1.1).

The web phone page polls ``collected_data.sms_consent_status === "opted_in"``
to know when to advance past "Check your phone". The backend must derive this
from ``user_endpoint.verification_status == "verified"`` (the YES-reply terminal
state), NOT from ``consent_status`` (which flips at checkbox attestation).

This test exercises the REAL route handler via the ``client`` fixture (no mock)
to prevent the MSW-mock divergence that hid this bug.

States tested:
  1. No sms endpoint → ``sms_consent_status == null``
  2. Endpoint pending → ``sms_consent_status == "pending"``
  3. Endpoint verified → ``sms_consent_status == "opted_in"``

Domain: identity_access (PRD §3.5)
"""

import hashlib
import uuid

import pytest

from app.models.auth import TenantUser
from app.models.core import User
from app.models.signup import TenantSignup
from services.notification_endpoints import upsert_owner_sms_endpoint

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]

# tenant_user_status.code='active' id (MCP-verified, seeded platform row).
_ACTIVE_STATUS_ID = "5b67cfd3-ef42-4311-9516-a4eec8642628"


def _create_signup_with_owner(db_session, tenant_id):
    """Create a TenantSignup + owner user + TenantUser for the given tenant."""
    user = User(
        id=uuid.uuid4(),
        email=f"fu3-owner-{uuid.uuid4().hex[:8]}@test.local",
        first_name="FU3",
        last_name="Owner",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    db_session.add(
        TenantUser(
            tenant_id=tenant_id,
            user_id=user.id,
            role_code="owner",
            status_id=_ACTIVE_STATUS_ID,
            is_active=True,
        )
    )
    db_session.flush()

    signup = TenantSignup(
        tenant_id=tenant_id,
        signup_state="step3_phone",
        signup_started_at="2026-01-01T00:00:00Z",
        business_name="FU3 Test Business",
        trade="electrical",
        business_size="solo",
        zip="12345",
        time_zone="America/New_York",
        owner_email=user.email,
        owner_first_name="FU3",
        owner_last_name="Owner",
    )
    db_session.add(signup)
    db_session.commit()
    return user, signup


class TestSignupStateSmsConsentStatus:
    """Regression: /state collected_data.sms_consent_status across 3 endpoint states."""

    def test_no_endpoint_returns_null(self, client, db_session, second_tenant):
        """When no sms endpoint exists, sms_consent_status is null."""
        _user, _signup = _create_signup_with_owner(db_session, second_tenant.id)

        resp = client.get(f"/api/v1/signup/{second_tenant.id}/state/test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["collected_data"]["sms_consent_status"] is None

    def test_pending_endpoint_returns_pending(self, client, db_session, second_tenant):
        """When an sms endpoint exists but is unverified, sms_consent_status is 'pending'."""
        user, _signup = _create_signup_with_owner(db_session, second_tenant.id)

        upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=second_tenant.id,
            phone="+15125550701",
            consent=True,
            ip="127.0.0.1",
            disclosure_hash=hashlib.sha256(b"d").hexdigest(),
        )
        db_session.commit()

        resp = client.get(f"/api/v1/signup/{second_tenant.id}/state/test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["collected_data"]["sms_consent_status"] == "pending"

    def test_verified_endpoint_returns_opted_in(
        self, client, db_session, second_tenant
    ):
        """When the sms endpoint is verified, sms_consent_status is 'opted_in'."""
        user, _signup = _create_signup_with_owner(db_session, second_tenant.id)

        endpoint = upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=second_tenant.id,
            phone="+15125550702",
            consent=True,
            ip="127.0.0.1",
            disclosure_hash=hashlib.sha256(b"d").hexdigest(),
        )
        # Simulate the YES reply: set verification_status='verified'.
        endpoint.verification_status = "verified"
        db_session.add(endpoint)
        db_session.commit()

        resp = client.get(f"/api/v1/signup/{second_tenant.id}/state/test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["collected_data"]["sms_consent_status"] == "opted_in"
