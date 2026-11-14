"""
Celery task for proactive QuickBooks token refresh.

Runs every 30 minutes via Celery Beat scheduler.
Refreshes access tokens expiring within 5 minutes.

QB-H1 (2026-08-28): Added transient/permanent error classification.
  - Transient (5xx / TransportError / timeout): log WARNING, leave connection
    ``active`` — the next beat cycle retries.
  - Permanent (invalid_grant / 400 / 401): mark ``expired`` + enqueue
    ``qb_connection_expired`` notification to the tenant owner.
  - All ``print()`` calls replaced with ``logger``.
  - ``intuit_tid`` logged on the token-endpoint call (CloudWatch Insights).

Design Reference: dev-docs/architecture-design/batch-designs/batch-qb-h1-design.md §F.1-F.2
"""

import asyncio
import base64
import logging
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import httpx
from pydantic import BaseModel
from sqlmodel import select

from app.models.system import AppService, IntegrationCredential
from core.celery_app import celery_app
from core.config import settings
from core.db import get_db
from core.encryption import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)


class TokenRefreshOutcome(StrEnum):
    """Outcome of a token refresh attempt."""

    REFRESHED = "refreshed"
    TRANSIENT_FAILURE = "transient_failure"  # 5xx / network — stays active
    PERMANENT_FAILURE = (
        "permanent_failure"  # invalid_grant / 400 / 401 — expired + notify
    )


class QuickBooksTokenResponse(BaseModel):
    """Response from QuickBooks token endpoint."""

    access_token: str
    refresh_token: str
    expires_in: int
    x_refresh_token_expires_in: int
    token_type: str = "Bearer"


def _classify_refresh_error(exc: Exception) -> TokenRefreshOutcome:
    """
    Classify a token-refresh exception as transient or permanent.

    - ``httpx.HTTPStatusError`` with 400/401 (or ``invalid_grant`` in the body)
      → ``PERMANENT_FAILURE`` (the refresh token is rejected; user must reconnect).
    - 5xx + ``httpx.TransportError`` / timeout → ``TRANSIENT_FAILURE``
      (Intuit blip or network issue; next beat retries).
    - Anything else → ``PERMANENT_FAILURE`` (fail-safe: unknown errors are
      treated as permanent to avoid silently retrying a dead token forever).

    Design: batch-qb-h1-design.md §F.1
    """
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code in (400, 401):
            return TokenRefreshOutcome.PERMANENT_FAILURE
        # Check for invalid_grant in the response body (Intuit sometimes
        # returns 400 with an OAuth error JSON body)
        try:
            body_text = exc.response.text
            if "invalid_grant" in body_text:
                return TokenRefreshOutcome.PERMANENT_FAILURE
        except Exception:
            pass
        if 500 <= status_code < 600:
            return TokenRefreshOutcome.TRANSIENT_FAILURE
        # Other 4xx (403, 404, 429) — treat as transient (retry-worthy)
        return TokenRefreshOutcome.TRANSIENT_FAILURE

    if isinstance(exc, (httpx.TransportError, httpx.TimeoutException)):
        return TokenRefreshOutcome.TRANSIENT_FAILURE

    # Unknown exception type — fail-safe to permanent
    return TokenRefreshOutcome.PERMANENT_FAILURE


async def _refresh_access_token(refresh_token: str) -> QuickBooksTokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        refresh_token: Plaintext refresh token (decrypted)

    Returns:
        QuickBooksTokenResponse with new tokens

    Raises:
        httpx.HTTPStatusError: If refresh fails
    """
    # Encode client credentials for Basic auth
    credentials = f"{settings.QUICKBOOKS_CLIENT_ID}:{settings.QUICKBOOKS_CLIENT_SECRET}"
    auth_header = base64.b64encode(credentials.encode()).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.QUICKBOOKS_TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        # QB-H1 Task 3: log the token-endpoint call + intuit_tid (arg-style)
        intuit_tid = response.headers.get("intuit_tid", "unknown")
        logger.info(
            "QBO token refresh call: POST %s | status=%d | intuit_tid=%s",
            settings.QUICKBOOKS_TOKEN_URL,
            response.status_code,
            intuit_tid,
        )
        response.raise_for_status()

        return QuickBooksTokenResponse(**response.json())


@celery_app.task(name="refresh_quickbooks_tokens")
def refresh_quickbooks_tokens_task():
    """
    Proactively refresh QuickBooks access tokens expiring within 5 minutes.

    This task runs every 30 minutes and checks all active QuickBooks connections
    for tokens that need refresh.

    QB-H1: Error classification (design §F.1):
    - Transient failure (5xx / network): log WARNING, leave ``active``, count
      ``transient_failed``. The next beat cycle retries.
    - Permanent failure (invalid_grant / 400 / 401): mark ``expired`` + enqueue
      ``qb_connection_expired`` notification to the tenant owner.

    Returns:
        Dict with refresh statistics (refreshed, failed, transient_failed)
    """
    db = next(get_db())

    try:
        # Find all active QuickBooks credentials expiring soon
        now = datetime.now(UTC)
        expiry_threshold = now + timedelta(minutes=5)

        stmt = (
            select(IntegrationCredential)
            .join(AppService)
            .where(
                AppService.provider_code == "quickbooks",
                IntegrationCredential.connection_status == "active",
                IntegrationCredential.expires_at < expiry_threshold,
            )
        )
        credentials = db.exec(stmt).all()

        refreshed_count = 0
        failed_count = 0
        transient_failed = 0

        for credential in credentials:
            try:
                # Decrypt refresh token
                refresh_token = decrypt_token(
                    credential.secret_json["refresh_token_encrypted"]
                )

                # Refresh via QuickBooks API (async operation)
                tokens = asyncio.run(_refresh_access_token(refresh_token))

                # Encrypt new tokens
                access_token_encrypted = encrypt_token(tokens.access_token)
                refresh_token_encrypted = encrypt_token(tokens.refresh_token)

                # Update credential
                expires_at = now + timedelta(seconds=tokens.expires_in)
                credential.secret_json["access_token_encrypted"] = (
                    access_token_encrypted
                )
                credential.secret_json["refresh_token_encrypted"] = (
                    refresh_token_encrypted
                )
                credential.expires_at = expires_at
                credential.last_refresh_at = now

                db.add(credential)
                refreshed_count += 1

            except Exception as e:
                outcome = _classify_refresh_error(e)

                if outcome == TokenRefreshOutcome.TRANSIENT_FAILURE:
                    # Leave connection active — next beat retries
                    logger.warning(
                        "Transient QB token refresh failure | tenant=%s "
                        "error=%s: %s — connection left active",
                        credential.tenant_id,
                        type(e).__name__,
                        e,
                    )
                    transient_failed += 1
                else:
                    # Permanent failure — mark expired + notify owner
                    logger.error(
                        "Permanent QB token refresh failure | tenant=%s "
                        "error=%s: %s — marking connection expired",
                        credential.tenant_id,
                        type(e).__name__,
                        e,
                    )
                    from services.qb_connection_notification import (
                        enqueue_connection_expired_notification,
                    )

                    enqueue_connection_expired_notification(db, credential)
                    failed_count += 1

        db.commit()

        return {
            "status": "completed",
            "refreshed": refreshed_count,
            "failed": failed_count,
            "transient_failed": transient_failed,
            "timestamp": now.isoformat(),
        }

    except Exception as e:
        db.rollback()
        logger.error("Error in refresh_quickbooks_tokens_task: %s", e)
        raise
    finally:
        db.close()
