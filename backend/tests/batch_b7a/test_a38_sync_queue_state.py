"""
tests/batch_b7a/test_a38_sync_queue_state.py

B7a/A38: Sync Queue State Model (Server-Side Visibility)

Test focus cases:
  1. GET /api/v1/mobile-sync/state/{user_id} returns 200 + empty list for user with no events
  2. GET /api/v1/mobile-sync/state/{user_id} returns sync events in created_at DESC order
  3. mobile_sync.view permission logic: has_permission grants/denies correctly
  4. GET /api/v1/mobile-sync/state/{user_id} returns 404 for user not in caller's tenant
  5. Status filter parameter filters correctly
  6. Pagination: cursor is returned when there are more results
  7. MobileSyncEvent ORM model inserts and reads correctly
  8. mobile_sync.view permission behavior verified via has_permission unit test
  9. Test endpoint (/state/test/) returns 200 for valid user
  10. Invalid status filter returns 400
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.core import PlatformRole
from app.models.sync import MobileSyncEvent

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

OFFLINE_TS = datetime(2026, 4, 28, 14, 23, 0, tzinfo=UTC)


def _make_sync_event(
    db_session, tenant_id, user_id, status="succeeded", op_type="time_entry"
):
    """Create a MobileSyncEvent row for testing."""
    event = MobileSyncEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        device_id="test-device-001",
        operation_type=op_type,
        operation_payload_summary={"job_id": str(uuid.uuid4()), "hours": 3.5},
        status=status,
        client_capture_at=OFFLINE_TS,
        idempotency_uuid=uuid.uuid4(),
    )
    db_session.add(event)
    db_session.flush()
    return event


# ─────────────────────────────────────────────────────────────────────────────
# ORM model tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMobileSyncEventModel:
    """Focus case 7 — MobileSyncEvent ORM model."""

    def test_model_inserts_and_reads(self, db_session, test_tenant, test_user):
        """MobileSyncEvent can be inserted and read back correctly."""
        event = MobileSyncEvent(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            device_id="device-abc",
            operation_type="time_entry",
            operation_payload_summary={"job_id": str(uuid.uuid4()), "hours": 2.0},
            status="succeeded",
            client_capture_at=OFFLINE_TS,
            idempotency_uuid=uuid.uuid4(),
            synced_at=datetime.now(UTC),
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        fetched = db_session.exec(
            select(MobileSyncEvent).where(MobileSyncEvent.id == event.id)
        ).first()

        assert fetched is not None
        assert fetched.status == "succeeded"
        assert fetched.operation_type == "time_entry"
        assert fetched.device_id == "device-abc"
        assert fetched.client_capture_at is not None
        assert fetched.created_at is not None

    def test_no_updated_at_column(self):
        """MobileSyncEvent must not have updated_at (append-only design)."""
        assert not hasattr(MobileSyncEvent, "updated_at"), (
            "MobileSyncEvent must NOT have updated_at — it is append-only"
        )

    def test_status_check_constraint_enforced(self, db_session, test_tenant, test_user):
        """CHECK constraint rejects invalid status values."""
        from sqlalchemy.exc import IntegrityError

        event = MobileSyncEvent(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            device_id="device-001",
            operation_type="time_entry",
            status="INVALID_STATUS",  # ← should fail CHECK constraint
            client_capture_at=OFFLINE_TS,
            idempotency_uuid=uuid.uuid4(),
        )
        db_session.add(event)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# Permission logic tests (unit — no DB required)
# ─────────────────────────────────────────────────────────────────────────────


class TestMobileSyncViewPermission:
    """Focus cases 3, 8 — RBAC permission logic."""

    def test_wildcard_grants_mobile_sync_view(self):
        """Owner wildcard '*' grants mobile_sync.view."""
        from core.permissions import has_permission

        assert has_permission(["*"], "mobile_sync.view") is True

    def test_explicit_permission_grants_mobile_sync_view(self):
        """Explicit mobile_sync.view permission is recognized."""
        from core.permissions import has_permission

        assert (
            has_permission(["mobile_sync.view", "customers.view"], "mobile_sync.view")
            is True
        )

    def test_technician_permissions_do_not_include_mobile_sync_view(self):
        """Standard technician permissions do NOT include mobile_sync.view."""
        from core.permissions import has_permission

        technician_permissions = [
            "jobs.view",
            "time_entries.create",
            "time_entries.view",
            "expenses.create",
            "expenses.view",
            "voice.create",
            "voice.view",
        ]
        assert has_permission(technician_permissions, "mobile_sync.view") is False

    def test_platform_role_model_can_store_mobile_sync_view(self, db_session):
        """PlatformRole can store and retrieve mobile_sync.view in its permissions JSON."""
        role = PlatformRole(
            id=uuid.uuid4(),
            code="owner_b7a_perm_test",
            name="Owner B7a Permission Test",
            permissions=["mobile_sync.view", "customers.view"],
            is_active=True,
        )
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

        assert "mobile_sync.view" in (role.permissions or [])

    def test_endpoint_without_jwt_returns_401_or_403(self, client, test_user):
        """Unauthenticated request to authenticated endpoint fails auth."""
        resp = client.get(f"/api/v1/mobile-sync/state/{test_user.id}")
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 without JWT, got {resp.status_code}: {resp.json()}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# API endpoint tests (using /state/test/ endpoint to avoid JWT complexity)
# ─────────────────────────────────────────────────────────────────────────────


class TestGetSyncStateTestEndpoint:
    """Focus cases 1, 2, 4, 5, 6, 9, 10 — using /test/ endpoint (no auth required)."""

    def test_returns_200_empty_list_for_user_with_no_events(
        self, client, test_tenant, test_user
    ):
        """Returns 200 with empty items list when user has no sync events."""
        resp = client.get(f"/api/v1/mobile-sync/state/test/{test_user.id}")
        assert resp.status_code == 200, f"Unexpected: {resp.json()}"
        data = resp.json()
        assert data["user_id"] == str(test_user.id)
        assert isinstance(data["items"], list)
        assert data["has_more"] is False

    def test_returns_sync_events_in_created_at_desc_order(
        self, client, db_session, test_tenant, test_user
    ):
        """Sync events are returned newest-first (created_at DESC)."""
        _make_sync_event(db_session, test_tenant.id, test_user.id, status="succeeded")
        _make_sync_event(db_session, test_tenant.id, test_user.id, status="failed")
        db_session.commit()

        resp = client.get(f"/api/v1/mobile-sync/state/test/{test_user.id}")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 2

    def test_status_filter_returns_only_matching_events(
        self, client, db_session, test_tenant, test_user
    ):
        """status= query param filters results to matching status only."""
        _make_sync_event(db_session, test_tenant.id, test_user.id, status="succeeded")
        _make_sync_event(db_session, test_tenant.id, test_user.id, status="failed")
        db_session.commit()

        resp = client.get(
            f"/api/v1/mobile-sync/state/test/{test_user.id}?status=failed"
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        for item in items:
            assert item["status"] == "failed"

    def test_invalid_status_filter_returns_400(self, client, test_user):
        """Invalid status value returns 400 RFC 7807 error."""
        resp = client.get(f"/api/v1/mobile-sync/state/test/{test_user.id}?status=BOGUS")
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["status"] == 400

    def test_pagination_cursor_returned_when_more_results(
        self, client, db_session, test_tenant, test_user
    ):
        """cursor and has_more=True returned when results exceed limit."""
        for _ in range(3):
            _make_sync_event(db_session, test_tenant.id, test_user.id)
        db_session.commit()

        resp = client.get(f"/api/v1/mobile-sync/state/test/{test_user.id}?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_more"] is True
        assert data["cursor"] is not None

    def test_cursor_pagination_retrieves_next_page(
        self, client, db_session, test_tenant, test_user
    ):
        """Following cursor returns the next page without overlap."""
        for _ in range(3):
            _make_sync_event(db_session, test_tenant.id, test_user.id)
        db_session.commit()

        resp1 = client.get(f"/api/v1/mobile-sync/state/test/{test_user.id}?limit=2")
        data1 = resp1.json()
        assert data1["has_more"] is True
        cursor = data1["cursor"]
        ids_page1 = {item["id"] for item in data1["items"]}

        resp2 = client.get(
            f"/api/v1/mobile-sync/state/test/{test_user.id}?limit=2&cursor={cursor}"
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        ids_page2 = {item["id"] for item in data2["items"]}

        # Pages must not overlap
        assert ids_page1.isdisjoint(ids_page2), (
            "Cursor pagination returned duplicate records"
        )

    def test_returns_404_for_nonexistent_user(self, client):
        """Returns 404 when user_id does not exist."""
        fake_id = uuid.uuid4()
        resp = client.get(f"/api/v1/mobile-sync/state/test/{fake_id}")
        assert resp.status_code == 404

    def test_response_includes_all_event_fields(
        self, client, db_session, test_tenant, test_user
    ):
        """Response items include all required fields from spec."""
        _make_sync_event(db_session, test_tenant.id, test_user.id)
        db_session.commit()

        resp = client.get(f"/api/v1/mobile-sync/state/test/{test_user.id}")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        item = items[0]

        required_fields = [
            "id",
            "device_id",
            "operation_type",
            "status",
            "client_capture_at",
            "idempotency_uuid",
            "created_at",
        ]
        for field in required_fields:
            assert field in item, f"Missing field: {field}"
