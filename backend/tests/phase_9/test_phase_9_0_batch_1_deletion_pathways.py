"""
Phase 9.0 Batch 1 — Hard-Delete Lockdown Tests
Verifies that ON DELETE RESTRICT constraints prevent hard-deletion of parent
records when child financial/audit records exist.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.billing import (
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    PaymentStatus,
    ProductFeature,
    ProductPlan,
    Subscription,
    SubscriptionStatus,
    UsageLedger,
)
from app.models.quoting import (
    QcoLineType,
    QplContactActionType,
    Quote,
    QuoteLine,
    QuoteLinkStatus,
    QuoteMessage,
    QuotePublicLink,
    QuotePublicLinkContactAction,
    QuoteVersion,
)

# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_quote(db_session, test_tenant, test_customer, test_site, test_quote_status):
    """Return a persisted Quote."""
    q = Quote(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=test_quote_status.id,
        currency="USD",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    return q


@pytest.fixture
def test_quote_version_local(db_session, test_tenant, test_quote):
    """Return a persisted QuoteVersion linked to test_quote."""
    v = QuoteVersion(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        quote_id=test_quote.id,
        version_no=1,
        snapshot={},
        created_at=datetime.now(UTC),
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)
    return v


@pytest.fixture
def test_qco_line_type_local(db_session, test_tenant):
    """Return a persisted QcoLineType (idempotent)."""
    from sqlmodel import select

    existing = db_session.exec(
        select(QcoLineType).where(
            QcoLineType.tenant_id == test_tenant.id,
            QcoLineType.code == "material_p9",
        )
    ).first()
    if existing:
        return existing

    lt = QcoLineType(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="material_p9",
        name="Material P9",
        is_default=False,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(lt)
    db_session.commit()
    db_session.refresh(lt)
    return lt


@pytest.fixture
def test_quote_line(db_session, test_tenant, test_quote, test_qco_line_type_local):
    """Return a persisted QuoteLine."""
    ql = QuoteLine(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        quote_id=test_quote.id,
        position=1,
        qco_line_type_id=test_qco_line_type_local.id,
        description="Test line item",
        unit_price_cents=10000,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(ql)
    db_session.commit()
    db_session.refresh(ql)
    return ql


@pytest.fixture
def test_quote_message(db_session, test_tenant, test_quote):
    """Return a persisted QuoteMessage."""

    qm = QuoteMessage(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        quote_id=test_quote.id,
        action_type="system",
        message="Test message",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(qm)
    db_session.commit()
    db_session.refresh(qm)
    return qm


@pytest.fixture
def test_invoice_status_local(db_session, test_tenant):
    """Return a persisted InvoiceStatus."""
    from sqlmodel import select

    existing = db_session.exec(
        select(InvoiceStatus).where(
            InvoiceStatus.tenant_id == test_tenant.id,
            InvoiceStatus.code == "draft_p9",
        )
    ).first()
    if existing:
        return existing

    s = InvoiceStatus(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="draft_p9",
        name="Draft P9",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture
def test_invoice(
    db_session, test_tenant, test_customer, test_site, test_invoice_status_local
):
    """Return a persisted Invoice."""
    inv = Invoice(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=test_invoice_status_local.id,
        invoice_number=f"INV-P9-{uuid.uuid4().hex[:6].upper()}",
        currency="USD",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)
    return inv


@pytest.fixture
def test_invoice_line(db_session, test_tenant, test_invoice, test_qco_line_type_local):
    """Return a persisted InvoiceLine."""
    il = InvoiceLine(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        invoice_id=test_invoice.id,
        source_type="ad_hoc",
        position=1,
        qco_line_type_id=test_qco_line_type_local.id,
        description="Test invoice line",
        unit_price_cents=10000,
        created_at=datetime.now(UTC),
    )
    db_session.add(il)
    db_session.commit()
    db_session.refresh(il)
    return il


@pytest.fixture
def test_product_plan_local(db_session):
    """Return a persisted ProductPlan."""
    from sqlmodel import select

    existing = db_session.exec(
        select(ProductPlan).where(ProductPlan.code == "starter_p9")
    ).first()
    if existing:
        return existing

    pp = ProductPlan(
        code="starter_p9",
        name="Starter P9",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(pp)
    db_session.commit()
    db_session.refresh(pp)
    return pp


@pytest.fixture
def test_subscription_status_local(db_session, test_tenant):
    """Return a persisted SubscriptionStatus."""
    from sqlmodel import select

    existing = db_session.exec(
        select(SubscriptionStatus).where(
            SubscriptionStatus.tenant_id == test_tenant.id,
            SubscriptionStatus.code == "active_p9",
        )
    ).first()
    if existing:
        return existing

    ss = SubscriptionStatus(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="active_p9",
        name="Active P9",
        is_billing_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(ss)
    db_session.commit()
    db_session.refresh(ss)
    return ss


@pytest.fixture
def test_subscription(
    db_session, test_tenant, test_product_plan_local, test_subscription_status_local
):
    """Return a persisted Subscription."""
    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        product_plan_code=test_product_plan_local.code,
        status_id=test_subscription_status_local.id,
        billing_interval="monthly",
        started_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


@pytest.fixture
def test_product_feature_local(db_session):
    """Return a persisted ProductFeature."""
    from sqlmodel import select

    existing = db_session.exec(
        select(ProductFeature).where(ProductFeature.code == "quotes_p9")
    ).first()
    if existing:
        return existing

    pf = ProductFeature(
        code="quotes_p9",
        name="Quotes P9",
        unit="count",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(pf)
    db_session.commit()
    db_session.refresh(pf)
    return pf


@pytest.fixture
def test_usage_ledger(
    db_session, test_tenant, test_subscription, test_product_feature_local
):
    """Return a persisted UsageLedger entry."""
    ul = UsageLedger(
        tenant_id=test_tenant.id,
        subscription_id=test_subscription.id,
        product_feature_code=test_product_feature_local.code,
        quantity=1.0,
        idempotency_key=f"p9-test-{uuid.uuid4().hex}",
        occurred_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(ul)
    db_session.commit()
    db_session.refresh(ul)
    return ul


@pytest.fixture
def test_quote_link_status_local(db_session, test_tenant):
    """Return a persisted QuoteLinkStatus."""
    from sqlmodel import select

    existing = db_session.exec(
        select(QuoteLinkStatus).where(
            QuoteLinkStatus.tenant_id == test_tenant.id,
            QuoteLinkStatus.code == "active_p9",
        )
    ).first()
    if existing:
        return existing

    qls = QuoteLinkStatus(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="active_p9",
        name="Active P9",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(qls)
    db_session.commit()
    db_session.refresh(qls)
    return qls


@pytest.fixture
def test_quote_public_link(
    db_session, test_tenant, test_quote, test_contact, test_quote_link_status_local
):
    """Return a persisted QuotePublicLink."""
    qpl = QuotePublicLink(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        quote_id=test_quote.id,
        contact_id=test_contact.id,
        token_hash=f"tok_{uuid.uuid4().hex}",
        status_id=test_quote_link_status_local.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(qpl)
    db_session.commit()
    db_session.refresh(qpl)
    return qpl


@pytest.fixture
def test_qpl_contact_action_type_local(db_session, test_tenant):
    """Return a persisted QplContactActionType."""
    from sqlmodel import select

    existing = db_session.exec(
        select(QplContactActionType).where(
            QplContactActionType.tenant_id == test_tenant.id,
            QplContactActionType.code == "view_p9",
        )
    ).first()
    if existing:
        return existing

    cat = QplContactActionType(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="view_p9",
        name="View P9",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.fixture
def test_quote_public_link_contact_action(
    db_session,
    test_tenant,
    test_quote,
    test_quote_public_link,
    test_contact,
    test_qpl_contact_action_type_local,
):
    """Return a persisted QuotePublicLinkContactAction."""
    action = QuotePublicLinkContactAction(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        quote_id=test_quote.id,
        contact_id=test_contact.id,
        qpl_contact_action_type_id=test_qpl_contact_action_type_local.id,
        occurred_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(action)
    db_session.commit()
    db_session.refresh(action)
    return action


# ---------------------------------------------------------------------------
# Tests — quote table
# ---------------------------------------------------------------------------


def test_tenant_hard_delete_blocked_by_quote(db_session, test_tenant, test_quote):
    """Deleting a tenant with an associated quote must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_customer_hard_delete_blocked_by_quote(
    db_session, test_tenant, test_customer, test_quote
):
    """Deleting a customer with an associated quote must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_customer)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests — quote_version table
# ---------------------------------------------------------------------------


def test_quote_hard_delete_blocked_by_quote_version(
    db_session, test_quote, test_quote_version_local
):
    """Deleting a quote with a version must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_quote)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests — quote_line table
