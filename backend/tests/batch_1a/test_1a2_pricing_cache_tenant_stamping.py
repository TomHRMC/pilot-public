"""
Task 1-A-2: `pricing_cache` Tenant Stamping — Verification Tests

Verifies:
1. `tenant_id` column exists on `pricing_cache` (nullable UUID)
2. `idx_pricing_cache_tenant` index exists
3. `id` bigserial surrogate PK exists (after PK expansion)
4. NULLS NOT DISTINCT unique constraint `uq_pricing_cache_supplier_sku_tenant` exists
5. No `tenant_id_coalesced` shadow column (trigger workaround was never merged)
6. Global cache entries (tenant_id=NULL) are readable by any tenant
7. Tenant-specific entries (tenant_id=X) are NOT readable by Tenant Y
8. Tenant-specific price takes precedence over global price for same SKU
9. Tenant A's own entries are always accessible to Tenant A

Reference: dev-docs/analysis/db-schema-domain-mvp-features-impl-plan.md Task 1-A-2
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, select

from app.models.billing import Currency
from app.models.catalog import PricingCache, Supplier, SupplierItem, SupplierItemUom
from app.models.crm import Customer, CustomerType, Site
from app.models.quoting import QcoLineType, QuoteStatus

# ============================================================
# Helpers
# ============================================================


def _ensure_currency(db: Session) -> None:
    if not db.exec(select(Currency).where(Currency.code == "USD")).first():
        db.add(Currency(code="USD", name="US Dollar", symbol="$"))
        db.flush()


def _create_supplier(db: Session) -> Supplier:
    supplier = Supplier(id=uuid.uuid4(), name=f"Supplier {uuid.uuid4().hex[:6]}")
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


def _create_supplier_item(
    db: Session,
    supplier: Supplier,
    uom: SupplierItemUom,
    tenant_id=None,
    sku: str = None,
) -> SupplierItem:
    sku = sku or f"SKU-{uuid.uuid4().hex[:8]}"
    item = SupplierItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        supplier_id=supplier.id,
        sku=sku,
        name=f"Item {sku}",
        uom_id=uom.id,
    )
    db.add(item)
    db.flush()
    return item


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


def _bootstrap_quote(
    client: TestClient,
    db: Session,
    tenant_id: uuid.UUID,
    token: str,
) -> str:
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
        code=f"mat-{uuid.uuid4().hex[:6]}",
        name="Material",
    )
    db.add(lt)
    db.flush()
    return lt


# ============================================================
# Schema Tests
# ============================================================


class TestPricingCacheSchema:
    """Verify the live DB schema after Task 1-A-2 migrations."""

    def test_pricing_cache_has_tenant_id_column(self, db_session: Session):
        """tenant_id must be present, nullable, UUID type."""
        rows = db_session.execute(
            text(
                "SELECT column_name, is_nullable, data_type "
                "FROM information_schema.columns "
                "WHERE table_name = 'pricing_cache' AND column_name = 'tenant_id'"
            )
        ).fetchall()
        assert len(rows) == 1, "`tenant_id` column NOT FOUND on `pricing_cache`."
        col = rows[0]
        assert col[1] == "YES", "tenant_id must be nullable (NULL = global price)"
        assert col[2] == "uuid", f"tenant_id must be UUID type, got {col[2]}"

    def test_pricing_cache_tenant_index_exists(self, db_session: Session):
        """idx_pricing_cache_tenant must exist for efficient tenant-scoped reads."""
        rows = db_session.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'pricing_cache' "
                "AND indexname = 'idx_pricing_cache_tenant'"
            )
        ).fetchall()
        assert len(rows) == 1, "Index `idx_pricing_cache_tenant` not found."

    def test_pricing_cache_has_surrogate_pk(self, db_session: Session):
        """Surrogate bigserial id PK must exist after PK expansion migration."""
        rows = db_session.execute(
            text(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_name = 'pricing_cache' AND column_name = 'id'"
            )
        ).fetchall()
        assert len(rows) == 1, "`id` surrogate PK not found on `pricing_cache`."
        assert rows[0][1] == "bigint", f"Expected bigint, got {rows[0][1]}"

    def test_pricing_cache_nulls_not_distinct_constraint(self, db_session: Session):
        """
        NULLS NOT DISTINCT unique constraint must exist on (supplier_id, sku, tenant_id).

        Verifies pg_index.indnullsnotdistinct = true for the constraint,
        confirming PostgreSQL 17 NULLS NOT DISTINCT syntax was applied.
        """
        # Constraint exists
        rows = db_session.execute(
            text(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_name = 'pricing_cache' "
                "AND constraint_name = 'uq_pricing_cache_supplier_sku_tenant'"
            )
        ).fetchall()
        assert len(rows) == 1, (
            "Unique constraint `uq_pricing_cache_supplier_sku_tenant` not found."
        )

        # Verify NULLS NOT DISTINCT via pg_index
        rows_nd = db_session.execute(
            text(
                "SELECT i.indnullsnotdistinct "
                "FROM pg_index i "
                "JOIN pg_class c ON c.oid = i.indrelid "
                "JOIN pg_class ic ON ic.oid = i.indexrelid "
                "WHERE c.relname = 'pricing_cache' "
                "AND ic.relname = 'uq_pricing_cache_supplier_sku_tenant'"
            )
        ).fetchall()
        assert len(rows_nd) == 1, (
            "Could not find index in pg_index for uq_pricing_cache_supplier_sku_tenant"
        )
        assert rows_nd[0][0] is True, (
            "Constraint is NOT using NULLS NOT DISTINCT. "
            "Expected pg_index.indnullsnotdistinct = true."
        )

    def test_pricing_cache_no_coalesced_shadow_column(self, db_session: Session):
        """tenant_id_coalesced shadow column must NOT exist (trigger workaround removed)."""
        rows = db_session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'pricing_cache' "
                "AND column_name = 'tenant_id_coalesced'"
            )
        ).fetchall()
        assert len(rows) == 0, (
            "`tenant_id_coalesced` shadow column still exists — trigger workaround was not removed."
        )


# ============================================================
# Functional / Security Tests
# ============================================================


class TestPricingCacheTenantStamping:
    """Task 1-A-2: Tenant-scoped PricingCache reads on quote line creation."""

    def test_global_cache_entry_accessible_to_any_tenant(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """POSITIVE: Global cache entry (tenant_id=NULL) is readable by any tenant."""
        _ensure_currency(db_session)
        supplier = _create_supplier(db_session)
        uom = _create_uom(db_session)
        sku = f"GLOBAL-{uuid.uuid4().hex[:8]}"

        item = _create_supplier_item(db_session, supplier, uom, tenant_id=None, sku=sku)
        _create_pricing_cache(db_session, supplier, sku, 7500, tenant_id=None)

        line_type = _create_line_type(db_session, tenant_a.id)
        token = mock_jwt_for_user(user_tenant_a.email)
        quote_id = _bootstrap_quote(client, db_session, tenant_a.id, token)

        resp = client.post(
            f"/api/v1/quotes/{quote_id}/lines",
            json={
                "position": 1,
                "qco_line_type_id": str(line_type.id),
                "description": "Global catalog item",
                "quantity": 1.0,
                "supplier_item_id": str(item.id),
            },
            headers={"Authorization": token},
        )

        assert resp.status_code == 201, resp.text
        assert resp.json()["unit_price_cents"] == 7500

    def test_private_cache_entry_not_leaked_to_other_tenant(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """SECURITY: Tenant B's private cache entry must NOT reach Tenant A."""
        _ensure_currency(db_session)
        supplier = _create_supplier(db_session)
        uom = _create_uom(db_session)
        sku = f"PRIV-{uuid.uuid4().hex[:8]}"

        item = _create_supplier_item(db_session, supplier, uom, tenant_id=None, sku=sku)
        _create_pricing_cache(db_session, supplier, sku, 99900, tenant_id=tenant_b.id)

        line_type = _create_line_type(db_session, tenant_a.id)
        token = mock_jwt_for_user(user_tenant_a.email)
        quote_id = _bootstrap_quote(client, db_session, tenant_a.id, token)

        resp = client.post(
            f"/api/v1/quotes/{quote_id}/lines",
            json={
                "position": 1,
                "qco_line_type_id": str(line_type.id),
                "description": "Attempting cross-tenant cache read",
                "quantity": 1.0,
                "unit_price_cents": 100,
                "supplier_item_id": str(item.id),
            },
            headers={"Authorization": token},
        )

        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["unit_price_cents"] != 99900, (
            "CACHE LEAK CONFIRMED: Tenant A received Tenant B's private price (99900)."
        )
        assert data["unit_price_cents"] == 100

    def test_tenant_specific_price_takes_precedence_over_global(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """
        POSITIVE: Tenant-specific negotiated price wins over global price for same SKU.
        Requires PK expansion migration (b2c3d4e5f6a7) with NULLS NOT DISTINCT constraint.
        """
        _ensure_currency(db_session)
        supplier = _create_supplier(db_session)
        uom = _create_uom(db_session)
        sku = f"DUAL-{uuid.uuid4().hex[:8]}"

        _create_pricing_cache(db_session, supplier, sku, 5000, tenant_id=None)
        _create_pricing_cache(db_session, supplier, sku, 4200, tenant_id=tenant_a.id)

        item = _create_supplier_item(db_session, supplier, uom, tenant_id=None, sku=sku)
        line_type = _create_line_type(db_session, tenant_a.id)
        token = mock_jwt_for_user(user_tenant_a.email)
        quote_id = _bootstrap_quote(client, db_session, tenant_a.id, token)

        resp = client.post(
            f"/api/v1/quotes/{quote_id}/lines",
            json={
                "position": 1,
                "qco_line_type_id": str(line_type.id),
                "description": "Dual pricing — tenant price should win",
                "quantity": 1.0,
                "supplier_item_id": str(item.id),
            },
            headers={"Authorization": token},
        )

        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["unit_price_cents"] == 4200, (
            f"Tenant negotiated price should win. Expected 4200, got {data['unit_price_cents']}"
        )

    def test_tenant_scoped_orm_query_excludes_other_tenant_cache(
        self,
        db_session: Session,
        tenant_a,
        tenant_b,
    ):
        """UNIT: ORM query scoped to Tenant A does NOT return Tenant B's entry."""
        supplier = _create_supplier(db_session)
        uom = _create_uom(db_session)

        sku_b = f"B-SKU-{uuid.uuid4().hex[:8]}"
        _create_supplier_item(
            db_session, supplier, uom, tenant_id=tenant_b.id, sku=sku_b
        )
        cache_b = _create_pricing_cache(
            db_session, supplier, sku_b, 88800, tenant_id=tenant_b.id
        )
        db_session.commit()

        result = db_session.exec(
            select(PricingCache).where(
                PricingCache.supplier_id == cache_b.supplier_id,
                PricingCache.sku == sku_b,
                (PricingCache.tenant_id == tenant_a.id)
                | (PricingCache.tenant_id == None),
            )
        ).first()

        assert result is None, (
            "SCOPE LEAK: Tenant-A-scoped query returned Tenant B's private cache entry! "
            f"price_cents={result.price_cents if result else 'N/A'}"
        )

    def test_own_tenant_cache_entry_accessible(
        self,
        client: TestClient,
        db_session: Session,
        tenant_a,
        user_tenant_a,
        mock_jwt_for_user,
    ):
        """POSITIVE: Tenant A's own private cache entry is always accessible."""
        _ensure_currency(db_session)
        supplier = _create_supplier(db_session)
        uom = _create_uom(db_session)
        sku = f"OWN-{uuid.uuid4().hex[:8]}"

        item = _create_supplier_item(
            db_session, supplier, uom, tenant_id=tenant_a.id, sku=sku
        )
        _create_pricing_cache(db_session, supplier, sku, 3300, tenant_id=tenant_a.id)

        line_type = _create_line_type(db_session, tenant_a.id)
        token = mock_jwt_for_user(user_tenant_a.email)
        quote_id = _bootstrap_quote(client, db_session, tenant_a.id, token)

        resp = client.post(
            f"/api/v1/quotes/{quote_id}/lines",
            json={
                "position": 1,
                "qco_line_type_id": str(line_type.id),
                "description": "Own private catalog item",
                "quantity": 1.0,
                "supplier_item_id": str(item.id),
            },
            headers={"Authorization": token},
        )

        assert resp.status_code == 201, resp.text
        assert resp.json()["unit_price_cents"] == 3300
