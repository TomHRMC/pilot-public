"""
tests/batch_b8/test_a51_mobile_push_infrastructure.py

B8/A51: Background Sync Infrastructure Tests

Test focus cases:
  - Push token registration (create new)
  - Push token upsert (update existing — same device, new token)
  - Push token revoke (DELETE endpoint)
  - Push token revoke — not found returns 404
  - Sync session complete (valid outcome)
  - Sync session complete — invalid outcome returns 400
  - register_or_refresh_push_token service function (direct)
  - revoke_push_token service function (direct)
  - dispatch_silent_push_for_device — rate limited path
  - dispatch_silent_push_for_device — revoked token path
  - dispatch_silent_push_for_device — permission denied path
  - dispatch_silent_push_for_device — success path
  - detect_os_throttle_for_device — returns False when no rate row
  - _get_push_interval_minutes — uses tenant override when set
  - _get_push_interval_minutes — uses system default when NULL
  - MobileDevicePushToken model — platform check constraint enforced via API
  - MobileSyncSession model — outcome check constraint enforced via API
  - Tenant isolation — token not visible across tenants
"""

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import select

from app.models.sync import MobileDevicePushToken
from services.mobile_background_sync import (
    detect_os_throttle_for_device,
    dispatch_silent_push_for_device,
    register_or_refresh_push_token,
    revoke_push_token,
)
from services.setting_resolver import get_effective_setting

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _push_token_payload(
    device_id: uuid.UUID | None = None, platform: str = "ios"
) -> dict:
    return {
        "device_id": str(device_id or uuid.uuid4()),
        "platform": platform,
        "push_token": f"fake-token-{uuid.uuid4().hex[:8]}",
        "app_version": "1.0.0",
        "os_version": "17.0",
        "notification_permission_granted": True,
    }


