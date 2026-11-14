"""
Tests for conversation session cleanup background jobs.

This module tests the Celery tasks that manage session lifecycle:
- expire_old_sessions: Mark sessions > 24 hours old as expired
- archive_old_sessions: Mark sessions > 30 days old as archived
- cleanup_orphaned_messages: Delete messages without valid session

Design Reference: Task #15 - Session Expiration & Cleanup
Gap Reference: Gap #19 in phase-1-4-implementation-gap-analysis.md
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.models.ai import ConversationMessage, ConversationSession
from app.models.core import Tenant, User
from tasks.cleanup_sessions import (
    archive_old_sessions,
    cleanup_orphaned_messages,
    expire_old_sessions,
    generate_session_summary,
)

# ==================== HELPER FUNCTIONS ====================


def create_test_session(
    db_session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str = "active",
    created_at: datetime = None,
    expires_at: datetime = None,
    context_window: dict = None,
) -> ConversationSession:
    """Helper to create a test conversation session."""
    session = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        status=status,
        context_window_json=context_window,
        expires_at=expires_at,
        is_active=(status == "active"),
        created_at=created_at or datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def create_test_message(
    db_session,
    session_id: uuid.UUID,
    role: str = "user",
    content: str = "Test message",
    created_at: datetime = None,
    tenant_id: uuid.UUID = None,
) -> ConversationMessage:
    """Helper to create a test conversation message."""
    message = ConversationMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        tenant_id=tenant_id,
        role=role,
        content_text=content,
        created_at=created_at or datetime.now(UTC),
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message


# ==================== UNIT TESTS - EXPIRE OLD SESSIONS ====================


class TestExpireOldSessions:
    """Tests for expire_old_sessions task."""

    def test_expire_old_sessions_marks_old_sessions(
        self, db_session, test_tenant, test_user
    ):
        """Old active sessions (>24h) are marked expired with summary."""
        # Create old active session (25 hours old)
        old_time = datetime.now(UTC) - timedelta(hours=25)
        old_session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="active",
            created_at=old_time,
            context_window={"active_customer_id": "123"},
        )

        # Create some messages
        create_test_message(
            db_session, old_session.id, "user", "Hello", tenant_id=test_tenant.id
        )
        create_test_message(
            db_session,
            old_session.id,
            "assistant",
            "Hi there",
            tenant_id=test_tenant.id,
        )

        # Run expire task
        result = expire_old_sessions(db_session)

        # Verify results
        assert result["expired_count"] == 1
        assert result["summary_generated_count"] == 1

        # Verify session was updated
        db_session.refresh(old_session)
        assert old_session.status == "abandoned"
        assert old_session.is_active is False
        assert old_session.expires_at is not None
        assert old_session.context_summary is not None
        assert "Customer: 123" in old_session.context_summary
        assert "2 messages" in old_session.context_summary

    def test_expire_old_sessions_skips_recent_sessions(
        self, db_session, test_tenant, test_user
    ):
        """Recent sessions (<24h) remain active."""
        # Create recent active session (2 hours old)
        recent_time = datetime.now(UTC) - timedelta(hours=2)
        recent_session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="active",
            created_at=recent_time,
        )

        # Run expire task
        result = expire_old_sessions(db_session)

        # Verify no sessions expired
        assert result["expired_count"] == 0
        assert result["summary_generated_count"] == 0

        # Verify session unchanged
        db_session.refresh(recent_session)
        assert recent_session.status == "active"
        assert recent_session.is_active is True
        assert recent_session.expires_at is None

    def test_expire_old_sessions_generates_summary_with_entities(
        self, db_session, test_tenant, test_user
    ):
        """Summary extracted from context_window_json with all entities."""
        # Create old session with full context
        old_time = datetime.now(UTC) - timedelta(hours=30)
        old_session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="active",
            created_at=old_time,
            context_window={
                "active_customer_id": "cust-123",
                "active_quote_id": "quote-456",
                "active_job_id": "job-789",
            },
        )

        # Create messages
        for i in range(5):
            create_test_message(
                db_session,
                old_session.id,
                "user",
                f"Message {i}",
                tenant_id=test_tenant.id,
            )

        # Run expire task
        result = expire_old_sessions(db_session)

        # Verify summary contains all entities
        db_session.refresh(old_session)
        summary = old_session.context_summary
        assert "Customer: cust-123" in summary
        assert "Quote: quote-456" in summary
        assert "Job: job-789" in summary
        assert "5 messages" in summary

    def test_expire_old_sessions_handles_empty_context(
        self, db_session, test_tenant, test_user
    ):
        """Sessions without context_window_json get default summary."""
        # Create old session with no context
        old_time = datetime.now(UTC) - timedelta(hours=25)
        old_session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="active",
            created_at=old_time,
            context_window=None,  # No context
        )

        # Run expire task
        result = expire_old_sessions(db_session)

        # Verify summary generated
        db_session.refresh(old_session)
        assert old_session.context_summary is not None
        assert "0 messages" in old_session.context_summary

    def test_expire_old_sessions_skips_already_expired(
        self, db_session, test_tenant, test_user
    ):
        """Already expired sessions are not processed again."""
        # Create old expired session
        old_time = datetime.now(UTC) - timedelta(hours=25)
        expired_session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="abandoned",
            created_at=old_time,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        # Run expire task
        result = expire_old_sessions(db_session)

        # Verify no sessions processed
        assert result["expired_count"] == 0

    def test_expire_old_sessions_preserves_existing_summary(
        self, db_session, test_tenant, test_user
    ):
        """Sessions with existing summary don't get overwritten."""
        # Create old session with existing summary
        old_time = datetime.now(UTC) - timedelta(hours=25)
        old_session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="active",
            created_at=old_time,
            context_window={"active_customer_id": "123"},
        )
        old_session.context_summary = "Existing custom summary"
        db_session.add(old_session)
        db_session.commit()

        # Run expire task
        result = expire_old_sessions(db_session)

        # Verify summary not overwritten
        assert result["expired_count"] == 1
        assert result["summary_generated_count"] == 0  # No new summary
        db_session.refresh(old_session)
        assert old_session.context_summary == "Existing custom summary"


