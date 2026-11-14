"""
SIGNUP-GA-B1 (Part A) — get_signup_state() returns owner names in collected_data.
Domain: identity_access (PRD §3.5)

Covers:
  - Owner names returned in collected_data when set on the signup row
  - Null-safe: owner names None returns None (not KeyError, not "")
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.core import Tenant
from app.models.signup import TenantSignup
from services.tenant_signup import get_signup_state

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


def _make_tenant_and_signup(
    db_session,
    *,
    owner_first_name: str | None,
    owner_last_name: str | None,
) -> tuple[Tenant, TenantSignup]:
    """Insert a tenant + tenant_signup row with the given owner names."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"Owner Names Test Tenant {uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(tenant)
    db_session.flush()

    signup = TenantSignup(
        tenant_id=tenant.id,
        signup_state="step1_account",
        signup_started_at=datetime.now(UTC),
        business_name="Acme Electric",
        trade="electrical",
        business_size="1-5",
        zip="12345",
        time_zone="America/New_York",
        owner_email=f"owner-{uuid.uuid4()}@example.com",
        owner_first_name=owner_first_name,
        owner_last_name=owner_last_name,
    )
    db_session.add(signup)
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(signup)
    return tenant, signup


class TestGetSignupStateOwnerNames:
    """get_signup_state() must surface owner_first_name / owner_last_name."""

    def test_owner_names_returned_when_set(self, db_session):
        tenant, _signup = _make_tenant_and_signup(
            db_session,
            owner_first_name="Mike",
            owner_last_name="Johnson",
        )

        result = get_signup_state(db_session, tenant.id)

        assert result["tenant_id"] == str(tenant.id)
        assert result["collected_data"]["owner_first_name"] == "Mike"
        assert result["collected_data"]["owner_last_name"] == "Johnson"
        # Existing fields still present
        assert result["collected_data"]["business_name"] == "Acme Electric"

    def test_owner_names_null_safe(self, db_session):
        tenant, _signup = _make_tenant_and_signup(
            db_session,
            owner_first_name=None,
            owner_last_name=None,
        )

        result = get_signup_state(db_session, tenant.id)

        # None, not "" and not a KeyError
        assert "owner_first_name" in result["collected_data"]
        assert "owner_last_name" in result["collected_data"]
        assert result["collected_data"]["owner_first_name"] is None
        assert result["collected_data"]["owner_last_name"] is None
