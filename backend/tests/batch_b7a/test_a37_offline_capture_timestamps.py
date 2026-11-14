"""
tests/batch_b7a/test_a37_offline_capture_timestamps.py

B7a/A37: Offline-Capable Operations API Contract

Test focus cases:
  1. client_capture_at field present and nullable on JobTimeEntry
  2. client_capture_at field present and nullable on JobExpense
  3. client_capture_at field present and nullable on JobAttachment (+ file_hash)
  4. client_capture_at field present and nullable on ChangeOrder
  5. client_capture_at field present and nullable on JobNotes
  6. client_capture_at = NULL for online-created rows (correct semantic default)
  7. client_capture_at can be set to a timezone-aware datetime (offline row)
  8. file_hash can be set on JobAttachment (§F.3 natural-key dedup)
  9. file_hash is NULL for legacy rows (no hash required at insert)
"""

import uuid
from datetime import UTC, datetime

from sqlmodel import select

from app.models.fulfillment import (
    JobAttachment,
    JobExpense,
    JobNotes,
    JobTimeEntry,
)
from app.models.quoting import ChangeOrder

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

OFFLINE_TS = datetime(2026, 4, 28, 14, 23, 0, tzinfo=UTC)


def _make_job(db_session, tenant_id):
    """Create a minimal job row for FK satisfaction."""
    from app.models.crm import Customer, Site
    from app.models.fulfillment import Job, JobStatus

    job_status = db_session.exec(
        select(JobStatus).where(JobStatus.code == "draft")
    ).first()
    if not job_status:
        job_status = JobStatus(
            id=uuid.uuid4(),
            code="draft",
            name="Draft",
            is_active=True,
        )
        db_session.add(job_status)
        db_session.flush()

    customer = db_session.exec(
        select(Customer).where(Customer.tenant_id == tenant_id)
    ).first()
    if not customer:
        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            type="person",
            display_name=f"Test Customer {uuid.uuid4().hex[:6]}",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()

    site = db_session.exec(select(Site).where(Site.tenant_id == tenant_id)).first()
    if not site:
        site = Site(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            customer_id=customer.id,
            site_name="Test Site",
            is_active=True,
        )
        db_session.add(site)
        db_session.flush()

    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_id=site.id,
        status_id=job_status.id,
        is_active=True,
    )
    db_session.add(job)
    db_session.flush()
    return job


def _make_expense_category(db_session):
    from app.models.fulfillment import JobExpenseCategory

    cat = db_session.exec(
        select(JobExpenseCategory).where(JobExpenseCategory.code == "materials")
    ).first()
    if not cat:
        cat = JobExpenseCategory(
            code="materials",
            name="Materials",
            is_active=True,
        )
        db_session.add(cat)
        db_session.flush()
    return cat


# ─────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────


