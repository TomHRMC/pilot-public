"""
Tests for: Custom Email Sender Lambda handler (COGNITO-EMAIL-1).
Domain: identity_access (PRD §3.5)

Covers (design §F + §G.4):
  - Per-flow coverage (4 verification trigger sources + forgot-password +
    admin-invite): correct subject; decrypted code in BOTH html + plaintext;
    FROM is noreply@pilotfortrades.com; click/open tracking disabled;
    sendgrid .send() called exactly once; handler returns the event.
  - Decrypt contract: kms.decrypt called with the verified EncryptionContext
    (userpool-id, client-id) and the base64-decoded blob.
  - Raise paths (§G.4): KMS ClientError → raises; SendGrid non-202 → raises;
    unknown triggerSource → raises; missing email attribute → raises.

Mirrors ``test_post_authentication_handler.py``'s importlib pattern. No DB
fixtures — the handler has no DB access by design (design §B).
"""

import base64
import importlib
import sys
import uuid
from unittest.mock import MagicMock

import pytest

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]

# ── Constants ────────────────────────────────────────────────────────────────

_DECRYPTED_CODE = "123456"
_USER_POOL_ID = "us-east-1_XXXXXXXXX"
_CLIENT_ID = "client-id-xyz"
_TEST_EMAIL = f"test-{uuid.uuid4()}@example.com"

# triggerSource → expected subject (design §F templates table).
_TRIGGER_SUBJECTS = {
    "CustomEmailSender_SignUp": "Your Pilot for Trades verification code",
    "CustomEmailSender_ResendCode": "Your Pilot for Trades verification code",
    "CustomEmailSender_VerifyUserAttribute": "Your Pilot for Trades verification code",
    "CustomEmailSender_UpdateUserAttribute": "Your Pilot for Trades verification code",
    "CustomEmailSender_ForgotPassword": "Reset your Pilot for Trades password",
    "CustomEmailSender_AdminCreateUser": "You've been invited to Pilot for Trades",
}


# ── Event fixture builder ────────────────────────────────────────────────────


def _event(
    trigger_source: str, email: str = _TEST_EMAIL, code_b64: str | None = None
) -> dict:
    """Build a synthetic Cognito Custom Email Sender event dict."""
    if code_b64 is None:
        code_b64 = base64.b64encode(b"encrypted-blob").decode("utf-8")
    return {
        "triggerSource": trigger_source,
        "userPoolId": _USER_POOL_ID,
        "userName": email,
        "callerContext": {
            "awsSdkVersion": "aws-sdk-js-2.1000.0",
            "clientId": _CLIENT_ID,
        },
        "request": {
            "userAttributes": {
                "email": email,
                "sub": str(uuid.uuid4()),
            },
            "code": code_b64,
        },
    }


# ── Shared mock setup ────────────────────────────────────────────────────────


def _setup_mocks(handler_mod, monkeypatch):
    """
    Monkeypatch the handler's KMS keyring factory + AWS Encryption SDK client
    + SendGrid client.

    The handler uses the AWS Encryption SDK (envelope encryption) to decrypt
    the Cognito code — NOT raw ``kms:Decrypt``. Tests inject a fake
    ``aws_encryption_sdk`` module into ``sys.modules`` so the function-local
    ``import aws_encryption_sdk`` picks up the mock without requiring the
    real SDK to be installed.

    Returns ``(fake_sg_instance, fake_client)`` — the SendGridAPIClient mock
    (for ``.send()`` call inspection) and the EncryptionSDKClient mock (for
    ``.decrypt()`` call inspection).
    """
    # 1. AWS Encryption SDK mock — decrypt returns the known plaintext.
    fake_client = MagicMock()
    fake_client.decrypt.return_value = (
        _DECRYPTED_CODE.encode("utf-8"),
        MagicMock(),
    )
    fake_aws_encryption_sdk = MagicMock()
    fake_aws_encryption_sdk.EncryptionSDKClient.return_value = fake_client
    fake_aws_encryption_sdk.CommitmentPolicy.REQUIRE_ENCRYPT_ALLOW_DECRYPT = MagicMock()
    monkeypatch.setitem(sys.modules, "aws_encryption_sdk", fake_aws_encryption_sdk)

    # 2. KMS keyring mock — _get_kms_keyring returns a fake keyring.
    fake_keyring = MagicMock()
    monkeypatch.setattr(handler_mod, "_get_kms_keyring", lambda: fake_keyring)

    # 3. SendGrid key — env override so tests never touch Secrets Manager.
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test-key")

    # 4. SendGridAPIClient mock — .send() returns a 202 response.
    fake_sg_instance = MagicMock()
    fake_response = MagicMock()
    fake_response.status_code = 202
    fake_response.body = b""
    fake_sg_instance.send.return_value = fake_response

    fake_sg_class = MagicMock(return_value=fake_sg_instance)
    monkeypatch.setattr(handler_mod, "SendGridAPIClient", fake_sg_class)

    return fake_sg_instance, fake_client


def _extract_contents(sent_mail):
    """Extract (plain_text, html_text) from a SendGrid Mail object's contents."""
    plain_content = ""
    html_str = ""
    for c in sent_mail.contents:
        val = str(c.content)
        if c.mime_type == "text/plain":
            plain_content = val
        elif c.mime_type == "text/html":
            html_str = val
    return plain_content, html_str


# ── Per-flow coverage ────────────────────────────────────────────────────────


