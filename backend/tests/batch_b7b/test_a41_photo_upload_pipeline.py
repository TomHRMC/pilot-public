"""
tests/batch_b7b/test_a41_photo_upload_pipeline.py

Tests for B7b/A41 — Resumable Photo Upload Pipeline.

Test focus cases (per design doc):
  1. job_attachment has upload_status, s3_upload_session_id, upload_completed_at, expense_id columns
  2. cleanup_incomplete_photo_uploads_impl marks orphaned rows as 'failed'
  3. cleanup_incomplete_photo_uploads_impl does NOT mark rows < 24 hours old
  4. cleanup_incomplete_photo_uploads_impl returns correct count
  5. s3_service.compute_chunk_count returns ceil(size/chunk_size), min 1
  6. s3_service.build_photo_object_key returns correct path
  7. tenant_settings has the 4 new offline/photo columns (via information_schema)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.fulfillment import JobAttachment
from services.s3_service import build_photo_object_key, compute_chunk_count
from tasks.photo_cleanup_tasks import _cleanup_incomplete_photo_uploads_impl

# ---------------------------------------------------------------------------
# Helper: raw INSERT with backdated created_at
# ---------------------------------------------------------------------------


def _insert_attachment_raw(
    db_session,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    upload_status: str,
    hours_ago: int,
) -> uuid.UUID:
    """
    Insert a job_attachment row with a backdated created_at using raw INSERT.
    Must use raw SQL because guard_created_fields_immutable trigger prevents
    any UPDATE of created_at after INSERT.
    """
    att_id = uuid.uuid4()
    past_ts = datetime.now(UTC) - timedelta(hours=hours_ago)
    db_session.execute(
        text("""
        INSERT INTO job_attachment (
            id, tenant_id, job_id, file_name, mime_type, size_bytes,
            object_key, upload_status, s3_upload_session_id,
            created_at, updated_at
        ) VALUES (
            :id, :tenant_id, :job_id, :file_name, :mime_type, :size_bytes,
            :object_key, :upload_status, :session_id,
            :created_at, :updated_at
        )
    """),
        {
            "id": str(att_id),
            "tenant_id": str(tenant_id),
            "job_id": str(job_id),
            "file_name": "test_photo.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 1_000_000,
            "object_key": f"tenants/{tenant_id}/photos/{att_id}/test_photo.jpg",
            "upload_status": upload_status,
            "session_id": "mock-session-id"
            if upload_status in ("pending_upload", "uploading")
            else None,
            "created_at": past_ts,
            "updated_at": past_ts,
        },
    )
    db_session.commit()
    return att_id


# ---------------------------------------------------------------------------
# ORM model columns (uses test_job + tenant_a from conftest)
# ---------------------------------------------------------------------------


class TestJobAttachmentColumns:
    def test_upload_status_column_exists(self, db_session, test_job, tenant_a):
        """job_attachment.upload_status column exists and stores value."""
        att = JobAttachment(
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            file_name="test.jpg",
            mime_type="image/jpeg",
            size_bytes=100,
            object_key="test/key.jpg",
            upload_status="pending_upload",
        )
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)
        assert att.upload_status == "pending_upload"

    def test_s3_upload_session_id_column_exists(self, db_session, test_job, tenant_a):
        """job_attachment.s3_upload_session_id column exists."""
        att = JobAttachment(
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            file_name="test.jpg",
            mime_type="image/jpeg",
            size_bytes=100,
            object_key="test/key.jpg",
            s3_upload_session_id="mock-session-xyz",
        )
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)
        assert att.s3_upload_session_id == "mock-session-xyz"

    def test_upload_completed_at_column_exists(self, db_session, test_job, tenant_a):
        """job_attachment.upload_completed_at column exists."""
        now = datetime.now(UTC)
        att = JobAttachment(
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            file_name="test.jpg",
            mime_type="image/jpeg",
            size_bytes=100,
            object_key="test/key.jpg",
            upload_completed_at=now,
        )
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)
        assert att.upload_completed_at is not None

    def test_expense_id_column_exists_nullable(self, db_session, test_job, tenant_a):
        """job_attachment.expense_id column exists and is nullable."""
        att = JobAttachment(
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            file_name="test.jpg",
            mime_type="image/jpeg",
            size_bytes=100,
            object_key="test/key.jpg",
            expense_id=None,
        )
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)
        assert att.expense_id is None

    def test_upload_status_null_allowed(self, db_session, test_job, tenant_a):
        """NULL upload_status is allowed (pre-B7b rows)."""
        att = JobAttachment(
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            file_name="legacy.jpg",
            mime_type="image/jpeg",
            size_bytes=100,
            object_key="test/legacy.jpg",
            upload_status=None,
        )
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)
        assert att.upload_status is None


# ---------------------------------------------------------------------------
# Platform settings catalog — offline/photo columns (FIND-086 update)
# ---------------------------------------------------------------------------


class TestTenantSettingsOfflineColumns:
    """Post-FIND-086: checks platform_setting_catalog instead of tenant_settings columns."""

    def _get_catalog_row(self, db_session, key: str):
        """Query platform_setting_catalog for a key."""
        from sqlmodel import select

        from app.models.platform_setting import PlatformSettingCatalog

        return db_session.exec(
            select(PlatformSettingCatalog).where(PlatformSettingCatalog.key == key)
        ).first()

    def test_photo_upload_wifi_only_column_exists_not_null(self, db_session):
        """photo_upload_wifi_only key exists in platform_setting_catalog, boolean type."""
        row = self._get_catalog_row(db_session, "photo_upload_wifi_only")
        assert row is not None, (
            "photo_upload_wifi_only column must exist in platform_setting_catalog"
        )
        assert row.value_type == "boolean"

    def test_photo_local_retention_days_column_exists_not_null(self, db_session):
        """photo_local_retention_days key exists in platform_setting_catalog."""
        row = self._get_catalog_row(db_session, "photo_local_retention_days")
        assert row is not None, "photo_local_retention_days column must exist"
        assert row.value_type == "integer"

    def test_offline_hard_limit_hours_column_exists_nullable(self, db_session):
        """offline_hard_limit_hours key exists in catalog (platform default 72)."""
        row = self._get_catalog_row(db_session, "offline_hard_limit_hours")
        assert row is not None, "offline_hard_limit_hours column must exist"
        assert row.value_type == "integer"

    def test_voice_offline_audio_storage_limit_mb_column_exists(self, db_session):
        """voice_offline_audio_storage_limit_mb key exists in catalog."""
        row = self._get_catalog_row(db_session, "voice_offline_audio_storage_limit_mb")
        assert row is not None, "voice_offline_audio_storage_limit_mb column must exist"
        assert row.value_type == "integer"


# ---------------------------------------------------------------------------
# cleanup_incomplete_photo_uploads_impl
# ---------------------------------------------------------------------------


class TestCleanupIncompletePhotoUploads:
    def test_marks_old_pending_as_failed(self, db_session, test_job, tenant_a):
        """Rows older than cutoff with pending_upload → upload_status = 'failed'."""
        att_id = _insert_attachment_raw(
            db_session,
            tenant_a.id,
            test_job.id,
            upload_status="pending_upload",
            hours_ago=25,
        )

        result = _cleanup_incomplete_photo_uploads_impl(db_session, cutoff_hours=24)

        att = db_session.exec(
            select(JobAttachment).where(JobAttachment.id == att_id)
        ).first()
        assert att.upload_status == "failed"
        assert result["cleaned_up"] >= 1

    def test_marks_old_uploading_as_failed(self, db_session, test_job, tenant_a):
        """Rows older than cutoff with uploading → upload_status = 'failed'."""
        att_id = _insert_attachment_raw(
            db_session,
            tenant_a.id,
            test_job.id,
            upload_status="uploading",
            hours_ago=26,
        )

        _cleanup_incomplete_photo_uploads_impl(db_session, cutoff_hours=24)

        att = db_session.exec(
            select(JobAttachment).where(JobAttachment.id == att_id)
        ).first()
        assert att.upload_status == "failed"

    def test_does_not_touch_recent_pending(self, db_session, test_job, tenant_a):
        """Rows younger than cutoff (just created) are NOT marked failed."""
        att = JobAttachment(
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            file_name="recent.jpg",
            mime_type="image/jpeg",
            size_bytes=100,
            object_key="test/recent.jpg",
            upload_status="pending_upload",
            s3_upload_session_id="recent-session",
        )
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)

        _cleanup_incomplete_photo_uploads_impl(db_session, cutoff_hours=24)

        db_session.refresh(att)
        assert att.upload_status == "pending_upload"

    def test_does_not_touch_complete_rows(self, db_session, test_job, tenant_a):
        """Rows with upload_status='complete' are never touched by cleanup."""
        att_id = _insert_attachment_raw(
            db_session,
            tenant_a.id,
            test_job.id,
            upload_status="complete",
            hours_ago=48,
        )

        _cleanup_incomplete_photo_uploads_impl(db_session, cutoff_hours=24)

        att = db_session.exec(
            select(JobAttachment).where(JobAttachment.id == att_id)
        ).first()
        assert att.upload_status == "complete"

    def test_returns_integer_count(self, db_session):
        """Returns a dict with an integer 'cleaned_up' key."""
        result = _cleanup_incomplete_photo_uploads_impl(db_session, cutoff_hours=24)
        assert isinstance(result["cleaned_up"], int)
        assert result["cleaned_up"] >= 0


# ---------------------------------------------------------------------------
# s3_service utilities (pure unit tests, no DB needed)
# ---------------------------------------------------------------------------


class TestS3ServiceUtils:
    def test_compute_chunk_count_exact_division(self):
        """10 MB file with 5 MB chunk = 2 parts."""
        result = compute_chunk_count(10_485_760)
        assert result == 2

    def test_compute_chunk_count_rounds_up(self):
        """6 MB file with 5 MB chunk = 2 parts (ceil)."""
        result = compute_chunk_count(6_291_456)
        assert result == 2

    def test_compute_chunk_count_small_file(self):
        """File smaller than chunk size → 1 part."""
        result = compute_chunk_count(100_000)
        assert result == 1

    def test_compute_chunk_count_min_one(self):
        """0-byte file → still 1 part (minimum)."""
        result = compute_chunk_count(0)
        assert result == 1

    def test_build_photo_object_key(self):
        """Object key uses the expected path pattern."""
        tenant_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        att_id = str(uuid.uuid4())
        file_name = "site_photo_001.jpg"

        key = build_photo_object_key(tenant_id, job_id, att_id, file_name)

        assert key == f"tenants/{tenant_id}/jobs/{job_id}/photos/{att_id}/{file_name}"
        assert "tenants/" in key
        assert "jobs/" in key
        assert "photos/" in key
        assert file_name in key


# ---------------------------------------------------------------------------
# BEHAVIORAL TESTS: Photo upload pipeline endpoints (FIND-134)
# ---------------------------------------------------------------------------


class TestInitiateUploadBehavior:
    """Test the _initiate_upload_impl function with S3 mocking."""

    def test_initiate_creates_correct_db_state(self, db_session, test_job, tenant_a):
        """Initiate creates JobAttachment with correct columns populated."""
        from unittest.mock import patch

        from api.routes.photos import (
            InitiateUploadRequest,
            _initiate_upload_impl,
        )
        from core.test_context import TestUserContext

        with (
            patch("api.routes.photos.create_multipart_upload") as mock_create,
            patch("api.routes.photos.generate_presigned_part_urls") as mock_gen,
        ):
            mock_create.return_value = "mock-upload-id-123"
            mock_gen.return_value = ["http://presigned-url-1", "http://presigned-url-2"]

            request = InitiateUploadRequest(
                job_id=test_job.id,
                file_size_bytes=5_000_000,
                mime_type="image/jpeg",
                file_name="test_photo.jpg",
                idempotency_uuid=uuid.uuid4(),
            )

            user_context = TestUserContext(
                id=uuid.uuid4(),
                tenant_id=tenant_a.id,
            )

            response = _initiate_upload_impl(request, db_session, user_context)

            # Verify response
            assert response.pilot_photo_id is not None
            assert response.s3_upload_session_id == "mock-upload-id-123"
            assert len(response.presigned_chunk_urls) == 2

            # Verify DB state
            attachment = db_session.exec(
                select(JobAttachment)
                .where(JobAttachment.id == response.pilot_photo_id)
                .where(JobAttachment.tenant_id == tenant_a.id)
            ).first()

            assert attachment is not None
            assert attachment.upload_status == "pending_upload"
            assert attachment.object_key.startswith(f"tenants/{tenant_a.id}/")
            assert attachment.s3_upload_session_id == "mock-upload-id-123"
            assert attachment.tenant_id == tenant_a.id

    def test_resume_idempotency(self, db_session, test_job, tenant_a):
        """Resume logic: same file_name+size returns existing row, no duplicate."""
        from unittest.mock import patch

        from api.routes.photos import (
            InitiateUploadRequest,
            _initiate_upload_impl,
        )
        from core.test_context import TestUserContext

        with (
            patch("api.routes.photos.create_multipart_upload") as mock_create,
            patch("api.routes.photos.generate_presigned_part_urls") as mock_gen,
        ):
            mock_create.return_value = "mock-upload-id-first"
            mock_gen.return_value = ["http://presigned-url-1"]

            user_context = TestUserContext(
                id=uuid.uuid4(),
                tenant_id=tenant_a.id,
            )

            # First initiate
            request1 = InitiateUploadRequest(
                job_id=test_job.id,
                file_size_bytes=5_000_000,
                mime_type="image/jpeg",
                file_name="test_photo.jpg",
                idempotency_uuid=uuid.uuid4(),
            )
            response1 = _initiate_upload_impl(request1, db_session, user_context)
            pilot_photo_id_1 = response1.pilot_photo_id

            # Count rows after first initiate
            count_after_first = db_session.exec(
                select(JobAttachment)
                .where(JobAttachment.job_id == test_job.id)
                .where(JobAttachment.upload_status.in_(["pending_upload", "uploading"]))
            ).all()
            assert len(count_after_first) == 1

            # Second initiate with same file_name + size_bytes (resume logic)
            mock_create.return_value = "mock-upload-id-second"
            request2 = InitiateUploadRequest(
                job_id=test_job.id,
                file_size_bytes=5_000_000,  # Same size
                mime_type="image/jpeg",
                file_name="test_photo.jpg",  # Same file name
                idempotency_uuid=uuid.uuid4(),
            )
            response2 = _initiate_upload_impl(request2, db_session, user_context)

            # Verify same pilot_photo_id is returned
            assert response2.pilot_photo_id == pilot_photo_id_1
            # Verify no new row created
            count_after_second = db_session.exec(
                select(JobAttachment)
                .where(JobAttachment.job_id == test_job.id)
                .where(JobAttachment.upload_status.in_(["pending_upload", "uploading"]))
            ).all()
            assert len(count_after_second) == 1


class TestCompleteUploadBehavior:
    """Test the _complete_upload_impl function with S3 mocking."""

    def test_complete_creates_correct_db_state(self, db_session, test_job, tenant_a):
        """Complete sets upload_status='complete', upload_completed_at, clears session_id."""
        from unittest.mock import patch

        from api.routes.photos import (
            ChunkEtag,
            CompleteUploadRequest,
            InitiateUploadRequest,
            _complete_upload_impl,
            _initiate_upload_impl,
        )
        from core.test_context import TestUserContext

        user_context = TestUserContext(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            user_id=uuid.uuid4(),
        )

        with (
            patch("api.routes.photos.create_multipart_upload") as mock_create,
            patch("api.routes.photos.generate_presigned_part_urls") as mock_gen,
            patch("api.routes.photos.complete_multipart_upload") as mock_complete,
        ):
            mock_create.return_value = "mock-upload-id-123"
            mock_gen.return_value = ["http://presigned-url-1"]

            # First initiate
            request = InitiateUploadRequest(
                job_id=test_job.id,
                file_size_bytes=5_000_000,
                mime_type="image/jpeg",
                file_name="test_photo.jpg",
                idempotency_uuid=uuid.uuid4(),
            )
            response = _initiate_upload_impl(request, db_session, user_context)

            # Now complete
            complete_request = CompleteUploadRequest(
                pilot_photo_id=response.pilot_photo_id,
                s3_upload_session_id="mock-upload-id-123",
                chunk_etags=[
                    ChunkEtag(part_number=1, etag="etag-1"),
                ],
            )

            complete_response = _complete_upload_impl(
                complete_request, db_session, user_context
            )

            # Verify response
            assert complete_response.id == response.pilot_photo_id
            assert complete_response.upload_completed_at is not None

            # Verify DB state
            attachment = db_session.exec(
                select(JobAttachment).where(JobAttachment.id == response.pilot_photo_id)
            ).first()

            assert attachment.upload_status == "complete"
            assert attachment.upload_completed_at is not None
            # Verify upload_completed_at is recent (UTC)
            now = datetime.now(UTC)
            assert (now - attachment.upload_completed_at).total_seconds() < 5
            assert attachment.s3_upload_session_id is None

    def test_recomplete_returns_409(self, db_session, test_job, tenant_a):
        """Re-complete on already-complete row returns 409."""
        from unittest.mock import patch

        from fastapi import HTTPException

        from api.routes.photos import (
            ChunkEtag,
            CompleteUploadRequest,
            InitiateUploadRequest,
            _complete_upload_impl,
            _initiate_upload_impl,
        )
        from core.test_context import TestUserContext

        user_context = TestUserContext(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
        )

        with (
            patch("api.routes.photos.create_multipart_upload") as mock_create,
            patch("api.routes.photos.generate_presigned_part_urls") as mock_gen,
            patch("api.routes.photos.complete_multipart_upload") as mock_complete,
        ):
            mock_create.return_value = "mock-upload-id-123"
            mock_gen.return_value = ["http://presigned-url-1"]

            # Initiate
            request = InitiateUploadRequest(
                job_id=test_job.id,
                file_size_bytes=5_000_000,
                mime_type="image/jpeg",
                file_name="test_photo.jpg",
                idempotency_uuid=uuid.uuid4(),
            )
            response = _initiate_upload_impl(request, db_session, user_context)

            # First complete
            complete_request = CompleteUploadRequest(
                pilot_photo_id=response.pilot_photo_id,
                s3_upload_session_id="mock-upload-id-123",
                chunk_etags=[ChunkEtag(part_number=1, etag="etag-1")],
            )
            _complete_upload_impl(complete_request, db_session, user_context)

            # Second complete (should return 409)
            with pytest.raises(HTTPException) as exc_info:
                _complete_upload_impl(complete_request, db_session, user_context)

            assert exc_info.value.status_code == 409

    def test_session_mismatch_error(self, db_session, test_job, tenant_a):
        """Complete with wrong s3_upload_session_id returns 400."""
        from unittest.mock import patch

        from fastapi import HTTPException

        from api.routes.photos import (
            ChunkEtag,
            CompleteUploadRequest,
            InitiateUploadRequest,
            _complete_upload_impl,
            _initiate_upload_impl,
        )
        from core.test_context import TestUserContext

        user_context = TestUserContext(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
        )

        with (
            patch("api.routes.photos.create_multipart_upload") as mock_create,
            patch("api.routes.photos.generate_presigned_part_urls") as mock_gen,
        ):
            mock_create.return_value = "mock-upload-id-123"
            mock_gen.return_value = ["http://presigned-url-1"]

            # Initiate
            request = InitiateUploadRequest(
                job_id=test_job.id,
                file_size_bytes=5_000_000,
                mime_type="image/jpeg",
                file_name="test_photo.jpg",
                idempotency_uuid=uuid.uuid4(),
            )
            response = _initiate_upload_impl(request, db_session, user_context)

            # Complete with WRONG session ID
            complete_request = CompleteUploadRequest(
                pilot_photo_id=response.pilot_photo_id,
                s3_upload_session_id="wrong-session-id",
                chunk_etags=[ChunkEtag(part_number=1, etag="etag-1")],
            )

            with pytest.raises(HTTPException) as exc_info:
                _complete_upload_impl(complete_request, db_session, user_context)

            assert exc_info.value.status_code == 400

    def test_cross_tenant_isolation(self, db_session, test_job, tenant_a, tenant_b):
        """Tenant B cannot complete-upload for Tenant A's photo → 404."""
        from unittest.mock import patch

        from fastapi import HTTPException

        from api.routes.photos import (
            ChunkEtag,
            CompleteUploadRequest,
            InitiateUploadRequest,
            _complete_upload_impl,
            _initiate_upload_impl,
        )
        from core.test_context import TestUserContext

        user_a = TestUserContext(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
        )

        user_b = TestUserContext(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
        )

        with (
            patch("api.routes.photos.create_multipart_upload") as mock_create,
            patch("api.routes.photos.generate_presigned_part_urls") as mock_gen,
        ):
            mock_create.return_value = "mock-upload-id-123"
            mock_gen.return_value = ["http://presigned-url-1"]

            # Tenant A initiates
            request = InitiateUploadRequest(
                job_id=test_job.id,
                file_size_bytes=5_000_000,
                mime_type="image/jpeg",
                file_name="test_photo.jpg",
                idempotency_uuid=uuid.uuid4(),
            )
            response = _initiate_upload_impl(request, db_session, user_a)

            # Tenant B tries to complete Tenant A's photo → 404
            complete_request = CompleteUploadRequest(
                pilot_photo_id=response.pilot_photo_id,
                s3_upload_session_id="mock-upload-id-123",
                chunk_etags=[ChunkEtag(part_number=1, etag="etag-1")],
            )

            with pytest.raises(HTTPException) as exc_info:
                _complete_upload_impl(complete_request, db_session, user_b)

            assert exc_info.value.status_code == 404

    def test_expense_id_linkage(self, db_session, test_job, tenant_a, test_user):
        """Initiate with expense_id set stores it correctly in JobAttachment."""
        from unittest.mock import patch

        from api.routes.photos import (
            InitiateUploadRequest,
            _initiate_upload_impl,
        )
        from app.models.fulfillment import JobExpense, JobExpenseCategory
        from core.test_context import TestUserContext

        # Create a valid JobExpenseCategory first
        category = db_session.exec(
            select(JobExpenseCategory).where(JobExpenseCategory.code == "other")
        ).first()
        if not category:
            category = JobExpenseCategory(
                code="other",
                name="Other",
                is_active=True,
            )
            db_session.add(category)
            db_session.flush()

        # Create a valid JobExpense row
        expense = JobExpense(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            user_id=test_user.id,
            description="Test expense",
            cost_cents=10000,
            job_expense_category_code="materials",  # SD-2: "other" not seeded; use "materials"
            billable_cents=10000,
        )
        db_session.add(expense)
        db_session.commit()

        with (
            patch("api.routes.photos.create_multipart_upload") as mock_create,
            patch("api.routes.photos.generate_presigned_part_urls") as mock_gen,
        ):
            mock_create.return_value = "mock-upload-id-123"
            mock_gen.return_value = ["http://presigned-url-1"]

            user_context = TestUserContext(
                id=uuid.uuid4(),
                tenant_id=tenant_a.id,
            )

            request = InitiateUploadRequest(
                job_id=test_job.id,
                file_size_bytes=5_000_000,
                mime_type="image/jpeg",
                file_name="test_photo.jpg",
                expense_id=expense.id,
                idempotency_uuid=uuid.uuid4(),
            )

            response = _initiate_upload_impl(request, db_session, user_context)

            # Verify expense_id is stored
            attachment = db_session.exec(
                select(JobAttachment).where(JobAttachment.id == response.pilot_photo_id)
            ).first()

            assert attachment.expense_id == expense.id

    def test_s3_key_tenant_partition(self, db_session, test_job, tenant_a):
        """S3 object_key always starts with tenants/{tenant_id}/ (no other prefix)."""
        from unittest.mock import patch

        from api.routes.photos import (
            InitiateUploadRequest,
            _initiate_upload_impl,
        )
        from core.test_context import TestUserContext

        with (
            patch("api.routes.photos.create_multipart_upload") as mock_create,
            patch("api.routes.photos.generate_presigned_part_urls") as mock_gen,
        ):
            mock_create.return_value = "mock-upload-id-123"
            mock_gen.return_value = ["http://presigned-url-1"]

            user_context = TestUserContext(
                id=uuid.uuid4(),
                tenant_id=tenant_a.id,
            )

            request = InitiateUploadRequest(
                job_id=test_job.id,
                file_size_bytes=5_000_000,
                mime_type="image/jpeg",
                file_name="test_photo.jpg",
                idempotency_uuid=uuid.uuid4(),
            )

            response = _initiate_upload_impl(request, db_session, user_context)

            attachment = db_session.exec(
                select(JobAttachment).where(JobAttachment.id == response.pilot_photo_id)
            ).first()

            # Verify object key starts with correct tenant prefix
            expected_prefix = f"tenants/{tenant_a.id}/"
            assert attachment.object_key.startswith(expected_prefix), (
                f"object_key '{attachment.object_key}' does not start with '{expected_prefix}'"
            )
            # Verify it follows the pattern: tenants/{tenant_id}/jobs/{job_id}/photos/{attachment_id}/{file_name}
            assert f"jobs/{test_job.id}/" in attachment.object_key
            assert f"photos/{attachment.id}/" in attachment.object_key
            assert attachment.file_name in attachment.object_key
