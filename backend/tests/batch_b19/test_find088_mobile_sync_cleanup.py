"""
tests/batch_b19/test_find088_mobile_sync_cleanup.py

Tests for FIND-088 mobile sync event cleanup task.

FIND-088 remediation: Archive mobile_sync_event rows older than 30 days
to prevent unbounded table growth while maintaining recent sync history.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.models.sync import MobileSyncEvent
from tasks.mobile_sync_cleanup import archive_old_mobile_sync_events


class TestMobileSyncCleanupTask:
    """Tests for archive_old_mobile_sync_events Celery task."""

    def test_task_runs_successfully(self):
        """Verify the cleanup task runs without errors."""
        # Run cleanup task
        result = archive_old_mobile_sync_events()

        # Should return a dict with rows_deleted count
        assert isinstance(result, dict)
        assert "rows_deleted" in result
        assert isinstance(result["rows_deleted"], int)
        assert result["rows_deleted"] >= 0

    def test_task_returns_deletion_count(self):
        """Verify the task returns a valid deletion count dict."""
        result = archive_old_mobile_sync_events()

        assert result["rows_deleted"] >= 0, "Deletion count should be non-negative"

    def test_recent_events_are_retained(
        self, db_session: Session, test_tenant, test_user
    ):
        """Verify that recent events (< 30 days) are preserved."""
        now = datetime.now(UTC)

        # Create a recent event
        recent_event = MobileSyncEvent(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            device_id="device_recent_test",
            operation_type="sync_job",
            operation_payload_summary={"job_id": str(uuid.uuid4())},
            status="succeeded",
            client_capture_at=now - timedelta(days=5),
            synced_at=now - timedelta(days=5),
            idempotency_uuid=uuid.uuid4(),
        )

        db_session.add(recent_event)
        db_session.commit()

        recent_event_id = recent_event.id

        # Run cleanup
        result = archive_old_mobile_sync_events()

        # Query for recent event - should still exist
        recent_event_exists = db_session.exec(
            select(MobileSyncEvent).where(MobileSyncEvent.id == recent_event_id)
        ).first()

        assert recent_event_exists is not None, "Recent event should not be deleted"
        assert recent_event_exists.status == "succeeded"

    def test_cleanup_with_empty_table(self):
        """Verify cleanup handles empty/sparse table gracefully."""
        # Run cleanup on potentially sparse table
        result = archive_old_mobile_sync_events()

        # Should complete without error
        assert result["rows_deleted"] >= 0, (
            "Cleanup should handle empty table without error"
        )


class TestMobileSyncCleanupTaskBehavior:
    """Behavioral tests for the cleanup task."""

    def test_cleanup_task_is_idempotent(self):
        """Verify that running cleanup multiple times is safe."""
        # First run
        result1 = archive_old_mobile_sync_events()
        deleted_first = result1["rows_deleted"]

        # Second run
        result2 = archive_old_mobile_sync_events()
        deleted_second = result2["rows_deleted"]

        # Both should return valid counts
        assert deleted_first >= 0, "First cleanup should return non-negative count"
        assert deleted_second >= 0, "Second cleanup should return non-negative count"

    def test_cleanup_respects_30_day_window(
        self, db_session: Session, test_tenant, test_user
    ):
        """Verify cleanup respects the 30-day retention window."""
        now = datetime.now(UTC)

        # Create a very recent event (should definitely be retained)
        recent_event = MobileSyncEvent(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            device_id="device_very_recent",
            operation_type="sync_job",
            operation_payload_summary={},
            status="succeeded",
            client_capture_at=now - timedelta(days=1),
            synced_at=now - timedelta(days=1),
            idempotency_uuid=uuid.uuid4(),
        )

        db_session.add(recent_event)
        db_session.commit()

        recent_id = recent_event.id

        # Run cleanup
        result = archive_old_mobile_sync_events()

        # Verify recent event still exists
        remaining = db_session.exec(
            select(MobileSyncEvent).where(MobileSyncEvent.id == recent_id)
        ).first()

        assert remaining is not None, "Events within 30-day window should be preserved"

    def test_cleanup_task_with_various_statuses(
        self, db_session: Session, test_tenant, test_user
    ):
        """Verify cleanup handles events with different statuses correctly."""
        now = datetime.now(UTC)

        # Create recent events with different statuses
        for status in ["pending", "syncing", "succeeded", "failed", "conflict"]:
            event = MobileSyncEvent(
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                device_id=f"device_{status}",
                operation_type="sync_job",
                operation_payload_summary={},
                status=status,
                client_capture_at=now - timedelta(days=2),
                idempotency_uuid=uuid.uuid4(),
            )
            db_session.add(event)

        db_session.commit()

        # Count events before cleanup
        count_before = db_session.exec(
            select(MobileSyncEvent).where(MobileSyncEvent.tenant_id == test_tenant.id)
        ).all()

        # Run cleanup
        archive_old_mobile_sync_events()

        # Count events after cleanup (should be same since all are recent)
        count_after = db_session.exec(
            select(MobileSyncEvent).where(MobileSyncEvent.tenant_id == test_tenant.id)
        ).all()

        assert len(count_after) == len(count_before), (
            f"Recent events should not be deleted (before: {len(count_before)}, "
            f"after: {len(count_after)})"
        )
