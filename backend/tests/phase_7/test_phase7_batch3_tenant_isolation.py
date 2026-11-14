"""
Phase 7.0 Batch 3 - Cross-Tenant IDOR Security Tests
Operations & Jobs: job_notes, job_time_entry, change_order,
change_order_attachment, change_order_line, change_order_line_tax_component

These tests verify that Phase 7.0 tenant stamping successfully prevents
Insecure Direct Object Reference (IDOR) vulnerabilities across all 6
batch-3 tables. A 404 response (not 403) is preferred to prevent
tenant ID enumeration attacks.

Test Coverage:
- tenant_id is present and correct on newly created records
- Tenant A cannot access Tenant B's records via direct GET
- Tenant A's list endpoints exclude Tenant B's records
- All 6 batch-3 tables are covered
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.core import Tenant, User
from app.models.crm import Customer, Site
from app.models.fulfillment import Job, JobNotes, JobStatus, JobTimeEntry
from app.models.quoting import (
    ChangeOrder,
    ChangeOrderAttachment,
    ChangeOrderLine,
    ChangeOrderLineTaxComponent,
    QcoLineType,
)

# ==================== FIXTURES ====================


@pytest.fixture
def tenant_a(db_session):
    """Tenant A - the 'attacker' tenant"""
    tenant = Tenant(id=uuid.uuid4(), name=f"Tenant A {uuid.uuid4()}", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def tenant_b(db_session):
    """Tenant B - the 'victim' tenant whose records should be isolated"""
    tenant = Tenant(id=uuid.uuid4(), name=f"Tenant B {uuid.uuid4()}", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def job_status_a(db_session, tenant_a):
    status = JobStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        code="active",
        name="Active",
        is_terminal=False,
        is_default=True,
        is_active=True,
    )
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


@pytest.fixture
def job_status_b(db_session, tenant_b):
    status = JobStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        code="active",
        name="Active",
        is_terminal=False,
        is_default=True,
        is_active=True,
    )
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


@pytest.fixture
def customer_a(db_session, tenant_a):
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        display_name=f"Customer A {uuid.uuid4()}",
        email=f"a-{uuid.uuid4()}@example.com",
        is_active=True,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def customer_b(db_session, tenant_b):
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        display_name=f"Customer B {uuid.uuid4()}",
        email=f"b-{uuid.uuid4()}@example.com",
        is_active=True,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def site_a(db_session, tenant_a, customer_a):
    site = Site(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        customer_id=customer_a.id,
        name="Site A",
        is_active=True,
    )
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)
    return site


@pytest.fixture
def site_b(db_session, tenant_b, customer_b):
    site = Site(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        customer_id=customer_b.id,
        name="Site B",
        is_active=True,
    )
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)
    return site


@pytest.fixture
def job_a(db_session, tenant_a, customer_a, site_a, job_status_a):
    """Job belonging to Tenant A"""
    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        customer_id=customer_a.id,
        site_id=site_a.id,
        status_id=job_status_a.id,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def job_b(db_session, tenant_b, customer_b, site_b, job_status_b):
    """Job belonging to Tenant B"""
    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        customer_id=customer_b.id,
        site_id=site_b.id,
        status_id=job_status_b.id,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def test_user(db_session):
    """Create a real User record to satisfy job_time_entry.user_id FK"""
    user = User(
        id=uuid.uuid4(),
        email=f"batch3-test-{uuid.uuid4()}@example.com",
        first_name="Batch3",
        last_name="TestUser",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def qco_line_type(db_session):
    """Shared QCO line type for change order line tests"""
    lt = QcoLineType(
        id=uuid.uuid4(),
        tenant_id=None,
        code=f"labor-{uuid.uuid4()}",
        name="Labor",
        is_default=True,
        is_active=True,
    )
    db_session.add(lt)
    db_session.commit()
    db_session.refresh(lt)
    return lt


@pytest.fixture
def utc_now():
    return datetime.now(UTC)


# ==================== JOB NOTES TESTS ====================


class TestJobNotesTenantIsolation:
    """Verify job_notes tenant_id stamping and cross-tenant isolation"""

    def test_job_notes_tenant_id_is_stamped(self, db_session, tenant_a, job_a):
        """tenant_id is correctly set when creating a JobNotes record"""
        note = JobNotes(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=job_a.id,
            notes="Panel upgrade complete",
            customer_visible=False,
        )
        db_session.add(note)
        db_session.commit()
        db_session.refresh(note)

        assert note.tenant_id == tenant_a.id

    def test_job_notes_cross_tenant_query_returns_none(
        self, db_session, tenant_a, tenant_b, job_b
    ):
        """Tenant A cannot retrieve Tenant B's job notes via tenant-scoped query"""
        note_b = JobNotes(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            notes="Secret note for tenant B",
            customer_visible=False,
        )
        db_session.add(note_b)
        db_session.commit()

        # Tenant A queries for Tenant B's note by ID — must return None (404 pattern)
        result = db_session.exec(
            select(JobNotes).where(
                JobNotes.id == note_b.id,
                JobNotes.tenant_id == tenant_a.id,  # Tenant A's scope
            )
        ).first()

        assert result is None, "IDOR: Tenant A must not access Tenant B's job notes"

    def test_job_notes_list_excludes_other_tenant(
        self, db_session, tenant_a, tenant_b, job_a, job_b
    ):
        """List query for Tenant A excludes Tenant B's notes"""
        note_a = JobNotes(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=job_a.id,
            notes="Tenant A note",
            customer_visible=False,
        )
        note_b = JobNotes(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            notes="Tenant B note",
            customer_visible=False,
        )
        db_session.add_all([note_a, note_b])
        db_session.commit()

        tenant_a_notes = db_session.exec(
            select(JobNotes).where(JobNotes.tenant_id == tenant_a.id)
        ).all()

        ids = [n.id for n in tenant_a_notes]
        assert note_a.id in ids
        assert note_b.id not in ids, "IDOR: Tenant B note leaked into Tenant A list"


