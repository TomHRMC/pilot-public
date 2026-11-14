"""
Google Calendar OAuth 2.0 integration endpoints.  Task 1-D-1.

Flow:
  1. GET  /api/v1/integrations/calendar/auth          — initiates OAuth, redirects to Google
  2. GET  /api/v1/integrations/calendar/callback      — exchanges code for tokens, stores encrypted
  3. GET  /api/v1/integrations/calendar/status        — returns connection status for tenant
  4. DELETE /api/v1/integrations/calendar/disconnect  — pauses / clears the integration

State token design:
  - A Fernet-encrypted JSON blob encoding {tenant_id, user_id, exp_iso}
  - Provides CSRF protection without a Redis dependency
  - Validated on callback; rejected if expired (>10 min) or tampered

Security:
  - Tokens (access + refresh) encrypted with Fernet before DB write (LargeBinary / bytea)
  - tenant_id enforced on every query (IDOR guard)
  - Test endpoints blocked in staging/production
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc as sa_desc
from sqlmodel import Session, select

from app.models.scheduling import CalendarSyncLog, TenantCalendarIntegration
from core.auth import AuthenticatedUser
from core.config import settings
from core.db import get_db, set_audit_context_sync
from core.encryption import encrypt_token
from core.permissions import require_permission
from core.test_context import get_test_context
from services.calendar_conflict_service import CalendarConflictService

router = APIRouter(prefix="/integrations/calendar", tags=["integrations"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CalendarConnectionStatus(BaseModel):
    """Response schema for calendar integration status (A35: extended with conflict count)."""

    model_config = ConfigDict(from_attributes=True)

    is_connected: bool
    provider_code: str | None = None
    sync_status: str | None = None
    # A35: connection_status maps from sync_status for mobile Owner tab
    connection_status: str | None = None  # connected | syncing | error | disconnected
    connected_at: datetime | None = None
    token_expires_at: datetime | None = None
    last_sync_at: datetime | None = None
    # A35: last successful sync from calendar_sync_log
    last_successful_sync_at: datetime | None = None
    # A35: pending conflict count for mobile Owner tab badge
    pending_conflicts_count: int = 0
    # A35: requires reconnect when sync_status = 'error' and token-related error
    requires_reconnect: bool = False


# ---------------------------------------------------------------------------
# State-token helpers  (CSRF protection — no Redis required)
# ---------------------------------------------------------------------------


def _encode_state(tenant_id: uuid.UUID, user_id: uuid.UUID) -> str:
    """Fernet-encrypt a JSON blob carrying tenant/user identity + expiry.

    Returns a URL-safe base64 string suitable as the OAuth ``state`` parameter.
    """
    if not settings.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY not configured")
    payload = json.dumps(
        {
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "exp": (
                datetime.now(UTC)
                + timedelta(seconds=settings.CALENDAR_OAUTH_STATE_TTL_SECONDS)
            ).isoformat(),
        }
    )
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(payload.encode()).decode()


def _decode_state(state: str) -> dict:
    """Decrypt and validate the OAuth state token.

    Returns the decoded dict on success.

    Raises:
        HTTPException 400 — if state is tampered, expired, or malformed.
    """
    if not settings.ENCRYPTION_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ENCRYPTION_KEY not configured",
        )
    try:
        f = Fernet(settings.ENCRYPTION_KEY.encode())
        payload = json.loads(f.decrypt(state.encode()).decode())
    except (InvalidToken, Exception):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or tampered OAuth state token",
        )

    exp = datetime.fromisoformat(payload["exp"])
    if datetime.now(UTC) > exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state token expired. Please initiate the connection again.",
        )
    return payload


# ---------------------------------------------------------------------------
# Token exchange helper
# ---------------------------------------------------------------------------


async def _exchange_code_for_tokens(code: str) -> dict:
    """Exchange Google authorization code for access + refresh tokens.

    Returns raw dict from Google's token endpoint.

    Raises:
        httpx.HTTPStatusError — on non-2xx response from Google.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.GOOGLE_CALENDAR_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
                "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Shared business logic
# ---------------------------------------------------------------------------


