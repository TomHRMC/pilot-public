"""
MFA-WIRE-1 — Cognito MFA client seam (design §F.1).

Provides a mock/real client Protocol for AWS Cognito user-scoped MFA APIs.
User-scoped calls (AssociateSoftwareToken, VerifySoftwareToken,
SetUserMFAPreference, GetUserAttributeVerificationCode, VerifyUserAttribute)
authenticate via the user's ACCESS token — no IAM credentials needed
(verified: ECS task role has zero cognito-idp grants). The real client is
built with ``Config(signature_version=UNSIGNED)``.

The mock is the default outside prod (``MFA_COGNITO_MOCK`` defaults True in
``core/config.py``); only the prod task definition sets it false. All unit
tests and ``/test`` twins run on the mock.

Security: the access token is use-in-memory-only — never logged, never
persisted, never returned in any response (design §E).
"""

from __future__ import annotations

import logging
from typing import Literal, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions (design §F.1 / §F.3)
# ---------------------------------------------------------------------------


class CognitoMfaError(Exception):
    """Base — maps to 502 ``cognito_unavailable``."""


class MfaAccessTokenInvalidError(CognitoMfaError):
    """``NotAuthorizedException`` → 401 ``mfa_access_token_invalid``."""


class MfaCodeMismatchError(CognitoMfaError):
    """``CodeMismatchException`` → 400 ``mfa_code_invalid``."""


class MfaCodeExpiredError(CognitoMfaError):
    """``ExpiredCodeException`` → 400 ``mfa_code_expired``."""


class MfaSmsRoleNotConfiguredError(CognitoMfaError):
    """``InvalidSmsRoleAccessPolicyException`` /
    ``InvalidSmsRoleTrustRelationshipException`` → 503
    ``sms_delivery_not_configured`` (unfinished DevOps Step 0 diagnosis)."""


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class CognitoMfaClient(Protocol):
    def associate_software_token(self, access_token: str) -> str:
        """→ SecretCode. Raises CognitoMfaError."""
        ...

    def verify_software_token(self, access_token: str, user_code: str) -> None:
        """Raises MfaCodeMismatchError / MfaCodeExpiredError."""
        ...

    def set_phone_number(self, access_token: str, phone_e164: str) -> None: ...

    def send_phone_verification_code(self, access_token: str) -> str:
        """GetUserAttributeVerificationCode(phone_number) → masked destination."""
        ...

    def verify_phone_number(self, access_token: str, code: str) -> None:
        """Raises MfaCodeMismatchError / MfaCodeExpiredError."""
        ...

    def set_mfa_preference(
        self,
        access_token: str,
        *,
        totp_enabled: bool | None = None,
        sms_enabled: bool | None = None,
        prefer: Literal["totp", "sms"] | None = None,
    ) -> None: ...


# ---------------------------------------------------------------------------
# Real client — boto3 cognito-idp, UNSIGNED (user-scoped calls need no IAM creds)
# ---------------------------------------------------------------------------


_SMS_ROLE_ERROR_CODES = {
    "InvalidSmsRoleAccessPolicyException",
    "InvalidSmsRoleTrustRelationshipException",
}


class RealCognitoMfaClient:
    """boto3 cognito-idp client for user-scoped MFA calls.

    Built with ``Config(signature_version=UNSIGNED)`` — the access token
    authenticates each call; no AWS IAM credentials are required.
    """

    def __init__(self) -> None:
        import boto3
        from botocore import UNSIGNED
        from botocore.config import Config

        from core.config import settings

        self._client = boto3.client(
            "cognito-idp",
            region_name=settings.COGNITO_REGION,
            config=Config(signature_version=UNSIGNED),
        )

    @staticmethod
    def _translate_error(e: Exception) -> CognitoMfaError:
        """Map a botocore ClientError to a domain exception. Never includes the
        access token in the message."""
        from botocore.exceptions import ClientError

        if isinstance(e, ClientError):
            code = e.response.get("Error", {}).get("Code", "")
            if code == "NotAuthorizedException":
                return MfaAccessTokenInvalidError(str(e))
            if code == "CodeMismatchException":
                return MfaCodeMismatchError(str(e))
            if code == "ExpiredCodeException":
                return MfaCodeExpiredError(str(e))
            if code in _SMS_ROLE_ERROR_CODES:
                return MfaSmsRoleNotConfiguredError(str(e))
            return CognitoMfaError(str(e))
        return CognitoMfaError(str(e))

    def associate_software_token(self, access_token: str) -> str:
        try:
            resp = self._client.associate_software_token(AccessToken=access_token)
        except Exception as e:
            raise self._translate_error(e) from e
        return resp["SecretCode"]

    def verify_software_token(self, access_token: str, user_code: str) -> None:
        try:
            resp = self._client.verify_software_token(
                AccessToken=access_token, UserCode=user_code
            )
        except Exception as e:
            raise self._translate_error(e) from e
        if resp.get("Status") != "SUCCESS":
            raise MfaCodeMismatchError("VerifySoftwareToken did not return SUCCESS")

    def set_phone_number(self, access_token: str, phone_e164: str) -> None:
        try:
            self._client.update_user_attributes(
                AccessToken=access_token,
                UserAttributes=[
                    {"Name": "phone_number", "Value": phone_e164},
                ],
            )
        except Exception as e:
            raise self._translate_error(e) from e

    def send_phone_verification_code(self, access_token: str) -> str:
        try:
            resp = self._client.get_user_attribute_verification_code(
                AccessToken=access_token, AttributeName="phone_number"
            )
        except Exception as e:
            raise self._translate_error(e) from e
        return resp.get("CodeDeliveryDetails", {}).get("Destination", "***-***-0000")

    def verify_phone_number(self, access_token: str, code: str) -> None:
        try:
            self._client.verify_user_attribute(
                AccessToken=access_token,
                AttributeName="phone_number",
                Code=code,
            )
        except Exception as e:
            raise self._translate_error(e) from e

    def set_mfa_preference(
        self,
        access_token: str,
        *,
        totp_enabled: bool | None = None,
        sms_enabled: bool | None = None,
        prefer: Literal["totp", "sms"] | None = None,
    ) -> None:
        totp_settings: dict | None = None
        sms_settings: dict | None = None
        if totp_enabled is not None:
            totp_settings = {
                "Enabled": totp_enabled,
                "PreferredMfa": prefer == "totp",
            }
        if sms_enabled is not None:
            sms_settings = {
                "Enabled": sms_enabled,
                "PreferredMfa": prefer == "sms",
            }
        # boto3 rejects None for *MfaSettings — omit the parameter entirely
        kwargs: dict = {"AccessToken": access_token}
        if totp_settings is not None:
            kwargs["SoftwareTokenMfaSettings"] = totp_settings
        if sms_settings is not None:
            kwargs["SMSMfaSettings"] = sms_settings
        try:
            self._client.set_user_mfa_preference(**kwargs)
        except Exception as e:
            raise self._translate_error(e) from e


