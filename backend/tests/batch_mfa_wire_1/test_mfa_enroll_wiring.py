"""
MFA-WIRE-1 — MFA enroll wiring end-to-end on the mock (design §F.5).

Tests:
  - TOTP enroll-start returns otpauth:// URI + secret.
  - Confirm 201 writes row with cognito_method_id="totp:software-token".
  - SMS full path with phone set.
  - No-DB-write invariant: force a client failure → zero user_mfa_method rows
    for the test user (scoped select, not a count-all).
  - Replay: second confirm → 200 same method_id, still exactly one row.
"""

import pytest
from sqlmodel import select

from app.models.core import User
from app.models.security import UserMfaMethod
from core.test_context import get_test_context
from services.cognito_mfa_client import (
    CognitoMfaError,
    MockCognitoMfaClient,
    reset_cognito_mfa_client,
)

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


def _set_test_user_phone(db_session, phone: str | None) -> None:
    ctx = get_test_context()
    user = db_session.exec(select(User).where(User.id == ctx.id)).first()
    if user:
        user.phone_number = phone
        db_session.add(user)
        db_session.flush()


class TestMfaEnrollWiring:
    def test_totp_enroll_start_returns_otpauth_uri(self, client):
        reset_cognito_mfa_client()
        resp = client.post("/api/v1/users/me/mfa/methods/totp/enroll-start/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "otpauth://" in data["qr_code_uri"]
        assert "PilotForTrades" in data["qr_code_uri"]
        assert data["secret"]

    def test_totp_confirm_writes_real_cognito_method_id(self, db_session, client):
        reset_cognito_mfa_client()
        ctx = get_test_context()
        resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        assert resp.status_code == 201
        method_id = resp.json()["method_id"]

        row = db_session.exec(
            select(UserMfaMethod)
            .where(UserMfaMethod.mfa_method_id == method_id)
            .where(UserMfaMethod.tenant_id == ctx.tenant_id)
            .where(UserMfaMethod.user_id == ctx.id)
        ).first()
        assert row is not None
        assert row.cognito_method_id == "totp:software-token"
        assert row.verification_status == "verified"

    def test_sms_full_path_with_phone(self, db_session, client):
        reset_cognito_mfa_client()
        ctx = get_test_context()
        _set_test_user_phone(db_session, "+15551234567")

        # enroll-start
        start_resp = client.post("/api/v1/users/me/mfa/methods/sms/enroll-start/test")
        assert start_resp.status_code == 200
        assert start_resp.json()["destination_masked"] == "***-***-4567"

        # enroll-confirm
        confirm_resp = client.post(
            "/api/v1/users/me/mfa/methods/sms/enroll-confirm/test",
            json={"code": "123456"},
        )
        assert confirm_resp.status_code == 201
        method_id = confirm_resp.json()["method_id"]

        row = db_session.exec(
            select(UserMfaMethod)
            .where(UserMfaMethod.mfa_method_id == method_id)
            .where(UserMfaMethod.tenant_id == ctx.tenant_id)
            .where(UserMfaMethod.user_id == ctx.id)
        ).first()
        assert row is not None
        assert row.cognito_method_id == "sms:phone_number"
        assert row.method_metadata == {"destination_last4": "4567"}

    def test_no_db_write_on_cognito_failure(self, db_session, client, monkeypatch):
        """The anti-mock guarantee: a Cognito failure ⇒ zero DB writes."""
        reset_cognito_mfa_client()
        ctx = get_test_context()

        # Monkeypatch the mock client's verify_software_token to raise
        client_instance = MockCognitoMfaClient()
        monkeypatch.setattr(
            client_instance,
            "verify_software_token",
            lambda *a, **kw: (_ for _ in ()).throw(CognitoMfaError("forced failure")),
        )
        import services.cognito_mfa_client as cmc_mod

        monkeypatch.setattr(cmc_mod, "_client_instance", client_instance)

        resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        assert resp.status_code == 502
        assert resp.json()["detail"]["code"] == "cognito_unavailable"

        # Assert zero rows for this test user + method_type
        rows = db_session.exec(
            select(UserMfaMethod)
            .where(UserMfaMethod.tenant_id == ctx.tenant_id)
            .where(UserMfaMethod.user_id == ctx.id)
            .where(UserMfaMethod.method_type == "totp")
        ).all()
        assert len(rows) == 0
        reset_cognito_mfa_client()

    def test_replay_second_confirm_returns_200_same_id(self, db_session, client):
        reset_cognito_mfa_client()
        ctx = get_test_context()
        resp1 = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        assert resp1.status_code == 201
        method_id_1 = resp1.json()["method_id"]

        resp2 = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "654321"},
        )
        assert resp2.status_code == 200
        method_id_2 = resp2.json()["method_id"]
        assert method_id_1 == method_id_2

        # Still exactly one row for (tenant, user, type)
        rows = db_session.exec(
            select(UserMfaMethod)
            .where(UserMfaMethod.tenant_id == ctx.tenant_id)
            .where(UserMfaMethod.user_id == ctx.id)
            .where(UserMfaMethod.method_type == "totp")
        ).all()
        assert len(rows) == 1