def _initiate_calendar_oauth_impl(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> RedirectResponse:
    """Build the Google OAuth consent URL and redirect."""
    state = _encode_state(tenant_id, user_id)
    scopes = (
        "https://www.googleapis.com/auth/calendar "
        "https://www.googleapis.com/auth/calendar.events"
    )
    auth_url = (
        f"{settings.GOOGLE_CALENDAR_AUTH_URL}"
        f"?client_id={settings.GOOGLE_CALENDAR_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_CALENDAR_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scopes}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={state}"
    )
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


async def _handle_calendar_callback_impl(
    code: str,
    state: str,
    db: Session,
) -> HTMLResponse | RedirectResponse:
    """Validate state, exchange code, encrypt tokens, upsert TenantCalendarIntegration."""
    # --- Decode & validate state token ---
    payload = _decode_state(state)
    tenant_id = uuid.UUID(payload["tenant_id"])
    user_id = uuid.UUID(payload["user_id"])

    # --- Exchange code for tokens ---
    try:
        token_data = await _exchange_code_for_tokens(code)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google token exchange failed: {exc.response.text}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google token exchange failed: {exc}",
        )

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google did not return an access token",
        )

    # --- Encrypt tokens (Fernet → str → bytes for LargeBinary column) ---
    access_encrypted: bytes = encrypt_token(access_token).encode()
    # Google only returns a refresh_token on first consent; store empty bytes if absent
    refresh_encrypted: bytes = (
        encrypt_token(refresh_token).encode() if refresh_token else b""
    )

    now = datetime.now(UTC)
    token_expires_at = now + timedelta(seconds=expires_in)

    # --- Upsert TenantCalendarIntegration (one row per tenant) ---
    set_audit_context_sync(db, user_id)
    existing = db.exec(
        select(TenantCalendarIntegration).where(
            TenantCalendarIntegration.tenant_id == tenant_id
        )
    ).first()

    if existing:
        existing.access_token_encrypted = access_encrypted
        if refresh_token:
            existing.refresh_token_encrypted = refresh_encrypted
        existing.token_expires_at = token_expires_at
        existing.sync_status = "active"
        existing.connected_by_user_id = user_id
        existing.connected_at = now
        existing.updated_by = user_id
        db.add(existing)
    else:
        integration = TenantCalendarIntegration(
            tenant_id=tenant_id,
            provider_code="google",
            # We use the token-endpoint "scope" as a stand-in; real calendar ID
            # is populated by the sync worker (Task 1-D-2) after first push.
            external_calendar_id="primary",
            access_token_encrypted=access_encrypted,
            refresh_token_encrypted=refresh_encrypted if refresh_token else b"",
            token_expires_at=token_expires_at,
            sync_status="active",
            connected_by_user_id=user_id,
            connected_at=now,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(integration)

    db.commit()

    # --- Return response ---
    if settings.ENVIRONMENT in ["dev", "qa"] or settings.TEST_ENDPOINT_ENABLED:
        html = f"""<!DOCTYPE html>
<html>
<head><title>Google Calendar Connected</title></head>
<body style="font-family:sans-serif;text-align:center;padding:2rem;">
  <h1>&#10003; Google Calendar Connected</h1>
  <p>Tenant <code>{tenant_id}</code> is now synced with Google Calendar.</p>
  <p>Token expires: <code>{token_expires_at.isoformat()}</code></p>
</body>
</html>"""
        return HTMLResponse(content=html, status_code=200)
    else:
        return RedirectResponse(
            url=f"{settings.API_BASE_URL.replace(':8000', ':3000')}/settings/integrations?calendar=connected",
            status_code=status.HTTP_302_FOUND,
        )


def _get_calendar_status_impl(
    tenant_id: uuid.UUID,
    db: Session,
) -> CalendarConnectionStatus:
    """Return current calendar integration status for a tenant (A35: extended)."""
    record = db.exec(
        select(TenantCalendarIntegration).where(
            TenantCalendarIntegration.tenant_id == tenant_id
        )
    ).first()

    if not record:
        return CalendarConnectionStatus(
            is_connected=False,
            connection_status="disconnected",
        )

    # A35: Map sync_status → connection_status for mobile Owner tab
    connection_status_map = {
        "active": "connected",
        "paused": "disconnected",
        "error": "error",
    }
    connection_status = connection_status_map.get(record.sync_status, "disconnected")

    # A35: Last successful sync from calendar_sync_log
    last_successful_sync = db.exec(
        select(CalendarSyncLog)
        .where(
            CalendarSyncLog.tenant_id == tenant_id,
            CalendarSyncLog.status == "success",
        )
        .order_by(sa_desc(CalendarSyncLog.created_at))
        .limit(1)
    ).first()
    last_successful_sync_at = (
        last_successful_sync.created_at if last_successful_sync else None
    )

    # A35: Pending conflicts count
    pending_conflicts_count = CalendarConflictService.get_pending_conflicts_count(
        db, tenant_id
    )

    # A35: requires_reconnect when error + token expired
    requires_reconnect = (
        record.sync_status == "error"
        and record.token_expires_at is not None
        and record.token_expires_at < datetime.now(UTC)
    )

    return CalendarConnectionStatus(
        is_connected=record.sync_status == "active",
        provider_code=record.provider_code,
        sync_status=record.sync_status,
        connection_status=connection_status,
        connected_at=record.connected_at,
        token_expires_at=record.token_expires_at,
        last_sync_at=record.last_sync_at,
        last_successful_sync_at=last_successful_sync_at,
        pending_conflicts_count=pending_conflicts_count,
        requires_reconnect=requires_reconnect,
    )


def _disconnect_calendar_impl(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
) -> dict:
    """Pause the calendar integration (soft disconnect — preserves token history)."""
    record = db.exec(
        select(TenantCalendarIntegration).where(
            TenantCalendarIntegration.tenant_id == tenant_id,
            TenantCalendarIntegration.sync_status == "active",
        )
    ).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Google Calendar integration found for this tenant",
        )

    set_audit_context_sync(db, user_id)
    record.sync_status = "paused"
    record.updated_by = user_id
    db.add(record)
    db.commit()

    return {
        "status": "disconnected",
        "message": "Google Calendar integration paused successfully",
    }


