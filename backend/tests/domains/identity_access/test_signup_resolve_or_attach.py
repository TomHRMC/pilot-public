"""
Tests for: initiate_signup resolve-or-attach + list_abandoned_signups (SIGNUP-GA-1).
Domain: identity_access (PRD §3.5)

Covers:
  - Lambda-created tenant then /signup → attaches, overwrites tenant.name,
    persists owner_email, no 2nd tenant
  - repeat call idempotent
  - email past step1_account → 409 signup-state-conflict
  - client-ahead-of-confirmation → credential_pending=True
  - cleanup helper: old incomplete appears, complete excluded, recent excluded
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.auth import TenantUser, TenantUserRole, TenantUserStatus
from app.models.core import Tenant, User
from app.models.signup import TenantSignup
from services.tenant_signup import initiate_signup, list_abandoned_signups

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


def _signup_payload(email: str | None = None) -> dict:
    return {
        "business_name": f"Acme Electric {uuid.uuid4()}",
        "trade": "electrical",
        "business_size": "1-5",
        "zip_code": "12345",
        "time_zone": "America/New_York",
        "owner_email": email or f"owner-{uuid.uuid4()}@example.com",
        "owner_first_name": "Mike",
        "owner_last_name": "Contractor",
    }


def _get_trial_tier_id(db_session) -> str:
    row = db_session.execute(
        text("SELECT tier_id FROM subscription_tier WHERE is_trial = true LIMIT 1")
    ).fetchone()
    return str(row[0])


def _create_lambda_owner(db, email: str) -> tuple[Tenant, User]:
    """Simulate Lambda Path 3: create tenant (placeholder) + owner user."""
    local_part = email.split("@")[0]
    tenant = Tenant(name=f"{local_part}'s Company", is_active=True)
    db.add(tenant)
    db.flush()

    user = User(email=email)
    db.add(user)
    db.flush()

    role = db.exec(select(TenantUserRole).where(TenantUserRole.code == "owner")).first()
    if not role:
        role = TenantUserRole(code="owner", name="Owner", is_default=True)
        db.add(role)
        db.flush()

    status = db.exec(
        select(TenantUserStatus).where(TenantUserStatus.code == "active")
    ).first()
    if not status:
        status = TenantUserStatus(code="active", name="Active", is_default=True)
        db.add(status)
        db.flush()

    tu = TenantUser(
        tenant_id=tenant.id,
        user_id=user.id,
        role_code=role.code,
        status_id=status.id,
        joined_at=datetime.now(UTC),
    )
    db.add(tu)
    db.commit()
    db.refresh(tenant)
    db.refresh(user)
    return tenant, user


def _insert_backdated_tenant_signup(
    db_session, tenant_id: uuid.UUID, email: str, state: str, days_old: int
) -> None:
    """Raw INSERT a tenant + tenant_signup with backdated created_at.

    The immutability trigger blocks UPDATE on created_at, so we must set it
    at INSERT time. The ORM before_insert event (trial tier auto-assign) does
    not fire for raw SQL, so we pass current_subscription_tier_id explicitly.
    """
    old_ts = datetime.now(UTC) - timedelta(days=days_old)
    tier_id = _get_trial_tier_id(db_session)
    db_session.execute(
        text(
            "INSERT INTO public.tenant "
            "(id, name, is_active, current_subscription_tier_id, created_at, updated_at) "
            "VALUES (:id, :name, true, :tier, :ts, :ts)"
        ),
        {
            "id": str(tenant_id),
            "name": f"Test Co {uuid.uuid4()}",
            "tier": tier_id,
            "ts": old_ts,
        },
    )
    db_session.execute(
        text(
            "INSERT INTO public.tenant_signup "
            "(tenant_id, signup_state, signup_started_at, business_name, "
            "trade, business_size, zip, time_zone, owner_email, created_at, updated_at) "
            "VALUES (:tid, :state, :ts, 'Test Co', 'electrical', "
            "'1-5', '12345', 'America/New_York', :email, :ts, :ts)"
        ),
        {"tid": str(tenant_id), "state": state, "ts": old_ts, "email": email},
    )
    db_session.commit()


class TestResolveOrAttach:
    """initiate_signup resolve-or-attach by email."""

    def test_lambda_created_then_signup_attaches(self, db_session):
        email = f"attach-{uuid.uuid4()}@example.com"
        tenant, _user = _create_lambda_owner(db_session, email)

        payload = _signup_payload(email)
        result = initiate_signup(db=db_session, **payload)

        assert result["credential_pending"] is False
        assert result["tenant_id"] == str(tenant.id)
        assert result["signup_state"] == "step1_account"

        # tenant.name overwritten with real business_name
        db_session.refresh(tenant)
        assert tenant.name == payload["business_name"]

        # owner_email persisted on signup
        signup = db_session.exec(
            select(TenantSignup).where(TenantSignup.tenant_id == tenant.id)
        ).first()
        assert signup is not None
        assert signup.owner_email == email
        assert signup.owner_first_name == "Mike"

        # No second tenant created for this email
        tenants = db_session.exec(select(Tenant).where(Tenant.id == tenant.id)).all()
        assert len(tenants) == 1

    def test_repeat_call_idempotent(self, db_session):
        email = f"idem-{uuid.uuid4()}@example.com"
        _create_lambda_owner(db_session, email)

        payload = _signup_payload(email)
        r1 = initiate_signup(db=db_session, **payload)
        r2 = initiate_signup(db=db_session, **payload)

        assert r1["tenant_id"] == r2["tenant_id"]
        assert r1["credential_pending"] is False
        assert r2["credential_pending"] is False

    def test_email_past_step1_returns_409(self, db_session):
        from fastapi import HTTPException

        email = f"conflict-{uuid.uuid4()}@example.com"
        tenant, _user = _create_lambda_owner(db_session, email)

        # Create a signup already past step1_account
        signup = TenantSignup(
            tenant_id=tenant.id,
            signup_state="step2_legal",
            signup_started_at=datetime.now(UTC),
            business_name="Old Name",
            trade="electrical",
            business_size="1-5",
            zip="12345",
            time_zone="America/New_York",
            owner_email=email,
        )
        db_session.add(signup)
        db_session.commit()

        payload = _signup_payload(email)
        with pytest.raises(HTTPException) as exc_info:
            initiate_signup(db=db_session, **payload)

        assert exc_info.value.status_code == 409
        assert "signup-state-conflict" in exc_info.value.detail["type"]

    def test_client_ahead_of_confirmation_credential_pending(self, db_session):
        email = f"pending-{uuid.uuid4()}@example.com"
        payload = _signup_payload(email)

        result = initiate_signup(db=db_session, **payload)

        assert result["credential_pending"] is True
        assert result["signup_state"] == "step1_account"

        # A tenant + signup were created (pending-credential posture)
        signup = db_session.exec(
            select(TenantSignup).where(TenantSignup.owner_email == email)
        ).first()
        assert signup is not None
        assert signup.owner_email == email

    def test_pending_repeat_idempotent(self, db_session):
        email = f"pending2-{uuid.uuid4()}@example.com"
        payload = _signup_payload(email)

        r1 = initiate_signup(db=db_session, **payload)
        r2 = initiate_signup(db=db_session, **payload)

        assert r1["tenant_id"] == r2["tenant_id"]
        assert r1["credential_pending"] is True
        assert r2["credential_pending"] is True


class TestListAbandonedSignups:
    """list_abandoned_signups helper — report-only, signup_state-keyed."""

    def test_old_incomplete_appears(self, db_session):
        email = f"abandoned-{uuid.uuid4()}@example.com"
        tenant_id = uuid.uuid4()
        _insert_backdated_tenant_signup(
            db_session, tenant_id, email, "step1_account", 40
        )

        result = list_abandoned_signups(db_session, older_than_days=30)
        abandoned_ids = [r["tenant_id"] for r in result]
        assert str(tenant_id) in abandoned_ids

    def test_complete_excluded(self, db_session):
        email = f"complete-{uuid.uuid4()}@example.com"
        tenant_id = uuid.uuid4()
        _insert_backdated_tenant_signup(db_session, tenant_id, email, "complete", 40)

        result = list_abandoned_signups(db_session, older_than_days=30)
        abandoned_ids = [r["tenant_id"] for r in result]
        assert str(tenant_id) not in abandoned_ids

    def test_recent_incomplete_excluded(self, db_session):
        email = f"recent-{uuid.uuid4()}@example.com"
        tenant = Tenant(name=f"Recent Co {uuid.uuid4()}", is_active=True)
        db_session.add(tenant)
        db_session.flush()

        signup = TenantSignup(
            tenant_id=tenant.id,
            signup_state="step1_account",
            signup_started_at=datetime.now(UTC),
            business_name="Recent Co",
            trade="electrical",
            business_size="1-5",
            zip="12345",
            time_zone="America/New_York",
            owner_email=email,
        )
        db_session.add(signup)
        db_session.commit()

        result = list_abandoned_signups(db_session, older_than_days=30)
        abandoned_ids = [r["tenant_id"] for r in result]
        assert str(tenant.id) not in abandoned_ids