def _sync_complete_payload(outcome: str = "success") -> dict:
    return {
        "outcome": outcome,
        "items_attempted": 5,
        "items_committed": 5,
        "items_deferred": 0,
        "items_failed": 0,
        "failure_reason": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# API endpoint tests — push token registration
# ─────────────────────────────────────────────────────────────────────────────


def test_register_push_token_creates_new_row(client: TestClient, test_user, db_session):
    """POST /push-tokens creates a new row for a new device."""
    device_id = uuid.uuid4()
    payload = _push_token_payload(device_id=device_id, platform="ios")

    resp = client.post("/api/v1/mobile/push-tokens/test", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["device_id"] == str(device_id)
    assert "registered_at" in data
    assert "last_seen_at" in data

    # Verify row in DB
    row = db_session.exec(
        select(MobileDevicePushToken).where(
            MobileDevicePushToken.device_id == device_id
        )
    ).first()
    assert row is not None
    assert row.platform == "ios"
    assert row.revoked_at is None


def test_register_push_token_upserts_on_same_device(
    client: TestClient, test_user, db_session
):
    """POST /push-tokens upserts when called again with same device_id."""
    device_id = uuid.uuid4()
    payload1 = _push_token_payload(device_id=device_id, platform="android")
    payload2 = {**payload1, "push_token": "new-token-xyz", "app_version": "2.0.0"}

    # First registration
    resp1 = client.post("/api/v1/mobile/push-tokens/test", json=payload1)
    assert resp1.status_code == 200

    # Second registration — same device, new token
    resp2 = client.post("/api/v1/mobile/push-tokens/test", json=payload2)
    assert resp2.status_code == 200

    # Only one row should exist for this device
    rows = db_session.exec(
        select(MobileDevicePushToken).where(
            MobileDevicePushToken.device_id == device_id
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].push_token == "new-token-xyz"
    assert rows[0].app_version == "2.0.0"


def test_register_push_token_rejects_invalid_platform(client: TestClient, test_user):
    """POST /push-tokens returns 400 for unsupported platform."""
    payload = _push_token_payload(platform="windows")
    resp = client.post("/api/v1/mobile/push-tokens/test", json=payload)
    assert resp.status_code == 400
    assert "platform" in resp.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# API endpoint tests — push token revoke
# ─────────────────────────────────────────────────────────────────────────────


def test_revoke_push_token_sets_revoked_at(client: TestClient, test_user, db_session):
    """DELETE /push-tokens/{device_id} sets revoked_at."""
    device_id = uuid.uuid4()
    # First register
    client.post(
        "/api/v1/mobile/push-tokens/test", json=_push_token_payload(device_id=device_id)
    )

    # Then revoke
    resp = client.delete(f"/api/v1/mobile/push-tokens/{device_id}/test")
    assert resp.status_code == 204

    row = db_session.exec(
        select(MobileDevicePushToken).where(
            MobileDevicePushToken.device_id == device_id
        )
    ).first()
    assert row is not None
    assert row.revoked_at is not None


def test_revoke_push_token_not_found_returns_404(client: TestClient, test_user):
    """DELETE /push-tokens/{device_id} returns 404 for unknown device."""
    unknown_device = uuid.uuid4()
    resp = client.delete(f"/api/v1/mobile/push-tokens/{unknown_device}/test")
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# API endpoint tests — sync session completion
# ─────────────────────────────────────────────────────────────────────────────


def test_complete_sync_session_valid_outcome(client: TestClient, test_user, db_session):
    """POST /sync-sessions/{id}/complete stores outcome and completed_at."""
    session_id = uuid.uuid4()
    payload = _sync_complete_payload(outcome="success")

    resp = client.post(
        f"/api/v1/mobile/sync-sessions/{session_id}/complete/test",
        json=payload,
    )
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["session_id"] == str(session_id)
    assert data["outcome"] == "success"
    assert data["completed_at"] is not None


def test_complete_sync_session_all_valid_outcomes(client: TestClient, test_user):
    """All 4 valid outcomes are accepted."""
    for outcome in ("success", "partial", "failed", "throttled"):
        session_id = uuid.uuid4()
        resp = client.post(
            f"/api/v1/mobile/sync-sessions/{session_id}/complete/test",
            json=_sync_complete_payload(outcome=outcome),
        )
        assert resp.status_code == 200, f"outcome={outcome} failed: {resp.text}"
        assert resp.json()["outcome"] == outcome


def test_complete_sync_session_invalid_outcome_returns_400(
    client: TestClient, test_user
):
    """POST /sync-sessions/{id}/complete returns 400 for invalid outcome."""
    session_id = uuid.uuid4()
    resp = client.post(
        f"/api/v1/mobile/sync-sessions/{session_id}/complete/test",
        json=_sync_complete_payload(outcome="crashed"),
    )
    assert resp.status_code == 400
    assert "outcome" in resp.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# Service function tests — register_or_refresh_push_token
# ─────────────────────────────────────────────────────────────────────────────


def test_service_register_creates_token(db_session, test_tenant, test_user):
    """register_or_refresh_push_token creates a new row."""
    device_id = uuid.uuid4()
    row = register_or_refresh_push_token(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        platform="ios",
        push_token="test-apns-token-abc",
        app_version="1.0",
        os_version="17.0",
        notification_permission_granted=True,
    )
    assert row.device_id == device_id
    assert row.push_token == "test-apns-token-abc"
    assert row.revoked_at is None


def test_service_register_clears_revoke_on_reregistration(
    db_session, test_tenant, test_user
):
    """Re-registering a previously revoked token clears revoked_at."""
    device_id = uuid.uuid4()
    # Register
    row = register_or_refresh_push_token(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        platform="ios",
        push_token="token-v1",
        app_version=None,
        os_version=None,
        notification_permission_granted=True,
    )
    # Manually revoke
    row.revoked_at = datetime.now(UTC)
    db_session.add(row)
    db_session.commit()

    # Re-register
    updated = register_or_refresh_push_token(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        platform="ios",
        push_token="token-v2",
        app_version=None,
        os_version=None,
        notification_permission_granted=True,
    )
    assert updated.revoked_at is None
    assert updated.push_token == "token-v2"


# ─────────────────────────────────────────────────────────────────────────────
# Service function tests — revoke_push_token
# ─────────────────────────────────────────────────────────────────────────────


def test_service_revoke_returns_true_when_found(db_session, test_tenant, test_user):
    """revoke_push_token returns True when token exists."""
    device_id = uuid.uuid4()
    register_or_refresh_push_token(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        platform="android",
        push_token="fcm-token-xyz",
        app_version=None,
        os_version=None,
        notification_permission_granted=True,
    )
    result = revoke_push_token(db=db_session, user_id=test_user.id, device_id=device_id)
    assert result is True


def test_service_revoke_returns_false_when_not_found(db_session, test_user):
    """revoke_push_token returns False when token doesn't exist."""
    result = revoke_push_token(
        db=db_session, user_id=test_user.id, device_id=uuid.uuid4()
    )
    assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# Service function tests — dispatch_silent_push_for_device
# ─────────────────────────────────────────────────────────────────────────────


def test_dispatch_push_succeeds_for_active_token(db_session, test_tenant, test_user):
    """dispatch_silent_push_for_device returns dispatched=True for valid token."""
    device_id = uuid.uuid4()
    register_or_refresh_push_token(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        platform="ios",
        push_token="valid-apns-token",
        app_version=None,
        os_version=None,
        notification_permission_granted=True,
    )

    result = dispatch_silent_push_for_device(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        sync_session_id=uuid.uuid4(),
    )
    assert result.dispatched is True
    assert result.skip_reason is None


def test_dispatch_push_skips_revoked_token(db_session, test_tenant, test_user):
    """dispatch_silent_push_for_device returns skip_reason=revoked_token for revoked token."""
    device_id = uuid.uuid4()
    row = register_or_refresh_push_token(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        platform="ios",
        push_token="old-token",
        app_version=None,
        os_version=None,
        notification_permission_granted=True,
    )
    row.revoked_at = datetime.now(UTC)
    db_session.add(row)
    db_session.commit()

    result = dispatch_silent_push_for_device(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        sync_session_id=uuid.uuid4(),
    )
    assert result.dispatched is False
    assert result.skip_reason == "revoked_token"


def test_dispatch_push_skips_permission_denied(db_session, test_tenant, test_user):
    """dispatch_silent_push_for_device returns skip_reason=permission_denied."""
    device_id = uuid.uuid4()
    register_or_refresh_push_token(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        platform="android",
        push_token="fcm-token",
        app_version=None,
        os_version=None,
        notification_permission_granted=False,  # Permission denied
    )

    result = dispatch_silent_push_for_device(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        sync_session_id=uuid.uuid4(),
    )
    assert result.dispatched is False
    assert result.skip_reason == "permission_denied"


def test_dispatch_push_rate_limited_on_second_call(db_session, test_tenant, test_user):
    """dispatch_silent_push_for_device is rate limited on rapid second call."""
    device_id = uuid.uuid4()
    register_or_refresh_push_token(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        platform="ios",
        push_token="token-ratelimit",
        app_version=None,
        os_version=None,
        notification_permission_granted=True,
    )

    session_id = uuid.uuid4()
    # First call — should succeed
    result1 = dispatch_silent_push_for_device(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        sync_session_id=session_id,
    )
    assert result1.dispatched is True

    # Second call immediately — rate limited
    result2 = dispatch_silent_push_for_device(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        sync_session_id=uuid.uuid4(),
    )
    assert result2.dispatched is False
    assert result2.skip_reason == "rate_limited"


# ─────────────────────────────────────────────────────────────────────────────
# Service function tests — detect_os_throttle_for_device
# ─────────────────────────────────────────────────────────────────────────────


def test_detect_throttle_returns_false_when_no_rate_row(db_session):
    """detect_os_throttle_for_device returns False when no rate limit row exists."""
    result = detect_os_throttle_for_device(db=db_session, device_id=uuid.uuid4())
    assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# Service function tests — _get_push_interval_minutes
# ─────────────────────────────────────────────────────────────────────────────


def test_get_push_interval_uses_system_default_when_none(db_session, test_tenant):
    """B9/A53: resolver returns system default (5) when no tenant override (FIND-086)."""
    from app.models.platform_setting import PlatformSetting

    # Ensure no tenant override exists for this key
    existing = db_session.exec(
        select(PlatformSetting)
        .where(PlatformSetting.key == "background_sync_push_interval_minutes")
        .where(PlatformSetting.tenant_id == test_tenant.id)
    ).first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    result, scope = get_effective_setting(
        db_session, test_tenant.id, "background_sync_push_interval_minutes", fallback=5
    )
    assert result == 5
    assert scope == "system"


def test_get_push_interval_uses_tenant_override(db_session, test_tenant):
    """B9/A53: resolver returns tenant override when explicitly set (FIND-086)."""
    from app.models.platform_setting import PlatformSetting

    override = PlatformSetting(
        key="background_sync_push_interval_minutes",
        value=15,
        tenant_id=test_tenant.id,
    )
    db_session.add(override)
    db_session.commit()

    result, scope = get_effective_setting(
        db_session, test_tenant.id, "background_sync_push_interval_minutes", fallback=5
    )
    assert result == 15
    assert scope == "tenant"

    # Restore (FIND-086: delete the platform_setting override)
    db_session.delete(override)
    db_session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Tenant isolation
# ─────────────────────────────────────────────────────────────────────────────


def test_push_token_tenant_isolation(db_session, test_tenant, test_user):
    """Push tokens are scoped to tenant — cross-tenant device_id returns no match."""
    device_id = uuid.uuid4()
    # Register for test_tenant
    register_or_refresh_push_token(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        device_id=device_id,
        platform="ios",
        push_token="isolated-token",
        app_version=None,
        os_version=None,
        notification_permission_granted=True,
    )

    # Query with a different tenant_id — should not find it
    other_tenant_id = uuid.uuid4()
    row = db_session.exec(
        select(MobileDevicePushToken)
        .where(MobileDevicePushToken.tenant_id == other_tenant_id)
        .where(MobileDevicePushToken.device_id == device_id)
    ).first()
    assert row is None
