"""
Batch 1-A-3: RBAC Permission Decorator Coverage Sweep — New Coverage Tests

Verifies that the three routes fixed in Task 1-A-3 now correctly gate access:

1. GET /api/v1/audit/summary          → requires audit.view   (was bare get_current_user)
2. POST /api/v1/catalog/supplier-items → requires catalog.create (was bare get_current_user)
3. GET  /api/v1/catalog/supplier-items → requires catalog.view  (was bare get_current_user)
4. GET  /api/v1/catalog/pricing-cache  → requires catalog.view  (was bare get_current_user)
5. POST /api/v1/voice/command          → requires voice.use    (was bare get_current_user)

Each test group has two paths:
  - A role missing the required permission → must receive 403 Forbidden
  - An authorised role (owner has wildcard *)  → must pass the permission gate

Security specification:
  - Technician-role users MUST NOT access audit/summary, catalog write, or catalog read
  - Technician-role users MUST be permitted to use voice commands (voice.use is seeded on technician)
  - Owner-role users (wildcard) MUST pass all gates
  - A role with empty permissions MUST NOT access voice commands
"""

import uuid
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.auth import TenantUser, TenantUserRole, TenantUserStatus
from app.models.core import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user_with_role(
    db_session: Session,
    tenant_id: uuid.UUID,
    role_code: str,
    email: str,
) -> User:
    """
    Create a User + TenantUser linked to the given tenant / role.

    The role must already exist in the DB (seeded by migrations).
    Returns the User so its id can be used to configure mock JWT verification.
    """
    user = User(
        id=uuid.uuid4(),
        email=email,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.flush()

    # Fetch or create status
    status = db_session.exec(
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
        db_session.add(status)
        db_session.flush()

    tenant_user = TenantUser(
        tenant_id=tenant_id,
        user_id=user.id,
        role_code=role_code,
        status_id=status.id,
        is_active=True,
        joined_at=datetime.now(UTC),
    )
    db_session.add(tenant_user)
    db_session.commit()

    return user


def _auth_headers(user: User) -> dict:
    """Return a minimal Authorization header for the test client."""
    return {"Authorization": f"Bearer test_token_{user.id}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant(db_session: Session):
    from app.models.core import Tenant

    t = Tenant(id=uuid.uuid4(), name=f"RBAC Sweep Test {uuid.uuid4()}", is_active=True)
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def technician(db_session: Session, tenant):
    return _make_user_with_role(
        db_session,
        tenant.id,
        "technician",
        f"tech_{uuid.uuid4().hex[:8]}@rbac-sweep.test",
    )


@pytest.fixture
def owner(db_session: Session, tenant):
    return _make_user_with_role(
        db_session,
        tenant.id,
        "owner",
        f"owner_{uuid.uuid4().hex[:8]}@rbac-sweep.test",
    )


@pytest.fixture
def accountant(db_session: Session, tenant):
    return _make_user_with_role(
        db_session,
        tenant.id,
        "accountant",
        f"acct_{uuid.uuid4().hex[:8]}@rbac-sweep.test",
    )


# ---------------------------------------------------------------------------
# Group 1 — Audit Summary  (GET /api/v1/audit/summary)
# ---------------------------------------------------------------------------


class TestAuditSummaryRBAC:
    """
    GET /audit/summary must require audit.view.
    Technician role does not hold audit.view → must receive 403.
    Accountant role holds audit.view → must pass the permission gate.
    """

    def test_technician_denied_audit_summary(
        self,
        client: TestClient,
        db_session: Session,
        technician: User,
        mock_cognito_jwt_verify,
    ):
        """Technician role is denied access to GET /audit/summary (403)."""
        mock_cognito_jwt_verify.return_value = {
            "sub": str(technician.id),
            "email": technician.email,
        }
        response = client.get(
            "/api/v1/audit/summary", headers=_auth_headers(technician)
        )
        assert response.status_code == 403, (
            f"Expected 403 Forbidden for technician on audit/summary, got {response.status_code}: "
            f"{response.text}"
        )
        body = response.json()
        assert body["detail"]["status"] == 403
        assert body["detail"]["required_permission"] == "audit.view"

    def test_accountant_permitted_audit_summary(
        self,
        client: TestClient,
        db_session: Session,
        accountant: User,
        mock_cognito_jwt_verify,
    ):
        """Accountant role passes the audit.view gate (not 403)."""
        mock_cognito_jwt_verify.return_value = {
            "sub": str(accountant.id),
            "email": accountant.email,
        }
        response = client.get(
            "/api/v1/audit/summary", headers=_auth_headers(accountant)
        )
        # May be 200 (results found) or 200 with empty result — must NOT be 403
        assert response.status_code != 403, (
            f"Accountant should not be denied audit/summary, got 403: {response.text}"
        )

    def test_owner_permitted_audit_summary(
        self,
        client: TestClient,
        db_session: Session,
        owner: User,
        mock_cognito_jwt_verify,
    ):
        """Owner role (wildcard *) passes the audit.view gate."""
        mock_cognito_jwt_verify.return_value = {
            "sub": str(owner.id),
            "email": owner.email,
        }
        response = client.get("/api/v1/audit/summary", headers=_auth_headers(owner))
        assert response.status_code != 403, (
            f"Owner should not be denied audit/summary, got 403: {response.text}"
        )


# ---------------------------------------------------------------------------
# Group 2 — Catalog Routes  (supplier-items + pricing-cache)
# ---------------------------------------------------------------------------


class TestCatalogRBAC:
    """
    catalog.create / catalog.view permissions now guard the catalog endpoints.
    Technician role does not hold these → must receive 403.
    Owner role (wildcard) passes all catalog gates.
    """

    def test_technician_denied_create_supplier_item(
        self,
        client: TestClient,
        db_session: Session,
        technician: User,
        mock_cognito_jwt_verify,
    ):
        """Technician cannot POST to /catalog/supplier-items (403)."""
        mock_cognito_jwt_verify.return_value = {
            "sub": str(technician.id),
            "email": technician.email,
        }
        payload = {
            "supplier_id": str(uuid.uuid4()),
            "sku": "WIRE-12-2",
            "name": "12/2 NM-B Wire",
        }
        response = client.post(
            "/api/v1/catalog/supplier-items",
            json=payload,
            headers=_auth_headers(technician),
        )
        assert response.status_code == 403, (
            f"Expected 403 for technician on catalog/supplier-items POST, got {response.status_code}: "
            f"{response.text}"
        )
        body = response.json()
        assert body["detail"]["required_permission"] == "catalog.create"

    def test_owner_permitted_create_supplier_item(
        self,
        client: TestClient,
        db_session: Session,
        owner: User,
        mock_cognito_jwt_verify,
    ):
        """Owner passes the catalog.create gate (not 403)."""
        mock_cognito_jwt_verify.return_value = {
            "sub": str(owner.id),
            "email": owner.email,
        }
        payload = {
            "supplier_id": str(uuid.uuid4()),
            "sku": "WIRE-12-2",
            "name": "12/2 NM-B Wire",
        }
        response = client.post(
            "/api/v1/catalog/supplier-items",
            json=payload,
            headers=_auth_headers(owner),
        )
        # Passes permission gate — may be 201 or 422 (validation), not 403
        assert response.status_code != 403, (
            f"Owner should not be denied catalog/supplier-items POST, got 403: {response.text}"
        )

    def test_technician_denied_list_supplier_items(
        self,
        client: TestClient,
        db_session: Session,
        technician: User,
        mock_cognito_jwt_verify,
    ):
        """Technician cannot GET /catalog/supplier-items (403)."""
        mock_cognito_jwt_verify.return_value = {
            "sub": str(technician.id),
            "email": technician.email,
        }
        response = client.get(
            "/api/v1/catalog/supplier-items", headers=_auth_headers(technician)
        )
        assert response.status_code == 403, (
            f"Expected 403 for technician on catalog/supplier-items GET, got {response.status_code}: "
            f"{response.text}"
        )
        body = response.json()
        assert body["detail"]["required_permission"] == "catalog.view"

    def test_owner_permitted_list_supplier_items(
        self,
        client: TestClient,
        db_session: Session,
        owner: User,
        mock_cognito_jwt_verify,
    ):
        """Owner passes the catalog.view gate on GET /catalog/supplier-items."""
        mock_cognito_jwt_verify.return_value = {
            "sub": str(owner.id),
            "email": owner.email,
        }
        response = client.get(
            "/api/v1/catalog/supplier-items", headers=_auth_headers(owner)
        )
        assert response.status_code != 403, (
            f"Owner should not be denied catalog/supplier-items GET, got 403: {response.text}"
        )

    def test_technician_denied_pricing_cache(
        self,
        client: TestClient,
        db_session: Session,
        technician: User,
        mock_cognito_jwt_verify,
    ):
        """Technician cannot GET /catalog/pricing-cache (403)."""
        mock_cognito_jwt_verify.return_value = {
            "sub": str(technician.id),
            "email": technician.email,
        }
        response = client.get(
            "/api/v1/catalog/pricing-cache", headers=_auth_headers(technician)
        )
        assert response.status_code == 403, (
            f"Expected 403 for technician on catalog/pricing-cache GET, got {response.status_code}: "
            f"{response.text}"
        )
        body = response.json()
        assert body["detail"]["required_permission"] == "catalog.view"

    def test_owner_permitted_pricing_cache(
        self,
        client: TestClient,
        db_session: Session,
        owner: User,
        mock_cognito_jwt_verify,
    ):
        """Owner passes the catalog.view gate on GET /catalog/pricing-cache."""
        mock_cognito_jwt_verify.return_value = {
            "sub": str(owner.id),
            "email": owner.email,
        }
        response = client.get(
            "/api/v1/catalog/pricing-cache", headers=_auth_headers(owner)
        )
        assert response.status_code != 403, (
            f"Owner should not be denied catalog/pricing-cache GET, got 403: {response.text}"
        )


# ---------------------------------------------------------------------------
# Group 3 — Voice Command  (POST /api/v1/voice/command)
# ---------------------------------------------------------------------------


class TestVoiceCommandRBAC:
    """
    POST /voice/command must now require voice.create.
    Technician role DOES hold voice.create, so it passes.
    A role with no permissions should receive 403.
    """

    def test_no_permission_role_denied_voice_command(
        self,
        client: TestClient,
        db_session: Session,
        tenant,
        mock_cognito_jwt_verify,
    ):
        """A user with an empty permission set cannot POST to /voice/command (403)."""
        # Create a custom role with zero permissions to verify the gate fires
        restricted_role = TenantUserRole(
            code=f"no_perm_{uuid.uuid4().hex[:6]}",
            name="No Permissions Role",
            permissions=[],  # Empty — no voice.create
            is_default=False,
            is_active=True,
        )
        db_session.add(restricted_role)
        db_session.flush()

        restricted_user = _make_user_with_role(
            db_session,
            tenant.id,
            restricted_role.code,
            f"noperm_{uuid.uuid4().hex[:8]}@rbac-sweep.test",
        )

        mock_cognito_jwt_verify.return_value = {
            "sub": str(restricted_user.id),
            "email": restricted_user.email,
        }

        dummy_audio = BytesIO(b"RIFF....WAVEfmt ")
        response = client.post(
            "/api/v1/voice/command",
            files={"audio": ("test.wav", dummy_audio, "audio/wav")},
            headers=_auth_headers(restricted_user),
        )
        assert response.status_code == 403, (
            f"Expected 403 for no-permission role on voice/command, got {response.status_code}: "
            f"{response.text}"
        )
        body = response.json()
        assert body["detail"]["required_permission"] == "voice.use"

    def test_technician_permitted_voice_command(
        self,
        client: TestClient,
        db_session: Session,
        technician: User,
        mock_cognito_jwt_verify,
    ):
        """
        Technician role holds voice.create and must pass the permission gate.
        We mock the AI services so the endpoint doesn't require live Whisper/Ollama.
        Expect anything other than 403 (likely 200).
        """
        mock_cognito_jwt_verify.return_value = {
            "sub": str(technician.id),
            "email": technician.email,
        }

        with (
            patch(
                "api.routes.voice.transcribe_audio",
                new_callable=AsyncMock,
                return_value="Add 10 panels to the quote",
            ),
            patch(
                "api.routes.voice.get_embedding",
                new_callable=AsyncMock,
                return_value=[0.1] * 1024,
            ),
            patch(
                "api.routes.voice.parse_intent",
                new_callable=AsyncMock,
                return_value='{"intent": "add_quote_line", "entities": {}}',
            ),
        ):
            dummy_audio = BytesIO(b"RIFF....WAVEfmt ")
            response = client.post(
                "/api/v1/voice/command",
                files={"audio": ("test.wav", dummy_audio, "audio/wav")},
                headers=_auth_headers(technician),
            )

        assert response.status_code != 403, (
            f"Technician (voice.create) should not be denied /voice/command, "
            f"got 403: {response.text}"
        )

    def test_owner_permitted_voice_command(
        self,
        client: TestClient,
        db_session: Session,
        owner: User,
        mock_cognito_jwt_verify,
    ):
        """
        Owner wildcard (*) must pass the voice.create gate.
        """
        mock_cognito_jwt_verify.return_value = {
            "sub": str(owner.id),
            "email": owner.email,
        }

        with (
            patch(
                "api.routes.voice.transcribe_audio",
                new_callable=AsyncMock,
                return_value="Create a new quote for Mike",
            ),
            patch(
                "api.routes.voice.get_embedding",
                new_callable=AsyncMock,
                return_value=[0.1] * 1024,
            ),
            patch(
                "api.routes.voice.parse_intent",
                new_callable=AsyncMock,
                return_value='{"intent": "create_quote", "entities": {}}',
            ),
        ):
            dummy_audio = BytesIO(b"RIFF....WAVEfmt ")
            response = client.post(
                "/api/v1/voice/command",
                files={"audio": ("test.wav", dummy_audio, "audio/wav")},
                headers=_auth_headers(owner),
            )

        assert response.status_code != 403, (
            f"Owner (wildcard) should not be denied /voice/command, got 403: {response.text}"
        )