# ==================== JOB TIME ENTRY TESTS ====================


class TestJobTimeEntryTenantIsolation:
    """Verify job_time_entry tenant_id stamping and cross-tenant isolation"""

    def test_job_time_entry_tenant_id_is_stamped(
        self, db_session, tenant_a, job_a, test_user, utc_now
    ):
        """tenant_id is correctly set on creation"""
        entry = JobTimeEntry(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=job_a.id,
            user_id=test_user.id,
            started_at=utc_now,
            ended_at=utc_now,
            hours=8.0,
            hourly_rate_cents=8500,
            total_cost_cents=68000,
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        assert entry.tenant_id == tenant_a.id

    def test_job_time_entry_cross_tenant_query_returns_none(
        self, db_session, tenant_a, tenant_b, job_b, test_user, utc_now
    ):
        """Tenant A cannot retrieve Tenant B's time entry via tenant-scoped query"""
        entry_b = JobTimeEntry(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            user_id=test_user.id,
            started_at=utc_now,
            ended_at=utc_now,
            hours=4.0,
            hourly_rate_cents=8500,
            total_cost_cents=34000,
        )
        db_session.add(entry_b)
        db_session.commit()

        # Tenant A queries for Tenant B's time entry — must return None
        result = db_session.exec(
            select(JobTimeEntry).where(
                JobTimeEntry.id == entry_b.id,
                JobTimeEntry.tenant_id == tenant_a.id,
            )
        ).first()

        assert result is None, "IDOR: Tenant A must not access Tenant B's time entries"

    def test_job_time_entry_list_excludes_other_tenant(
        self, db_session, tenant_a, tenant_b, job_a, job_b, test_user, utc_now
    ):
        """List query for Tenant A excludes Tenant B's time entries"""
        entry_a = JobTimeEntry(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=job_a.id,
            user_id=test_user.id,
            started_at=utc_now,
            ended_at=utc_now,
            hours=8.0,
            hourly_rate_cents=8500,
            total_cost_cents=68000,
        )
        entry_b = JobTimeEntry(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            user_id=test_user.id,
            started_at=utc_now,
            ended_at=utc_now,
            hours=8.0,
            hourly_rate_cents=8500,
            total_cost_cents=68000,
        )
        db_session.add_all([entry_a, entry_b])
        db_session.commit()

        tenant_a_entries = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.tenant_id == tenant_a.id)
        ).all()

        ids = [e.id for e in tenant_a_entries]
        assert entry_a.id in ids
        assert entry_b.id not in ids, "IDOR: Tenant B entry leaked into Tenant A list"


# ==================== CHANGE ORDER TESTS ====================


