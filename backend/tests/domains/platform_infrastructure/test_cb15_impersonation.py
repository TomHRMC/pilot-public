"""Tests for C-B15 — Tenant Impersonation Backend.

Domain: platform_infrastructure (PRD §3.8)

Covers:
    - AuthenticatedUser.impersonator_user_id + is_impersonated
    - _try_impersonation() security invariants (6 invariants from design §D.4)
    - get_current_user() impersonation branch (header ignored for tenant users,
      403 for accountant, 404/409/400 for invalid target)
    - 3 operator endpoints (GET /tenants, POST /impersonation/start, /end)
    - Impersonated-mutation audit middleware (action='request' row)
"""

import uuid
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


def _get_trial_tier_id(db_session):
    """Return the trial subscription tier ID for Tenant creation."""
    from app.models.subscription import SubscriptionTier

    tier = db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
    ).first()
    if tier is None:
        raise RuntimeError("Trial subscription tier not seeded")
    return tier.tier_id


def _create_platform_user(
    db_session,
    email="cb15-platform@pilot.local",
    role_code="owner",
    impersonate_tenant=True,
):
    """Create a platform user + ensure the platform role has impersonate_tenant.

    Uses the existing seeded platform role if available; otherwise creates one
    with the specified impersonate_tenant flag.
    """
    from app.models.core import PlatformRole, User

    role = db_session.exec(
        select(PlatformRole).where(PlatformRole.code == role_code)
    ).first()
    if not role:
        role = PlatformRole(
            code=role_code,
            name=f"Test {role_code}",
            permissions={
                "write": ["tenants", "users", "billing"],
                "read_all": True,
                "impersonate_tenant": impersonate_tenant,
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


def _create_tenant(db_session, name="CB15 Target", is_active=True):
    """Create a tenant for impersonation target testing."""
    from app.models.core import Tenant

    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"{name} {uuid.uuid4().hex[:8]}",
        is_active=is_active,
        current_subscription_tier_id=_get_trial_tier_id(db_session),
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


def _create_tenant_user(db_session, tenant, email=None, role_code="owner"):
    """Create a tenant user (non-platform) for testing header-ignoring."""
    from app.models.auth import TenantUser, TenantUserStatus
    from app.models.core import User

    status = TenantUserStatus(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        code="active",
        name="Active",
        is_default=True,
        is_active=True,
    )
    db_session.add(status)
    db_session.flush()

    user = User(
        id=uuid.uuid4(),
        email=email or f"tenant-user-{uuid.uuid4()}@example.com",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    tenant_user = TenantUser(
        tenant_id=tenant.id,
        user_id=user.id,
        role_code=role_code,
        status_id=status.id,
        is_active=True,
    )
    db_session.add(tenant_user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Tenant user + X-Impersonate-Tenant header → header ignored
# ─────────────────────────────────────────────────────────────────────────────


class TestImpersonationHeaderIgnoredForTenantUsers:
    """Security invariant 1: header is silently ignored for tenant users."""

    def test_tenant_user_header_ignored(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """Tenant user sending X-Impersonate-Tenant gets their own tenant context."""

        # Create a tenant + tenant user
        own_tenant = _create_tenant(db_session, name="Own Tenant")
        target_tenant = _create_tenant(db_session, name="Target Tenant")
        tenant_user_obj = _create_tenant_user(
            db_session, own_tenant, email="cb15-tenant@pilot.local"
        )

        # Mock JWT for the tenant user
        mock_cognito_jwt_verify.return_value = {
            "sub": str(tenant_user_obj.id),
            "email": tenant_user_obj.email,
        }
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {
            "Authorization": token,
            "X-Impersonate-Tenant": str(target_tenant.id),
        }

        # ACT: call /users/me/permissions with the impersonation header
        resp = client.get("/api/v1/users/me/permissions", headers=headers)

        # ASSERT: 200, returns the user's OWN tenant, not the target
        assert resp.status_code == 200
        data = resp.json()
        # The tenant_id should be the user's own tenant, not the target
        assert data["tenant_id"] == str(own_tenant.id)
        assert data["tenant_id"] != str(target_tenant.id)


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Platform user + valid header → target tenant context
# ─────────────────────────────────────────────────────────────────────────────


class TestImpersonationValid:
    """Security invariant 5: impersonated context is role_code='owner'."""

    def test_platform_user_impersonates_target(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """Platform user with owner role + valid header → target tenant + owner."""
        platform_user = _create_platform_user(
            db_session, email="cb15-imp@pilot.local", role_code="owner"
        )
        target_tenant = _create_tenant(db_session, name="Impersonation Target")

        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {
            "Authorization": token,
            "X-Impersonate-Tenant": str(target_tenant.id),
        }

        resp = client.get("/api/v1/users/me/permissions", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == str(target_tenant.id)
        assert data["role_code"] == "owner"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Platform user, no header → existing 403 preserved
# ─────────────────────────────────────────────────────────────────────────────


class TestNoHeaderPreserves403:
    """Security invariant 2: platform user without header → existing 403."""

    def test_platform_user_no_header_403(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """Platform user without X-Impersonate-Tenant → 403 from get_current_user."""
        platform_user = _create_platform_user(
            db_session, email="cb15-no-header@pilot.local", role_code="owner"
        )

        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {"Authorization": token}

        resp = client.get("/api/v1/users/me/permissions", headers=headers)

        # 403 — platform user has no tenant_user row and no impersonation header
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Accountant role + header → 403
# ─────────────────────────────────────────────────────────────────────────────


class TestAccountantCannotImpersonate:
    """Security invariant 3: accountant (impersonate_tenant=false) → 403."""

    def test_accountant_with_header_403(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """Platform user with accountant role + header → 403 RFC 7807."""
        platform_user = _create_platform_user(
            db_session,
            email="cb15-accountant@pilot.local",
            role_code="accountant",
            impersonate_tenant=False,
        )
        target_tenant = _create_tenant(db_session, name="Accountant Target")

        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {
            "Authorization": token,
            "X-Impersonate-Tenant": str(target_tenant.id),
        }

        resp = client.get("/api/v1/users/me/permissions", headers=headers)

        assert resp.status_code == 403
        detail = resp.json()["detail"]
        assert detail["type"] == "https://errors.pilotfortrades.com/forbidden"
        assert "impersonate_tenant" in detail["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Unknown UUID → 404, inactive tenant → 409, malformed UUID → 400
# ─────────────────────────────────────────────────────────────────────────────


class TestImpersonationTargetValidation:
    """Security invariant 4: target tenant must exist (404) and be active (409)."""

    def test_unknown_tenant_uuid_404(self, client, db_session, mock_cognito_jwt_verify):
        """Header with unknown tenant UUID → 404."""
        platform_user = _create_platform_user(
            db_session, email="cb15-404@pilot.local", role_code="owner"
        )
        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        unknown_uuid = uuid.uuid4()
        headers = {
            "Authorization": token,
            "X-Impersonate-Tenant": str(unknown_uuid),
        }

        resp = client.get("/api/v1/users/me/permissions", headers=headers)

        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["title"] == "Tenant not found"

    def test_inactive_tenant_409(self, client, db_session, mock_cognito_jwt_verify):
        """Header with inactive tenant UUID → 409."""
        platform_user = _create_platform_user(
            db_session, email="cb15-409@pilot.local", role_code="owner"
        )
        inactive_tenant = _create_tenant(
            db_session, name="Inactive Tenant", is_active=False
        )

        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {
            "Authorization": token,
            "X-Impersonate-Tenant": str(inactive_tenant.id),
        }

        resp = client.get("/api/v1/users/me/permissions", headers=headers)

        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["title"] == "Tenant inactive"

    def test_malformed_uuid_400(self, client, db_session, mock_cognito_jwt_verify):
        """Header with malformed UUID → 400."""
        platform_user = _create_platform_user(
            db_session, email="cb15-400@pilot.local", role_code="owner"
        )
        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {
            "Authorization": token,
            "X-Impersonate-Tenant": "not-a-uuid",
        }

        resp = client.get("/api/v1/users/me/permissions", headers=headers)

        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["title"] == "Invalid tenant identifier"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: GET /api/v1/operator/tenants returns 200
# ─────────────────────────────────────────────────────────────────────────────


class TestOperatorTenantList:
    """GET /api/v1/operator/tenants — tenant selector source."""

    def test_list_tenants_200(self, client, db_session, mock_cognito_jwt_verify):
        """Platform user with read_all → 200 with list; assert by inserted ID."""
        platform_user = _create_platform_user(
            db_session, email="cb15-list@pilot.local", role_code="owner"
        )
        target_tenant = _create_tenant(db_session, name="List Test Tenant")

        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {"Authorization": token}

        resp = client.get("/api/v1/operator/tenants", headers=headers)

        assert resp.status_code == 200
        tenants = resp.json()["tenants"]
        # Find our inserted tenant by ID (never assert on total count)
        found = [t for t in tenants if t["tenant_id"] == str(target_tenant.id)]
        assert len(found) == 1
        assert found[0]["name"] == target_tenant.name
        assert found[0]["is_active"] is True

    def test_list_tenants_accountant_read_all_allowed(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """Accountant role has read_all=true → 200 on GET /tenants."""
        platform_user = _create_platform_user(
            db_session, email="cb15-acct-list@pilot.local", role_code="accountant"
        )
        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {"Authorization": token}

        resp = client.get("/api/v1/operator/tenants", headers=headers)

        # Accountant has read_all=true → 200
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: POST /impersonation/start writes audit.event row
# ─────────────────────────────────────────────────────────────────────────────


class TestImpersonationStart:
    """POST /api/v1/operator/impersonation/start — audit-logged session start."""

    def test_start_writes_audit_event(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """POST /start writes audit.event with action='start', actor_type='platform'."""
        from app.models.system import AuditEvent

        platform_user = _create_platform_user(
            db_session, email="cb15-start@pilot.local", role_code="owner"
        )
        target_tenant = _create_tenant(db_session, name="Start Target")

        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {"Authorization": token}

        resp = client.post(
            "/api/v1/operator/impersonation/start",
            json={"tenant_id": str(target_tenant.id)},
            headers=headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == str(target_tenant.id)
        assert data["tenant_name"] == target_tenant.name
        assert data["role_code"] == "owner"
        assert data["impersonator_user_id"] == str(platform_user.id)

        # Query audit.event for the start row (scoped by our IDs)
        events = db_session.exec(
            select(AuditEvent)
            .where(AuditEvent.entity_name == "impersonation")
            .where(AuditEvent.action == "start")
            .where(AuditEvent.tenant_id == target_tenant.id)
            .where(AuditEvent.user_id == platform_user.id)
        ).all()
        assert len(events) >= 1
        assert events[0].actor_type == "platform"

    def test_start_unknown_tenant_404(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """POST /start with unknown tenant → 404."""
        platform_user = _create_platform_user(
            db_session, email="cb15-start-404@pilot.local", role_code="owner"
        )
        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {"Authorization": token}

        resp = client.post(
            "/api/v1/operator/impersonation/start",
            json={"tenant_id": str(uuid.uuid4())},
            headers=headers,
        )

        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: POST /impersonation/end writes audit.event row; end-without-start 200
# ─────────────────────────────────────────────────────────────────────────────


class TestImpersonationEnd:
    """POST /api/v1/operator/impersonation/end — audit-logged session end."""

    def test_end_writes_audit_event(self, client, db_session, mock_cognito_jwt_verify):
        """POST /end writes audit.event with action='end'."""
        from app.models.system import AuditEvent

        platform_user = _create_platform_user(
            db_session, email="cb15-end@pilot.local", role_code="owner"
        )
        target_tenant = _create_tenant(db_session, name="End Target")

        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {"Authorization": token}

        resp = client.post(
            "/api/v1/operator/impersonation/end",
            json={"tenant_id": str(target_tenant.id)},
            headers=headers,
        )

        assert resp.status_code == 200
        assert resp.json()["ended"] is True

        # Query audit.event for the end row
        events = db_session.exec(
            select(AuditEvent)
            .where(AuditEvent.entity_name == "impersonation")
            .where(AuditEvent.action == "end")
            .where(AuditEvent.tenant_id == target_tenant.id)
            .where(AuditEvent.user_id == platform_user.id)
        ).all()
        assert len(events) >= 1
        assert events[0].actor_type == "platform"

    def test_end_without_start_still_200(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """POST /end without a prior /start → still 200 (defensive design §D.3)."""
        platform_user = _create_platform_user(
            db_session, email="cb15-end-no-start@pilot.local", role_code="owner"
        )
        target_tenant = _create_tenant(db_session, name="End No Start Target")

        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {"Authorization": token}

        resp = client.post(
            "/api/v1/operator/impersonation/end",
            json={"tenant_id": str(target_tenant.id)},
            headers=headers,
        )

        assert resp.status_code == 200
        assert resp.json()["ended"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Accountant → 403 on start/end; tenant JWT → 403 on all three
# ─────────────────────────────────────────────────────────────────────────────


class TestImpersonationPermissionDenied:
    """Accountant role and tenant JWT → 403 on impersonation endpoints."""

    def test_accountant_403_on_start(self, client, db_session, mock_cognito_jwt_verify):
        """Accountant role → 403 on POST /impersonation/start."""
        platform_user = _create_platform_user(
            db_session, email="cb15-acct-start@pilot.local", role_code="accountant"
        )
        target_tenant = _create_tenant(db_session, name="Acct Start Target")

        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {"Authorization": token}

        resp = client.post(
            "/api/v1/operator/impersonation/start",
            json={"tenant_id": str(target_tenant.id)},
            headers=headers,
        )

        assert resp.status_code == 403

    def test_accountant_403_on_end(self, client, db_session, mock_cognito_jwt_verify):
        """Accountant role → 403 on POST /impersonation/end."""
        platform_user = _create_platform_user(
            db_session, email="cb15-acct-end@pilot.local", role_code="accountant"
        )
        target_tenant = _create_tenant(db_session, name="Acct End Target")

        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {"Authorization": token}

        resp = client.post(
            "/api/v1/operator/impersonation/end",
            json={"tenant_id": str(target_tenant.id)},
            headers=headers,
        )

        assert resp.status_code == 403

    def test_tenant_jwt_403_on_all_operator_endpoints(
        self, client, db_session, mock_cognito_jwt
    ):
        """Tenant user JWT → 403 on all 3 operator endpoints (get_platform_user)."""
        own_tenant = _create_tenant(db_session, name="Tenant JWT Tenant")
        tenant_user_obj = _create_tenant_user(
            db_session, own_tenant, email="cb15-tenant-jwt@pilot.local"
        )

        mock_cognito_jwt(tenant_user_obj)

        # GET /tenants → 403
        resp = client.get("/api/v1/operator/tenants")
        assert resp.status_code == 403

        # POST /start → 403
        resp = client.post(
            "/api/v1/operator/impersonation/start",
            json={"tenant_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 403

        # POST /end → 403
        resp = client.post(
            "/api/v1/operator/impersonation/end",
            json={"tenant_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Mutation under impersonation writes action='request' audit row
# ─────────────────────────────────────────────────────────────────────────────


class TestImpersonatedMutationAudit:
    """Impersonated-mutation audit middleware writes action='request' row.

    Approach: The middleware uses its own ``Session(engine)`` (separate from the
    test's ``db_session``).  To avoid permanently writing to the dev DB and to
    capture the audit event within the test's transaction, we patch
    ``app.main.Session`` to yield a mock session that records the ``add()`` call.
    We then assert the ``AuditEvent`` object has the correct fields.
    """

    def test_mutation_under_impersonation_writes_request_audit(
        self, client, db_session, mock_cognito_jwt_verify
    ):
        """POST under impersonation → middleware writes action='request' row."""
        platform_user = _create_platform_user(
            db_session, email="cb15-mutation@pilot.local", role_code="owner"
        )
        target_tenant = _create_tenant(db_session, name="Mutation Target")

        _mock_platform_jwt(mock_cognito_jwt_verify, platform_user)
        token = f"Bearer mock_token_{uuid.uuid4()}"
        headers = {
            "Authorization": token,
            "X-Impersonate-Tenant": str(target_tenant.id),
        }

        # Patch the middleware's Session to capture the audit event without
        # permanently writing to the dev DB.
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        with patch("app.main.Session", return_value=mock_session):
            resp = client.post(
                "/api/v1/customers/",
                json={"display_name": "CB15 Impersonated Customer"},
                headers=headers,
            )

        # The POST should succeed (owner role has * permission)
        assert resp.status_code == 201

        # Verify the middleware wrote an audit event
        mock_session.add.assert_called_once()
        event = mock_session.add.call_args[0][0]
        assert event.entity_name == "impersonation"
        assert event.action == "request"
        assert event.actor_type == "platform"
        assert event.tenant_id == target_tenant.id
        assert event.user_id == platform_user.id
        assert event.contextdata["method"] == "POST"
        assert "/customers" in event.contextdata["path"]
        mock_session.commit.assert_called_once()
