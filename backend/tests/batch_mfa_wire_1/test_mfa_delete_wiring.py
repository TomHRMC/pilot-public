"""
MFA-WIRE-1 — MFA delete wiring tests (design §D.3, §F.5).

Tests:
  - Delete disables the factor on the mock (assert the mock's recorded
    preference state).
  - Remaining-method prefer-shift.
  - Cognito failure (monkeypatched raise) → 502 and row retained.
  - 409 last-method guard still fires before any client call.
"""

import uuid

import pytest
from sqlmodel import select

from app.models.platform_setting import PlatformSetting
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


class TestMfaDeleteWiring:
    def test_delete_disables_factor_on_mock(self, db_session, client, monkeypatch):
        reset_cognito_mfa_client()
        ctx = get_test_context()
        # Enroll a TOTP method
        enroll_resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        method_id = enroll_resp.json()["method_id"]

        # Get the mock client instance to inspect its state
        import services.cognito_mfa_client as cmc_mod

        mock_client = cmc_mod._client_instance
        assert isinstance(mock_client, MockCognitoMfaClient)

        # Delete
        del_resp = client.delete(f"/api/v1/users/me/mfa/methods/{method_id}/test")
        assert del_resp.status_code == 204

        # Assert the mock recorded totp_enabled=False
        state = mock_client.get_preference_state("test-mock-access-token")
        assert state.get("totp_enabled") is False

        # Row is gone
        row = db_session.exec(
            select(UserMfaMethod)
            .where(UserMfaMethod.mfa_method_id == uuid.UUID(method_id))
            .where(UserMfaMethod.tenant_id == ctx.tenant_id)
            .where(UserMfaMethod.user_id == ctx.id)
        ).first()
        assert row is None
        reset_cognito_mfa_client()

    def test_delete_remaining_method_prefer_shift(
        self, db_session, client, monkeypatch
    ):
        reset_cognito_mfa_client()
        ctx = get_test_context()
        # Enroll TOTP
        r1 = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        totp_id = r1.json()["method_id"]

        # Enroll SMS (set phone first)
        from app.models.core import User

        user = db_session.exec(select(User).where(User.id == ctx.id)).first()
        if user:
            user.phone_number = "+15551234567"
            db_session.add(user)
            db_session.flush()

        client.post("/api/v1/users/me/mfa/methods/sms/enroll-start/test")
        client.post(
            "/api/v1/users/me/mfa/methods/sms/enroll-confirm/test",
            json={"code": "123456"},
        )
        # Get the mock client instance
        import services.cognito_mfa_client as cmc_mod

        mock_client = cmc_mod._client_instance
        assert isinstance(mock_client, MockCognitoMfaClient)

        # Delete TOTP — SMS should become preferred
        del_resp = client.delete(f"/api/v1/users/me/mfa/methods/{totp_id}/test")
        assert del_resp.status_code == 204

        state = mock_client.get_preference_state("test-mock-access-token")
        # totp disabled, then sms preferred
        assert state.get("totp_enabled") is False
        assert state.get("preferred") == "sms"
        reset_cognito_mfa_client()

    def test_cognito_failure_row_retained(self, db_session, client, monkeypatch):
        reset_cognito_mfa_client()
        ctx = get_test_context()
        # Enroll a method
        enroll_resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        method_id = enroll_resp.json()["method_id"]

        # Monkeypatch the mock client's set_mfa_preference to raise
        client_instance = MockCognitoMfaClient()
        monkeypatch.setattr(
            client_instance,
            "set_mfa_preference",
            lambda *a, **kw: (_ for _ in ()).throw(CognitoMfaError("forced failure")),
        )
        import services.cognito_mfa_client as cmc_mod

        monkeypatch.setattr(cmc_mod, "_client_instance", client_instance)

        # Delete should fail with 502
        del_resp = client.delete(f"/api/v1/users/me/mfa/methods/{method_id}/test")
        assert del_resp.status_code == 502
        assert del_resp.json()["detail"]["code"] == "cognito_unavailable"

        # Row is retained (not deleted)
        row = db_session.exec(
            select(UserMfaMethod)
            .where(UserMfaMethod.mfa_method_id == uuid.UUID(method_id))
            .where(UserMfaMethod.tenant_id == ctx.tenant_id)
            .where(UserMfaMethod.user_id == ctx.id)
        ).first()
        assert row is not None
        reset_cognito_mfa_client()

    def test_409_last_method_guard_fires_before_client_call(
        self, db_session, client, monkeypatch
    ):
        reset_cognito_mfa_client()
        ctx = get_test_context()
        # Enable MFA policy
        existing = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "tenant_mfa_required")
            .where(PlatformSetting.tenant_id == ctx.tenant_id)
        ).first()
        if existing:
            existing.value = True
        else:
            existing = PlatformSetting(
                key="tenant_mfa_required", value=True, tenant_id=ctx.tenant_id
            )
        db_session.add(existing)
        db_session.commit()

        # Enroll one method
        enroll_resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        method_id = enroll_resp.json()["method_id"]

        # Monkeypatch set_mfa_preference to track if it was called
        client_instance = MockCognitoMfaClient()
        call_count = {"n": 0}

        def _counting_set_mfa_preference(*a, **kw):
            call_count["n"] += 1

        monkeypatch.setattr(
            client_instance, "set_mfa_preference", _counting_set_mfa_preference
        )
        import services.cognito_mfa_client as cmc_mod

        monkeypatch.setattr(cmc_mod, "_client_instance", client_instance)

        # Delete should fail with 409
        del_resp = client.delete(f"/api/v1/users/me/mfa/methods/{method_id}/test")
        assert del_resp.status_code == 409
        assert del_resp.json()["detail"]["code"] == "last_method_required"

        # set_mfa_preference was NOT called (guard fires before client)
        assert call_count["n"] == 0
        reset_cognito_mfa_client()
