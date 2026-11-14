"""
QuickBooks OAuth 2.0 integration endpoints.

Implements the OAuth 2.0 authorization code flow for QuickBooks Online (QBO):
1. /connect - Initiates OAuth flow with state token (CSRF protection)
2. /callback - Handles OAuth callback, exchanges code for tokens
3. /refresh - Refreshes expired access tokens (manual + background worker)
4. /disconnect - Disconnects QuickBooks integration
5. /status - Gets current connection status

Design Reference: Task #16 in phase-2-5-implementation-roadmap.md
Gap Reference: Gap #22 in phase-1-4-implementation-gap-analysis.md
Security: Tokens encrypted with Fernet (AES-128-CBC + HMAC), state token validation, tenant isolation
"""

import base64
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.system import AppService, IntegrationCredential, IntegrationSyncConflict
from core.auth import AuthenticatedUser
from core.config import settings
from core.db import get_db
from core.encryption import decrypt_token, encrypt_token
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.quickbooks_sync import QuickBooksSync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/quickbooks", tags=["integrations"])
sync_dashboard_router = APIRouter(
    prefix="/integrations/sync-dashboard", tags=["integrations"]
)


# ==================== PYDANTIC SCHEMAS ====================


class QuickBooksConnectionStatus(BaseModel):
    """QuickBooks connection status response."""

    is_connected: bool
    realm_id: str | None = None
    company_name: str | None = None
    connected_at: datetime | None = None
    expires_at: datetime | None = None
    connection_status: str


class QuickBooksTokenResponse(BaseModel):
    """Response from QuickBooks token endpoint."""

    access_token: str
    refresh_token: str
    expires_in: int
    x_refresh_token_expires_in: int
    token_type: str = "Bearer"


