"""
Test Suite: Phase 3 Task 10 - Temporal Exclusion Constraints
Tests temporal exclusion constraints from Golden Master v2.6h
Prevents overlapping date ranges in versioned tables.

Authority: dev-docs/db-design/aevofab-db-schema-v2.6h.json
Task: Phase 4.5 Task 10 - Missing Temporal Exclusion Constraints
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from psycopg2.extras import DateTimeTZRange
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.models.billing import (
    ProductFeature,
    ProductPlan,
    ProductPlanProductFeatureVersion,
    ProductPlanVersion,
)
from app.models.catalog import (
    SupplierItem,
    SupplierItemPrice,
    TaxRateVersion,
    TenantMarkupVersion,
)
from app.models.fulfillment import JobExpenseCategory
from app.models.quoting import PricebookItem, PricebookItemVersion

# ==================== FIXTURES ====================


@pytest.fixture
def job_expense_category(db_session):
    """Create a job expense category for testing"""
    category = JobExpenseCategory(
        code="MAT",
        name="Materials",
        description="Material costs",
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def supplier_item(db_session, test_tenant, test_supplier):
    """Create a supplier item for testing"""
    from app.models.catalog import SupplierItemUom

    # Create UOM if needed
    uom = db_session.exec(
        select(SupplierItemUom).where(SupplierItemUom.code == "EA")
    ).first()
    if not uom:
        uom = SupplierItemUom(
            code="EA",
            name="Each",
            symbol="ea",
        )
        db_session.add(uom)
        db_session.commit()
        db_session.refresh(uom)

    item = SupplierItem(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        supplier_id=test_supplier.id,
        sku="TEST-SKU-001",
        name="Test Item",
        base_uom_code="EA",
        uom_id=uom.id,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def pricebook_item(db_session, test_tenant):
    """Create a pricebook item for testing"""
    item = PricebookItem(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        sku="PB-TEST-001",
        name="Test Pricebook Item",
        description="Test item for pricebook",
        is_active=True,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def product_plan(db_session):
    """Create a product plan for testing"""
    plan = ProductPlan(
        code="BASIC",
        name="Basic Plan",
        description="Basic subscription plan",
        billing_period="month",
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def product_feature(db_session):
    """Create a product feature for testing"""
    feature = ProductFeature(
        code="VOICE_QUOTE",
        name="Voice Quoting",
        unit="quotes",
        description="Voice-powered quote generation",
        is_active=True,
    )
    db_session.add(feature)
    db_session.commit()
    db_session.refresh(feature)
    return feature


# ==================== TENANT_MARKUP_VERSION TESTS ====================


class TestTenantMarkupVersionTemporalExclusion:
    """Test temporal exclusion constraint on tenant_markup_version"""

    def test_non_overlapping_versions_allowed(
        self, db_session, test_tenant, job_expense_category
    ):
        """Non-overlapping date ranges should be accepted"""

        # Version 1: Jan 1 - Dec 31, 2024
        v1 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            job_expense_category_code=job_expense_category.code,
            markup_pct=Decimal("0.2000"),  # 20%
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: Jan 1, 2025 onwards (no overlap)
        v2 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            job_expense_category_code=job_expense_category.code,
            markup_pct=Decimal("0.2500"),  # 25%
            valid_period=DateTimeTZRange(
                datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)
        db_session.commit()  # Should succeed

        # Verify both this test's rows exist — scope by ID to avoid counting
        # pre-existing seed data for this tenant.
        inserted_ids = {v1.id, v2.id}
        result = db_session.exec(
            select(TenantMarkupVersion).where(TenantMarkupVersion.id.in_(inserted_ids))
        ).all()
        assert len(result) == 2

    def test_overlapping_versions_rejected(
        self, db_session, test_tenant, job_expense_category
    ):
        """Overlapping date ranges should be rejected"""

        # Version 1: Jan 1 - Dec 31, 2024
        v1 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            job_expense_category_code=job_expense_category.code,
            markup_pct=Decimal("0.2000"),
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: Jun 1, 2024 - Jun 1, 2025 (OVERLAPS with v1)
        v2 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            job_expense_category_code=job_expense_category.code,
            markup_pct=Decimal("0.2500"),
            valid_period=DateTimeTZRange(
                datetime(2024, 6, 1, tzinfo=UTC), datetime(2025, 6, 1, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert (
            "tmv_no_overlap" in str(exc_info.value)
            or "exclusion" in str(exc_info.value).lower()
        )

    def test_adjacent_ranges_allowed(
        self, db_session, test_tenant, job_expense_category
    ):
        """Adjacent but non-overlapping ranges should be allowed"""

        # Version 1: Jan 1 - Jun 30, 2024
        v1 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            job_expense_category_code=job_expense_category.code,
            markup_pct=Decimal("0.2000"),
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 6, 30, 23, 59, 59, tzinfo=UTC),
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: Jul 1, 2024 onwards (adjacent, no overlap due to range semantics)
        v2 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            job_expense_category_code=job_expense_category.code,
            markup_pct=Decimal("0.2500"),
            valid_period=DateTimeTZRange(
                datetime(2024, 7, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)
        db_session.commit()  # Should succeed

        # Verify both this test's rows exist — scope by ID to avoid counting
        # pre-existing seed data for this tenant.
        inserted_ids = {v1.id, v2.id}
        result = db_session.exec(
            select(TenantMarkupVersion).where(TenantMarkupVersion.id.in_(inserted_ids))
        ).all()
        assert len(result) == 2


# ==================== SUPPLIER_ITEM_PRICE TESTS ====================


class TestSupplierItemPriceTemporalExclusion:
    """Test temporal exclusion constraint on supplier_item_price"""

    def test_non_overlapping_prices_allowed(
        self, db_session, test_tenant, supplier_item
    ):
        """Non-overlapping price periods should be accepted"""

        # Price 1: Jan 1 - Jun 30, 2024
        p1 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=supplier_item.id,
            unit_price=100.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 6, 30, tzinfo=UTC)
            ),
        )
        db_session.add(p1)
        db_session.commit()

        # Price 2: Jul 1, 2024 onwards (no overlap)
        p2 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=supplier_item.id,
            unit_price=110.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 7, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(p2)
        db_session.commit()

        result = db_session.exec(
            select(SupplierItemPrice).where(
                SupplierItemPrice.supplier_item_id == supplier_item.id
            )
        ).all()
        assert len(result) == 2

    def test_overlapping_prices_rejected(self, db_session, test_tenant, supplier_item):
        """Overlapping price periods should be rejected"""

        # Price 1: Jan 1 - Dec 31, 2024
        p1 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=supplier_item.id,
            unit_price=100.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(p1)
        db_session.commit()

        # Price 2: Jun 1, 2024 - Jun 1, 2025 (OVERLAPS)
        p2 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=supplier_item.id,
            unit_price=110.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 6, 1, tzinfo=UTC), datetime(2025, 6, 1, tzinfo=UTC)
            ),
        )
        db_session.add(p2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert (
            "sip_no_overlap_per_tenant" in str(exc_info.value)
            or "exclusion" in str(exc_info.value).lower()
        )

    def test_different_tenants_same_ranges_allowed(
        self, db_session, test_tenant, second_tenant, supplier_item
    ):
        """Different tenants can have same date ranges

        NOTE: DEPRECATED - Phase 6.0 replaced per-tenant constraint with simpler global constraint
        """

        # Tenant 1 price
        p1 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=supplier_item.id,
            unit_price=100.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(p1)
        db_session.commit()

        # Tenant 2 price (same date range, should be allowed)
        p2 = SupplierItemPrice(
            tenant_id=second_tenant.id,
            supplier_item_id=supplier_item.id,
            unit_price=105.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(p2)
        db_session.commit()  # Should succeed

        result = db_session.exec(
            select(SupplierItemPrice).where(
                SupplierItemPrice.supplier_item_id == supplier_item.id
            )
        ).all()
        assert len(result) == 2


# ==================== TAX_RATE_VERSION TESTS ====================


class TestTaxRateVersionTemporalExclusion:
    """Test temporal exclusion constraint on tax_rate_version"""

    def test_non_overlapping_tax_versions_allowed(self, db_session):
        """Non-overlapping tax rate versions should be accepted"""

        # Version 1: 2024 rate
        v1 = TaxRateVersion(
            jurisdiction_code="US-CA-06001",
            description="California State Tax 2024",
            rate_pct=Decimal("7.2500"),
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: 2025 rate (no overlap)
        v2 = TaxRateVersion(
            jurisdiction_code="US-CA-06001",
            description="California State Tax 2025",
            rate_pct=Decimal("7.5000"),
            valid_period=DateTimeTZRange(
                datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)
        db_session.commit()

        result = db_session.exec(
            select(TaxRateVersion).where(
                TaxRateVersion.jurisdiction_code == "US-CA-06001"
            )
        ).all()
        assert len(result) == 2

    def test_overlapping_tax_versions_rejected(self, db_session):
        """Overlapping tax rate versions should be rejected"""

        # Version 1: Full year 2024
        v1 = TaxRateVersion(
            jurisdiction_code="US-CA-06001",
            description="California State Tax 2024",
            rate_pct=Decimal("7.2500"),
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: Mid-2024 to mid-2025 (OVERLAPS)
        v2 = TaxRateVersion(
            jurisdiction_code="US-CA-06001",
            description="California State Tax Mid-Year",
            rate_pct=Decimal("7.5000"),
            valid_period=DateTimeTZRange(
                datetime(2024, 6, 1, tzinfo=UTC), datetime(2025, 6, 1, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert (
            "tax_rate_version_no_overlap" in str(exc_info.value)
            or "exclusion" in str(exc_info.value).lower()
        )

    def test_adjacent_tax_rates_allowed(self, db_session):
        """Adjacent tax rate periods should be allowed"""

        # Version 1: H1 2024
        v1 = TaxRateVersion(
            jurisdiction_code="US-CA-06001",
            description="California State Tax H1 2024",
            rate_pct=Decimal("7.2500"),
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 6, 30, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: H2 2024 (adjacent)
        v2 = TaxRateVersion(
            jurisdiction_code="US-CA-06001",
            description="California State Tax H2 2024",
            rate_pct=Decimal("7.5000"),
            valid_period=DateTimeTZRange(
                datetime(2024, 7, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)
        db_session.commit()

        result = db_session.exec(
            select(TaxRateVersion).where(
                TaxRateVersion.jurisdiction_code == "US-CA-06001"
            )
        ).all()
        assert len(result) == 2


# ==================== PRICEBOOK_ITEM_VERSION TESTS ====================


class TestPricebookItemVersionTemporalExclusion:
    """Test temporal exclusion constraint on pricebook_item_version"""

    def test_non_overlapping_pricebook_versions_allowed(
        self, db_session, test_tenant, pricebook_item
    ):
        """Non-overlapping pricebook versions should be accepted"""

        # Version 1: 2024 pricing
        v1 = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=10000,  # $100.00
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: 2025 pricing (no overlap)
        v2 = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=11000,  # $110.00
            valid_period=DateTimeTZRange(
                datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)
        db_session.commit()

        result = db_session.exec(
            select(PricebookItemVersion).where(
                PricebookItemVersion.pricebook_item_id == pricebook_item.id
            )
        ).all()
        assert len(result) == 2

    def test_overlapping_pricebook_versions_rejected(
        self, db_session, test_tenant, pricebook_item
    ):
        """Overlapping pricebook versions should be rejected"""

        # Version 1: Full 2024
        v1 = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=10000,
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: Mid-2024 to 2025 (OVERLAPS)
        v2 = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=11000,
            valid_period=DateTimeTZRange(
                datetime(2024, 6, 1, tzinfo=UTC), datetime(2025, 6, 1, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert (
            "piv_no_overlap" in str(exc_info.value)
            or "exclusion" in str(exc_info.value).lower()
        )

    def test_adjacent_pricebook_versions_allowed(
        self, db_session, test_tenant, pricebook_item
    ):
        """Adjacent pricebook versions should be allowed"""

        # Version 1: H1 2024
        v1 = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=10000,
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 6, 30, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: H2 2024 (adjacent)
        v2 = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=10500,
            valid_period=DateTimeTZRange(
                datetime(2024, 7, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)
        db_session.commit()

        result = db_session.exec(
            select(PricebookItemVersion).where(
                PricebookItemVersion.pricebook_item_id == pricebook_item.id
            )
        ).all()
        assert len(result) == 2


# ==================== PRODUCT_PLAN_VERSION TESTS ====================


class TestProductPlanVersionTemporalExclusion:
    """Test temporal exclusion constraint on product_plan_version"""

    def test_non_overlapping_plan_versions_allowed(self, db_session, product_plan):
        """Non-overlapping plan versions should be accepted"""

        # Version 1: 2024 pricing
        v1 = ProductPlanVersion(
            product_plan_code=product_plan.code,
            name="Basic Plan 2024",
            price_cents=4900,  # $49.00/month
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: 2025 pricing (no overlap)
        v2 = ProductPlanVersion(
            product_plan_code=product_plan.code,
            name="Basic Plan 2025",
            price_cents=5900,  # $59.00/month
            valid_period=DateTimeTZRange(
                datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)
        db_session.commit()

        result = db_session.exec(
            select(ProductPlanVersion).where(
                ProductPlanVersion.product_plan_code == product_plan.code
            )
        ).all()
        assert len(result) == 2

    def test_overlapping_plan_versions_rejected(self, db_session, product_plan):
        """Overlapping plan versions should be rejected"""

        # Version 1: Full 2024
        v1 = ProductPlanVersion(
            product_plan_code=product_plan.code,
            name="Basic Plan 2024",
            price_cents=4900,
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: Mid-2024 to 2025 (OVERLAPS)
        v2 = ProductPlanVersion(
            product_plan_code=product_plan.code,
            name="Basic Plan Mid-Year",
            price_cents=5400,
            valid_period=DateTimeTZRange(
                datetime(2024, 6, 1, tzinfo=UTC), datetime(2025, 6, 1, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert (
            "product_plan_version_no_overlap" in str(exc_info.value)
            or "exclusion" in str(exc_info.value).lower()
        )

    def test_adjacent_plan_versions_allowed(self, db_session, product_plan):
        """Adjacent plan versions should be allowed"""

        # Version 1: H1 2024
        v1 = ProductPlanVersion(
            product_plan_code=product_plan.code,
            name="Basic Plan H1 2024",
            price_cents=4900,
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 6, 30, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: H2 2024 (adjacent)
        v2 = ProductPlanVersion(
            product_plan_code=product_plan.code,
            name="Basic Plan H2 2024",
            price_cents=5400,
            valid_period=DateTimeTZRange(
                datetime(2024, 7, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
        )
        db_session.add(v2)
        db_session.commit()

        result = db_session.exec(
            select(ProductPlanVersion).where(
                ProductPlanVersion.product_plan_code == product_plan.code
            )
        ).all()
        assert len(result) == 2


# ==================== PRODUCT_PLAN_PRODUCT_FEATURE_VERSION TESTS ====================


class TestProductPlanProductFeatureVersionTemporalExclusion:
    """Test temporal exclusion constraint on product_plan_product_feature_version"""

    def test_non_overlapping_feature_versions_allowed(
        self, db_session, product_plan, product_feature
    ):
        """Non-overlapping feature versions should be accepted"""

        # Version 1: 2024 limits
        v1 = ProductPlanProductFeatureVersion(
            product_plan_code=product_plan.code,
            product_feature_code=product_feature.code,
            limit_quantity=100,
            included_quantity=50,
            overage_price_cents=100,
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
            limit_enforcement="block",
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: 2025 limits (no overlap)
        v2 = ProductPlanProductFeatureVersion(
            product_plan_code=product_plan.code,
            product_feature_code=product_feature.code,
            limit_quantity=200,
            included_quantity=100,
            overage_price_cents=80,
            valid_period=DateTimeTZRange(
                datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
            limit_enforcement="block",
        )
        db_session.add(v2)
        db_session.commit()

        result = db_session.exec(
            select(ProductPlanProductFeatureVersion).where(
                ProductPlanProductFeatureVersion.product_plan_code == product_plan.code,
                ProductPlanProductFeatureVersion.product_feature_code
                == product_feature.code,
            )
        ).all()
        assert len(result) == 2

    def test_overlapping_feature_versions_rejected(
        self, db_session, product_plan, product_feature
    ):
        """Overlapping feature versions should be rejected"""

        # Version 1: Full 2024
        v1 = ProductPlanProductFeatureVersion(
            product_plan_code=product_plan.code,
            product_feature_code=product_feature.code,
            limit_quantity=100,
            included_quantity=50,
            overage_price_cents=100,
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
            limit_enforcement="block",
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: Mid-2024 to 2025 (OVERLAPS)
        v2 = ProductPlanProductFeatureVersion(
            product_plan_code=product_plan.code,
            product_feature_code=product_feature.code,
            limit_quantity=150,
            included_quantity=75,
            overage_price_cents=90,
            valid_period=DateTimeTZRange(
                datetime(2024, 6, 1, tzinfo=UTC), datetime(2025, 6, 1, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
            limit_enforcement="block",
        )
        db_session.add(v2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert (
            "pppfv_no_overlap" in str(exc_info.value)
            or "exclusion" in str(exc_info.value).lower()
        )

    def test_adjacent_feature_versions_allowed(
        self, db_session, product_plan, product_feature
    ):
        """Adjacent feature versions should be allowed"""

        # Version 1: H1 2024
        v1 = ProductPlanProductFeatureVersion(
            product_plan_code=product_plan.code,
            product_feature_code=product_feature.code,
            limit_quantity=100,
            included_quantity=50,
            overage_price_cents=100,
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 6, 30, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
            limit_enforcement="block",
        )
        db_session.add(v1)
        db_session.commit()

        # Version 2: H2 2024 (adjacent)
        v2 = ProductPlanProductFeatureVersion(
            product_plan_code=product_plan.code,
            product_feature_code=product_feature.code,
            limit_quantity=120,
            included_quantity=60,
            overage_price_cents=90,
            valid_period=DateTimeTZRange(
                datetime(2024, 7, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
            recorded_at=datetime.now(UTC),
            limit_enforcement="block",
        )
        db_session.add(v2)
        db_session.commit()

        result = db_session.exec(
            select(ProductPlanProductFeatureVersion).where(
                ProductPlanProductFeatureVersion.product_plan_code == product_plan.code,
                ProductPlanProductFeatureVersion.product_feature_code
                == product_feature.code,
            )
        ).all()
        assert len(result) == 2
