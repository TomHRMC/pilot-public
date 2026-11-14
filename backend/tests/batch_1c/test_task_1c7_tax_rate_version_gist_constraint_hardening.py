"""
Test Suite: Task 1-C-7 — tax_rate_version GiST Constraint Hardening
====================================================================
Verifies the following:

1. DB Schema: `taxability_code` (VARCHAR, NOT NULL, default 'taxable') column
   is present in the live `tax_rate_version` table.
2. DB Schema: FK constraint `fk_tax_rate_version_taxability_code` references
   `taxability_code(code)` with ON DELETE RESTRICT.
3. DB Schema: GiST exclusion constraint `tax_rate_version_no_overlap` now
   includes `taxability_code` as a 3rd discriminator.
4. ORM: TaxRateVersion persists with explicit taxability_code values.
5. ORM: Default taxability_code is 'taxable' when not supplied.
6. Business Logic: Same jurisdiction CAN hold concurrent rates for different
   taxability codes ('taxable' and 'exempt') — the primary goal of this task.
7. Exclusion: Overlapping periods for the SAME jurisdiction + taxability_code
   are still blocked by the GiST constraint.
8. FK Enforcement: An invalid taxability_code value is rejected at DB level.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from psycopg2.extras import DateTimeTZRange
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.models.catalog import TaxRateVersion

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _period(start_year: int, end_year: int) -> DateTimeTZRange:
    """Build a non-empty tstzrange for testing."""
    return DateTimeTZRange(
        datetime(start_year, 1, 1, tzinfo=UTC),
        datetime(end_year, 12, 31, tzinfo=UTC),
    )


def _make_tax_rate(
    jurisdiction_code: str,
    taxability_code: str = "taxable",
    rate_pct: Decimal = Decimal("8.2500"),
    start_year: int = 2026,
    end_year: int = 2026,
) -> TaxRateVersion:
    """Factory: build a TaxRateVersion for testing."""
    return TaxRateVersion(
        jurisdiction_code=jurisdiction_code,
        taxability_code=taxability_code,
        description=f"Test rate: {jurisdiction_code} / {taxability_code}",
        rate_pct=rate_pct,
        valid_period=_period(start_year, end_year),
    )


# ---------------------------------------------------------------------------
# 1. DB Schema Tests
# ---------------------------------------------------------------------------


class TestTaxRateVersionGistSchema:
    """Verify taxability_code column and updated GiST constraint in the live DB."""

    def test_taxability_code_column_exists(self, db_engine):
        """taxability_code must be present, VARCHAR, NOT NULL, with server default 'taxable'."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name   = 'tax_rate_version'
                      AND column_name  = 'taxability_code'
                """)
            ).fetchone()
        assert row is not None, (
            "Column 'taxability_code' is missing from tax_rate_version"
        )
        assert row.data_type == "character varying", (
            f"Expected character varying, got {row.data_type}"
        )
        assert row.is_nullable == "NO", "taxability_code must be NOT NULL"
        assert row.column_default is not None, (
            "taxability_code must have a server default of 'taxable'"
        )
        assert "taxable" in row.column_default, (
            f"Expected server default to contain 'taxable', got {row.column_default}"
        )

    def test_fk_to_taxability_code_lookup_exists(self, db_engine):
        """FK constraint fk_tax_rate_version_taxability_code must reference taxability_code(code)."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT conname, pg_get_constraintdef(oid) AS constraint_def
                    FROM pg_constraint
                    WHERE conrelid  = 'public.tax_rate_version'::regclass
                      AND conname   = 'fk_tax_rate_version_taxability_code'
                      AND contype   = 'f'
                """)
            ).fetchone()
        assert row is not None, (
            "FK 'fk_tax_rate_version_taxability_code' is missing from tax_rate_version"
        )
        assert "taxability_code" in row.constraint_def, (
            f"FK definition does not reference taxability_code table: {row.constraint_def}"
        )
        assert "RESTRICT" in row.constraint_def, (
            f"FK must use ON DELETE RESTRICT, got: {row.constraint_def}"
        )

    def test_gist_constraint_includes_taxability_code(self, db_engine):
        """GiST exclusion constraint must include jurisdiction_code, taxability_code, AND valid_period."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT pg_get_constraintdef(oid) AS constraint_def
                    FROM pg_constraint
                    WHERE conrelid = 'public.tax_rate_version'::regclass
                      AND conname  = 'tax_rate_version_no_overlap'
                      AND contype  = 'x'
                """)
            ).fetchone()
        assert row is not None, (
            "Exclusion constraint 'tax_rate_version_no_overlap' not found"
        )
        constraint_def = row.constraint_def.lower()
        assert "jurisdiction_code" in constraint_def, (
            "GiST constraint must include jurisdiction_code"
        )
        assert "taxability_code" in constraint_def, (
            "GiST constraint must include taxability_code — Task 1-C-7 hardening not applied"
        )
        assert "valid_period" in constraint_def, (
            "GiST constraint must include valid_period"
        )
        # Verify it is a GiST constraint, not btree
        assert "gist" in constraint_def, "Constraint must use GIST method"

    def test_old_2_column_gist_replaced(self, db_engine):
        """Confirm the old 2-column constraint (without taxability_code) is gone."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT pg_get_constraintdef(oid) AS constraint_def
                    FROM pg_constraint
                    WHERE conrelid = 'public.tax_rate_version'::regclass
                      AND conname  = 'tax_rate_version_no_overlap'
                      AND contype  = 'x'
                """)
            ).fetchone()
        assert row is not None
        # Old constraint had only 2 elements — jurisdiction_code and valid_period.
        # New constraint has 3. Verify taxability_code is present so we know
        # the old 2-column version was replaced.
        assert "taxability_code" in row.constraint_def.lower(), (
            "GiST constraint still appears to be the old 2-column version without taxability_code"
        )


# ---------------------------------------------------------------------------
# 2. ORM Model Tests
# ---------------------------------------------------------------------------


class TestTaxRateVersionOrmTaxabilityCode:
    """Verify TaxRateVersion ORM persists and reads taxability_code correctly."""

    def test_taxability_code_defaults_to_taxable(self, db_session):
        """TaxRateVersion created without explicit taxability_code defaults to 'taxable'."""
        rate = TaxRateVersion(
            jurisdiction_code="US-TX-HARRIS-DEFAULT",
            description="Default taxability test",
            rate_pct=Decimal("8.2500"),
            valid_period=_period(2027, 2027),
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(TaxRateVersion).where(TaxRateVersion.id == rate.id)
        ).first()
        assert fetched is not None
        assert fetched.taxability_code == "taxable", (
            f"Default taxability_code should be 'taxable', got '{fetched.taxability_code}'"
        )

    def test_taxable_code_persists_explicitly(self, db_session):
        """TaxRateVersion with taxability_code='taxable' persists correctly."""
        rate = _make_tax_rate("US-TX-HARRIS-T7", taxability_code="taxable")
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(TaxRateVersion).where(TaxRateVersion.id == rate.id)
        ).first()
        assert fetched.taxability_code == "taxable"

    def test_exempt_code_persists(self, db_session):
        """TaxRateVersion with taxability_code='exempt' persists correctly."""
        rate = _make_tax_rate(
            "US-TX-HARRIS-E7", taxability_code="exempt", rate_pct=Decimal("0.0000")
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(TaxRateVersion).where(TaxRateVersion.id == rate.id)
        ).first()
        assert fetched.taxability_code == "exempt"

    def test_zero_rated_code_persists(self, db_session):
        """TaxRateVersion with taxability_code='zero_rated' persists correctly."""
        rate = _make_tax_rate(
            "US-TX-HARRIS-Z7", taxability_code="zero_rated", rate_pct=Decimal("0.0000")
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(TaxRateVersion).where(TaxRateVersion.id == rate.id)
        ).first()
        assert fetched.taxability_code == "zero_rated"


# ---------------------------------------------------------------------------
# 3. Business Logic — Core Use Case of Task 1-C-7
# ---------------------------------------------------------------------------


class TestTaxRateVersionConcurrentRatesByTaxability:
    """
    Core business rule: the same jurisdiction can hold concurrent (overlapping)
    valid_period rates as long as they have different taxability_codes.

    This is required in states like TX and CA where labor is taxed differently
    from materials.
    """

    def test_same_jurisdiction_different_taxability_codes_allowed(self, db_session):
        """
        A single jurisdiction CAN hold concurrent rates for 'taxable' and 'exempt'
        over the same time period — the primary use case unlocked by Task 1-C-7.
        """
        taxable_rate = _make_tax_rate(
            "US-TX-MATERIALS-C7",
            taxability_code="taxable",
            rate_pct=Decimal("8.2500"),
            start_year=2026,
            end_year=2026,
        )
        exempt_rate = _make_tax_rate(
            "US-TX-MATERIALS-C7",
            taxability_code="exempt",
            rate_pct=Decimal("0.0000"),
            start_year=2026,
            end_year=2026,
        )

        db_session.add(taxable_rate)
        db_session.add(exempt_rate)
        db_session.commit()  # Must NOT raise — different taxability_code allows overlap

        fetched_taxable = db_session.exec(
            select(TaxRateVersion).where(
                TaxRateVersion.jurisdiction_code == "US-TX-MATERIALS-C7",
                TaxRateVersion.taxability_code == "taxable",
            )
        ).first()
        fetched_exempt = db_session.exec(
            select(TaxRateVersion).where(
                TaxRateVersion.jurisdiction_code == "US-TX-MATERIALS-C7",
                TaxRateVersion.taxability_code == "exempt",
            )
        ).first()

        assert fetched_taxable is not None, (
            "taxable rate for US-TX-MATERIALS-C7 not found"
        )
        assert fetched_exempt is not None, (
            "exempt rate for US-TX-MATERIALS-C7 not found"
        )
        assert fetched_taxable.rate_pct == Decimal("8.2500")
        assert fetched_exempt.rate_pct == Decimal("0.0000")

    def test_labor_materials_split_jurisdiction_rates(self, db_session):
        """
        Real-world scenario: TX contractor has separate rates for labor (exempt)
        and materials (taxable) in Harris County.
        Both rates should coexist over the same period.
        """
        labor_rate = _make_tax_rate(
            "US-TX-HARRIS-LABOR",
            taxability_code="exempt",  # TX labor is not taxable
            rate_pct=Decimal("0.0000"),
            start_year=2026,
            end_year=2028,
        )
        materials_rate = _make_tax_rate(
            "US-TX-HARRIS-LABOR",
            taxability_code="taxable",  # TX materials ARE taxable
            rate_pct=Decimal("8.2500"),
            start_year=2026,
            end_year=2028,
        )

        db_session.add(labor_rate)
        db_session.add(materials_rate)
        db_session.commit()

        all_rates = db_session.exec(
            select(TaxRateVersion).where(
                TaxRateVersion.jurisdiction_code == "US-TX-HARRIS-LABOR"
            )
        ).all()

        assert len(all_rates) == 2, (
            f"Expected 2 rates for US-TX-HARRIS-LABOR, found {len(all_rates)}"
        )
        codes = {r.taxability_code for r in all_rates}
        assert codes == {"taxable", "exempt"}

    def test_three_concurrent_taxability_codes_allowed(self, db_session):
        """
        A jurisdiction can hold all 3 taxability codes concurrently:
        taxable, exempt, zero_rated — each with different rates over the same period.
        """
        rates = [
            _make_tax_rate("US-CA-SF-ALL", "taxable", Decimal("10.7500"), 2026, 2026),
            _make_tax_rate("US-CA-SF-ALL", "exempt", Decimal("0.0000"), 2026, 2026),
            _make_tax_rate("US-CA-SF-ALL", "zero_rated", Decimal("0.0000"), 2026, 2026),
        ]
        for r in rates:
            db_session.add(r)
        db_session.commit()

        all_rates = db_session.exec(
            select(TaxRateVersion).where(
                TaxRateVersion.jurisdiction_code == "US-CA-SF-ALL"
            )
        ).all()

        assert len(all_rates) == 3, (
            f"Expected 3 concurrent taxability codes, found {len(all_rates)}"
        )
        codes = {r.taxability_code for r in all_rates}
        assert codes == {"taxable", "exempt", "zero_rated"}


# ---------------------------------------------------------------------------
# 4. Exclusion Constraint Enforcement — Overlap Still Blocked
# ---------------------------------------------------------------------------


class TestTaxRateVersionGistExclusionEnforcement:
    """
    Verify the 3-column GiST constraint still blocks overlapping valid_periods
    for the same (jurisdiction_code, taxability_code) pair.
    """

    def test_same_jurisdiction_same_taxability_overlapping_period_rejected(
        self, db_session
    ):
        """
        Two 'taxable' rates for the same jurisdiction with overlapping periods
        must still be rejected by the GiST exclusion constraint.
        """
        rate1 = _make_tax_rate(
            "US-TX-HARRIS-OVERLAP",
            taxability_code="taxable",
            rate_pct=Decimal("8.2500"),
            start_year=2026,
            end_year=2027,
        )
        db_session.add(rate1)
        db_session.commit()

        # Second rate overlaps: 2027-01-01 to 2028-12-31 overlaps with 2026-2027
        rate2 = _make_tax_rate(
            "US-TX-HARRIS-OVERLAP",
            taxability_code="taxable",
            rate_pct=Decimal("9.0000"),
            start_year=2027,
            end_year=2028,
        )
        db_session.add(rate2)

        with pytest.raises(IntegrityError, match="tax_rate_version_no_overlap"):
            db_session.commit()

    def test_non_overlapping_periods_same_jurisdiction_taxability_allowed(
        self, db_session
    ):
        """
        Non-overlapping valid_periods for the same jurisdiction + taxability_code
        must be allowed (e.g., rate change from 2026 to 2027).
        """
        rate_2026 = TaxRateVersion(
            jurisdiction_code="US-TX-HARRIS-NOOVLP",
            taxability_code="taxable",
            rate_pct=Decimal("8.2500"),
            valid_period=DateTimeTZRange(
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2026, 12, 31, tzinfo=UTC),
                bounds="[)",
            ),
        )
        rate_2027 = TaxRateVersion(
            jurisdiction_code="US-TX-HARRIS-NOOVLP",
            taxability_code="taxable",
            rate_pct=Decimal("8.5000"),
            valid_period=DateTimeTZRange(
                datetime(2027, 1, 1, tzinfo=UTC),
                datetime(2027, 12, 31, tzinfo=UTC),
                bounds="[)",
            ),
        )
        db_session.add(rate_2026)
        db_session.add(rate_2027)
        db_session.commit()  # Must NOT raise — periods are adjacent, not overlapping

        all_rates = db_session.exec(
            select(TaxRateVersion).where(
                TaxRateVersion.jurisdiction_code == "US-TX-HARRIS-NOOVLP",
                TaxRateVersion.taxability_code == "taxable",
            )
        ).all()
        assert len(all_rates) == 2


# ---------------------------------------------------------------------------
# 5. FK Enforcement — Invalid taxability_code Rejected
# ---------------------------------------------------------------------------


class TestTaxRateVersionTaxabilityCodeFk:
    """Verify the FK to taxability_code lookup table is enforced at DB level."""

    def test_invalid_taxability_code_rejected(self, db_session):
        """
        Inserting a TaxRateVersion with an invalid taxability_code (not in the
        taxability_code lookup table) must raise an IntegrityError.
        """
        rate = _make_tax_rate(
            "US-TX-HARRIS-INVALID",
            taxability_code="invalid_code_not_in_lookup",
        )
        db_session.add(rate)

        with pytest.raises(IntegrityError):
            db_session.commit()
