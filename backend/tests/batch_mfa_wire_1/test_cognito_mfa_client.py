"""
MFA-WIRE-1 — Cognito MFA Client unit tests (design §F.1, §F.5).

Tests:
  - MockCognitoMfaClient semantics (fixed secret; code matrix incl. 000000/999999;
    masked destination from recorded phone; preference state recording).
  - Factory: monkeypatch settings.MFA_COGNITO_MOCK True/False → Mock/Real instance
    + mock-init WARNING via caplog.
  - Real client via botocore Stubber: success paths + each ClientError code →
    correct exception (all five §F.3-relevant codes + generic → CognitoMfaError).
"""

import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from services.cognito_mfa_client import (
    CognitoMfaError,
    MfaAccessTokenInvalidError,
    MfaCodeExpiredError,
    MfaCodeMismatchError,
    MfaSmsRoleNotConfiguredError,
    MockCognitoMfaClient,
    RealCognitoMfaClient,
    get_cognito_mfa_client,
    reset_cognito_mfa_client,
)

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


# ── MockCognitoMfaClient semantics ──────────────────────────────────────────


class TestMockCognitoMfaClient:
    def test_associate_software_token_returns_fixed_secret(self):
        client = MockCognitoMfaClient()
        secret = client.associate_software_token("tok-1")
        assert secret == "MFAW1MOCKSECRETBASE32AAAAAAA"

    def test_verify_software_token_any_code_passes(self):
        client = MockCognitoMfaClient()
        client.verify_software_token("tok-1", "123456")  # no exception

    def test_verify_software_token_mismatch(self):
        client = MockCognitoMfaClient()
        with pytest.raises(MfaCodeMismatchError):
            client.verify_software_token("tok-1", "000000")

    def test_verify_software_token_expired(self):
        client = MockCognitoMfaClient()
        with pytest.raises(MfaCodeExpiredError):
            client.verify_software_token("tok-1", "999999")

    def test_verify_phone_number_any_code_passes(self):
        client = MockCognitoMfaClient()
        client.verify_phone_number("tok-1", "123456")

    def test_verify_phone_number_mismatch(self):
        client = MockCognitoMfaClient()
        with pytest.raises(MfaCodeMismatchError):
            client.verify_phone_number("tok-1", "000000")

    def test_verify_phone_number_expired(self):
        client = MockCognitoMfaClient()
        with pytest.raises(MfaCodeExpiredError):
            client.verify_phone_number("tok-1", "999999")

    def test_set_phone_number_and_send_verification(self):
        client = MockCognitoMfaClient()
        client.set_phone_number("tok-1", "+15551234567")
        dest = client.send_phone_verification_code("tok-1")
        assert dest == "***-***-4567"

    def test_send_verification_no_phone_set(self):
        client = MockCognitoMfaClient()
        dest = client.send_phone_verification_code("tok-1")
        assert dest == "***-***-0000"

    def test_set_mfa_preference_records_state(self):
        client = MockCognitoMfaClient()
        client.set_mfa_preference("tok-1", totp_enabled=True, prefer="totp")
        state = client.get_preference_state("tok-1")
        assert state["totp_enabled"] is True
        assert state["preferred"] == "totp"

    def test_set_mfa_preference_sms_disable(self):
        client = MockCognitoMfaClient()
        client.set_mfa_preference("tok-1", sms_enabled=False)
        state = client.get_preference_state("tok-1")
        assert state["sms_enabled"] is False


# ── Factory routing ─────────────────────────────────────────────────────────


class TestFactoryRouting:
    def test_factory_returns_mock_when_setting_true(self, monkeypatch):
        reset_cognito_mfa_client()
        from core.config import settings

        monkeypatch.setattr(settings, "MFA_COGNITO_MOCK", True)
        client = get_cognito_mfa_client()
        assert isinstance(client, MockCognitoMfaClient)
        reset_cognito_mfa_client()

    def test_factory_returns_real_when_setting_false(self, monkeypatch):
        reset_cognito_mfa_client()
        from core.config import settings

        monkeypatch.setattr(settings, "MFA_COGNITO_MOCK", False)
        client = get_cognito_mfa_client()
        assert isinstance(client, RealCognitoMfaClient)
        reset_cognito_mfa_client()

    def test_factory_caches_singleton(self, monkeypatch):
        reset_cognito_mfa_client()
        from core.config import settings

        monkeypatch.setattr(settings, "MFA_COGNITO_MOCK", True)
        c1 = get_cognito_mfa_client()
        c2 = get_cognito_mfa_client()
        assert c1 is c2
        reset_cognito_mfa_client()

    def test_mock_init_warning_logged(self, caplog):
        reset_cognito_mfa_client()
        with caplog.at_level("WARNING", logger="services.cognito_mfa_client"):
            MockCognitoMfaClient()
        assert any("MFA_COGNITO_MOCK=true" in rec.message for rec in caplog.records)
        reset_cognito_mfa_client()


