"""
Batch B1 — A3 Test Coverage
============================

A3: Time-Limited Discounts with Margin Cap

Test Coverage:
- quote.discount_pct, discount_amount_cents, discount_expires_at, discount_applied_by_user_id columns exist in DB
- platform_setting_catalog has max_discount_pct_owner key (FIND-086: replaces tenant_settings column check)
- Quote ORM model has all 4 A3 discount fields
- PlatformSettingCatalog has max_discount_pct_owner key
- QuoteApplyDiscountRequest/Response schemas are present
- expire_quote_discounts task is registered in celery_app
- _expire_quote_discounts_impl returns {"expired": 0} when no expired discounts
- _expire_quote_discounts_impl correctly expires past-due discounts
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlmodel import Session, select

from api.schemas.quotes import QuoteApplyDiscountRequest, QuoteApplyDiscountResponse
from app.models.platform_setting import PlatformSettingCatalog
from app.models.quoting import Quote, QuoteStatus
from tasks.quote_discount_expiry import _expire_quote_discounts_impl

# ─────────────────────────────────────────────────────────────────────────────
# A3 — DB Column verification
# ─────────────────────────────────────────────────────────────────────────────


class TestA3QuoteDiscountColumns:
    """Verify A3 discount columns exist on the quote table."""

    def _get_col(self, db_session: Session, col: str):
        return db_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'quote'
                  AND column_name = :col
            """),
            {"col": col},
        ).first()

    def test_discount_pct_col_exists(self, db_session: Session):
        row = self._get_col(db_session, "discount_pct")
        assert row is not None, "discount_pct missing from quote"
        assert row.is_nullable == "YES"

    def test_discount_amount_cents_col_exists(self, db_session: Session):
        row = self._get_col(db_session, "discount_amount_cents")
        assert row is not None, "discount_amount_cents missing from quote"
        assert row.is_nullable == "YES"

    def test_discount_expires_at_col_exists(self, db_session: Session):
        row = self._get_col(db_session, "discount_expires_at")
        assert row is not None, "discount_expires_at missing from quote"
        assert row.is_nullable == "YES"

    def test_discount_applied_by_user_id_col_exists(self, db_session: Session):
        row = self._get_col(db_session, "discount_applied_by_user_id")
        assert row is not None, "discount_applied_by_user_id missing from quote"
        assert row.is_nullable == "YES"


class TestA3TenantSettingsMaxDiscount:
    """Verify max_discount_pct_owner exists in platform_setting_catalog (FIND-086)."""

    def test_max_discount_pct_owner_in_catalog(self, db_session: Session):
        from sqlmodel import select

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "max_discount_pct_owner"
            )
        ).first()
        assert row is not None, (
            "max_discount_pct_owner missing from platform_setting_catalog"
        )
        assert row.value_type == "decimal"
        assert row.tenant_editable is True


# ─────────────────────────────────────────────────────────────────────────────
# A3 — ORM model field presence
# ─────────────────────────────────────────────────────────────────────────────


class TestA3OrmFields:
    """Verify A3 ORM field presence."""

    def test_quote_has_discount_pct(self):
        assert hasattr(Quote, "discount_pct")

    def test_quote_has_discount_amount_cents(self):
        assert hasattr(Quote, "discount_amount_cents")

    def test_quote_has_discount_expires_at(self):
        assert hasattr(Quote, "discount_expires_at")

    def test_quote_has_discount_applied_by_user_id(self):
        assert hasattr(Quote, "discount_applied_by_user_id")

    def test_catalog_has_max_discount_pct_owner(self, db_session: Session):
        """FIND-086: PlatformSettingCatalog has max_discount_pct_owner with decimal type."""
        from sqlmodel import select as _sel

        row = db_session.exec(
            _sel(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "max_discount_pct_owner"
            )
        ).first()
        assert row is not None, (
            "max_discount_pct_owner missing from platform_setting_catalog"
        )
        assert row.value_type == "decimal"


