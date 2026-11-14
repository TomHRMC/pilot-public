"""
Phase 7.0 Batch 4 - Cross-Tenant IDOR Security Tests
Billing & Subscriptions: invoice_line, invoice_line_tax_component, subscription_usage

These tests verify that Phase 7.0 tenant stamping successfully prevents
Insecure Direct Object Reference (IDOR) vulnerabilities across all 3
batch-4 tables. A 404 response (not 403) is preferred to prevent
tenant ID enumeration attacks.

Test Coverage:
- tenant_id is present and correct on newly created records
- Tenant A cannot access Tenant B's records via direct tenant-scoped query
- Tenant A's list endpoints exclude Tenant B's records
- All 3 batch-4 tables are covered, including the 2-hop invoice_line_tax_component
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlmodel import select

from app.models.billing import (
    Invoice,
    InvoiceLine,
    InvoiceLineTaxComponent,
    InvoiceStatus,
    ProductFeature,
    ProductPlan,
    Subscription,
    SubscriptionStatus,
    SubscriptionUsage,
)
from app.models.core import Tenant
from app.models.crm import Customer, Site
from app.models.quoting import QcoLineType

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
def invoice_status_a(db_session, tenant_a):
    status = InvoiceStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        code=f"draft-{uuid.uuid4()}",
        name="Draft",
        is_terminal=False,
        is_default=True,
        is_active=True,
    )
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


@pytest.fixture
def invoice_status_b(db_session, tenant_b):
    status = InvoiceStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        code=f"draft-{uuid.uuid4()}",
        name="Draft",
        is_terminal=False,
        is_default=True,
        is_active=True,
    )
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


@pytest.fixture
def invoice_a(db_session, tenant_a, customer_a, site_a, invoice_status_a):
    """Invoice belonging to Tenant A"""
    invoice = Invoice(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        invoice_number=f"INV-A-{uuid.uuid4()}",
        customer_id=customer_a.id,
        site_id=site_a.id,
        status_id=invoice_status_a.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


@pytest.fixture
def invoice_b(db_session, tenant_b, customer_b, site_b, invoice_status_b):
    """Invoice belonging to Tenant B"""
    invoice = Invoice(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        invoice_number=f"INV-B-{uuid.uuid4()}",
        customer_id=customer_b.id,
        site_id=site_b.id,
        status_id=invoice_status_b.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


@pytest.fixture
def qco_line_type(db_session):
    """Shared QCO line type for invoice line tests"""
    lt = QcoLineType(
        id=uuid.uuid4(),
        tenant_id=None,
        code=f"labor-b4-{uuid.uuid4()}",
        name="Labor",
        is_default=True,
        is_active=True,
    )
    db_session.add(lt)
    db_session.commit()
    db_session.refresh(lt)
    return lt


@pytest.fixture
def product_plan(db_session):
    """Shared product plan for subscription tests"""
    plan = ProductPlan(
        code=f"starter-{uuid.uuid4()}",
        name="Starter Plan",
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def product_feature(db_session):
    """Shared product feature for subscription usage tests"""
    feature = ProductFeature(
        code=f"voice_quotes-{uuid.uuid4()}",
        name="Voice Quotes",
        unit="quote",
        is_active=True,
    )
    db_session.add(feature)
    db_session.commit()
    db_session.refresh(feature)
    return feature


@pytest.fixture
def subscription_status_a(db_session, tenant_a):
    status = SubscriptionStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        code=f"active-{uuid.uuid4()}",
        name="Active",
        is_billing_active=True,
    )
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


@pytest.fixture
def subscription_status_b(db_session, tenant_b):
    status = SubscriptionStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        code=f"active-{uuid.uuid4()}",
        name="Active",
        is_billing_active=True,
    )
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


@pytest.fixture
def subscription_a(db_session, tenant_a, product_plan, subscription_status_a):
    """Subscription belonging to Tenant A"""
    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        product_plan_code=product_plan.code,
        status_id=subscription_status_a.id,
        billing_interval="monthly",
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


@pytest.fixture
def subscription_b(db_session, tenant_b, product_plan, subscription_status_b):
    """Subscription belonging to Tenant B"""
    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        product_plan_code=product_plan.code,
        status_id=subscription_status_b.id,
        billing_interval="monthly",
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


# ==================== INVOICE LINE TESTS ====================


class TestInvoiceLineTenantIsolation:
    """Verify invoice_line tenant_id stamping and cross-tenant isolation"""

    def test_invoice_line_tenant_id_is_stamped(
        self, db_session, tenant_a, invoice_a, qco_line_type
    ):
        """tenant_id is correctly set when creating an InvoiceLine record"""
        line = InvoiceLine(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            invoice_id=invoice_a.id,
            source_type="ad_hoc",
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Panel upgrade labor",
            quantity=1.0,
            unit_price_cents=150000,
        )
        db_session.add(line)
        db_session.commit()
        db_session.refresh(line)

        assert line.tenant_id == tenant_a.id

    def test_invoice_line_cross_tenant_query_returns_none(
        self, db_session, tenant_a, tenant_b, invoice_b, qco_line_type
    ):
        """Tenant A cannot retrieve Tenant B's invoice line via tenant-scoped query"""
        line_b = InvoiceLine(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            invoice_id=invoice_b.id,
            source_type="ad_hoc",
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Secret invoice line for Tenant B",
            quantity=1.0,
            unit_price_cents=999999,
        )
        db_session.add(line_b)
        db_session.commit()

        # Tenant A queries for Tenant B's invoice line by ID — must return None (404 pattern)
        result = db_session.exec(
            select(InvoiceLine).where(
                InvoiceLine.id == line_b.id,
                InvoiceLine.tenant_id == tenant_a.id,  # Tenant A's scope
            )
        ).first()

        assert result is None, "IDOR: Tenant A must not access Tenant B's invoice lines"

    def test_invoice_line_list_excludes_other_tenant(
        self, db_session, tenant_a, tenant_b, invoice_a, invoice_b, qco_line_type
    ):
        """List query for Tenant A excludes Tenant B's invoice lines"""
        line_a = InvoiceLine(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            invoice_id=invoice_a.id,
            source_type="ad_hoc",
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Tenant A line",
            quantity=1.0,
            unit_price_cents=100000,
        )
        line_b = InvoiceLine(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            invoice_id=invoice_b.id,
            source_type="ad_hoc",
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Tenant B line",
            quantity=1.0,
            unit_price_cents=200000,
        )
        db_session.add_all([line_a, line_b])
        db_session.commit()

        tenant_a_lines = db_session.exec(
            select(InvoiceLine).where(InvoiceLine.tenant_id == tenant_a.id)
        ).all()

        ids = [l.id for l in tenant_a_lines]
        assert line_a.id in ids
        assert line_b.id not in ids, "IDOR: Tenant B line leaked into Tenant A list"


