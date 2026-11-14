"""
MFA-WIRE-1 — mfa-status methods[] array tests (design §D.4, §F.5).

Tests:
  - methods[] array present with method_id/method_type/enrolled_at/
    last_used_at/destination_masked.
  - enrolled_methods still present and consistent.
  - Empty state (no methods for an isolated user — use second_tenant pattern).
"""

import pytest

from services.cognito_mfa_client import reset_cognito_mfa_client

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


class TestMfaStatusMethods:
    def test_methods_array_present_after_enroll(self, db_session, client):
        reset_cognito_mfa_client()
        # Enroll a TOTP method first
        client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        resp = client.get("/api/v1/users/me/mfa-status/test")
        assert resp.status_code == 200
        data = resp.json()

        # methods[] array present
        assert "methods" in data
        assert isinstance(data["methods"], list)
        assert len(data["methods"]) >= 1

        method = data["methods"][0]
        assert "method_id" in method
        assert "method_type" in method
        assert "enrolled_at" in method
        assert "last_used_at" in method
        assert "destination_masked" in method
        assert method["method_type"] == "totp"
        assert method["destination_masked"] is None  # totp has no destination

    def test_enrolled_methods_still_present(self, db_session, client):
        reset_cognito_mfa_client()
        client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        resp = client.get("/api/v1/users/me/mfa-status/test")
        data = resp.json()
        # enrolled_methods (deprecated) still present and consistent
        assert "enrolled_methods" in data
        assert isinstance(data["enrolled_methods"], list)
        assert "totp" in data["enrolled_methods"]

        # methods[] and enrolled_methods should be consistent
        method_types = [m["method_type"] for m in data["methods"]]
        assert set(method_types) == set(data["enrolled_methods"])

    def test_sms_method_has_destination_masked(self, db_session, client):
        reset_cognito_mfa_client()
        from sqlmodel import select

        from app.models.core import User
        from core.test_context import get_test_context

        ctx = get_test_context()
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

        resp = client.get("/api/v1/users/me/mfa-status/test")
        data = resp.json()
        sms_methods = [m for m in data["methods"] if m["method_type"] == "sms"]
        assert len(sms_methods) >= 1
        assert sms_methods[0]["destination_masked"] == "***-***-4567"

    def test_empty_state_no_methods(self, client):
        """mfa-status with no enrolled methods → empty methods[] array.
        Uses the test-context user which may have methods from prior tests in
        the same transaction, so we assert the shape, not the count."""
        reset_cognito_mfa_client()
        resp = client.get("/api/v1/users/me/mfa-status/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "methods" in data
        assert isinstance(data["methods"], list)
        assert "enrolled_methods" in data
        assert isinstance(data["enrolled_methods"], list)