# ── Real client via botocore Stubber ─────────────────────────────────────────


def _make_stubbed_real_client():
    """Create a RealCognitoMfaClient with a Stubber attached."""
    client = RealCognitoMfaClient()
    stubber = Stubber(client._client)
    return client, stubber


class TestRealCognitoMfaClientSuccess:
    def test_associate_software_token_success(self):
        client, stubber = _make_stubbed_real_client()
        stubber.add_response(
            "associate_software_token",
            {"SecretCode": "REALSECRET1234567890"},
        )
        with stubber:
            secret = client.associate_software_token("tok-1")
        assert secret == "REALSECRET1234567890"

    def test_verify_software_token_success(self):
        client, stubber = _make_stubbed_real_client()
        stubber.add_response(
            "verify_software_token",
            {"Status": "SUCCESS"},
            {"AccessToken": "tok-1", "UserCode": "123456"},
        )
        with stubber:
            client.verify_software_token("tok-1", "123456")

    def test_verify_software_token_non_success_raises_mismatch(self):
        client, stubber = _make_stubbed_real_client()
        stubber.add_response(
            "verify_software_token",
            {"Status": "ERROR"},
            {"AccessToken": "tok-1", "UserCode": "123456"},
        )
        with stubber:
            with pytest.raises(MfaCodeMismatchError):
                client.verify_software_token("tok-1", "123456")

    def test_set_phone_number_success(self):
        client, stubber = _make_stubbed_real_client()
        stubber.add_response(
            "update_user_attributes",
            {},
            {
                "AccessToken": "tok-1",
                "UserAttributes": [{"Name": "phone_number", "Value": "+15551234567"}],
            },
        )
        with stubber:
            client.set_phone_number("tok-1", "+15551234567")

    def test_send_phone_verification_code_success(self):
        client, stubber = _make_stubbed_real_client()
        stubber.add_response(
            "get_user_attribute_verification_code",
            {"CodeDeliveryDetails": {"Destination": "***-***-4567"}},
            {"AccessToken": "tok-1", "AttributeName": "phone_number"},
        )
        with stubber:
            dest = client.send_phone_verification_code("tok-1")
        assert dest == "***-***-4567"

    def test_verify_phone_number_success(self):
        client, stubber = _make_stubbed_real_client()
        stubber.add_response(
            "verify_user_attribute",
            {},
            {"AccessToken": "tok-1", "AttributeName": "phone_number", "Code": "123456"},
        )
        with stubber:
            client.verify_phone_number("tok-1", "123456")

    def test_set_mfa_preference_totp(self):
        client, stubber = _make_stubbed_real_client()
        stubber.add_response(
            "set_user_mfa_preference",
            {},
            {
                "AccessToken": "tok-1",
                "SoftwareTokenMfaSettings": {"Enabled": True, "PreferredMfa": True},
            },
        )
        with stubber:
            client.set_mfa_preference("tok-1", totp_enabled=True, prefer="totp")


class TestRealCognitoMfaClientErrors:
    @staticmethod
    def _make_client_error(code: str) -> ClientError:
        return ClientError(
            {"Error": {"Code": code, "Message": f"mock {code}"}},
            "OperationName",
        )

    def test_not_authorized_exception(self):
        client = RealCognitoMfaClient()
        exc = client._translate_error(self._make_client_error("NotAuthorizedException"))
        assert isinstance(exc, MfaAccessTokenInvalidError)

    def test_code_mismatch_exception(self):
        client = RealCognitoMfaClient()
        exc = client._translate_error(self._make_client_error("CodeMismatchException"))
        assert isinstance(exc, MfaCodeMismatchError)

    def test_expired_code_exception(self):
        client = RealCognitoMfaClient()
        exc = client._translate_error(self._make_client_error("ExpiredCodeException"))
        assert isinstance(exc, MfaCodeExpiredError)

    def test_invalid_sms_role_access_policy(self):
        client = RealCognitoMfaClient()
        exc = client._translate_error(
            self._make_client_error("InvalidSmsRoleAccessPolicyException")
        )
        assert isinstance(exc, MfaSmsRoleNotConfiguredError)

    def test_invalid_sms_role_trust_relationship(self):
        client = RealCognitoMfaClient()
        exc = client._translate_error(
            self._make_client_error("InvalidSmsRoleTrustRelationshipException")
        )
        assert isinstance(exc, MfaSmsRoleNotConfiguredError)

    def test_generic_cognito_error(self):
        client = RealCognitoMfaClient()
        exc = client._translate_error(self._make_client_error("SomeOtherException"))
        assert isinstance(exc, CognitoMfaError)
        assert not isinstance(exc, MfaAccessTokenInvalidError)
        assert not isinstance(exc, MfaCodeMismatchError)
        assert not isinstance(exc, MfaCodeExpiredError)
        assert not isinstance(exc, MfaSmsRoleNotConfiguredError)