# ---------------------------------------------------------------------------


def test_quote_hard_delete_blocked_by_quote_line(
    db_session, test_quote, test_quote_line
):
    """Deleting a quote with a line must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_quote)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests — quote_message table
# ---------------------------------------------------------------------------


def test_quote_hard_delete_blocked_by_quote_message(
    db_session, test_quote, test_quote_message
):
    """Deleting a quote with a message must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_quote)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_tenant_hard_delete_blocked_by_quote_message(
    db_session, test_tenant, test_quote, test_quote_message
):
    """Deleting a tenant with a quote_message must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests — invoice table
# ---------------------------------------------------------------------------


def test_tenant_hard_delete_blocked_by_invoice(db_session, test_tenant, test_invoice):
    """Deleting a tenant with an invoice must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_customer_hard_delete_blocked_by_invoice(
    db_session, test_customer, test_invoice
):
    """Deleting a customer with an invoice must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_customer)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests — invoice_line table
# ---------------------------------------------------------------------------


def test_invoice_hard_delete_blocked_by_invoice_line(
    db_session, test_invoice, test_invoice_line
):
    """Deleting an invoice with lines must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_invoice)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_tenant_hard_delete_blocked_by_invoice_line(
    db_session, test_tenant, test_invoice, test_invoice_line
):
    """Deleting a tenant with invoice_line rows must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests — subscription table
# ---------------------------------------------------------------------------


def test_tenant_hard_delete_blocked_by_subscription(
    db_session, test_tenant, test_subscription
):
    """Deleting a tenant with a subscription must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests — usage_ledger table
