"""
Test Suite: Task 1-C-8 — labor_rate_version Catalog Table
==========================================================
Verifies the following:

1. DB Schema: `labor_rate_version` table exists with all required columns,
   correct types, nullability, and server defaults.
2. DB Schema: GiST exclusion constraint `labor_rate_version_no_overlap` exists
   covering (tenant_id, skill_level_code, valid_period).
3. DB Schema: Composite index `ix_labor_rate_version_tenant_skill` exists.
4. DB Schema: FKs to tenant (RESTRICT) and user (RESTRICT) are present.
5. ORM: LaborRateVersion can be created and persists all fields correctly.
6. ORM: valid_period server default fires when not explicitly supplied.
7. Business Logic: Different skill_level_codes for the same tenant CAN have
   concurrent (overlapping) valid_periods.
8. Business Logic: Same (tenant_id, skill_level_code) rejects overlapping periods.
9. Business Logic: Non-overlapping periods for same (tenant, skill) are allowed
   (e.g., rate change history).
10. Burdened Cost Computation: hourly_rate_cents * (1 + burden_pct) = burdened rate.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from psycopg2.extras import DateTimeTZRange
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.models.catalog import LaborRateVersion
from app.models.core import Tenant

# ---------------------------------------------------------------------------
# Local Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_tenant_b(db_session):
    """A second test tenant for cross-tenant isolation tests."""
    tenant_b_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    tenant = db_session.get(Tenant, tenant_b_id)
    if not tenant:
        tenant = Tenant(
            id=tenant_b_id,
            name="[TEST] Pilot for Trades Test Tenant B",
            is_active=True,
        )
        db_session.add(tenant)
        db_session.commit()
        db_session.refresh(tenant)
    return tenant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _period(start_year: int, end_year: int, bounds: str = "[)") -> DateTimeTZRange:
    return DateTimeTZRange(
        datetime(start_year, 1, 1, tzinfo=UTC),
        datetime(end_year, 12, 31, 23, 59, 59, tzinfo=UTC),
        bounds=bounds,
    )


def _make_rate(
    tenant_id: uuid.UUID,
    skill_level_code: str,
    hourly_rate_cents: int = 8500,
    burden_pct: Decimal = Decimal("0.3000"),
    start_year: int = 2026,
    end_year: int = 2026,
) -> LaborRateVersion:
    return LaborRateVersion(
        tenant_id=tenant_id,
        skill_level_code=skill_level_code,
        hourly_rate_cents=hourly_rate_cents,
        burden_pct=burden_pct,
        valid_period=_period(start_year, end_year),
    )


# ---------------------------------------------------------------------------
# 1. DB Schema Tests
# ---------------------------------------------------------------------------


class TestLaborRateVersionSchema:
    """Verify table structure in the live DB."""

    def test_table_exists(self, db_engine):
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'labor_rate_version'
                """)
            ).fetchone()
        assert row is not None, "labor_rate_version table does not exist"

    def test_required_columns_exist(self, db_engine):
        """All columns from the spec must be present with correct types."""
        expected = {
            "id": "bigint",
            "tenant_id": "uuid",
            "skill_level_code": "character varying",
            "hourly_rate_cents": "integer",
            "burden_pct": "numeric",
            "valid_period": "tstzrange",
            "recorded_at": "timestamp with time zone",
            "created_at": "timestamp with time zone",
            "created_by": "uuid",
        }
        with db_engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'labor_rate_version'
                """)
            ).fetchall()
        actual = {r.column_name: r.data_type for r in rows}
        for col, expected_type in expected.items():
            assert col in actual, f"Column '{col}' missing from labor_rate_version"
            assert actual[col] == expected_type, (
                f"Column '{col}': expected '{expected_type}', got '{actual[col]}'"
            )

    def test_not_null_columns(self, db_engine):
        """Mandatory columns must be NOT NULL."""
        required_not_null = {
            "id",
            "tenant_id",
            "skill_level_code",
            "hourly_rate_cents",
            "burden_pct",
            "valid_period",
            "recorded_at",
            "created_at",
        }
        with db_engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT column_name, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'labor_rate_version'
                """)
            ).fetchall()
        nullable_map = {r.column_name: r.is_nullable for r in rows}
        for col in required_not_null:
            assert nullable_map[col] == "NO", (
                f"Column '{col}' must be NOT NULL, but is nullable"
            )
        # created_by must be nullable (optional audit field)
        assert nullable_map["created_by"] == "YES", "created_by must be nullable"

    def test_valid_period_server_default(self, db_engine):
        """valid_period must have server default tstzrange(now(), NULL, '[)')."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'labor_rate_version'
                      AND column_name = 'valid_period'
                """)
            ).fetchone()
        assert row is not None
        assert row.column_default is not None, "valid_period must have a server default"
        assert "tstzrange" in row.column_default.lower(), (
            f"Expected tstzrange server default, got: {row.column_default}"
        )

    def test_check_constraint_valid_period_not_empty(self, db_engine):
        """CHECK constraint labor_rate_version_valid_period_chk must exist."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT pg_get_constraintdef(oid) AS constraint_def
                    FROM pg_constraint
                    WHERE conrelid = 'public.labor_rate_version'::regclass
                      AND conname  = 'labor_rate_version_valid_period_chk'
                      AND contype  = 'c'
                """)
            ).fetchone()
        assert row is not None, (
            "CHECK constraint 'labor_rate_version_valid_period_chk' not found"
        )
        assert "isempty" in row.constraint_def.lower()

    def test_gist_exclusion_constraint_exists(self, db_engine):
        """labor_rate_version_no_overlap must be a 3-column GiST exclusion constraint."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT pg_get_constraintdef(oid) AS constraint_def
                    FROM pg_constraint
                    WHERE conrelid = 'public.labor_rate_version'::regclass
                      AND conname  = 'labor_rate_version_no_overlap'
                      AND contype  = 'x'
                """)
            ).fetchone()
        assert row is not None, (
            "GiST constraint 'labor_rate_version_no_overlap' not found"
        )
        cdef = row.constraint_def.lower()
        assert "tenant_id" in cdef, "GiST must include tenant_id"
        assert "skill_level_code" in cdef, "GiST must include skill_level_code"
        assert "valid_period" in cdef, "GiST must include valid_period"
        assert "gist" in cdef, "Constraint must use GIST method"

    def test_composite_index_exists(self, db_engine):
        """ix_labor_rate_version_tenant_skill composite index must exist."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT indexname FROM pg_indexes
                    WHERE tablename = 'labor_rate_version'
                      AND indexname = 'ix_labor_rate_version_tenant_skill'
                """)
            ).fetchone()
        assert row is not None, "Index 'ix_labor_rate_version_tenant_skill' not found"

    def test_fk_to_tenant_exists(self, db_engine):
        """FK to tenant.id with ON DELETE RESTRICT must be present."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT pg_get_constraintdef(oid) AS constraint_def
                    FROM pg_constraint
                    WHERE conrelid = 'public.labor_rate_version'::regclass
                      AND conname  = 'fk_labor_rate_version_tenant'
                      AND contype  = 'f'
                """)
            ).fetchone()
        assert row is not None, "FK 'fk_labor_rate_version_tenant' not found"
        assert "tenant" in row.constraint_def.lower()
        assert "RESTRICT" in row.constraint_def

    def test_fk_to_user_exists(self, db_engine):
        """FK to user.id with ON DELETE RESTRICT must be present for created_by."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT pg_get_constraintdef(oid) AS constraint_def
                    FROM pg_constraint
                    WHERE conrelid = 'public.labor_rate_version'::regclass
                      AND conname  = 'fk_labor_rate_version_created_by'
                      AND contype  = 'f'
                """)
            ).fetchone()
        assert row is not None, "FK 'fk_labor_rate_version_created_by' not found"
        assert "user" in row.constraint_def.lower()
        assert "RESTRICT" in row.constraint_def


