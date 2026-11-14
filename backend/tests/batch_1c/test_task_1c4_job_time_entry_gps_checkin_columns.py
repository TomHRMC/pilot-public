"""
Test Suite: Task 1-C-4 — job_time_entry GPS Check-In Columns
=============================================================
Verifies the following:

1. DB Schema: `check_in_lat` (NUMERIC(10,7)), `check_in_lng` (NUMERIC(10,7)), and
   `gps_variance_meters` (INTEGER) are present in the live `job_time_entry` table.
2. ORM Model: JobTimeEntry model exposes all three fields and they round-trip correctly.
3. Null Default: JobTimeEntry can be persisted WITHOUT GPS fields (all are optional).
4. Precision: lat/lng accept 7-decimal-place values (WGS84 ~1cm precision).
5. Variance: gps_variance_meters accepts integer meter values (e.g., 5, 50, 150).
6. Partial Fill: GPS data can be partially present (lat+lng without variance).
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.fulfillment import Job, JobStatus, JobTimeEntry

# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def jte_job_status(db_session):
    """Ensure a 'scheduled' JobStatus exists for time entry tests."""
    status = db_session.exec(
        select(JobStatus).where(JobStatus.code == "scheduled")
    ).first()
    if not status:
        status = JobStatus(
            id=uuid.uuid4(),
            code="scheduled",
            name="Scheduled",
            is_active=True,
        )
        db_session.add(status)
        db_session.flush()
    return status


@pytest.fixture
def jte_job(db_session, test_tenant, test_customer, test_site, jte_job_status):
    """Create a minimal Job for JobTimeEntry FK requirements."""
    job = Job(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=jte_job_status.id,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def jte_user(db_session, test_tenant):
    """Create a minimal User for JobTimeEntry.user_id FK."""
    from app.models.core import User

    user = User(
        id=uuid.uuid4(),
        email=f"tech-{uuid.uuid4().hex[:8]}@test.com",
        first_name="Field",
        last_name="Tech",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_jte(
    tenant_id,
    job_id,
    user_id,
    check_in_lat=None,
    check_in_lng=None,
    gps_variance_meters=None,
) -> JobTimeEntry:
    """Factory: build a JobTimeEntry with optional GPS check-in fields."""
    now = datetime.now(UTC)
    return JobTimeEntry(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        user_id=user_id,
        started_at=now,
        hourly_rate_cents=8500,
        total_cost_cents=0,
        check_in_lat=check_in_lat,
        check_in_lng=check_in_lng,
        gps_variance_meters=gps_variance_meters,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# 1. DB Schema Tests — query information_schema directly
# ---------------------------------------------------------------------------


class TestJobTimeEntryGpsSchema:
    """Verify the three GPS columns exist in the live DB with correct types."""

    def test_check_in_lat_column_exists(self, db_engine):
        """check_in_lat must be present, numeric, nullable."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_name, data_type,
                           numeric_precision, numeric_scale, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'job_time_entry'
                      AND column_name = 'check_in_lat'
                """)
            ).fetchone()
        assert row is not None, "Column 'check_in_lat' is missing from job_time_entry"
        assert row.data_type == "numeric", f"Expected numeric, got {row.data_type}"
        assert row.numeric_precision == 10, (
            f"Expected precision 10, got {row.numeric_precision}"
        )
        assert row.numeric_scale == 7, f"Expected scale 7, got {row.numeric_scale}"
        assert row.is_nullable == "YES", "check_in_lat must be nullable"

    def test_check_in_lng_column_exists(self, db_engine):
        """check_in_lng must be present, numeric(10,7), nullable."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_name, data_type,
                           numeric_precision, numeric_scale, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'job_time_entry'
                      AND column_name = 'check_in_lng'
                """)
            ).fetchone()
        assert row is not None, "Column 'check_in_lng' is missing from job_time_entry"
        assert row.data_type == "numeric", f"Expected numeric, got {row.data_type}"
        assert row.numeric_precision == 10, (
            f"Expected precision 10, got {row.numeric_precision}"
        )
        assert row.numeric_scale == 7, f"Expected scale 7, got {row.numeric_scale}"
        assert row.is_nullable == "YES", "check_in_lng must be nullable"

    def test_gps_variance_meters_column_exists(self, db_engine):
        """gps_variance_meters must be present, integer, nullable."""
        with db_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'job_time_entry'
                      AND column_name = 'gps_variance_meters'
                """)
            ).fetchone()
        assert row is not None, (
            "Column 'gps_variance_meters' is missing from job_time_entry"
        )
        assert row.data_type == "integer", f"Expected integer, got {row.data_type}"
        assert row.is_nullable == "YES", "gps_variance_meters must be nullable"

    def test_no_server_defaults_on_gps_fields(self, db_engine):
        """All three GPS fields must have no server default — NULL signals 'GPS not captured'."""
        with db_engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT column_name, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'job_time_entry'
                      AND column_name IN (
                          'check_in_lat', 'check_in_lng', 'gps_variance_meters'
                      )
                    ORDER BY column_name
                """)
            ).fetchall()
        assert len(rows) == 3, f"Expected 3 GPS column rows, got {len(rows)}"
        for row in rows:
            assert row.column_default is None, (
                f"{row.column_name} should have no server default — "
                "NULL signals GPS not captured at clock-in"
            )


# ---------------------------------------------------------------------------
# 2. ORM Model Tests — round-trip through JobTimeEntry model
# ---------------------------------------------------------------------------


class TestJobTimeEntryOrmGps:
    """Verify JobTimeEntry ORM exposes and persists GPS fields correctly."""

    def test_jte_with_all_gps_fields_persists(
        self, db_session, test_tenant, jte_job, jte_user
    ):
        """JobTimeEntry with all three GPS fields set round-trips correctly."""
        entry = _make_jte(
            tenant_id=test_tenant.id,
            job_id=jte_job.id,
            user_id=jte_user.id,
            check_in_lat=30.2671533,
            check_in_lng=-97.7430608,
            gps_variance_meters=8,
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        fetched = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.id == entry.id)
        ).first()
        assert fetched is not None
        assert float(fetched.check_in_lat) == pytest.approx(30.2671533, abs=1e-6)
        assert float(fetched.check_in_lng) == pytest.approx(-97.7430608, abs=1e-6)
        assert fetched.gps_variance_meters == 8

    def test_jte_without_gps_fields_defaults_to_null(
        self, db_session, test_tenant, jte_job, jte_user
    ):
        """JobTimeEntry persisted without GPS fields has all three as None."""
        entry = _make_jte(
            tenant_id=test_tenant.id,
            job_id=jte_job.id,
            user_id=jte_user.id,
            # Intentionally omit all GPS fields
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        fetched = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.id == entry.id)
        ).first()
        assert fetched is not None
        assert fetched.check_in_lat is None, "check_in_lat should be None"
        assert fetched.check_in_lng is None, "check_in_lng should be None"
        assert fetched.gps_variance_meters is None, "gps_variance_meters should be None"

    def test_lat_lng_7_decimal_precision(
        self, db_session, test_tenant, jte_job, jte_user
    ):
        """Lat/lng must preserve 7 decimal places (WGS84 ~1cm precision)."""
        lat = Decimal("30.1234567")
        lng = Decimal("-97.9876543")
        entry = _make_jte(
            tenant_id=test_tenant.id,
            job_id=jte_job.id,
            user_id=jte_user.id,
            check_in_lat=lat,
            check_in_lng=lng,
            gps_variance_meters=5,
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        fetched = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.id == entry.id)
        ).first()
        assert float(fetched.check_in_lat) == pytest.approx(30.1234567, abs=1e-6)
        assert float(fetched.check_in_lng) == pytest.approx(-97.9876543, abs=1e-6)

    def test_southern_hemisphere_negative_lat(
        self, db_session, test_tenant, jte_job, jte_user
    ):
        """check_in_lat accepts negative values (southern hemisphere)."""
        entry = _make_jte(
            tenant_id=test_tenant.id,
            job_id=jte_job.id,
            user_id=jte_user.id,
            check_in_lat=-33.8688197,  # Sydney, Australia
            check_in_lng=151.2092955,
            gps_variance_meters=12,
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        fetched = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.id == entry.id)
        ).first()
        assert float(fetched.check_in_lat) == pytest.approx(-33.8688197, abs=1e-6)

    def test_partial_gps_lat_lng_without_variance(
        self, db_session, test_tenant, jte_job, jte_user
    ):
        """GPS lat/lng can be set without gps_variance_meters (device may not report it)."""
        entry = _make_jte(
            tenant_id=test_tenant.id,
            job_id=jte_job.id,
            user_id=jte_user.id,
            check_in_lat=29.7604267,
            check_in_lng=-95.3698028,
            gps_variance_meters=None,  # Device didn't report accuracy
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        fetched = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.id == entry.id)
        ).first()
        assert fetched.check_in_lat is not None
        assert fetched.check_in_lng is not None
        assert fetched.gps_variance_meters is None

    def test_high_gps_variance_flags_poor_accuracy(
        self, db_session, test_tenant, jte_job, jte_user
    ):
        """gps_variance_meters accepts large values (e.g., 500m poor GPS signal)."""
        entry = _make_jte(
            tenant_id=test_tenant.id,
            job_id=jte_job.id,
            user_id=jte_user.id,
            check_in_lat=30.2672,
            check_in_lng=-97.7431,
            gps_variance_meters=500,  # Very poor GPS accuracy — flagged for audit
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        fetched = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.id == entry.id)
        ).first()
        assert fetched.gps_variance_meters == 500

    def test_gps_fields_can_be_updated_after_creation(
        self, db_session, test_tenant, jte_job, jte_user
    ):
        """GPS fields can be populated retroactively after the time entry is created."""
        entry = _make_jte(
            tenant_id=test_tenant.id,
            job_id=jte_job.id,
            user_id=jte_user.id,
            # No GPS at creation — mobile app will backfill once permission granted
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        # Simulate mobile app retroactively adding GPS
        entry.check_in_lat = Decimal("30.2671533")
        entry.check_in_lng = Decimal("-97.7430608")
        entry.gps_variance_meters = 15
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        fetched = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.id == entry.id)
        ).first()
        assert float(fetched.check_in_lat) == pytest.approx(30.2671533, abs=1e-6)
        assert fetched.gps_variance_meters == 15

    def test_gps_variance_zero_means_exact_location(
        self, db_session, test_tenant, jte_job, jte_user
    ):
        """gps_variance_meters = 0 is valid (theoretical perfect GPS accuracy)."""
        entry = _make_jte(
            tenant_id=test_tenant.id,
            job_id=jte_job.id,
            user_id=jte_user.id,
            check_in_lat=30.2671533,
            check_in_lng=-97.7430608,
            gps_variance_meters=0,
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        fetched = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.id == entry.id)
        ).first()
        assert fetched.gps_variance_meters == 0
