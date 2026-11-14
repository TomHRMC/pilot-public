"""
E2E-specific fixtures for SD-10 Tier 1 pytest integration tests.

Uses pilot_e2e_db (port 5433) — NEVER the dev DB (pilot_dev on port 5432).
Run with: pytest tests/e2e/ --e2e

All autouse fixtures from tests/conftest.py (mock_cognito_jwks, mock_ai_services,
mock_entitlement_allowed) remain active here — they are declared session-wide.
E2E tests use the test-endpoint pattern (unauthenticated /test routes) so
JWT mocking is not needed for data creation. RBAC tests use mock_jwt_for_user.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

# Ensure backend root is in path (allows: from app.main import app)
backend_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# E2E DB URL — from environment (set in .env.e2e or CI env vars)
E2E_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db",
)


@pytest.fixture(scope="session")
def e2e_engine():
    """
    Session-scoped engine pointing at pilot_e2e_db.
    This is the E2E isolated database — never connects to pilot_dev.
    """
    engine = create_engine(E2E_DATABASE_URL, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def e2e_client(e2e_engine):
    """
    Session-scoped TestClient with the E2E DB injected via dependency override.

    Session scope is correct here: E2E tests do NOT rollback after each test
    (unlike unit tests). E2E tests work against persistent state in pilot_e2e_db.
    Tests must use unique IDs and assert on those IDs (not total counts).
    """
    from app.main import app
    from core.db import get_db

    def override_get_db():
        with Session(e2e_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def e2e_mock_cognito():
    """
    Session-scoped Cognito JWKS mock for E2E tests.
    Mirrors the function-scoped mock_cognito_jwks in conftest.py but session-scoped
    for performance across the E2E session.
    """
    with patch("core.auth.get_jwks") as mock_jwks:
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
        yield mock_jwks


@pytest.fixture(scope="session")
def e2e_mock_entitlement():
    """
    Session-scoped entitlement bypass for E2E tests.
    Prevents 402 Payment Required on subscription-gated endpoints.
    """
    from services.entitlement_service import EntitlementResult

    with patch(
        "services.entitlement_service.get_cached_entitlement",
        return_value=EntitlementResult(is_allowed=True, reason="e2e_bypass"),
    ):
        yield


@pytest.fixture(scope="session")
def e2e_mock_ai():
    """
    Session-scoped AI service mock for E2E tests.
    Prevents real Ollama/Whisper calls — identical to autouse mock_ai_services in conftest.py.
    """
    from unittest.mock import AsyncMock

    patches = [
        patch(
            "services.ai_service.parse_intent",
            new_callable=AsyncMock,
            return_value='{"intent": "unknown", "entities": {}}',
        ),
        patch(
            "services.ai_service.get_embedding",
            new_callable=AsyncMock,
            return_value=[0.0] * 1024,
        ),
        patch(
            "services.ai_service.generate_text_sync",
            return_value="Mock AI response",
        ),
        patch(
            "services.voice_action_router._apply_tone_aware_message",
            side_effect=lambda result, *args, **kwargs: result,
        ),
        patch(
            "services.ai_service.transcribe_audio",
            new_callable=AsyncMock,
            return_value="mock transcription",
        ),
    ]
    started = [p.start() for p in patches]
    yield started
    for p in patches:
        p.stop()


def make_owner_auth_header(e2e_client, mock_cognito_verify) -> dict:
    """
    Helper to build an Authorization header for dev@pilot.local (owner).
    Mutates the mock's return_value to match the seeded test-tenant owner.

    Returns headers dict: {"Authorization": "Bearer mock_token_..."}
    """
    import uuid

    mock_cognito_verify.return_value = {
        "sub": "00000000-0000-0000-0000-000000000002",
        "email": "dev@pilot.local",
    }
    token = f"Bearer mock_token_{uuid.uuid4()}"
    return {"Authorization": token}


def make_tech_auth_header(e2e_client, mock_cognito_verify) -> dict:
    """
    Helper to build an Authorization header for tech@pilot.local (technician).
    The tech user is seeded with ID 00000000-0000-0000-0000-000000000003.
    """
    import uuid

    mock_cognito_verify.return_value = {
        "sub": "00000000-0000-0000-0000-000000000003",
        "email": "tech@pilot.local",
    }
    token = f"Bearer mock_token_{uuid.uuid4()}"
    return {"Authorization": token}
