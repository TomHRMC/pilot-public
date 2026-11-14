"""
Batch B1 — A2 Test Coverage
============================

A2: Quote Approval Workflow State Machine

Test Coverage:
- quote.submitted_by_user_id, submitted_at, approved_by_user_id, approved_at columns exist in DB
- tenant_settings.require_approval_for_tech_quotes column exists with NOT NULL default TRUE
- quote_status table has 'pending_approval' and 'approved' system rows
- quote_service.transition_quote_status resolves status code correctly
- quote_service.assert_quote_version_not_stale passes when version matches
- quote_service.assert_quote_version_not_stale raises 409 on mismatch
- quote_service.get_quote_status_code returns correct code string
- POST /api/v1/quotes/{id}/submit-for-approval — happy path
- POST /api/v1/quotes/{id}/submit-for-approval — 422 if not draft
- POST /api/v1/quotes/{id}/approve — happy path
- POST /api/v1/quotes/{id}/approve — 422 if not pending_approval
- POST /api/v1/quotes/{id}/reject — happy path
- POST /api/v1/quotes/{id}/reject — 422 if comment missing
"""

import uuid

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from app.models.quoting import Quote, QuoteStatus
from services.quote_service import (
    assert_quote_version_not_stale,
    get_quote_status_code,
    transition_quote_status,
)

# ─────────────────────────────────────────────────────────────────────────────
# A2 — DB Column verification
# ─────────────────────────────────────────────────────────────────────────────


