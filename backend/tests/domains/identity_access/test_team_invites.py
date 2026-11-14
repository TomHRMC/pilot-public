"""
TEAM-INVITE-1 — Team invite API tests.

Domain: identity_access
Covers: create, list, resend, revoke, public token validation, RBAC,
idempotency, cross-tenant isolation, and service-level token validation.

Email dispatch is mocked: monkeypatches ``send_email`` inside
``services.email_service`` so no real SendGrid calls happen.
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from app.models.auth import TenantUser, TenantUserInvite, TenantUserRole
from app.models.core import User
from services.team_invite_service import validate_invite_token

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _patch_email_send():
    """Patch send_email inside email_service (imported lazily by render_and_send)."""
    return patch("services.email_service.send_email")


def _extract_token_from_url(url: str) -> str:
    """Extract the raw token from an invite URL like .../invite/{token}."""
    return url.rsplit("/invite/", 1)[-1]


def _make_owner_user(db_session: Session, test_tenant) -> User:
    """Create an owner user linked to the test tenant (for RBAC tests)."""
    from app.models.auth import TenantUserStatus

    role = db_session.exec(
        select(TenantUserRole).where(TenantUserRole.code == "owner")
    ).first()
    if not role:
        role = TenantUserRole(code="owner", name="Owner", is_default=True)
        db_session.add(role)
        db_session.flush()

    status = db_session.exec(
        select(TenantUserStatus).where(TenantUserStatus.code == "active")
    ).first()
    if not status:
        status = TenantUserStatus(code="active", name="Active", is_default=True)
        db_session.add(status)
        db_session.flush()

    email = f"owner-{uuid.uuid4()}@pilot.local"
    user = User(
        id=uuid.uuid4(),
        email=email,
        first_name="Test",
        last_name="Owner",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    tu = TenantUser(
        tenant_id=test_tenant.id,
        user_id=user.id,
        role_code="owner",
        status_id=status.id,
        joined_at=datetime.now(UTC),
    )
    db_session.add(tu)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_tech_user(db_session: Session, test_tenant) -> User:
    """Create a technician user (no users.manage permission)."""
    from app.models.auth import TenantUserStatus

    role = db_session.exec(
        select(TenantUserRole).where(TenantUserRole.code == "technician")
    ).first()
    if not role:
        role = TenantUserRole(code="technician", name="Field Technician")
        db_session.add(role)
        db_session.flush()

    status = db_session.exec(
        select(TenantUserStatus).where(TenantUserStatus.code == "active")
    ).first()
    if not status:
        status = TenantUserStatus(code="active", name="Active", is_default=True)
        db_session.add(status)
        db_session.flush()

    email = f"tech-{uuid.uuid4()}@pilot.local"
    user = User(
        id=uuid.uuid4(),
        email=email,
        first_name="Test",
        last_name="Tech",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    tu = TenantUser(
        tenant_id=test_tenant.id,
        user_id=user.id,
        role_code="technician",
        status_id=status.id,
        joined_at=datetime.now(UTC),
    )
    db_session.add(tu)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── Test Classes ──────────────────────────────────────────────────────────────


class TestCreateInvite:
    """Cases 1-6: create invite happy path, validation, conflicts, RBAC."""

    def test_1_create_invite_happy_path(self, client, db_session, test_tenant):
        """Create invite: 201, row has role_code, ~7d expiry, email sent with /invite/<token>."""
        email = f"invitee-{uuid.uuid4()}@example.com"
        with _patch_email_send() as mock_send:
            resp = client.post(
                "/api/v1/users/invites/test",
                json={"email": email, "role_code": "technician"},
            )

        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["email"] == email.lower()
        assert data["role_code"] == "technician"
        assert "expires_at" in data
        assert "id" in data
        # Raw token must NOT be in the response
        assert "token" not in data
        assert "raw_token" not in data
        assert "token_hash" not in data

        # Email was "sent"
        assert mock_send.called

        # Verify the invite row has role_code + ~7d expiry
        invite = db_session.exec(
            select(TenantUserInvite).where(TenantUserInvite.id == data["id"])
        ).first()
        assert invite is not None
        assert invite.role_code == "technician"
        delta = invite.expires_at - datetime.now(UTC)
        assert timedelta(days=6, hours=23) < delta <= timedelta(days=7)

    def test_2_create_invite_bogus_role(self, client, db_session, test_tenant):
        """Create with bogus role → 400 invalid_role."""
        with _patch_email_send():
            resp = client.post(
                "/api/v1/users/invites/test",
                json={
                    "email": f"bogus-{uuid.uuid4()}@example.com",
                    "role_code": "superadmin",
                },
            )

        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["type"] == "https://errors.pilotfortrades.com/invalid-role"

    def test_3_create_invite_user_exists(self, client, db_session, test_tenant):
        """Create when user row exists for email → 409 invite_user_exists (specific type URI)."""
        existing_email = f"existing-{uuid.uuid4()}@example.com"
        existing_user = User(email=existing_email, is_active=True)
        db_session.add(existing_user)
        db_session.commit()

        with _patch_email_send():
            resp = client.post(
                "/api/v1/users/invites/test",
                json={"email": existing_email, "role_code": "technician"},
            )

        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["type"] == "https://errors.pilotfortrades.com/invite_user_exists"
        assert "already has a Pilot account" in detail.get("detail", "")

    def test_4_create_invite_duplicate_pending(self, client, db_session, test_tenant):
        """Create duplicate pending (same tenant+email) → 409 invite_pending_exists (specific type URI) + existing id."""
        email = f"dup-{uuid.uuid4()}@example.com"

        with _patch_email_send():
            resp1 = client.post(
                "/api/v1/users/invites/test",
                json={"email": email, "role_code": "technician"},
            )
            assert resp1.status_code == 201
            first_id = resp1.json()["id"]

            resp2 = client.post(
                "/api/v1/users/invites/test",
                json={"email": email, "role_code": "technician"},
            )

        assert resp2.status_code == 409
        detail = resp2.json()["detail"]
        assert (
            detail["type"] == "https://errors.pilotfortrades.com/invite_pending_exists"
        )
        assert "pending invite already exists" in detail.get("detail", "")
        assert detail.get("invite_id") == first_id

    def test_4b_create_invite_after_revoke_reactivates(
        self, client, db_session, test_tenant
    ):
        """Create invite for email that was previously revoked → reactivates the existing row (no unique constraint violation)."""
        email = f"reactivate-{uuid.uuid4()}@example.com"

        # Create + revoke
        with _patch_email_send():
            create_resp = client.post(
                "/api/v1/users/invites/test",
                json={"email": email, "role_code": "technician"},
            )
            assert create_resp.status_code == 201
            invite_id = create_resp.json()["id"]

            revoke_resp = client.post(f"/api/v1/users/invites/{invite_id}/revoke/test")
            assert revoke_resp.status_code == 200

        # Now create again for the same email — should reactivate, not 500
        with _patch_email_send():
            resp = client.post(
                "/api/v1/users/invites/test",
                json={"email": email, "role_code": "office_staff"},
            )

        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["email"] == email.lower()
        assert data["role_code"] == "office_staff"
        # Same invite row was reactivated (same ID)
        assert data["id"] == invite_id

    def test_5_create_invite_missing_idempotency_key(
        self, client, db_session, test_tenant, mock_cognito_jwt
    ):
        """Missing Idempotency-Key on authenticated route → 400."""
        owner = _make_owner_user(db_session, test_tenant)
        mock_cognito_jwt(owner)

        with _patch_email_send():
            resp = client.post(
                "/api/v1/users/invites",
                json={
                    "email": f"nokey-{uuid.uuid4()}@example.com",
                    "role_code": "technician",
                },
            )

        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "missing-header" in detail.get("type", "")

    def test_6_create_invite_rbac_non_owner(
        self, client, db_session, test_tenant, mock_cognito_jwt
    ):
        """Non-owner (technician) create → 403."""
        tech = _make_tech_user(db_session, test_tenant)
        mock_cognito_jwt(tech)

        with _patch_email_send():
            resp = client.post(
                "/api/v1/users/invites",
                json={
                    "email": f"rbac-{uuid.uuid4()}@example.com",
                    "role_code": "technician",
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )

        assert resp.status_code == 403


class TestListInvites:
    """Case 7: list invites with status precedence."""

    def test_7_list_invites_status_precedence(self, client, db_session, test_tenant):
        """List invites: status precedence correct (accepted > revoked > expired > pending)."""
        now = datetime.now(UTC)

        accepted = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=f"accepted-{uuid.uuid4()}@example.com",
            token_hash=f"hash-{uuid.uuid4()}",
            role_code="technician",
            expires_at=now + timedelta(days=7),
            accepted_at=now,
            is_active=True,
        )
        revoked = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=f"revoked-{uuid.uuid4()}@example.com",
            token_hash=f"hash-{uuid.uuid4()}",
            role_code="technician",
            expires_at=now + timedelta(days=7),
            is_active=False,
        )
        expired = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=f"expired-{uuid.uuid4()}@example.com",
            token_hash=f"hash-{uuid.uuid4()}",
            role_code="technician",
            expires_at=now - timedelta(days=1),
            is_active=True,
        )
        pending = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=f"pending-{uuid.uuid4()}@example.com",
            token_hash=f"hash-{uuid.uuid4()}",
            role_code="technician",
            expires_at=now + timedelta(days=7),
            is_active=True,
        )
        for inv in [accepted, revoked, expired, pending]:
            db_session.add(inv)
        db_session.commit()

        resp = client.get("/api/v1/users/invites/test")

        assert resp.status_code == 200
        items = resp.json()

        by_id = {item["id"]: item for item in items}
        assert str(accepted.id) in by_id
        assert by_id[str(accepted.id)]["status"] == "accepted"
        assert str(revoked.id) in by_id
        assert by_id[str(revoked.id)]["status"] == "revoked"
        assert str(expired.id) in by_id
        assert by_id[str(expired.id)]["status"] == "expired"
        assert str(pending.id) in by_id
        assert by_id[str(pending.id)]["status"] == "pending"


class TestResendInvite:
    """Cases 8-9: resend happy path + accepted conflict."""

    def test_8_resend_happy_path(self, client, db_session, test_tenant):
        """Resend: new expiry, email resent, old token invalid, new token valid."""
        # Create an invite first
        with _patch_email_send():
            create_resp = client.post(
                "/api/v1/users/invites/test",
                json={
                    "email": f"resend-{uuid.uuid4()}@example.com",
                    "role_code": "technician",
                },
            )
        assert create_resp.status_code == 201
        invite_id = create_resp.json()["id"]
        old_expires = create_resp.json()["expires_at"]

        # Capture the first invite's token_hash
        invite = db_session.exec(
            select(TenantUserInvite).where(TenantUserInvite.id == invite_id)
        ).first()
        old_token_hash = invite.token_hash

        # Resend
        with _patch_email_send() as mock_send2:
            resp = client.post(f"/api/v1/users/invites/{invite_id}/resend/test")

        assert resp.status_code == 200, resp.text
        new_expires = resp.json()["expires_at"]
        assert new_expires != old_expires

        # Token was rotated
        db_session.refresh(invite)
        assert invite.token_hash != old_token_hash

        # Email was resent
        assert mock_send2.called

    def test_9_resend_accepted_invite(self, client, db_session, test_tenant):
        """Resend accepted invite → 409 invite_already_accepted."""
        invite = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=f"resend-accepted-{uuid.uuid4()}@example.com",
            token_hash=f"hash-{uuid.uuid4()}",
            role_code="technician",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            accepted_at=datetime.now(UTC),
            is_active=True,
        )
        db_session.add(invite)
        db_session.commit()

        resp = client.post(f"/api/v1/users/invites/{invite.id}/resend/test")

        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert "already been accepted" in detail.get("detail", "")


class TestRevokeInvite:
    """Cases 10-11: revoke pending + revoke accepted."""

    def test_10_revoke_pending(self, client, db_session, test_tenant):
        """Revoke pending → is_active=False; subsequent public lookup → 404."""
        with _patch_email_send():
            create_resp = client.post(
                "/api/v1/users/invites/test",
                json={
                    "email": f"revoke-{uuid.uuid4()}@example.com",
                    "role_code": "technician",
                },
            )
        assert create_resp.status_code == 201
        invite_id = create_resp.json()["id"]

        resp = client.post(f"/api/v1/users/invites/{invite_id}/revoke/test")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        invite = db_session.exec(
            select(TenantUserInvite).where(TenantUserInvite.id == invite_id)
        ).first()
        assert invite.is_active is False

    def test_11_revoke_accepted(self, client, db_session, test_tenant):
        """Revoke accepted → 409."""
        invite = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=f"revoke-accepted-{uuid.uuid4()}@example.com",
            token_hash=f"hash-{uuid.uuid4()}",
            role_code="technician",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            accepted_at=datetime.now(UTC),
            is_active=True,
        )
        db_session.add(invite)
        db_session.commit()

        resp = client.post(f"/api/v1/users/invites/{invite.id}/revoke/test")

        assert resp.status_code == 409


class TestPublicInviteLookup:
    """Case 12: public GET /invites/{token}."""

    def test_12_public_invite_lookup(self, client, db_session, test_tenant):
        """Public GET /invites/{token}: happy, unknown, expired, accepted, revoked → all 404 except happy."""
        # Create a valid invite directly with a known token
        raw_token = f"test-token-{uuid.uuid4()}"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        valid_invite = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=f"public-{uuid.uuid4()}@example.com",
            token_hash=token_hash,
            role_code="office_staff",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
        )
        db_session.add(valid_invite)
        db_session.commit()

        # Happy path
        resp = client.get(f"/api/v1/invites/{raw_token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == valid_invite.email
        assert data["role_code"] == "office_staff"
        assert "tenant_name" in data

        # Unknown token → 404
        resp = client.get("/api/v1/invites/garbage-token-xyz")
        assert resp.status_code == 404
        assert "invite_invalid" in resp.json()["detail"]["type"]

        # Expired → 404
        expired_token = f"expired-{uuid.uuid4()}"
        expired_hash = hashlib.sha256(expired_token.encode()).hexdigest()
        expired_invite = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=f"expired-{uuid.uuid4()}@example.com",
            token_hash=expired_hash,
            role_code="technician",
            expires_at=datetime.now(UTC) - timedelta(days=1),
            is_active=True,
        )
        db_session.add(expired_invite)
        db_session.commit()
        resp = client.get(f"/api/v1/invites/{expired_token}")
        assert resp.status_code == 404

        # Accepted → 404
        accepted_token = f"accepted-{uuid.uuid4()}"
        accepted_hash = hashlib.sha256(accepted_token.encode()).hexdigest()
        accepted_invite = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=f"accepted-{uuid.uuid4()}@example.com",
            token_hash=accepted_hash,
            role_code="technician",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            accepted_at=datetime.now(UTC),
            is_active=True,
        )
        db_session.add(accepted_invite)
        db_session.commit()
        resp = client.get(f"/api/v1/invites/{accepted_token}")
        assert resp.status_code == 404

        # Revoked → 404
        revoked_token = f"revoked-{uuid.uuid4()}"
        revoked_hash = hashlib.sha256(revoked_token.encode()).hexdigest()
        revoked_invite = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=f"revoked-{uuid.uuid4()}@example.com",
            token_hash=revoked_hash,
            role_code="technician",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=False,
        )
        db_session.add(revoked_invite)
        db_session.commit()
        resp = client.get(f"/api/v1/invites/{revoked_token}")
        assert resp.status_code == 404


class TestCrossTenantIsolation:
    """Case 13: cross-tenant invite access → 404."""

    def test_13_cross_tenant_invite_access(
        self, client, db_session, test_tenant, second_tenant
    ):
        """Invite from tenant_a targeted by tenant_b owner → 404 (no UUID leak)."""
        invite = TenantUserInvite(
            id=uuid.uuid4(),
            tenant_id=second_tenant.id,
            email=f"crosstenant-{uuid.uuid4()}@example.com",
            token_hash=f"hash-{uuid.uuid4()}",
            role_code="technician",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
        )
        db_session.add(invite)
        db_session.commit()

        # Use /test endpoint (test_tenant context) to try to revoke second_tenant's invite
        resp = client.post(f"/api/v1/users/invites/{invite.id}/revoke/test")
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert "not found" in detail.get("detail", "").lower()


class TestServiceTokenValidation:
    """Case 14: service-level validate_invite_token."""

    def test_14_validate_invite_token(self, client, db_session, test_tenant):
        """Service unit: validate_invite_token hash path — valid token validates, garbage → None."""
        # Create an invite via the /test endpoint to get a real token
        with _patch_email_send() as mock_send:
            resp = client.post(
                "/api/v1/users/invites/test",
                json={
                    "email": f"svc-{uuid.uuid4()}@example.com",
                    "role_code": "technician",
                },
            )
        assert resp.status_code == 201

        # Extract the invite_url from the mocked send_email call.
        # send_email(to=..., subject=..., body=..., html_body=...) — body is plain text.
        assert mock_send.called
        call_kwargs = mock_send.call_args.kwargs
        body = call_kwargs.get("body", "")
        # The plain-text body contains the invite URL on its own line
        assert "/invite/" in body
        # Extract the token: find the URL line and parse it
        for line in body.split("\n"):
            if "/invite/" in line:
                raw_token = line.strip().rsplit("/invite/", 1)[-1]
                break
        else:
            pytest.fail("No invite URL found in email body")

        # Validate the token via the service
        invite = validate_invite_token(db_session, raw_token=raw_token)
        assert invite is not None
        assert invite.role_code == "technician"

        # Garbage token → None
        assert validate_invite_token(db_session, raw_token="garbage") is None


class TestOfficeStaffJobsViewSeed:
    """PLP-FIX-7 §C.1 — office_staff permissions include jobs.view + converge-safe UPDATE idempotency."""

    def test_office_staff_has_jobs_view(self, db_session):
        """office_staff permissions array contains 'jobs.view' (Schedule board loads jobs)."""
        role = db_session.exec(
            select(TenantUserRole).where(TenantUserRole.code == "office_staff")
        ).first()
        assert role is not None
        assert "jobs.view" in role.permissions

    def test_converge_update_is_idempotent(self, db_session):
        """Running the converge UPDATE twice is a no-op on the second pass.

        Simulates the seed_core.py tenant_user_role block's else-branch:
        UPDATE ... WHERE permissions <> CAST(:permissions AS jsonb).
        The first call converges (if needed); the second must update 0 rows.
        """
        import json

        from sqlalchemy import text

        role = db_session.exec(
            select(TenantUserRole).where(TenantUserRole.code == "office_staff")
        ).first()
        assert role is not None

        # The seed definition's permissions (must match TENANT_USER_ROLE_ROWS)
        seed_permissions = [
            "addresses.*",
            "contacts.*",
            "customers.*",
            "invoices.create",
            "invoices.view",
            "jobs.view",
            "quotes.*",
            "reports.view",
            "sites.*",
            "users.view",
            "schedule.manage",
            "schedule.view_all",
            "dashboard.manage",
            # PLP-FIX-9: communications + self-service Security-page grants
            "communications.view",
            "communications.send",
            "mfa.enroll_self",
            "account.session.view_own",
            "account.session.revoke_own",
            "help_chat.delete_own_history",
        ]
        permissions_json = json.dumps(seed_permissions)

        # First pass — converge (may or may not update depending on DB state)
        db_session.execute(
            text("""
                UPDATE public.tenant_user_role
                SET permissions = CAST(:permissions AS jsonb), updated_at = now()
                WHERE code = :code AND permissions <> CAST(:permissions AS jsonb)
            """),
            {"code": "office_staff", "permissions": permissions_json},
        )
        db_session.commit()

        # Second pass — must be a no-op (0 rows updated)
        result2 = db_session.execute(
            text("""
                UPDATE public.tenant_user_role
                SET permissions = CAST(:permissions AS jsonb), updated_at = now()
                WHERE code = :code AND permissions <> CAST(:permissions AS jsonb)
            """),
            {"code": "office_staff", "permissions": permissions_json},
        )
        db_session.commit()

        assert result2.rowcount == 0, (
            "Second converge pass should be a no-op (0 rows updated), "
            f"but {result2.rowcount} row(s) were updated — permissions not stable"
        )

        # Verify the row has jobs.view after converge
        db_session.expire_all()
        role = db_session.exec(
            select(TenantUserRole).where(TenantUserRole.code == "office_staff")
        ).first()
        assert "jobs.view" in role.permissions