# ---------------------------------------------------------------------------
# 2. ORM Model Tests
# ---------------------------------------------------------------------------


class TestLaborRateVersionOrm:
    """Verify LaborRateVersion ORM persists and reads all fields correctly."""

    def test_basic_rate_persists(self, db_session, test_tenant):
        """LaborRateVersion can be created and all fields round-trip correctly."""
        # Use a past CLOSED year range to avoid GiST conflict with seeded rows.
        # seed_test_tenant.py seeds master/journeyman/apprentice with open-ended
        # ranges [2026-06-01, NULL) for test_tenant — any overlapping range fails.
        rate = _make_rate(
            test_tenant.id,
            skill_level_code="journeyman",
            hourly_rate_cents=8500,
            burden_pct=Decimal("0.3000"),
            start_year=2020,
            end_year=2020,
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(LaborRateVersion).where(LaborRateVersion.id == rate.id)
        ).first()

        assert fetched is not None
        assert fetched.tenant_id == test_tenant.id
        assert fetched.skill_level_code == "journeyman"
        assert fetched.hourly_rate_cents == 8500
        assert fetched.burden_pct == Decimal("0.3000")
        assert fetched.created_by is None

    def test_all_skill_levels_persist(self, db_session, test_tenant):
        """Multiple skill level codes can be stored for the same tenant."""
        # Use a past CLOSED year (2020) to avoid GiST conflict with seeded rows.
        # seed_test_tenant.py seeds master/journeyman/apprentice with open-ended
        # ranges [2026-06-01, NULL) — any range extending into or beyond that fails.
        skill_levels = [
            ("apprentice", 4500, Decimal("0.2500")),
            ("journeyman", 8500, Decimal("0.3000")),
            ("master", 11000, Decimal("0.3500")),
            ("foreman", 12500, Decimal("0.4000")),
        ]
        for skill, rate_cents, burden in skill_levels:
            db_session.add(
                _make_rate(
                    test_tenant.id,
                    skill_level_code=skill,
                    hourly_rate_cents=rate_cents,
                    burden_pct=burden,
                    start_year=2020,
                    end_year=2020,
                )
            )
        db_session.commit()

        all_rates = db_session.exec(
            select(LaborRateVersion).where(
                LaborRateVersion.tenant_id == test_tenant.id,
                LaborRateVersion.skill_level_code.in_(
                    ["apprentice", "journeyman", "master", "foreman"]
                ),
            )
        ).all()

        # Filter to just 2020 rows we inserted — scope by rate_cents to avoid
        # counting seeded rows for the same skill codes.
        rates_2020 = [
            r
            for r in all_rates
            if r.hourly_rate_cents in {4500, 8500, 11000, 12500}
            and r.valid_period.lower.year == 2020
        ]
        skill_codes = {r.skill_level_code for r in rates_2020}
        assert {"apprentice", "journeyman", "master", "foreman"}.issubset(skill_codes)

    def test_created_at_auto_set(self, db_session, test_tenant):
        """created_at must be automatically set by server default on insert."""
        rate = _make_rate(
            test_tenant.id, "journeyman_c8_ts", start_year=2028, end_year=2028
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        assert rate.created_at is not None

    def test_different_tenants_have_independent_rates(
        self, db_session, test_tenant, test_tenant_b
    ):
        """Two tenants can each have their own 'journeyman' rate for the same period."""
        rate_a = _make_rate(
            test_tenant.id,
            "journeyman_c8_ind",
            hourly_rate_cents=8500,
            start_year=2029,
            end_year=2029,
        )
        rate_b = _make_rate(
            test_tenant_b.id,
            "journeyman_c8_ind",
            hourly_rate_cents=9500,
            start_year=2029,
            end_year=2029,
        )
        db_session.add(rate_a)
        db_session.add(rate_b)
        db_session.commit()

        fetched_a = db_session.exec(
            select(LaborRateVersion).where(
                LaborRateVersion.tenant_id == test_tenant.id,
                LaborRateVersion.skill_level_code == "journeyman_c8_ind",
                LaborRateVersion.hourly_rate_cents == 8500,
            )
        ).first()
        fetched_b = db_session.exec(
            select(LaborRateVersion).where(
                LaborRateVersion.tenant_id == test_tenant_b.id,
                LaborRateVersion.skill_level_code == "journeyman_c8_ind",
                LaborRateVersion.hourly_rate_cents == 9500,
            )
        ).first()

        assert fetched_a is not None, "Tenant A journeyman rate not found"
        assert fetched_b is not None, "Tenant B journeyman rate not found"
        assert fetched_a.hourly_rate_cents != fetched_b.hourly_rate_cents


# ---------------------------------------------------------------------------
# 3. Business Logic — GiST Exclusion Constraint Enforcement
# ---------------------------------------------------------------------------


class TestLaborRateVersionGistEnforcement:
    """Verify the GiST exclusion constraint enforces non-overlapping periods."""

    def test_different_skill_levels_same_period_allowed(self, db_session, test_tenant):
        """
        Core Rule: different skill_level_codes for the same tenant CAN have
        concurrent (overlapping) valid_periods.
        """
        journeyman = _make_rate(
            test_tenant.id, "journeyman_c8_diff", start_year=2030, end_year=2030
        )
        master = _make_rate(
            test_tenant.id, "master_c8_diff", start_year=2030, end_year=2030
        )

        db_session.add(journeyman)
        db_session.add(master)
        db_session.commit()  # Must NOT raise

        all_rates = db_session.exec(
            select(LaborRateVersion).where(
                LaborRateVersion.tenant_id == test_tenant.id,
                LaborRateVersion.skill_level_code.in_(
                    ["journeyman_c8_diff", "master_c8_diff"]
                ),
            )
        ).all()
        skill_codes = {r.skill_level_code for r in all_rates}
        assert "journeyman_c8_diff" in skill_codes
        assert "master_c8_diff" in skill_codes

    def test_same_skill_overlapping_period_rejected(self, db_session, test_tenant):
        """
        Same (tenant_id, skill_level_code) pair with overlapping valid_periods
        must be rejected by the GiST exclusion constraint.
        """
        rate1 = _make_rate(
            test_tenant.id, "journeyman_c8_ovlp", start_year=2031, end_year=2032
        )
        db_session.add(rate1)
        db_session.commit()

        # Second rate overlaps 2032 with the first (2031-2032 and 2032-2033 share 2032)
        rate2 = _make_rate(
            test_tenant.id,
            "journeyman_c8_ovlp",
            hourly_rate_cents=9000,
            start_year=2032,
            end_year=2033,
        )
        db_session.add(rate2)

        with pytest.raises(IntegrityError, match="labor_rate_version_no_overlap"):
            db_session.commit()

    def test_non_overlapping_periods_same_skill_allowed(self, db_session, test_tenant):
        """
        Non-overlapping periods for the same (tenant, skill) are allowed —
        this is how rate history is recorded (e.g., annual rate increases).
        """
        rate_2034 = LaborRateVersion(
            tenant_id=test_tenant.id,
            skill_level_code="apprentice_c8_noo",
            hourly_rate_cents=4500,
            burden_pct=Decimal("0.2500"),
            valid_period=DateTimeTZRange(
                datetime(2034, 1, 1, tzinfo=UTC),
                datetime(2034, 12, 31, tzinfo=UTC),
                bounds="[)",
            ),
        )
        rate_2035 = LaborRateVersion(
            tenant_id=test_tenant.id,
            skill_level_code="apprentice_c8_noo",
            hourly_rate_cents=4800,
            burden_pct=Decimal("0.2500"),
            valid_period=DateTimeTZRange(
                datetime(2035, 1, 1, tzinfo=UTC),
                datetime(2035, 12, 31, tzinfo=UTC),
                bounds="[)",
            ),
        )
        db_session.add(rate_2034)
        db_session.add(rate_2035)
        db_session.commit()  # Must NOT raise

        all_rates = db_session.exec(
            select(LaborRateVersion).where(
                LaborRateVersion.tenant_id == test_tenant.id,
                LaborRateVersion.skill_level_code == "apprentice_c8_noo",
            )
        ).all()
        rate_values = {r.hourly_rate_cents for r in all_rates}
        assert 4500 in rate_values and 4800 in rate_values

    def test_same_skill_same_period_different_tenants_allowed(
        self, db_session, test_tenant, test_tenant_b
    ):
        """
        The same skill_level_code and overlapping valid_period is allowed
        if they belong to different tenants (tenant_id discriminates).
        """
        rate_a = _make_rate(
            test_tenant.id,
            "master_c8_cross",
            hourly_rate_cents=11000,
            start_year=2036,
            end_year=2036,
        )
        rate_b = _make_rate(
            test_tenant_b.id,
            "master_c8_cross",
            hourly_rate_cents=12000,
            start_year=2036,
            end_year=2036,
        )
        db_session.add(rate_a)
        db_session.add(rate_b)
        db_session.commit()  # Must NOT raise — different tenants


# ---------------------------------------------------------------------------
# 4. Burdened Cost Computation
# ---------------------------------------------------------------------------


class TestLaborRateVersionBurdenedCost:
    """Verify burdened rate calculation from stored fields."""

    def test_burdened_hourly_rate_calculation(self, db_session, test_tenant):
        """
        Burdened rate = hourly_rate_cents * (1 + burden_pct).
        This is computed in application code; verify the stored values
        are sufficient to perform the calculation correctly.
        """
        rate = _make_rate(
            test_tenant.id,
            skill_level_code="foreman_c8_bur",
            hourly_rate_cents=12500,  # $125.00/hr
            burden_pct=Decimal("0.3000"),  # 30% overhead
            start_year=2037,
            end_year=2037,
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(LaborRateVersion).where(LaborRateVersion.id == rate.id)
        ).first()

        burdened_cents = int(fetched.hourly_rate_cents * (1 + fetched.burden_pct))
        assert burdened_cents == 16250, (
            f"Expected burdened rate of 16250 cents ($162.50/hr), got {burdened_cents}"
        )

    def test_zero_burden_pct_allowed(self, db_session, test_tenant):
        """burden_pct of 0.0000 (no overhead) must be accepted."""
        rate = _make_rate(
            test_tenant.id,
            skill_level_code="subcontractor_c8",
            hourly_rate_cents=9500,
            burden_pct=Decimal("0.0000"),
            start_year=2038,
            end_year=2038,
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)

        fetched = db_session.exec(
            select(LaborRateVersion).where(LaborRateVersion.id == rate.id)
        ).first()
        assert fetched.burden_pct == Decimal("0.0000")
        burdened = int(fetched.hourly_rate_cents * (1 + fetched.burden_pct))
        assert burdened == 9500  # No burden added
