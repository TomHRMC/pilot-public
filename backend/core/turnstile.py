"""
MKT-B1-BE — Cloudflare Turnstile server-side verification helper.

Usage:
    from core.turnstile import verify_turnstile

    is_valid = await verify_turnstile(token)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid request")

Dev/test: Set CLOUDFLARE_TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA
          This is the Cloudflare always-passes test secret — no real Turnstile account needed.

Fail-closed: Any network error or unexpected response returns False.
"""

import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str) -> bool:
    """
    Verify a Cloudflare Turnstile challenge token server-side.

    Args:
        token: The cf-turnstile-response token from the browser form submission.

    Returns:
        True if Cloudflare confirms the token is valid ("success": true).
        False if verification fails or any network/parse error occurs.

    Security:
        Fail-closed: exceptions return False (reject request) rather than True.
        The secret key is never sent to the client — only used in this server-side call.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                TURNSTILE_VERIFY_URL,
                data={
                    "secret": settings.CLOUDFLARE_TURNSTILE_SECRET_KEY,
                    "response": token,
                },
            )
            response.raise_for_status()
            result = response.json()
            return bool(result.get("success", False))
    except Exception as exc:
        logger.warning(
            "Turnstile verification failed (fail-closed): %s",
            exc,
            exc_info=False,
        )
        return False