# ---------------------------------------------------------------------------
# Mock client — deterministic, in-memory, for dev/tests
# ---------------------------------------------------------------------------

_MOCK_SECRET = "MFAW1MOCKSECRETBASE32AAAAAAA"


class MockCognitoMfaClient:
    """Deterministic for tests/dev: fixed secret; any 6-digit code verifies
    EXCEPT ``"000000"`` (mismatch) and ``"999999"`` (expired), so both error
    paths are testable without AWS.

    Records phone numbers and MFA preference state per access-token in instance
    dicts so delete-wiring tests can assert against this state.
    """

    def __init__(self) -> None:
        # Per-token state dicts (access token → recorded state)
        self._phones: dict[str, str] = {}
        self._preferences: dict[str, dict] = {}
        logger.warning(
            "CognitoMfaClient running with MFA_COGNITO_MOCK=true — "
            "no real Cognito MFA calls will be made"
        )

    def associate_software_token(self, access_token: str) -> str:
        return _MOCK_SECRET

    def verify_software_token(self, access_token: str, user_code: str) -> None:
        if user_code == "000000":
            raise MfaCodeMismatchError("mock: code mismatch")
        if user_code == "999999":
            raise MfaCodeExpiredError("mock: code expired")

    def set_phone_number(self, access_token: str, phone_e164: str) -> None:
        self._phones[access_token] = phone_e164

    def send_phone_verification_code(self, access_token: str) -> str:
        phone = self._phones.get(access_token)
        if phone and len(phone) >= 4:
            return f"***-***-{phone[-4:]}"
        return "***-***-0000"

    def verify_phone_number(self, access_token: str, code: str) -> None:
        if code == "000000":
            raise MfaCodeMismatchError("mock: code mismatch")
        if code == "999999":
            raise MfaCodeExpiredError("mock: code expired")

    def set_mfa_preference(
        self,
        access_token: str,
        *,
        totp_enabled: bool | None = None,
        sms_enabled: bool | None = None,
        prefer: Literal["totp", "sms"] | None = None,
    ) -> None:
        state = self._preferences.setdefault(access_token, {})
        if totp_enabled is not None:
            state["totp_enabled"] = totp_enabled
        if sms_enabled is not None:
            state["sms_enabled"] = sms_enabled
        if prefer is not None:
            state["preferred"] = prefer

    # ── Test-inspection helpers (not part of the Protocol) ──────────────────

    def get_phone(self, access_token: str) -> str | None:
        return self._phones.get(access_token)

    def get_preference_state(self, access_token: str) -> dict:
        return dict(self._preferences.get(access_token, {}))


# ---------------------------------------------------------------------------
# Factory — cached singleton; reads setting at call time for test monkeypatch
# ---------------------------------------------------------------------------

_client_instance: CognitoMfaClient | None = None


def get_cognito_mfa_client() -> CognitoMfaClient:
    """Return the cached MFA client singleton. Mock when
    ``settings.MFA_COGNITO_MOCK`` is true (default), else Real. The setting is
    read at call time so tests can monkeypatch it."""
    global _client_instance
    if _client_instance is not None:
        return _client_instance
    from core.config import settings

    if settings.MFA_COGNITO_MOCK:
        _client_instance = MockCognitoMfaClient()
    else:
        _client_instance = RealCognitoMfaClient()
    return _client_instance


def reset_cognito_mfa_client() -> None:
    """Clear the cached singleton — for test isolation."""
    global _client_instance
    _client_instance = None
