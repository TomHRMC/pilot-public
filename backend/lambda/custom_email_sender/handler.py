"""
COGNITO-EMAIL-1 — Cognito Custom Email Sender Lambda handler.

Design: dev-docs/architecture-design/batch-designs/batch-cognito-email-1-design.md
        §F (event contract + module interfaces) + §G (resolved decisions).

Cognito invokes this Lambda (trigger type ``CustomEmailSender``, lambda version
``V1_0``) **instead of** sending its own auth emails. The handler:
  1. Routes on ``event["triggerSource"]`` → one of three template flows.
  2. KMS-decrypts ``event["request"]["code"]`` (the OTP / temp password).
  3. Renders a branded template (inline styles, Pilot brand, tracking-free).
  4. Sends via SendGrid (``noreply@pilotfortrades.com``, verified sender).
  5. Returns the event unmodified (Cognito's expected response contract).

⚠️  RETHROW on failure — the OPPOSITE invariant from our passive hooks
    (Post-Confirmation / Post-Authentication, which must NEVER raise). This
    Lambda IS the email delivery path: if it swallows a KMS or SendGrid
    failure, Cognito believes the email sent and the user has no code and no
    error — an unrecoverable silent hole. So: structured log + **raise** →
    Cognito surfaces a clean failure to the user, who can retry (ResendCode
    hits the same path) → and the CloudWatch ``Errors`` alarm fires.
    Unknown ``triggerSource`` also raises (loud > silent when config drifts).
    (design §G.4)

Package discipline: this Lambda package is **self-contained** — no
``app.*`` / ``core.*`` / ``services.*`` imports, no DB, no FastAPI. Only
stdlib + ``sendgrid`` + ``aws-encryption-sdk`` + ``aws-cryptographic-material-providers``
(packaged by DevOps Part B) + lazily-imported ``boto3``
(runtime-provided by the AWS Lambda Python runtime, NEVER packaged). This
keeps the auth path independent of RDS and the zip tiny.

Runtime dependencies (DevOps Part B packaging):
  - ``sendgrid==6.11.0`` (packaged).
  - ``aws-encryption-sdk==4.0.6`` (packaged — Cognito encrypts the code using
    the AWS Encryption SDK envelope format, NOT raw KMS Encrypt; this SDK is
    required to decrypt).
  - ``aws-cryptographic-material-providers==1.11.3`` (packaged — provides the
    KMS keyring used by the Encryption SDK v4.x MPL API).
  - ``boto3`` / ``botocore`` (NOT packaged — pre-bundled in the Lambda runtime;
    imported lazily inside ``_get_kms_keyring()`` and ``_resolve_sendgrid_key()``
    only when the env-var overrides are unset, i.e. in Lambda, not local/tests).

Env vars:
  - ``SENDGRID_API_KEY`` — local/tests override (bypasses Secrets Manager).
  - ``SENDGRID_SECRET_ARN`` — prod: ARN of the ``pilot/prod/sendgrid`` secret
    (JSON key ``SENDGRID_API_KEY``).
  - ``KMS_KEY_ARN`` — prod: ARN of the Cognito pool's KMS key (used to build
    the strict KMS keyring for decryption).
"""

import base64
import json
import logging
import os

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

try:
    from .templates import render  # package context (tests via importlib)
except ImportError:
    from templates import render  # flat layout (Lambda runtime zip root)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Constants ────────────────────────────────────────────────────────────────

# FROM address + display name — match backend/core/config.py SENDGRID_FROM_*.
_FROM_EMAIL = "noreply@pilotfortrades.com"
_FROM_NAME = "Pilot for Trades"

# triggerSource → flow mapping (design §F).
_TRIGGER_TO_FLOW = {
    "CustomEmailSender_SignUp": "verification_code",
    "CustomEmailSender_ResendCode": "verification_code",
    "CustomEmailSender_VerifyUserAttribute": "verification_code",
    "CustomEmailSender_UpdateUserAttribute": "verification_code",
    "CustomEmailSender_ForgotPassword": "forgot_password",
    "CustomEmailSender_AdminCreateUser": "admin_invite",
}

# SendGrid accepted status code.
_SENDGRID_ACCEPTED = 202


# ==================== ENTRY POINT ====================