class ConflictListResponse(BaseModel):
    """Response schema for conflict listing."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    app_service_id: uuid.UUID
    entity_type_code: str
    entity_id: uuid.UUID
    external_id: str
    status: str
    internal_payload: dict
    external_payload: dict
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: uuid.UUID | None = None


class ConflictResolutionRequest(BaseModel):
    """Request schema for resolving a conflict."""

    strategy: str  # accept_local | accept_remote | merge
    merged_payload: dict | None = None  # Required if strategy=merge
    notes: str | None = None


class SyncDashboardResponse(BaseModel):
    """Response schema for the QuickBooks sync dashboard."""

    model_config = ConfigDict(from_attributes=True)

    quickbooks_connected: bool
    last_sync_at: datetime | None = None
    total_customers_mapped: int
    requires_attention_count: int


# ==================== SHARED BUSINESS LOGIC ====================


def _initiate_qbo_oauth_impl(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
) -> RedirectResponse:
    """
    Shared logic for initiating QuickBooks OAuth 2.0 Flow.
    """
    # Generate state token (UUID4 for security + uniqueness)
    state_token = str(uuid.uuid4())

    # Find or create QuickBooks AppService for this tenant
    stmt = select(AppService).where(
        AppService.tenant_id == tenant_id,
        AppService.provider_code == "quickbooks",
    )
    app_service = db.exec(stmt).first()

    if not app_service:
        # Create new QuickBooks service entry
        app_service = AppService(
            tenant_id=tenant_id,
            name="QuickBooks Online",
            category_code="accounting",
            provider_code="quickbooks",
            is_active=True,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(app_service)
        db.flush()

    # Store pending credential with state token
    # Note: Will be updated in callback with actual tokens
    credential = IntegrationCredential(
        tenant_id=tenant_id,
        app_service_id=app_service.id,
        secret_json={"state_token": state_token},
        connection_status="pending",
        initiated_by_user_id=user_id,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(credential)
    db.commit()

    # Build QuickBooks authorization URL
    auth_url = (
        f"{settings.QUICKBOOKS_AUTH_URL}?"
        f"client_id={settings.QUICKBOOKS_CLIENT_ID}&"
        f"redirect_uri={settings.QUICKBOOKS_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=com.intuit.quickbooks.accounting&"
        f"state={state_token}"
    )

    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


# ==================== OAUTH ENDPOINTS ====================


@router.get("/connect")
async def initiate_qbo_oauth(
    current_user: Annotated[
        AuthenticatedUser, Depends(require_permission("integrations.manage"))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    """
    Step 1: Initiate QuickBooks OAuth 2.0 Flow.

    Requires integrations.manage permission (owner only).

    Generates a cryptographically secure state token (CSRF protection),
    stores it in the database, and redirects the user to QuickBooks
    consent screen.

    Security:
    - Requires integrations.manage permission
    - State token prevents CSRF attacks
    - Expires in 10 minutes
    - One-time use (validated and consumed in callback)

    Returns:
        302 redirect to QuickBooks authorization URL
    """
    return _initiate_qbo_oauth_impl(current_user.tenant_id, current_user.user_id, db)


@router.get("/callback")
async def qbo_oauth_callback(
    code: str = Query(..., description="Authorization code from QuickBooks"),
    state: str = Query(..., description="State token for CSRF validation"),
    realmId: str = Query(..., description="QuickBooks Company ID"),  # noqa: N803
    db: Session = Depends(get_db),
):
    """
    Step 2: Handle QuickBooks OAuth Callback.

    Validates state token, exchanges authorization code for access/refresh tokens,
    encrypts and stores tokens, updates connection status to 'active'.

    Security:
    - Validates state token (CSRF protection)
    - Validates state token not expired (<10 minutes)
    - Encrypts tokens before storage (Fernet)
    - Enforces tenant isolation

    Returns:
        Redirect to frontend success page

    Raises:
        HTTPException: If state token invalid, expired, or token exchange fails
    """
    # Validate state token
    stmt = select(IntegrationCredential).where(
        IntegrationCredential.secret_json["state_token"].astext == state,
        IntegrationCredential.connection_status == "pending",
    )
    credential = db.exec(stmt).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token",
        )

    # Check if state token is expired (>10 minutes old)
    state_age = datetime.now(UTC) - credential.created_at
    if state_age.total_seconds() > 600:  # 10 minutes
        credential.connection_status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State token expired (>10 minutes). Please try again.",
        )

    # Exchange authorization code for tokens
    try:
        tokens = await _exchange_code_for_tokens(code)
    except Exception as e:
        credential.connection_status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to exchange authorization code: {e!s}",
        )

    # Encrypt tokens
    access_token_encrypted = encrypt_token(tokens.access_token)
    refresh_token_encrypted = encrypt_token(tokens.refresh_token)

    # Calculate expiration times
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=tokens.expires_in)

    # Update credential with encrypted tokens
    credential.secret_json = {
        "access_token_encrypted": access_token_encrypted,
        "refresh_token_encrypted": refresh_token_encrypted,
        "state_token": state,  # Keep for audit trail
    }
    credential.expires_at = expires_at
    credential.connected_at = now
    credential.last_refresh_at = now
    credential.connection_status = "active"
    credential.updated_by = credential.initiated_by_user_id

    # Update AppService with realm_id for webhook routing
    app_service = db.get(AppService, credential.app_service_id)
    if app_service:
        app_service.external_account_id = realmId
        app_service.updated_by = credential.initiated_by_user_id

    db.commit()

    # Return success response based on environment
    # In dev/test environments, return HTML success page
    # In production, redirect to frontend application
    if settings.ENVIRONMENT in ["dev", "qa"] or settings.TEST_ENDPOINT_ENABLED:
        # Return simple HTML success page for testing
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>QuickBooks Connected Successfully</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 2rem;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    text-align: center;
                    max-width: 500px;
                }}
                .success-icon {{
                    color: #10b981;
                    font-size: 48px;
                    margin-bottom: 1rem;
                }}
                h1 {{
                    color: #1f2937;
                    margin-bottom: 1rem;
                }}
                .details {{
                    background: #f3f4f6;
                    padding: 1rem;
                    border-radius: 4px;
                    margin: 1rem 0;
                    text-align: left;
                }}
                .detail-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 0.5rem 0;
                    border-bottom: 1px solid #e5e7eb;
                }}
                .detail-row:last-child {{
                    border-bottom: none;
                }}
                .label {{
                    font-weight: 600;
                    color: #6b7280;
                }}
                .value {{
                    color: #1f2937;
                    font-family: monospace;
                }}
                .note {{
                    color: #6b7280;
                    font-size: 14px;
                    margin-top: 1rem;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✓</div>
                <h1>QuickBooks Connected Successfully!</h1>
                <p>Your QuickBooks account has been connected to Pilot for Trades.</p>

                <div class="details">
                    <div class="detail-row">
                        <span class="label">Company ID:</span>
                        <span class="value">{realmId}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Status:</span>
                        <span class="value">Active</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Connected At:</span>
                        <span class="value">{now.isoformat()}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Token Expires:</span>
                        <span class="value">{expires_at.isoformat()}</span>
                    </div>
                </div>

                <p class="note">
                    You can close this window and return to testing.<br>
                    Tokens will be automatically refreshed every 30 minutes.
                </p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=200)
    else:
        # Production: Redirect to frontend application
        frontend_success_url = f"{settings.FRONTEND_URL}/settings/integrations?status=success&realmId={realmId}"
        return RedirectResponse(
            url=frontend_success_url, status_code=status.HTTP_302_FOUND
        )


async def _refresh_qbo_token_impl(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
) -> dict:
    """
    Shared logic for manually refreshing QuickBooks Access Token.

    QB-H1 (2026-08-28): Error classification (design §F.2):
    - Transient failure (5xx / network): raise HTTP 503 (RFC 7807), leave
      connection ``active`` — the next beat cycle retries.
    - Permanent failure (invalid_grant / 400 / 401): mark ``expired`` + enqueue
      ``qb_connection_expired`` notification to the tenant owner, then raise
      HTTP 500 (contract preserved for the API caller).
    """
    # Find active QuickBooks credential
    stmt = (
        select(IntegrationCredential)
        .join(AppService)
        .where(
            IntegrationCredential.tenant_id == tenant_id,
            AppService.provider_code == "quickbooks",
            IntegrationCredential.connection_status == "active",
        )
    )
    credential = db.exec(stmt).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Resource not found",
                "status": 404,
                "detail": "No active QuickBooks connection found.",
            },
        )

    # Check if token needs refresh (expires in <5 minutes)
    now = datetime.now(UTC)
    time_until_expiry = (credential.expires_at - now).total_seconds()

    if time_until_expiry > 300:  # >5 minutes
        return {
            "status": "not_needed",
            "expires_at": credential.expires_at.isoformat(),
            "seconds_until_expiry": int(time_until_expiry),
        }

    # Decrypt refresh token
    try:
        refresh_token = decrypt_token(credential.secret_json["refresh_token_encrypted"])
    except Exception as e:
        from services.qb_connection_notification import (
            enqueue_connection_expired_notification,
        )

        enqueue_connection_expired_notification(db, credential)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "https://errors.pilotfortrades.com/qb-refresh-failed",
                "title": "QuickBooks token refresh failed",
                "status": 500,
                "detail": f"Failed to decrypt refresh token: {e!s}",
            },
        )

    # Refresh tokens via QuickBooks API
    try:
        tokens = await _refresh_access_token(refresh_token)
    except Exception as e:
        from tasks.quickbooks_token_refresh import (
            TokenRefreshOutcome,
            _classify_refresh_error,
        )

        outcome = _classify_refresh_error(e)

        if outcome == TokenRefreshOutcome.TRANSIENT_FAILURE:
            # Leave connection active — raise 503 so the caller can retry
            logger.warning(
                "Transient QB token refresh failure (route) | tenant=%s error=%s: %s",
                tenant_id,
                type(e).__name__,
                e,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "type": "https://errors.pilotfortrades.com/qb-refresh-transient",
                    "title": "QuickBooks temporarily unavailable",
                    "status": 503,
                    "detail": (
                        "QuickBooks token refresh failed due to a transient "
                        "error. The connection remains active and will be "
                        "retried automatically."
                    ),
                },
            )
        else:
            # Permanent failure — mark expired + notify owner, then raise 500
            from services.qb_connection_notification import (
                enqueue_connection_expired_notification,
            )

            logger.error(
                "Permanent QB token refresh failure (route) | tenant=%s error=%s: %s",
                tenant_id,
                type(e).__name__,
                e,
            )
            enqueue_connection_expired_notification(db, credential)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "type": "https://errors.pilotfortrades.com/qb-refresh-failed",
                    "title": "QuickBooks connection expired",
                    "status": 500,
                    "detail": (
                        "QuickBooks token refresh failed permanently. "
                        "The connection has been marked expired and the "
                        "tenant owner has been notified. Please reconnect "
                        "via Settings → Integrations → QuickBooks."
                    ),
                },
            )

    # Encrypt new tokens
    access_token_encrypted = encrypt_token(tokens.access_token)
    refresh_token_encrypted = encrypt_token(tokens.refresh_token)

    # Update credential
    expires_at = now + timedelta(seconds=tokens.expires_in)
    credential.secret_json["access_token_encrypted"] = access_token_encrypted
    credential.secret_json["refresh_token_encrypted"] = refresh_token_encrypted
    credential.expires_at = expires_at
    credential.last_refresh_at = now
    credential.updated_by = user_id

    db.commit()

    return {
        "status": "refreshed",
        "expires_at": expires_at.isoformat(),
        "last_refresh_at": now.isoformat(),
    }


def _disconnect_qbo_impl(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
) -> dict:
    """
    Shared logic for disconnecting QuickBooks Integration.
    """
    # Find active QuickBooks credential
    stmt = (
        select(IntegrationCredential)
        .join(AppService)
        .where(
            IntegrationCredential.tenant_id == tenant_id,
            AppService.provider_code == "quickbooks",
            IntegrationCredential.connection_status == "active",
        )
    )
    credential = db.exec(stmt).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active QuickBooks connection found",
        )

    # Update connection status
    credential.connection_status = "disconnected"
    credential.disconnected_at = datetime.now(UTC)
    credential.updated_by = user_id

    # Optional: Revoke tokens via QuickBooks API
    # (Skipped for MVP - token will expire naturally in 1 hour)

    db.commit()

    return {
        "status": "disconnected",
        "disconnected_at": credential.disconnected_at.isoformat(),
        "message": "QuickBooks integration disconnected successfully",
    }


def _get_qbo_connection_status_impl(
    tenant_id: uuid.UUID,
    db: Session,
) -> QuickBooksConnectionStatus:
    """
    Shared logic to get QuickBooks connection status for a tenant.
    """
    # Find QuickBooks credential
    stmt = (
        select(IntegrationCredential, AppService)
        .join(AppService)
        .where(
            IntegrationCredential.tenant_id == tenant_id,
            AppService.provider_code == "quickbooks",
        )
        .order_by(IntegrationCredential.created_at.desc())
    )
    result = db.exec(stmt).first()

    if not result:
        return QuickBooksConnectionStatus(
            is_connected=False, connection_status="not_configured"
        )

    credential, app_service = result

    return QuickBooksConnectionStatus(
        is_connected=credential.connection_status == "active",
        realm_id=app_service.external_account_id,
        company_name=app_service.name,
        connected_at=credential.connected_at,
        expires_at=credential.expires_at,
        connection_status=credential.connection_status,
    )


@router.post("/refresh")
async def refresh_qbo_token(
    current_user: Annotated[
        AuthenticatedUser, Depends(require_permission("integrations.manage"))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    Step 3: Manually Refresh QuickBooks Access Token.

    Requires integrations.manage permission (owner only).

    Proactively refreshes the access token if it's expiring within 5 minutes.
    Also called by background Celery Beat task for automatic refresh.

    Returns:
        Dict with new expiration time and status

    Raises:
        HTTPException: If no active QuickBooks connection or refresh fails
    """
    return await _refresh_qbo_token_impl(
        current_user.tenant_id, current_user.user_id, db
    )


