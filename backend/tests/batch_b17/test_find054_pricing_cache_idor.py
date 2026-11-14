"""
FIND-054 (S1 Critical) — Pricing cache IDOR fix: tenant_id filter on _get_pricing_cache_impl.

Verifies that the IDOR vulnerability is closed: `_get_pricing_cache_impl` now returns
only global rows (tenant_id IS NULL) and the requesting tenant's private rows, ordered
with tenant-specific rows first (tenant_id NULLS LAST).

Before the fix: ALL tenants' private pricing was returned to every caller.
After the fix:  Each tenant sees only their own private prices + shared global prices.

Test plan from remediation plan FIND-054:
  - Tenant A gets global $1.00 row + their own $0.90 row; tenant-specific first
  - Tenant B gets only the global $1.00 row — NOT Tenant A's $0.90 private rate
  - New tenant with no private prices gets only global rows

Test subfolder: tests/batch_b17/
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from api.routes.catalog import _get_pricing_cache_impl
from app.models.catalog import PricingCache, Supplier
from app.models.core import Tenant
from core.test_context import TestUserContext as UserContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_tenant(db: Session, name: str) -> Tenant:
    from sqlmodel import select

    from app.models.subscription import SubscriptionTier

    tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
    ).first()
    assert tier is not None, "Trial tier not seeded — run alembic upgrade head"

    tenant = Tenant(
        id=uuid.uuid4(),
        name=name,
        is_active=True,
        current_subscription_tier_id=tier.tier_id,
    )
    db.add(tenant)
    db.flush()
    return tenant


def _create_supplier(db: Session) -> Supplier:
    from sqlmodel import select

    from app.models.catalog import SupplierLifecycleStatus

    status = db.exec(select(SupplierLifecycleStatus).limit(1)).first()
    supplier = Supplier(
        id=uuid.uuid4(),
        name=f"Supplier-{uuid.uuid4().hex[:6]}",
        lifecycle_status_id=status.id if status else None,
    )
    db.add(supplier)
    db.flush()
    return supplier


def _create_pricing_cache(
    db: Session,
    supplier: Supplier,
    sku: str,
    price_cents: int,
    tenant_id=None,
) -> PricingCache:
    cache = PricingCache(
        supplier_id=supplier.id,
        sku=sku,
        price_cents=price_cents,
        currency="USD",
        expires_at=datetime.now(UTC) + timedelta(days=30),
        tenant_id=tenant_id,
    )
    db.add(cache)
    db.flush()
    return cache


def _make_user_context(tenant_id: uuid.UUID) -> UserContext:
    """Return a minimal TestUserContext with the given tenant_id."""
    return UserContext(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="test@pilot.local",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPricingCacheIdorFix:
    """
    FIND-054: _get_pricing_cache_impl must filter by tenant_id.

    Each test creates isolated pricing cache rows and verifies the filter.
    All DB changes are rolled back via the transactional db_session fixture.
    """

    def test_tenant_a_sees_own_private_price_and_global(self, db_session: Session):
        """
        Tenant A should get:
          - their own private $0.90 row
          - the shared global $1.00 row
        Order: tenant-specific first (NULLS LAST ordering).
        """
        supplier = _create_supplier(db_session)
        tenant_a = _create_tenant(db_session, "Tenant A")

        sku = f"SKU-A-{uuid.uuid4().hex[:8]}"
        global_row = _create_pricing_cache(
            db_session, supplier, sku, 100, tenant_id=None
        )
        tenant_row = _create_pricing_cache(
            db_session, supplier, sku, 90, tenant_id=tenant_a.id
        )

        context_a = _make_user_context(tenant_a.id)
        results = _get_pricing_cache_impl(sku, db_session, context_a)

        prices = [r.price_cents for r in results]
        ids = [r.id for r in results]

        assert global_row.id in ids, "Global row must be visible to tenant A"
        assert tenant_row.id in ids, (
            "Tenant A's private row must be visible to tenant A"
        )
        assert len(results) == 2, f"Expected 2 rows for Tenant A, got {len(results)}"

    def test_tenant_specific_row_appears_before_global(self, db_session: Session):
        """
        NULLS LAST ordering: tenant-specific rows appear first.
        Tenant A's $0.90 row must appear before the global $1.00 row.
        """
        supplier = _create_supplier(db_session)
        tenant_a = _create_tenant(db_session, "Tenant A ordering")

        sku = f"SKU-ORD-{uuid.uuid4().hex[:8]}"
        _create_pricing_cache(db_session, supplier, sku, 100, tenant_id=None)  # global
        _create_pricing_cache(
            db_session, supplier, sku, 90, tenant_id=tenant_a.id
        )  # private

        context_a = _make_user_context(tenant_a.id)
        results = _get_pricing_cache_impl(sku, db_session, context_a)

        assert len(results) == 2
        # tenant-specific row has tenant_id set; global row has None
        assert results[0].tenant_id == tenant_a.id, (
            "Tenant-specific row must appear first (NULLS LAST ordering). "
            f"First result tenant_id={results[0].tenant_id}"
        )
        assert results[1].tenant_id is None, (
            "Global row must appear second. "
            f"Second result tenant_id={results[1].tenant_id}"
        )

    def test_tenant_b_cannot_see_tenant_a_private_price(self, db_session: Session):
        """
        IDOR fix: Tenant B must NOT see Tenant A's private $0.90 negotiated price.
        Tenant B should only see the global $1.00 row.
        """
        supplier = _create_supplier(db_session)
        tenant_a = _create_tenant(db_session, "Tenant A IDOR source")
        tenant_b = _create_tenant(db_session, "Tenant B IDOR attacker")

        sku = f"SKU-IDOR-{uuid.uuid4().hex[:8]}"
        global_row = _create_pricing_cache(
            db_session, supplier, sku, 100, tenant_id=None
        )
        tenant_a_row = _create_pricing_cache(
            db_session, supplier, sku, 90, tenant_id=tenant_a.id
        )

        context_b = _make_user_context(tenant_b.id)
        results = _get_pricing_cache_impl(sku, db_session, context_b)

        ids = [r.id for r in results]

        assert global_row.id in ids, "Global row should be visible to Tenant B"
        assert tenant_a_row.id not in ids, (
            "IDOR VULNERABILITY: Tenant B can see Tenant A's private $0.90 pricing! "
            "FIND-054 fix must prevent this."
        )
        assert len(results) == 1, (
            f"Expected 1 row (global only) for Tenant B, got {len(results)}: "
            f"prices={[r.price_cents for r in results]}"
        )

    def test_new_tenant_sees_only_global_rows(self, db_session: Session):
        """
        A brand-new tenant with no private negotiated prices should see only global rows.
        """
        supplier = _create_supplier(db_session)
        new_tenant = _create_tenant(db_session, "New Tenant no private prices")

        sku = f"SKU-NEW-{uuid.uuid4().hex[:8]}"
        global_row = _create_pricing_cache(
            db_session, supplier, sku, 100, tenant_id=None
        )

        context_new = _make_user_context(new_tenant.id)
        results = _get_pricing_cache_impl(sku, db_session, context_new)

        assert len(results) == 1, f"Expected 1 global row, got {len(results)}"
        assert results[0].id == global_row.id

    def test_sku_filter_still_works_after_idor_fix(self, db_session: Session):
        """
        SKU filter must still narrow results correctly after the tenant filter is applied.
        """
        supplier = _create_supplier(db_session)
        tenant_a = _create_tenant(db_session, "Tenant A SKU filter")

        sku_a = f"SKU-FILTER-A-{uuid.uuid4().hex[:8]}"
        sku_b = f"SKU-FILTER-B-{uuid.uuid4().hex[:8]}"

        row_a = _create_pricing_cache(db_session, supplier, sku_a, 100, tenant_id=None)
        row_b = _create_pricing_cache(db_session, supplier, sku_b, 200, tenant_id=None)

        context_a = _make_user_context(tenant_a.id)
        results = _get_pricing_cache_impl(sku_a, db_session, context_a)

        ids = [r.id for r in results]
        assert row_a.id in ids, f"SKU {sku_a} row should be in results"
        assert row_b.id not in ids, (
            f"SKU {sku_b} row should be filtered out by sku param"
        )

    def test_no_cross_tenant_leakage_multiple_tenants(self, db_session: Session):
        """
        With N tenants each having a private price for the same SKU, each tenant
        sees only their own private price + the global price, never another's.
        """
        supplier = _create_supplier(db_session)
        sku = f"SKU-MULTI-{uuid.uuid4().hex[:8]}"

        tenant_x = _create_tenant(db_session, "Tenant X multi")
        tenant_y = _create_tenant(db_session, "Tenant Y multi")
        tenant_z = _create_tenant(db_session, "Tenant Z multi")

        global_row = _create_pricing_cache(
            db_session, supplier, sku, 100, tenant_id=None
        )
        row_x = _create_pricing_cache(
            db_session, supplier, sku, 80, tenant_id=tenant_x.id
        )
        row_y = _create_pricing_cache(
            db_session, supplier, sku, 70, tenant_id=tenant_y.id
        )
        row_z = _create_pricing_cache(
            db_session, supplier, sku, 60, tenant_id=tenant_z.id
        )

        for tenant, own_row, other_rows in [
            (tenant_x, row_x, [row_y, row_z]),
            (tenant_y, row_y, [row_x, row_z]),
            (tenant_z, row_z, [row_x, row_y]),
        ]:
            ctx = _make_user_context(tenant.id)
            results = _get_pricing_cache_impl(sku, db_session, ctx)
            ids = {r.id for r in results}

            assert global_row.id in ids, f"{tenant.name} must see global row"
            assert own_row.id in ids, f"{tenant.name} must see their own private row"
            assert len(results) == 2, (
                f"{tenant.name} expected 2 rows, got {len(results)}"
            )
            for other in other_rows:
                assert other.id not in ids, (
                    f"IDOR: {tenant.name} can see another tenant's row (price_cents={other.price_cents})"
                )