def handler(event: dict, context) -> dict:
    """
    Cognito Custom Email Sender trigger entry point.

    Routes on ``event["triggerSource"]``, decrypts the code, renders a branded
    template, sends via SendGrid, and returns the event.

    ⚠️  RAISES on every failure path (design §G.4) — see module docstring.

    Returns:
        The unmodified ``event`` dict (Cognito's expected response contract).
    """
    trigger_source = event.get("triggerSource")
    flow = _TRIGGER_TO_FLOW.get(trigger_source)
    if flow is None:
        logger.error(
            "custom_email_sender: unknown triggerSource=%s — raising (§G.4)",
            trigger_source,
        )
        raise ValueError(f"Unknown triggerSource: {trigger_source!r}")

    # Extract recipient email.
    try:
        email = event["request"]["userAttributes"]["email"]
    except (KeyError, TypeError):
        logger.error(
            "custom_email_sender: missing email in userAttributes for "
            "triggerSource=%s — raising (§G.4)",
            trigger_source,
        )
        raise
    if not email or not isinstance(email, str):
        logger.error(
            "custom_email_sender: empty/non-string email for triggerSource=%s "
            "— raising (§G.4)",
            trigger_source,
        )
        raise ValueError(
            f"Empty or non-string email for triggerSource={trigger_source}"
        )

    # Decrypt the code (KMS).
    code = _decrypt_code(event)

    # Render the branded template.
    rendered = render(flow, code, email)

    # Send via SendGrid.
    _send(email, rendered)

    logger.info(
        "custom_email_sender: sent flow=%s to=%s triggerSource=%s",
        flow,
        email,
        trigger_source,
    )
    return event


# ==================== KMS DECRYPT (AWS Encryption SDK) ====================


def _get_kms_keyring():
    """
    Build a strict KMS keyring for the AWS Encryption SDK.

    Cognito encrypts the auth code using the **AWS Encryption SDK** (envelope
    encryption format), NOT raw ``kms:Encrypt``. Therefore ``kms:Decrypt``
    alone cannot decrypt it — the AWS Encryption SDK client + a KMS keyring
    are required.

    ``boto3`` is pre-bundled in the AWS Lambda Python runtime — NOT packaged.
    Imported inside this function so local dev/tests (which monkeypatch this
    factory) never trigger the import.

    Returns:
        A KMS keyring (IKeyring) configured with the pool's KMS key ARN
        from the ``KMS_KEY_ARN`` env var.

    Raises:
        RuntimeError if ``KMS_KEY_ARN`` is not set.
    """
    kms_key_arn = os.environ.get("KMS_KEY_ARN")
    if not kms_key_arn:
        raise RuntimeError(
            "KMS_KEY_ARN env var is not set — DevOps must configure the KMS "
            "key ARN for the Custom Email Sender Lambda."
        )

    import boto3
    from aws_cryptographic_material_providers.mpl import (
        AwsCryptographicMaterialProviders,
    )
    from aws_cryptographic_material_providers.mpl.config import (
        MaterialProvidersConfig,
    )
    from aws_cryptographic_material_providers.mpl.models import (
        CreateAwsKmsKeyringInput,
    )

    mat_prov = AwsCryptographicMaterialProviders(config=MaterialProvidersConfig())
    keyring = mat_prov.create_aws_kms_keyring(
        input=CreateAwsKmsKeyringInput(
            kms_key_id=kms_key_arn,
            kms_client=boto3.client("kms"),
        )
    )
    return keyring


def _decrypt_code(event: dict) -> str:
    """
    Decrypt ``event["request"]["code"]`` using the AWS Encryption SDK.

    Cognito encrypts the code with the pool's KMS key via the AWS Encryption
    SDK envelope format (NOT raw KMS Encrypt). The code is base64-encoded.
    The AWS Encryption SDK client handles the envelope unwrapping + KMS
    Decrypt of the data key internally.

    Returns:
        The decrypted code as a UTF-8 string.

    Raises:
        Propagates any Encryption SDK / KMS exception (design §G.4 — rethrow,
        never swallow).
    """
    import aws_encryption_sdk
    from aws_encryption_sdk import CommitmentPolicy

    code_b64 = event["request"]["code"]
    ciphertext_blob = base64.b64decode(code_b64)

    keyring = _get_kms_keyring()
    # Cognito encrypts with an older algorithm (Algorithm ID 888 — uncommitted
    # messages). The SDK v4.x defaults to REQUIRE_ENCRYPT_REQUIRE_DECRYPT which
    # rejects uncommitted messages. Use REQUIRE_ENCRYPT_ALLOW_DECRYPT to accept
    # both committed and uncommitted (legacy) ciphertexts.
    # See: https://docs.aws.amazon.com/encryption-sdk/latest/developer-guide/troubleshooting-migration.html
    client = aws_encryption_sdk.EncryptionSDKClient(
        commitment_policy=CommitmentPolicy.REQUIRE_ENCRYPT_ALLOW_DECRYPT,
    )

    plaintext, _header = client.decrypt(
        source=ciphertext_blob,
        keyring=keyring,
    )
    return plaintext.decode("utf-8")