class TestA37ClientCaptureAtJobTimeEntry:
    """Focus cases 1, 6, 7 — JobTimeEntry."""

    def test_field_exists_and_is_nullable(self):
        """client_capture_at field declared on JobTimeEntry, nullable=True."""
        field = JobTimeEntry.model_fields.get("client_capture_at")
        assert field is not None, "client_capture_at field missing from JobTimeEntry"
        assert field.default is None or field.is_required() is False

    def test_online_row_has_null_client_capture_at(
        self, db_session, test_tenant, test_user
    ):
        """Online-created rows have client_capture_at = NULL (correct semantic)."""
        job = _make_job(db_session, test_tenant.id)
        entry = JobTimeEntry(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,
            started_at=datetime.now(UTC),
            hourly_rate_cents=5000,
            total_cost_cents=5000,
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        assert entry.client_capture_at is None, (
            "Online row should have NULL client_capture_at"
        )

    def test_offline_row_stores_client_capture_at(
        self, db_session, test_tenant, test_user
    ):
        """Offline-captured rows can store a timezone-aware datetime."""
        job = _make_job(db_session, test_tenant.id)
        entry = JobTimeEntry(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,
            started_at=datetime.now(UTC),
            hourly_rate_cents=5000,
            total_cost_cents=5000,
            client_capture_at=OFFLINE_TS,
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        assert entry.client_capture_at is not None
        assert entry.client_capture_at.replace(microsecond=0) == OFFLINE_TS.replace(
            microsecond=0
        )


class TestA37ClientCaptureAtJobExpense:
    """Focus case 2 — JobExpense."""

    def test_field_exists_and_is_nullable(self):
        """client_capture_at field declared on JobExpense, nullable=True."""
        field = JobExpense.model_fields.get("client_capture_at")
        assert field is not None, "client_capture_at field missing from JobExpense"

    def test_online_row_has_null_client_capture_at(
        self, db_session, test_tenant, test_user
    ):
        """Online-created expense has client_capture_at = NULL."""
        job = _make_job(db_session, test_tenant.id)
        cat = _make_expense_category(db_session)
        expense = JobExpense(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,  # FIND-121: user_id required
            job_expense_category_code=cat.code,
            description="Test expense",
            incurred_at=datetime.now(UTC),
            cost_cents=1000,
            markup_pct=0.15,
            billable_cents=1150,
        )
        db_session.add(expense)
        db_session.commit()
        db_session.refresh(expense)

        assert expense.client_capture_at is None

    def test_offline_row_stores_client_capture_at(
        self, db_session, test_tenant, test_user
    ):
        """Offline expense can store client_capture_at."""
        job = _make_job(db_session, test_tenant.id)
        cat = _make_expense_category(db_session)
        expense = JobExpense(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,  # FIND-121: user_id required
            job_expense_category_code=cat.code,
            description="Offline expense",
            incurred_at=datetime.now(UTC),
            cost_cents=2500,
            markup_pct=0.15,
            billable_cents=2875,
            client_capture_at=OFFLINE_TS,
        )
        db_session.add(expense)
        db_session.commit()
        db_session.refresh(expense)

        assert expense.client_capture_at is not None
        assert expense.client_capture_at.replace(microsecond=0) == OFFLINE_TS.replace(
            microsecond=0
        )


class TestA37ClientCaptureAtJobAttachment:
    """Focus cases 3, 8, 9 — JobAttachment (+ file_hash)."""

    def test_client_capture_at_field_exists(self):
        """client_capture_at field declared on JobAttachment."""
        field = JobAttachment.model_fields.get("client_capture_at")
        assert field is not None, "client_capture_at field missing from JobAttachment"

    def test_file_hash_field_exists(self):
        """file_hash field declared on JobAttachment (§F.3 natural-key dedup)."""
        field = JobAttachment.model_fields.get("file_hash")
        assert field is not None, "file_hash field missing from JobAttachment"

    def test_legacy_row_has_null_fields(self, db_session, test_tenant):
        """Legacy/online rows have both file_hash=NULL and client_capture_at=NULL."""
        job = _make_job(db_session, test_tenant.id)
        attachment = JobAttachment(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            file_name="test.jpg",
            mime_type="image/jpeg",
            size_bytes=1024,
            object_key="uploads/test.jpg",
        )
        db_session.add(attachment)
        db_session.commit()
        db_session.refresh(attachment)

        assert attachment.client_capture_at is None
        assert attachment.file_hash is None

    def test_offline_photo_stores_both_fields(self, db_session, test_tenant):
        """Offline photo can store client_capture_at and file_hash."""
        job = _make_job(db_session, test_tenant.id)
        test_hash = "a" * 64  # SHA-256 placeholder
        attachment = JobAttachment(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            file_name="photo.jpg",
            mime_type="image/jpeg",
            size_bytes=20480,
            object_key="uploads/photo.jpg",
            client_capture_at=OFFLINE_TS,
            file_hash=test_hash,
        )
        db_session.add(attachment)
        db_session.commit()
        db_session.refresh(attachment)

        assert attachment.client_capture_at is not None
        assert attachment.file_hash == test_hash


class TestA37ClientCaptureAtChangeOrder:
    """Focus case 4 — ChangeOrder."""

    def test_field_exists_and_is_nullable(self):
        """client_capture_at field declared on ChangeOrder, nullable=True."""
        field = ChangeOrder.model_fields.get("client_capture_at")
        assert field is not None, "client_capture_at field missing from ChangeOrder"

    def test_online_change_order_has_null(self, db_session, test_tenant):
        """Online change orders have client_capture_at = NULL."""
        job = _make_job(db_session, test_tenant.id)
        co = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            description="Add outlet",
            subtotal_cents=15000,
            tax_cents=1050,
            total_cents=16050,
        )
        db_session.add(co)
        db_session.commit()
        db_session.refresh(co)

        assert co.client_capture_at is None

    def test_offline_change_order_stores_capture_at(self, db_session, test_tenant):
        """Offline change orders can store client_capture_at."""
        job = _make_job(db_session, test_tenant.id)
        co = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            description="Panel upgrade — offline capture",
            subtotal_cents=50000,
            tax_cents=3500,
            total_cents=53500,
            client_capture_at=OFFLINE_TS,
        )
        db_session.add(co)
        db_session.commit()
        db_session.refresh(co)

        assert co.client_capture_at is not None
        assert co.client_capture_at.replace(microsecond=0) == OFFLINE_TS.replace(
            microsecond=0
        )


class TestA37ClientCaptureAtJobNotes:
    """Focus case 5 — JobNotes."""

    def test_field_exists_and_is_nullable(self):
        """client_capture_at field declared on JobNotes, nullable=True."""
        field = JobNotes.model_fields.get("client_capture_at")
        assert field is not None, "client_capture_at field missing from JobNotes"

    def test_online_note_has_null_client_capture_at(self, db_session, test_tenant):
        """Online notes have client_capture_at = NULL."""
        job = _make_job(db_session, test_tenant.id)
        note = JobNotes(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            notes="Tech arrived on time.",
            customer_visible=False,
        )
        db_session.add(note)
        db_session.commit()
        db_session.refresh(note)

        assert note.client_capture_at is None

    def test_offline_note_stores_client_capture_at(self, db_session, test_tenant):
        """Offline notes can store client_capture_at."""
        job = _make_job(db_session, test_tenant.id)
        note = JobNotes(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            notes="Discovered faulty breaker — offline note.",
            customer_visible=True,
            client_capture_at=OFFLINE_TS,
        )
        db_session.add(note)
        db_session.commit()
        db_session.refresh(note)

        assert note.client_capture_at is not None
        assert note.client_capture_at.replace(microsecond=0) == OFFLINE_TS.replace(
            microsecond=0
        )
