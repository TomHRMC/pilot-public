"""
OAuth token encryption utilities using Fernet (AES-128-CBC + HMAC-SHA256).

Security Notes:
- ENCRYPTION_KEY must be 32 URL-safe base64-encoded bytes
- Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
- Never log decrypted tokens
- Rotate encryption key periodically (requires re-encrypting all tokens)

Task Reference: Phase 3, Task #16 - QuickBooks OAuth 2.0 Flow
Gap Reference: Gap #22 in phase-1-4-implementation-gap-analysis.md
"""

from cryptography.fernet import Fernet

from core.config import settings


def encrypt_token(token: str) -> str:
    """
    Encrypt OAuth token using Fernet (AES-128-CBC + HMAC-SHA256).

    Args:
        token: Plaintext OAuth access or refresh token

    Returns:
        Base64-encoded encrypted token string

    Raises:
        ValueError: If ENCRYPTION_KEY is invalid or not set
        TypeError: If token is not a string

    Example:
        >>> encrypted = encrypt_token("qb_access_token_123")
        >>> print(encrypted)
        'gAAAAABh...'
    """
    if not settings.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY not configured in settings")

    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt OAuth token.

    Args:
        encrypted_token: Base64-encoded encrypted token

    Returns:
        Plaintext OAuth token

    Raises:
        cryptography.fernet.InvalidToken: If token is corrupted or key is wrong
        ValueError: If ENCRYPTION_KEY is invalid or not set

    Example:
        >>> decrypted = decrypt_token("gAAAAABh...")
        >>> print(decrypted)
        'qb_access_token_123'
    """
    if not settings.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY not configured in settings")

    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted_token.encode()).decode()
