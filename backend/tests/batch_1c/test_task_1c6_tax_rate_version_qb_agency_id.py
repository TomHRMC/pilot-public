"""
Test Suite: Task 1-C-6 — tax_rate_version QB Tax Agency ID Column
=================================================================
Verifies the following:

1. DB Schema: `external_tax_agency_id` (VARCHAR(100), nullable) is present
   in the live `tax_rate_version` table with correct type and nullability.
2. ORM Model: TaxRateVersion model exposes the field and it round-trips correctly.
3. Null Default: TaxRateVersion can be persisted WITHOUT the QB agency ID (it is optional).
4. Field Length: external_tax_agency_id is limited to VARCHAR(100).
5. Multiple Jurisdictions: Different jurisdictions can each have their own QB agency ID.
6. Update: The field can be set after initial creation (mapped via integrations UI later).
"""

from datetime import UTC, datetime
from decimal import Decimal

from psycopg2.extras import DateTimeTZRange
from sqlalchemy import text
from sqlmodel import select

from app.models.catalog import TaxRateVersion

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_tax_rate(
    jurisdiction_code: str,
    rate_pct: Decimal = Decimal("8.2500"),
    external_tax_agency_id: str = None,
    year_offset: int = 0,
) -> TaxRateVersion:
    """Factory: build a TaxRateVersion instance with an optional QB agency ID."""
    base_year = 2026 + year_offset
    return TaxRateVersion(
        jurisdiction_code=jurisdiction_code,
        description=f"Test rate for {jurisdiction_code}",
        rate_pct=rate_pct,
        external_tax_agency_id=external_tax_agency_id,
        valid_period=DateTimeTZRange(
            datetime(base_year, 1, 1, tzinfo=UTC),
            datetime(base_year, 12, 31, tzinfo=UTC),
        ),
    )


# ---------------------------------------------------------------------------
# 1. DB Schema Tests — query information_schema directly
# ---------------------------------------------------------------------------


class TestTaxRateVersionQbAgencyIdSchema:
    """Verify external_tax_agency_id exists in the live DB with correct type."""

    def test_external_tax_agency_id_column_exists(self, db_engine):
        """external_tax_agency_id must be present, VARCHAR(100), nullable."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_name, data_type,
                           character_maximum_length, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'tax_rate_version'
                      AND column_name = 'external_tax_agency_id'
                """)
            ).fetchone()
        assert row is not None, (
            "Column 'external_tax_agency_id' is missing from tax_rate_version"
        )
        assert row.data_type == "character varying", (
            f"Expected character varying, got {row.data_type}"
        )
        assert row.character_maximum_length == 100, (
            f"Expected VARCHAR(100), got VARCHAR({row.character_maximum_length})"
        )
        assert row.is_nullable == "YES", "external_tax_agency_id must be nullable"

    def test_no_server_default_on_external_tax_agency_id(self, db_engine):
        """external_tax_agency_id must have no server default — NULL is the signal for 'not yet mapped'."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_default
                    FROM information_schema.columns
                    WHERE table_name = 'tax_rate_version'
                      AND column_name = 'external_tax_agency_id'
                """)
            ).fetchone()
        assert row is not None
        assert row.column_default is None, (
            "external_tax_agency_id should have no server default — "
            "NULL signals 'not yet mapped to a QB Tax Agency'"
        )


# ---------------------------------------------------------------------------
# 2. ORM Model Tests — round-trip through TaxRateVersion model
# ---------------------------------------------------------------------------


