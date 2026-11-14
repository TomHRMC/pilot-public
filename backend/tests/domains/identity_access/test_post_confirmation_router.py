"""
Tests for: Post-Confirmation Lambda 3-path router (SIGNUP-GA-1).
Domain: identity_access (PRD §3.5)

Covers Path 1 (existing user → no-op), Path 2 (pending invite → attach),
Path 3 (new owner → create), re-fire idempotency, handler-never-raises, and
the placeholder-name insert with no unique constraint (ADR-0012).
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from app.models.auth import (
    TenantUser,
    TenantUserInvite,
    TenantUserRole,
    TenantUserStatus,
)
from app.models.core import Tenant, User

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


def _make_cognito_event(email: str) -> dict:
    """Build a synthetic Cognito Post-Confirmation event dict."""
    return {
        "request": {
            "userAttributes": {
                "email": email,
                "sub": str(uuid.uuid4()),
            }
        },
        "response": {},
    }


def _get_or_create_role(db: Session, code: str) -> TenantUserRole:
    role = db.exec(select(TenantUserRole).where(TenantUserRole.code == code)).first()
    if not role:
        role = TenantUserRole(code=code, name=code.capitalize(), is_default=True)
        db.add(role)
        db.flush()
    return role


def _get_or_create_status(db: Session, code: str) -> TenantUserStatus:
    status = db.exec(
        select(TenantUserStatus).where(TenantUserStatus.code == code)
    ).first()
    if not status:
        status = TenantUserStatus(code=code, name=code.capitalize(), is_default=True)
        db.add(status)
        db.flush()
    return status


class TestPath1ExistingUserNoOp:
    """Path 1: a user row already exists → no-op, no tenant created."""

    def test_existing_user_no_op(self, db_session: Session):
        import importlib

        handler_mod = importlib.import_module("lambda.post_confirmation.handler")

        email = f"path1-{uuid.uuid4()}@example.com"
        # Pre-create a user (simulates a platform user or re-fire)
        user = User(email=email)
        db_session.add(user)
        db_session.commit()

        event = _make_cognito_event(email)
        # Patch the engine so the handler uses our test session's connection
        with patch.object(
            handler_mod, "_get_engine", return_value=db_session.get_bind()
        ):
            result = handler_mod.handler(event, None)

        assert result is event  # handler returns event unchanged
        # No second user created
        users = db_session.exec(select(User).where(User.email == email)).all()
        assert len(users) == 1


class TestPath2InviteAttach:
    """Path 2: pending invite → user + tenant_user attached, accepted_at set."""

    def test_pending_invite_attach(self, db_session: Session, test_tenant):
        import importlib

        handler_mod = importlib.import_module("lambda.post_confirmation.handler")

        email = f"path2-{uuid.uuid4()}@example.com"
        # Ensure role/status exist (the handler will look them up)
        _get_or_create_role(db_session, "technician")
        _get_or_create_status(db_session, "active")

        invite = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=email,
            token_hash=f"hash-{uuid.uuid4()}",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
        )
        db_session.add(invite)
        db_session.commit()

        event = _make_cognito_event(email)
        with patch.object(
            handler_mod, "_get_engine", return_value=db_session.get_bind()
        ):
            result = handler_mod.handler(event, None)

        assert result is event

        # User created
        user = db_session.exec(select(User).where(User.email == email)).first()
        assert user is not None

        # tenant_user attached to the invite's tenant
        tu = db_session.exec(
            select(TenantUser)
            .where(TenantUser.tenant_id == test_tenant.id)
            .where(TenantUser.user_id == user.id)
        ).first()
        assert tu is not None
        assert tu.joined_at is not None

        # invite.accepted_at set
        db_session.refresh(invite)
        assert invite.accepted_at is not None


class TestPath3NewOwnerCreate:
    """Path 3: new owner → tenant + user + tenant_user created."""

    def test_new_owner_create(self, db_session: Session):
        import importlib

        handler_mod = importlib.import_module("lambda.post_confirmation.handler")

        email = f"path3-{uuid.uuid4()}@example.com"
        event = _make_cognito_event(email)
        with patch.object(
            handler_mod, "_get_engine", return_value=db_session.get_bind()
        ):
            result = handler_mod.handler(event, None)

        assert result is event

        user = db_session.exec(select(User).where(User.email == email)).first()
        assert user is not None

        tu = db_session.exec(
            select(TenantUser).where(TenantUser.user_id == user.id)
        ).first()
        assert tu is not None
        assert tu.role_code == "owner"
        assert tu.joined_at is not None

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == tu.tenant_id)
        ).first()
        assert tenant is not None
        # Placeholder name = "{local_part}'s Company"
        local_part = email.split("@")[0]
        assert tenant.name == f"{local_part}'s Company"

    def test_placeholder_name_no_unique_violation(self, db_session: Session):
        """Two emails with the same local-part both create 'tom's Company'."""
        import importlib

        handler_mod = importlib.import_module("lambda.post_confirmation.handler")

        email_a = f"tom-{uuid.uuid4()}@a.com"
        email_b = f"tom-{uuid.uuid4()}@b.com"
        # Both have local part starting with "tom-..." — but we want exact
        # same local part to prove no unique violation. Use a fixed local.
        local = f"sameuser{uuid.uuid4().hex[:8]}"
        email_a = f"{local}@a.com"
        email_b = f"{local}@b.com"

        with patch.object(
            handler_mod, "_get_engine", return_value=db_session.get_bind()
        ):
            handler_mod.handler(_make_cognito_event(email_a), None)
            handler_mod.handler(_make_cognito_event(email_b), None)

        tenants = db_session.exec(
            select(Tenant).where(Tenant.name == f"{local}'s Company")
        ).all()
        assert len(tenants) == 2  # both created, no unique violation