# ==================== UNIT TESTS - ARCHIVE OLD SESSIONS ====================


class TestArchiveOldSessions:
    """Tests for archive_old_sessions task."""

    def test_archive_old_sessions_marks_old_expired(
        self, db_session, test_tenant, test_user
    ):
        """Expired sessions (>30d) are marked archived."""
        # Create old expired session (35 days old)
        old_time = datetime.now(UTC) - timedelta(days=35)
        old_session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="abandoned",
            created_at=old_time,
            expires_at=old_time,
        )

        # Run archive task
        result = archive_old_sessions(db_session)

        # Verify results
        assert result["archived_count"] == 1

        # Verify session was updated
        db_session.refresh(old_session)
        assert old_session.status == "ended"
        assert old_session.is_active is False

    def test_archive_old_sessions_skips_recent_expired(
        self, db_session, test_tenant, test_user
    ):
        """Recent expired sessions (<30d) remain expired, not archived."""
        # Create recent expired session (10 days old)
        recent_time = datetime.now(UTC) - timedelta(days=10)
        recent_session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="abandoned",
            created_at=recent_time,
            expires_at=recent_time,
        )

        # Run archive task
        result = archive_old_sessions(db_session)

        # Verify no sessions archived
        assert result["archived_count"] == 0

        # Verify session unchanged
        db_session.refresh(recent_session)
        assert recent_session.status == "abandoned"

    def test_archive_old_sessions_skips_active(
        self, db_session, test_tenant, test_user
    ):
        """Active sessions are never archived, even if old."""
        # Create old active session (35 days old)
        old_time = datetime.now(UTC) - timedelta(days=35)
        old_active_session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="active",
            created_at=old_time,
        )

        # Run archive task
        result = archive_old_sessions(db_session)

        # Verify no sessions archived
        assert result["archived_count"] == 0

        # Verify session unchanged
        db_session.refresh(old_active_session)
        assert old_active_session.status == "active"


# ==================== UNIT TESTS - CLEANUP ORPHANED MESSAGES ====================


class TestCleanupOrphanedMessages:
    """Tests for cleanup_orphaned_messages task."""

    def test_cleanup_orphaned_messages_runs_successfully(self, db_session):
        """Cleanup task runs without errors on empty database."""
        # Run cleanup on clean database
        result = cleanup_orphaned_messages(db_session)

        # Verify task completes successfully
        assert "deleted_count" in result
        assert result["deleted_count"] == 0

    def test_cleanup_orphaned_messages_preserves_valid_messages(
        self, db_session, test_tenant, test_user
    ):
        """Messages with valid session_id are preserved."""
        # Create valid session
        session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="active",
        )

        # Create old message with valid session
        old_time = datetime.now(UTC) - timedelta(days=8)
        valid_msg = create_test_message(
            db_session,
            session.id,
            "user",
            "Valid message",
            created_at=old_time,
            tenant_id=test_tenant.id,
        )

        # Run cleanup task
        result = cleanup_orphaned_messages(db_session)

        # Verify no messages deleted (all valid)
        assert result["deleted_count"] == 0

        # Verify message still exists
        msg = db_session.get(ConversationMessage, valid_msg.id)
        assert msg is not None


# ==================== INTEGRATION TESTS - TENANT ISOLATION ====================


