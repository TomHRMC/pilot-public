"""
B13/A69 — MFA Enrollment & Recovery Code Tests (MFA-WIRE-1 reworked).

Test focus (reworked onto MockCognitoMfaClient semantics):
- POST /me/mfa/methods/totp/enroll-start/test returns qr_code_uri and secret
- POST /me/mfa/methods/sms/enroll-start/test returns destination_masked (phone set)
- POST /me/mfa/methods/email/enroll-start/test → 400 email_mfa_not_available
- POST /me/mfa/methods/totp/enroll-confirm/test creates UserMfaMethod row
  with cognito_method_id == "totp:software-token"
- Re-enrolling same method type → 200 (replay matrix), still one row
- Code "000000" → 400 mfa_code_invalid; "999999" → 400 mfa_code_expired
- DELETE /me/mfa/methods/{method_id}/test removes the method
- DELETE blocks deletion of last method when tenant_mfa_required=True (409)
- POST /me/mfa/recovery-codes/generate/test generates 10 codes
- GET /me/mfa/recovery-codes/status/test returns unused count
- Invalid method_type returns 400
"""

import uuid

import pytest
from sqlmodel import select

from app.models.core import User
from app.models.platform_setting import PlatformSetting
from app.models.security import UserMfaMethod
from core.test_context import get_test_context
from services.cognito_mfa_client import reset_cognito_mfa_client

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


def _set_test_user_phone(db_session, phone: str | None) -> None:
    """Set phone_number on the shared test-context user inside the db_session
    transaction (rolls back with the fixture). Permitted exception per the
    MFA-WIRE-1 test-resilience rules."""
    ctx = get_test_context()
    user = db_session.exec(select(User).where(User.id == ctx.id)).first()
    if user:
        user.phone_number = phone
        db_session.add(user)
        db_session.flush()


class TestMfaEnrollStart:
    def test_totp_returns_qr_code_uri(self, client):
        reset_cognito_mfa_client()
        resp = client.post("/api/v1/users/me/mfa/methods/totp/enroll-start/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["method_type"] == "totp"
        assert "otpauth://" in data["qr_code_uri"]
        assert "secret" in data
        assert data["secret"]  # non-empty (mock fixed secret)

    def test_sms_returns_destination_masked(self, db_session, client):
        reset_cognito_mfa_client()
        _set_test_user_phone(db_session, "+15551234567")
        resp = client.post("/api/v1/users/me/mfa/methods/sms/enroll-start/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["method_type"] == "sms"
        assert "destination_masked" in data
        assert data["destination_masked"] == "***-***-4567"

    def test_sms_phone_null_returns_400(self, db_session, client):
        reset_cognito_mfa_client()
        _set_test_user_phone(db_session, None)
        resp = client.post("/api/v1/users/me/mfa/methods/sms/enroll-start/test")
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "phone_number_required"

    def test_email_returns_400_not_available(self, client):
        reset_cognito_mfa_client()
        resp = client.post("/api/v1/users/me/mfa/methods/email/enroll-start/test")
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "email_mfa_not_available"

    def test_invalid_method_type_returns_400(self, client):
        reset_cognito_mfa_client()
        resp = client.post("/api/v1/users/me/mfa/methods/fax/enroll-start/test")
        assert resp.status_code == 400


class TestMfaEnrollConfirm:
    def test_creates_mfa_method_row(self, db_session, client):
        reset_cognito_mfa_client()
        resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "method_id" in data
        assert "enrolled_at" in data

        # Verify the row has the real cognito_method_id (not mock-cognito-...)
        ctx = get_test_context()
        row = db_session.exec(
            select(UserMfaMethod)
            .where(UserMfaMethod.tenant_id == ctx.tenant_id)
            .where(UserMfaMethod.user_id == ctx.id)
            .where(UserMfaMethod.method_type == "totp")
        ).first()
        assert row is not None
        assert row.cognito_method_id == "totp:software-token"

    def test_no_duplicate_on_reenroll(self, db_session, client):
        reset_cognito_mfa_client()
        ctx = get_test_context()
        client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        # Second confirm → 200 (replay matrix), same row
        resp2 = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "654321"},
        )
        assert resp2.status_code == 200
        methods = db_session.exec(
            select(UserMfaMethod)
            .where(UserMfaMethod.tenant_id == ctx.tenant_id)
            .where(UserMfaMethod.user_id == ctx.id)
            .where(UserMfaMethod.method_type == "totp")
        ).all()
        assert len(methods) == 1

    def test_code_mismatch_returns_400(self, client):
        reset_cognito_mfa_client()
        resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "000000"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "mfa_code_invalid"

    def test_code_expired_returns_400(self, client):
        reset_cognito_mfa_client()
        resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "999999"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "mfa_code_expired"


class TestMfaMethodDelete:
    def test_delete_method(self, db_session, client):
        reset_cognito_mfa_client()
        # Enroll first
        enroll_resp = client.post(
            "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
            json={"code": "123456"},
        )
        method_id = enroll_resp.json()["method_id"]

        del_resp = client.delete(f"/api/v1/users/me/mfa/methods/{method_id}/test")
        assert del_resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, client):
        reset_cognito_mfa_client()
        resp = client.delete(f"/api/v1/users/me/mfa/methods/{uuid.uuid4()}/test")
        assert resp.status_code == 404

    def test_delete_last_method_blocked_when_required(self, db_session, client):
        reset_cognito_mfa_client()
        ctx = get_test_context()
        # Enable MFA policy via platform_setting (FIND-086)
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

        # Try to delete — should fail with 409
        del_resp = client.delete(f"/api/v1/users/me/mfa/methods/{method_id}/test")
        assert del_resp.status_code == 409
        assert del_resp.json()["detail"]["code"] == "last_method_required"


class TestMfaRecoveryCodes:
    def test_generate_creates_10_codes(self, db_session, client):
        resp = client.post("/api/v1/users/me/mfa/recovery-codes/generate/test")
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["codes"]) == 10
        assert "set_id" in data

    def test_codes_are_unique(self, client):
        resp = client.post("/api/v1/users/me/mfa/recovery-codes/generate/test")
        codes = resp.json()["codes"]
        assert len(codes) == len(set(codes))

    def test_status_returns_unused_count(self, db_session, client):
        client.post("/api/v1/users/me/mfa/recovery-codes/generate/test")
        resp = client.get("/api/v1/users/me/mfa/recovery-codes/status/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["unused_code_count"] == 10
        assert data["last_generated_at"] is not None

    def test_status_returns_zero_initially(self, client):
        resp = client.get("/api/v1/users/me/mfa/recovery-codes/status/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["unused_code_count"] == 0
        assert data["last_generated_at"] is None
