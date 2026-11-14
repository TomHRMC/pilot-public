"""
QuickBooks webhook signature verification utilities.

Security: All webhook requests MUST verify the HMAC signature to prevent
spoofing attacks. Intuit sends the signature in the 'intuit-signature' header.

Design Reference: Task #19 in phase-2-5-implementation-roadmap.md
Gap Reference: Gap #27 in phase-1-4-implementation-gap-analysis.md
"""

import base64
import hashlib
import hmac
import logging

from fastapi import HTTPException, Request

from core.config import settings

logger = logging.getLogger(__name__)


async def verify_quickbooks_signature(request: Request, payload: bytes) -> bool:
    """
    Verify webhook authenticity using HMAC-SHA256.

    Intuit sends signature in header: intuit-signature

    Args:
        request: FastAPI request object
        payload: Raw request body bytes

    Returns:
        True if signature is valid

    Raises:
        HTTPException(401): If signature is missing or invalid
    """
    signature = request.headers.get("intuit-signature")
    if not signature:
        logger.warning("Webhook received without signature header")
        raise HTTPException(status_code=401, detail="Missing signature header")

    # Get verifier token from environment
    verifier_token = settings.QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN
    if not verifier_token:
        logger.error("QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN not configured")
        raise HTTPException(status_code=500, detail="Webhook verifier not configured")

    # Calculate expected signature (QuickBooks uses Base64-encoded HMAC)
    expected_signature = base64.b64encode(
        hmac.new(verifier_token.encode(), payload, hashlib.sha256).digest()
    ).decode()

    # Compare signatures (timing-safe comparison)
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning(
            f"Invalid webhook signature. Expected: {expected_signature[:8]}..., Got: {signature[:8]}..."
        )
        raise HTTPException(status_code=401, detail="Invalid signature")

    logger.info("Webhook signature verified successfully")
    return True