# ---------------------------------------------------------------------------


def test_tenant_hard_delete_blocked_by_usage_ledger(
    db_session, test_tenant, test_usage_ledger
):
    """Deleting a tenant with ledger entries must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_subscription_hard_delete_blocked_by_usage_ledger(
    db_session, test_subscription, test_usage_ledger
):
    """Deleting a subscription with ledger entries must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_subscription)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests — quote_public_link table
# ---------------------------------------------------------------------------


def test_tenant_hard_delete_blocked_by_quote_public_link(
    db_session, test_tenant, test_quote_public_link
):
    """Deleting a tenant with a quote_public_link must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests — quote_public_link_contact_action table
# ---------------------------------------------------------------------------


def test_tenant_hard_delete_blocked_by_qpl_contact_action(
    db_session, test_tenant, test_quote_public_link_contact_action
):
    """Deleting a tenant with qpl_contact_action rows must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests — quote_status lookup (tenant-scoped)
# ---------------------------------------------------------------------------


def test_tenant_hard_delete_blocked_by_quote_status(
    db_session, test_tenant, test_quote_status
):
    """Deleting a tenant with a quote_status must raise IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests — payment_status lookup (tenant-scoped)
# ---------------------------------------------------------------------------


def test_tenant_hard_delete_blocked_by_payment_status(db_session, test_tenant):
    """Deleting a tenant with a payment_status must raise IntegrityError (RESTRICT)."""
    from sqlmodel import select

    pay_status = db_session.exec(
        select(PaymentStatus).where(PaymentStatus.tenant_id == test_tenant.id)
    ).first()
    if not pay_status:
        pay_status = PaymentStatus(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            code="pending_p9",
            name="Pending P9",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(pay_status)
        db_session.commit()

    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