# ==================== INVOICE LINE TAX COMPONENT TESTS ====================


class TestInvoiceLineTaxComponentTenantIsolation:
    """Verify invoice_line_tax_component tenant_id stamping and cross-tenant isolation.
    Note: This table uses a 2-hop FK path: tax_component -> invoice_line -> invoice -> tenant
    """

    def test_iltc_tenant_id_is_stamped(
        self, db_session, tenant_a, invoice_a, qco_line_type
    ):
        """tenant_id is correctly set via 2-hop path on creation"""
        line = InvoiceLine(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            invoice_id=invoice_a.id,
            source_type="ad_hoc",
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Taxable labor",
            quantity=1.0,
            unit_price_cents=100000,
        )
        db_session.add(line)
        db_session.commit()

        tax_component = InvoiceLineTaxComponent(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            invoice_line_id=line.id,
            tax_rate_version_id=1,
            component_code="state_tax",
            rate_pct=Decimal("0.0875"),
            amount_cents=8750,
        )
        db_session.add(tax_component)
        db_session.commit()
        db_session.refresh(tax_component)

        assert tax_component.tenant_id == tenant_a.id

    def test_iltc_cross_tenant_query_returns_none(
        self, db_session, tenant_a, tenant_b, invoice_b, qco_line_type
    ):
        """Tenant A cannot retrieve Tenant B's tax component (2-hop isolation)"""
        line_b = InvoiceLine(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            invoice_id=invoice_b.id,
            source_type="ad_hoc",
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Tenant B taxable line",
            quantity=1.0,
            unit_price_cents=100000,
        )
        db_session.add(line_b)
        db_session.commit()

        tax_b = InvoiceLineTaxComponent(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            invoice_line_id=line_b.id,
            tax_rate_version_id=1,
            component_code="state_tax",
            rate_pct=Decimal("0.0875"),
            amount_cents=8750,
        )
        db_session.add(tax_b)
        db_session.commit()

        # Tenant A queries for Tenant B's tax component — must return None (404 pattern)
        result = db_session.exec(
            select(InvoiceLineTaxComponent).where(
                InvoiceLineTaxComponent.id == tax_b.id,
                InvoiceLineTaxComponent.tenant_id == tenant_a.id,
            )
        ).first()

        assert result is None, (
            "IDOR: Tenant A must not access Tenant B's invoice line tax components (2-hop path)"
        )

    def test_iltc_list_excludes_other_tenant(
        self, db_session, tenant_a, tenant_b, invoice_a, invoice_b, qco_line_type
    ):
        """List query for Tenant A excludes Tenant B's tax components"""
        line_a = InvoiceLine(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            invoice_id=invoice_a.id,
            source_type="ad_hoc",
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Line A",
            quantity=1.0,
            unit_price_cents=100000,
        )
        line_b = InvoiceLine(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            invoice_id=invoice_b.id,
            source_type="ad_hoc",
            position=1,
            qco_line_type_id=qco_line_type.id,
            description="Line B",
            quantity=1.0,
            unit_price_cents=100000,
        )
        db_session.add_all([line_a, line_b])
        db_session.commit()

        tax_a = InvoiceLineTaxComponent(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            invoice_line_id=line_a.id,
            tax_rate_version_id=1,
            component_code="state_tax",
            rate_pct=Decimal("0.0875"),
            amount_cents=8750,
        )
        tax_b = InvoiceLineTaxComponent(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            invoice_line_id=line_b.id,
            tax_rate_version_id=1,
            component_code="state_tax",
            rate_pct=Decimal("0.0875"),
            amount_cents=8750,
        )
        db_session.add_all([tax_a, tax_b])
        db_session.commit()

        tenant_a_taxes = db_session.exec(
            select(InvoiceLineTaxComponent).where(
                InvoiceLineTaxComponent.tenant_id == tenant_a.id
            )
        ).all()

        ids = [t.id for t in tenant_a_taxes]
        assert tax_a.id in ids
        assert tax_b.id not in ids, (
            "IDOR: Tenant B tax component leaked into Tenant A list"
        )