@router.delete("/disconnect")
async def disconnect_qbo(
    current_user: Annotated[
        AuthenticatedUser, Depends(require_permission("integrations.manage"))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    Step 4: Disconnect QuickBooks Integration.

    Requires integrations.manage permission (owner only).

    Marks the connection as 'disconnected' and sets disconnected_at timestamp.
    Preserves historical sync_mapping records (does NOT delete data).

    Optional: Can revoke tokens via QuickBooks API for extra security.

    Returns:
        Dict confirming disconnection

    Raises:
        HTTPException: If no active QuickBooks connection found
    """
    return _disconnect_qbo_impl(current_user.tenant_id, current_user.user_id, db)


@router.get("/status")
async def get_qbo_connection_status(
    current_user: Annotated[
        AuthenticatedUser, Depends(require_permission("integrations.view"))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> QuickBooksConnectionStatus:
    """
    Get QuickBooks connection status for current tenant.

    Requires integrations.view permission.

    Returns:
        QuickBooksConnectionStatus with connection details
    """
    return _get_qbo_connection_status_impl(current_user.tenant_id, db)


# ==================== TEST ENDPOINTS (UNAUTHENTICATED) ====================


@router.get("/connect/test")
async def initiate_qbo_oauth_test(
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    """
    TEST ENDPOINT: Initiate QuickBooks OAuth 2.0 Flow without JWT.

    Security:
    - Only available when TEST_ENDPOINT_ENABLED=true
    """
    test_context = get_test_context()
    return _initiate_qbo_oauth_impl(test_context.tenant_id, test_context.id, db)


@router.post("/refresh/test")
async def refresh_qbo_token_test(
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    TEST ENDPOINT: Manually Refresh QuickBooks Access Token without JWT.
    """
    test_context = get_test_context()
    return await _refresh_qbo_token_impl(test_context.tenant_id, test_context.id, db)


@router.delete("/disconnect/test")
async def disconnect_qbo_test(
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    TEST ENDPOINT: Disconnect QuickBooks Integration without JWT.
    """
    test_context = get_test_context()
    return _disconnect_qbo_impl(test_context.tenant_id, test_context.id, db)


@router.get("/status/test")
async def get_qbo_connection_status_test(
    db: Annotated[Session, Depends(get_db)],
) -> QuickBooksConnectionStatus:
    """
    TEST ENDPOINT: Get QuickBooks connection status without JWT.
    """
    test_context = get_test_context()
    return _get_qbo_connection_status_impl(test_context.tenant_id, db)


# ==================== HELPER FUNCTIONS ====================


async def _exchange_code_for_tokens(code: str) -> QuickBooksTokenResponse:
    """
    Exchange authorization code for access/refresh tokens.

    Args:
        code: Authorization code from QuickBooks callback

    Returns:
        QuickBooksTokenResponse with tokens and expiration times

    Raises:
        httpx.HTTPStatusError: If token exchange fails
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
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.QUICKBOOKS_REDIRECT_URI,
            },
        )
        # QB-H1 Task 3: log the OAuth callback token exchange + intuit_tid
        intuit_tid = response.headers.get("intuit_tid", "unknown")
        logger.info(
            "QBO token exchange call: POST %s | status=%d | intuit_tid=%s",
            settings.QUICKBOOKS_TOKEN_URL,
            response.status_code,
            intuit_tid,
        )
        response.raise_for_status()

        return QuickBooksTokenResponse(**response.json())


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
        # QB-H1 Task 3: log the token refresh call + intuit_tid
        intuit_tid = response.headers.get("intuit_tid", "unknown")
        logger.info(
            "QBO token refresh call: POST %s | status=%d | intuit_tid=%s",
            settings.QUICKBOOKS_TOKEN_URL,
            response.status_code,
            intuit_tid,
        )
        response.raise_for_status()

        return QuickBooksTokenResponse(**response.json())


# ==================== SYNC ENDPOINTS (TEST) ====================


@router.post("/sync/customers/test")
async def sync_customers_from_qb_test(
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    TEST ENDPOINT: Manually trigger customer sync from QuickBooks.

    Fetches all customers modified since the last sync timestamp
    (incremental sync) and creates/updates them in Pilot for Trades.

    Security:
    - Only available when TEST_ENDPOINT_ENABLED=true
    - Uses test tenant context

    Returns:
        Dict with sync results:
            - status: "success" or "error"
            - customers_synced: Number of customers synced
            - last_sync_at: Timestamp of previous sync (if any)
            - synced_at: Timestamp of this sync

    Raises:
        HTTPException: If QuickBooks not connected or sync fails
    """
    test_context = get_test_context()

    try:
        sync = QuickBooksSync(test_context.tenant_id, db)

        # Get last sync timestamp for incremental sync
        last_sync = await sync.get_last_sync_timestamp()

        # Perform incremental sync
        result = await sync.sync_all_customers_from_qb(since=last_sync)

        return {
            "status": "success",
            "customers_synced": result["synced"],
            "conflicts_detected": result["conflicts"],
            "sync_failures": result["failed"],
            "last_sync_at": last_sync.isoformat() if last_sync else None,
            "synced_at": datetime.now(UTC).isoformat(),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {e!s}",
        )


@router.get("/sync/status/test")
async def get_sync_status_test(
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    TEST ENDPOINT: Get QuickBooks sync status and statistics.

    Returns information about the last sync and total number of
    customers mapped to QuickBooks.

    Returns:
        Dict with sync status:
            - last_sync_at: Timestamp of last successful sync (or null)
            - total_customers_mapped: Number of customers with QB mappings
            - quickbooks_connected: Whether QB is connected
    """
    from app.models.system import IntegrationSyncMapping

    test_context = get_test_context()

    try:
        sync = QuickBooksSync(test_context.tenant_id, db)

        # Get last sync timestamp

        last_sync = await sync.get_last_sync_timestamp()

        # Count total customers mapped
        app_service_id = await sync._get_app_service_id()
        stmt = select(IntegrationSyncMapping).where(
            IntegrationSyncMapping.tenant_id == test_context.tenant_id,
            IntegrationSyncMapping.app_service_id == app_service_id,
            IntegrationSyncMapping.entity_type_code == "customer",
        )
        mappings = db.exec(stmt).all()

        return {
            "last_sync_at": last_sync.isoformat() if last_sync else None,
            "total_customers_mapped": len(mappings),
            "quickbooks_connected": True,
        }

    except ValueError:
        # QuickBooks not connected
        return {
            "last_sync_at": None,
            "total_customers_mapped": 0,
            "quickbooks_connected": False,
        }


# ==================== CONFLICT MANAGEMENT ENDPOINTS ====================


@router.get("/conflicts", response_model=list[ConflictListResponse])
async def list_quickbooks_conflicts(
    current_user: Annotated[
        AuthenticatedUser, Depends(require_permission("integrations.view"))
    ],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 20,
    status_filter: str | None = Query(None, alias="status"),
) -> list:
    """
    List QuickBooks sync conflicts for current tenant.

    Requires integrations.view permission.

    Query Parameters:
        skip: Offset for pagination (default: 0)
        limit: Max results (default: 20, max: 100)
        status: Filter by status (pending|resolved)

    Returns:
        List of conflict records with internal and external payloads

    Example:
        GET /api/v1/integrations/quickbooks/conflicts?status=pending&skip=0&limit=20
    """
    from app.models.system import AppService

    # Build query
    stmt = (
        select(IntegrationSyncConflict, AppService)
        .join(AppService, IntegrationSyncConflict.app_service_id == AppService.id)
        .where(
            IntegrationSyncConflict.tenant_id == current_user.tenant_id,
            AppService.provider_code == "quickbooks",
        )
        .order_by(IntegrationSyncConflict.created_at.desc())
        .offset(skip)
        .limit(min(limit, 100))
    )

    # Filter by status if provided
    if status_filter:
        if status_filter == "pending":
            stmt = stmt.where(IntegrationSyncConflict.resolved_at == None)
        elif status_filter == "resolved":
            stmt = stmt.where(IntegrationSyncConflict.resolved_at != None)

    results = db.exec(stmt).all()
    conflicts = [result[0] for result in results]

    return conflicts


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_quickbooks_conflict(
    conflict_id: uuid.UUID,
    resolution: ConflictResolutionRequest,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_permission("integrations.manage"))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    Resolve a QuickBooks sync conflict.

    Requires integrations.manage permission (owner only).

    Resolution strategies:
        - accept_local: Keep Pilot for Trades version, overwrite QuickBooks
        - accept_remote: Keep QuickBooks version, overwrite Pilot for Trades
        - merge: Apply user-provided merged data to both systems

    Args:
        conflict_id: UUID of the conflict to resolve
        resolution: Resolution strategy and optional merged payload

    Returns:
        Dict with resolution status and timestamp

    Raises:
        HTTPException 404: Conflict not found
        HTTPException 403: Access denied (wrong tenant)
        HTTPException 400: Invalid strategy or conflict already resolved

    Example:
        POST /api/v1/integrations/quickbooks/conflicts/{id}/resolve
        {
            "strategy": "accept_local",
            "notes": "Keep our version - QB data was outdated"
        }
    """
    from app.models.crm import Customer

    # Get conflict
    conflict = db.get(IntegrationSyncConflict, conflict_id)
    if not conflict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found"
        )

    # Verify tenant ownership
    if conflict.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    # Check if already resolved
    if conflict.resolved_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conflict already resolved at {conflict.resolved_at.isoformat()}",
        )

    # Validate strategy
    valid_strategies = ["accept_local", "accept_remote", "merge"]
    if resolution.strategy not in valid_strategies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid strategy. Must be one of: {', '.join(valid_strategies)}",
        )

    if resolution.strategy == "merge" and not resolution.merged_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="merged_payload required when strategy=merge",
        )

    # Initialize sync service
    sync = QuickBooksSync(current_user.tenant_id, db)

    try:
        # Apply resolution based on strategy
        if resolution.strategy == "accept_local":
            # CRITICAL: Update mapping with current QB SyncToken from conflict
            # The mapping has a STALE SyncToken (from before the conflict)
            # but QuickBooks requires the CURRENT SyncToken for updates
            from app.models.system import IntegrationSyncMapping

            stmt = select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.entity_id == conflict.entity_id,
                IntegrationSyncMapping.app_service_id == conflict.app_service_id,
                IntegrationSyncMapping.entity_type_code == "customer",
            )
            mapping = db.exec(stmt).first()
            if mapping:
                # Update with current SyncToken from QB (stored in conflict)
                qb_customer = conflict.external_payload
                mapping.external_version_token = qb_customer.get("SyncToken")
                db.add(mapping)
                db.commit()

            # Now sync Pilot for Trades → QuickBooks (will use updated SyncToken)
            await sync.sync_customer_to_qb(conflict.entity_id)

        elif resolution.strategy == "accept_remote":
            # Sync QuickBooks → Pilot for Trades (force overwrite)
            qb_customer = conflict.external_payload
            await sync.sync_customer_from_qb(qb_customer)

        elif resolution.strategy == "merge":
            # Apply merged data to Pilot for Trades first
            customer = db.get(Customer, conflict.entity_id)
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Customer {conflict.entity_id} not found",
                )

            # Update customer with merged data
            merged = resolution.merged_payload
            allowed_fields = {
                "display_name",
                "first_name",
                "last_name",
                "company_name",
                "email",
                "mobile_phone",
                "notes",
                "is_active",
            }

            for key, value in merged.items():
                if key in allowed_fields and hasattr(customer, key):
                    setattr(customer, key, value)

            db.add(customer)
            db.commit()
            db.refresh(customer)

            # CRITICAL: Update mapping with current QB SyncToken before sync
            from app.models.system import IntegrationSyncMapping

            stmt = select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.entity_id == conflict.entity_id,
                IntegrationSyncMapping.app_service_id == conflict.app_service_id,
                IntegrationSyncMapping.entity_type_code == "customer",
            )
            mapping = db.exec(stmt).first()
            if mapping:
                qb_customer = conflict.external_payload
                mapping.external_version_token = qb_customer.get("SyncToken")
                db.add(mapping)
                db.commit()

            # Now sync merged data to QuickBooks
            await sync.sync_customer_to_qb(conflict.entity_id)

        # Mark conflict as resolved with appropriate status
        conflict.resolved_at = datetime.now(UTC)
        conflict.resolved_by = current_user.user_id

        # Map resolution strategy to status (per CHECK constraint)
        if resolution.strategy == "accept_local" or resolution.strategy == "merge":
            conflict.status = "resolved_keep_internal"
        elif resolution.strategy == "accept_remote":
            conflict.status = "resolved_keep_external"

        db.add(conflict)
        db.commit()
        db.refresh(conflict)

        return {
            "status": conflict.status,
            "conflict_id": str(conflict.id),
            "resolution_strategy": resolution.strategy,
            "resolved_at": conflict.resolved_at.isoformat(),
            "resolved_by": str(current_user.user_id),
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conflict resolution failed: {e!s}",
        )


# ==================== TEST ENDPOINTS ====================


@router.get("/conflicts/test", response_model=list[ConflictListResponse])
async def list_quickbooks_conflicts_test(
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 20,
    status_filter: str | None = Query(None, alias="status"),
) -> list:
    """
    TEST ENDPOINT: List QuickBooks sync conflicts for test tenant.

    Uses test context instead of authentication for testing purposes.
    """
    from app.models.system import AppService

    test_context = get_test_context()

    # Build query
    stmt = (
        select(IntegrationSyncConflict, AppService)
        .join(AppService, IntegrationSyncConflict.app_service_id == AppService.id)
        .where(
            IntegrationSyncConflict.tenant_id == test_context.tenant_id,
            AppService.provider_code == "quickbooks",
        )
        .order_by(IntegrationSyncConflict.created_at.desc())
        .offset(skip)
        .limit(min(limit, 100))
    )

    # Filter by status if provided
    if status_filter:
        if status_filter == "pending":
            stmt = stmt.where(IntegrationSyncConflict.resolved_at == None)
        elif status_filter == "resolved":
            stmt = stmt.where(IntegrationSyncConflict.resolved_at != None)

    results = db.exec(stmt).all()
    conflicts = [result[0] for result in results]

    return conflicts


@router.post("/conflicts/{conflict_id}/resolve/test")
async def resolve_quickbooks_conflict_test(
    conflict_id: uuid.UUID,
    resolution: ConflictResolutionRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    TEST ENDPOINT: Resolve a QuickBooks sync conflict.

    Uses test context instead of authentication for testing purposes.
    """
    from app.models.crm import Customer

    test_context = get_test_context()

    # Get conflict
    conflict = db.get(IntegrationSyncConflict, conflict_id)
    if not conflict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found"
        )

    # Verify tenant ownership
    if conflict.tenant_id != test_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    # Check if already resolved
    if conflict.resolved_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conflict already resolved at {conflict.resolved_at.isoformat()}",
        )

    # Validate strategy
    valid_strategies = ["accept_local", "accept_remote", "merge"]
    if resolution.strategy not in valid_strategies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid strategy. Must be one of: {', '.join(valid_strategies)}",
        )

    if resolution.strategy == "merge" and not resolution.merged_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="merged_payload required when strategy=merge",
        )

    # Initialize sync service
    sync = QuickBooksSync(test_context.tenant_id, db)

    try:
        # Apply resolution based on strategy
        if resolution.strategy == "accept_local":
            # CRITICAL: Update mapping with current QB SyncToken from conflict
            # The mapping has a STALE SyncToken (from before the conflict)
            # but QuickBooks requires the CURRENT SyncToken for updates
            from sqlmodel import select

            from app.models.system import IntegrationSyncMapping

            stmt = select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.entity_id == conflict.entity_id,
                IntegrationSyncMapping.app_service_id == conflict.app_service_id,
                IntegrationSyncMapping.entity_type_code == "customer",
            )
            mapping = db.exec(stmt).first()
            if mapping:
                # Update with current SyncToken from QB (stored in conflict)
                qb_customer = conflict.external_payload
                mapping.external_version_token = qb_customer.get("SyncToken")
                db.add(mapping)
                db.commit()

            # Now sync Pilot for Trades → QuickBooks (will use updated SyncToken)
            await sync.sync_customer_to_qb(conflict.entity_id)

        elif resolution.strategy == "accept_remote":
            # Sync QuickBooks → Pilot for Trades (force overwrite)
            # NOTE: We cannot use sync_customer_from_qb() because it has conflict
            # detection that would re-detect this same conflict. Instead, manually
            # apply the external payload to the customer.
            customer = db.get(Customer, conflict.entity_id)
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Customer {conflict.entity_id} not found",
                )

            qb_customer = conflict.external_payload

            # Update customer with QuickBooks data
            customer.display_name = qb_customer.get(
                "DisplayName", customer.display_name
            )
            if "GivenName" in qb_customer:
                customer.first_name = qb_customer["GivenName"]
            if "FamilyName" in qb_customer:
                customer.last_name = qb_customer["FamilyName"]
            if "CompanyName" in qb_customer:
                customer.company_name = qb_customer["CompanyName"]
            if "PrimaryEmailAddr" in qb_customer:
                customer.email = qb_customer["PrimaryEmailAddr"].get("Address")
            if "PrimaryPhone" in qb_customer:
                customer.mobile_phone = qb_customer["PrimaryPhone"].get(
                    "FreeFormNumber"
                )
            if "Notes" in qb_customer:
                customer.notes = qb_customer["Notes"]
            if "Active" in qb_customer:
                customer.is_active = qb_customer["Active"]

            db.add(customer)
            db.commit()
            db.refresh(customer)

            # Update the sync mapping to reflect the resolution
            from sqlmodel import select

            from app.models.system import IntegrationSyncMapping

            stmt = select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.entity_id == customer.id,
                IntegrationSyncMapping.app_service_id == conflict.app_service_id,
                IntegrationSyncMapping.entity_type_code == "customer",
            )
            mapping = db.exec(stmt).first()
            if mapping:
                mapping.external_version_token = qb_customer.get(
                    "SyncToken", mapping.external_version_token
                )
                mapping.internal_version_token = customer.updated_at.isoformat()
                mapping.last_synced_at = datetime.now(UTC)
                db.add(mapping)
                db.commit()

        elif resolution.strategy == "merge":
            # Apply merged data to Pilot for Trades first
            customer = db.get(Customer, conflict.entity_id)
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Customer {conflict.entity_id} not found",
                )

            # Update customer with merged data
            merged = resolution.merged_payload
            allowed_fields = {
                "display_name",
                "first_name",
                "last_name",
                "company_name",
                "email",
                "mobile_phone",
                "notes",
                "is_active",
            }

            for key, value in merged.items():
                if key in allowed_fields and hasattr(customer, key):
                    setattr(customer, key, value)

            db.add(customer)
            db.commit()
            db.refresh(customer)

            # CRITICAL: Update mapping with current QB SyncToken before sync
            from sqlmodel import select

            from app.models.system import IntegrationSyncMapping

            stmt = select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.entity_id == conflict.entity_id,
                IntegrationSyncMapping.app_service_id == conflict.app_service_id,
                IntegrationSyncMapping.entity_type_code == "customer",
            )
            mapping = db.exec(stmt).first()
            if mapping:
                qb_customer = conflict.external_payload
                mapping.external_version_token = qb_customer.get("SyncToken")
                db.add(mapping)
                db.commit()

            # Now sync merged data to QuickBooks
            await sync.sync_customer_to_qb(conflict.entity_id)

        # Mark conflict as resolved with appropriate status
        conflict.resolved_at = datetime.now(UTC)
        conflict.resolved_by = test_context.id

        # Map resolution strategy to status (per CHECK constraint)
        if resolution.strategy == "accept_local" or resolution.strategy == "merge":
            conflict.status = "resolved_keep_internal"
        elif resolution.strategy == "accept_remote":
            conflict.status = "resolved_keep_external"

        db.add(conflict)
        db.commit()
        db.refresh(conflict)

        return {
            "status": conflict.status,
            "conflict_id": str(conflict.id),
            "resolution_strategy": resolution.strategy,
            "resolved_at": conflict.resolved_at.isoformat(),
            "resolved_by": str(test_context.id),
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conflict resolution failed: {e!s}",
        )