class TestTenantIsolation:
    """Tests for multi-tenant isolation in cleanup tasks."""

    def test_expire_old_sessions_respects_tenant_isolation(
        self, db_session, test_tenant, test_user
    ):
        """Sessions from different tenants are isolated."""
        # Create second tenant and user
        tenant_b = Tenant(
            id=uuid.uuid4(),
            name="Tenant B",
            subdomain="tenant-b",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(tenant_b)
        db_session.commit()

        user_b = User(
            id=uuid.uuid4(),
            email="user_b@tenantb.com",
            first_name="User",
            last_name="B",
            is_active=True,
        )
        db_session.add(user_b)
        db_session.commit()

        # Create old sessions for both tenants
        old_time = datetime.now(UTC) - timedelta(hours=25)
        session_a = create_test_session(
            db_session, test_tenant.id, test_user.id, "active", old_time
        )
        session_b = create_test_session(
            db_session, tenant_b.id, user_b.id, "active", old_time
        )

        # Run expire task
        result = expire_old_sessions(db_session)

        # Verify both sessions expired (tenant isolation respected)
        assert result["expired_count"] == 2

        # Verify each tenant's session updated independently
        db_session.refresh(session_a)
        db_session.refresh(session_b)
        assert session_a.status == "abandoned"
        assert session_b.status == "abandoned"


# ==================== INTEGRATION TESTS - CELERY TASK REGISTRATION ====================


class TestCeleryTaskRegistration:
    """Tests for Celery task registration and configuration."""

    def test_expire_old_sessions_task_registered(self):
        """Celery task 'expire_old_sessions' is registered."""
        from core.celery_app import celery_app

        registered_tasks = list(celery_app.tasks.keys())
        assert "expire_old_sessions" in registered_tasks

    def test_archive_old_sessions_task_registered(self):
        """Celery task 'archive_old_sessions' is registered."""
        from core.celery_app import celery_app

        registered_tasks = list(celery_app.tasks.keys())
        assert "archive_old_sessions" in registered_tasks

    def test_cleanup_orphaned_messages_task_registered(self):
        """Celery task 'cleanup_orphaned_messages' is registered."""
        from core.celery_app import celery_app

        registered_tasks = list(celery_app.tasks.keys())
        assert "cleanup_orphaned_messages" in registered_tasks

    def test_celery_beat_schedule_includes_session_tasks(self):
        """Beat schedule includes all 3 session cleanup tasks."""
        from core.celery_app import celery_app

        beat_schedule = celery_app.conf.beat_schedule

        # Verify all tasks scheduled
        assert "expire-old-sessions" in beat_schedule
        assert "archive-old-sessions" in beat_schedule
        assert "cleanup-orphaned-messages" in beat_schedule

        # Verify correct task names
        assert beat_schedule["expire-old-sessions"]["task"] == "expire_old_sessions"
        assert beat_schedule["archive-old-sessions"]["task"] == "archive_old_sessions"
        assert (
            beat_schedule["cleanup-orphaned-messages"]["task"]
            == "cleanup_orphaned_messages"
        )

        # Verify schedules are crontab (not immediate)
        from celery.schedules import crontab

        assert isinstance(beat_schedule["expire-old-sessions"]["schedule"], crontab)
        assert isinstance(beat_schedule["archive-old-sessions"]["schedule"], crontab)
        assert isinstance(
            beat_schedule["cleanup-orphaned-messages"]["schedule"], crontab
        )


# ==================== EDGE CASES ====================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_generate_session_summary_with_null_context(
        self, db_session, test_tenant, test_user
    ):
        """Null context_window_json doesn't break summary generation."""
        session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="active",
            context_window=None,
        )

        # Generate summary
        summary = generate_session_summary(session, db_session)

        # Verify summary generated without errors
        assert summary is not None
        assert "0 messages" in summary

    def test_expire_sessions_handles_no_messages(
        self, db_session, test_tenant, test_user
    ):
        """Sessions without messages get correct summary."""
        old_time = datetime.now(UTC) - timedelta(hours=25)
        session = create_test_session(
            db_session,
            test_tenant.id,
            test_user.id,
            status="active",
            created_at=old_time,
            context_window={"active_customer_id": "123"},
        )

        # Run expire task
        result = expire_old_sessions(db_session)

        # Verify summary shows 0 messages
        db_session.refresh(session)
        assert "0 messages" in session.context_summary

    def test_cleanup_sessions_handles_empty_tables(self, db_session):
        """Cleanup tasks handle empty tables gracefully."""
        # Run all cleanup tasks on empty database
        expire_result = expire_old_sessions(db_session)
        archive_result = archive_old_sessions(db_session)
        cleanup_result = cleanup_orphaned_messages(db_session)

        # Verify all return zero counts
        assert expire_result["expired_count"] == 0
        assert archive_result["archived_count"] == 0
        assert cleanup_result["deleted_count"] == 0

    def test_expire_sessions_atomic_updates(self, db_session, test_tenant, test_user):
        """Multiple sessions updated atomically (all or nothing)."""
        # Create multiple old sessions
        old_time = datetime.now(UTC) - timedelta(hours=25)
        sessions = []
        for i in range(3):
            session = create_test_session(
                db_session, test_tenant.id, test_user.id, "active", old_time
            )
            sessions.append(session)

        # Run expire task
        result = expire_old_sessions(db_session)

        # Verify all sessions updated
        assert result["expired_count"] == 3
        for session in sessions:
            db_session.refresh(session)
            assert session.status == "abandoned"
