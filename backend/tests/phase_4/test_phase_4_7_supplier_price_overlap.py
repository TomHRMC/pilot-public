"""
Test Suite: Phase 4.7 Task 7 - Supplier Item Price Overlap Prevention
Tests EXCLUDE constraint enforcement - final schema alignment for production deployment

Reference: phase-4.7-db-schema-sync-3-plan.md - Phase 4, Task 7
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.catalog import (
    Supplier,
    SupplierItem,
    SupplierItemCategory,
    SupplierItemPrice,
    SupplierItemUom,
    SupplierLifecycleStatus,
)
from app.models.core import Tenant


@pytest.fixture
def test_supplier_lifecycle_status(db_session: Session, test_tenant):
    """Create a test supplier lifecycle status"""
    status = SupplierLifecycleStatus(
        tenant_id=test_tenant.id,
        code="active",
        name="Active",
        is_default=True,
        is_active=True,
    )
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


@pytest.fixture
def test_supplier(db_session: Session, test_tenant, test_supplier_lifecycle_status):
    """Create a test supplier"""
    supplier = Supplier(
        tenant_id=test_tenant.id,
        name="Test Supplier",
        website="https://test-supplier.com",
        is_active=True,
        lifecycle_status_id=test_supplier_lifecycle_status.id,
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier


@pytest.fixture
def test_supplier_item_uom(db_session: Session, test_tenant):
    """Create a test unit of measure"""
    uom = SupplierItemUom(
        tenant_id=test_tenant.id,
        code="EA",
        name="Each",
        is_default=True,
        is_active=True,
    )
    db_session.add(uom)
    db_session.commit()
    db_session.refresh(uom)
    return uom


@pytest.fixture
def test_supplier_item_category(db_session: Session, test_tenant):
    """Create a test supplier item category"""
    category = SupplierItemCategory(
        tenant_id=test_tenant.id,
        code="ELECTRICAL",
        name="Electrical",
        is_active=True,
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def test_supplier_item(
    db_session: Session,
    test_tenant,
    test_supplier,
    test_supplier_item_uom,
    test_supplier_item_category,
):
    """Create a test supplier item"""
    item = SupplierItem(
        tenant_id=test_tenant.id,
        supplier_id=test_supplier.id,
        sku="SKU-TEST-001",
        name="Test Item",
        description="Test item for price overlap testing",
        uom_id=test_supplier_item_uom.id,
        category_id=test_supplier_item_category.id,
        is_active=True,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


class TestSupplierPriceOverlapPrevention:
    """Test EXCLUDE constraint prevents overlapping price date ranges"""

    def test_non_overlapping_adjacent_ranges_allowed(
        self, db_session: Session, test_tenant, test_supplier_item
    ):
        """Adjacent non-overlapping date ranges should be allowed"""
        # Price 1: 2024-01-01 to 2024-12-31
        price1 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price=100.00,
            currency="USD",
        )
        db_session.add(price1)
        db_session.commit()

        # Price 2: 2025-01-01 to 2025-12-31 (adjacent, no overlap)
        price2 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2025-01-01 00:00:00+00,2025-12-31 23:59:59+00]",
            unit_price=120.00,
            currency="USD",
        )
        db_session.add(price2)
        db_session.commit()  # Should succeed

        # Verify both exist
        prices = db_session.exec(
            select(SupplierItemPrice)
            .where(SupplierItemPrice.supplier_item_id == test_supplier_item.id)
            .order_by(SupplierItemPrice.id)
        ).all()
        assert len(prices) == 2

    def test_overlapping_ranges_rejected(
        self, db_session: Session, test_tenant, test_supplier_item
    ):
        """Overlapping date ranges for same supplier item + tenant should be rejected"""
        # Price 1: 2024-01-01 to 2024-12-31
        price1 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price=100.00,
            currency="USD",
        )
        db_session.add(price1)
        db_session.commit()

        # Price 2: 2024-06-01 to 2025-06-01 (overlaps with Price 1)
        price2 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2024-06-01 00:00:00+00,2025-06-01 23:59:59+00]",
            unit_price=120.00,
            currency="USD",
        )
        db_session.add(price2)

        # Should fail with exclusion constraint violation
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "exclude_supplier_item_price_period_overlap" in str(exc_info.value)

        db_session.rollback()

    def test_different_tenant_same_range_allowed(
        self, db_session: Session, test_tenant, test_supplier_item
    ):
        """Different tenants can have same supplier item with overlapping ranges

        NOTE: DEPRECATED - Phase 6.0 replaced sip_no_overlap with simpler constraint
        """
        # Create second tenant
        tenant2 = Tenant(name="Tenant 2", business_name="Tenant 2 LLC")
        db_session.add(tenant2)
        db_session.commit()

        # Price 1: Tenant 1, 2024-01-01 to 2024-12-31
        price1 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price=100.00,
            currency="USD",
        )
        db_session.add(price1)
        db_session.commit()

        # Price 2: Tenant 2, 2024-01-01 to 2024-12-31 (same range, different tenant)
        price2 = SupplierItemPrice(
            tenant_id=tenant2.id,
            supplier_item_id=test_supplier_item.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price=120.00,
            currency="USD",
        )
        db_session.add(price2)
        db_session.commit()  # Should succeed (different tenant)

        # Verify both exist
        prices = db_session.exec(
            select(SupplierItemPrice).where(
                SupplierItemPrice.supplier_item_id == test_supplier_item.id
            )
        ).all()
        assert len(prices) == 2

    def test_different_supplier_item_same_range_allowed(
        self,
        db_session: Session,
        test_tenant,
        test_supplier,
        test_supplier_item_uom,
        test_supplier_item_category,
    ):
        """Different supplier items can have overlapping ranges"""
        # Create two supplier items
        item1 = SupplierItem(
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            sku="SKU-001",
            name="Item 1",
            uom_id=test_supplier_item_uom.id,
            category_id=test_supplier_item_category.id,
            is_active=True,
        )
        item2 = SupplierItem(
            tenant_id=test_tenant.id,
            supplier_id=test_supplier.id,
            sku="SKU-002",
            name="Item 2",
            uom_id=test_supplier_item_uom.id,
            category_id=test_supplier_item_category.id,
            is_active=True,
        )
        db_session.add_all([item1, item2])
        db_session.commit()

        # Price 1: Item 1, 2024-01-01 to 2024-12-31
        price1 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=item1.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price=100.00,
            currency="USD",
        )
        db_session.add(price1)
        db_session.commit()

        # Price 2: Item 2, 2024-01-01 to 2024-12-31 (same range, different item)
        price2 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=item2.id,
            valid_period="[2024-01-01 00:00:00+00,2024-12-31 23:59:59+00]",
            unit_price=120.00,
            currency="USD",
        )
        db_session.add(price2)
        db_session.commit()  # Should succeed (different supplier item)

        # Verify both exist — scope to the two items created in this test
        prices = db_session.exec(
            select(SupplierItemPrice).where(
                SupplierItemPrice.supplier_item_id.in_([item1.id, item2.id])
            )
        ).all()
        assert len(prices) == 2
