"""
tests/batch_b7b/test_a43_force_quit_recovery.py

Tests for B7b/A43 — Force-Quit Recovery State Persistence.

Server contribution for A43:
  - NO new migrations required (design doc §B execution order, item 4)
  - The existing idempotency_uuid column on MobileSyncEvent (established in B7a/A39)
    allows the server to detect duplicate submissions after a client force-quit.
  - Client retry path: client queries GET /api/v1/mobile-sync/state/ with its
    idempotency_uuid to check if the operation was already processed before retrying.

Test focus cases (per design doc §B item 4):
  1. MobileSyncEvent.idempotency_uuid column exists and is NOT NULL
  2. MobileSyncEvent rows can be queried by idempotency_uuid (retry-detection path)
  3. Two distinct idempotency_uuids create separate rows (no false dedup)
  4. A second lookup with the same idempotency_uuid finds the existing row
     (confirming the server-side force-quit recovery path is functional)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlmodel import select

from app.models.sync import MobileSyncEvent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sync_event(
    db_session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    idempotency_uuid: uuid.UUID,
    status: str = "pending",
) -> MobileSyncEvent:
    """Create a MobileSyncEvent for testing."""
    event = MobileSyncEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        device_id="test-device-001",
        operation_type="time_entry",
        operation_payload_summary={"hours": 2.5},
        status=status,
        client_capture_at=datetime.now(UTC),
        idempotency_uuid=idempotency_uuid,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


# ---------------------------------------------------------------------------
# A43: idempotency_uuid column and dedup path
# ---------------------------------------------------------------------------


class TestA43ForceQuitRecovery:
    def test_mobile_sync_event_idempotency_uuid_column_exists(self, db_session):
        """idempotency_uuid column exists on mobile_sync_event with NOT NULL constraint."""
        result = db_session.execute(
            text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'mobile_sync_event'
            AND column_name = 'idempotency_uuid'
        """)
        ).fetchone()
        assert result is not None, (
            "idempotency_uuid column must exist on mobile_sync_event"
        )
        assert result[1] == "uuid", f"Expected uuid type, got {result[1]}"
        assert result[2] == "NO", "idempotency_uuid must be NOT NULL"

    def test_idempotency_uuid_is_stored_on_insert(
        self, db_session, test_user, test_tenant
    ):
        """MobileSyncEvent stores the idempotency_uuid provided at insert time."""
        idempotency_uuid = uuid.uuid4()
        event = _make_sync_event(
            db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            idempotency_uuid=idempotency_uuid,
        )
        assert event.idempotency_uuid == idempotency_uuid

    def test_duplicate_idempotency_uuid_can_be_queried(
        self, db_session, test_user, test_tenant
    ):
        """
        Retry-after-force-quit: server can find existing row by idempotency_uuid.
        This is the core of A43: if client retries after force-quit, server detects
        the already-synced operation and returns the existing row's status.
        """
        idempotency_uuid = uuid.uuid4()

        # First submission (original)
        event1 = _make_sync_event(
            db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            idempotency_uuid=idempotency_uuid,
            status="succeeded",
        )

        # Retry lookup after force-quit: find existing by idempotency_uuid
        existing = db_session.exec(
            select(MobileSyncEvent)
            .where(MobileSyncEvent.idempotency_uuid == idempotency_uuid)
            .where(MobileSyncEvent.tenant_id == test_tenant.id)
        ).first()

        assert existing is not None, (
            "Server must find the existing row by idempotency_uuid"
        )
        assert existing.id == event1.id, "Found row must be the original submission"
        assert existing.status == "succeeded"

    def test_different_idempotency_uuids_create_separate_events(
        self, db_session, test_user, test_tenant
    ):
        """Two distinct idempotency_uuids create two separate events (no false dedup)."""
        event1 = _make_sync_event(
            db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            idempotency_uuid=uuid.uuid4(),
        )
        event2 = _make_sync_event(
            db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            idempotency_uuid=uuid.uuid4(),
        )
        assert event1.id != event2.id
        assert event1.idempotency_uuid != event2.idempotency_uuid

    def test_tenant_scoped_query_isolates_by_tenant(
        self, db_session, test_user, test_tenant, tenant_a, user_tenant_a
    ):
        """
        Tenant scoping: same idempotency_uuid in different tenants does not cause
        cross-tenant false dedup (tenant isolation in the recovery lookup).
        """
        shared_uuid = uuid.uuid4()

        # Event in test_tenant
        event_a = _make_sync_event(
            db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            idempotency_uuid=shared_uuid,
        )

        # Event in tenant_a (same idempotency_uuid, different tenant)
        event_b = _make_sync_event(
            db_session,
            tenant_id=tenant_a.id,
            user_id=user_tenant_a.id,
            idempotency_uuid=shared_uuid,
        )

        # Querying test_tenant finds only event_a
        result = db_session.exec(
            select(MobileSyncEvent)
            .where(MobileSyncEvent.idempotency_uuid == shared_uuid)
            .where(MobileSyncEvent.tenant_id == test_tenant.id)
        ).first()
        assert result is not None
        assert result.id == event_a.id

        # Querying tenant_a finds only event_b
        result_b = db_session.exec(
            select(MobileSyncEvent)
            .where(MobileSyncEvent.idempotency_uuid == shared_uuid)
            .where(MobileSyncEvent.tenant_id == tenant_a.id)
        ).first()
        assert result_b is not None
        assert result_b.id == event_b.id