# ---------------------------------------------------------------------------
# Test endpoints  (register BEFORE authenticated endpoints — path priority)
# ---------------------------------------------------------------------------


@router.get("/auth/test", response_model=None)
async def initiate_calendar_oauth_test(
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    """TEST ENDPOINT: Initiate Google Calendar OAuth — no JWT required.

    Blocked in staging/production (TEST_ENDPOINT_ENABLED must be true).
    """
    test_context = get_test_context()
    return _initiate_calendar_oauth_impl(test_context.tenant_id, test_context.id)


@router.get("/status/test", response_model=CalendarConnectionStatus)
def get_calendar_status_test(
    db: Session = Depends(get_db),
) -> CalendarConnectionStatus:
    """TEST ENDPOINT: Return calendar integration status — no JWT required."""
    test_context = get_test_context()
    return _get_calendar_status_impl(test_context.tenant_id, db)


@router.delete("/disconnect/test")
def disconnect_calendar_test(
    db: Session = Depends(get_db),
) -> dict:
    """TEST ENDPOINT: Pause Google Calendar integration — no JWT required."""
    test_context = get_test_context()
    return _disconnect_calendar_impl(test_context.tenant_id, test_context.id, db)


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------


@router.get("/auth", response_model=None)
async def initiate_calendar_oauth(
    current_user: Annotated[
        AuthenticatedUser, Depends(require_permission("integrations.manage"))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    """Initiate Google Calendar OAuth 2.0 flow.

    Requires ``integrations.manage`` permission (owner only).

    Returns a 302 redirect to Google's OAuth consent screen.  A Fernet-signed
    state token (carrying tenant_id + user_id + expiry) is embedded in the URL
    for CSRF protection.
    """
    return _initiate_calendar_oauth_impl(current_user.tenant_id, current_user.user_id)


@router.get("/callback", response_model=None)
async def calendar_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(
        ..., description="Fernet-encrypted state token for CSRF validation"
    ),
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Handle Google Calendar OAuth callback.

    1. Decodes and validates the Fernet-encrypted state token (CSRF guard).
    2. Exchanges the authorization ``code`` for access + refresh tokens.
    3. Fernet-encrypts both tokens before storage.
    4. Upserts a ``tenant_calendar_integration`` row.

    Returns an HTML success page in dev/qa, or a 302 redirect to the frontend
    in production.
    """
    return await _handle_calendar_callback_impl(code, state, db)


@router.get("/status", response_model=CalendarConnectionStatus)
def get_calendar_status(
    current_user: Annotated[
        AuthenticatedUser, Depends(require_permission("integrations.view"))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> CalendarConnectionStatus:
    """Return current Google Calendar integration status for the caller's tenant.

    Requires ``integrations.view`` permission.
    """
    return _get_calendar_status_impl(current_user.tenant_id, db)


@router.delete("/disconnect")
def disconnect_calendar(
    current_user: Annotated[
        AuthenticatedUser, Depends(require_permission("integrations.manage"))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Pause the Google Calendar integration for the caller's tenant.

    Requires ``integrations.manage`` permission (owner only).

    The integration row is preserved; only ``sync_status`` is changed to
    ``'paused'``.  Tokens are NOT deleted, enabling re-activation without a
    full re-auth if the refresh token is still valid.
    """
    return _disconnect_calendar_impl(current_user.tenant_id, current_user.user_id, db)