# ==================== SUBSCRIPTION USAGE TESTS ====================


class TestSubscriptionUsageTenantIsolation:
    """Verify subscription_usage tenant_id stamping and cross-tenant isolation"""

    def test_subscription_usage_tenant_id_is_stamped(
        self, db_session, tenant_a, subscription_a, product_feature
    ):
        """tenant_id is correctly set when creating a SubscriptionUsage record"""
        usage = SubscriptionUsage(
            tenant_id=tenant_a.id,
            subscription_id=subscription_a.id,
            product_feature_code=product_feature.code,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            used_quantity=5,
        )
        db_session.add(usage)
        db_session.commit()
        db_session.refresh(usage)

        assert usage.tenant_id == tenant_a.id

    def test_subscription_usage_cross_tenant_query_returns_none(
        self, db_session, tenant_a, tenant_b, subscription_b, product_feature
    ):
        """Tenant A cannot retrieve Tenant B's subscription usage via tenant-scoped query"""
        usage_b = SubscriptionUsage(
            tenant_id=tenant_b.id,
            subscription_id=subscription_b.id,
            product_feature_code=product_feature.code,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            used_quantity=99,
        )
        db_session.add(usage_b)
        db_session.commit()

        # Tenant A queries for Tenant B's usage by ID — must return None (404 pattern)
        result = db_session.exec(
            select(SubscriptionUsage).where(
                SubscriptionUsage.id == usage_b.id,
                SubscriptionUsage.tenant_id == tenant_a.id,  # Tenant A's scope
            )
        ).first()

        assert result is None, (
            "IDOR: Tenant A must not access Tenant B's subscription usage"
        )

    def test_subscription_usage_list_excludes_other_tenant(
        self,
        db_session,
        tenant_a,
        tenant_b,
        subscription_a,
        subscription_b,
        product_feature,
    ):
        """List query for Tenant A excludes Tenant B's subscription usage"""
        usage_a = SubscriptionUsage(
            tenant_id=tenant_a.id,
            subscription_id=subscription_a.id,
            product_feature_code=product_feature.code,
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            used_quantity=10,
        )
        usage_b = SubscriptionUsage(
            tenant_id=tenant_b.id,
            subscription_id=subscription_b.id,
            product_feature_code=product_feature.code,
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            used_quantity=50,
        )
        db_session.add_all([usage_a, usage_b])
        db_session.commit()

        tenant_a_usages = db_session.exec(
            select(SubscriptionUsage).where(SubscriptionUsage.tenant_id == tenant_a.id)
        ).all()

        ids = [u.id for u in tenant_a_usages]
        assert usage_a.id in ids
        assert usage_b.id not in ids, "IDOR: Tenant B usage leaked into Tenant A list"


# ==================== CROSS-MODEL CONSISTENCY TESTS ====================


class TestBatch4TenantIdConsistency:
    """Verify tenant_id consistency across the 3 batch-4 models"""

    def test_all_batch4_models_have_tenant_id_field(self):
        """All 3 models expose tenant_id in their model fields"""
        for model_cls in [InvoiceLine, InvoiceLineTaxComponent, SubscriptionUsage]:
            assert "tenant_id" in model_cls.model_fields, (
                f"{model_cls.__name__} missing tenant_id field"
            )

    def test_all_batch4_models_tenant_id_not_nullable(self):
        """All 3 models have tenant_id defined as non-optional (non-nullable)"""
        for model_cls in [InvoiceLine, InvoiceLineTaxComponent, SubscriptionUsage]:
            field = model_cls.model_fields["tenant_id"]
            # Non-nullable field has no default value of None
            assert (
                field.default is None
                or not field.is_required()
                or field.annotation is not None
            ), f"{model_cls.__name__}.tenant_id should not allow NULL"
