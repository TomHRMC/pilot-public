"""
Task 1-A-1: Cross-Tenant Pricing IDOR Fix — Security Tests

Verifies that the SupplierItem lookup in `_create_quote_line_impl()` is scoped
to `tenant_id IS NULL OR tenant_id = current_tenant.id`, closing the IDOR
vulnerability where Tenant A could read Tenant B's private catalog prices.

Security principle:
  - Private SupplierItems (tenant_id = Tenant B) → invisible to Tenant A
  - Global SupplierItems (tenant_id IS NULL) → accessible to ALL tenants
  - Quote line price must not reflect a foreign tenant's PricingCache entry

Reference: dev-docs/analysis/db-schema-domain-mvp-features-impl-plan.md Task 1-A-1
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.billing import Currency
from app.models.catalog import PricingCache, Supplier, SupplierItem, SupplierItemUom
from app.models.crm import Customer, CustomerType, Site
from app.models.quoting import QcoLineType, QuoteStatus

# ============================================================
# Helpers
# ============================================================


def _ensure_currency(db: Session) -> None:
    from sqlmodel import select

    if not db.exec(select(Currency).where(Currency.code == "USD")).first():
        db.add(Currency(code="USD", name="US Dollar", symbol="$"))
        db.flush()


def _create_global_supplier(db: Session) -> Supplier:
    """System-wide supplier — no tenant_id."""
    supplier = Supplier(id=uuid.uuid4(), name="Global Electric Supply Co.")
    db.add(supplier)
    db.flush()
    return supplier


def _create_uom(db: Session) -> SupplierItemUom:
    uom = SupplierItemUom(
        id=uuid.uuid4(),
        code=f"EA-{uuid.uuid4().hex[:6]}",
        name="Each",
    )
    db.add(uom)
    db.flush()
    return uom


def _create_pricing_cache(
    db: Session, supplier: Supplier, sku: str, price_cents: int
) -> PricingCache:
    cache_entry = PricingCache(
        supplier_id=supplier.id,
        sku=sku,
        price_cents=price_cents,
        currency="USD",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(cache_entry)
    db.flush()
    return cache_entry


def _create_quote_status(db: Session, tenant_id: uuid.UUID) -> QuoteStatus:
    qs = QuoteStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="draft",
        name="Draft",
        is_default=True,
    )
    db.add(qs)
    db.flush()
    return qs


def _create_quote_for_tenant(
    client: TestClient,
    db: Session,
    tenant_id: uuid.UUID,
    token: str,
) -> str:
    """Create a customer, site, and quote; return the quote UUID string."""
    customer = Customer(
        tenant_id=tenant_id,
        type=CustomerType.person,
        display_name=f"Customer {uuid.uuid4().hex[:6]}",
    )
    db.add(customer)
    db.flush()

    site = Site(tenant_id=tenant_id, customer_id=customer.id, name="Test Site")
    db.add(site)
    db.flush()

    _create_quote_status(db, tenant_id)
    db.commit()

    resp = client.post(
        "/api/v1/quotes",
        json={
            "customer_id": str(customer.id),
            "site_id": str(site.id),
            "currency": "USD",
        },
        headers={"Authorization": token},
    )
    assert resp.status_code == 201, f"Quote creation failed: {resp.text}"
    return resp.json()["id"]


def _create_line_type(db: Session, tenant_id: uuid.UUID) -> QcoLineType:
    lt = QcoLineType(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=f"material-{uuid.uuid4().hex[:6]}",
        name="Material",
    )
    db.add(lt)
    db.flush()
    return lt


# ============================================================
# IDOR Tests
# ============================================================


class TestCrossTenantPricingIDOR:
    """Task 1-A-1: SupplierItem lookup is tenant-scoped on quote line creation."""

    def test_private_supplier_item_not_visible_to_other_tenant(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """
        SECURITY: Tenant A cannot read Tenant B's private catalog price
        via quote line creation.

        Attack vector: Tenant A creates a quote line passing `supplier_item_id`
        that belongs to Tenant B. Before the fix, `db.get(SupplierItem, id)`
        returned the record regardless of tenant, leaking Tenant B's price.

        Expected behavior after fix: The scoped query returns no match →
        unit_price_cents stays at the caller-provided value (0 default), NOT
        Tenant B's private price (99900).
        """
        _ensure_currency(db_session)

        # ARRANGE: Tenant B has a private supplier item with a known price
        supplier = _create_global_supplier(db_session)
        uom = _create_uom(db_session)

        tenant_b_sku = f"PRIV-ITEM-{uuid.uuid4().hex[:8]}"
        tenant_b_price_cents = 99900  # $999.00 — Tenant B's secret price

        tenant_b_item = SupplierItem(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,  # PRIVATE to Tenant B
            supplier_id=supplier.id,
            sku=tenant_b_sku,
            name="Tenant B Secret Breaker Panel",
            uom_id=uom.id,
        )
        db_session.add(tenant_b_item)
        db_session.flush()

        _create_pricing_cache(db_session, supplier, tenant_b_sku, tenant_b_price_cents)

        # Create line type for Tenant A
        line_type = _create_line_type(db_session, tenant_a.id)

        # Build a quote for Tenant A
        token = mock_jwt_for_user(user_tenant_a.email)
        quote_id = _create_quote_for_tenant(client, db_session, tenant_a.id, token)

        # ACT: Tenant A tries to reference Tenant B's supplier_item_id in a line
        line_payload = {
            "position": 1,
            "qco_line_type_id": str(line_type.id),
            "description": "Attempted IDOR via supplier_item_id",
            "quantity": 1.0,
            # Explicitly provide a low price; IDOR would override this with 99900
            "unit_price_cents": 100,
            "supplier_item_id": str(tenant_b_item.id),  # <- foreign tenant's item
        }

        resp = client.post(
            f"/api/v1/quotes/{quote_id}/lines",
            json=line_payload,
            headers={"Authorization": token},
        )

        # ASSERT: Request succeeds (no crash), but price is NOT Tenant B's price
        assert resp.status_code == 201, f"Unexpected error: {resp.text}"
        data = resp.json()

        assert data["unit_price_cents"] != tenant_b_price_cents, (
            f"IDOR CONFIRMED: Tenant A read Tenant B's private price ({tenant_b_price_cents} cents). "
            "The SupplierItem lookup is not tenant-scoped!"
        )
        # The fallback is the caller-provided unit_price_cents since no scoped match was found
        assert data["unit_price_cents"] == 100, (
            f"Expected caller-provided price 100 cents, got {data['unit_price_cents']}"
        )

    def test_global_supplier_item_accessible_to_any_tenant(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """
        POSITIVE CASE: Global supplier items (tenant_id IS NULL) MUST remain
        accessible to all tenants. The IDOR fix must not break global catalog access.
        """
        _ensure_currency(db_session)

        # ARRANGE: A global/system-wide supplier item (no tenant ownership)
        supplier = _create_global_supplier(db_session)
        uom = _create_uom(db_session)

        global_sku = f"GLOBAL-ITEM-{uuid.uuid4().hex[:8]}"
        global_price_cents = 4500  # $45.00

        global_item = SupplierItem(
            id=uuid.uuid4(),
            tenant_id=None,  # GLOBAL — available to all tenants
            supplier_id=supplier.id,
            sku=global_sku,
            name="Global 20A Breaker",
            uom_id=uom.id,
        )
        db_session.add(global_item)
        db_session.flush()

        _create_pricing_cache(db_session, supplier, global_sku, global_price_cents)

        line_type = _create_line_type(db_session, tenant_a.id)

        token = mock_jwt_for_user(user_tenant_a.email)
        quote_id = _create_quote_for_tenant(client, db_session, tenant_a.id, token)

        # ACT: Tenant A references the global item
        line_payload = {
            "position": 1,
            "qco_line_type_id": str(line_type.id),
            "description": "20A Breaker from global catalog",
            "quantity": 2.0,
            "supplier_item_id": str(global_item.id),
        }

        resp = client.post(
            f"/api/v1/quotes/{quote_id}/lines",
            json=line_payload,
            headers={"Authorization": token},
        )

        # ASSERT: Global item price IS applied (tenant_id IS NULL passes the filter)
        assert resp.status_code == 201, f"Unexpected error: {resp.text}"
        data = resp.json()

        assert data["unit_price_cents"] == global_price_cents, (
            f"Global catalog item price not applied. "
            f"Expected {global_price_cents}, got {data['unit_price_cents']}"
        )
        assert data["subtotal_cents"] == global_price_cents * 2, (
            f"Subtotal mismatch: expected {global_price_cents * 2}, got {data['subtotal_cents']}"
        )

    def test_own_tenant_supplier_item_accessible(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """
        POSITIVE CASE: Tenant A can always access its OWN private supplier items.
        The fix must not break same-tenant catalog access.
        """
        _ensure_currency(db_session)

        supplier = _create_global_supplier(db_session)
        uom = _create_uom(db_session)

        own_sku = f"OWN-ITEM-{uuid.uuid4().hex[:8]}"
        own_price_cents = 7500  # $75.00

        own_item = SupplierItem(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,  # Owned by Tenant A
            supplier_id=supplier.id,
            sku=own_sku,
            name="Tenant A Custom Wire Spool",
            uom_id=uom.id,
        )
        db_session.add(own_item)
        db_session.flush()

        _create_pricing_cache(db_session, supplier, own_sku, own_price_cents)

        line_type = _create_line_type(db_session, tenant_a.id)

        token = mock_jwt_for_user(user_tenant_a.email)
        quote_id = _create_quote_for_tenant(client, db_session, tenant_a.id, token)

        line_payload = {
            "position": 1,
            "qco_line_type_id": str(line_type.id),
            "description": "Own catalog item",
            "quantity": 1.0,
            "supplier_item_id": str(own_item.id),
        }

        resp = client.post(
            f"/api/v1/quotes/{quote_id}/lines",
            json=line_payload,
            headers={"Authorization": token},
        )

        assert resp.status_code == 201, f"Unexpected error: {resp.text}"
        data = resp.json()

        assert data["unit_price_cents"] == own_price_cents, (
            f"Own-tenant supplier item price not applied. "
            f"Expected {own_price_cents}, got {data['unit_price_cents']}"
        )
