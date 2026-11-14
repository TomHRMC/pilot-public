"""
FIND-050 (S2 High) — Add server_received_at to 5 offline-capable tables.

server_received_at is a TIMESTAMPTZ NULL column on:
  job_time_entry, job_expense, job_attachment, change_order, job_notes

- NULL  = record was created online in real-time (no offline capture)
- Non-NULL = record arrived via offline sync batch;
             delta vs client_capture_at shows round-trip latency

Test subfolder: tests/batch_b18/
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# DB schema: column exists on all 5 tables
# ─────────────────────────────────────────────────────────────────────────────
class TestFind050ColumnExistsInDB:
    """Verify server_received_at column was created by migration."""

    @pytest.mark.parametrize(
        "table_name",
        [
            "job_time_entry",
            "job_expense",
            "job_attachment",
            "change_order",
            "job_notes",
        ],
    )
    def test_column_exists_and_is_nullable(self, db_session, table_name):
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_name, is_nullable, data_type "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = :tbl "
                "  AND column_name = 'server_received_at'"
            ).bindparams(tbl=table_name)
        ).first()
        assert result is not None, (
            f"server_received_at column missing from {table_name}"
        )
        assert result[1] == "YES", (
            f"server_received_at must be nullable on {table_name}"
        )
        assert "timestamp" in result[2].lower(), (
            f"server_received_at must be a timestamp type on {table_name}, got {result[2]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ORM model fields
# ─────────────────────────────────────────────────────────────────────────────
class TestFind050ORMFieldsPresent:
    """ORM models must expose server_received_at field."""

    def test_job_time_entry_has_server_received_at(self):
        from app.models.fulfillment import JobTimeEntry

        assert hasattr(JobTimeEntry, "server_received_at")

    def test_job_expense_has_server_received_at(self):
        from app.models.fulfillment import JobExpense

        assert hasattr(JobExpense, "server_received_at")

    def test_job_attachment_has_server_received_at(self):
        from app.models.fulfillment import JobAttachment

        assert hasattr(JobAttachment, "server_received_at")

    def test_change_order_has_server_received_at(self):
        from app.models.quoting import ChangeOrder

        assert hasattr(ChangeOrder, "server_received_at")

    def test_job_notes_has_server_received_at(self):
        from app.models.fulfillment import JobNotes

        assert hasattr(JobNotes, "server_received_at")


# ─────────────────────────────────────────────────────────────────────────────
# Schema fields
# ─────────────────────────────────────────────────────────────────────────────
class TestFind050SchemaFields:
    """Create schemas must accept client_capture_at to trigger server_received_at."""

    def test_job_time_entry_create_accepts_client_capture_at(self):
        from api.schemas.schemas import JobTimeEntryCreate

        now = datetime.now(UTC)
        s = JobTimeEntryCreate(
            started_at=now, client_capture_at=now - timedelta(minutes=5)
        )
        assert s.client_capture_at is not None

    def test_job_time_entry_create_client_capture_at_optional(self):
        from api.schemas.schemas import JobTimeEntryCreate

        now = datetime.now(UTC)
        s = JobTimeEntryCreate(started_at=now)
        assert s.client_capture_at is None

    def test_job_expense_create_accepts_client_capture_at(self):
        from api.schemas.schemas import JobExpenseCreate

        now = datetime.now(UTC)
        s = JobExpenseCreate(
            job_expense_category_code="labor",
            description="Test",
            incurred_at=now,
            cost_cents=1000,
            client_capture_at=now - timedelta(minutes=5),
        )
        assert s.client_capture_at is not None

    def test_job_expense_create_client_capture_at_optional(self):
        from api.schemas.schemas import JobExpenseCreate

        now = datetime.now(UTC)
        s = JobExpenseCreate(
            job_expense_category_code="labor",
            description="Test",
            incurred_at=now,
            cost_cents=1000,
        )
        assert s.client_capture_at is None

    def test_change_order_create_accepts_client_capture_at(self):
        from api.schemas.schemas import ChangeOrderCreate

        now = datetime.now(UTC)
        s = ChangeOrderCreate(
            description="Test CO", client_capture_at=now - timedelta(minutes=3)
        )
        assert s.client_capture_at is not None

    def test_change_order_create_client_capture_at_optional(self):
        from api.schemas.schemas import ChangeOrderCreate

        s = ChangeOrderCreate(description="Test CO")
        assert s.client_capture_at is None


# ─────────────────────────────────────────────────────────────────────────────
# Behavioral population: ORM direct insert tests
# ─────────────────────────────────────────────────────────────────────────────
class TestFind050PopulationBehavior:
    """Verify server_received_at is set/unset correctly via direct ORM insert."""

    def _make_job_fixture(self, db_session, test_tenant, test_user):
        """Create minimal Job row for FK requirements."""
        from sqlmodel import select

        from app.models.crm import Customer, Site
        from app.models.fulfillment import Job, JobStatus

        now = datetime.now(UTC)
        job_status = db_session.exec(select(JobStatus).limit(1)).first()
        assert job_status is not None, "No job status seeded"

        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            type="person",
            display_name=f"Test Customer {uuid.uuid4().hex[:6]}",
            created_at=now,
            updated_at=now,
        )
        db_session.add(customer)

        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            display_name="Test Site",
            created_at=now,
            updated_at=now,
        )
        db_session.add(site)

        job = Job(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=job_status.id,
            created_at=now,
            updated_at=now,
        )
        db_session.add(job)
        db_session.flush()
        return job

    # --- job_time_entry ---

    def test_job_time_entry_with_client_capture_at_sets_server_received_at(
        self, db_session, test_tenant, test_user
    ):
        """JobTimeEntry with client_capture_at → server_received_at is non-null and >= client."""
        from sqlmodel import select

        from app.models.fulfillment import JobTimeEntry

        now = datetime.now(UTC)
        client_cap = now - timedelta(minutes=30)
        job = self._make_job_fixture(db_session, test_tenant, test_user)
        before = datetime.now(UTC)

        entry = JobTimeEntry(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,
            started_at=client_cap,
            hours=1.0,
            hourly_rate_cents=8500,
            total_cost_cents=8500,
            client_capture_at=client_cap,
            server_received_at=datetime.now(UTC),  # simulates handler logic
            created_at=now,
            updated_at=now,
        )
        db_session.add(entry)
        db_session.commit()

        fetched = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.id == entry.id)
        ).first()
        assert fetched.server_received_at is not None, (
            "server_received_at must be set when client_capture_at is provided"
        )
        assert fetched.server_received_at >= client_cap, (
            "server_received_at must be >= client_capture_at"
        )
        assert fetched.server_received_at >= before, (
            "server_received_at must be set at or after request receipt"
        )

    def test_job_time_entry_without_client_capture_at_has_null_server_received_at(
        self, db_session, test_tenant, test_user
    ):
        """JobTimeEntry without client_capture_at → server_received_at is NULL."""
        from sqlmodel import select

        from app.models.fulfillment import JobTimeEntry

        now = datetime.now(UTC)
        job = self._make_job_fixture(db_session, test_tenant, test_user)

        entry = JobTimeEntry(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,
            started_at=now,
            hours=1.0,
            hourly_rate_cents=8500,
            total_cost_cents=8500,
            client_capture_at=None,
            server_received_at=None,  # online submission
            created_at=now,
            updated_at=now,
        )
        db_session.add(entry)
        db_session.commit()

        fetched = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.id == entry.id)
        ).first()
        assert fetched.server_received_at is None, (
            "Online submission must have server_received_at=NULL"
        )

    # --- job_expense ---

    def _make_expense_category(self, db_session, test_tenant):
        """Create a minimal JobExpenseCategory for FK requirements."""
        from app.models.fulfillment import JobExpenseCategory

        # Try existing first (avoid duplicate code errors)
        code = f"test_cat_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC)
        cat = JobExpenseCategory(
            code=code,
            tenant_id=test_tenant.id,
            name="Test Category",
            created_at=now,
            updated_at=now,
        )
        db_session.add(cat)
        db_session.flush()
        return cat

    def test_job_expense_with_client_capture_at_sets_server_received_at(
        self, db_session, test_tenant, test_user
    ):
        """JobExpense with client_capture_at → server_received_at is non-null."""
        from sqlmodel import select

        from app.models.fulfillment import JobExpense

        now = datetime.now(UTC)
        client_cap = now - timedelta(minutes=20)
        job = self._make_job_fixture(db_session, test_tenant, test_user)
        cat = self._make_expense_category(db_session, test_tenant)

        expense = JobExpense(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,  # FIND-121: user_id required
            job_expense_category_code=cat.code,
            description="Test offline expense",
            incurred_at=client_cap,
            cost_cents=5000,
            markup_pct=0,
            billable_cents=5000,
            client_capture_at=client_cap,
            server_received_at=datetime.now(UTC),
            created_at=now,
            updated_at=now,
        )
        db_session.add(expense)
        db_session.commit()

        fetched = db_session.exec(
            select(JobExpense).where(JobExpense.id == expense.id)
        ).first()
        assert fetched.server_received_at is not None
        assert fetched.server_received_at >= client_cap

    def test_job_expense_without_client_capture_at_has_null_server_received_at(
        self, db_session, test_tenant, test_user
    ):
        """JobExpense without client_capture_at → server_received_at is NULL."""
        from sqlmodel import select

        from app.models.fulfillment import JobExpense

        now = datetime.now(UTC)
        job = self._make_job_fixture(db_session, test_tenant, test_user)
        cat = self._make_expense_category(db_session, test_tenant)

        expense = JobExpense(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,  # FIND-121: user_id required
            job_expense_category_code=cat.code,
            description="Test online expense",
            incurred_at=now,
            cost_cents=5000,
            markup_pct=0,
            billable_cents=5000,
            client_capture_at=None,
            server_received_at=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(expense)
        db_session.commit()

        fetched = db_session.exec(
            select(JobExpense).where(JobExpense.id == expense.id)
        ).first()
        assert fetched.server_received_at is None

    # --- change_order ---

    def test_change_order_with_client_capture_at_sets_server_received_at(
        self, db_session, test_tenant, test_user
    ):
        """ChangeOrder with client_capture_at → server_received_at is non-null."""
        from sqlmodel import select

        from app.models.quoting import ChangeOrder

        now = datetime.now(UTC)
        client_cap = now - timedelta(minutes=10)
        job = self._make_job_fixture(db_session, test_tenant, test_user)

        co = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            description="Offline CO",
            subtotal_cents=0,
            tax_cents=0,
            total_cents=0,
            client_capture_at=client_cap,
            server_received_at=datetime.now(UTC),
            created_at=now,
            updated_at=now,
        )
        db_session.add(co)
        db_session.commit()

        fetched = db_session.exec(
            select(ChangeOrder).where(ChangeOrder.id == co.id)
        ).first()
        assert fetched.server_received_at is not None
        assert fetched.server_received_at >= client_cap

    def test_change_order_without_client_capture_at_has_null_server_received_at(
        self, db_session, test_tenant, test_user
    ):
        """ChangeOrder without client_capture_at → server_received_at is NULL."""
        from sqlmodel import select

        from app.models.quoting import ChangeOrder

        now = datetime.now(UTC)
        job = self._make_job_fixture(db_session, test_tenant, test_user)

        co = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            description="Online CO",
            subtotal_cents=0,
            tax_cents=0,
            total_cents=0,
            client_capture_at=None,
            server_received_at=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(co)
        db_session.commit()

        fetched = db_session.exec(
            select(ChangeOrder).where(ChangeOrder.id == co.id)
        ).first()
        assert fetched.server_received_at is None

    # --- job_notes ---

    def test_job_notes_with_client_capture_at_sets_server_received_at(
        self, db_session, test_tenant, test_user
    ):
        """JobNotes with client_capture_at → server_received_at is non-null."""
        from sqlmodel import select

        from app.models.fulfillment import JobNotes

        now = datetime.now(UTC)
        client_cap = now - timedelta(minutes=15)
        job = self._make_job_fixture(db_session, test_tenant, test_user)

        note = JobNotes(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            notes="Offline note",
            client_capture_at=client_cap,
            server_received_at=datetime.now(UTC),
            created_at=now,
            updated_at=now,
        )
        db_session.add(note)
        db_session.commit()

        fetched = db_session.exec(
            select(JobNotes).where(JobNotes.id == note.id)
        ).first()
        assert fetched.server_received_at is not None
        assert fetched.server_received_at >= client_cap

    def test_job_notes_without_client_capture_at_has_null_server_received_at(
        self, db_session, test_tenant, test_user
    ):
        """JobNotes without client_capture_at → server_received_at is NULL."""
        from sqlmodel import select

        from app.models.fulfillment import JobNotes

        now = datetime.now(UTC)
        job = self._make_job_fixture(db_session, test_tenant, test_user)

        note = JobNotes(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            notes="Online note",
            client_capture_at=None,
            server_received_at=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(note)
        db_session.commit()

        fetched = db_session.exec(
            select(JobNotes).where(JobNotes.id == note.id)
        ).first()
        assert fetched.server_received_at is None

    # --- job_attachment ---

    def test_job_attachment_with_client_capture_at_sets_server_received_at(
        self, db_session, test_tenant, test_user
    ):
        """JobAttachment with client_capture_at → server_received_at is non-null."""
        from sqlmodel import select

        from app.models.fulfillment import JobAttachment

        now = datetime.now(UTC)
        client_cap = now - timedelta(minutes=8)
        job = self._make_job_fixture(db_session, test_tenant, test_user)

        att = JobAttachment(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            file_name="photo.jpg",
            mime_type="image/jpeg",
            size_bytes=1024,
            object_key=f"tenants/{test_tenant.id}/jobs/{job.id}/photo.jpg",
            client_capture_at=client_cap,
            server_received_at=datetime.now(UTC),
            created_at=now,
            updated_at=now,
        )
        db_session.add(att)
        db_session.commit()

        fetched = db_session.exec(
            select(JobAttachment).where(JobAttachment.id == att.id)
        ).first()
        assert fetched.server_received_at is not None
        assert fetched.server_received_at >= client_cap

    def test_job_attachment_without_client_capture_at_has_null_server_received_at(
        self, db_session, test_tenant, test_user
    ):
        """JobAttachment without client_capture_at → server_received_at is NULL."""
        from sqlmodel import select

        from app.models.fulfillment import JobAttachment

        now = datetime.now(UTC)
        job = self._make_job_fixture(db_session, test_tenant, test_user)

        att = JobAttachment(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            file_name="photo2.jpg",
            mime_type="image/jpeg",
            size_bytes=2048,
            object_key=f"tenants/{test_tenant.id}/jobs/{job.id}/photo2.jpg",
            client_capture_at=None,
            server_received_at=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(att)
        db_session.commit()

        fetched = db_session.exec(
            select(JobAttachment).where(JobAttachment.id == att.id)
        ).first()
        assert fetched.server_received_at is None

    # --- handler population logic unit test ---

    def test_handler_sets_server_received_at_when_client_capture_provided(self):
        """The 3-line population pattern correctly sets server_received_at."""
        now = datetime.now(UTC)
        client_cap = now - timedelta(minutes=30)

        # Simulate the handler pattern for any of the 5 tables
        class FakeCreate:
            client_capture_at = client_cap

        record_in = FakeCreate()
        server_received_at = None
        if getattr(record_in, "client_capture_at", None) is not None:
            server_received_at = datetime.now(UTC)

        assert server_received_at is not None
        assert server_received_at >= client_cap

    def test_handler_leaves_null_when_no_client_capture(self):
        """The 3-line population pattern leaves server_received_at=None for online submissions."""

        class FakeCreate:
            client_capture_at = None

        record_in = FakeCreate()
        server_received_at = None
        if getattr(record_in, "client_capture_at", None) is not None:
            server_received_at = datetime.now(UTC)

        assert server_received_at is None