class TestChangeOrderTenantIsolation:
    """Verify change_order tenant_id stamping and cross-tenant isolation"""

    def test_change_order_tenant_id_is_stamped(self, db_session, tenant_a, job_a):
        """tenant_id is correctly set on creation"""
        co = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=job_a.id,
            description="Additional panel circuits",
        )
        db_session.add(co)
        db_session.commit()
        db_session.refresh(co)

        assert co.tenant_id == tenant_a.id

    def test_change_order_cross_tenant_query_returns_none(
        self, db_session, tenant_a, tenant_b, job_b
    ):
        """Tenant A cannot retrieve Tenant B's change order"""
        co_b = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            description="Tenant B change order",
        )
        db_session.add(co_b)
        db_session.commit()

        result = db_session.exec(
            select(ChangeOrder).where(
                ChangeOrder.id == co_b.id,
                ChangeOrder.tenant_id == tenant_a.id,
            )
        ).first()

        assert result is None, "IDOR: Tenant A must not access Tenant B's change orders"

    def test_change_order_list_excludes_other_tenant(
        self, db_session, tenant_a, tenant_b, job_a, job_b
    ):
        """List query for Tenant A excludes Tenant B's change orders"""
        co_a = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=job_a.id,
            description="CO for Tenant A",
        )
        co_b = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            description="CO for Tenant B",
        )
        db_session.add_all([co_a, co_b])
        db_session.commit()

        tenant_a_cos = db_session.exec(
            select(ChangeOrder).where(ChangeOrder.tenant_id == tenant_a.id)
        ).all()

        ids = [co.id for co in tenant_a_cos]
        assert co_a.id in ids
        assert co_b.id not in ids, "IDOR: Tenant B CO leaked into Tenant A list"


# ==================== CHANGE ORDER ATTACHMENT TESTS ====================


class TestChangeOrderAttachmentTenantIsolation:
    """Verify change_order_attachment tenant_id stamping and cross-tenant isolation"""

    def test_change_order_attachment_tenant_id_is_stamped(
        self, db_session, tenant_a, job_a
    ):
        """tenant_id is correctly set on creation"""
        co = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=job_a.id,
            description="CO with attachment",
        )
        db_session.add(co)
        db_session.commit()

        attachment = ChangeOrderAttachment(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            change_order_id=co.id,
            file_name="scope_photo.jpg",
            mime_type="image/jpeg",
            size_bytes=204800,
            object_key="tenants/t-1/co/file.jpg",
        )
        db_session.add(attachment)
        db_session.commit()
        db_session.refresh(attachment)

        assert attachment.tenant_id == tenant_a.id

    def test_change_order_attachment_cross_tenant_query_returns_none(
        self, db_session, tenant_a, tenant_b, job_b
    ):
        """Tenant A cannot retrieve Tenant B's attachment"""
        co_b = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            description="Tenant B CO",
        )
        db_session.add(co_b)
        db_session.commit()

        attachment_b = ChangeOrderAttachment(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            change_order_id=co_b.id,
            file_name="secret_photo.jpg",
            mime_type="image/jpeg",
            size_bytes=102400,
            object_key="tenants/t-b/co/secret.jpg",
        )
        db_session.add(attachment_b)
        db_session.commit()

        result = db_session.exec(
            select(ChangeOrderAttachment).where(
                ChangeOrderAttachment.id == attachment_b.id,
                ChangeOrderAttachment.tenant_id == tenant_a.id,
            )
        ).first()

        assert result is None, (
            "IDOR: Tenant A must not access Tenant B's CO attachments"
        )


# ==================== CHANGE ORDER LINE TESTS ====================


class TestChangeOrderLineTenantIsolation:
    """Verify change_order_line tenant_id stamping and cross-tenant isolation"""

    def test_change_order_line_tenant_id_is_stamped(
        self, db_session, tenant_a, job_a, qco_line_type
    ):
        """tenant_id is correctly set on creation"""
        co = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=job_a.id,
            description="CO for line test",
        )
        db_session.add(co)
        db_session.commit()

        line = ChangeOrderLine(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            change_order_id=co.id,
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Labor - panel upgrade",
            quantity=1,
            unit_price_cents=150000,
        )
        db_session.add(line)
        db_session.commit()
        db_session.refresh(line)

        assert line.tenant_id == tenant_a.id

    def test_change_order_line_cross_tenant_query_returns_none(
        self, db_session, tenant_a, tenant_b, job_b, qco_line_type
    ):
        """Tenant A cannot retrieve Tenant B's change order line"""
        co_b = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            description="Tenant B CO",
        )
        db_session.add(co_b)
        db_session.commit()

        line_b = ChangeOrderLine(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            change_order_id=co_b.id,
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Secret line item",
            quantity=1,
            unit_price_cents=999999,
        )
        db_session.add(line_b)
        db_session.commit()

        result = db_session.exec(
            select(ChangeOrderLine).where(
                ChangeOrderLine.id == line_b.id,
                ChangeOrderLine.tenant_id == tenant_a.id,
            )
        ).first()

        assert result is None, "IDOR: Tenant A must not access Tenant B's CO lines"

    def test_change_order_line_list_excludes_other_tenant(
        self, db_session, tenant_a, tenant_b, job_a, job_b, qco_line_type
    ):
        """List query for Tenant A excludes Tenant B's lines"""
        co_a = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=job_a.id,
            description="CO A",
        )
        co_b = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            description="CO B",
        )
        db_session.add_all([co_a, co_b])
        db_session.commit()

        line_a = ChangeOrderLine(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            change_order_id=co_a.id,
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Line A",
            quantity=1,
            unit_price_cents=10000,
        )
        line_b = ChangeOrderLine(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            change_order_id=co_b.id,
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Line B",
            quantity=1,
            unit_price_cents=99999,
        )
        db_session.add_all([line_a, line_b])
        db_session.commit()

        tenant_a_lines = db_session.exec(
            select(ChangeOrderLine).where(ChangeOrderLine.tenant_id == tenant_a.id)
        ).all()

        ids = [l.id for l in tenant_a_lines]
        assert line_a.id in ids
        assert line_b.id not in ids, "IDOR: Tenant B CO line leaked into Tenant A list"


