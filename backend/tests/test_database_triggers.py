"""
Test Database Triggers for Quote Totals, Change Order Totals, and User Email Sync

These tests verify that PostgreSQL triggers correctly maintain data integrity
for financial calculations and user email synchronization.

Related Gaps: #31 (Quote Totals), #32 (Change Order Totals), #33 (User Email Sync)
Migration: 2026_03_17_1451-a4d2659a2921_add_database_triggers_for_quote_totals_.py
"""

import uuid
from decimal import Decimal

import pytest
from sqlmodel import Session, select

from app.models.billing import Currency
from app.models.core import Tenant, User, UserEndpoint
from app.models.crm import Customer, CustomerType, Site
from app.models.fulfillment import Job, JobStatus
from app.models.quoting import (
    ChangeOrder,
    ChangeOrderLine,
    ChangeOrderLineTaxComponent,
    QcoLineType,
    Quote,
    QuoteLine,
    QuoteLineTaxComponent,
    QuoteStatus,
)

# ============================================================================
# Test Fixtures and Helpers
# ============================================================================


@pytest.fixture
def test_tenant(db_session: Session):
    """Create a test tenant."""
    tenant = Tenant(name=f"Trigger Test Tenant {uuid.uuid4()}")
    db_session.add(tenant)
    db_session.flush()
    return tenant


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user."""
    user = User(email=f"trigger-test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def test_customer(db_session: Session, test_tenant: Tenant):
    """Create a test customer."""
    customer = Customer(
        tenant_id=test_tenant.id,
        type=CustomerType.person,
        display_name="Trigger Test Customer",
    )
    db_session.add(customer)
    db_session.flush()
    return customer


@pytest.fixture
def test_site(db_session: Session, test_tenant: Tenant, test_customer: Customer):
    """Create a test site."""
    site = Site(
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        name="Trigger Test Site",
    )
    db_session.add(site)
    db_session.flush()
    return site


@pytest.fixture
def test_quote_status(db_session: Session, test_tenant: Tenant):
    """Create a test quote status."""
    status = QuoteStatus(
        tenant_id=test_tenant.id,
        code="draft",
        name="Draft",
        is_default=True,
    )
    db_session.add(status)
    db_session.flush()
    return status


@pytest.fixture
def test_line_type(db_session: Session, test_tenant: Tenant):
    """Create a test line type."""
    line_type = QcoLineType(
        tenant_id=test_tenant.id,
        code="material",
        name="Material",
    )
    db_session.add(line_type)
    db_session.flush()
    return line_type


@pytest.fixture
def test_currency(db_session: Session):
    """Ensure USD currency exists."""
    currency = db_session.exec(select(Currency).where(Currency.code == "USD")).first()
    if not currency:
        currency = Currency(code="USD", name="US Dollar", symbol="$")
        db_session.add(currency)
        db_session.flush()
    return currency


@pytest.fixture
def test_quote(
    db_session: Session,
    test_tenant: Tenant,
    test_customer: Customer,
    test_site: Site,
    test_quote_status: QuoteStatus,
    test_currency: Currency,
):
    """Create a test quote with initial totals set to 0."""
    quote = Quote(
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=test_quote_status.id,
        subtotal_cents=0,
        tax_cents=0,
        total_cents=0,
        currency="USD",
    )
    db_session.add(quote)
    db_session.flush()
    return quote


@pytest.fixture
def test_job_status(db_session: Session, test_tenant: Tenant):
    """Create a test job status."""
    status = JobStatus(
        tenant_id=test_tenant.id,
        code="active",
        name="Active",
        is_default=True,
    )
    db_session.add(status)
    db_session.flush()
    return status


@pytest.fixture
def test_job(
    db_session: Session,
    test_tenant: Tenant,
    test_customer: Customer,
    test_site: Site,
    test_job_status: JobStatus,
):
    """Create a test job."""
    job = Job(
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=test_job_status.id,
        name="Trigger Test Job",
    )
    db_session.add(job)
    db_session.flush()
    return job


# ============================================================================
# Quote Totals Trigger Tests
# ============================================================================


def test_quote_totals_recalc_on_line_insert(
    db_session: Session, test_quote: Quote, test_line_type: QcoLineType
):
    """Test that quote totals update when quote_line is inserted."""
    # Create a quote line
    line = QuoteLine(
        tenant_id=test_quote.tenant_id,
        quote_id=test_quote.id,
        position=1,
        qco_line_type_id=test_line_type.id,
        description="Test Line Item",
        quantity=Decimal("2.0"),
        unit_price_cents=10000,  # $100.00
        subtotal_cents=20000,  # $200.00
        total_cents=21600,  # $216.00
    )
    db_session.add(line)
    db_session.flush()

    # Create tax component (new componentized approach)
    tax_comp = QuoteLineTaxComponent(
        tenant_id=test_quote.tenant_id,
        quote_line_id=line.id,
        tax_rate_version_id=1,  # Assume seeded
        component_code="STATE",
        rate_pct=Decimal("8.0"),
        amount_cents=1600,  # $16.00 (8% tax)
    )
    db_session.add(tax_comp)
    db_session.commit()

    # Refresh quote to get trigger-updated values
    db_session.refresh(test_quote)

    # Verify trigger fired and updated quote totals
    assert test_quote.subtotal_cents == 20000, "Subtotal should be $200.00"
    assert test_quote.tax_cents == 1600, "Tax should be $16.00"
    assert test_quote.total_cents == 21600, "Total should be $216.00"


def test_quote_totals_recalc_on_line_update(
    db_session: Session, test_quote: Quote, test_line_type: QcoLineType
):
    """Test that quote totals update when quote_line is modified."""
    # Create initial line
    line = QuoteLine(
        tenant_id=test_quote.tenant_id,
        quote_id=test_quote.id,
        position=1,
        qco_line_type_id=test_line_type.id,
        description="Initial Line",
        quantity=Decimal("1.0"),
        unit_price_cents=5000,
        subtotal_cents=5000,
        total_cents=5400,
    )
    db_session.add(line)
    db_session.flush()

    # Create tax component
    tax_comp = QuoteLineTaxComponent(
        tenant_id=test_quote.tenant_id,
        quote_line_id=line.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("8.0"),
        amount_cents=400,
    )
    db_session.add(tax_comp)
    db_session.commit()
    db_session.refresh(test_quote)

    assert test_quote.subtotal_cents == 5000
    assert test_quote.tax_cents == 400

    # Update the tax component amount (simulate rate change)
    tax_comp.amount_cents = 1200  # $12.00
    db_session.commit()
    db_session.refresh(test_quote)

    # Verify trigger updated quote totals
    assert test_quote.tax_cents == 1200, "Tax should update to $12.00"
    assert test_quote.total_cents == 6200, "Total should update to $62.00 (5000 + 1200)"


def test_quote_totals_recalc_on_line_delete(
    db_session: Session, test_quote: Quote, test_line_type: QcoLineType
):
    """Test that quote totals update when quote_line is deleted."""
    # Create two lines
    line1 = QuoteLine(
        tenant_id=test_quote.tenant_id,
        quote_id=test_quote.id,
        position=1,
        qco_line_type_id=test_line_type.id,
        description="Line 1",
        subtotal_cents=10000,
        total_cents=10800,
    )
    line2 = QuoteLine(
        tenant_id=test_quote.tenant_id,
        quote_id=test_quote.id,
        position=2,
        qco_line_type_id=test_line_type.id,
        description="Line 2",
        subtotal_cents=5000,
        total_cents=5400,
    )
    db_session.add_all([line1, line2])
    db_session.flush()

    # Create tax components for both lines
    tax_comp1 = QuoteLineTaxComponent(
        tenant_id=test_quote.tenant_id,
        quote_line_id=line1.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("8.0"),
        amount_cents=800,
    )
    tax_comp2 = QuoteLineTaxComponent(
        tenant_id=test_quote.tenant_id,
        quote_line_id=line2.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("8.0"),
        amount_cents=400,
    )
    db_session.add_all([tax_comp1, tax_comp2])
    db_session.commit()
    db_session.refresh(test_quote)

    # Verify initial totals (sum of both lines)
    assert test_quote.subtotal_cents == 15000
    assert test_quote.tax_cents == 1200
    assert test_quote.total_cents == 16200

    # Delete tax component first (FK constraint doesn't have CASCADE)
    db_session.delete(tax_comp2)
    db_session.flush()  # Flush to ensure tax component is deleted first
    # Then delete the line
    db_session.delete(line2)
    db_session.commit()
    db_session.refresh(test_quote)

    # Verify totals now only reflect line1
    assert test_quote.subtotal_cents == 10000, "Should only include remaining line"
    assert test_quote.tax_cents == 800
    assert test_quote.total_cents == 10800


def test_quote_totals_multiple_lines(
    db_session: Session, test_quote: Quote, test_line_type: QcoLineType
):
    """Test that quote totals correctly sum multiple quote lines."""
    # Create three lines with different amounts
    amounts = [10000, 25000, 15000]
    lines = []
    for i, amount in enumerate(amounts, start=1):
        line = QuoteLine(
            tenant_id=test_quote.tenant_id,
            quote_id=test_quote.id,
            position=i,
            qco_line_type_id=test_line_type.id,
            description=f"Line {i}",
            subtotal_cents=amount,
            total_cents=int(amount * 1.08),
        )
        lines.append(line)

    db_session.add_all(lines)
    db_session.flush()

    # Create tax components for each line
    tax_components = []
    for line, amount in zip(lines, amounts):
        tax_comp = QuoteLineTaxComponent(
            tenant_id=test_quote.tenant_id,
            quote_line_id=line.id,
            tax_rate_version_id=1,
            component_code="STATE",
            rate_pct=Decimal("8.0"),
            amount_cents=int(amount * 0.08),  # 8% tax
        )
        tax_components.append(tax_comp)

    db_session.add_all(tax_components)
    db_session.commit()
    db_session.refresh(test_quote)

    # Verify totals are sum of all lines
    expected_subtotal = 50000  # $500.00
    expected_tax = 4000  # $40.00 (8% of $500)
    expected_total = 54000  # $540.00

    assert test_quote.subtotal_cents == expected_subtotal
    assert test_quote.tax_cents == expected_tax
    assert test_quote.total_cents == expected_total


def test_quote_totals_handles_null_tax(
    db_session: Session, test_quote: Quote, test_line_type: QcoLineType
):
    """Test that trigger handles NULL tax_amount_cents (treats as 0)."""
    line = QuoteLine(
        tenant_id=test_quote.tenant_id,
        quote_id=test_quote.id,
        position=1,
        qco_line_type_id=test_line_type.id,
        description="No Tax Line",
        subtotal_cents=10000,
        tax_amount_cents=None,  # Explicitly NULL
        total_cents=10000,
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(test_quote)

    # COALESCE should treat NULL as 0
    assert test_quote.subtotal_cents == 10000
    assert test_quote.tax_cents == 0, "NULL tax should be treated as 0"
    assert test_quote.total_cents == 10000


def test_quote_totals_soft_delete_ignored(
    db_session: Session, test_quote: Quote, test_line_type: QcoLineType
):
    """Test that soft-deleted lines (is_active=false) are excluded from totals calculation."""
    # Create two lines
    line1 = QuoteLine(
        tenant_id=test_quote.tenant_id,
        quote_id=test_quote.id,
        position=1,
        qco_line_type_id=test_line_type.id,
        description="Active Line",
        subtotal_cents=10000,
    )
    line2 = QuoteLine(
        tenant_id=test_quote.tenant_id,
        quote_id=test_quote.id,
        position=2,
        qco_line_type_id=test_line_type.id,
        description="To Be Soft Deleted Line",
        subtotal_cents=5000,
    )
    db_session.add_all([line1, line2])
    db_session.flush()

    # Create tax components
    tax_comp1 = QuoteLineTaxComponent(
        tenant_id=test_quote.tenant_id,
        quote_line_id=line1.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("8.0"),
        amount_cents=800,
    )
    tax_comp2 = QuoteLineTaxComponent(
        tenant_id=test_quote.tenant_id,
        quote_line_id=line2.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("8.0"),
        amount_cents=400,
    )
    db_session.add_all([tax_comp1, tax_comp2])
    db_session.commit()
    db_session.refresh(test_quote)

    assert test_quote.subtotal_cents == 15000

    # Soft delete line2 by setting is_active = false
    line2.is_active = False
    db_session.commit()
    db_session.refresh(test_quote)

    # Trigger should exclude soft-deleted line
    assert test_quote.subtotal_cents == 10000, "Soft-deleted line should be excluded"
    assert test_quote.tax_cents == 800


def test_quote_totals_empty_quote(db_session: Session, test_quote: Quote):
    """Test that quote with no lines has totals = 0."""
    # Quote already created with no lines
    db_session.refresh(test_quote)

    # Should have zero totals (COALESCE handles empty SUM)
    assert test_quote.subtotal_cents == 0
    assert test_quote.tax_cents == 0
    assert test_quote.total_cents == 0


def test_quote_totals_updates_timestamp(
    db_session: Session, test_quote: Quote, test_line_type: QcoLineType
):
    """Test that trigger updates quote.updated_at timestamp."""
    # Store original timestamp as string for comparison
    original_updated_at = str(test_quote.updated_at)

    # Wait a moment to ensure timestamp difference
    import time

    time.sleep(0.01)

    # Add a line to trigger the update
    line = QuoteLine(
        tenant_id=test_quote.tenant_id,
        quote_id=test_quote.id,
        position=1,
        qco_line_type_id=test_line_type.id,
        description="Timestamp Test",
        subtotal_cents=1000,
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(test_quote)

    # Verify updated_at was changed (compare as strings to avoid timezone issues)
    assert str(test_quote.updated_at) != original_updated_at, (
        "updated_at should be refreshed"
    )


# ============================================================================
# Change Order Totals Trigger Tests
# ============================================================================


def test_change_order_totals_recalc_on_line_insert(
    db_session: Session, test_job: Job, test_line_type: QcoLineType
):
    """Test that change_order totals update when change_order_line is inserted."""
    # Create change order
    change_order = ChangeOrder(
        tenant_id=test_job.tenant_id,
        job_id=test_job.id,
        description="Test Change Order",
        subtotal_cents=0,
        tax_cents=0,
        total_cents=0,
    )
    db_session.add(change_order)
    db_session.commit()

    # Add line to change order
    line = ChangeOrderLine(
        tenant_id=test_job.tenant_id,
        change_order_id=change_order.id,
        position=1,
        qco_line_type_id=test_line_type.id,
        description="Change Order Line",
        subtotal_cents=8000,
        total_cents=8640,
    )
    db_session.add(line)
    db_session.flush()

    # Create tax component
    tax_comp = ChangeOrderLineTaxComponent(
        tenant_id=test_job.tenant_id,
        change_order_line_id=line.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("8.0"),
        amount_cents=640,
    )
    db_session.add(tax_comp)
    db_session.commit()
    db_session.refresh(change_order)

    # Verify trigger updated change order totals
    assert change_order.subtotal_cents == 8000
    assert change_order.tax_cents == 640
    assert change_order.total_cents == 8640


def test_change_order_totals_recalc_on_line_delete(
    db_session: Session, test_job: Job, test_line_type: QcoLineType
):
    """Test that change_order totals update when line is deleted."""
    change_order = ChangeOrder(
        tenant_id=test_job.tenant_id,
        job_id=test_job.id,
        description="Test CO",
        subtotal_cents=0,
        tax_cents=0,
        total_cents=0,
    )
    db_session.add(change_order)
    db_session.commit()

    # Add two lines
    line1 = ChangeOrderLine(
        tenant_id=test_job.tenant_id,
        change_order_id=change_order.id,
        position=1,
        qco_line_type_id=test_line_type.id,
        description="Line 1",
        subtotal_cents=5000,
    )
    line2 = ChangeOrderLine(
        tenant_id=test_job.tenant_id,
        change_order_id=change_order.id,
        position=2,
        qco_line_type_id=test_line_type.id,
        description="Line 2",
        subtotal_cents=3000,
    )
    db_session.add_all([line1, line2])
    db_session.flush()

    # Create tax components
    tax_comp1 = ChangeOrderLineTaxComponent(
        tenant_id=test_job.tenant_id,
        change_order_line_id=line1.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("8.0"),
        amount_cents=400,
    )
    tax_comp2 = ChangeOrderLineTaxComponent(
        tenant_id=test_job.tenant_id,
        change_order_line_id=line2.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("8.0"),
        amount_cents=240,
    )
    db_session.add_all([tax_comp1, tax_comp2])
    db_session.commit()
    db_session.refresh(change_order)

    assert change_order.subtotal_cents == 8000

    # Delete tax component first (FK constraint doesn't have CASCADE)
    db_session.delete(tax_comp2)
    db_session.flush()  # Flush to ensure tax component is deleted first
    # Then delete the line
    db_session.delete(line2)
    db_session.commit()
    db_session.refresh(change_order)

    # Verify totals updated
    assert change_order.subtotal_cents == 5000
    assert change_order.tax_cents == 400


def test_change_order_totals_soft_delete_ignored(
    db_session: Session, test_job: Job, test_line_type: QcoLineType
):
    """Test that soft-deleted change order lines (is_active=false) are excluded from totals."""
    # Create change order
    change_order = ChangeOrder(
        tenant_id=test_job.tenant_id,
        job_id=test_job.id,
        description="Test CO for Soft Delete",
        subtotal_cents=0,
        tax_cents=0,
        total_cents=0,
    )
    db_session.add(change_order)
    db_session.commit()

    # Create two lines
    line1 = ChangeOrderLine(
        tenant_id=test_job.tenant_id,
        change_order_id=change_order.id,
        position=1,
        qco_line_type_id=test_line_type.id,
        description="Active Line",
        subtotal_cents=10000,
    )
    line2 = ChangeOrderLine(
        tenant_id=test_job.tenant_id,
        change_order_id=change_order.id,
        position=2,
        qco_line_type_id=test_line_type.id,
        description="To Be Soft Deleted Line",
        subtotal_cents=5000,
    )
    db_session.add_all([line1, line2])
    db_session.flush()

    # Create tax components
    tax_comp1 = ChangeOrderLineTaxComponent(
        tenant_id=test_job.tenant_id,
        change_order_line_id=line1.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("8.0"),
        amount_cents=800,
    )
    tax_comp2 = ChangeOrderLineTaxComponent(
        tenant_id=test_job.tenant_id,
        change_order_line_id=line2.id,
        tax_rate_version_id=1,
        component_code="STATE",
        rate_pct=Decimal("8.0"),
        amount_cents=400,
    )
    db_session.add_all([tax_comp1, tax_comp2])
    db_session.commit()
    db_session.refresh(change_order)

    assert change_order.subtotal_cents == 15000

    # Soft delete line2 by setting is_active = false
    line2.is_active = False
    db_session.commit()
    db_session.refresh(change_order)

    # Trigger should exclude soft-deleted line
    assert change_order.subtotal_cents == 10000, "Soft-deleted line should be excluded"
    assert change_order.tax_cents == 800


# ============================================================================
# User Email Sync Trigger Tests
# ============================================================================


def test_user_email_sync_on_primary_endpoint_insert(
    db_session: Session, test_user: User
):
    """Test that user.email syncs when primary email endpoint is inserted."""
    original_email = test_user.email

    # Insert a primary email endpoint
    endpoint = UserEndpoint(
        user_id=test_user.id,
        channel="email",
        value="new-primary@example.com",
        is_primary=True,
        verification_status="verified",
    )
    db_session.add(endpoint)
    db_session.commit()
    db_session.refresh(test_user)

    # Verify trigger synced email (lowercased)
    assert test_user.email == "new-primary@example.com"


def test_user_email_sync_on_primary_endpoint_update(
    db_session: Session, test_user: User
):
    """Test that user.email syncs when primary endpoint value changes."""
    # Create initial primary endpoint
    endpoint = UserEndpoint(
        user_id=test_user.id,
        channel="email",
        value="initial@example.com",
        is_primary=True,
    )
    db_session.add(endpoint)
    db_session.commit()
    db_session.refresh(test_user)

    assert test_user.email == "initial@example.com"

    # Update the endpoint value
    endpoint.value = "updated@example.com"
    db_session.commit()
    db_session.refresh(test_user)

    # Verify email synced to new value
    assert test_user.email == "updated@example.com"


def test_user_email_no_sync_on_non_primary(db_session: Session, test_user: User):
    """Test that non-primary endpoints don't sync to user.email."""
    original_email = test_user.email

    # Insert non-primary endpoint
    endpoint = UserEndpoint(
        user_id=test_user.id,
        channel="email",
        value="secondary@example.com",
        is_primary=False,
    )
    db_session.add(endpoint)
    db_session.commit()
    db_session.refresh(test_user)

    # Email should not change
    assert test_user.email == original_email


