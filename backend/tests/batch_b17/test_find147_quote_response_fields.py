"""
FIND-147 (S3 Medium) — QuoteResponse: add A3 discount fields + A83 acceptance/decline fields.

Fields added to QuoteResponse:
  A3 discount: discount_pct, discount_amount_cents, discount_expires_at, discount_applied_by_user_id
  A83 acceptance: customer_accepted_at, customer_acceptance_comment, customer_declined_at,
                  customer_decline_comment, customer_decline_reason, customer_email_at_action

Test subfolder: tests/batch_b17/
"""

import uuid


class TestQuoteResponseHasDiscountFields:
    """FIND-147: QuoteResponse must expose A3 discount fields."""

    def test_has_discount_pct(self):
        from api.schemas.quotes import QuoteResponse

        assert "discount_pct" in QuoteResponse.model_fields

    def test_has_discount_amount_cents(self):
        from api.schemas.quotes import QuoteResponse

        assert "discount_amount_cents" in QuoteResponse.model_fields

    def test_has_discount_expires_at(self):
        from api.schemas.quotes import QuoteResponse

        assert "discount_expires_at" in QuoteResponse.model_fields

    def test_has_discount_applied_by_user_id(self):
        from api.schemas.quotes import QuoteResponse

        assert "discount_applied_by_user_id" in QuoteResponse.model_fields

    def test_discount_fields_are_optional_with_none_defaults(self):
        from api.schemas.quotes import QuoteResponse

        resp = QuoteResponse(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            site_id=uuid.uuid4(),
            status_id=uuid.uuid4(),
            subtotal_cents=10000,
            tax_cents=0,
            total_cents=10000,
            currency="USD",
            is_active=True,
        )
        assert resp.discount_pct is None
        assert resp.discount_amount_cents is None
        assert resp.discount_expires_at is None
        assert resp.discount_applied_by_user_id is None


class TestQuoteResponseHasAcceptanceFields:
    """FIND-147: QuoteResponse must expose A83 acceptance/decline fields."""

    def test_has_customer_accepted_at(self):
        from api.schemas.quotes import QuoteResponse

        assert "customer_accepted_at" in QuoteResponse.model_fields

    def test_has_customer_acceptance_comment(self):
        from api.schemas.quotes import QuoteResponse

        assert "customer_acceptance_comment" in QuoteResponse.model_fields

    def test_has_customer_declined_at(self):
        from api.schemas.quotes import QuoteResponse

        assert "customer_declined_at" in QuoteResponse.model_fields

    def test_has_customer_decline_comment(self):
        from api.schemas.quotes import QuoteResponse

        assert "customer_decline_comment" in QuoteResponse.model_fields

    def test_has_customer_decline_reason(self):
        from api.schemas.quotes import QuoteResponse

        assert "customer_decline_reason" in QuoteResponse.model_fields

    def test_has_customer_email_at_action(self):
        from api.schemas.quotes import QuoteResponse

        assert "customer_email_at_action" in QuoteResponse.model_fields

    def test_acceptance_fields_are_optional_with_none_defaults(self):
        from api.schemas.quotes import QuoteResponse

        resp = QuoteResponse(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            site_id=uuid.uuid4(),
            status_id=uuid.uuid4(),
            subtotal_cents=10000,
            tax_cents=0,
            total_cents=10000,
            currency="USD",
            is_active=True,
        )
        assert resp.customer_accepted_at is None
        assert resp.customer_acceptance_comment is None
        assert resp.customer_declined_at is None
        assert resp.customer_decline_comment is None
        assert resp.customer_decline_reason is None
        assert resp.customer_email_at_action is None

    def test_quote_response_populates_from_orm(self, db_session):
        """QuoteResponse.model_validate populates all new fields from Quote ORM."""
        import uuid as _uuid
        from datetime import UTC, datetime

        from sqlmodel import select

        from api.schemas.quotes import QuoteResponse
        from app.models.core import Tenant
        from app.models.crm import Customer, Site
        from app.models.quoting import Quote, QuoteStatus
        from app.models.subscription import SubscriptionTier

        tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
        ).first()
        assert tier is not None

        tenant = Tenant(
            id=_uuid.uuid4(),
            name=f"FIND147-{_uuid.uuid4().hex[:6]}",
            is_active=True,
            current_subscription_tier_id=tier.tier_id,
        )
        db_session.add(tenant)
        db_session.flush()

        customer = Customer(id=_uuid.uuid4(), tenant_id=tenant.id, display_name="Test")
        db_session.add(customer)
        db_session.flush()

        site = Site(
            id=_uuid.uuid4(),
            tenant_id=tenant.id,
            customer_id=customer.id,
            display_name="Test Site",
        )
        db_session.add(site)
        db_session.flush()

        qs = db_session.exec(
            select(QuoteStatus).where(
                QuoteStatus.code == "draft", QuoteStatus.tenant_id.is_(None)
            )
        ).first()

        accepted_at = datetime.now(UTC)
        quote = Quote(
            id=_uuid.uuid4(),
            tenant_id=tenant.id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=qs.id if qs else _uuid.uuid4(),
            currency="USD",
            subtotal_cents=10000,
            tax_cents=0,
            total_cents=9500,
            discount_pct=5,
            discount_amount_cents=500,
            customer_accepted_at=accepted_at,
            customer_acceptance_comment="Looks good!",
            customer_email_at_action="customer@test.test",
        )
        db_session.add(quote)
        db_session.flush()

        resp = QuoteResponse.model_validate(quote)
        assert resp.discount_pct == 5
        assert resp.discount_amount_cents == 500
        assert resp.customer_accepted_at is not None
        assert resp.customer_acceptance_comment == "Looks good!"
        assert resp.customer_email_at_action == "customer@test.test"