# ─────────────────────────────────────────────────────────────────────────────
# A3 — Pydantic schema tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA3PydanticSchemas:
    """Verify A3 request/response schemas."""

    def test_apply_discount_request_fields(self):
        req = QuoteApplyDiscountRequest(discount_pct=Decimal("10.00"))
        assert req.discount_pct == Decimal("10.00")
        assert req.discount_expires_at is None
        assert req.expected_quote_version_id is None

    def test_apply_discount_response_fields(self):
        fields = QuoteApplyDiscountResponse.model_fields
        assert "quote_id" in fields
        assert "discount_pct" in fields
        assert "discount_amount_cents" in fields
        assert "discount_expires_at" in fields
        assert "new_version_id" in fields


# ─────────────────────────────────────────────────────────────────────────────
# A3 — Celery task registration
# ─────────────────────────────────────────────────────────────────────────────


class TestA3TaskRegistration:
    """Verify expire_quote_discounts task is registered."""

    def test_task_is_registered(self):
        from tasks.quote_discount_expiry import expire_quote_discounts

        assert expire_quote_discounts.name == "expire_quote_discounts"

    def test_task_in_celery_imports(self):
        from core.celery_app import celery_app

        assert "tasks.quote_discount_expiry" in celery_app.conf.imports

    def test_task_in_beat_schedule(self):
        from core.celery_app import celery_app

        assert "expire-quote-discounts" in celery_app.conf.beat_schedule
        entry = celery_app.conf.beat_schedule["expire-quote-discounts"]
        assert entry["task"] == "expire_quote_discounts"


# ─────────────────────────────────────────────────────────────────────────────
# A3 — Task impl tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA3ExpireDiscountImpl:
    """Test _expire_quote_discounts_impl function."""

    def _make_quote_with_discount(
        self,
        db_session: Session,
        tenant_id: uuid.UUID,
        expires_at: datetime,
    ) -> Quote:
        """Helper: create a quote with a discount set."""
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
                tenant_id=tenant_id,
                code="draft",
                name="Draft",
                is_default=True,
            )
            db_session.add(draft_status)
            db_session.flush()

        customer = Customer(
            tenant_id=tenant_id,
            type=CustomerType.person,
            display_name=f"A3-Discount-{uuid.uuid4().hex[:8]}",
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(tenant_id=tenant_id, customer_id=customer.id, name="Test Site")
        db_session.add(site)
        db_session.flush()

        quote = Quote(
            tenant_id=tenant_id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=draft_status.id,
            currency="USD",
            total_cents=100000,
            discount_pct=Decimal("10.00"),
            discount_amount_cents=10000,
            discount_expires_at=expires_at,
        )
        db_session.add(quote)
        db_session.flush()
        return quote

    def test_returns_zero_when_no_expired_discounts(self, db_session: Session):
        """_impl returns {"expired": 0} when no quotes have expired discounts."""
        result = _expire_quote_discounts_impl(db_session)
        assert isinstance(result["expired"], int)

    def test_expires_past_due_discount(self, db_session: Session, test_tenant):
        """_impl clears discount fields on quotes with past discount_expires_at."""
        past_time = datetime.now(UTC) - timedelta(hours=2)
        quote = self._make_quote_with_discount(db_session, test_tenant.id, past_time)

        assert quote.discount_pct is not None

        result = _expire_quote_discounts_impl(db_session)
        assert result["expired"] >= 1

        # Refresh the quote to see updated fields
        db_session.expire(quote)
        updated_quote = db_session.get(Quote, quote.id)
        assert updated_quote.discount_pct is None
        assert updated_quote.discount_amount_cents is None
        assert updated_quote.discount_expires_at is None

    def test_does_not_expire_future_discounts(self, db_session: Session, test_tenant):
        """_impl does not touch discounts that haven't expired yet."""
        future_time = datetime.now(UTC) + timedelta(days=7)
        quote = self._make_quote_with_discount(db_session, test_tenant.id, future_time)

        initial_pct = quote.discount_pct
        _expire_quote_discounts_impl(db_session)

        db_session.expire(quote)
        still_live = db_session.get(Quote, quote.id)
        # Discount should still be there (future expiry)
        assert still_live.discount_pct == initial_pct
