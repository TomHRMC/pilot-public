import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.auth import TenantUser
from app.models.core import Tenant, User, UserEndpoint


def test_signup_success(client: TestClient, db_session: Session):
    # Setup test data with unique email for this test
    test_email = f"newuser{uuid.uuid4()}@example.com"
    test_tenant_name = f"Test Tenant {uuid.uuid4()}"
    test_first_name = "Jane"
    test_last_name = "Doe"

    payload = {
        "tenant_name": test_tenant_name,
        "first_name": test_first_name,
        "last_name": test_last_name,
    }

    # Mock JWT verification to return unique email
    with (
        patch("core.auth.verify_cognito_jwt") as mock_verify_core,
        patch("api.routes.auth.verify_cognito_jwt") as mock_verify_api,
        patch("core.auth.get_jwks") as mock_jwks,
    ):
        mock_verify_core.return_value = {
            "sub": str(uuid.uuid4()),
            "email": test_email,
        }
        mock_verify_api.return_value = {
            "sub": str(uuid.uuid4()),
            "email": test_email,
        }
        mock_jwks.return_value = {
            "keys": [
                {
                    "alg": "RS256",
                    "e": "AQAB",
                    "kid": "test_kid",
                    "kty": "RSA",
                    "n": "test_n",
                    "use": "sig",
                }
            ]
        }

        headers = {"Authorization": "Bearer dummy_test_token_12345"}
        response = client.post("/api/v1/auth/signup", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert "user_id" in data
    assert "tenant_id" in data
    assert data["message"] == "Signup successful"

    user_id = uuid.UUID(data["user_id"])
    tenant_id = uuid.UUID(data["tenant_id"])

    # Verify in database
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    assert user is not None
    assert user.email == test_email
    assert user.first_name == test_first_name
    assert user.last_name == test_last_name

    tenant = db_session.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    assert tenant is not None
    assert tenant.name == test_tenant_name

    endpoint = db_session.exec(
        select(UserEndpoint).where(UserEndpoint.user_id == user_id)
    ).first()
    assert endpoint is not None
    assert endpoint.channel == "email"
    assert endpoint.value == test_email
    assert endpoint.is_primary is True

    tenant_user = db_session.exec(
        select(TenantUser)
        .where(TenantUser.tenant_id == tenant_id)
        .where(TenantUser.user_id == user_id)
    ).first()
    assert tenant_user is not None
    assert tenant_user.role_code == "owner"


def test_signup_existing_user(client: TestClient, db_session: Session, test_user):
    # Use the test_user fixture which already exists in the test DB.
    # Email aligned with seed_test_tenant.py → dev@pilot.local (previously test@pilot.local).
    test_email = "dev@pilot.local"

    payload = {"tenant_name": f"Test Tenant {uuid.uuid4()}"}

    # Mock JWT to return email of existing user
    with (
        patch("core.auth.verify_cognito_jwt") as mock_verify_core,
        patch("api.routes.auth.verify_cognito_jwt") as mock_verify_api,
        patch("core.auth.get_jwks") as mock_jwks,
    ):
        mock_verify_core.return_value = {
            "sub": "00000000-0000-0000-0000-000000000002",
            "email": test_email,  # dev@pilot.local — matches seeded user
        }
        mock_verify_api.return_value = {
            "sub": "00000000-0000-0000-0000-000000000002",
            "email": test_email,  # dev@pilot.local — matches seeded user
        }
        mock_jwks.return_value = {
            "keys": [
                {
                    "alg": "RS256",
                    "e": "AQAB",
                    "kid": "test_kid",
                    "kty": "RSA",
                    "n": "test_n",
                    "use": "sig",
                }
            ]
        }

        headers = {"Authorization": "Bearer dummy_test_token_12345"}
        response = client.post("/api/v1/auth/signup", json=payload, headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists"


def test_signup_duplicate_tenant_name_allowed(client: TestClient, db_session: Session):
    """
    ADR-0012 / G6: the tenant.name uniqueness pre-check was removed.
    Two signups with the same tenant_name must both succeed (the
    tenant_name_key constraint is dropped). Email must still be unique.
    """
    test_tenant_name = f"Duplicate Co {uuid.uuid4()}"
    test_email_a = f"uniqueuser-a-{uuid.uuid4()}@example.com"
    test_email_b = f"uniqueuser-b-{uuid.uuid4()}@example.com"

    payload_a = {"tenant_name": test_tenant_name, "first_name": "A", "last_name": "B"}
    payload_b = {"tenant_name": test_tenant_name, "first_name": "C", "last_name": "D"}

    # First signup with the name — should succeed
    with (
        patch("core.auth.verify_cognito_jwt") as mock_verify_core,
        patch("api.routes.auth.verify_cognito_jwt") as mock_verify_api,
        patch("core.auth.get_jwks") as mock_jwks,
    ):
        mock_verify_core.return_value = {
            "sub": str(uuid.uuid4()),
            "email": test_email_a,
        }
        mock_verify_api.return_value = {"sub": str(uuid.uuid4()), "email": test_email_a}
        mock_jwks.return_value = {
            "keys": [
                {
                    "alg": "RS256",
                    "e": "AQAB",
                    "kid": "test_kid",
                    "kty": "RSA",
                    "n": "test_n",
                    "use": "sig",
                }
            ]
        }
        headers = {"Authorization": "Bearer dummy_test_token_12345"}
        response_a = client.post("/api/v1/auth/signup", json=payload_a, headers=headers)

    assert response_a.status_code == 201

    # Second signup with the SAME name but a different email — must also
    # succeed (duplicate tenant names are now allowed; ADR-0012).
    with (
        patch("core.auth.verify_cognito_jwt") as mock_verify_core,
        patch("api.routes.auth.verify_cognito_jwt") as mock_verify_api,
        patch("core.auth.get_jwks") as mock_jwks,
    ):
        mock_verify_core.return_value = {
            "sub": str(uuid.uuid4()),
            "email": test_email_b,
        }
        mock_verify_api.return_value = {"sub": str(uuid.uuid4()), "email": test_email_b}
        mock_jwks.return_value = {
            "keys": [
                {
                    "alg": "RS256",
                    "e": "AQAB",
                    "kid": "test_kid",
                    "kty": "RSA",
                    "n": "test_n",
                    "use": "sig",
                }
            ]
        }
        headers = {"Authorization": "Bearer dummy_test_token_12345"}
        response_b = client.post("/api/v1/auth/signup", json=payload_b, headers=headers)

    assert response_b.status_code == 201
    assert response_a.json()["tenant_id"] != response_b.json()["tenant_id"]
