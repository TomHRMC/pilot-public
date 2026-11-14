"""
MFA-WIRE-1 — MFA error mapping tests (design §F.3, §F.5).

Every §F.3 row asserted through the /test twins by monkeypatching the mock
client to raise each exception. Asserts the RFC 7807 dict shape
(keys type/title/status/detail/code), not just the status.
"""

import pytest

from services.cognito_mfa_client import (
    CognitoMfaError,
    MfaAccessTokenInvalidError,
    MfaSmsRoleNotConfiguredError,
    MockCognitoMfaClient,
    reset_cognito_mfa_client,
)

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


def _patch_client_to_raise(monkeypatch, exc_factory):
    """Replace the cached client with a MockCognitoMfaClient whose
    verify_software_token raises the given exception."""
    client_instance = MockCognitoMfaClient()
    monkeypatch.setattr(
        client_instance,
        "verify_software_token",
        lambda *a, **kw: (_ for _ in ()).throw(exc_factory()),
    )
    import services.cognito_mfa_client as cmc_mod

    monkeypatch.setattr(cmc_mod, "_client_instance", client_instance)


def _assert_rfc7807_shape(detail: dict) -> None:
    """Assert the RFC 7807 Problem Details dict has all required keys."""
    assert "type" in detail
    assert "title" in detail
    assert "status" in detail
    assert "detail" in detail
    assert "code" in detail


class TestMfaErrorMapping:
    def test_401_mfa_access_token_invalid(self, client, monkeypatch):
        reset_cognito_mfa_client()
        _patch_client_to_raise(monkeypatch, MfaAccessTokenInvalidError)
        resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        assert resp.status_code == 401
        detail = resp.json()["detail"]
        assert detail["code"] == "mfa_access_token_invalid"
        _assert_rfc7807_shape(detail)
        reset_cognito_mfa_client()

    def test_400_mfa_code_invalid(self, client):
        reset_cognito_mfa_client()
        resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "000000"},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["code"] == "mfa_code_invalid"
        _assert_rfc7807_shape(detail)

    def test_400_mfa_code_expired(self, client):
        reset_cognito_mfa_client()
        resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "999999"},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["code"] == "mfa_code_expired"
        _assert_rfc7807_shape(detail)

    def test_503_sms_delivery_not_configured(self, client, monkeypatch):
        reset_cognito_mfa_client()
        _patch_client_to_raise(monkeypatch, MfaSmsRoleNotConfiguredError)
        resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert detail["code"] == "sms_delivery_not_configured"
        _assert_rfc7807_shape(detail)
        reset_cognito_mfa_client()

    def test_502_cognito_unavailable(self, client, monkeypatch):
        reset_cognito_mfa_client()
        _patch_client_to_raise(monkeypatch, CognitoMfaError)
        resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert detail["code"] == "cognito_unavailable"
        _assert_rfc7807_shape(detail)
        reset_cognito_mfa_client()

    def test_400_email_mfa_not_available(self, client):
        reset_cognito_mfa_client()
        resp = client.post("/api/v1/users/me/mfa/methods/email/enroll-start/test")
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["code"] == "email_mfa_not_available"
        _assert_rfc7807_shape(detail)

    def test_400_phone_number_required(self, db_session, client):
        reset_cognito_mfa_client()
        from sqlmodel import select

        from app.models.core import User
        from core.test_context import get_test_context

        ctx = get_test_context()
        user = db_session.exec(select(User).where(User.id == ctx.id)).first()
        if user:
            user.phone_number = None
            db_session.add(user)
            db_session.flush()

        resp = client.post("/api/v1/users/me/mfa/methods/sms/enroll-start/test")
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["code"] == "phone_number_required"
        _assert_rfc7807_shape(detail)

    def test_400_phone_number_invalid(self, db_session, client):
        reset_cognito_mfa_client()
        from sqlmodel import select

        from app.models.core import User
        from core.test_context import get_test_context

        ctx = get_test_context()
        user = db_session.exec(select(User).where(User.id == ctx.id)).first()
        if user:
            # 5 digits — not 10, not + prefixed → invalid
            user.phone_number = "12345"
            db_session.add(user)
            db_session.flush()

        resp = client.post("/api/v1/users/me/mfa/methods/sms/enroll-start/test")
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["code"] == "phone_number_invalid"
        _assert_rfc7807_shape(detail)
