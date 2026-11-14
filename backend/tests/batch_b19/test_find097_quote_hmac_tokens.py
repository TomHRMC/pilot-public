"""
FIND-097: Quote Public Link HMAC Token Tests

Tests HMAC-SHA256 signed token generation and verification for quote public links.
Verifies the same pattern used in FIND-073 for invoice links, but applied to quotes.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from services.public_link_signer import (
    TokenExpiredError,
    TokenInvalidError,
    generate_signed_token,
    verify_signed_token,
)


class TestQuoteTokenGeneration:
    """Tests for HMAC-SHA256 signed token generation (quote links)."""

    def test_generate_token_returns_tuple(self):
        """generate_signed_token returns (token: str, expires_at: datetime)."""
        link_id = uuid4()
        customer_id = uuid4()

        token, expires_at = generate_signed_token(
            link_id=link_id,
            link_type="quote",
            customer_id=customer_id,
            expires_in_days=90,
        )

        assert isinstance(token, str)
        assert isinstance(expires_at, datetime)
        assert token  # Non-empty
        assert "." in token  # Contains separator

    def test_token_format_valid_base64url(self):
        """Token format is base64url(payload).base64url(signature)."""
        link_id = uuid4()
        customer_id = uuid4()

        token, _ = generate_signed_token(
            link_id=link_id,
            link_type="quote",
            customer_id=customer_id,
        )

        parts = token.split(".")
        assert len(parts) == 2
        assert parts[0]  # payload
        assert parts[1]  # signature

    def test_token_expiration_matches_ttl(self):
        """Token expiration is N days from now."""
        link_id = uuid4()
        customer_id = uuid4()
        now = datetime.now(UTC)

        _, expires_at = generate_signed_token(
            link_id=link_id,
            link_type="quote",
            customer_id=customer_id,
            expires_in_days=90,
        )

        # Should be ~90 days from now (allow 1-minute drift)
        expected = now + timedelta(days=90)
        assert abs((expires_at - expected).total_seconds()) < 60

    def test_payload_contains_link_id_quote_type_customer_id(self):
        """Verified payload contains link_id, link_type='quote', customer_id, expiration."""
        link_id = uuid4()
        customer_id = uuid4()

        token, _ = generate_signed_token(
            link_id=link_id,
            link_type="quote",
            customer_id=customer_id,
            expires_in_days=90,
        )

        payload = verify_signed_token(token)
        assert payload["link_id"] == str(link_id)
        assert payload["link_type"] == "quote"
        assert payload["customer_id"] == str(customer_id)
        assert "expiration" in payload


class TestQuoteTokenVerification:
    """Tests for HMAC-SHA256 token verification (quote links)."""

    def test_verify_valid_token_returns_payload(self):
        """Verifying a valid token returns the payload dict."""
        link_id = uuid4()
        customer_id = uuid4()

        token, _ = generate_signed_token(
            link_id=link_id,
            link_type="quote",
            customer_id=customer_id,
        )

        payload = verify_signed_token(token)
        assert isinstance(payload, dict)
        assert payload["link_id"] == str(link_id)

    def test_tampered_signature_raises_invalid_error(self):
        """Modifying the signature raises TokenInvalidError."""
        link_id = uuid4()
        customer_id = uuid4()

        token, _ = generate_signed_token(
            link_id=link_id,
            link_type="quote",
            customer_id=customer_id,
        )

        # Tamper with the signature (multiple characters to ensure detection)
        parts = token.split(".")
        tampered = parts[0] + "." + "XXXXXXXXXXXXXXXXXXXXXXXX"

        with pytest.raises(TokenInvalidError):
            verify_signed_token(tampered)

    def test_tampered_payload_raises_invalid_error(self):
        """Modifying the payload raises TokenInvalidError."""
        link_id = uuid4()
        customer_id = uuid4()

        token, _ = generate_signed_token(
            link_id=link_id,
            link_type="quote",
            customer_id=customer_id,
        )

        # Tamper with the payload (first character)
        parts = token.split(".")
        tampered = "X" + parts[0][1:] + "." + parts[1]

        with pytest.raises(TokenInvalidError):
            verify_signed_token(tampered)

    def test_expired_token_raises_expired_error(self):
        """Token past expiration raises TokenExpiredError."""
        link_id = uuid4()
        customer_id = uuid4()

        # Generate with -1 day TTL (already expired)
        token, _ = generate_signed_token(
            link_id=link_id,
            link_type="quote",
            customer_id=customer_id,
            expires_in_days=-1,
        )

        with pytest.raises(TokenExpiredError):
            verify_signed_token(token)

    def test_malformed_token_missing_separator_raises_invalid_error(self):
        """Token without separator raises TokenInvalidError."""
        with pytest.raises((TokenInvalidError, ValueError)):
            verify_signed_token("noseparatorhere")

    def test_malformed_token_empty_raises_invalid_error(self):
        """Empty token raises TokenInvalidError."""
        with pytest.raises((TokenInvalidError, ValueError)):
            verify_signed_token("")


class TestQuoteTokenIntegration:
    """Test HMAC token round-trip with quote link generation."""

    def test_token_round_trip_generate_and_verify(self):
        """Token can be generated and verified in the same operation."""
        link_id = uuid4()
        customer_id = uuid4()

        # Generate token
        token, expires_at = generate_signed_token(
            link_id=link_id,
            link_type="quote",
            customer_id=customer_id,
            expires_in_days=90,
        )

        # Verify token
        payload = verify_signed_token(token)

        # Assertions
        assert payload["link_id"] == str(link_id)
        assert payload["link_type"] == "quote"
        assert payload["customer_id"] == str(customer_id)
        assert isinstance(payload["expiration"], str)

    def test_token_format_matches_invoice_pattern(self):
        """Quote tokens use same format as invoice tokens."""
        link_id = uuid4()
        customer_id = uuid4()

        quote_token, _ = generate_signed_token(
            link_id=link_id,
            link_type="quote",
            customer_id=customer_id,
        )

        # Should match: base64url(payload).base64url(signature)
        assert isinstance(quote_token, str)
        assert quote_token.count(".") == 1
        parts = quote_token.split(".")
        assert len(parts[0]) > 0  # payload
        assert len(parts[1]) > 0  # signature
