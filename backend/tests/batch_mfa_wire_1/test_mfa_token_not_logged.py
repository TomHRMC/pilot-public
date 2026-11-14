"""
MFA-WIRE-1 — Access token not-logged test (design §E, §F.5).

caplog over a full enroll-start→confirm→delete cycle: assert the access-token
sentinel string appears in ZERO log records.
"""

import logging

import pytest

from services.cognito_mfa_client import reset_cognito_mfa_client

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]

SENTINEL = "test-mock-access-token"


class TestMfaTokenNotLogged:
    def test_access_token_never_logged(self, db_session, client, caplog):
        reset_cognito_mfa_client()

        # Capture ALL log records at ALL levels from ALL loggers
        with caplog.at_level(logging.DEBUG, logger=""):
            # enroll-start
            client.post("/api/v1/users/me/mfa/methods/totp/enroll-start/test")
            # enroll-confirm
            client.post(
                "/api/v1/users/me/mfa/methods/totp/enroll-confirm/test",
                json={"code": "123456"},
            )
            # Get the method_id and delete
            from sqlmodel import select

            from app.models.security import UserMfaMethod
            from core.test_context import get_test_context

            ctx = get_test_context()
            row = db_session.exec(
                select(UserMfaMethod)
                .where(UserMfaMethod.tenant_id == ctx.tenant_id)
                .where(UserMfaMethod.user_id == ctx.id)
                .where(UserMfaMethod.method_type == "totp")
            ).first()
            if row:
                client.delete(f"/api/v1/users/me/mfa/methods/{row.mfa_method_id}/test")

        # Assert the sentinel appears in ZERO log records
        for record in caplog.records:
            assert SENTINEL not in record.message, (
                f"Access token sentinel leaked into log: {record.message!r}"
            )
            # Also check formatted message (args may contain it)
            formatted = record.getMessage()
            assert SENTINEL not in formatted, (
                f"Access token sentinel leaked into formatted log: {formatted!r}"
            )

        reset_cognito_mfa_client()
