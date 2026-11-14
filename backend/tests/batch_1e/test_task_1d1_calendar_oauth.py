"""
Task 1-D-1: Google Calendar OAuth Flow — unit tests.

Coverage:
  1. _encode_state / _decode_state round-trip
  2. _decode_state rejects expired tokens
  3. _decode_state rejects tampered ciphertext
  4. _get_calendar_status_impl returns is_connected=False when no record
  5. _disconnect_calendar_impl raises 404 when no active record
  6. Full upsert path via _handle_calendar_callback_impl (mocked token exchange)
     — new record is created with encrypted tokens
  7. Second callback call upserts rather than inserting a duplicate
  8. GET /api/v1/integrations/calendar/status/test — 200, is_connected=False (fresh tenant)
  9. DELETE /api/v1/integrations/calendar/disconnect/test — 404 when nothing to disconnect

All tests use the test_tenant / test_user fixtures from conftest (no hardcoded UUIDs).
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from sqlmodel import select

from api.routes.calendar_integration import (
    _decode_state,
    _disconnect_calendar_impl,
    _encode_state,
    _get_calendar_status_impl,
    _handle_calendar_callback_impl,
)
from app.models.scheduling import TenantCalendarIntegration
from core.config import settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    tenant_id: uuid.UUID, user_id: uuid.UUID, offset_seconds: int = 300
) -> str:
    """Build a Fernet-encrypted state token with a custom expiry offset."""
    payload = json.dumps(
        {
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "exp": (datetime.now(UTC) + timedelta(seconds=offset_seconds)).isoformat(),
        }
    )
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(payload.encode()).decode()


def _fake_token_response(
    access_token: str = "fake_access", refresh_token: str = "fake_refresh"
) -> dict:
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "https://www.googleapis.com/auth/calendar",
    }


# ---------------------------------------------------------------------------
# 1. State token round-trip
# ---------------------------------------------------------------------------


def test_encode_decode_state_round_trip(test_tenant, test_user):
    """_encode_state / _decode_state must round-trip cleanly."""
    state = _encode_state(test_tenant.id, test_user.id)
    payload = _decode_state(state)

    assert payload["tenant_id"] == str(test_tenant.id)
    assert payload["user_id"] == str(test_user.id)
    # exp must be in the future
    exp = datetime.fromisoformat(payload["exp"])
    assert exp > datetime.now(UTC)


# ---------------------------------------------------------------------------
# 2. Expired state token
# ---------------------------------------------------------------------------


def test_decode_state_rejects_expired_token(test_tenant, test_user):
    """_decode_state must raise HTTP 400 for a state token that is past its exp."""
    from fastapi import HTTPException

    expired_state = _make_state(test_tenant.id, test_user.id, offset_seconds=-1)
    with pytest.raises(HTTPException) as exc_info:
        _decode_state(expired_state)

    assert exc_info.value.status_code == 400
    assert "expired" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# 3. Tampered state token
# ---------------------------------------------------------------------------


def test_decode_state_rejects_tampered_token():
    """_decode_state must raise HTTP 400 for ciphertext that has been modified."""
    from fastapi import HTTPException

    tampered = "not-a-valid-fernet-token"
    with pytest.raises(HTTPException) as exc_info:
        _decode_state(tampered)

    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# 4. Status — no record → is_connected=False
# ---------------------------------------------------------------------------


def test_get_calendar_status_no_record(db_session, test_tenant):
    """Status must return is_connected=False when tenant has no calendar row."""
    result = _get_calendar_status_impl(test_tenant.id, db_session)

    assert result.is_connected is False
    assert result.provider_code is None


# ---------------------------------------------------------------------------
# 5. Disconnect — nothing active → 404
# ---------------------------------------------------------------------------


def test_disconnect_calendar_no_active_record(db_session, test_tenant, test_user):
    """_disconnect_calendar_impl must raise 404 when there is no active integration."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        _disconnect_calendar_impl(test_tenant.id, test_user.id, db_session)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# 6. Callback — new record created with encrypted tokens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_callback_creates_integration(db_session, test_tenant, test_user):
    """A valid callback must create a TenantCalendarIntegration row."""
    state = _encode_state(test_tenant.id, test_user.id)

    with patch(
        "api.routes.calendar_integration._exchange_code_for_tokens",
        new_callable=AsyncMock,
        return_value=_fake_token_response(),
    ):
        await _handle_calendar_callback_impl("auth_code_xyz", state, db_session)

    record = db_session.exec(
        select(TenantCalendarIntegration).where(
            TenantCalendarIntegration.tenant_id == test_tenant.id
        )
    ).first()

    assert record is not None
    assert record.sync_status == "active"
    assert record.provider_code == "google"
    # Tokens must be stored as bytes (encrypted)
    assert isinstance(record.access_token_encrypted, bytes)
    assert len(record.access_token_encrypted) > 0
    assert isinstance(record.refresh_token_encrypted, bytes)
    assert len(record.refresh_token_encrypted) > 0
    # Decrypted token must match what Google returned
    from core.encryption import decrypt_token

    decrypted_access = decrypt_token(record.access_token_encrypted.decode())
    assert decrypted_access == "fake_access"


# ---------------------------------------------------------------------------
# 7. Callback — upsert on second call (no duplicate row)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_callback_upserts_on_second_call(
    db_session, test_tenant, test_user
):
    """A second callback for the same tenant must update, not insert a second row."""
    state1 = _encode_state(test_tenant.id, test_user.id)
    state2 = _encode_state(test_tenant.id, test_user.id)

    with patch(
        "api.routes.calendar_integration._exchange_code_for_tokens",
        new_callable=AsyncMock,
        return_value=_fake_token_response("token_v1", "refresh_v1"),
    ):
        await _handle_calendar_callback_impl("code1", state1, db_session)

    with patch(
        "api.routes.calendar_integration._exchange_code_for_tokens",
        new_callable=AsyncMock,
        return_value=_fake_token_response("token_v2", "refresh_v2"),
    ):
        await _handle_calendar_callback_impl("code2", state2, db_session)

    records = db_session.exec(
        select(TenantCalendarIntegration).where(
            TenantCalendarIntegration.tenant_id == test_tenant.id
        )
    ).all()

    assert len(records) == 1, "Must not create duplicate rows for the same tenant"

    from core.encryption import decrypt_token

    decrypted = decrypt_token(records[0].access_token_encrypted.decode())
    assert decrypted == "token_v2", "Upsert must store the latest token"


# ---------------------------------------------------------------------------
# 8. HTTP test endpoint — GET /status/test → 200
# ---------------------------------------------------------------------------


def test_status_test_endpoint_returns_200(client, test_tenant):
    """GET /api/v1/integrations/calendar/status/test must return 200."""
    response = client.get("/api/v1/integrations/calendar/status/test")
    assert response.status_code == 200
    body = response.json()
    assert "is_connected" in body
    assert body["is_connected"] is False


# ---------------------------------------------------------------------------
# 9. HTTP test endpoint — DELETE /disconnect/test → 404 (nothing active)
# ---------------------------------------------------------------------------


def test_disconnect_test_endpoint_returns_404_when_no_integration(client):
    """DELETE /api/v1/integrations/calendar/disconnect/test must return 404."""
    response = client.delete("/api/v1/integrations/calendar/disconnect/test")
    assert response.status_code == 404
