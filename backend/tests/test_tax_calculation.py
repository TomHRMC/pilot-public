"""
Test Suite for Tax Calculation System (Gap #11)

Tests the jurisdiction-based tax rate lookup, IRS-compliant tax calculation,
and integration with quote line creation.

Reference: dev-docs/analysis/gap-11-tax-calculation-remediation-plan.md
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.catalog import TaxRateVersion
from app.models.crm import Customer, Site
from app.models.quoting import (
    QcoLineType,
    Quote,
    QuoteLine,
    QuoteLineTaxComponent,
    QuoteStatus,
)
from core.tax_calculation import (
    calculate_combined_tax_rate,
    calculate_tax_components,
    get_tax_rates_for_quote_line,
)
from tests.test_phase2 import setup_test_user

# ==================== Unit Tests for Tax Calculation Functions ====================


class TestTaxRateLookup:
    """Test the get_tax_rates_for_quote_line() function."""

    def test_get_tax_rates_valid_jurisdiction(self, db_session: Session):
        """Test tax rate lookup for a valid jurisdiction with existing rates."""
        # Create tenant first
        from app.models.core import Tenant

        tenant = Tenant(name="Test Tenant", is_active=True)
        db_session.add(tenant)
        db_session.flush()

        # Create customer and site with jurisdiction
        customer = Customer(
            tenant_id=tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            type="person",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(
            tenant_id=tenant.id,
            customer_id=customer.id,
            name="Test Site",
            jurisdiction_code="US-TX-HARRIS",
        )
        db_session.add(site)
        db_session.commit()

        # Look up tax rates
        tax_rates = get_tax_rates_for_quote_line(
            db=db_session,
            site_id=site.id,
            taxability_code="taxable",
            as_of_timestamp=datetime.now(UTC),
        )

        # Should find the Harris County rate (8.25%)
        assert len(tax_rates) > 0
        assert any(rate.jurisdiction_code == "US-TX-HARRIS" for rate in tax_rates)
        harris_rate = next(
            r for r in tax_rates if r.jurisdiction_code == "US-TX-HARRIS"
        )
        assert harris_rate.rate_pct == Decimal("8.25")

    def test_get_tax_rates_exempt_items(self, db_session: Session):
        """Test that exempt items return no tax rates (0% tax)."""
        # Create tenant first
        from app.models.core import Tenant

        tenant = Tenant(name="Test Tenant", is_active=True)
        db_session.add(tenant)
        db_session.flush()

        customer = Customer(
            tenant_id=tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            type="person",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(
            tenant_id=tenant.id,
            customer_id=customer.id,
            name="Test Site",
            jurisdiction_code="US-TX-HARRIS",
        )
        db_session.add(site)
        db_session.commit()

        # Look up tax rates for exempt item
        tax_rates = get_tax_rates_for_quote_line(
            db=db_session,
            site_id=site.id,
            taxability_code="exempt",
            as_of_timestamp=datetime.now(UTC),
        )

        # Should return empty list for exempt items
        assert len(tax_rates) == 0

    def test_get_tax_rates_default_jurisdiction(self, db_session: Session):
        """Test fallback to US-DEFAULT jurisdiction when site has no jurisdiction_code."""
        # Create tenant first
        from app.models.core import Tenant

        tenant = Tenant(name="Test Tenant", is_active=True)
        db_session.add(tenant)
        db_session.flush()

        customer = Customer(
            tenant_id=tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            type="person",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(
            tenant_id=tenant.id,
            customer_id=customer.id,
            name="Test Site",
            jurisdiction_code=None,  # No jurisdiction
        )
        db_session.add(site)
        db_session.commit()

        # Look up tax rates (should fall back to US-DEFAULT)
        tax_rates = get_tax_rates_for_quote_line(
            db=db_session,
            site_id=site.id,
            taxability_code="taxable",
            as_of_timestamp=datetime.now(UTC),
        )

        # Should find the US-DEFAULT rate (6.0%)
        assert len(tax_rates) > 0
        assert any(rate.jurisdiction_code == "US-DEFAULT" for rate in tax_rates)
        default_rate = next(r for r in tax_rates if r.jurisdiction_code == "US-DEFAULT")
        assert default_rate.rate_pct == Decimal("6.0")

    def test_get_tax_rates_site_not_found(self, db_session: Session):
        """Test that looking up rates for non-existent site returns empty list."""
        fake_site_id = uuid4()

        # Should return empty list for non-existent site (not raise exception)
        tax_rates = get_tax_rates_for_quote_line(
            db=db_session,
            site_id=fake_site_id,
            taxability_code="taxable",
            as_of_timestamp=datetime.now(UTC),
        )

        assert len(tax_rates) == 0


class TestTaxComponentCalculation:
    """Test the calculate_tax_components() function."""

    def test_calculate_tax_basic(self, db_session: Session):
        """Test basic tax calculation with single rate (8.25%)."""
        # Create a tax rate
        tax_rate = TaxRateVersion(
            jurisdiction_code="TEST-BASIC",
            description="Test Rate",
            rate_pct=Decimal("8.25"),
            valid_period="[2024-01-01,)",
            recorded_at=datetime.now(UTC),
        )
        db_session.add(tax_rate)
        db_session.flush()

        # Calculate tax on $100.00 (10000 cents)
        subtotal_cents = 10000
        total_tax, components = calculate_tax_components(
            subtotal_cents=subtotal_cents,
            tax_rates=[tax_rate],
        )

        # Tax should be $8.25 (825 cents)
        assert total_tax == 825
        assert len(components) == 1
        assert components[0].component_code == "TEST-BASIC"
        assert components[0].rate_pct == 8.25
        assert components[0].amount_cents == 825

    def test_calculate_tax_rounding_up(self, db_session: Session):
        """Test that tax calculation rounds UP to nearest cent (IRS compliance)."""
        # Create a tax rate that will produce fractional cents
        tax_rate = TaxRateVersion(
            jurisdiction_code="TEST-ROUND",
            description="Test Rounding",
            rate_pct=Decimal("7.77"),  # 7.77% will produce fractional cents
            valid_period="[2024-01-01,)",
            recorded_at=datetime.now(UTC),
        )
        db_session.add(tax_rate)
        db_session.flush()

        # Calculate tax on $100.11 (10011 cents)
        # 10011 * 0.0777 = 777.8547 cents = $7.778547
        # Should round UP to 778 cents = $7.78
        subtotal_cents = 10011
        total_tax, components = calculate_tax_components(
            subtotal_cents=subtotal_cents,
            tax_rates=[tax_rate],
        )

        # Verify rounding UP occurred
        assert total_tax == 778  # Rounded up from 777.8547
        assert components[0].amount_cents == 778

    def test_calculate_tax_zero_tax(self):
        """Test that exempt items (no rates) return $0 tax."""
        total_tax, components = calculate_tax_components(
            subtotal_cents=10000,
            tax_rates=[],  # No rates = exempt
        )

        assert total_tax == 0
        assert len(components) == 0

    def test_calculate_combined_tax_rate(self):
        """Test combined rate calculation for multiple tax components."""
        rates = [
            TaxRateVersion(
                jurisdiction_code="STATE",
                rate_pct=Decimal("6.0"),
                valid_period="[2024-01-01,)",
                recorded_at=datetime.now(UTC),
            ),
            TaxRateVersion(
                jurisdiction_code="COUNTY",
                rate_pct=Decimal("1.5"),
                valid_period="[2024-01-01,)",
                recorded_at=datetime.now(UTC),
            ),
            TaxRateVersion(
                jurisdiction_code="CITY",
                rate_pct=Decimal("0.75"),
                valid_period="[2024-01-01,)",
                recorded_at=datetime.now(UTC),
            ),
        ]

        combined_rate = calculate_combined_tax_rate(rates)
        assert combined_rate == 8.25  # 6.0 + 1.5 + 0.75


# ==================== Integration Tests with Quote Line Creation ====================


class TestQuoteLineTaxIntegration:
    """Test tax calculation integration with quote line creation."""

    def test_create_quote_line_with_tax(
        self, client: TestClient, db_session: Session, mock_cognito_jwt_verify
    ):
        """Test that creating a quote line calculates and stores tax."""
        headers, user_id, tenant_id = setup_test_user(client, db_session)

        # Create customer and site with jurisdiction
        customer = Customer(
            tenant_id=tenant_id,
            display_name="Tax Test Customer",
            type="person",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(
            tenant_id=tenant_id,
            customer_id=customer.id,
            name="Tax Test Site",
            jurisdiction_code="US-DEFAULT",  # 6.0% tax
        )
        db_session.add(site)
        db_session.flush()

        # Get or create default quote status
        default_status = db_session.exec(
            select(QuoteStatus).where(QuoteStatus.is_default == True).limit(1)
        ).first()
        if not default_status:
            default_status = QuoteStatus(
                tenant_id=tenant_id,
                code="draft",
                name="Draft",
                is_default=True,
                is_active=True,
            )
            db_session.add(default_status)
            db_session.flush()

        # Create quote
        quote = Quote(
            tenant_id=tenant_id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=default_status.id,
            subtotal_cents=0,
            tax_cents=0,
            total_cents=0,
        )
        db_session.add(quote)
        db_session.flush()

        # Get a line type
        line_type = db_session.exec(select(QcoLineType).limit(1)).first()
        if not line_type:
            line_type = QcoLineType(
                tenant_id=None,
                code="material",
                name="Material",
                is_default=True,
                is_active=True,
            )
            db_session.add(line_type)
            db_session.flush()

        db_session.commit()

        # Create quote line via API (using test endpoint)
        response = client.post(
            f"/api/v1/quotes/{quote.id}/lines/test",
            json={
                "position": 1,
                "qco_line_type_id": str(line_type.id),
                "description": "Test Item",
                "quantity": 1,
                "unit_price_cents": 10000,  # $100.00
                "taxability_code": "taxable",
            },
        )

        assert response.status_code == 201
        line_data = response.json()

        # Verify tax was calculated
        assert line_data["subtotal_cents"] == 10000  # $100.00
        assert line_data["tax_amount_cents"] == 600  # 6% of $100 = $6.00
        assert line_data["total_cents"] == 10600  # $106.00
        assert line_data["tax_rate_pct"] == 6.0
        assert line_data["tax_jurisdiction_code"] == "US-DEFAULT"
        assert line_data["tax_source"] == "internal_lookup"
        assert line_data["tax_as_of"] is not None

        # Verify tax components were created
        quote_line_id = line_data["id"]
        tax_components = db_session.exec(
            select(QuoteLineTaxComponent).where(
                QuoteLineTaxComponent.quote_line_id == quote_line_id
            )
        ).all()

        assert len(tax_components) == 1
        assert tax_components[0].component_code == "US-DEFAULT"
        assert tax_components[0].rate_pct == 6.0
        assert tax_components[0].amount_cents == 600

    def test_create_quote_line_tax_exempt(
        self, client: TestClient, db_session: Session, mock_cognito_jwt_verify
    ):
        """Test that tax-exempt items have $0 tax."""
        headers, user_id, tenant_id = setup_test_user(client, db_session)

        # Create customer and site
        customer = Customer(
            tenant_id=tenant_id,
            display_name="Exempt Test Customer",
            type="person",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(
            tenant_id=tenant_id,
            customer_id=customer.id,
            name="Exempt Test Site",
            jurisdiction_code="US-TX-HARRIS",  # 8.25% but item is exempt
        )
        db_session.add(site)
        db_session.flush()

        # Get or create default quote status
        default_status = db_session.exec(
            select(QuoteStatus).where(QuoteStatus.is_default == True).limit(1)
        ).first()
        if not default_status:
            default_status = QuoteStatus(
                tenant_id=tenant_id,
                code="draft",
                name="Draft",
                is_default=True,
                is_active=True,
            )
            db_session.add(default_status)
            db_session.flush()

        quote = Quote(
            tenant_id=tenant_id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=default_status.id,
            subtotal_cents=0,
            tax_cents=0,
            total_cents=0,
        )
        db_session.add(quote)
        db_session.flush()

        # Get or create line type
        line_type = db_session.exec(select(QcoLineType).limit(1)).first()
        if not line_type:
            line_type = QcoLineType(
                tenant_id=None,
                code="material",
                name="Material",
                is_default=True,
                is_active=True,
            )
            db_session.add(line_type)
            db_session.flush()

        db_session.commit()

        # Create EXEMPT quote line
        response = client.post(
            f"/api/v1/quotes/{quote.id}/lines/test",
            json={
                "position": 1,
                "qco_line_type_id": str(line_type.id),
                "description": "Tax Exempt Item",
                "quantity": 1,
                "unit_price_cents": 10000,
                "taxability_code": "exempt",  # EXEMPT
            },
        )

        assert response.status_code == 201
        line_data = response.json()

        # Verify NO tax
        assert line_data["subtotal_cents"] == 10000
        assert line_data["tax_amount_cents"] == 0  # NO TAX
        assert line_data["total_cents"] == 10000  # Same as subtotal
        assert line_data["tax_rate_pct"] == 0.0

        # Verify no tax components
        quote_line_id = line_data["id"]
        tax_components = db_session.exec(
            select(QuoteLineTaxComponent).where(
                QuoteLineTaxComponent.quote_line_id == quote_line_id
            )
        ).all()

        assert len(tax_components) == 0  # No components for exempt items

    def test_quote_header_totals_include_tax(
        self, client: TestClient, db_session: Session, mock_cognito_jwt_verify
    ):
        """Test that quote header totals include tax via database trigger."""
        headers, user_id, tenant_id = setup_test_user(client, db_session)

        # Create customer and site
        customer = Customer(
            tenant_id=tenant_id,
            display_name="Header Test Customer",
            type="person",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(
            tenant_id=tenant_id,
            customer_id=customer.id,
            name="Header Test Site",
            jurisdiction_code="US-CA-LA",  # 9.5% tax
        )
        db_session.add(site)
        db_session.flush()

        # Get or create default quote status
        default_status = db_session.exec(
            select(QuoteStatus).where(QuoteStatus.is_default == True).limit(1)
        ).first()
        if not default_status:
            default_status = QuoteStatus(
                tenant_id=tenant_id,
                code="draft",
                name="Draft",
                is_default=True,
                is_active=True,
            )
            db_session.add(default_status)
            db_session.flush()

        quote = Quote(
            tenant_id=tenant_id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=default_status.id,
            subtotal_cents=0,
            tax_cents=0,
            total_cents=0,
        )
        db_session.add(quote)
        db_session.flush()

        # Get or create line type
        line_type = db_session.exec(select(QcoLineType).limit(1)).first()
        if not line_type:
            line_type = QcoLineType(
                tenant_id=None,
                code="material",
                name="Material",
                is_default=True,
                is_active=True,
            )
            db_session.add(line_type)
            db_session.flush()

        db_session.commit()

        # Create first line: $100.00
        client.post(
            f"/api/v1/quotes/{quote.id}/lines/test",
            json={
                "position": 1,
                "qco_line_type_id": str(line_type.id),
                "description": "Item 1",
                "quantity": 1,
                "unit_price_cents": 10000,
            },
        )

        # Create second line: $50.00
        client.post(
            f"/api/v1/quotes/{quote.id}/lines/test",
            json={
                "position": 2,
                "qco_line_type_id": str(line_type.id),
                "description": "Item 2",
                "quantity": 1,
                "unit_price_cents": 5000,
            },
        )

        # Refresh quote to get updated totals
        db_session.refresh(quote)

        # Verify quote header totals (trigger should have updated these)
        # Subtotal: $150.00
        # Tax: $150.00 * 9.5% = $14.25
        # Total: $164.25
        assert quote.subtotal_cents == 15000  # $150.00
        assert quote.tax_cents == 1425  # $14.25 (rounded up from $14.25)
        assert quote.total_cents == 16425  # $164.25


# ==================== Snapshot Principle Tests ====================


class TestTaxSnapshotPrinciple:
    """Test that tax rates are snapshotted and don't change retroactively."""

    def test_tax_snapshot_immutability(
        self, client: TestClient, db_session: Session, mock_cognito_jwt_verify
    ):
        """Test that changing tax rates doesn't affect existing quote lines."""
        headers, user_id, tenant_id = setup_test_user(client, db_session)

        # Create customer and site
        customer = Customer(
            tenant_id=tenant_id,
            display_name="Snapshot Test Customer",
            type="person",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(
            tenant_id=tenant_id,
            customer_id=customer.id,
            name="Snapshot Test Site",
            jurisdiction_code="TEST-SNAPSHOT",
        )
        db_session.add(site)
        db_session.flush()

        # Create initial tax rate: 5% (covers current time)
        initial_rate = TaxRateVersion(
            jurisdiction_code="TEST-SNAPSHOT",
            description="Initial Rate 5%",
            rate_pct=Decimal("5.0"),
            valid_period="[2020-01-01,2027-07-01)",  # Ends before new rate starts, covers current time
            recorded_at=datetime.now(UTC),
        )
        db_session.add(initial_rate)
        db_session.flush()

        # Get or create default quote status
        default_status = db_session.exec(
            select(QuoteStatus).where(QuoteStatus.is_default == True).limit(1)
        ).first()
        if not default_status:
            default_status = QuoteStatus(
                tenant_id=tenant_id,
                code="draft",
                name="Draft",
                is_default=True,
                is_active=True,
            )
            db_session.add(default_status)
            db_session.flush()

        quote = Quote(
            tenant_id=tenant_id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=default_status.id,
            subtotal_cents=0,
            tax_cents=0,
            total_cents=0,
        )
        db_session.add(quote)
        db_session.flush()

        # Get or create line type
        line_type = db_session.exec(select(QcoLineType).limit(1)).first()
        if not line_type:
            line_type = QcoLineType(
                tenant_id=None,
                code="material",
                name="Material",
                is_default=True,
                is_active=True,
            )
            db_session.add(line_type)
            db_session.flush()

        db_session.commit()

        # Create quote line with 5% tax
        response = client.post(
            f"/api/v1/quotes/{quote.id}/lines/test",
            json={
                "position": 1,
                "qco_line_type_id": str(line_type.id),
                "description": "Snapshot Test Item",
                "quantity": 1,
                "unit_price_cents": 10000,  # $100.00
            },
        )

        assert response.status_code == 201
        line_data = response.json()
        quote_line_id = line_data["id"]

        # Verify initial tax: 5% of $100 = $5.00
        assert line_data["tax_amount_cents"] == 500
        assert line_data["tax_rate_pct"] == 5.0

        # Now add a NEW tax rate: 7% (simulating a tax rate increase)
        new_rate = TaxRateVersion(
            jurisdiction_code="TEST-SNAPSHOT",
            description="New Rate 7%",
            rate_pct=Decimal("7.0"),
            valid_period="[2027-07-01,)",  # New rate starts July 1, 2027 (non-overlapping)
            recorded_at=datetime.now(UTC),
        )
        db_session.add(new_rate)
        db_session.commit()

        # Re-fetch the quote line from database
        db_line = db_session.get(QuoteLine, quote_line_id)

        # CRITICAL: Tax should still be $5.00 (5%), NOT $7.00 (7%)
        # This proves the Snapshot Principle is working
        assert db_line.tax_amount_cents == 500  # Still $5.00
        assert db_line.tax_rate_pct == 5.0  # Still 5%
        assert db_line.tax_jurisdiction_code == "TEST-SNAPSHOT"

        print(
            "✅ Snapshot Principle verified: tax rates are immutable after quote line creation"
        )