@router.post("/sync/customer/{customer_id}/test")
async def sync_customer_to_qb_test(
    customer_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    TEST ENDPOINT: Manually push Pilot for Trades customer to QuickBooks.

    Creates or updates the customer in QuickBooks and updates
    the integration_sync_mapping table.

    Args:
        customer_id: UUID of the Pilot for Trades customer to sync

    Returns:
        Dict with sync results:
            - status: "success"
            - customer_id: Pilot for Trades customer ID
            - qb_customer_id: QuickBooks customer ID
            - qb_sync_token: QuickBooks SyncToken
            - synced_at: Timestamp of sync

    Raises:
        HTTPException: If customer not found or sync fails
    """
    test_context = get_test_context()

    try:
        sync = QuickBooksSync(test_context.tenant_id, db)

        # Sync customer to QuickBooks
        qb_customer = await sync.sync_customer_to_qb(customer_id)

        return {
            "status": "success",
            "customer_id": str(customer_id),
            "qb_customer_id": qb_customer.get("Id"),
            "qb_sync_token": qb_customer.get("SyncToken"),
            "qb_display_name": qb_customer.get("DisplayName"),
            "synced_at": datetime.now(UTC).isoformat(),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {e!s}",
        )


# ==================== SYNC DASHBOARD ====================


def _get_sync_dashboard_impl(
    db: Session,
    user_context,
) -> SyncDashboardResponse:
    """
    Shared logic for the sync dashboard.

    Queries:
    - QB connection status
    - Last sync timestamp
    - Total active customer mappings
    - Pending conflict count (uses idx_isc_tenant_status index)

    Args:
        db: Database session
        user_context: AuthenticatedUser or TestUserContext

    Returns:
        SyncDashboardResponse
    """
    from app.models.system import IntegrationSyncMapping

    # --- QB connection status -----------------------------------------------
    connection_status = _get_qbo_connection_status_impl(user_context.tenant_id, db)
    quickbooks_connected = connection_status.is_connected

    last_sync_at: datetime | None = None
    total_customers_mapped: int = 0

    # --- Mapping stats (direct SQL — no async needed) -----------------------
    # Find the QB AppService for this tenant (same logic as QuickBooksSync._get_app_service_id)
    app_service_stmt = select(AppService).where(
        AppService.tenant_id == user_context.tenant_id,
        AppService.provider_code == "quickbooks",
    )
    qb_app_service = db.exec(app_service_stmt).first()

    if qb_app_service:
        # Last sync timestamp = most recent last_synced_at among customer mappings
        last_mapping_stmt = (
            select(IntegrationSyncMapping)
            .where(
                IntegrationSyncMapping.tenant_id == user_context.tenant_id,
                IntegrationSyncMapping.app_service_id == qb_app_service.id,
                IntegrationSyncMapping.entity_type_code == "customer",
            )
            .order_by(IntegrationSyncMapping.last_synced_at.desc())
            .limit(1)
        )
        last_mapping = db.exec(last_mapping_stmt).first()
        if last_mapping:
            last_sync_at = last_mapping.last_synced_at

        # Total active customer mappings
        mappings_count = db.exec(
            select(func.count())
            .select_from(IntegrationSyncMapping)
            .where(
                IntegrationSyncMapping.tenant_id == user_context.tenant_id,
                IntegrationSyncMapping.app_service_id == qb_app_service.id,
                IntegrationSyncMapping.entity_type_code == "customer",
            )
        ).one()
        total_customers_mapped = mappings_count

    # --- Pending conflicts count (leverages idx_isc_tenant_status) ----------
    requires_attention_count = db.exec(
        select(func.count())
        .select_from(IntegrationSyncConflict)
        .where(
            IntegrationSyncConflict.tenant_id == user_context.tenant_id,
            IntegrationSyncConflict.status == "pending",
        )
    ).one()

    return SyncDashboardResponse(
        quickbooks_connected=quickbooks_connected,
        last_sync_at=last_sync_at,
        total_customers_mapped=total_customers_mapped,
        requires_attention_count=requires_attention_count,
    )


# ==================== SYNC DASHBOARD ENDPOINTS (register /test FIRST) ====================


@sync_dashboard_router.get("/test", response_model=SyncDashboardResponse)
def get_sync_dashboard_test(
    db: Session = Depends(get_db),
) -> SyncDashboardResponse:
    """
    TEST ENDPOINT: QuickBooks sync dashboard — no auth required.

    Blocked in staging/production (TEST_ENDPOINT_ENABLED must be true).
    """
    test_context = get_test_context()
    return _get_sync_dashboard_impl(db, test_context)


@sync_dashboard_router.get("/", response_model=SyncDashboardResponse)
def get_sync_dashboard(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("integrations.view")),
) -> SyncDashboardResponse:
    """
    GET /integrations/sync-dashboard

    Returns the QuickBooks sync dashboard with pending conflict count.
    Requires integrations.view permission.
    """
    return _get_sync_dashboard_impl(db, current_user)


# ==================== A49/A50: QB CONFLICT QUEUE (diff-aware, qb_conflict.view RBAC) ====================
# These replace the pre-B8 conflict endpoints with new diff-aware schemas and RBAC.
# Pre-B8 endpoints (integrations.view) remain for backward compat.


class QbConflictListItem(BaseModel):
    """A49: QB conflict list item with diff summary."""

    model_config = ConfigDict(from_attributes=True)

    conflict_id: uuid.UUID
    entity_type: str
    entity_identifier: str
    entity_summary: str
    master_direction: str
    pilot_change_summary: str
    qb_change_summary: str
    detected_at: datetime
    financial_delta_cents: int | None = None
    affected_entity_url: str | None = None
    auto_expire_at: datetime | None = None
    pre_warning_at: datetime | None = None


class QbConflictListResponse(BaseModel):
    """A49: QB conflict list response."""

    items: list[QbConflictListItem]
    total: int
    offset: int
    limit: int


class QbConflictDetailResponse(BaseModel):
    """A49: QB conflict detail with full diff payload."""

    model_config = ConfigDict(from_attributes=True)

    conflict_id: uuid.UUID
    entity_type: str
    base_snapshot: dict
    pilot_snapshot: dict
    qb_snapshot: dict
    field_diffs: list[dict]
    master_direction: str
    master_recommended_action: str
    conflict_subtype: str
    available_resolutions: list[str]
    financial_delta_payload: dict | None = None
    tax_period_warning: bool
    auto_expire_at: datetime | None = None
    pre_warning_at: datetime | None = None


class QbConflictHistoryItem(BaseModel):
    """A49/A50: QB conflict history item."""

    model_config = ConfigDict(from_attributes=True)

    conflict_id: uuid.UUID
    entity_type: str
    entity_identifier: str
    detected_at: datetime
    resolved_at: datetime | None = None
    resolver_user_id: uuid.UUID | None = None
    resolution_action: str | None = None
    status: str


class QbConflictHistoryResponse(BaseModel):
    """A49: QB conflict history response."""

    items: list[QbConflictHistoryItem]
    total: int
    offset: int
    limit: int


class QbConflictResolveRequest(BaseModel):
    """A50: QB conflict resolution request."""

    resolution: str  # accept_local | accept_remote | restore_and_accept_remote | recreate_and_keep_local | delete_both
    expected_pilot_modified_at: datetime | None = None
    expected_qb_modified_at: datetime | None = None


class QbConflictResolveResponse(BaseModel):
    """A50: QB conflict resolution response."""

    committed: bool
    resolution_outcome: str
    post_commit_state: dict | None = None
    push_to_other_side_dispatched: bool = False


# ---------------------------------------------------------------------------
# A49 Shared implementation
# ---------------------------------------------------------------------------


def _qb_conflict_list_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    entity_type_filter: str | None = None,
    status_filter: str = "pending",
    limit: int = 25,
    offset: int = 0,
) -> QbConflictListResponse:
    """A49: List QB conflicts with diff-aware summary."""
    from app.models.system import AppService
    from services.qb_conflict_diff import build_entity_summary, compute_financial_delta

    stmt = (
        select(IntegrationSyncConflict, AppService)
        .join(AppService, IntegrationSyncConflict.app_service_id == AppService.id)
        .where(
            IntegrationSyncConflict.tenant_id == user_context.tenant_id,
            AppService.provider_code == "quickbooks",
        )
        .order_by(IntegrationSyncConflict.created_at.desc())
    )

    if entity_type_filter:
        stmt = stmt.where(
            IntegrationSyncConflict.entity_type_code == entity_type_filter
        )

    if status_filter == "pending":
        stmt = stmt.where(IntegrationSyncConflict.status == "pending")
    elif status_filter == "resolved":
        stmt = stmt.where(IntegrationSyncConflict.status != "pending")

    count_stmt = (
        select(func.count())
        .select_from(IntegrationSyncConflict)
        .join(AppService, IntegrationSyncConflict.app_service_id == AppService.id)
        .where(
            IntegrationSyncConflict.tenant_id == user_context.tenant_id,
            AppService.provider_code == "quickbooks",
        )
    )
    if entity_type_filter:
        count_stmt = count_stmt.where(
            IntegrationSyncConflict.entity_type_code == entity_type_filter
        )
    total = db.exec(count_stmt).one()

    results = db.exec(stmt.offset(offset).limit(limit)).all()
    conflicts = [r[0] for r in results]

    items = []
    for conflict in conflicts:
        entity_type = conflict.entity_type_code
        pilot_snap = conflict.internal_payload or {}
        qb_snap = conflict.external_payload or {}
        pilot_summary, qb_summary = build_entity_summary(
            entity_type, pilot_snap, qb_snap
        )
        financial_delta = compute_financial_delta(entity_type, pilot_snap, qb_snap)

        items.append(
            QbConflictListItem(
                conflict_id=conflict.id,
                entity_type=entity_type,
                entity_identifier=conflict.external_id,
                entity_summary=f"{entity_type.title()} #{conflict.external_id}",
                master_direction="user_choice",
                pilot_change_summary=pilot_summary,
                qb_change_summary=qb_summary,
                detected_at=conflict.created_at,
                financial_delta_cents=financial_delta,
                auto_expire_at=getattr(conflict, "auto_expire_at", None),
                pre_warning_at=getattr(conflict, "pre_warning_at", None),
            )
        )

    return QbConflictListResponse(items=items, total=total, offset=offset, limit=limit)


def _qb_conflict_detail_impl(
    conflict_id: uuid.UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QbConflictDetailResponse:
    """A49: QB conflict detail with full diff payload."""
    from app.models.system import AppService
    from services.qb_conflict_diff import (
        compute_financial_delta,
        compute_qb_field_diffs,
        detect_tax_period_warning,
    )

    stmt = (
        select(IntegrationSyncConflict, AppService)
        .join(AppService, IntegrationSyncConflict.app_service_id == AppService.id)
        .where(
            IntegrationSyncConflict.id == conflict_id,
            IntegrationSyncConflict.tenant_id == user_context.tenant_id,
            AppService.provider_code == "quickbooks",
        )
    )
    result = db.exec(stmt).first()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found"
        )

    conflict = result[0]
    entity_type = conflict.entity_type_code
    pilot_snap = conflict.internal_payload or {}
    qb_snap = conflict.external_payload or {}
    base_snap = getattr(conflict, "base_snapshot", {}) or {}

    field_diffs = compute_qb_field_diffs(entity_type, pilot_snap, qb_snap)
    financial_delta = compute_financial_delta(entity_type, pilot_snap, qb_snap)
    tax_warning = detect_tax_period_warning(entity_type, qb_snap)

    available = ["accept_local", "accept_remote"]
    if entity_type in ("customer", "invoice"):
        available.append("restore_and_accept_remote")
        available.append("recreate_and_keep_local")
    available.append("delete_both")

    financial_payload = None
    if financial_delta is not None:
        financial_payload = {
            "financial_delta_cents": financial_delta,
            "direction": "pilot_higher"
            if financial_delta > 0
            else ("qb_higher" if financial_delta < 0 else "equal"),
        }

    return QbConflictDetailResponse(
        conflict_id=conflict.id,
        entity_type=entity_type,
        base_snapshot=base_snap,
        pilot_snapshot=pilot_snap,
        qb_snapshot=qb_snap,
        field_diffs=field_diffs,
        master_direction="user_choice",
        master_recommended_action="review_and_resolve",
        conflict_subtype="field_diff",
        available_resolutions=available,
        financial_delta_payload=financial_payload,
        tax_period_warning=tax_warning,
        auto_expire_at=getattr(conflict, "auto_expire_at", None),
        pre_warning_at=getattr(conflict, "pre_warning_at", None),
    )


def _qb_conflict_history_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    entity_type_filter: str | None = None,
    resolved_at_after: datetime | None = None,
    resolved_at_before: datetime | None = None,
    limit: int = 25,
    offset: int = 0,
) -> QbConflictHistoryResponse:
    """A49: QB conflict history — resolved/expired conflicts."""
    from app.models.system import AppService

    stmt = (
        select(IntegrationSyncConflict, AppService)
        .join(AppService, IntegrationSyncConflict.app_service_id == AppService.id)
        .where(
            IntegrationSyncConflict.tenant_id == user_context.tenant_id,
            AppService.provider_code == "quickbooks",
            IntegrationSyncConflict.status != "pending",
        )
        .order_by(IntegrationSyncConflict.resolved_at.desc())
    )

    if entity_type_filter:
        stmt = stmt.where(
            IntegrationSyncConflict.entity_type_code == entity_type_filter
        )
    if resolved_at_after:
        stmt = stmt.where(IntegrationSyncConflict.resolved_at >= resolved_at_after)
    if resolved_at_before:
        stmt = stmt.where(IntegrationSyncConflict.resolved_at <= resolved_at_before)

    count_stmt = (
        select(func.count())
        .select_from(IntegrationSyncConflict)
        .join(AppService, IntegrationSyncConflict.app_service_id == AppService.id)
        .where(
            IntegrationSyncConflict.tenant_id == user_context.tenant_id,
            AppService.provider_code == "quickbooks",
            IntegrationSyncConflict.status != "pending",
        )
    )
    total = db.exec(count_stmt).one()

    results = db.exec(stmt.offset(offset).limit(limit)).all()
    conflicts = [r[0] for r in results]

    items = [
        QbConflictHistoryItem(
            conflict_id=c.id,
            entity_type=c.entity_type_code,
            entity_identifier=c.external_id,
            detected_at=c.created_at,
            resolved_at=c.resolved_at,
            resolver_user_id=c.resolved_by,
            resolution_action=c.status,
            status=c.status,
        )
        for c in conflicts
    ]
    return QbConflictHistoryResponse(
        items=items, total=total, offset=offset, limit=limit
    )


# ---------------------------------------------------------------------------
# A49/A50: TEST endpoints (registered FIRST per §8.2)
# ---------------------------------------------------------------------------


@router.get(
    "/conflicts/b8/test",
    response_model=QbConflictListResponse,
    summary="[TEST] A49: List QB conflicts with diff summary (no JWT)",
)
def list_qb_conflicts_b8_test(
    entity_type: str | None = None,
    status_filter: str = "pending",
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _qb_conflict_list_impl(
        db,
        test_context,
        entity_type_filter=entity_type,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/conflicts/b8/history/test",
    response_model=QbConflictHistoryResponse,
    summary="[TEST] A49: QB conflict history (no JWT)",
)
def list_qb_conflict_history_test(
    entity_type: str | None = None,
    resolved_at_after: datetime | None = None,
    resolved_at_before: datetime | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required."""
    test_context = get_test_context()
    return _qb_conflict_history_impl(
        db,
        test_context,
        entity_type_filter=entity_type,
        resolved_at_after=resolved_at_after,
        resolved_at_before=resolved_at_before,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/conflicts/b8/{conflict_id}/test",
    response_model=QbConflictDetailResponse,
    summary="[TEST] A49: QB conflict detail (no JWT)",
)
def get_qb_conflict_b8_detail_test(
    conflict_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required."""
    test_context = get_test_context()
    return _qb_conflict_detail_impl(conflict_id, db, test_context)


@router.post(
    "/conflicts/b8/{conflict_id}/resolve/test",
    response_model=QbConflictResolveResponse,
    summary="[TEST] A50: Resolve QB conflict (no JWT)",
)
def resolve_qb_conflict_b8_test(
    conflict_id: uuid.UUID,
    data: QbConflictResolveRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required."""
    test_context = get_test_context()
    return _resolve_qb_conflict_impl(conflict_id, data, db, test_context)


# ---------------------------------------------------------------------------
# A49/A50: Authenticated endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/conflicts/b8",
    response_model=QbConflictListResponse,
    summary="A49: List QB conflicts with diff summary",
)
def list_qb_conflicts_b8(
    entity_type: str | None = None,
    status_filter: str = "pending",
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("qb_conflict.view")),
):
    """
    A49: List QB sync conflicts with field-diff summaries.

    Requires qb_conflict.view permission (owner, accountant roles).
    Filters: entity_type (customer|quote|invoice|expense), status (pending|resolved)
    """
    return _qb_conflict_list_impl(
        db,
        current_user,
        entity_type_filter=entity_type,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/conflicts/b8/history",
    response_model=QbConflictHistoryResponse,
    summary="A49: QB conflict history archive",
)
def list_qb_conflict_history(
    entity_type: str | None = None,
    resolved_at_after: datetime | None = None,
    resolved_at_before: datetime | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("qb_conflict.view")),
):
    """A49: Historical archive of resolved QB conflicts."""
    return _qb_conflict_history_impl(
        db,
        current_user,
        entity_type_filter=entity_type,
        resolved_at_after=resolved_at_after,
        resolved_at_before=resolved_at_before,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/conflicts/b8/{conflict_id}",
    response_model=QbConflictDetailResponse,
    summary="A49: QB conflict detail with full diff payload",
)
def get_qb_conflict_b8_detail(
    conflict_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("qb_conflict.view")),
):
    """
    A49: Get QB conflict detail with full field-diff payload.
    Includes base_snapshot, pilot_snapshot, qb_snapshot, field_diffs, financial_delta.
    """
    return _qb_conflict_detail_impl(conflict_id, db, current_user)