def test_user_email_no_sync_on_sms_channel(db_session: Session, test_user: User):
    """Test that primary SMS endpoints don't sync to user.email."""
    original_email = test_user.email

    # Insert primary SMS endpoint (not email)
    endpoint = UserEndpoint(
        user_id=test_user.id,
        channel="sms",
        value="+15551234567",
        is_primary=True,
    )
    db_session.add(endpoint)
    db_session.commit()
    db_session.refresh(test_user)

    # Email should not change for SMS channel
    assert test_user.email == original_email


def test_user_email_sync_updates_timestamp(db_session: Session, test_user: User):
    """Test that email sync updates user.updated_at."""
    # Store original timestamp as string for comparison
    original_updated_at = str(test_user.updated_at)

    import time

    time.sleep(0.01)

    # Add primary email endpoint
    endpoint = UserEndpoint(
        user_id=test_user.id,
        channel="email",
        value="timestamp-test@example.com",
        is_primary=True,
    )
    db_session.add(endpoint)
    db_session.commit()
    db_session.refresh(test_user)

    # Verify timestamp updated (compare as strings to avoid timezone issues)
    assert str(test_user.updated_at) != original_updated_at


# ============================================================================
# Edge Cases & Integration Tests
# ============================================================================


def test_trigger_within_transaction_rollback(
    db_session: Session, test_quote: Quote, test_line_type: QcoLineType
):
    """Test that triggers respect transaction rollback."""
    # Begin nested transaction
    savepoint = db_session.begin_nested()

    try:
        # Add line within transaction
        line = QuoteLine(
            tenant_id=test_quote.tenant_id,
            quote_id=test_quote.id,
            position=1,
            qco_line_type_id=test_line_type.id,
            description="Rollback Test",
            subtotal_cents=99999,
            tax_amount_cents=7999,
        )
        db_session.add(line)
        db_session.flush()

        # Rollback the nested transaction
        savepoint.rollback()

        # Refresh quote
        db_session.refresh(test_quote)

        # Totals should still be 0 (rollback worked)
        assert test_quote.subtotal_cents == 0, "Rollback should revert trigger changes"
        assert test_quote.tax_cents == 0

    except Exception:
        savepoint.rollback()
        raise


def test_quote_totals_with_zero_amounts(
    db_session: Session, test_quote: Quote, test_line_type: QcoLineType
):
    """Test that trigger handles lines with zero amounts correctly."""
    line = QuoteLine(
        tenant_id=test_quote.tenant_id,
        quote_id=test_quote.id,
        position=1,
        qco_line_type_id=test_line_type.id,
        description="Zero Amount Line",
        subtotal_cents=0,
        tax_amount_cents=0,
        total_cents=0,
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(test_quote)

    # Should handle zero amounts gracefully
    assert test_quote.subtotal_cents == 0
    assert test_quote.tax_cents == 0
    assert test_quote.total_cents == 0
