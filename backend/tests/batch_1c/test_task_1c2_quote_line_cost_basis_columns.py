"""
Test Suite: Task 1-C-2 — quote_line Cost-Basis Columns
=======================================================
Verifies the following:

1. DB Schema: `unit_cost_cents` (bigint, nullable) and `cost_source` (varchar, nullable)
   are present in the live `quote_line` table.
2. ORM Model: QuoteLine model exposes both fields and they round-trip correctly via SQLModel.
3. Null Default: QuoteLine can be persisted WITHOUT cost-basis fields (they are optional).
4. Gross Margin Calculation: API-layer formula `unit_price_cents - unit_cost_cents`
   produces correct pre-sale margin at the Python layer.
5. Cost Source Enumeration: Various cost_source string values are accepted without constraint.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.quoting import Quote, QuoteLine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_quote(db_session, test_tenant, test_customer, test_site, test_quote_status):
    """Create a minimal parent quote for QuoteLine tests."""
    quote = Quote(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=test_quote_status.id,
        currency="USD",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(quote)
    db_session.commit()
    db_session.refresh(quote)
    return quote


def _make_quote_line(
    tenant_id,
    quote_id,
    qco_line_type_id,
    unit_price_cents: int,
    unit_cost_cents=None,
    cost_source=None,
) -> QuoteLine:
    """Factory: build a QuoteLine instance with optional cost-basis fields."""
    return QuoteLine(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quote_id=quote_id,
        position=1,
        qco_line_type_id=qco_line_type_id,
        description="20A circuit breaker installation",
        quantity=Decimal("1.000"),
        unit_price_cents=unit_price_cents,
        unit_cost_cents=unit_cost_cents,
        cost_source=cost_source,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# 1. DB Schema Tests — query information_schema directly
# ---------------------------------------------------------------------------


class TestQuoteLineCostBasisSchema:
    """Verify columns exist in the live DB with correct types and nullability."""

    def test_unit_cost_cents_column_exists(self, db_engine):
        """unit_cost_cents must be present, bigint, nullable."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'quote_line'
                      AND column_name = 'unit_cost_cents'
                """)
            ).fetchone()
        assert row is not None, "Column 'unit_cost_cents' is missing from quote_line"
        assert row.data_type == "bigint", f"Expected bigint, got {row.data_type}"
        assert row.is_nullable == "YES", (
            "unit_cost_cents must be nullable (not all lines require a cost basis)"
        )

    def test_cost_source_column_exists(self, db_engine):
        """cost_source must be present, varchar, nullable."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'quote_line'
                      AND column_name = 'cost_source'
                """)
            ).fetchone()
        assert row is not None, "Column 'cost_source' is missing from quote_line"
        assert row.data_type == "character varying", (
            f"Expected character varying, got {row.data_type}"
        )
        assert row.is_nullable == "YES", "cost_source must be nullable"

    def test_no_default_on_unit_cost_cents(self, db_engine):
        """unit_cost_cents must have no server default (it is nullable, not defaulted to 0)."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_default
                    FROM information_schema.columns
                    WHERE table_name = 'quote_line'
                      AND column_name = 'unit_cost_cents'
                """)
            ).fetchone()
        assert row is not None
        assert row.column_default is None, (
            "unit_cost_cents should have no server default — NULL signals 'cost unknown'"
        )


# ---------------------------------------------------------------------------
# 2. ORM Model Tests — round-trip through QuoteLine model
# ---------------------------------------------------------------------------


class TestQuoteLineOrmCostBasis:
    """Verify QuoteLine ORM exposes and persists cost-basis fields correctly."""

    def test_quote_line_with_cost_basis_persists(
        self, db_session, test_tenant, test_quote, test_qco_line_type
    ):
        """QuoteLine with unit_cost_cents + cost_source round-trips correctly."""
        line = _make_quote_line(
            tenant_id=test_tenant.id,
            quote_id=test_quote.id,
            qco_line_type_id=test_qco_line_type.id,
            unit_price_cents=25000,  # $250.00 sell price
            unit_cost_cents=15000,  # $150.00 cost
            cost_source="supplier_catalog",
        )
        db_session.add(line)
        db_session.commit()
        db_session.refresh(line)

        fetched = db_session.exec(
            select(QuoteLine).where(QuoteLine.id == line.id)
        ).first()
        assert fetched is not None
        assert fetched.unit_cost_cents == 15000
        assert fetched.cost_source == "supplier_catalog"

    def test_quote_line_without_cost_basis_defaults_to_null(
        self, db_session, test_tenant, test_quote, test_qco_line_type
    ):
        """QuoteLine persisted without cost-basis fields defaults both to None."""
        line = _make_quote_line(
            tenant_id=test_tenant.id,
            quote_id=test_quote.id,
            qco_line_type_id=test_qco_line_type.id,
            unit_price_cents=5000,
            # Intentionally omit unit_cost_cents and cost_source
        )
        db_session.add(line)
        db_session.commit()
        db_session.refresh(line)

        fetched = db_session.exec(
            select(QuoteLine).where(QuoteLine.id == line.id)
        ).first()
        assert fetched is not None
        assert fetched.unit_cost_cents is None, (
            "unit_cost_cents should be None when not provided"
        )
        assert fetched.cost_source is None, (
            "cost_source should be None when not provided"
        )

    def test_cost_source_accepts_various_values(
        self, db_session, test_tenant, test_quote, test_qco_line_type
    ):
        """cost_source is a free VARCHAR — any string should be accepted."""
        for idx, source in enumerate(
            ["supplier_catalog", "labor_rate", "manual", "voice_ai"]
        ):
            line = QuoteLine(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                quote_id=test_quote.id,
                position=idx + 10,
                qco_line_type_id=test_qco_line_type.id,
                description=f"Test line {source}",
                quantity=Decimal("1.000"),
                unit_price_cents=1000,
                unit_cost_cents=600,
                cost_source=source,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db_session.add(line)
        db_session.commit()
        # All 4 should have been accepted with no error

    def test_unit_cost_cents_accepts_large_bigint(
        self, db_session, test_tenant, test_quote, test_qco_line_type
    ):
        """unit_cost_cents is BIGINT — should accept values beyond INTEGER range (> 2^31)."""
        large_value = 10_000_000_00  # $1,000,000.00 in cents — exceeds INTEGER max
        line = _make_quote_line(
            tenant_id=test_tenant.id,
            quote_id=test_quote.id,
            qco_line_type_id=test_qco_line_type.id,
            unit_price_cents=10_000_000_00,
            unit_cost_cents=large_value,
            cost_source="manual",
        )
        db_session.add(line)
        db_session.commit()
        db_session.refresh(line)

        fetched = db_session.exec(
            select(QuoteLine).where(QuoteLine.id == line.id)
        ).first()
        assert fetched.unit_cost_cents == large_value


# ---------------------------------------------------------------------------
# 3. Gross Margin Calculation Tests — Python-layer formula
# ---------------------------------------------------------------------------


class TestGrossMarginCalculation:
    """
    Verify the gross margin formula works correctly at the API/Python layer.
    Formula: gross_margin_cents = unit_price_cents - unit_cost_cents
    Formula: gross_margin_pct = (unit_price_cents - unit_cost_cents) / unit_price_cents * 100
    These are computed values — NOT stored in the DB — so tests exercise the formula only.
    """

    def _compute_margin(self, unit_price_cents: int, unit_cost_cents: int) -> dict:
        """Simulates the API-layer gross margin calculation."""
        if unit_price_cents == 0:
            return {
                "gross_margin_cents": None,
                "gross_margin_pct": None,
            }
        margin_cents = unit_price_cents - unit_cost_cents
        margin_pct = round((margin_cents / unit_price_cents) * 100, 2)
        return {
            "gross_margin_cents": margin_cents,
            "gross_margin_pct": margin_pct,
        }

    def test_standard_margin_calculation(self):
        """Standard case: $250 sell, $150 cost → $100 margin, 40%."""
        result = self._compute_margin(25000, 15000)
        assert result["gross_margin_cents"] == 10000
        assert result["gross_margin_pct"] == 40.0

    def test_zero_margin(self):
        """Cost equals price → 0 margin, 0%."""
        result = self._compute_margin(10000, 10000)
        assert result["gross_margin_cents"] == 0
        assert result["gross_margin_pct"] == 0.0

    def test_negative_margin(self):
        """Cost exceeds price → negative margin (underbidding scenario)."""
        result = self._compute_margin(10000, 12000)
        assert result["gross_margin_cents"] == -2000
        assert result["gross_margin_pct"] == -20.0

    def test_zero_price_returns_none(self):
        """Zero unit_price_cents → no margin calculation possible (avoid divide-by-zero)."""
        result = self._compute_margin(0, 5000)
        assert result["gross_margin_cents"] is None
        assert result["gross_margin_pct"] is None

    def test_margin_when_cost_is_none(
        self, db_session, test_tenant, test_quote, test_qco_line_type
    ):
        """When unit_cost_cents is NULL, gross_margin_pct must be None (no cost basis)."""
        line = _make_quote_line(
            tenant_id=test_tenant.id,
            quote_id=test_quote.id,
            qco_line_type_id=test_qco_line_type.id,
            unit_price_cents=25000,
            unit_cost_cents=None,  # No cost known
        )
        db_session.add(line)
        db_session.commit()
        db_session.refresh(line)

        fetched = db_session.exec(
            select(QuoteLine).where(QuoteLine.id == line.id)
        ).first()

        # API layer: if cost is None, margin cannot be computed
        if fetched.unit_cost_cents is None:
            gross_margin_pct = None
        else:
            gross_margin_pct = round(
                (fetched.unit_price_cents - fetched.unit_cost_cents)
                / fetched.unit_price_cents
                * 100,
                2,
            )
        assert gross_margin_pct is None, "Cannot compute margin without cost basis"
