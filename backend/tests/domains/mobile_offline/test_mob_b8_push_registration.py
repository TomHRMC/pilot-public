"""
Tests for: MOB-B8 Push Token Registration endpoint
Domain: mobile_offline (PRD §3.15)

Covers POST /api/v1/mobile/push-tokens/test (unauthenticated test endpoint)
which delegates to the same _register_push_token_impl() as the authenticated route.

Note: The push token endpoint lives in api/routes/mobile_push.py (exists pre-B8).
Task 1 was SKIPPED — endpoint already existed.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.sync import MobileDevicePushToken

pytestmark = [
    pytest.mark.domain_mobile_offline,
    pytest.mark.unit,
]


def _make_register_payload(
    device_id: uuid.UUID | None = None,
    platform: str = "ios",
    push_token: str | None = None,
    app_version: str | None = "1.0.0",
    os_version: str | None = "17.0",
) -> dict:
    """Build a valid push token registration payload."""
    return {
        "device_id": str(device_id or uuid.uuid4()),
        "platform": platform,
        "push_token": push_token or f"ExponentPushToken[{uuid.uuid4().hex[:16]}]",
        "app_version": app_version,
        "os_version": os_version,
    }


class TestPushTokenRegistration:
    """Tests for POST /api/v1/mobile/push-tokens/test — push token registration."""

    def test_register_new_push_token(self, client, test_user, db_session):
        """POST /register/test creates a new row with correct tenant/user/device."""
        device_id = uuid.uuid4()
        payload = _make_register_payload(device_id=device_id, platform="ios")

        resp = client.post("/api/v1/mobile/push-tokens/test", json=payload)
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["device_id"] == str(device_id)
        assert "registered_at" in data
        assert "last_seen_at" in data

        # Verify row exists in DB with correct values
        row = db_session.exec(
            select(MobileDevicePushToken).where(
                MobileDevicePushToken.device_id == device_id
            )
        ).first()
        assert row is not None
        assert row.push_token == payload["push_token"]
        assert row.platform == "ios"
        assert row.revoked_at is None
        assert row.notification_permission_granted is True

    def test_register_updates_existing_token(self, client, test_user, db_session):
        """Calling /register/test twice with same device_id updates push_token and last_seen_at."""
        device_id = uuid.uuid4()
        first_token = f"ExponentPushToken[first-{uuid.uuid4().hex[:8]}]"
        second_token = f"ExponentPushToken[second-{uuid.uuid4().hex[:8]}]"

        # First registration
        resp1 = client.post(
            "/api/v1/mobile/push-tokens/test",
            json=_make_register_payload(device_id=device_id, push_token=first_token),
        )
        assert resp1.status_code == 200

        # Second registration — same device, new token
        resp2 = client.post(
            "/api/v1/mobile/push-tokens/test",
            json=_make_register_payload(
                device_id=device_id,
                push_token=second_token,
                app_version="2.0.0",
            ),
        )
        assert resp2.status_code == 200

        # Only one row should exist for this device_id
        rows = db_session.exec(
            select(MobileDevicePushToken).where(
                MobileDevicePushToken.device_id == device_id
            )
        ).all()
        assert len(rows) == 1, "Expected upsert — only one row per device"
        assert rows[0].push_token == second_token
        assert rows[0].app_version == "2.0.0"

    def test_register_revived_revoked_token(self, client, test_user, db_session):
        """A device with revoked_at set gets re-activated (revoked_at = None) on re-register."""
        device_id = uuid.uuid4()

        # Initial registration
        resp = client.post(
            "/api/v1/mobile/push-tokens/test",
            json=_make_register_payload(device_id=device_id),
        )
        assert resp.status_code == 200

        # Manually revoke the token
        row = db_session.exec(
            select(MobileDevicePushToken).where(
                MobileDevicePushToken.device_id == device_id
            )
        ).first()
        assert row is not None
        row.revoked_at = datetime.now(UTC)
        db_session.add(row)
        db_session.commit()

        # Re-register same device — should clear revoked_at
        new_token = f"ExponentPushToken[revived-{uuid.uuid4().hex[:8]}]"
        resp2 = client.post(
            "/api/v1/mobile/push-tokens/test",
            json=_make_register_payload(device_id=device_id, push_token=new_token),
        )
        assert resp2.status_code == 200

        db_session.refresh(row)
        assert row.revoked_at is None, "Re-registration should clear revoked_at"
        assert row.push_token == new_token

    def test_register_invalid_platform(self, client, test_user):
        """platform='web' is not in ('ios', 'android') — endpoint returns 400."""
        payload = _make_register_payload(platform="web")
        resp = client.post("/api/v1/mobile/push-tokens/test", json=payload)
        # mobile_push.py validates platform and returns 400 for unsupported values
        assert resp.status_code == 400, resp.text

    def test_register_empty_push_token(self, client, test_user):
        """Empty push_token string should be rejected (422 from pydantic or route validation)."""
        payload = _make_register_payload()
        payload["push_token"] = ""

        resp = client.post("/api/v1/mobile/push-tokens/test", json=payload)
        # mobile_push.py validates empty push_token; FastAPI may return 400 or 422
        assert resp.status_code in (400, 422), (
            f"Expected 400 or 422 for empty push_token, got {resp.status_code}: {resp.text}"
        )
