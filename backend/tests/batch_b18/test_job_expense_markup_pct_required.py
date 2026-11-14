"""
FIND-061 (S2 High) — job_expense.markup_pct NOT NULL constraint.

PRD-§3.4-F3: "mandatory markup percentage capture"

Before this change:
  - markup_pct was NULLABLE
  - A permissive CHECK `job_expense_markup_presence_chk` allowed either
    markup_pct OR markup_amt_cents to be non-null

After this change:
  - markup_pct is NOT NULL DEFAULT 0
  - Zero markup is valid (cost-pass-through items)
  - `job_expense_markup_presence_chk` constraint dropped (NOT NULL alone is sufficient)

Test coverage:
  1. DB schema: column is NOT NULL + DEFAULT 0; check constraint is absent
  2. ORM model: field is non-Optional float with nullable=False
  3. Integrity: INSERT with markup_pct=NULL raises IntegrityError
  4. Integrity: INSERT with markup_pct=0 succeeds
  5. Integrity: INSERT with markup_pct=0.15 succeeds
  6. Endpoint: POST /jobs/{job_id}/expenses/test always returns non-null markup_pct

Test subfolder: tests/batch_b18/
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_job_fixture(db_session, test_tenant):
    """Create minimal Job row satisfying FK requirements."""
    from sqlmodel import select

    from app.models.crm import Customer, Site
    from app.models.fulfillment import Job, JobStatus

    now = datetime.now(UTC)
    job_status = db_session.exec(select(JobStatus).limit(1)).first()
    assert job_status is not None, "No JobStatus seeded — seed data required"

    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        type="person",
        display_name=f"Test Customer {uuid.uuid4().hex[:6]}",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)

    site = Site(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=customer.id,
        display_name="Test Site",
        created_at=now,
        updated_at=now,
    )
    db_session.add(site)

    job = Job(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=customer.id,
        site_id=site.id,
        status_id=job_status.id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(job)
    db_session.flush()
    return job


def _make_expense_category(db_session, test_tenant):
    """Create a minimal JobExpenseCategory satisfying the FK requirement."""
    from app.models.fulfillment import JobExpenseCategory

    code = f"test_cat_{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC)
    cat = JobExpenseCategory(
        code=code,
        tenant_id=test_tenant.id,
        name="Test Category",
        created_at=now,
        updated_at=now,
    )
    db_session.add(cat)
    db_session.flush()
    return cat


def _make_expense_kwargs(tenant_id, job_id, category_code, markup_pct=0, user_id=None):
    """Return a dict of minimal JobExpense kwargs."""
    import uuid as _uuid

    now = datetime.now(UTC)
    return dict(
        id=_uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        # FIND-121: user_id is required (NOT NULL) after B18 migration
        user_id=user_id or _uuid.UUID("00000000-0000-0000-0000-000000000002"),
        job_expense_category_code=category_code,
        description="Test expense",
        incurred_at=now,
        cost_cents=5000,
        markup_pct=markup_pct,
        billable_cents=5000,
        is_billable=True,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. DB schema: column is NOT NULL + no check constraint
# ─────────────────────────────────────────────────────────────────────────────


class TestFind061DBSchema:
    """Verify migration applied the correct column-level constraints."""

    def test_markup_pct_column_is_not_nullable(self, db_session):
        """markup_pct must be NOT NULL after FIND-061 migration."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_name, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'job_expense' "
                "  AND column_name = 'markup_pct'"
            )
        ).first()

        assert result is not None, "markup_pct column missing from job_expense"
        assert result[1] == "NO", (
            f"markup_pct must be NOT NULL (is_nullable='NO'), got '{result[1]}'"
        )

    def test_markup_pct_has_default_zero(self, db_session):
        """markup_pct server default must be 0."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_default "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'job_expense' "
                "  AND column_name = 'markup_pct'"
            )
        ).first()

        assert result is not None, "markup_pct column missing from job_expense"
        assert result[0] is not None, "markup_pct must have a server default"
        # Server default is stored as '0' or '0::numeric' depending on PG version
        assert "0" in str(result[0]), (
            f"markup_pct server default must contain '0', got '{result[0]}'"
        )

    def test_markup_presence_check_constraint_is_absent(self, db_session):
        """job_expense_markup_presence_chk must be dropped — NOT NULL replaces it."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT constraint_name "
                "FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'job_expense' "
                "  AND constraint_type = 'CHECK' "
                "  AND constraint_name = 'job_expense_markup_presence_chk'"
            )
        ).first()

        assert result is None, (
            "job_expense_markup_presence_chk CHECK constraint must have been dropped "
            "by FIND-061 migration — NOT NULL on markup_pct is the replacement"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. ORM model: field is non-Optional float with nullable=False
# ─────────────────────────────────────────────────────────────────────────────


class TestFind061ORMModel:
    """ORM model must declare markup_pct as non-Optional with nullable=False."""

    def test_markup_pct_field_is_not_optional(self):
        """JobExpense.markup_pct must be a non-Optional float (not Optional[float])."""
        import typing

        from app.models.fulfillment import JobExpense

        # Retrieve the SQLModel field type annotation
        hints = typing.get_type_hints(JobExpense)
        markup_pct_type = hints.get("markup_pct")

        assert markup_pct_type is not None, "markup_pct field missing from JobExpense"
        # Should be float, not Optional[float]
        origin = getattr(markup_pct_type, "__origin__", None)
        assert origin is not typing.Union, (
            f"markup_pct must be float (not Optional[float]), got {markup_pct_type}"
        )

    def test_markup_pct_sa_column_nullable_false(self):
        """SA column must have nullable=False."""
        from app.models.fulfillment import JobExpense

        col = JobExpense.__table__.c["markup_pct"]
        assert col.nullable is False, (
            f"markup_pct SA column nullable must be False, got {col.nullable}"
        )

    def test_markup_pct_sa_column_has_server_default(self):
        """SA column must have server_default=0."""
        from app.models.fulfillment import JobExpense

        col = JobExpense.__table__.c["markup_pct"]
        assert col.server_default is not None, (
            "markup_pct SA column must have a server_default"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3–5. Integrity: NULL violation + valid inserts
# ─────────────────────────────────────────────────────────────────────────────


class TestFind061IntegrityConstraints:
    """Direct ORM insert tests verifying the NOT NULL constraint is enforced."""

    def test_insert_null_markup_pct_raises_integrity_error(
        self, db_session, test_tenant
    ):
        """Raw SQL INSERT with markup_pct=NULL must raise IntegrityError.

        NOTE: The ORM default=0 coerces Python None → 0 before flush, so we
        must use raw SQL to actually deliver NULL to the DB and prove the NOT NULL
        constraint fires.
        """
        from sqlalchemy import text

        job = _make_job_fixture(db_session, test_tenant)
        cat = _make_expense_category(db_session, test_tenant)
        db_session.flush()

        now = datetime.now(UTC)
        with pytest.raises(IntegrityError):
            db_session.exec(
                text(
                    "INSERT INTO job_expense "
                    "(id, tenant_id, job_id, job_expense_category_code, "
                    " description, incurred_at, cost_cents, markup_pct, "
                    " billable_cents, is_billable, is_active, created_at, updated_at) "
                    "VALUES (:id, :tenant_id, :job_id, :cat_code, "
                    " :desc, :incurred_at, :cost_cents, NULL, "
                    " :billable_cents, true, true, :now, :now)"
                ).bindparams(
                    id=str(uuid.uuid4()),
                    tenant_id=str(test_tenant.id),
                    job_id=str(job.id),
                    cat_code=cat.code,
                    desc="Test NULL markup",
                    incurred_at=now,
                    cost_cents=5000,
                    billable_cents=5000,
                    now=now,
                )
            )
            db_session.flush()

        db_session.rollback()

    def test_insert_zero_markup_pct_succeeds(self, db_session, test_tenant):
        """INSERT with markup_pct=0 must succeed (cost-pass-through item)."""
        from sqlmodel import select

        from app.models.fulfillment import JobExpense

        job = _make_job_fixture(db_session, test_tenant)
        cat = _make_expense_category(db_session, test_tenant)
        kwargs = _make_expense_kwargs(test_tenant.id, job.id, cat.code, markup_pct=0)
        expense = JobExpense(**kwargs)
        db_session.add(expense)
        db_session.commit()

        fetched = db_session.exec(
            select(JobExpense).where(JobExpense.id == expense.id)
        ).first()
        assert fetched is not None, "Expense row must persist to DB"
        assert float(fetched.markup_pct) == 0.0, (
            f"markup_pct must be 0.0, got {fetched.markup_pct}"
        )

    def test_insert_nonzero_markup_pct_succeeds(self, db_session, test_tenant):
        """INSERT with markup_pct=0.15 must succeed."""
        from sqlmodel import select

        from app.models.fulfillment import JobExpense

        job = _make_job_fixture(db_session, test_tenant)
        cat = _make_expense_category(db_session, test_tenant)
        kwargs = _make_expense_kwargs(test_tenant.id, job.id, cat.code, markup_pct=0.15)
        expense = JobExpense(**kwargs)
        db_session.add(expense)
        db_session.commit()

        fetched = db_session.exec(
            select(JobExpense).where(JobExpense.id == expense.id)
        ).first()
        assert fetched is not None, "Expense row must persist to DB"
        assert abs(float(fetched.markup_pct) - 0.15) < 0.0001, (
            f"markup_pct must be 0.15, got {fetched.markup_pct}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Endpoint: POST /jobs/{job_id}/expenses/test always returns non-null markup_pct
# ─────────────────────────────────────────────────────────────────────────────


class TestFind061EndpointResponse:
    """Expense creation endpoint must always return a non-null markup_pct."""

    def test_create_expense_endpoint_returns_nonnull_markup_pct(
        self, client, db_session, test_tenant
    ):
        """POST /jobs/{id}/expenses/test → response.markup_pct is never null."""
        job = _make_job_fixture(db_session, test_tenant)
        cat = _make_expense_category(db_session, test_tenant)
        db_session.commit()

        payload = {
            "job_expense_category_code": cat.code,
            "description": "Wire 12/2",
            "cost_cents": 5000,
            "incurred_at": datetime.now(UTC).isoformat(),
            "is_billable": True,
        }

        response = client.post(
            f"/api/v1/jobs/{job.id}/expenses/test",
            json=payload,
        )

        assert response.status_code == 201, (
            f"Expected 201 Created, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "markup_pct" in data, "markup_pct must be present in response"
        assert data["markup_pct"] is not None, (
            "markup_pct must never be null in expense creation response"
        )

    def test_create_expense_endpoint_zero_markup_in_response(
        self, client, db_session, test_tenant
    ):
        """When no markup version found, response markup_pct defaults to 0 (not null)."""
        job = _make_job_fixture(db_session, test_tenant)
        cat = _make_expense_category(db_session, test_tenant)
        db_session.commit()

        payload = {
            "job_expense_category_code": cat.code,
            "description": "Receptacle",
            "cost_cents": 1200,
            "incurred_at": datetime.now(UTC).isoformat(),
            "is_billable": False,  # non-billable → no markup lookup
        }

        response = client.post(
            f"/api/v1/jobs/{job.id}/expenses/test",
            json=payload,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["markup_pct"] is not None, (
            "Non-billable expense must still have markup_pct=0 in response, not null"
        )
        assert float(data["markup_pct"]) == 0.0, (
            f"Non-billable expense markup_pct must default to 0.0, got {data['markup_pct']}"
        )