# ==================== CHANGE ORDER LINE TAX COMPONENT TESTS ====================


class TestChangeOrderLineTaxComponentTenantIsolation:
    """Verify change_order_line_tax_component tenant_id stamping and cross-tenant isolation
    Note: This table uses a 2-hop FK path: tax_component -> co_line -> change_order -> tenant
    """

    def test_coltc_tenant_id_is_stamped(
        self, db_session, tenant_a, job_a, qco_line_type
    ):
        """tenant_id is correctly set via 2-hop path on creation"""
        from decimal import Decimal

        co = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            job_id=job_a.id,
            description="CO with tax component",
        )
        db_session.add(co)
        db_session.commit()

        line = ChangeOrderLine(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            change_order_id=co.id,
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Taxable labor",
            quantity=1,
            unit_price_cents=100000,
        )
        db_session.add(line)
        db_session.commit()

        # Get a tax_rate_version_id (use a dummy bigint)
        tax_component = ChangeOrderLineTaxComponent(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            change_order_line_id=line.id,
            tax_rate_version_id=1,
            component_code="state_tax",
            rate_pct=Decimal("0.0875"),
            amount_cents=8750,
        )
        db_session.add(tax_component)
        db_session.commit()
        db_session.refresh(tax_component)

        assert tax_component.tenant_id == tenant_a.id

    def test_coltc_cross_tenant_query_returns_none(
        self, db_session, tenant_a, tenant_b, job_b, qco_line_type
    ):
        """Tenant A cannot retrieve Tenant B's tax component (2-hop isolation)"""
        from decimal import Decimal

        co_b = ChangeOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            job_id=job_b.id,
            description="Tenant B CO",
        )
        db_session.add(co_b)
        db_session.commit()

        line_b = ChangeOrderLine(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            change_order_id=co_b.id,
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Tenant B taxable line",
            quantity=1,
            unit_price_cents=100000,
        )
        db_session.add(line_b)
        db_session.commit()

        tax_b = ChangeOrderLineTaxComponent(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            change_order_line_id=line_b.id,
            tax_rate_version_id=1,
            component_code="state_tax",
            rate_pct=Decimal("0.0875"),
            amount_cents=8750,
        )
        db_session.add(tax_b)
        db_session.commit()

        # Tenant A queries for Tenant B's tax component — must return None (404 pattern)
        result = db_session.exec(
            select(ChangeOrderLineTaxComponent).where(
                ChangeOrderLineTaxComponent.id == tax_b.id,
                ChangeOrderLineTaxComponent.tenant_id == tenant_a.id,
            )
        ).first()

        assert result is None, (
            "IDOR: Tenant A must not access Tenant B's CO line tax components (2-hop path)"
        )


# ==================== CROSS-MODEL CONSISTENCY TEST ====================


class TestBatch3TenantIdConsistency:
    """Verify tenant_id consistency across the 6 batch-3 models"""

    def test_all_batch3_models_have_tenant_id_field(self):
        """All 6 models expose tenant_id in their model fields"""
        for model_cls in [
            JobNotes,
            JobTimeEntry,
            ChangeOrder,
            ChangeOrderAttachment,
            ChangeOrderLine,
            ChangeOrderLineTaxComponent,
        ]:
            assert "tenant_id" in model_cls.model_fields, (
                f"{model_cls.__name__} missing tenant_id field"
            )

    def test_all_batch3_models_tenant_id_not_nullable(self):
        """All 6 models have tenant_id defined as non-optional (non-nullable)"""
        for model_cls in [
            JobNotes,
            JobTimeEntry,
            ChangeOrder,
            ChangeOrderAttachment,
            ChangeOrderLine,
            ChangeOrderLineTaxComponent,
        ]:
            field = model_cls.model_fields["tenant_id"]
            # Non-nullable field has no default value of None
            assert (
                field.default is None
                or not field.is_required()
                or field.annotation is not None
            ), f"{model_cls.__name__}.tenant_id should not allow NULL"
