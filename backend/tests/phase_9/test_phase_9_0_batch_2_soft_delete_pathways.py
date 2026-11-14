"""
Phase 9.0 Batch 2 — Soft-Delete Cascade Pathway Tests

Verifies that the DB-level AFTER UPDATE triggers installed in migration
39ca85621aad correctly cascade is_active = false from parent to child
records across all 9 deployed trigger pathways.

ACTUAL TRIGGER PATHWAYS (verified against live DB FKs):
  Hierarchy A (CRM):
    A1. customer → site    (site.customer_id)
    A2. customer → contact (contact.customer_id)

  Hierarchy B (Sales):
    B1. quote      → quote_line                (quote_line.quote_id)
    B2. quote_line → quote_line_tax_component  (quote_line_tax_component.quote_line_id)

  Hierarchy C (Billing):
    C1. invoice      → invoice_line               (invoice_line.invoice_id)
    C2. invoice_line → invoice_line_tax_component (invoice_line_tax_component.invoice_line_id)

  Hierarchy D (Fulfillment):
    D1. job          → change_order      (change_order.job_id)
    D2. change_order → change_order_line (change_order_line.change_order_id)
    D3. job          → job_expense       (job_expense.job_id)

NOTE: The prompt spec listed additional hierarchies (site→contact, contact→address,
change_order_line→job_expense) which do NOT exist as FK constraints in the actual DB.
The triggers deployed, and tests written here, strictly follow the live schema.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlmodel import select

# ===========================================================================
# LOCAL FIXTURES (self-contained within this test module)
# ===========================================================================


@pytest.fixture
def p9_customer(db_session, test_tenant):
    """A fresh active customer for pathway tests."""
    from app.models.crm import Customer

    obj = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        display_name=f"P9 Customer {uuid.uuid4().hex[:6]}",
        type="person",
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_site(db_session, test_tenant, p9_customer):
    """A fresh active site linked to p9_customer."""
    from app.models.crm import Site

    obj = Site(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=p9_customer.id,
        name="P9 Site",
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_contact(db_session, test_tenant, p9_customer):
    """A fresh active contact linked to p9_customer."""
    from app.models.crm import Contact

    obj = Contact(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=p9_customer.id,
        first_name="P9",
        last_name="Contact",
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_quote_status(db_session, test_tenant):
    """Reusable quote_status for the session."""
    from app.models.quoting import QuoteStatus

    existing = db_session.exec(
        select(QuoteStatus).where(
            QuoteStatus.tenant_id == test_tenant.id,
            QuoteStatus.code == "p9_draft",
        )
    ).first()
    if existing:
        return existing
    obj = QuoteStatus(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="p9_draft",
        name="P9 Draft",
        is_default=False,
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_quote(db_session, test_tenant, p9_customer, p9_site, p9_quote_status):
    """A fresh active quote."""
    from app.models.quoting import Quote

    obj = Quote(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=p9_customer.id,
        site_id=p9_site.id,
        status_id=p9_quote_status.id,
        currency="USD",
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_qco_line_type(db_session, test_tenant):
    """Reusable QcoLineType."""
    from app.models.quoting import QcoLineType

    existing = db_session.exec(
        select(QcoLineType).where(
            QcoLineType.tenant_id == test_tenant.id,
            QcoLineType.code == "p9_material",
        )
    ).first()
    if existing:
        return existing
    obj = QcoLineType(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="p9_material",
        name="P9 Material",
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_quote_line(db_session, test_tenant, p9_quote, p9_qco_line_type):
    """A fresh active quote_line."""
    from app.models.quoting import QuoteLine

    obj = QuoteLine(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        quote_id=p9_quote.id,
        position=1,
        qco_line_type_id=p9_qco_line_type.id,
        description="P9 Quote Line Item",
        quantity=Decimal("1.0"),
        unit_price_cents=10000,
        subtotal_cents=10000,
        total_cents=10000,
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_tax_rate_version_id(db_session):
    """Return the id of the first available tax_rate_version (id=1 guaranteed from seed)."""
    from app.models.catalog import TaxRateVersion

    tv = db_session.exec(select(TaxRateVersion)).first()
    assert tv is not None, "No tax_rate_version row found; seed data required."
    return tv.id


@pytest.fixture
def p9_quote_line_tax_component(
    db_session, test_tenant, p9_quote_line, p9_tax_rate_version_id
):
    """A fresh active quote_line_tax_component."""
    from app.models.quoting import QuoteLineTaxComponent

    obj = QuoteLineTaxComponent(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        quote_line_id=p9_quote_line.id,
        tax_rate_version_id=p9_tax_rate_version_id,
        component_code="STATE",
        rate_pct=Decimal("0.0825"),
        amount_cents=825,
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_invoice_status(db_session, test_tenant):
    """Reusable InvoiceStatus."""
    from app.models.billing import InvoiceStatus

    existing = db_session.exec(
        select(InvoiceStatus).where(
            InvoiceStatus.tenant_id == test_tenant.id,
            InvoiceStatus.code == "p9_draft",
        )
    ).first()
    if existing:
        return existing
    obj = InvoiceStatus(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="p9_draft",
        name="P9 Draft",
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_invoice(db_session, test_tenant, p9_customer, p9_site, p9_invoice_status):
    """A fresh active invoice."""
    from app.models.billing import Invoice

    obj = Invoice(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        invoice_number=f"INV-P9-{uuid.uuid4().hex[:8].upper()}",
        customer_id=p9_customer.id,
        site_id=p9_site.id,
        status_id=p9_invoice_status.id,
        currency="USD",
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_invoice_line(db_session, test_tenant, p9_invoice, p9_qco_line_type):
    """A fresh active invoice_line."""
    from app.models.billing import InvoiceLine

    obj = InvoiceLine(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        invoice_id=p9_invoice.id,
        source_type="ad_hoc",
        position=1,
        qco_line_type_id=p9_qco_line_type.id,
        description="P9 Invoice Line Item",
        quantity=1.0,
        unit_price_cents=10000,
        subtotal_cents=10000,
        total_cents=10000,
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_invoice_line_tax_component(
    db_session, test_tenant, p9_invoice_line, p9_tax_rate_version_id
):
    """A fresh active invoice_line_tax_component."""
    from app.models.billing import InvoiceLineTaxComponent

    obj = InvoiceLineTaxComponent(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        invoice_line_id=p9_invoice_line.id,
        tax_rate_version_id=p9_tax_rate_version_id,
        component_code="STATE",
        rate_pct=Decimal("0.0825"),
        amount_cents=825,
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_job_status(db_session):
    """Reusable JobStatus."""
    from app.models.fulfillment import JobStatus

    existing = db_session.exec(
        select(JobStatus).where(JobStatus.code == "p9_active")
    ).first()
    if existing:
        return existing
    obj = JobStatus(
        id=uuid.uuid4(),
        code="p9_active",
        name="P9 Active",
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_job(db_session, test_tenant, p9_customer, p9_site, p9_job_status):
    """A fresh active job."""
    from app.models.fulfillment import Job

    obj = Job(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=p9_customer.id,
        site_id=p9_site.id,
        status_id=p9_job_status.id,
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_change_order(db_session, test_tenant, p9_job):
    """A fresh active change_order."""
    from app.models.quoting import ChangeOrder

    obj = ChangeOrder(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        job_id=p9_job.id,
        description="P9 Change Order",
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_change_order_line(db_session, test_tenant, p9_change_order, p9_qco_line_type):
    """A fresh active change_order_line."""
    from app.models.quoting import ChangeOrderLine

    obj = ChangeOrderLine(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        change_order_id=p9_change_order.id,
        position=1,
        qco_line_type_id=p9_qco_line_type.id,
        description="P9 Change Order Line",
        quantity=Decimal("1.0"),
        unit_price_cents=5000,
        subtotal_cents=5000,
        total_cents=5000,
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_job_expense_category(db_session):
    """Reusable JobExpenseCategory."""
    from app.models.fulfillment import JobExpenseCategory

    existing = db_session.exec(
        select(JobExpenseCategory).where(JobExpenseCategory.code == "p9_materials")
    ).first()
    if existing:
        return existing
    obj = JobExpenseCategory(
        code="p9_materials",
        name="P9 Materials",
        is_active=True,
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture
def p9_job_expense(db_session, test_tenant, test_user, p9_job, p9_job_expense_category):
    """A fresh active job_expense linked to p9_job."""
    from app.models.fulfillment import JobExpense

    obj = JobExpense(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        job_id=p9_job.id,
        user_id=test_user.id,  # FIND-121: user_id required (NOT NULL)
        job_expense_category_code=p9_job_expense_category.code,
        description="P9 Job Expense",
        cost_cents=2000,
        markup_pct=0.20,
        billable_cents=2400,
        is_billable=True,
        is_active=True,
        incurred_at=datetime.now(UTC),
    )
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


# ===========================================================================
# HIERARCHY A: Core CRM
# customer → site  |  customer → contact
# ===========================================================================


def test_customer_soft_delete_cascades_to_site(
    db_session, test_tenant, p9_customer, p9_site
):
    """Trigger trg_soft_delete_customer_to_site: soft-deleting customer deactivates its sites."""
    # Pre-condition: child is active
    assert p9_site.is_active is True

    # 1. Soft-delete the parent
    p9_customer.is_active = False
    db_session.add(p9_customer)
    db_session.commit()

    # 2. Refresh child from DB to capture trigger effect
    db_session.refresh(p9_site)

    # 3. Assert cascade
    assert p9_site.is_active is False, (
        "DB trigger trg_soft_delete_customer_to_site did not cascade soft-delete from customer to site."
    )


def test_customer_soft_delete_cascades_to_contact(
    db_session, test_tenant, p9_customer, p9_contact
):
    """Trigger trg_soft_delete_customer_to_contact: soft-deleting customer deactivates its contacts."""
    assert p9_contact.is_active is True

    p9_customer.is_active = False
    db_session.add(p9_customer)
    db_session.commit()

    db_session.refresh(p9_contact)

    assert p9_contact.is_active is False, (
        "DB trigger trg_soft_delete_customer_to_contact did not cascade soft-delete from customer to contact."
    )


# ===========================================================================
# HIERARCHY B: Sales
# quote → quote_line → quote_line_tax_component
# ===========================================================================


def test_quote_soft_delete_cascades_to_quote_line(
    db_session, test_tenant, p9_quote, p9_quote_line
):
    """Trigger trg_soft_delete_quote_to_quote_line: soft-deleting quote deactivates its lines."""
    assert p9_quote_line.is_active is True

    p9_quote.is_active = False
    db_session.add(p9_quote)
    db_session.commit()

    db_session.refresh(p9_quote_line)

    assert p9_quote_line.is_active is False, (
        "DB trigger trg_soft_delete_quote_to_quote_line did not cascade soft-delete from quote to quote_line."
    )


def test_quote_line_soft_delete_cascades_to_tax_component(
    db_session, test_tenant, p9_quote_line, p9_quote_line_tax_component
):
    """Trigger trg_soft_delete_quote_line_to_tax_component: soft-deleting quote_line deactivates tax components."""
    assert p9_quote_line_tax_component.is_active is True

    p9_quote_line.is_active = False
    db_session.add(p9_quote_line)
    db_session.commit()

    db_session.refresh(p9_quote_line_tax_component)

    assert p9_quote_line_tax_component.is_active is False, (
        "DB trigger trg_soft_delete_quote_line_to_tax_component did not cascade soft-delete "
        "from quote_line to quote_line_tax_component."
    )


# ===========================================================================
# HIERARCHY C: Billing
# invoice → invoice_line → invoice_line_tax_component
# ===========================================================================


def test_invoice_soft_delete_cascades_to_invoice_line(
    db_session, test_tenant, p9_invoice, p9_invoice_line
):
    """Trigger trg_soft_delete_invoice_to_invoice_line: soft-deleting invoice deactivates its lines."""
    assert p9_invoice_line.is_active is True

    p9_invoice.is_active = False
    db_session.add(p9_invoice)
    db_session.commit()

    db_session.refresh(p9_invoice_line)

    assert p9_invoice_line.is_active is False, (
        "DB trigger trg_soft_delete_invoice_to_invoice_line did not cascade soft-delete "
        "from invoice to invoice_line."
    )


def test_invoice_line_soft_delete_cascades_to_tax_component(
    db_session, test_tenant, p9_invoice_line, p9_invoice_line_tax_component
):
    """Trigger trg_soft_delete_invoice_line_to_tax_component: soft-deleting invoice_line deactivates tax components."""
    assert p9_invoice_line_tax_component.is_active is True

    p9_invoice_line.is_active = False
    db_session.add(p9_invoice_line)
    db_session.commit()

    db_session.refresh(p9_invoice_line_tax_component)

    assert p9_invoice_line_tax_component.is_active is False, (
        "DB trigger trg_soft_delete_invoice_line_to_tax_component did not cascade soft-delete "
        "from invoice_line to invoice_line_tax_component."
    )


# ===========================================================================
# HIERARCHY D: Fulfillment
# job → change_order → change_order_line
# job → job_expense (direct FK)
# ===========================================================================


def test_job_soft_delete_cascades_to_change_order(
    db_session, test_tenant, p9_job, p9_change_order
):
    """Trigger trg_soft_delete_job_to_change_order: soft-deleting job deactivates its change_orders."""
    assert p9_change_order.is_active is True

    p9_job.is_active = False
    db_session.add(p9_job)
    db_session.commit()

    db_session.refresh(p9_change_order)

    assert p9_change_order.is_active is False, (
        "DB trigger trg_soft_delete_job_to_change_order did not cascade soft-delete from job to change_order."
    )


def test_change_order_soft_delete_cascades_to_change_order_line(
    db_session, test_tenant, p9_change_order, p9_change_order_line
):
    """Trigger trg_soft_delete_change_order_to_change_order_line: soft-deleting change_order deactivates its lines."""
    assert p9_change_order_line.is_active is True

    p9_change_order.is_active = False
    db_session.add(p9_change_order)
    db_session.commit()

    db_session.refresh(p9_change_order_line)

    assert p9_change_order_line.is_active is False, (
        "DB trigger trg_soft_delete_change_order_to_change_order_line did not cascade soft-delete "
        "from change_order to change_order_line."
    )


def test_job_soft_delete_cascades_to_job_expense(
    db_session, test_tenant, p9_job, p9_job_expense
):
    """Trigger trg_soft_delete_job_to_job_expense: soft-deleting job deactivates its job_expenses."""
    assert p9_job_expense.is_active is True

    p9_job.is_active = False
    db_session.add(p9_job)
    db_session.commit()

    db_session.refresh(p9_job_expense)

    assert p9_job_expense.is_active is False, (
        "DB trigger trg_soft_delete_job_to_job_expense did not cascade soft-delete from job to job_expense."
    )


# ===========================================================================
# ANTI-REGRESSION: Confirm trigger does NOT fire on non-is_active updates
# ===========================================================================


def test_customer_update_non_is_active_does_not_cascade(
    db_session, test_tenant, p9_customer, p9_site, p9_contact
):
    """Updating a non-is_active field on customer must NOT soft-delete child site or contact."""
    assert p9_site.is_active is True
    assert p9_contact.is_active is True

    # Update a non-is_active field (notes) — trigger must NOT fire
    p9_customer.notes = "Anti-regression update — no cascade should occur"
    db_session.add(p9_customer)
    db_session.commit()

    db_session.refresh(p9_site)
    db_session.refresh(p9_contact)

    assert p9_site.is_active is True, (
        "Trigger fired incorrectly: customer notes update should NOT deactivate child site."
    )
    assert p9_contact.is_active is True, (
        "Trigger fired incorrectly: customer notes update should NOT deactivate child contact."
    )
