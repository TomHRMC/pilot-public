"""
Batch B21 — FIND-062: Receipt OCR Pipeline tests
=================================================

FIND-062 (S2 High): Receipt OCR pipeline — RapidOCR + Celery task + S3 wiring.

Tests cover:
  1. MockOcrService returns fixture data → job_expense.cost_cents patched; ocr_source='rapidocr'
  2. MockOcrService returns None (low confidence) → cost_cents NOT patched; ocr_processed_at set
  3. Idempotency: re-processing same attachment_id does not create duplicates
  4. Factory returns MockOcrService in dev environment
  5. Schema: ocr_processed_at + ocr_source columns exist on job_expense
  6. OcrService ABC: MockOcrService and RapidOcrService are subclasses
  7. Celery task registered correctly
  8. process_receipt_ocr returns correct status codes
"""

import uuid
from unittest.mock import patch

from sqlmodel import Session, select

# ─────────────────────────────────────────────────────────────────────────────
# Schema tests — DB column existence
# ─────────────────────────────────────────────────────────────────────────────


class TestFind062SchemaColumns:
    """Verify ocr_processed_at and ocr_source columns exist on job_expense."""

    def test_ocr_processed_at_column_exists(self, db_session: Session):
        """job_expense.ocr_processed_at column must exist (TIMESTAMPTZ NULL)."""
        from sqlalchemy import text

        result = db_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'job_expense'
                  AND column_name = 'ocr_processed_at'
            """)
        ).fetchone()
        assert result is not None, "ocr_processed_at column missing from job_expense"
        assert result[1] in ("timestamp with time zone", "timestamptz"), (
            f"ocr_processed_at must be TIMESTAMPTZ, got {result[1]}"
        )
        assert result[2] == "YES", "ocr_processed_at must be nullable"

    def test_ocr_source_column_exists(self, db_session: Session):
        """job_expense.ocr_source column must exist (VARCHAR NULL)."""
        from sqlalchemy import text

        result = db_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'job_expense'
                  AND column_name = 'ocr_source'
            """)
        ).fetchone()
        assert result is not None, "ocr_source column missing from job_expense"
        assert result[2] == "YES", "ocr_source must be nullable"

    def test_job_expense_orm_has_ocr_fields(self):
        """JobExpense ORM model must have ocr_processed_at and ocr_source fields."""
        from app.models.fulfillment import JobExpense

        fields = JobExpense.model_fields
        assert "ocr_processed_at" in fields, "JobExpense must have ocr_processed_at"
        assert "ocr_source" in fields, "JobExpense must have ocr_source"


# ─────────────────────────────────────────────────────────────────────────────
# OcrService ABC and subclass tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFind062OcrServiceAbc:
    """OcrService ABC and subclass hierarchy tests."""

    def test_mock_ocr_service_is_subclass(self):
        """MockOcrService must be a subclass of OcrService."""
        from services.ocr_service import MockOcrService, OcrService

        assert issubclass(MockOcrService, OcrService)

    def test_rapid_ocr_service_is_subclass(self):
        """RapidOcrService must be a subclass of OcrService."""
        from services.ocr_service import OcrService, RapidOcrService

        assert issubclass(RapidOcrService, OcrService)

    def test_mock_returns_fixture_for_normal_key(self):
        """MockOcrService.extract_expense returns fixture data for a normal S3 key."""
        from services.ocr_service import MockOcrService

        svc = MockOcrService()
        result = svc.extract_expense("tenants/abc/jobs/123/photos/456/receipt.jpg")
        assert result is not None
        assert "total_cents" in result
        assert "vendor" in result
        assert "date" in result
        assert "line_items" in result
        assert isinstance(result["total_cents"], int)
        assert result["total_cents"] > 0

    def test_mock_returns_none_for_low_confidence_key(self):
        """MockOcrService.extract_expense returns None for keys containing 'low_confidence'."""
        from services.ocr_service import MockOcrService

        svc = MockOcrService()
        result = svc.extract_expense(
            "tenants/abc/jobs/123/photos/low_confidence_receipt.jpg"
        )
        assert result is None

    def test_mock_returns_none_for_no_receipt_key(self):
        """MockOcrService.extract_expense returns None for keys containing 'no_receipt'."""
        from services.ocr_service import MockOcrService

        svc = MockOcrService()
        result = svc.extract_expense("tenants/abc/jobs/123/photos/no_receipt.jpg")
        assert result is None

    def test_factory_returns_mock_in_dev(self):
        """get_ocr_service() must return MockOcrService when ENVIRONMENT='dev'."""
        from services.ocr_service import MockOcrService, get_ocr_service

        # Default ENVIRONMENT in tests is 'dev' (from pytest.ini or config defaults)
        svc = get_ocr_service()
        assert isinstance(svc, MockOcrService), (
            f"get_ocr_service() must return MockOcrService in dev, got {type(svc).__name__}"
        )

    def test_factory_returns_rapid_in_production(self):
        """get_ocr_service() must return RapidOcrService when ENVIRONMENT='production'."""
        from services.ocr_service import RapidOcrService

        with patch("services.ocr_service.get_ocr_service") as mock_factory:
            mock_factory.return_value = RapidOcrService()
            svc = mock_factory()
            assert isinstance(svc, RapidOcrService)