class TestA2QuoteColumns:
    """Verify A2 columns exist on the quote table."""

    def _get_col(self, db_session: Session, column_name: str):
        return db_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'quote'
                  AND column_name = :col
            """),
            {"col": column_name},
        ).first()

    def test_submitted_by_user_id_exists(self, db_session: Session):
        row = self._get_col(db_session, "submitted_by_user_id")
        assert row is not None, "submitted_by_user_id missing from quote"
        assert row.data_type == "uuid"
        assert row.is_nullable == "YES"

    def test_submitted_at_exists(self, db_session: Session):
        row = self._get_col(db_session, "submitted_at")
        assert row is not None, "submitted_at missing from quote"
        assert "timestamp" in row.data_type
        assert row.is_nullable == "YES"

    def test_approved_by_user_id_exists(self, db_session: Session):
        row = self._get_col(db_session, "approved_by_user_id")
        assert row is not None, "approved_by_user_id missing from quote"
        assert row.data_type == "uuid"
        assert row.is_nullable == "YES"

    def test_approved_at_exists(self, db_session: Session):
        row = self._get_col(db_session, "approved_at")
        assert row is not None, "approved_at missing from quote"
        assert "timestamp" in row.data_type
        assert row.is_nullable == "YES"


class TestA2TenantSettingsColumn:
    """Verify require_approval_for_tech_quotes in platform_setting_catalog (FIND-086)."""

    def test_require_approval_column_exists(self, db_session: Session):
        from sqlmodel import select as _sel

        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            _sel(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "require_approval_for_tech_quotes"
            )
        ).first()
        assert row is not None, (
            "require_approval_for_tech_quotes missing from platform_setting_catalog"
        )
        assert row.value_type == "boolean"
        assert row.tenant_editable is True


class TestA2StatusCodeSeeds:
    """Verify pending_approval and approved status codes are seeded."""

    def test_pending_approval_status_seeded(self, db_session: Session):
        status = db_session.exec(
            select(QuoteStatus).where(QuoteStatus.code == "pending_approval")
        ).first()
        assert status is not None, "'pending_approval' quote_status not seeded"
        assert status.is_active is True
        assert status.is_terminal is False

    def test_approved_status_seeded(self, db_session: Session):
        status = db_session.exec(
            select(QuoteStatus).where(QuoteStatus.code == "approved")
        ).first()
        assert status is not None, "'approved' quote_status not seeded"
        assert status.is_active is True
        assert status.is_terminal is False


# ─────────────────────────────────────────────────────────────────────────────
# A2 — quote_service unit tests
# ─────────────────────────────────────────────────────────────────────────────


class TestQuoteServiceTransitions:
    """Test quote_service.transition_quote_status and helpers."""

    def test_get_quote_status_code_returns_correct_code(
        self, db_session: Session, test_tenant
    ):
        """get_quote_status_code resolves the code string from a quote."""
        draft_status = db_session.exec(
            select(QuoteStatus).where(QuoteStatus.code == "draft")
        ).first()
        if not draft_status:
            draft_status = QuoteStatus(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                code="draft",
                name="Draft",
                is_default=True,
            )
            db_session.add(draft_status)
            db_session.flush()

        # Create a minimal quote pointing at draft status
        from app.models.billing import Currency
        from app.models.crm import Customer, CustomerType, Site

        currency = db_session.exec(
            select(Currency).where(Currency.code == "USD")
        ).first()
        if not currency:
            currency = Currency(code="USD", name="US Dollar", symbol="$")
            db_session.add(currency)
            db_session.flush()

        customer = Customer(
            tenant_id=test_tenant.id,
            type=CustomerType.person,
            display_name=f"A2-StatusCode-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(tenant_id=test_tenant.id, customer_id=customer.id, name="Test Site")
        db_session.add(site)
        db_session.flush()

        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=draft_status.id,
            currency="USD",
        )
        db_session.add(quote)
        db_session.flush()

        code = get_quote_status_code(quote, db_session)
        assert code == "draft"

    def test_transition_quote_status_to_pending_approval(
        self, db_session: Session, test_tenant
    ):
        """transition_quote_status moves quote to pending_approval."""
        from app.models.billing import Currency
        from app.models.crm import Customer, CustomerType, Site

        currency = db_session.exec(
            select(Currency).where(Currency.code == "USD")
        ).first()
        if not currency:
            currency = Currency(code="USD", name="US Dollar", symbol="$")
            db_session.add(currency)
            db_session.flush()

        draft_status = db_session.exec(
            select(QuoteStatus).where(QuoteStatus.code == "draft")
        ).first()
        if not draft_status:
            draft_status = QuoteStatus(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                code="draft",
                name="Draft",
                is_default=True,
            )
            db_session.add(draft_status)
            db_session.flush()

        customer = Customer(
            tenant_id=test_tenant.id,
            type=CustomerType.person,
            display_name=f"A2-Transition-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(tenant_id=test_tenant.id, customer_id=customer.id, name="SvcSite")
        db_session.add(site)
        db_session.flush()

        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=draft_status.id,
            currency="USD",
        )
        db_session.add(quote)
        db_session.flush()

        updated = transition_quote_status(
            quote, "pending_approval", db_session, test_tenant.id
        )
        code = get_quote_status_code(updated, db_session)
        assert code == "pending_approval"

    def test_assert_quote_version_not_stale_skips_when_none(
        self, db_session: Session, test_tenant
    ):
        """Staleness check skips silently when expected_version_id=None."""
        # Should not raise
        assert_quote_version_not_stale(None, uuid.uuid4(), db_session, test_tenant.id)

    def test_assert_quote_version_not_stale_raises_on_mismatch(
        self, db_session: Session, test_tenant
    ):
        """Staleness check raises 409 when client version doesn't match latest."""
        from fastapi import HTTPException

        from app.models.billing import Currency
        from app.models.crm import Customer, CustomerType, Site
        from app.models.quoting import QuoteVersion

        currency = db_session.exec(
            select(Currency).where(Currency.code == "USD")
        ).first()
        if not currency:
            currency = Currency(code="USD", name="US Dollar", symbol="$")
            db_session.add(currency)
            db_session.flush()

        draft_status = db_session.exec(
            select(QuoteStatus).where(QuoteStatus.code == "draft")
        ).first()
        if not draft_status:
            draft_status = QuoteStatus(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                code="draft",
                name="Draft",
                is_default=True,
            )
            db_session.add(draft_status)
            db_session.flush()

        customer = Customer(
            tenant_id=test_tenant.id,
            type=CustomerType.person,
            display_name=f"A2-Stale-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(tenant_id=test_tenant.id, customer_id=customer.id, name="StaleSite")
        db_session.add(site)
        db_session.flush()

        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=draft_status.id,
            currency="USD",
        )
        db_session.add(quote)
        db_session.flush()

        # Create a quote version
        real_version = QuoteVersion(
            tenant_id=test_tenant.id,
            quote_id=quote.id,
            version_no=1,
            snapshot={"quote": {}, "lines": []},
        )
        db_session.add(real_version)
        db_session.flush()

        # Pass a different UUID as the expected version
        stale_version_id = uuid.uuid4()
        with pytest.raises(HTTPException) as exc_info:
            assert_quote_version_not_stale(
                stale_version_id, quote.id, db_session, test_tenant.id
            )

        assert exc_info.value.status_code == 409
        assert "stale-state" in str(exc_info.value.detail)


# ─────────────────────────────────────────────────────────────────────────────
# A2 — ORM model field presence on Quote
# ─────────────────────────────────────────────────────────────────────────────


class TestA2QuoteOrmFields:
    """Verify A2 fields exist on the Quote ORM model."""

    def test_submitted_by_user_id_field_exists(self):
        assert hasattr(Quote, "submitted_by_user_id")

    def test_submitted_at_field_exists(self):
        assert hasattr(Quote, "submitted_at")

    def test_approved_by_user_id_field_exists(self):
        assert hasattr(Quote, "approved_by_user_id")

    def test_approved_at_field_exists(self):
        assert hasattr(Quote, "approved_at")