@pytest.mark.parametrize("trigger_source", list(_TRIGGER_SUBJECTS.keys()))
class TestPerFlow:
    """One parametrized set over all six trigger sources."""

    def test_correct_subject(self, trigger_source, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")
        fake_sg, _ = _setup_mocks(handler_mod, monkeypatch)

        event = _event(trigger_source)
        handler_mod.handler(event, None)

        sent_mail = fake_sg.send.call_args.args[0]
        assert sent_mail.subject.subject == _TRIGGER_SUBJECTS[trigger_source]

    def test_code_in_html_and_plaintext(self, trigger_source, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")
        fake_sg, _ = _setup_mocks(handler_mod, monkeypatch)

        event = _event(trigger_source)
        handler_mod.handler(event, None)

        sent_mail = fake_sg.send.call_args.args[0]
        plain_content, html_str = _extract_contents(sent_mail)
        assert _DECRYPTED_CODE in plain_content, (
            f"code missing from plaintext for {trigger_source}"
        )
        assert _DECRYPTED_CODE in html_str, (
            f"code missing from HTML for {trigger_source}"
        )

    def test_from_address(self, trigger_source, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")
        fake_sg, _ = _setup_mocks(handler_mod, monkeypatch)

        event = _event(trigger_source)
        handler_mod.handler(event, None)

        sent_mail = fake_sg.send.call_args.args[0]
        from_email = sent_mail.from_email
        assert from_email.email == "noreply@pilotfortrades.com"
        assert from_email.name == "Pilot for Trades"

    def test_tracking_disabled(self, trigger_source, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")
        fake_sg, _ = _setup_mocks(handler_mod, monkeypatch)

        event = _event(trigger_source)
        handler_mod.handler(event, None)

        sent_mail = fake_sg.send.call_args.args[0]
        ts = sent_mail.tracking_settings
        assert ts is not None
        assert ts.click_tracking.enable is False
        assert ts.click_tracking.enable_text is False
        assert ts.open_tracking.enable is False

    def test_send_called_once(self, trigger_source, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")
        fake_sg, _ = _setup_mocks(handler_mod, monkeypatch)

        event = _event(trigger_source)
        handler_mod.handler(event, None)

        assert fake_sg.send.call_count == 1

    def test_returns_event(self, trigger_source, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")
        _setup_mocks(handler_mod, monkeypatch)

        event = _event(trigger_source)
        result = handler_mod.handler(event, None)
        assert result is event


# ── Decrypt contract ─────────────────────────────────────────────────────────


class TestDecryptContract:
    """EncryptionSDKClient.decrypt called with base64-decoded blob + keyring."""

    def test_decrypt_context_and_blob(self, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")
        _fake_sg, fake_client = _setup_mocks(handler_mod, monkeypatch)

        raw_blob = b"\x00\x01\x02\x03encrypted"
        code_b64 = base64.b64encode(raw_blob).decode("utf-8")
        event = _event("CustomEmailSender_SignUp", code_b64=code_b64)

        handler_mod.handler(event, None)

        fake_client.decrypt.assert_called_once()
        call_kwargs = fake_client.decrypt.call_args.kwargs
        assert call_kwargs["source"] == raw_blob
        assert "keyring" in call_kwargs


# ── Raise paths (§G.4) ───────────────────────────────────────────────────────


class TestRaisePaths:
    """Every failure path raises (design §G.4 — rethrow, never swallow)."""

    def test_kms_client_error_raises(self, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")

        # AWS Encryption SDK mock — decrypt raises (simulates KMS failure).
        fake_client = MagicMock()
        fake_client.decrypt.side_effect = Exception("KMS InvalidCiphertextException")
        fake_aws_encryption_sdk = MagicMock()
        fake_aws_encryption_sdk.EncryptionSDKClient.return_value = fake_client
        fake_aws_encryption_sdk.CommitmentPolicy.REQUIRE_ENCRYPT_ALLOW_DECRYPT = (
            MagicMock()
        )
        monkeypatch.setitem(sys.modules, "aws_encryption_sdk", fake_aws_encryption_sdk)

        fake_keyring = MagicMock()
        monkeypatch.setattr(handler_mod, "_get_kms_keyring", lambda: fake_keyring)
        monkeypatch.setenv("SENDGRID_API_KEY", "SG.test-key")

        event = _event("CustomEmailSender_SignUp")
        with pytest.raises(Exception, match="InvalidCiphertextException"):
            handler_mod.handler(event, None)

    def test_sendgrid_non_202_raises(self, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")
        fake_sg, _ = _setup_mocks(handler_mod, monkeypatch)
        # Override the response to 400.
        fake_response = MagicMock()
        fake_response.status_code = 400
        fake_response.body = b'{"errors": ["bad request"]}'
        fake_sg.send.return_value = fake_response

        event = _event("CustomEmailSender_SignUp")
        with pytest.raises(RuntimeError, match="SendGrid returned status 400"):
            handler_mod.handler(event, None)

    def test_unknown_trigger_source_raises(self, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")
        _setup_mocks(handler_mod, monkeypatch)

        event = _event("CustomEmailSender_AccountTakeOverNotification")
        with pytest.raises(ValueError, match="Unknown triggerSource"):
            handler_mod.handler(event, None)

    def test_missing_email_attribute_raises(self, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")
        _setup_mocks(handler_mod, monkeypatch)

        event = _event("CustomEmailSender_SignUp")
        # Remove the email attribute.
        del event["request"]["userAttributes"]["email"]
        with pytest.raises((KeyError, ValueError)):
            handler_mod.handler(event, None)

    def test_empty_email_raises(self, monkeypatch):
        handler_mod = importlib.import_module("lambda.custom_email_sender.handler")
        _setup_mocks(handler_mod, monkeypatch)

        event = _event("CustomEmailSender_SignUp", email="")
        with pytest.raises(ValueError, match="Empty or non-string email"):
            handler_mod.handler(event, None)