# ==================== SENDGRID KEY RESOLUTION ====================


def _resolve_sendgrid_key() -> str:
    """
    Resolve the SendGrid API key.

    Resolution order (mirrors post-authentication handler resource pattern):
      1. ``SENDGRID_API_KEY`` env var if set (local dev / tests / explicit
         override).
      2. Else fetch the secret from AWS Secrets Manager via
         ``SENDGRID_SECRET_ARN`` (JSON key ``SENDGRID_API_KEY`` — verified in
         aws-env-mgmt-ops-plan.md line 79).

    Never logs the key.

    Raises:
        RuntimeError if neither is configured.
        Propagates Secrets Manager ``ClientError`` (design §G.4).
    """
    api_key = os.environ.get("SENDGRID_API_KEY")
    if api_key:
        return api_key

    secret_arn = os.environ.get("SENDGRID_SECRET_ARN")
    if not secret_arn:
        raise RuntimeError(
            "Neither SENDGRID_API_KEY nor SENDGRID_SECRET_ARN is set — DevOps "
            "must configure the SendGrid key for the Custom Email Sender Lambda."
        )

    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("secretsmanager")
    try:
        response = client.get_secret_value(SecretId=secret_arn)
    except ClientError:
        logger.exception("Failed to fetch SendGrid secret from Secrets Manager")
        raise
    secret = response.get("SecretString")
    if not secret:
        raise RuntimeError(f"SendGrid secret {secret_arn} has no SecretString")
    try:
        payload = json.loads(secret)
    except (ValueError, TypeError) as err:
        raise RuntimeError(f"SendGrid secret {secret_arn} is not valid JSON") from err
    # The pilot/prod/sendgrid secret (created via Console) uses the key name
    # "api_key" (not "SENDGRID_API_KEY"). Accept both for forward-compat.
    api_key = payload.get("SENDGRID_API_KEY") or payload.get("api_key")
    if not api_key:
        raise RuntimeError(
            f"SendGrid secret {secret_arn} has no 'SENDGRID_API_KEY' or "
            "'api_key' field — DevOps must populate it"
        )
    return api_key


# ==================== SEND ====================


def _send(to_email: str, rendered) -> None:
    """
    Send the rendered email via SendGrid.

    - FROM: ``noreply@pilotfortrades.com`` / ``Pilot for Trades`` (matches
      ``backend/core/config.py`` SENDGRID_FROM_*).
    - Click + open tracking **disabled** on the Mail object (design §G.5 —
      auth links must not be wrapped; wrapped links break code-visibility and
      deliverability).
    - ``response.status_code == 202`` required — anything else → log body +
      raise (design §G.4).

    Args:
        to_email: Recipient email address.
        rendered: A ``RenderedEmail`` (subject, html, text) from templates.py.

    Raises:
        RuntimeError if SendGrid returns a non-202 status (design §G.4).
        Propagates any SendGrid client exception (design §G.4).
    """
    message = Mail(
        from_email=(_FROM_EMAIL, _FROM_NAME),
        to_emails=to_email,
        subject=rendered.subject,
        plain_text_content=rendered.text,
        html_content=rendered.html,
    )

    # Disable click + open tracking (design §G.5).
    # SendGrid Mail object exposes tracking settings via .mail_settings or
    # via the TrackingSettings helper. The simplest cross-version approach:
    # set the tracking flags on the Mail's personalizations/contents is not
    # directly available; use the SendGrid helper's set_tracking_settings.
    # sendgrid 6.11.0: Mail has no direct attribute, but we can use
    # TrackingSettings + ClickTracking + OpenTracking from helpers.mail.
    from sendgrid.helpers.mail import (
        ClickTracking,
        OpenTracking,
        TrackingSettings,
    )

    tracking = TrackingSettings(
        click_tracking=ClickTracking(enable=False, enable_text=False),
        open_tracking=OpenTracking(enable=False),
    )
    message.tracking_settings = tracking

    sg = SendGridAPIClient(_resolve_sendgrid_key())
    response = sg.send(message)

    if response.status_code != _SENDGRID_ACCEPTED:
        body = response.body.decode("utf-8") if response.body else ""
        logger.error(
            "custom_email_sender: SendGrid non-202 status=%s body=%s — raising (§G.4)",
            response.status_code,
            body,
        )
        raise RuntimeError(
            f"SendGrid returned status {response.status_code}, expected 202. Body: {body}"
        )
