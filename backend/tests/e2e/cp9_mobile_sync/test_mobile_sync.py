"""
CP-9: Mobile Sync Lifecycle (SD-10 E2E Tier 1)

W-11: Mobile sync session creation, event insertion, and seed data verification.

Note: mobile_sync_event.device_id is TEXT (not UUID) per MCP schema verification.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

pytestmark = [pytest.mark.e2e]

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TECH_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

# Seed device UUID (stable — used by seed_scenario_mobile_sync.py)
SEED_DEVICE_ID = uuid.UUID("00000000-0000-0000-0001-000000000001")


class TestMobileSyncLifecycle:
    """W-11: Mobile sync session + event lifecycle."""

    def test_mobile_sync_session_can_be_created_and_completed(
        self, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Create a mobile_sync_session row, update it to completed, verify fields.
        """
        from sqlmodel import Session

        from app.models.sync import MobileSyncSession

        device_id = uuid.uuid4()
        started_at = datetime.now(UTC)

        with Session(e2e_engine) as db:
            # Create session row
            session_row = MobileSyncSession(
                tenant_id=TEST_TENANT_ID,
                user_id=TECH_USER_ID,
                device_id=device_id,
                triggered_by="manual",
                outcome=None,
                items_attempted=0,
                items_committed=0,
                items_deferred=0,
                items_failed=0,
                started_at=started_at,
            )
            db.add(session_row)
            db.commit()
            db.refresh(session_row)
            session_id = session_row.id

            # Update: mark completed
            session_row.outcome = "success"
            session_row.completed_at = datetime.now(UTC)
            session_row.items_attempted = 1
            session_row.items_committed = 1
            db.add(session_row)
            db.commit()
            db.refresh(session_row)

            # Verify
            assert session_row.completed_at is not None, (
                "completed_at must be set after completing the session"
            )
            assert session_row.outcome == "success"
            assert session_row.items_committed == 1

            # Store for next test
            TestMobileSyncLifecycle._session_device_id = device_id

    def test_mobile_sync_event_row_can_be_inserted(
        self, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Create a mobile_sync_event row, verify it can be fetched back.
        Note: device_id is TEXT type in mobile_sync_event.
        """
        from sqlmodel import Session, select

        from app.models.sync import MobileSyncEvent

        device_id = getattr(TestMobileSyncLifecycle, "_session_device_id", uuid.uuid4())
        idempotency_uuid = uuid.uuid4()

        with Session(e2e_engine) as db:
            event = MobileSyncEvent(
                tenant_id=TEST_TENANT_ID,
                user_id=TECH_USER_ID,
                device_id=str(device_id),  # TEXT column
                operation_type="create_time_entry",
                status="succeeded",
                idempotency_uuid=idempotency_uuid,
                client_capture_at=datetime.now(UTC),
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            event_id = event.id

            # Fetch back and assert
            fetched = db.exec(
                select(MobileSyncEvent).where(MobileSyncEvent.id == event_id)
            ).first()
            assert fetched is not None, f"MobileSyncEvent {event_id} must be fetchable"
            assert fetched.operation_type == "create_time_entry"
            assert fetched.status == "succeeded"
            assert fetched.idempotency_uuid == idempotency_uuid

    def test_seed_mobile_sync_scenario_data_present(
        self, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Cross-check: verify that seed_scenario_mobile_sync.py data is visible in E2E DB.
        At least 1 mobile_sync_session with triggered_by='background' must exist for test tenant.

        If this test fails, seed_e2e_db.py needs to be re-run against pilot_e2e_db.
        """
        from sqlmodel import Session, select

        from app.models.sync import MobileSyncSession

        with Session(e2e_engine) as db:
            sessions = db.exec(
                select(MobileSyncSession).where(
                    MobileSyncSession.tenant_id == TEST_TENANT_ID,
                    MobileSyncSession.triggered_by == "silent_push",
                )
            ).all()

            assert len(sessions) >= 1, (
                "At least 1 mobile_sync_session with triggered_by='silent_push' must exist "
                "for test tenant. This seed data is inserted by seed_scenario_mobile_sync.py. "
                "Run: DATABASE_URL=postgresql://pilot:pilot_e2e_password@localhost:5433/pilot_e2e_db "
                "python tests/e2e/seed_e2e_db.py"
            )

            # Verify the seed session has expected fields
            seed_session = sessions[0]
            assert seed_session.outcome == "success", (
                f"Seed session must have outcome='success', got: {seed_session.outcome}"
            )
            assert seed_session.items_committed == 3, (
                f"Seed session must have items_committed=3, got: {seed_session.items_committed}"
            )
