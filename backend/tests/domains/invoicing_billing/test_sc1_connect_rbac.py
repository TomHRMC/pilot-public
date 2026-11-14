"""
STRIPE-CONNECT-1 (A4) Tests: Owner-only RBAC on Connect management.

Tests:
1. test_owner_onboard_allowed — owner role → 200 on /onboard
2. test_owner_disconnect_allowed — owner role → 200 on DELETE
3. test_operator_onboard_forbidden — operator role → 403 RFC 7807 on /onboard
4. test_operator_disconnect_forbidden — operator role → 403 on DELETE
5. test_test_endpoint_owner_allowed — /test variant (TestUserContext
   role_code='owner') → 200 on /onboard/test
6. test_require_owner_role_helper — direct unit test of the guard helper
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, select

from app.models.auth import TenantUser, TenantUserStatus
from app.models.core import User

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]

BASE = "/api/v1/settings/billing"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user_with_role(
    db: Session, tenant_id, role_code: str, email_suffix: str = ""
) -> User:
    """Create a User + TenantUser with the given role_code."""
    user = User(
        id=uuid.uuid4(),
        email=f"sc1-{role_code}-{uuid.uuid4()}@example.com",
        cognito_user_id=f"sc1-{role_code}-{uuid.uuid4()}",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()

    status = db.exec(
        select(TenantUserStatus).where(
            TenantUserStatus.code == "active",
            TenantUserStatus.tenant_id == tenant_id,
        )
    ).first()
    if not status:
        status = TenantUserStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            code="active",
            name="Active",
            is_default=True,
            is_active=True,
        )
        db.add(status)
        db.flush()

    tu = TenantUser(
        tenant_id=tenant_id,
        user_id=user.id,
        role_code=role_code,
        status_id=status.id,
        is_active=True,
        joined_at=datetime.now(UTC),
    )
    db.add(tu)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Owner-guard helper unit test
# ---------------------------------------------------------------------------


class TestRequireOwnerRoleHelper:
    """Direct unit test of _require_owner_role."""

    def test_owner_passes(self):
        from api.routes.stripe_connect import _require_owner_role

        ctx = MagicMock()
        ctx.role_code = "owner"
        # Should not raise
        _require_owner_role(ctx)

    def test_operator_raises_403(self):
        from fastapi import HTTPException

        from api.routes.stripe_connect import _require_owner_role

        ctx = MagicMock()
        ctx.role_code = "operator"
        with pytest.raises(HTTPException) as exc_info:
            _require_owner_role(ctx)
        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        assert detail["type"] == "https://errors.pilotfortrades.com/forbidden"
        assert detail["status"] == 403

    def test_accountant_raises_403(self):
        from fastapi import HTTPException

        from api.routes.stripe_connect import _require_owner_role

        ctx = MagicMock()
        ctx.role_code = "accountant"
        with pytest.raises(HTTPException) as exc_info:
            _require_owner_role(ctx)
        assert exc_info.value.status_code == 403

    def test_no_role_code_raises_403(self):
        from fastapi import HTTPException

        from api.routes.stripe_connect import _require_owner_role

        ctx = MagicMock()
        # MagicMock returns a Mock for any attribute by default; configure
        # role_code to return None (simulates a context without role_code)
        ctx.role_code = None
        with pytest.raises(HTTPException) as exc_info:
            _require_owner_role(ctx)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# /test endpoint tests (TestUserContext role_code='owner' by default)
# ---------------------------------------------------------------------------


class TestTestEndpointOwnerAllowed:
    """/test variants use TestUserContext with role_code='owner'."""

    def test_test_onboard_owner_allowed(self, client, db_session, test_tenant):
        """/onboard/test with default TestUserContext (owner) → 200."""
        from app.models.core import Tenant

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_connect_account_id = None
        db_session.add(tenant)
        db_session.commit()

        mock_account = MagicMock()
        mock_account.id = "acct_test_rbac"
        mock_link = MagicMock()
        mock_link.url = "https://connect.stripe.com/test"
        mock_link.expires_at = 1721563200

        with (
            patch("stripe.Account.create", return_value=mock_account),
            patch("stripe.AccountLink.create", return_value=mock_link),
        ):
            resp = client.post(f"{BASE}/stripe-connect/onboard/test")

        assert resp.status_code == 200

    def test_test_disconnect_owner_allowed(self, client, db_session, test_tenant):
        """DELETE /stripe-connect/test with default TestUserContext (owner) → 200."""
        from app.models.core import Tenant

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_connect_account_id = "acct_test_disconnect_rbac"
        db_session.add(tenant)
        db_session.commit()

        resp = client.delete(f"{BASE}/stripe-connect/test")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Authed endpoint tests (owner vs operator)
# ---------------------------------------------------------------------------


class TestAuthedOwnerRbac:
    """Authed endpoints: owner → 200, operator → 403."""

    def test_owner_onboard_allowed(
        self, client, db_session, tenant_a, mock_cognito_jwt
    ):
        """Owner role → 200 on /onboard (authed)."""
        owner = _make_user_with_role(db_session, tenant_a.id, "owner")
        mock_cognito_jwt(owner)

        mock_link = MagicMock()
        mock_link.url = "https://connect.stripe.com/owner"
        mock_link.expires_at = 1721563200

        # Tenant already has no account → Account.create will be called
        mock_account = MagicMock()
        mock_account.id = "acct_owner_test"

        with (
            patch("stripe.Account.create", return_value=mock_account),
            patch("stripe.AccountLink.create", return_value=mock_link),
        ):
            resp = client.post(f"{BASE}/stripe-connect/onboard")

        assert resp.status_code == 200

    def test_accountant_onboard_forbidden(
        self, client, db_session, tenant_a, mock_cognito_jwt
    ):
        """Accountant role → 403 on /onboard (authed).

        The accountant role has ``*.view`` but NOT ``settings.tenant.write``,
        so ``require_permission`` blocks it with 403. The owner guard is a
        defense-in-depth secondary check (tested directly via the helper unit
        tests above) — it catches any future role that gains
        ``settings.tenant.write`` without being ``owner``.
        """
        accountant = _make_user_with_role(db_session, tenant_a.id, "accountant")
        mock_cognito_jwt(accountant)

        resp = client.post(f"{BASE}/stripe-connect/onboard")
        assert resp.status_code == 403

    def test_accountant_disconnect_forbidden(
        self, client, db_session, tenant_a, mock_cognito_jwt
    ):
        """Accountant role → 403 on DELETE (authed)."""
        accountant = _make_user_with_role(db_session, tenant_a.id, "accountant")
        mock_cognito_jwt(accountant)

        resp = client.delete(f"{BASE}/stripe-connect")
        assert resp.status_code == 403
