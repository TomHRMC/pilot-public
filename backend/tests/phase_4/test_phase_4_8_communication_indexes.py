"""
Test Suite: Phase 4.8 Task 7 - Add Communication Domain Composite Indexes
Tests index creation for conversation threading and notification scheduling

Reference: phase-4.8-db-schema-sync-4-plan.md
"""

from sqlalchemy import text
from sqlmodel import Session


class TestCommunicationIndexes:
    """Verify communication domain composite indexes were created"""

    def test_communication_indexes_exist(self, db_session: Session):
        """Verify all 5 communication indexes were created"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE indexname IN (
                'idx_conv_msg_session_time',
                'idx_notif_outbox_status_sched',
                'idx_notif_outbox_channel_status',
                'idx_notif_outbox_provider_msg',
                'idx_notif_outbox_created_at'
            )
            ORDER BY indexname
        """)
        )
        indexes = [row[0] for row in result]
        expected_count = 5
        assert len(indexes) == expected_count, (
            f"Expected {expected_count} indexes, found {len(indexes)}: {indexes}"
        )

    def test_conversation_message_indexes_definition(self, db_session: Session):
        """Verify conversation_message indexes have correct definitions"""
        result = db_session.execute(
            text("""
            SELECT indexname, indexdef FROM pg_indexes
            WHERE tablename = 'conversation_message'
            AND indexname = 'idx_conv_msg_session_time'
        """)
        )
        indexes = {row[0]: row[1] for row in result}

        # Verify conversation threading index
        assert "idx_conv_msg_session_time" in indexes
        assert "session_id" in indexes["idx_conv_msg_session_time"]
        assert "created_at" in indexes["idx_conv_msg_session_time"]

    def test_notification_outbox_indexes_definition(self, db_session: Session):
        """Verify notification_outbox indexes have correct definitions"""
        result = db_session.execute(
            text("""
            SELECT indexname, indexdef FROM pg_indexes
            WHERE tablename = 'notification_outbox'
            AND indexname IN (
                'idx_notif_outbox_status_sched',
                'idx_notif_outbox_channel_status',
                'idx_notif_outbox_provider_msg',
                'idx_notif_outbox_created_at'
            )
        """)
        )
        indexes = {row[0]: row[1] for row in result}

        # Verify critical background worker index
        assert "idx_notif_outbox_status_sched" in indexes
        assert "status" in indexes["idx_notif_outbox_status_sched"]
        assert "scheduled_at" in indexes["idx_notif_outbox_status_sched"]

        # Verify channel filtering index
        assert "idx_notif_outbox_channel_status" in indexes
        assert "channel" in indexes["idx_notif_outbox_channel_status"]
        assert "status" in indexes["idx_notif_outbox_channel_status"]

        # Verify provider callback index
        assert "idx_notif_outbox_provider_msg" in indexes
        assert "provider_message_id" in indexes["idx_notif_outbox_provider_msg"]

        # Verify time-series ordering index
        assert "idx_notif_outbox_created_at" in indexes
        assert "created_at" in indexes["idx_notif_outbox_created_at"]
