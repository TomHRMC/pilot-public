"""
Test Phase 5.2 Exclusion Constraint Fixes

This module tests the specific constraint fixes made in Phase 5.2:
1. supplier_item_price.sip_no_overlap - COALESCE logic for NULL tenant_id
2. pricebook_item_version.piv_no_overlap - tenant_id parameter for multi-tenancy

Reference: dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md
"""

from datetime import UTC, datetime

import pytest
from psycopg2.extras import DateTimeTZRange
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.catalog import (
    Supplier,
    SupplierItem,
    SupplierItemCategory,
    SupplierItemPrice,
    SupplierItemUom,
)
from app.models.quoting import PricebookItem, PricebookItemVersion

UTC = UTC


# Note: test_tenant and second_tenant fixtures are already defined in conftest.py


@pytest.fixture
def supplier_item(db_session: Session):
    """Create a test supplier item"""
    # Create supplier
    supplier = Supplier(name="Test Supplier")
    db_session.add(supplier)
    db_session.commit()

    # Create category
    category = SupplierItemCategory(code="test-cat", name="Test Category")
    db_session.add(category)
    db_session.commit()

    # Create UOM
    uom = SupplierItemUom(code="ea", name="each")
    db_session.add(uom)
    db_session.commit()

    # Create supplier item
    item = SupplierItem(
        supplier_id=supplier.id,
        category_id=category.id,
        uom_id=uom.id,
        name="Test Item",
        sku="TEST-SKU-001",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def pricebook_item(db_session: Session, test_tenant):
    """Create a test pricebook item"""
    item = PricebookItem(
        tenant_id=test_tenant.id,
        sku="TEST-PB-001",
        name="Test Pricebook Item",
        description="Test Pricebook Item Description",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


class TestSupplierItemPriceNullTenantCoalesce:
    """
    Test Phase 5.2 Fix #1: supplier_item_price.sip_no_overlap COALESCE logic

    Before Fix: Two prices with NULL tenant_id could have overlapping periods
    After Fix: NULL values are treated as sentinel UUID for proper exclusion

    NOTE: DEPRECATED in Phase 6.0 Task 2 - Constraint simplified to prevent ALL overlaps
    regardless of tenant_id. See test_phase_6_0_task_2_indexes_exclusion.py for new behavior.
    """

    def test_null_tenant_overlapping_periods_rejected(
        self, db_session: Session, supplier_item
    ):
        """
        CRITICAL TEST: Two prices with NULL tenant_id and overlapping periods
        should be REJECTED by the sip_no_overlap constraint.

        This validates the COALESCE fix for NULL-safe comparison.
        """
        # Price 1: NULL tenant, 2024-01-01 to 2024-12-31
        price1 = SupplierItemPrice(
            tenant_id=None,  # NULL tenant (global pricing)
            supplier_item_id=supplier_item.id,
            unit_price=100.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(price1)
        db_session.commit()

        # Price 2: NULL tenant, 2024-06-01 to 2025-06-01 (OVERLAPS with Price 1)
        price2 = SupplierItemPrice(
            tenant_id=None,  # NULL tenant (global pricing)
            supplier_item_id=supplier_item.id,
            unit_price=110.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 6, 1, tzinfo=UTC), datetime(2025, 6, 1, tzinfo=UTC)
            ),
        )
        db_session.add(price2)

        # Should raise IntegrityError due to sip_no_overlap constraint
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # Verify it's the exclusion constraint (renamed in Phase 6.0 Task 2)
        assert "exclude_supplier_item_price_period_overlap" in str(exc_info.value)

    def test_null_tenant_non_overlapping_periods_allowed(
        self, db_session: Session, supplier_item
    ):
        """
        Two prices with NULL tenant_id and NON-overlapping periods
        should be ALLOWED.
        """
        # Price 1: NULL tenant, 2024-01-01 to 2024-06-30
        price1 = SupplierItemPrice(
            tenant_id=None,
            supplier_item_id=supplier_item.id,
            unit_price=100.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 6, 30, tzinfo=UTC)
            ),
        )
        db_session.add(price1)
        db_session.commit()

        # Price 2: NULL tenant, 2024-07-01 to 2024-12-31 (NO OVERLAP)
        price2 = SupplierItemPrice(
            tenant_id=None,
            supplier_item_id=supplier_item.id,
            unit_price=110.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 7, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(price2)
        db_session.commit()  # Should succeed

        # Verify both prices exist
        prices = db_session.exec(
            select(SupplierItemPrice).where(
                SupplierItemPrice.supplier_item_id == supplier_item.id
            )
        ).all()
        assert len(prices) == 2

    def test_null_vs_tenant_same_period_allowed(
        self, db_session: Session, test_tenant, supplier_item
    ):
        """
        One price with NULL tenant_id and another with a specific tenant_id
        can have the same period (different scopes).
        """
        # Price 1: NULL tenant, 2024
        price1 = SupplierItemPrice(
            tenant_id=None,
            supplier_item_id=supplier_item.id,
            unit_price=100.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(price1)
        db_session.commit()

        # Price 2: Specific tenant, same 2024 period
        price2 = SupplierItemPrice(
            tenant_id=test_tenant.id,
            supplier_item_id=supplier_item.id,
            unit_price=110.00,
            currency="USD",
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(price2)
        db_session.commit()  # Should succeed (different tenant scopes)

        # Verify both prices exist
        prices = db_session.exec(
            select(SupplierItemPrice).where(
                SupplierItemPrice.supplier_item_id == supplier_item.id
            )
        ).all()
        assert len(prices) == 2


class TestPricebookItemVersionTenantIsolation:
    """
    Test Phase 5.2 Fix #2: pricebook_item_version.piv_no_overlap tenant_id parameter

    Before Fix: Constraint lacked tenant_id, preventing cross-tenant overlaps
    After Fix: Constraint includes tenant_id for proper multi-tenancy isolation
    """

    def test_different_tenants_overlapping_periods_allowed(
        self, db_session: Session, test_tenant, second_tenant, pricebook_item
    ):
        """
        CRITICAL TEST: Two versions for DIFFERENT tenants with overlapping periods
        should be ALLOWED.

        This validates the tenant_id parameter was added to piv_no_overlap.
        """
        # Create pricebook item for second tenant
        pricebook_item2 = PricebookItem(
            tenant_id=second_tenant.id,
            sku="TEST-PB-002",
            name="Test Pricebook Item Tenant 2",
            description="Test Pricebook Item Tenant 2 Description",
        )
        db_session.add(pricebook_item2)
        db_session.commit()

        # Version 1: Tenant 1, 2024 pricing
        version1 = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=10000,
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(version1)
        db_session.commit()

        # Version 2: Tenant 2, SAME 2024 period (should be allowed - different tenant)
        version2 = PricebookItemVersion(
            tenant_id=second_tenant.id,
            pricebook_item_id=pricebook_item2.id,
            default_unit_price_cents=12000,
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(version2)
        db_session.commit()  # Should succeed (different tenants)

        # Verify both test-specific versions exist — filter by the two test item IDs
        # to avoid counting pre-existing pricebook_item_versions from seed scripts
        test_item_ids = [pricebook_item.id, pricebook_item2.id]
        versions = db_session.exec(
            select(PricebookItemVersion).where(
                PricebookItemVersion.pricebook_item_id.in_(test_item_ids)
            )
        ).all()
        assert len(versions) == 2

    def test_same_tenant_overlapping_periods_rejected(
        self, db_session: Session, test_tenant, pricebook_item
    ):
        """
        Two versions for the SAME tenant with overlapping periods
        should be REJECTED.
        """
        # Version 1: 2024 pricing
        version1 = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=10000,
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(version1)
        db_session.commit()

        # Version 2: Mid-2024 to 2025 (OVERLAPS with Version 1, SAME TENANT)
        version2 = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=12000,
            valid_period=DateTimeTZRange(
                datetime(2024, 6, 1, tzinfo=UTC), datetime(2025, 6, 1, tzinfo=UTC)
            ),
        )
        db_session.add(version2)

        # Should raise IntegrityError due to piv_no_overlap constraint
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "piv_no_overlap" in str(exc_info.value)

    def test_same_tenant_non_overlapping_periods_allowed(
        self, db_session: Session, test_tenant, pricebook_item
    ):
        """
        Two versions for the SAME tenant with NON-overlapping periods
        should be ALLOWED.
        """
        # Version 1: H1 2024
        version1 = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=10000,
            valid_period=DateTimeTZRange(
                datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 6, 30, tzinfo=UTC)
            ),
        )
        db_session.add(version1)
        db_session.commit()

        # Version 2: H2 2024 (adjacent, no overlap)
        version2 = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=12000,
            valid_period=DateTimeTZRange(
                datetime(2024, 7, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
            ),
        )
        db_session.add(version2)
        db_session.commit()  # Should succeed

        # Verify both versions exist
        versions = db_session.exec(
            select(PricebookItemVersion).where(
                PricebookItemVersion.pricebook_item_id == pricebook_item.id
            )
        ).all()
        assert len(versions) == 2
