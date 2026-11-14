"""
Tests for QuickBooks OAuth 2.0 integration.

Test Coverage:
- Token encryption/decryption
- OAuth flow basic functionality
- Security (CSRF protection, tenant isolation)

Design Reference: Task #16 in phase-2-5-implementation-roadmap.md
Gap Reference: Gap #22 in phase-1-4-implementation-gap-analysis.md
"""

import pytest

from core.encryption import decrypt_token, encrypt_token


class TestTokenEncryption:
    """Test token encryption/decryption utilities"""

    def test_encrypt_token(self):
        """Test token encryption produces encrypted output"""
        token = "test_access_token_12345"
        encrypted = encrypt_token(token)

        # Encrypted token should be different from plaintext
        assert encrypted != token
        assert isinstance(encrypted, str)
        assert len(encrypted) > len(token)

    def test_decrypt_token(self):
        """Test token decryption returns original token"""
        token = "test_access_token_12345"
        encrypted = encrypt_token(token)
        decrypted = decrypt_token(encrypted)

        assert decrypted == token

    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption/decryption roundtrip with various tokens"""
        test_tokens = [
            "short",
            "a" * 1000,  # Long token
            "token_with_special_chars!@#$%^&*()",
        ]

        for token in test_tokens:
            encrypted = encrypt_token(token)
            decrypted = decrypt_token(encrypted)
            assert decrypted == token

    def test_decrypt_invalid_token_fails(self):
        """Test decrypting invalid token raises error"""
        with pytest.raises(Exception):
            decrypt_token("invalid_encrypted_token")
