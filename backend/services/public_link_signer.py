"""
B15/A80 — Public Link Signer

HMAC-SHA256 signed token service for public quote/invoice links.

Token format: base64url(payload_json) + '.' + base64url(hmac_signature)

The payload is JSON: {"link_id": str, "link_type": "quote"|"invoice",
                      "customer_id": str, "expiration": ISO-8601-str}

Design notes:
  - token_hash (legacy) and signed_token coexist on both public link tables.
  - This module implements signed_token semantics only.
  - Revocation check is caller's responsibility (requires DB lookup).
  - Secret is read from settings.PUBLIC_LINK_SECRET; falls back to a dev stub.
"""

import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

# ─────────────────────────────────────────────────────────────────────────────
# Custom exceptions
# ─────────────────────────────────────────────────────────────────────────────


class PublicLinkSignerError(Exception):
    """Base exception for token errors."""


class TokenExpiredError(PublicLinkSignerError):
    """Token has passed its expiration timestamp."""


class TokenRevokedError(PublicLinkSignerError):
    """Token has been revoked by the tenant."""


class TokenInvalidError(PublicLinkSignerError):
    """HMAC signature is invalid or payload is malformed."""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    # Add back padding
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def _get_secret() -> str:
    """Read PUBLIC_LINK_SECRET from settings; fallback to dev stub."""
    from core.config import settings

    secret = getattr(settings, "PUBLIC_LINK_SECRET", None)
    if not secret:
        # Dev stub — non-empty string to allow local testing
        return "dev-pilot-public-link-secret-CHANGE-IN-PRODUCTION"
    return secret


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def generate_signed_token(
    link_id: uuid.UUID,
    link_type: Literal["quote", "invoice"],
    customer_id: uuid.UUID,
    secret: str | None = None,
    expires_in_days: int = 90,
) -> tuple[str, datetime]:
    """
    Generate a URL-safe HMAC-SHA256 signed token.

    Args:
        link_id: UUID of the public link record.
        link_type: 'quote' or 'invoice'.
        customer_id: UUID of the customer for verification.
        secret: Per-deployment secret. None → read from settings.
        expires_in_days: Token TTL (default 90 days per §18.2).

    Returns:
        Tuple of (signed_token: str, expires_at: datetime).
    """
    if secret is None:
        secret = _get_secret()

    expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

    payload = {
        "link_id": str(link_id),
        "link_type": link_type,
        "customer_id": str(customer_id),
        "expiration": expires_at.isoformat(),
    }

    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)

    sig = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64url_encode(sig)

    token = f"{payload_b64}.{sig_b64}"
    return token, expires_at


def verify_signed_token(
    token: str,
    secret: str | None = None,
) -> dict:
    """
    Decode and verify a signed token.

    Args:
        token: The signed token string from the URL.
        secret: Per-deployment secret. None → read from settings.

    Returns:
        Payload dict if valid and not expired:
        {"link_id": str, "link_type": str, "customer_id": str, "expiration": str}

    Raises:
        TokenInvalidError: HMAC mismatch or malformed payload.
        TokenExpiredError: Token expiration has passed.

    Notes:
        Does NOT check revocation (requires DB lookup — caller's responsibility).
    """
    if secret is None:
        secret = _get_secret()

    parts = token.split(".")
    if len(parts) != 2:
        raise TokenInvalidError("Token format invalid: expected payload.signature")

    payload_b64, sig_b64 = parts

    try:
        payload_bytes = _b64url_decode(payload_b64)
    except Exception:
        raise TokenInvalidError("Token payload is not valid base64url")

    # Verify HMAC
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).digest()
    try:
        provided_sig = _b64url_decode(sig_b64)
    except Exception:
        raise TokenInvalidError("Token signature is not valid base64url")

    if not hmac.compare_digest(expected_sig, provided_sig):
        raise TokenInvalidError("Token signature verification failed")

    # Parse payload
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise TokenInvalidError("Token payload is not valid JSON")

    # Check expiration
    expiration_str = payload.get("expiration")
    if not expiration_str:
        raise TokenInvalidError("Token payload missing expiration field")

    try:
        expiration_dt = datetime.fromisoformat(expiration_str)
    except ValueError:
        raise TokenInvalidError("Token expiration is not a valid ISO datetime")

    if datetime.now(UTC) > expiration_dt:
        raise TokenExpiredError(f"Token expired at {expiration_str}")

    return payload