@router.post(
    "/conflicts/b8/{conflict_id}/resolve",
    response_model=QbConflictResolveResponse,
    summary="A50: Resolve QB conflict",
)
def resolve_qb_conflict_b8(
    conflict_id: uuid.UUID,
    data: QbConflictResolveRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("qb_conflict.resolve")
    ),
):
    """
    A50: Resolve a QB sync conflict.

    Resolution variants: accept_local | accept_remote | restore_and_accept_remote |
                         recreate_and_keep_local | delete_both

    409 shapes:
      - server_changed: pilot or QB side changed since viewed
      - auto_recovered: conflict was auto-resolved before you acted
    """
    return _resolve_qb_conflict_impl(conflict_id, data, db, current_user)


# ---------------------------------------------------------------------------
# A50: QB conflict resolution implementation
# ---------------------------------------------------------------------------


def _resolve_qb_conflict_impl(
    conflict_id: uuid.UUID,
    data: QbConflictResolveRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QbConflictResolveResponse:
    """A50: Resolve a QB conflict with dual-timestamp staleness check."""
    from app.models.system import AppService
    from utils.staleness_check import assert_not_stale_dual

    valid_resolutions = {
        "accept_local",
        "accept_remote",
        "restore_and_accept_remote",
        "recreate_and_keep_local",
        "delete_both",
    }
    if data.resolution not in valid_resolutions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid resolution. Must be one of: {sorted(valid_resolutions)}",
        )

    stmt = (
        select(IntegrationSyncConflict, AppService)
        .join(AppService, IntegrationSyncConflict.app_service_id == AppService.id)
        .where(
            IntegrationSyncConflict.id == conflict_id,
            IntegrationSyncConflict.tenant_id == user_context.tenant_id,
            AppService.provider_code == "quickbooks",
        )
    )
    result = db.exec(stmt).first()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found"
        )

    conflict = result[0]

    # A50: auto_recovered check
    if conflict.status not in ("pending",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "staleness_type": "auto_recovered",
                "auto_recovery_outcome": conflict.status,
                "message": f"This conflict was already resolved (status: {conflict.status}).",
            },
        )

    # A50: dual-timestamp staleness check via B8 utility
    pilot_modified_at = getattr(conflict, "pilot_modified_at", None)
    qb_modified_at = getattr(conflict, "qb_modified_at", None)

    if pilot_modified_at and qb_modified_at:
        assert_not_stale_dual(
            expected_pilot_modified_at=data.expected_pilot_modified_at,
            actual_pilot_modified_at=pilot_modified_at,
            expected_qb_modified_at=data.expected_qb_modified_at,
            actual_qb_modified_at=qb_modified_at,
            refreshed_payload=_qb_conflict_detail_impl(
                conflict_id, db, user_context
            ).model_dump(),
        )

    now = datetime.now(UTC)

    # Map resolution to status
    if data.resolution == "accept_local":
        conflict.status = "resolved_keep_internal"
    elif data.resolution == "accept_remote":
        conflict.status = "resolved_keep_external"
    elif data.resolution in (
        "restore_and_accept_remote",
        "recreate_and_keep_local",
        "delete_both",
    ):
        conflict.status = "resolved_keep_internal"  # simplified for MVP
    else:
        conflict.status = "resolved_keep_internal"

    conflict.resolved_at = now
    conflict.resolved_by = user_context.id

    db.add(conflict)
    db.commit()
    db.refresh(conflict)

    logger.info(
        "QB conflict %s resolved by user %s with action %s",
        conflict_id,
        user_context.id,
        data.resolution,
    )

    return QbConflictResolveResponse(
        committed=True,
        resolution_outcome=data.resolution,
        post_commit_state={"status": conflict.status},
        push_to_other_side_dispatched=False,  # Full QB push sync in B10
    )
