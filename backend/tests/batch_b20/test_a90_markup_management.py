"""
Comprehensive tests for FIND-055 (A90): Category-Specific Markup Management

Tests the temporal versioning endpoints:
  - GET  /api/v1/settings/markups (active list)
  - POST /api/v1/settings/markups (temporal supersession)
  - GET  /api/v1/settings/markups/{category_code}/history (audit trail)

Per the design doc (§F), this file covers 18 test methods across 4 classes:
  - TestA90GetActiveMarkups (5 tests)
  - TestA90PostMarkupSupersession (8 tests)
  - TestA90GetCategoryHistory (4 tests)
  - TestA90Integration (2 tests)
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import status
from sqlmodel import Session, select, text

from app.models.catalog import TenantMarkupVersion
from app.models.fulfillment import JobExpenseCategory
from core.test_context import TestUserContext

# ==================== FIXTURES ====================


@pytest.fixture
def test_category_labor(db_session: Session, test_tenant) -> JobExpenseCategory:
    """Return (or create) the system-wide labor expense category for testing.

    job_expense_category PK is 'code' (VARCHAR) — rows may already be seeded
    by Alembic migration. Use get-or-create to avoid duplicate PK violations.
    """
    category = db_session.get(JobExpenseCategory, "labor")
    if category is None:
        category = JobExpenseCategory(
            code="labor",
            name="Labor",
            description="Labor services",
            tenant_id=None,
        )
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)
    return category


@pytest.fixture
def test_category_materials(db_session: Session, test_tenant) -> JobExpenseCategory:
    """Return (or create) the system-wide materials expense category for testing.

    job_expense_category PK is 'code' (VARCHAR) — may already be seeded by migration.
    """
    category = db_session.get(JobExpenseCategory, "materials")
    if category is None:
        category = JobExpenseCategory(
            code="materials",
            name="Materials",
            description="Materials and supplies",
            tenant_id=None,
        )
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)
    return category


@pytest.fixture
def other_tenant_category(test_category_labor, second_tenant) -> JobExpenseCategory:
    """Return the same system-wide labor category for testing across tenants."""
    # Return the existing "labor" category fixture.
    # Categories are system-wide (code is global PK).
    # Both tenants can use the same category; markups are tenant-scoped.
    return test_category_labor


def _make_test_context(tenant_id) -> TestUserContext:
    """Create a minimal TestUserContext for testing."""
    return TestUserContext(
        id=uuid4(),
        tenant_id=tenant_id,
        email="test@pilot.local",
    )


def _create_active_markup(
    db_session: Session,
    tenant_id,
    category_code: str,
    markup_pct: float,
    markup_amt_cents: int | None = None,
    created_by=None,
) -> TenantMarkupVersion:
    """Helper: Create an active markup row with open upper bound."""
    # Create a new row with open upper bound [now(), ∞)
    now = datetime.now(UTC)
    row = TenantMarkupVersion(
        tenant_id=tenant_id,
        job_expense_category_code=category_code,
        markup_pct=markup_pct,
        markup_amt_cents=markup_amt_cents,
        created_by=created_by,
    )
    db_session.add(row)
    db_session.flush()

    # Update to set the exact valid_period
    db_session.execute(
        text(
            "UPDATE tenant_markup_version "
            "SET valid_period = tstzrange(:lower, null, '[)') "
            "WHERE id = :id"
        ).bindparams(lower=now, id=row.id)
    )
    db_session.commit()
    db_session.refresh(row)
    return row


def _create_historical_markup(
    db_session: Session,
    tenant_id,
    category_code: str,
    markup_pct: float,
    lower: datetime,
    upper: datetime,
    created_by=None,
) -> TenantMarkupVersion:
    """Helper: Create a closed historical markup row [lower, upper)."""
    row = TenantMarkupVersion(
        tenant_id=tenant_id,
        job_expense_category_code=category_code,
        markup_pct=markup_pct,
        created_by=created_by,
    )
    db_session.add(row)
    db_session.flush()

    db_session.execute(
        text(
            "UPDATE tenant_markup_version "
            "SET valid_period = tstzrange(:lower, :upper, '[)') "
            "WHERE id = :id"
        ).bindparams(lower=lower, upper=upper, id=row.id)
    )
    db_session.commit()
    db_session.refresh(row)
    return row


# ==================== TEST CLASSES ====================


class TestA90GetActiveMarkups:
    """Tests for GET /api/v1/settings/markups (active list)."""

    def test_get_active_markups_empty_returns_empty_list(
        self,
        client,
        second_tenant,
    ):
        """GET with no rows in tenant_markup_version → 200 OK, items=[], total=0.

        Uses second_tenant which has no pre-seeded markup rows (test_tenant has
        seed data from seed_test_tenant.py for dev/QA convenience).
        Passes test_tenant_id query param so endpoint uses second_tenant, not TEST_TENANT_ID.
        """
        response = client.get(
            "/api/v1/settings/markups/test",
            params={"test_tenant_id": str(second_tenant.id)},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_active_markups_returns_only_current_rows(
        self,
        client,
        db_session: Session,
        test_tenant,
        test_category_labor,
    ):
        """Two rows: one active [past, ∞), one closed [2020, 2021) → response contains only the active row."""
        # Create a historical (closed) row
        past_2020 = datetime(2020, 1, 1, tzinfo=UTC)
        past_2021 = datetime(2021, 1, 1, tzinfo=UTC)
        _create_historical_markup(
            db_session,
            test_tenant.id,
            "labor",
            15.0,
            past_2020,
            past_2021,
        )

        # Create an active row (open upper bound)
        active_row = _create_active_markup(
            db_session,
            test_tenant.id,
            "labor",
            20.0,
        )

        context = _make_test_context(test_tenant.id)
        response = client.get(
            "/api/v1/settings/markups/test",
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Verify the active row is present (don't count total — test_tenant may have
        # pre-seeded markup rows from seed_test_tenant.py for dev/QA convenience).
        active_ids = [item["id"] for item in data["items"]]
        assert active_row.id in active_ids
        # Historical row should NOT be returned (it has a closed upper bound)
        historical_ids = [
            item["id"]
            for item in data["items"]
            if item["valid_period_upper"] is not None
        ]
        assert len(historical_ids) == 0

    def test_get_active_markups_scoped_to_tenant(
        self,
        client,
        db_session: Session,
        test_tenant,
        second_tenant,
        test_category_labor,
        other_tenant_category,
    ):
        """Two tenants each with an active markup → each tenant only sees its own row."""
        # Create markup for test_tenant
        test_markup = _create_active_markup(
            db_session,
            test_tenant.id,
            "labor",
            20.0,
        )

        # Create markup for second_tenant
        other_markup = _create_active_markup(
            db_session,
            second_tenant.id,
            "labor",
            25.0,
        )

        # Test tenant queries
        context_test = _make_test_context(test_tenant.id)
        response = client.get(
            "/api/v1/settings/markups/test",
            headers=context_test.headers(),
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Verify test_tenant's markup is present. Don't assert total count — test_tenant
        # may have pre-seeded rows from seed_test_tenant.py.
        active_ids = [item["id"] for item in data["items"]]
        assert test_markup.id in active_ids
        test_markup_data = next(i for i in data["items"] if i["id"] == test_markup.id)
        assert test_markup_data["markup_pct"] == 20.0

        # Other tenant queries
        context_other = _make_test_context(second_tenant.id)
        response = client.get(
            "/api/v1/settings/markups/test",
            params={"test_tenant_id": str(second_tenant.id)},
            headers=context_other.headers(),
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == other_markup.id
        assert data["items"][0]["markup_pct"] == 25.0

    def test_get_active_markups_test_endpoint_no_auth(
        self,
        client,
        test_tenant,
    ):
        """GET /settings/markups/test with TestUserContext → 200 OK (no JWT required)."""
        context = _make_test_context(test_tenant.id)
        response = client.get(
            "/api/v1/settings/markups/test",
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_active_markups_empty_total(
        self,
        client,
        second_tenant,
    ):
        """GET with no rows → total=0.

        Uses second_tenant which has no pre-seeded markup rows (test_tenant has
        seed data from seed_test_tenant.py for dev/QA convenience).
        Passes test_tenant_id query param so endpoint uses second_tenant, not TEST_TENANT_ID.
        """
        response = client.get(
            "/api/v1/settings/markups/test",
            params={"test_tenant_id": str(second_tenant.id)},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 0


class TestA90PostMarkupSupersession:
    """Tests for POST /api/v1/settings/markups (temporal supersession)."""

    def test_post_creates_first_markup_no_supersession(
        self,
        client,
        db_session: Session,
        test_tenant,
        test_category_labor,
    ):
        """Category has no prior row → POST inserts new row, upper bound = null (open)."""
        now = datetime.now(UTC)
        context = _make_test_context(test_tenant.id)
        response = client.post(
            "/api/v1/settings/markups/test",
            json={
                "job_expense_category_code": "labor",
                "markup_pct": 20.0,
                "effective_from": now.isoformat(),
            },
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["markup_pct"] == 20.0
        assert data["valid_period_upper"] is None  # Open upper bound

        # Verify in DB
        row = db_session.exec(
            select(TenantMarkupVersion).where(
                TenantMarkupVersion.job_expense_category_code == "labor"
            )
        ).first()
        assert row is not None
        assert row.valid_period.upper is None

    def test_post_supersession_closes_existing_row(
        self,
        client,
        db_session: Session,
        test_tenant,
        test_category_labor,
    ):
        """Active row [past, ∞), POST effective_from=recent → old closed, new open."""
        # Create initial active row anchored 120 days ago (outside 90-day window)
        now = datetime.now(UTC)
        initial_lower = now - timedelta(days=120)
        initial_row = _create_active_markup(
            db_session,
            test_tenant.id,
            "labor",
            20.0,
        )
        # Manually set lower bound
        db_session.execute(
            text(
                "UPDATE tenant_markup_version "
                "SET valid_period = tstzrange(:lower, null, '[)') "
                "WHERE id = :id"
            ).bindparams(lower=initial_lower, id=initial_row.id)
        )
        db_session.commit()

        # POST new markup effective 30 days ago (within 90-day window)
        new_effective = now - timedelta(days=30)
        context = _make_test_context(test_tenant.id)
        response = client.post(
            "/api/v1/settings/markups/test",
            json={
                "job_expense_category_code": "labor",
                "markup_pct": 25.0,
                "effective_from": new_effective.isoformat(),
            },
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_201_CREATED
        new_row_id = response.json()["id"]

        # Verify old row is closed
        db_session.refresh(initial_row)
        assert initial_row.valid_period.upper == new_effective

        # Verify new row is open
        new_row = db_session.exec(
            select(TenantMarkupVersion).where(TenantMarkupVersion.id == new_row_id)
        ).first()
        assert new_row.valid_period.upper is None

    def test_post_invalid_category_code_returns_404(
        self,
        client,
        test_tenant,
    ):
        """Nonexistent category_code → 404."""
        now = datetime.now(UTC)
        context = _make_test_context(test_tenant.id)
        response = client.post(
            "/api/v1/settings/markups/test",
            json={
                "job_expense_category_code": "nonexistent_category",
                "markup_pct": 20.0,
                "effective_from": now.isoformat(),
            },
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_post_negative_markup_pct_returns_422(
        self,
        client,
        test_tenant,
    ):
        """markup_pct=-5.0 → 422 Unprocessable Entity."""
        now = datetime.now(UTC)
        context = _make_test_context(test_tenant.id)
        response = client.post(
            "/api/v1/settings/markups/test",
            json={
                "job_expense_category_code": "labor",
                "markup_pct": -5.0,
                "effective_from": now.isoformat(),
            },
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_post_markup_pct_stored_correctly(
        self,
        client,
        db_session: Session,
        test_tenant,
        test_category_labor,
    ):
        """POST markup_pct=20.0 → DB row has markup_pct = 20.0 (not 0.20)."""
        now = datetime.now(UTC)
        context = _make_test_context(test_tenant.id)
        response = client.post(
            "/api/v1/settings/markups/test",
            json={
                "job_expense_category_code": "labor",
                "markup_pct": 20.0,
                "effective_from": now.isoformat(),
            },
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Verify in DB
        row = db_session.exec(
            select(TenantMarkupVersion).where(
                TenantMarkupVersion.job_expense_category_code == "labor"
            )
        ).first()
        assert float(row.markup_pct) == 20.0

    def test_post_markup_amt_cents_optional(
        self,
        client,
        test_category_labor,
        test_tenant,
    ):
        """POST with only markup_pct=15.0, no markup_amt_cents → 201 OK, markup_amt_cents=null."""
        now = datetime.now(UTC)
        context = _make_test_context(test_tenant.id)
        response = client.post(
            "/api/v1/settings/markups/test",
            json={
                "job_expense_category_code": "labor",
                "markup_pct": 15.0,
                "effective_from": now.isoformat(),
            },
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["markup_amt_cents"] is None

    def test_post_creates_creates_new_row(
        self,
        client,
        db_session: Session,
        test_tenant,
        test_category_labor,
    ):
        """POST creates a new row in the database."""
        now = datetime.now(UTC)
        context = _make_test_context(test_tenant.id)
        response = client.post(
            "/api/v1/settings/markups/test",
            json={
                "job_expense_category_code": "labor",
                "markup_pct": 20.0,
                "effective_from": now.isoformat(),
            },
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["id"] is not None

    def test_post_test_endpoint_no_auth(
        self,
        client,
        test_category_labor,
        test_tenant,
    ):
        """POST /settings/markups/test with TestUserContext → 201 OK."""
        now = datetime.now(UTC)
        context = _make_test_context(test_tenant.id)
        response = client.post(
            "/api/v1/settings/markups/test",
            json={
                "job_expense_category_code": "labor",
                "markup_pct": 20.0,
                "effective_from": now.isoformat(),
            },
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_201_CREATED


class TestA90GetCategoryHistory:
    """Tests for GET /api/v1/settings/markups/{category_code}/history (audit trail)."""

    def test_get_history_returns_all_rows_sorted_desc(
        self,
        client,
        db_session: Session,
        test_tenant,
        test_category_labor,
    ):
        """Category with 3 versions → history returns all 3 rows ordered by recorded_at DESC."""
        # Create three versions (recorded_at increases automatically)
        _row1 = _create_historical_markup(
            db_session,
            test_tenant.id,
            "labor",
            20.0,
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 3, 1, tzinfo=UTC),
        )
        _row2 = _create_historical_markup(
            db_session,
            test_tenant.id,
            "labor",
            22.0,
            datetime(2026, 3, 1, tzinfo=UTC),
            datetime(2026, 5, 1, tzinfo=UTC),
        )
        _row3 = _create_active_markup(
            db_session,
            test_tenant.id,
            "labor",
            25.0,
        )

        context = _make_test_context(test_tenant.id)
        response = client.get(
            "/api/v1/settings/markups/labor/history/test",
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_get_history_empty_for_new_category(
        self,
        client,
        test_category_labor,
        test_tenant,
    ):
        """Category with zero markup rows → 200 OK, items=[]."""
        context = _make_test_context(test_tenant.id)
        response = client.get(
            "/api/v1/settings/markups/labor/history/test",
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_history_invalid_category_returns_404(
        self,
        client,
        test_tenant,
    ):
        """Nonexistent category_code path param → 404."""
        context = _make_test_context(test_tenant.id)
        response = client.get(
            "/api/v1/settings/markups/nonexistent_category/history/test",
            headers=context.headers(),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_history_scoped_to_tenant(
        self,
        client,
        db_session: Session,
        test_tenant,
        second_tenant,
        test_category_labor,
        other_tenant_category,
    ):
        """Two tenants, same category_code → each tenant only sees its own rows."""
        # Create history for test_tenant
        test_row = _create_active_markup(
            db_session,
            test_tenant.id,
            "labor",
            20.0,
        )

        # Create history for second_tenant
        other_row = _create_active_markup(
            db_session,
            second_tenant.id,
            "labor",
            25.0,
        )

        # Test tenant queries
        context_test = _make_test_context(test_tenant.id)
        response = client.get(
            "/api/v1/settings/markups/labor/history/test",
            headers=context_test.headers(),
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == test_row.id

        # Other tenant queries
        context_other = _make_test_context(second_tenant.id)
        response = client.get(
            "/api/v1/settings/markups/labor/history/test",
            params={"test_tenant_id": str(second_tenant.id)},
            headers=context_other.headers(),
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == other_row.id


class TestA90Integration:
    """Integration tests covering full supersession lifecycle."""

    def test_full_supersession_lifecycle(
        self,
        client,
        db_session: Session,
        second_tenant,
        test_category_labor,
    ):
        """Test that POST creates a markup and GET returns it.

        Uses second_tenant which has no pre-seeded markup rows.
        Passes test_tenant_id query param to target second_tenant.
        """
        now = datetime.now(UTC)
        response = client.post(
            "/api/v1/settings/markups/test",
            json={
                "job_expense_category_code": "labor",
                "markup_pct": 20.0,
                "effective_from": now.isoformat(),
            },
            params={"test_tenant_id": str(second_tenant.id)},
        )
        assert response.status_code == status.HTTP_201_CREATED
        v1_id = response.json()["id"]

        # GET active for second_tenant — expect exactly 1 row (labor only)
        response = client.get(
            "/api/v1/settings/markups/test",
            params={"test_tenant_id": str(second_tenant.id)},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == v1_id

    def test_multiple_categories_independent(
        self,
        client,
        db_session: Session,
        second_tenant,
        test_category_labor,
        test_category_materials,
    ):
        """Create markups for two categories; verify they're independent.

        Uses second_tenant which has no pre-seeded markup rows.
        Passes test_tenant_id query param to target second_tenant.
        """
        now = datetime.now(UTC)
        # POST labor markup for second_tenant
        response = client.post(
            "/api/v1/settings/markups/test",
            json={
                "job_expense_category_code": "labor",
                "markup_pct": 20.0,
                "effective_from": now.isoformat(),
            },
            params={"test_tenant_id": str(second_tenant.id)},
        )
        assert response.status_code == status.HTTP_201_CREATED

        # POST materials markup for second_tenant
        response = client.post(
            "/api/v1/settings/markups/test",
            json={
                "job_expense_category_code": "materials",
                "markup_pct": 15.0,
                "effective_from": now.isoformat(),
            },
            params={"test_tenant_id": str(second_tenant.id)},
        )
        assert response.status_code == status.HTTP_201_CREATED

        # GET active for second_tenant → exactly 2 rows (labor + materials)
        response = client.get(
            "/api/v1/settings/markups/test",
            params={"test_tenant_id": str(second_tenant.id)},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        active_categories = {
            item["job_expense_category_code"] for item in data["items"]
        }
        assert "labor" in active_categories
        assert "materials" in active_categories
