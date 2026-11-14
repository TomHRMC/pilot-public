"""
Tests for FIND-165: Audit log S3 archive with JSONL/gzip export before DB deletion.

Test Plan (from FIND-165):
1. Mock boto3.client('s3').put_object → task exports events to correct S3 key path before deleting
2. S3 upload failure → events NOT deleted from DB (safety gate); error logged
3. Events ≤90 days old → NOT exported or deleted (retention boundary respected)
4. Events >90 days old → exported + deleted from audit.event (both verified)
5. JSONL format: each line is valid JSON with all audit event fields present
"""

import gzip
import io
import json
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlmodel import delete, select

from app.models.system import AuditEvent
from tasks.archive_audit_logs import (
    BATCH_SIZE,
    _batch_export_to_s3,
    _serialize_audit_event_to_dict,
    archive_old_events,
    get_archive_statistics,
)


@pytest.fixture(autouse=True)
def cleanup_audit_table(db_session):
    """Clean up audit.event table before each test to ensure isolation."""
    # Delete all audit events before test using bulk delete for efficiency
    db_session.exec(delete(AuditEvent))
    db_session.commit()

    yield

    # Clean up after test using bulk delete
    db_session.exec(delete(AuditEvent))
    db_session.commit()


class TestAuditEventSerialization:
    """Test conversion of AuditEvent ORM to JSON-serializable dict."""

    def test_serialize_audit_event_to_dict_all_fields(self, db_session, test_tenant):
        """Test that all audit event fields serialize correctly to dict."""
        now = datetime.now(UTC)

        event = AuditEvent(
            occurred_at=now,
            tenant_id=test_tenant.id,
            user_id=uuid4(),
            actor_type="user",
            user_role="technician",
            ip="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id="req-12345",
            correlation_id="corr-67890",
            idempotency_key="idem-key-123",
            entity_name="job",
            entity_id="job-456",
            action="INSERT",
            old_values=None,
            new_values={"status": "scheduled"},
            reason="Job created via mobile app",
            contextdata={"source": "mobile"},
            prev_hash="hash-prev",
            self_hash="hash-self",
            hashed_at=now,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        result = _serialize_audit_event_to_dict(event)

        assert result["id"] == event.id
        assert result["occurred_at"] == now.isoformat()
        assert result["tenant_id"] == str(test_tenant.id)
        assert result["actor_type"] == "user"
        assert result["entity_name"] == "job"
        assert result["action"] == "INSERT"
        assert result["new_values"] == {"status": "scheduled"}
        assert result["reason"] == "Job created via mobile app"

    def test_serialize_audit_event_with_nulls(self, db_session, test_tenant):
        """Test serialization with optional/null fields."""
        now = datetime.now(UTC)

        event = AuditEvent(
            occurred_at=now,
            tenant_id=test_tenant.id,
            user_id=None,  # null
            actor_type="system",
            user_role=None,  # null
            ip=None,
            user_agent=None,
            request_id=None,
            correlation_id=None,
            idempotency_key=None,
            entity_name="tenant_setting",
            entity_id="setting-123",
            action="UPDATE",
            old_values=None,
            new_values=None,
            reason=None,
            contextdata=None,
            prev_hash=None,
            self_hash=None,
            hashed_at=None,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        result = _serialize_audit_event_to_dict(event)

        assert result["user_id"] is None
        assert result["user_role"] is None
        assert result["ip"] is None
        assert result["new_values"] is None
        assert result["hashed_at"] is None


class TestBatchExportToS3:
    """Test S3 export logic with batching and error handling."""

    @patch("tasks.archive_audit_logs.boto3.client")
    def test_batch_export_to_s3_success_single_tenant(
        self, mock_boto3_client, db_session, test_tenant
    ):
        """Test successful S3 export for events from single tenant."""
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        # Create 3 audit events
        now = datetime.now(UTC)
        timestamp = now.isoformat()
        events = []

        for i in range(3):
            event = AuditEvent(
                occurred_at=now - timedelta(days=91 + i),
                tenant_id=test_tenant.id,
                actor_type="user",
                entity_name=f"entity_{i}",
                entity_id=f"id_{i}",
                action="INSERT",
                new_values={"idx": i},
            )
            db_session.add(event)
            events.append(event)

        db_session.commit()
        for e in events:
            db_session.refresh(e)

        # Export batch
        result = _batch_export_to_s3(events, timestamp)

        assert result is True
        assert mock_s3_client.put_object.called

        # Verify S3 call
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]["Bucket"] == "pilot-audit-archive"
        s3_key = call_args[1]["Key"]

        # Verify S3 path: YYYY/MM/DD/{tenant_id}/audit-events-{timestamp}.jsonl.gz
        assert f"/{test_tenant.id}/audit-events-" in s3_key
        assert s3_key.endswith(".jsonl.gz")

        # Verify gzipped JSONL content
        gz_body = call_args[1]["Body"]
        with gzip.GzipFile(fileobj=io.BytesIO(gz_body), mode="rb") as gz_file:
            decompressed = gz_file.read().decode("utf-8")

        lines = decompressed.strip().split("\n")
        assert len(lines) == 3

        # Verify each line is valid JSON
        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed["entity_name"] == f"entity_{i}"
            assert parsed["new_values"]["idx"] == i

    @patch("tasks.archive_audit_logs.boto3.client")
    def test_batch_export_to_s3_multiple_tenants(
        self, mock_boto3_client, db_session, test_tenant
    ):
        """Test S3 export with events from multiple tenants (separate uploads)."""
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        now = datetime.now(UTC)
        timestamp = now.isoformat()
        tenant2 = uuid4()

        # Create events for two tenants
        events = []
        for tenant_id in [test_tenant.id, tenant2]:
            for i in range(2):
                event = AuditEvent(
                    occurred_at=now - timedelta(days=91),
                    tenant_id=tenant_id,
                    actor_type="user",
                    entity_name=f"entity_{i}",
                    entity_id=f"id_{i}",
                    action="INSERT",
                )
                db_session.add(event)
                events.append(event)

        db_session.commit()
        for e in events:
            db_session.refresh(e)

        # Export batch
        result = _batch_export_to_s3(events, timestamp)

        assert result is True
        assert mock_s3_client.put_object.call_count == 2  # One per tenant

        # Verify both tenants in S3 keys
        s3_keys = [call[1]["Key"] for call in mock_s3_client.put_object.call_args_list]
        assert any(str(test_tenant.id) in key for key in s3_keys)
        assert any(str(tenant2) in key for key in s3_keys)

    @patch("tasks.archive_audit_logs.boto3.client")
    def test_batch_export_to_s3_failure_returns_false(
        self, mock_boto3_client, db_session, test_tenant, caplog
    ):
        """Test S3 upload failure returns False (safety gate for DB deletion)."""
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        mock_s3_client.put_object.side_effect = Exception("S3 connection timeout")

        now = datetime.now(UTC)
        timestamp = now.isoformat()

        event = AuditEvent(
            occurred_at=now - timedelta(days=91),
            tenant_id=test_tenant.id,
            actor_type="user",
            entity_name="job",
            entity_id="job-1",
            action="INSERT",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        with caplog.at_level(logging.ERROR):
            result = _batch_export_to_s3([event], timestamp)

        assert result is False
        assert "Error exporting batch to S3" in caplog.text

    def test_batch_export_to_s3_empty_events_returns_true(self):
        """Test empty event list returns True (no-op)."""
        result = _batch_export_to_s3([], "2026-05-13T00:00:00+00:00")
        assert result is True


class TestArchiveOldEvents:
    """Integration tests for full archive_old_events flow."""

    @patch("tasks.archive_audit_logs.boto3.client")
    def test_archive_old_events_exports_and_deletes_old_events(
        self, mock_boto3_client, db_session, test_tenant
    ):
        """Test events >90 days old are exported to S3 and deleted from DB."""
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        now = datetime.now(UTC)
        old_date = now - timedelta(days=91)
        recent_date = now - timedelta(days=30)

        # Create old event (should be archived)
        old_event = AuditEvent(
            occurred_at=old_date,
            tenant_id=test_tenant.id,
            actor_type="user",
            entity_name="job",
            entity_id="old-job-1",
            action="INSERT",
        )
        db_session.add(old_event)

        # Create recent event (should NOT be archived)
        recent_event = AuditEvent(
            occurred_at=recent_date,
            tenant_id=test_tenant.id,
            actor_type="user",
            entity_name="job",
            entity_id="recent-job-1",
            action="INSERT",
        )
        db_session.add(recent_event)

        db_session.commit()
        db_session.refresh(old_event)
        db_session.refresh(recent_event)

        old_event_id = old_event.id
        recent_event_id = recent_event.id

        # Run archive
        result = archive_old_events(db_session)

        # Verify old event deleted
        assert result["exported_count"] == 1
        assert result["deleted_count"] == 1

        deleted = db_session.exec(
            select(AuditEvent).where(AuditEvent.id == old_event_id)
        ).first()
        assert deleted is None

        # Verify recent event still exists
        still_exists = db_session.exec(
            select(AuditEvent).where(AuditEvent.id == recent_event_id)
        ).first()
        assert still_exists is not None

        # Verify S3 call
        assert mock_s3_client.put_object.called

    @patch("tasks.archive_audit_logs.boto3.client")
    def test_archive_old_events_s3_failure_prevents_deletion(
        self, mock_boto3_client, db_session, test_tenant, caplog
    ):
        """Test S3 upload failure prevents DB deletion (safety gate)."""
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        mock_s3_client.put_object.side_effect = Exception("S3 network error")

        now = datetime.now(UTC)
        old_date = now - timedelta(days=91)

        event = AuditEvent(
            occurred_at=old_date,
            tenant_id=test_tenant.id,
            actor_type="user",
            entity_name="job",
            entity_id="job-1",
            action="INSERT",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        event_id = event.id

        # Run archive (S3 will fail)
        with caplog.at_level(logging.ERROR):
            result = archive_old_events(db_session)

        # Verify event NOT deleted (safety gate)
        assert result["deleted_count"] == 0

        still_exists = db_session.exec(
            select(AuditEvent).where(AuditEvent.id == event_id)
        ).first()
        assert still_exists is not None
        assert "S3 upload failed" in caplog.text or "Error" in caplog.text

    @patch("tasks.archive_audit_logs.boto3.client")
    def test_archive_old_events_respects_retention_boundary(
        self, mock_boto3_client, db_session, test_tenant
    ):
        """Test >90-day old events are archived while recent events are not."""
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        now = datetime.now(UTC)

        # Recent event (30 days old) - should NOT be archived
        recent_event = AuditEvent(
            occurred_at=now - timedelta(days=30),
            tenant_id=test_tenant.id,
            actor_type="user",
            entity_name="job",
            entity_id="job-recent",
            action="INSERT",
        )
        db_session.add(recent_event)

        # Very old event (120 days old) - SHOULD be archived
        old_event = AuditEvent(
            occurred_at=now - timedelta(days=120),
            tenant_id=test_tenant.id,
            actor_type="user",
            entity_name="job",
            entity_id="job-old",
            action="INSERT",
        )
        db_session.add(old_event)

        db_session.commit()
        db_session.refresh(recent_event)
        db_session.refresh(old_event)

        recent_id = recent_event.id
        old_id = old_event.id

        # Run archive
        result = archive_old_events(db_session)

        # At least the old event should be archived
        assert result["deleted_count"] >= 1

        # Verify recent event still exists
        assert (
            db_session.exec(
                select(AuditEvent).where(AuditEvent.id == recent_id)
            ).first()
            is not None
        )

        # Verify old event was deleted
        assert (
            db_session.exec(select(AuditEvent).where(AuditEvent.id == old_id)).first()
            is None
        )

    @patch("tasks.archive_audit_logs.boto3.client")
    def test_archive_old_events_no_events_to_archive(
        self, mock_boto3_client, db_session, test_tenant, caplog
    ):
        """Test handling when no events are older than 90 days."""
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        now = datetime.now(UTC)

        # Only recent events
        event = AuditEvent(
            occurred_at=now - timedelta(days=30),
            tenant_id=test_tenant.id,
            actor_type="user",
            entity_name="job",
            entity_id="job-1",
            action="INSERT",
        )
        db_session.add(event)
        db_session.commit()

        with caplog.at_level(logging.INFO):
            result = archive_old_events(db_session)

        assert result["exported_count"] == 0
        assert result["deleted_count"] == 0
        assert "No audit events to archive" in caplog.text
        assert not mock_s3_client.put_object.called

    @patch("tasks.archive_audit_logs.boto3.client")
    def test_archive_old_events_batching_large_dataset(
        self, mock_boto3_client, db_session, test_tenant
    ):
        """Test batching logic with dataset larger than BATCH_SIZE."""
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        now = datetime.now(UTC)
        old_date = now - timedelta(days=91)

        # Create BATCH_SIZE * 2 + 500 old events
        num_events = BATCH_SIZE * 2 + 500
        for i in range(num_events):
            event = AuditEvent(
                occurred_at=old_date,
                tenant_id=test_tenant.id,
                actor_type="user",
                entity_name="job",
                entity_id=f"job-{i}",
                action="INSERT",
            )
            db_session.add(event)

        db_session.commit()

        # Run archive
        result = archive_old_events(db_session)

        # Should process all events in batches
        assert result["exported_count"] == num_events
        assert result["deleted_count"] == num_events

        # Verify multiple S3 calls (one per batch)
        expected_batches = (num_events + BATCH_SIZE - 1) // BATCH_SIZE
        assert mock_s3_client.put_object.call_count == expected_batches


class TestGetArchiveStatistics:
    """Test archive statistics helper function."""

    def test_get_archive_statistics_empty_database(self, db_session):
        """Test statistics with no events."""
        stats = get_archive_statistics(db_session)

        assert stats["total_events"] == 0
        assert stats["hot_events"] == 0
        assert stats["archival_candidates"] == 0
        assert stats["oldest_event_date"] is None
        assert stats["newest_event_date"] is None

    def test_get_archive_statistics_mixed_ages(self, db_session, test_tenant):
        """Test statistics with mix of old and recent events."""
        now = datetime.now(UTC)

        # Old event
        old_event = AuditEvent(
            occurred_at=now - timedelta(days=91),
            tenant_id=test_tenant.id,
            actor_type="user",
            entity_name="job",
            entity_id="old",
            action="INSERT",
        )
        db_session.add(old_event)

        # Recent event
        recent_event = AuditEvent(
            occurred_at=now - timedelta(days=30),
            tenant_id=test_tenant.id,
            actor_type="user",
            entity_name="job",
            entity_id="recent",
            action="INSERT",
        )
        db_session.add(recent_event)

        db_session.commit()

        stats = get_archive_statistics(db_session)

        assert stats["total_events"] == 2
        assert stats["hot_events"] == 1  # Recent event
        assert stats["archival_candidates"] == 1  # Old event
        assert stats["oldest_event_date"] is not None
        assert stats["newest_event_date"] is not None


class TestJSONLFormat:
    """Test JSONL serialization format compliance."""

    @patch("tasks.archive_audit_logs.boto3.client")
    def test_jsonl_format_valid_json_per_line(
        self, mock_boto3_client, db_session, test_tenant
    ):
        """Test that exported JSONL has valid JSON on each line."""
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        now = datetime.now(UTC)
        old_date = now - timedelta(days=91)
        timestamp = now.isoformat()

        # Create events with various payloads
        events = []
        for i in range(5):
            event = AuditEvent(
                occurred_at=old_date,
                tenant_id=test_tenant.id,
                actor_type="user" if i % 2 == 0 else "system",
                entity_name=f"entity_{i}",
                entity_id=f"id_{i}",
                action="INSERT" if i % 2 == 0 else "UPDATE",
                new_values={"field": f"value_{i}", "nested": {"count": i}},
                contextdata={"source": "api", "version": "v1"},
            )
            db_session.add(event)
            events.append(event)

        db_session.commit()
        for e in events:
            db_session.refresh(e)

        # Export
        result = _batch_export_to_s3(events, timestamp)

        assert result is True

        # Extract and validate JSONL
        call_args = mock_s3_client.put_object.call_args
        gz_body = call_args[1]["Body"]

        with gzip.GzipFile(fileobj=io.BytesIO(gz_body), mode="rb") as gz_file:
            decompressed = gz_file.read().decode("utf-8")

        lines = decompressed.strip().split("\n")
        assert len(lines) == 5

        # Verify each line is independently valid JSON
        for i, line in enumerate(lines):
            parsed = json.loads(line)  # Should not raise
            assert isinstance(parsed, dict)
            assert "id" in parsed
            assert "occurred_at" in parsed
            assert "entity_name" in parsed
            assert parsed["entity_name"] == f"entity_{i}"

    @patch("tasks.archive_audit_logs.boto3.client")
    def test_jsonl_format_preserves_all_fields(
        self, mock_boto3_client, db_session, test_tenant
    ):
        """Test JSONL preserves all audit event fields including complex types."""
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        now = datetime.now(UTC)
        old_date = now - timedelta(days=91)
        timestamp = now.isoformat()

        event = AuditEvent(
            occurred_at=old_date,
            tenant_id=test_tenant.id,
            user_id=uuid4(),
            actor_type="user",
            user_role="manager",
            ip="10.0.0.1",
            user_agent="CustomAgent/1.0",
            request_id="req-abc123",
            correlation_id="corr-xyz789",
            idempotency_key="idem-key-456",
            entity_name="job",
            entity_id="job-789",
            action="UPDATE",
            old_values={"status": "draft", "amount_cents": 50000},
            new_values={"status": "issued", "amount_cents": 50000},
            reason="Manual status update",
            contextdata={"browser": "Chrome", "location": "office"},
            prev_hash="abc123",
            self_hash="def456",
            hashed_at=old_date,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        # Export
        result = _batch_export_to_s3([event], timestamp)
        assert result is True

        # Extract JSONL
        call_args = mock_s3_client.put_object.call_args
        gz_body = call_args[1]["Body"]

        with gzip.GzipFile(fileobj=io.BytesIO(gz_body), mode="rb") as gz_file:
            decompressed = gz_file.read().decode("utf-8")

        parsed = json.loads(decompressed.strip())

        # Verify all fields are present
        assert parsed["user_role"] == "manager"
        assert parsed["ip"] == "10.0.0.1"
        assert parsed["user_agent"] == "CustomAgent/1.0"
        assert parsed["request_id"] == "req-abc123"
        assert parsed["correlation_id"] == "corr-xyz789"
        assert parsed["idempotency_key"] == "idem-key-456"
        assert parsed["old_values"] == {"status": "draft", "amount_cents": 50000}
        assert parsed["new_values"] == {"status": "issued", "amount_cents": 50000}
        assert parsed["reason"] == "Manual status update"
        assert parsed["contextdata"] == {"browser": "Chrome", "location": "office"}
        assert parsed["prev_hash"] == "abc123"
        assert parsed["self_hash"] == "def456"