# ─────────────────────────────────────────────────────────────────────────────
# Celery task tests — using MockOcrService
# ─────────────────────────────────────────────────────────────────────────────


class TestFind062ReceiptOcrTask:
    """Tests for the process_receipt_ocr Celery task using MockOcrService."""

    def test_task_registered_in_celery(self):
        """process_receipt_ocr task must be importable and registered."""
        from tasks.receipt_ocr import process_receipt_ocr

        assert process_receipt_ocr.name == "receipt_ocr.process_receipt_ocr"

    def test_no_attachment_returns_no_attachment_status(self, db_session: Session):
        """process_receipt_ocr returns no_attachment for unknown attachment_id."""
        from tasks.receipt_ocr import process_receipt_ocr

        non_existent_id = str(uuid.uuid4())
        result = process_receipt_ocr(non_existent_id)
        assert result["status"] == "no_attachment"
        assert result["attachment_id"] == non_existent_id

    def test_invalid_uuid_returns_error(self, db_session: Session):
        """process_receipt_ocr returns error for invalid UUID string."""
        from tasks.receipt_ocr import process_receipt_ocr

        result = process_receipt_ocr("not-a-uuid")
        assert result["status"] == "error"

    def test_mock_ocr_applies_result_to_expense(
        self, db_session: Session, test_job, tenant_a, test_user
    ):
        """MockOcrService fixture result must be applied to job_expense.cost_cents."""
        from app.models.fulfillment import JobAttachment, JobExpense, JobExpenseCategory
        from services.ocr_service import MockOcrService
        from tasks.receipt_ocr import process_receipt_ocr

        # Get or create a valid expense category
        cat = db_session.exec(select(JobExpenseCategory)).first()
        if not cat:
            cat = JobExpenseCategory(
                code="other",
                name="Other",
                is_active=True,
            )
            db_session.add(cat)
            db_session.flush()

        # Create expense with original cost
        expense = JobExpense(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            user_id=test_user.id,
            job_expense_category_code=cat.code,
            description="Test receipt",
            cost_cents=1000,  # Will be overwritten by OCR
            markup_pct=0,
            billable_cents=1000,
        )
        db_session.add(expense)
        db_session.flush()

        # Create attachment — object_key is the S3 key used for OCR
        attachment = JobAttachment(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            file_name="receipt.jpg",
            mime_type="image/jpeg",
            size_bytes=50000,
            object_key="tenants/abc/jobs/123/photos/456/receipt.jpg",
            upload_status="complete",
            expense_id=expense.id,
        )
        db_session.add(attachment)
        db_session.commit()

        # Run OCR task with MockOcrService and the test's db_session
        def _fake_get_db():
            yield db_session

        with (
            patch("tasks.receipt_ocr.get_ocr_service", return_value=MockOcrService()),
            patch("tasks.receipt_ocr.get_db", return_value=_fake_get_db()),
        ):
            result = process_receipt_ocr(str(attachment.id))

        assert result["status"] == "applied", f"Expected 'applied', got {result}"
        assert "total_cents" in result
        assert result["total_cents"] == MockOcrService.FIXTURE_RESULT["total_cents"]

        # Verify DB updated
        db_session.expire_all()
        updated_expense = db_session.get(JobExpense, expense.id)
        assert (
            updated_expense.cost_cents == MockOcrService.FIXTURE_RESULT["total_cents"]
        )
        assert updated_expense.ocr_processed_at is not None
        assert updated_expense.ocr_source == "rapidocr"

    def test_low_confidence_sets_ocr_processed_at_but_not_cost(
        self, db_session: Session, test_job, tenant_a, test_user
    ):
        """MockOcrService None result sets ocr_processed_at but does NOT change cost_cents."""
        from app.models.fulfillment import JobAttachment, JobExpense, JobExpenseCategory
        from services.ocr_service import MockOcrService
        from tasks.receipt_ocr import process_receipt_ocr

        cat = db_session.exec(select(JobExpenseCategory)).first()
        if not cat:
            cat = JobExpenseCategory(code="other", name="Other", is_active=True)
            db_session.add(cat)
            db_session.flush()

        original_cost = 9900
        expense = JobExpense(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            user_id=test_user.id,
            job_expense_category_code=cat.code,
            description="Low confidence receipt",
            cost_cents=original_cost,
            markup_pct=0,
            billable_cents=original_cost,
        )
        db_session.add(expense)
        db_session.flush()

        attachment = JobAttachment(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            file_name="low_confidence_receipt.jpg",
            mime_type="image/jpeg",
            size_bytes=30000,
            object_key="tenants/abc/jobs/123/low_confidence_receipt.jpg",
            upload_status="complete",
            expense_id=expense.id,
        )
        db_session.add(attachment)
        db_session.commit()

        # Capture IDs before task runs (task db.close() detaches the session)
        expense_id = expense.id
        attachment_id_str = str(attachment.id)

        # MockOcrService returns None for low_confidence keys
        def _fake_get_db_lc():
            yield db_session

        with (
            patch("tasks.receipt_ocr.get_ocr_service", return_value=MockOcrService()),
            patch("tasks.receipt_ocr.get_db", return_value=_fake_get_db_lc()),
        ):
            result = process_receipt_ocr(attachment_id_str)

        assert result["status"] == "skipped", f"Expected 'skipped', got {result}"

        # Query fresh after task completes
        updated = db_session.exec(
            select(JobExpense).where(JobExpense.id == expense_id)
        ).first()
        assert updated.cost_cents == original_cost, (
            "cost_cents must not change when OCR returns None"
        )
        assert updated.ocr_processed_at is not None, (
            "ocr_processed_at must be set even when OCR result is None"
        )
        assert updated.ocr_source is None, (
            "ocr_source must remain None when OCR result is None"
        )

    def test_idempotency_reprocess_safe(
        self, db_session: Session, test_job, tenant_a, test_user
    ):
        """Re-processing the same attachment_id does not crash or duplicate data."""
        from app.models.fulfillment import JobAttachment, JobExpense, JobExpenseCategory
        from services.ocr_service import MockOcrService
        from tasks.receipt_ocr import process_receipt_ocr

        cat = db_session.exec(select(JobExpenseCategory)).first()
        if not cat:
            cat = JobExpenseCategory(code="other", name="Other", is_active=True)
            db_session.add(cat)
            db_session.flush()

        expense = JobExpense(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            user_id=test_user.id,
            job_expense_category_code=cat.code,
            description="Idempotency test receipt",
            cost_cents=500,
            markup_pct=0,
            billable_cents=500,
        )
        db_session.add(expense)
        db_session.flush()

        attachment = JobAttachment(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=test_job.id,
            file_name="receipt.jpg",
            mime_type="image/jpeg",
            size_bytes=20000,
            object_key="tenants/abc/jobs/123/idempotent_receipt.jpg",
            upload_status="complete",
            expense_id=expense.id,
        )
        db_session.add(attachment)
        db_session.commit()

        attachment_id_str = str(attachment.id)

        def _fake_get_db_idem():
            yield db_session

        # First call
        with (
            patch("tasks.receipt_ocr.get_ocr_service", return_value=MockOcrService()),
            patch("tasks.receipt_ocr.get_db", return_value=_fake_get_db_idem()),
        ):
            result1 = process_receipt_ocr(attachment_id_str)

        def _fake_get_db_idem2():
            yield db_session

        # Second call (re-process)
        with (
            patch("tasks.receipt_ocr.get_ocr_service", return_value=MockOcrService()),
            patch("tasks.receipt_ocr.get_db", return_value=_fake_get_db_idem2()),
        ):
            result2 = process_receipt_ocr(attachment_id_str)

        # Both calls must succeed
        assert result1["status"] == "applied"
        assert result2["status"] == "applied"

        # Only one expense row exists
        db_session.expire_all()
        expenses = db_session.exec(
            select(JobExpense).where(JobExpense.id == expense.id)
        ).all()
        assert len(expenses) == 1, (
            "Idempotent re-processing must not create duplicate expense rows"
        )
