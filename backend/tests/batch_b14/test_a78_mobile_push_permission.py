"""
B14/A78 — Mobile Push Permission State tests.

Test focus cases:
1. PUT /users/test/devices/{id}/push-permission creates record with state=granted
2. GET /users/test/devices/{id}/push-permission returns not_asked by default
3. Update to denied_by_user_choice → banner_should_appear=True
4. banner_should_appear=False when state=granted
5. banner_should_appear=False when state=not_asked
6. Invalid permission_state → 422
7. Upsert updates existing record (same device_id)
8. Banner reappears after 7 days
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.mobile_push_permission import MobilePushPermissionState

# ==================== FIXTURES ====================


@pytest.fixture
def push_device(db_session, test_tenant, test_user):
    """
    Create a mobile_device_push_token row so FK in mobile_push_permission_state is satisfied.
    Uses raw SQL + session_replication_role to bypass audit trigger (no 'id' col in fallback chain).
    """
    device_id = uuid.uuid4()
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")  # test_user.id

    db_session.execute(text("SET LOCAL session_replication_role = 'replica'"))
    db_session.execute(
        text("""
            INSERT INTO mobile_device_push_token
                (id, tenant_id, user_id, device_id, platform, push_token,
                 registered_at, last_seen_at, notification_permission_granted,
                 created_at, updated_at)
            VALUES
                (gen_random_uuid(), :tid, :uid, :did, 'ios', 'test-push-token',
                 now(), now(), false, now(), now())
            ON CONFLICT DO NOTHING
        """),
        {
            "tid": str(test_tenant.id),
            "uid": str(user_id),
            "did": str(device_id),
        },
    )
    db_session.execute(text("SET LOCAL session_replication_role = 'origin'"))
    db_session.commit()
    return device_id


# ==================== TEST CASES ====================


class TestPushPermissionCRUD:
    """Test cases 1-2, 6-7."""

    def test_put_creates_granted_record(self, client, test_tenant, push_device):
        """PUT with granted state creates record."""
        response = client.put(
            f"/api/v1/users/test/devices/{push_device}/push-permission",
            json={"permission_state": "granted"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == str(push_device)
        assert data["permission_state"] == "granted"
        assert data["banner_should_appear"] is False

    def test_get_returns_not_asked_by_default(self, client, test_tenant):
        """GET for unknown device returns not_asked default (no DB row)."""
        unknown_device = uuid.uuid4()
        response = client.get(
            f"/api/v1/users/test/devices/{unknown_device}/push-permission"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["permission_state"] == "not_asked"
        assert data["banner_should_appear"] is False

    def test_invalid_state_returns_422(self, client, test_tenant, push_device):
        """Invalid permission_state returns 422."""
        response = client.put(
            f"/api/v1/users/test/devices/{push_device}/push-permission",
            json={"permission_state": "invalid_state"},
        )
        assert response.status_code == 422

    def test_upsert_updates_existing_record(
        self, client, db_session, test_tenant, push_device
    ):
        """Second PUT with same device_id updates the existing row."""
        # First create
        client.put(
            f"/api/v1/users/test/devices/{push_device}/push-permission",
            json={"permission_state": "granted"},
        )

        # Update to denied
        response = client.put(
            f"/api/v1/users/test/devices/{push_device}/push-permission",
            json={"permission_state": "denied_by_user_choice"},
        )
        assert response.status_code == 200
        assert response.json()["permission_state"] == "denied_by_user_choice"

        # Only one row should exist per device
        rows = db_session.exec(
            select(MobilePushPermissionState)
            .where(MobilePushPermissionState.tenant_id == test_tenant.id)
            .where(MobilePushPermissionState.device_id == push_device)
        ).all()
        assert len(rows) == 1


class TestBannerLogic:
    """Test cases 3-5, 8: banner_should_appear computation."""

    def test_denied_by_user_banner_appears(self, client, test_tenant, push_device):
        """denied_by_user_choice with no dismissal → banner_should_appear=True."""
        response = client.put(
            f"/api/v1/users/test/devices/{push_device}/push-permission",
            json={"permission_state": "denied_by_user_choice"},
        )
        assert response.json()["banner_should_appear"] is True

    def test_granted_banner_does_not_appear(self, client, test_tenant, push_device):
        """granted → banner_should_appear=False."""
        response = client.put(
            f"/api/v1/users/test/devices/{push_device}/push-permission",
            json={"permission_state": "granted"},
        )
        assert response.json()["banner_should_appear"] is False

    def test_banner_logic_dismissed_within_7_days(self, db_session, test_tenant):
        """When dismissed less than 7 days ago, banner should NOT appear."""
        from api.routes.mobile_push_permission import _compute_banner_should_appear

        now = datetime.now(UTC)
        record = MobilePushPermissionState(
            tenant_id=test_tenant.id,
            user_id=uuid.uuid4(),
            device_id=uuid.uuid4(),
            permission_state="denied_by_user_choice",
            last_state_change_at=now,
            dismissable_banner_dismissed_at=now - timedelta(days=3),
        )
        assert _compute_banner_should_appear(record) is False

    def test_banner_logic_dismissed_more_than_7_days_ago(self, db_session, test_tenant):
        """When dismissed more than 7 days ago, banner SHOULD appear again."""
        from api.routes.mobile_push_permission import _compute_banner_should_appear

        now = datetime.now(UTC)
        record = MobilePushPermissionState(
            tenant_id=test_tenant.id,
            user_id=uuid.uuid4(),
            device_id=uuid.uuid4(),
            permission_state="denied_by_user_choice",
            last_state_change_at=now,
            dismissable_banner_dismissed_at=now - timedelta(days=8),
        )
        assert _compute_banner_should_appear(record) is True

    def test_not_asked_banner_does_not_appear(self, db_session, test_tenant):
        """not_asked state → banner_should_appear=False."""
        from api.routes.mobile_push_permission import _compute_banner_should_appear

        now = datetime.now(UTC)
        record = MobilePushPermissionState(
            tenant_id=test_tenant.id,
            user_id=uuid.uuid4(),
            device_id=uuid.uuid4(),
            permission_state="not_asked",
            last_state_change_at=now,
        )
        assert _compute_banner_should_appear(record) is False
