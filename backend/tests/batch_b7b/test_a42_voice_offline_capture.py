"""
tests/batch_b7b/test_a42_voice_offline_capture.py

Tests for B7b/A42 — Voice Command Offline Capture & Deferred Processing.

Test focus cases (per design doc):
  1. VoiceCommandLog has all 7 new offline columns
  2. processing_status CHECK constraint enforces valid values
  3. idempotency_uuid column exists and is nullable (NULL for synchronous)
  4. _process_voice_audio_async_impl updates processing_status pipeline
  5. _process_voice_audio_async_impl raises ValueError for missing log row
  6. _expire_pending_voice_confirmations_impl returns correct dict shape
  7. Status polling: query by idempotency_uuid returns correct row
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.ai import VoiceCommandLog
from tasks.voice_offline_tasks import (
    _expire_pending_voice_confirmations_impl,
    _process_voice_audio_async_impl,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_voice_log(
    db_session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    processing_status: str = "pending_upload",
    idempotency_uuid: uuid.UUID = None,
    audio_object_key: str = "tenants/test/voice/test.m4a",
) -> VoiceCommandLog:
    log = VoiceCommandLog(
        tenant_id=tenant_id,
        user_id=user_id,
        is_successful=True,
        processing_status=processing_status,
        audio_object_key=audio_object_key,
        captured_at=datetime.now(UTC),
        idempotency_uuid=idempotency_uuid or uuid.uuid4(),
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    return log


# ---------------------------------------------------------------------------
# ORM columns — information_schema verification
# ---------------------------------------------------------------------------


class TestVoiceCommandLogOfflineColumns:
    def _column_info(self, db_session, col: str):
        return db_session.execute(
            text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'voice_command_log'
            AND column_name = :col
        """),
            {"col": col},
        ).fetchone()

    def test_audio_object_key_column(self, db_session):
        row = self._column_info(db_session, "audio_object_key")
        assert row is not None, "audio_object_key must exist"
        assert row[1] == "text"
        assert row[2] == "YES"

    def test_captured_at_column(self, db_session):
        row = self._column_info(db_session, "captured_at")
        assert row is not None, "captured_at must exist"
        assert "timestamp" in row[1]
        assert row[2] == "YES"

    def test_uploaded_at_column(self, db_session):
        row = self._column_info(db_session, "uploaded_at")
        assert row is not None, "uploaded_at must exist"

    def test_transcribed_at_column(self, db_session):
        row = self._column_info(db_session, "transcribed_at")
        assert row is not None, "transcribed_at must exist"

    def test_parsed_at_column(self, db_session):
        row = self._column_info(db_session, "parsed_at")
        assert row is not None, "parsed_at must exist"

    def test_processing_status_column(self, db_session):
        row = self._column_info(db_session, "processing_status")
        assert row is not None, "processing_status must exist"
        assert row[1] == "text"
        assert row[2] == "YES"

    def test_idempotency_uuid_column(self, db_session):
        row = self._column_info(db_session, "idempotency_uuid")
        assert row is not None, "idempotency_uuid must exist"
        assert row[1] == "uuid"
        assert row[2] == "YES"


# ---------------------------------------------------------------------------
# processing_status check constraint
# ---------------------------------------------------------------------------


class TestProcessingStatusConstraint:
    def test_valid_pending_upload_status(self, db_session, test_user, test_tenant):
        """pending_upload is a valid processing_status."""
        log = _make_voice_log(
            db_session, test_tenant.id, test_user.id, "pending_upload"
        )
        assert log.processing_status == "pending_upload"

    def test_valid_completed_status(self, db_session, test_user, test_tenant):
        """completed is a valid processing_status."""
        log = _make_voice_log(db_session, test_tenant.id, test_user.id, "completed")
        assert log.processing_status == "completed"

    def test_valid_failed_status(self, db_session, test_user, test_tenant):
        """failed is a valid processing_status."""
        log = _make_voice_log(db_session, test_tenant.id, test_user.id, "failed")
        assert log.processing_status == "failed"

    def test_null_processing_status_allowed(self, db_session, test_user, test_tenant):
        """NULL processing_status is allowed (synchronous command rows)."""
        log = VoiceCommandLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            is_successful=True,
            processing_status=None,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)
        assert log.processing_status is None


# ---------------------------------------------------------------------------
# Celery task impl
# ---------------------------------------------------------------------------


class TestProcessVoiceAudioAsyncImpl:
    def test_updates_processing_status_to_completed(
        self, db_session, test_user, test_tenant
    ):
        """_process_voice_audio_async_impl drives the row through to 'completed'."""
        log = _make_voice_log(
            db_session,
            test_tenant.id,
            test_user.id,
            processing_status="pending_upload",
        )

        result = _process_voice_audio_async_impl(log.id, db_session)

        db_session.refresh(log)
        assert log.processing_status == "completed"
        assert log.uploaded_at is not None
        assert log.transcribed_at is not None
        assert log.parsed_at is not None
        assert result["status"] == "completed"
        assert result["voice_command_log_id"] == log.id

    def test_raises_value_error_for_missing_row(self, db_session):
        """_process_voice_audio_async_impl raises ValueError for missing log ID."""
        with pytest.raises(ValueError, match="not found"):
            _process_voice_audio_async_impl(99999999, db_session)


# ---------------------------------------------------------------------------
# expire_pending_voice_confirmations_impl
# ---------------------------------------------------------------------------


class TestExpirePendingVoiceConfirmations:
    def test_returns_expired_count_dict(self, db_session):
        """_expire_pending_voice_confirmations_impl returns {expired: N} dict."""
        result = _expire_pending_voice_confirmations_impl(db_session)
        assert isinstance(result, dict)
        assert "expired" in result
        assert isinstance(result["expired"], int)


# ---------------------------------------------------------------------------
# Status polling by idempotency_uuid
# ---------------------------------------------------------------------------


class TestStatusPollingByIdempotencyUUID:
    def test_poll_finds_row_by_idempotency_uuid(
        self, db_session, test_user, test_tenant
    ):
        """Client can find a VoiceCommandLog row by idempotency_uuid for polling."""
        idem_uuid = uuid.uuid4()
        log = _make_voice_log(
            db_session,
            test_tenant.id,
            test_user.id,
            processing_status="transcribing",
            idempotency_uuid=idem_uuid,
        )

        found = db_session.exec(
            select(VoiceCommandLog)
            .where(VoiceCommandLog.idempotency_uuid == idem_uuid)
            .where(VoiceCommandLog.tenant_id == test_tenant.id)
        ).first()

        assert found is not None
        assert found.id == log.id
        assert found.processing_status == "transcribing"

    def test_idempotency_uuid_null_for_synchronous_commands(
        self, db_session, test_user, test_tenant
    ):
        """Synchronous (online) commands can have NULL idempotency_uuid."""
        log = VoiceCommandLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            is_successful=True,
            idempotency_uuid=None,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)
        assert log.idempotency_uuid is None