class TestReFireIdempotency:
    """Same email twice → Path 1 no-op the second time."""

    def test_refire_idempotent(self, db_session: Session):
        import importlib

        handler_mod = importlib.import_module("lambda.post_confirmation.handler")

        email = f"refire-{uuid.uuid4()}@example.com"
        with patch.object(
            handler_mod, "_get_engine", return_value=db_session.get_bind()
        ):
            handler_mod.handler(_make_cognito_event(email), None)
            handler_mod.handler(_make_cognito_event(email), None)

        users = db_session.exec(select(User).where(User.email == email)).all()
        assert len(users) == 1  # exactly one user


class TestPath2RoleAtInvite:
    """TEAM-INVITE-1: role carried on the invite; NULL → technician fallback."""

    def test_role_code_office_staff(self, db_session: Session, test_tenant):
        """Invite with role_code='office_staff' → attached tenant_user has that role."""
        import importlib

        handler_mod = importlib.import_module("lambda.post_confirmation.handler")

        email = f"role-office-{uuid.uuid4()}@example.com"
        _get_or_create_role(db_session, "office_staff")
        _get_or_create_role(db_session, "technician")
        _get_or_create_status(db_session, "active")

        invite = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=email,
            token_hash=f"hash-{uuid.uuid4()}",
            role_code="office_staff",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
        )
        db_session.add(invite)
        db_session.commit()

        event = _make_cognito_event(email)
        with patch.object(
            handler_mod, "_get_engine", return_value=db_session.get_bind()
        ):
            result = handler_mod.handler(event, None)

        assert result is event

        user = db_session.exec(select(User).where(User.email == email)).first()
        assert user is not None

        tu = db_session.exec(
            select(TenantUser)
            .where(TenantUser.tenant_id == test_tenant.id)
            .where(TenantUser.user_id == user.id)
        ).first()
        assert tu is not None
        assert tu.role_code == "office_staff"

    def test_role_code_null_falls_back_to_technician(
        self, db_session: Session, test_tenant
    ):
        """Invite with role_code=None → attached tenant_user gets 'technician'."""
        import importlib

        handler_mod = importlib.import_module("lambda.post_confirmation.handler")

        email = f"role-null-{uuid.uuid4()}@example.com"
        _get_or_create_role(db_session, "technician")
        _get_or_create_status(db_session, "active")

        invite = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=email,
            token_hash=f"hash-{uuid.uuid4()}",
            role_code=None,
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
        )
        db_session.add(invite)
        db_session.commit()

        event = _make_cognito_event(email)
        with patch.object(
            handler_mod, "_get_engine", return_value=db_session.get_bind()
        ):
            result = handler_mod.handler(event, None)

        assert result is event

        user = db_session.exec(select(User).where(User.email == email)).first()
        assert user is not None

        tu = db_session.exec(
            select(TenantUser)
            .where(TenantUser.tenant_id == test_tenant.id)
            .where(TenantUser.user_id == user.id)
        ).first()
        assert tu is not None
        assert tu.role_code == "technician"

    def test_usage_counter_failure_still_completes_attach(
        self, db_session: Session, test_tenant
    ):
        """If the usage counter fails, the attach still completes (ADR-0011)."""
        import importlib

        handler_mod = importlib.import_module("lambda.post_confirmation.handler")

        email = f"counter-fail-{uuid.uuid4()}@example.com"
        _get_or_create_role(db_session, "technician")
        _get_or_create_status(db_session, "active")

        invite = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=email,
            token_hash=f"hash-{uuid.uuid4()}",
            role_code="technician",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
        )
        db_session.add(invite)
        db_session.commit()

        event = _make_cognito_event(email)
        # Force the usage counter to fail
        with (
            patch.object(
                handler_mod, "_get_engine", return_value=db_session.get_bind()
            ),
            patch.object(
                handler_mod,
                "_increment_user_count_best_effort",
                side_effect=RuntimeError("forced failure"),
            ),
        ):
            result = handler_mod.handler(event, None)

        assert result is event

        # User was still created and attached
        user = db_session.exec(select(User).where(User.email == email)).first()
        assert user is not None

        tu = db_session.exec(
            select(TenantUser)
            .where(TenantUser.tenant_id == test_tenant.id)
            .where(TenantUser.user_id == user.id)
        ).first()
        assert tu is not None
        assert tu.role_code == "technician"

        # Invite was still marked accepted
        db_session.refresh(invite)
        assert invite.accepted_at is not None


class TestHandlerNeverRaises:
    """Malformed event → returns event, logs, does not throw."""

    def test_malformed_event_returns_event(self):
        import importlib

        handler_mod = importlib.import_module("lambda.post_confirmation.handler")

        malformed_events = [
            {},
            {"request": {}},
            {"request": {"userAttributes": {}}},
            {"request": {"userAttributes": {"email": ""}}},
            None,
            "not a dict",
        ]
        for event in malformed_events:
            result = handler_mod.handler(event, None)
            assert result is event