class TestTaxRateVersionOrmQbAgencyId:
    """Verify TaxRateVersion ORM exposes and persists external_tax_agency_id correctly."""

    def test_tax_rate_with_agency_id_persists(self, db_session):
        """TaxRateVersion with external_tax_agency_id set round-trips correctly."""
        rate = _make_tax_rate(
            jurisdiction_code="US-TX-HARRIS-C6",
            rate_pct=Decimal("8.2500"),
            external_tax_agency_id="TAX_AGENCY_1",
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(TaxRateVersion).where(TaxRateVersion.id == rate.id)
        ).first()
        assert fetched is not None
        assert fetched.external_tax_agency_id == "TAX_AGENCY_1"

    def test_tax_rate_without_agency_id_defaults_to_null(self, db_session):
        """TaxRateVersion persisted without QB agency ID has None for the field."""
        rate = _make_tax_rate(
            jurisdiction_code="US-CA-SF-C6",
            rate_pct=Decimal("10.2500"),
            # Intentionally omit external_tax_agency_id
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(TaxRateVersion).where(TaxRateVersion.id == rate.id)
        ).first()
        assert fetched is not None
        assert fetched.external_tax_agency_id is None, (
            "external_tax_agency_id should be None when not provided"
        )

    def test_agency_id_accepts_various_qb_formats(self, db_session):
        """external_tax_agency_id accepts various QB Online agency ID formats."""
        test_cases = [
            ("US-TX-HARRIS-V1", "TAX_AGENCY_1"),
            ("US-CA-LA-V1", "QB:TaxCode:US-CA-LA"),
            ("US-WA-KING-V1", "145"),  # Numeric QB internal ID
            ("US-NY-NYC-V1", "QuickBooks_TaxAgency_NYC_8875"),  # Long format
        ]
        for jur_code, agency_id in test_cases:
            rate = _make_tax_rate(
                jurisdiction_code=jur_code,
                external_tax_agency_id=agency_id,
            )
            db_session.add(rate)
        db_session.commit()

        # All 4 should have persisted with no error
        for jur_code, agency_id in test_cases:
            fetched = db_session.exec(
                select(TaxRateVersion).where(
                    TaxRateVersion.jurisdiction_code == jur_code
                )
            ).first()
            assert fetched is not None
            assert fetched.external_tax_agency_id == agency_id

    def test_agency_id_max_length_boundary(self, db_session):
        """external_tax_agency_id at exactly 100 characters must be accepted."""
        agency_id_100 = "A" * 100  # exactly VARCHAR(100) limit
        rate = _make_tax_rate(
            jurisdiction_code="US-FL-MIAMI-C6",
            external_tax_agency_id=agency_id_100,
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(TaxRateVersion).where(TaxRateVersion.id == rate.id)
        ).first()
        assert fetched is not None
        assert fetched.external_tax_agency_id == agency_id_100
        assert len(fetched.external_tax_agency_id) == 100

    def test_agency_id_can_be_set_after_creation(self, db_session):
        """
        external_tax_agency_id can be populated after initial creation.
        Simulates the QB integrations UI mapping flow: create rate first,
        then associate the QB Tax Agency ID once the QB account is connected.
        """
        # Step 1: Create rate without QB mapping
        rate = _make_tax_rate(
            jurisdiction_code="US-AZ-PHOENIX-C6",
            rate_pct=Decimal("8.6000"),
            # No QB agency ID yet
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)
        assert rate.external_tax_agency_id is None

        # Step 2: QB integration connected — map the agency ID
        rate.external_tax_agency_id = "TAX_AGENCY_AZ_PHOENIX"
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(TaxRateVersion).where(TaxRateVersion.id == rate.id)
        ).first()
        assert fetched.external_tax_agency_id == "TAX_AGENCY_AZ_PHOENIX"

    def test_multiple_jurisdictions_have_independent_agency_ids(self, db_session):
        """
        Different jurisdictions can have different QB Tax Agency IDs independently.
        Critical for multi-jurisdiction contractors who collect tax for multiple jurisdictions.
        """
        rates = [
            _make_tax_rate(
                "US-TX-HARRIS-IND", "8.2500", "AGENCY_TX_HARRIS", year_offset=0
            ),
            _make_tax_rate(
                "US-TX-DALLAS-IND", "8.0000", "AGENCY_TX_DALLAS", year_offset=0
            ),
            _make_tax_rate(
                "US-TX-BEXAR-IND", "8.1250", None, year_offset=0
            ),  # Not yet mapped
        ]
        for r in rates:
            db_session.add(r)
        db_session.commit()

        harris = db_session.exec(
            select(TaxRateVersion).where(
                TaxRateVersion.jurisdiction_code == "US-TX-HARRIS-IND"
            )
        ).first()
        dallas = db_session.exec(
            select(TaxRateVersion).where(
                TaxRateVersion.jurisdiction_code == "US-TX-DALLAS-IND"
            )
        ).first()
        bexar = db_session.exec(
            select(TaxRateVersion).where(
                TaxRateVersion.jurisdiction_code == "US-TX-BEXAR-IND"
            )
        ).first()

        assert harris.external_tax_agency_id == "AGENCY_TX_HARRIS"
        assert dallas.external_tax_agency_id == "AGENCY_TX_DALLAS"
        assert bexar.external_tax_agency_id is None  # Not yet mapped — QB not connected

    def test_agency_id_cleared_to_null(self, db_session):
        """external_tax_agency_id can be reset to None (e.g., QB account disconnected)."""
        rate = _make_tax_rate(
            jurisdiction_code="US-NV-CLARK-C6",
            external_tax_agency_id="TAX_AGENCY_NV",
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)
        assert rate.external_tax_agency_id == "TAX_AGENCY_NV"

        # QB account disconnected — clear the mapping
        rate.external_tax_agency_id = None
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(TaxRateVersion).where(TaxRateVersion.id == rate.id)
        ).first()
        assert fetched.external_tax_agency_id is None
