"""
Test timezone compliance for Phase 4.5 Task 1.

This test suite verifies that all 9 columns fixed in Task 1 properly store
timezone-aware datetime values (v2.0 "Double-Lock" standard).
"""

from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.billing import ProductPlanProductFeatureVersion, ProductPlanVersion
from app.models.catalog import TaxRateVersion, TenantMarkupVersion
from app.models.quoting import PricebookItemVersion, QuotePublicLinkContactAction
from app.models.system import IdempotencyKey, IntegrationSyncMapping, NotificationEvent


class TestTimezoneCompliance:
    """Test timezone-aware datetime fields for Task 1 (9 columns)."""

    def test_idempotency_key_first_seen_at_timezone(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test IdempotencyKey.first_seen_at is timezone-aware."""
        now = datetime.now(UTC)
        key = IdempotencyKey(
            key="test-key-tz",
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            first_seen_at=now,
            status="in_progress",
            expires_at=datetime(2099, 12, 31, 23, 59, 59, tzinfo=UTC),
        )
        db_session.add(key)
        db_session.commit()

        # Retrieve and verify timezone awareness
        retrieved = db_session.exec(
            select(IdempotencyKey).where(IdempotencyKey.key == "test-key-tz")
        ).first()
        assert retrieved is not None
        assert retrieved.first_seen_at.tzinfo is not None
        assert retrieved.first_seen_at.tzinfo == UTC

    def test_notification_event_occurred_at_timezone(
        self, db_session: Session, test_tenant
    ):
        """Test NotificationEvent.occurred_at is timezone-aware."""
        # Create a minimal notification_type for testing
        from app.models.system import NotificationType

        notification_type = NotificationType(
            code="test_notification_tz",
            audience="customer",
            name="Test Notification",
        )
        db_session.add(notification_type)
        db_session.commit()

        now = datetime.now(UTC)
        event = NotificationEvent(
            tenant_id=test_tenant.id,
            notification_type_code=notification_type.code,
            entity_type_code="customer",
            entity_id="test-entity",
            occurred_at=now,
        )
        db_session.add(event)
        db_session.commit()

        # Retrieve and verify timezone awareness
        retrieved = db_session.exec(
            select(NotificationEvent).where(NotificationEvent.id == event.id)
        ).first()
        assert retrieved is not None
        assert retrieved.occurred_at.tzinfo is not None
        assert retrieved.occurred_at.tzinfo == UTC

    def test_integration_sync_mapping_last_synced_at_timezone(
        self, db_session: Session, test_tenant
    ):
        """Test IntegrationSyncMapping.last_synced_at is timezone-aware."""
        # Create a minimal app_service for testing
        from app.models.system import AppService

        app_service = AppService(
            tenant_id=test_tenant.id,
            name="Test QuickBooks",
            category_code="accounting",
            provider_code="quickbooks",
        )
        db_session.add(app_service)
        db_session.commit()

        now = datetime.now(UTC)
        mapping = IntegrationSyncMapping(
            tenant_id=test_tenant.id,
            app_service_id=app_service.id,
            entity_type_code="customer",
            entity_id=test_tenant.id,
            external_id="EXT-123",
            last_synced_at=now,
        )
        db_session.add(mapping)
        db_session.commit()

        # Retrieve and verify timezone awareness
        retrieved = db_session.exec(
            select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.id == mapping.id
            )
        ).first()
        assert retrieved is not None
        assert retrieved.last_synced_at.tzinfo is not None
        assert retrieved.last_synced_at.tzinfo == UTC

    def test_pricebook_item_version_recorded_at_timezone(
        self, db_session: Session, test_tenant
    ):
        """Test PricebookItemVersion.recorded_at is timezone-aware."""
        # Create a minimal pricebook_item for testing
        from app.models.quoting import PricebookItem

        pricebook_item = PricebookItem(
            tenant_id=test_tenant.id,
            sku="TEST-SKU-TZ",
            name="Test Item",
        )
        db_session.add(pricebook_item)
        db_session.commit()

        now = datetime.now(UTC)
        version = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=pricebook_item.id,
            default_unit_price_cents=10000,
            valid_period=f"[{now.isoformat()},)",
            recorded_at=now,
        )
        db_session.add(version)
        db_session.commit()

        # Retrieve and verify timezone awareness
        retrieved = db_session.exec(
            select(PricebookItemVersion).where(PricebookItemVersion.id == version.id)
        ).first()
        assert retrieved is not None
        assert retrieved.recorded_at.tzinfo is not None
        assert retrieved.recorded_at.tzinfo == UTC

    def test_quote_public_link_contact_action_occurred_at_timezone(
        self,
        db_session: Session,
        test_customer,
        test_site,
        test_quote_status,
        test_contact,
    ):
        """Test QuotePublicLinkContactAction.occurred_at is timezone-aware."""
        # Create a minimal quote for testing
        from app.models.quoting import Quote

        quote = Quote(
            tenant_id=test_customer.tenant_id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=test_quote_status.id,
        )
        db_session.add(quote)
        db_session.commit()

        # Create a minimal qpl_contact_action_type for testing
        from app.models.quoting import QplContactActionType

        action_type = QplContactActionType(
            code="viewed_tz",
            name="Viewed",
        )
        db_session.add(action_type)
        db_session.commit()

        now = datetime.now(UTC)
        action = QuotePublicLinkContactAction(
            tenant_id=quote.tenant_id,
            quote_id=quote.id,
            contact_id=test_contact.id,
            qpl_contact_action_type_id=action_type.id,
            occurred_at=now,
        )
        db_session.add(action)
        db_session.commit()

        # Retrieve and verify timezone awareness
        retrieved = db_session.exec(
            select(QuotePublicLinkContactAction).where(
                QuotePublicLinkContactAction.id == action.id
            )
        ).first()
        assert retrieved is not None
        assert retrieved.occurred_at.tzinfo is not None
        assert retrieved.occurred_at.tzinfo == UTC

    def test_product_plan_product_feature_version_recorded_at_timezone(
        self, db_session: Session
    ):
        """Test ProductPlanProductFeatureVersion.recorded_at is timezone-aware."""
        # Create minimal product_plan and product_feature for testing
        from app.models.billing import ProductFeature, ProductPlan

        plan = ProductPlan(code="test_plan_tz", name="Test Plan")
        feature = ProductFeature(
            code="test_feature_tz",
            name="Test Feature",
            unit="seats",  # unit is required
            category="core",
            is_metered=False,
        )
        db_session.add(plan)
        db_session.add(feature)
        db_session.commit()

        now = datetime.now(UTC)
        version = ProductPlanProductFeatureVersion(
            product_plan_code=plan.code,
            product_feature_code=feature.code,
            limit_quantity=100,
            included_quantity=10,
            valid_period=f"[{now.isoformat()},)",
            recorded_at=now,
        )
        db_session.add(version)
        db_session.commit()

        # Retrieve and verify timezone awareness
        retrieved = db_session.exec(
            select(ProductPlanProductFeatureVersion).where(
                ProductPlanProductFeatureVersion.id == version.id
            )
        ).first()
        assert retrieved is not None
        assert retrieved.recorded_at.tzinfo is not None
        assert retrieved.recorded_at.tzinfo == UTC

    def test_product_plan_version_recorded_at_timezone(self, db_session: Session):
        """Test ProductPlanVersion.recorded_at is timezone-aware."""
        # Create minimal product_plan for testing
        from app.models.billing import ProductPlan

        plan = ProductPlan(code="test_plan_v2", name="Test Plan V2")
        db_session.add(plan)
        db_session.commit()

        now = datetime.now(UTC)
        version = ProductPlanVersion(
            product_plan_code=plan.code,
            name="Test Plan V1",
            price_cents=9999,
            valid_period=f"[{now.isoformat()},)",
            recorded_at=now,
        )
        db_session.add(version)
        db_session.commit()

        # Retrieve and verify timezone awareness
        retrieved = db_session.exec(
            select(ProductPlanVersion).where(ProductPlanVersion.id == version.id)
        ).first()
        assert retrieved is not None
        assert retrieved.recorded_at.tzinfo is not None
        assert retrieved.recorded_at.tzinfo == UTC

    def test_tax_rate_version_recorded_at_timezone(self, db_session: Session):
        """Test TaxRateVersion.recorded_at is timezone-aware."""
        now = datetime.now(UTC)
        version = TaxRateVersion(
            jurisdiction_code="CA-SF",
            description="San Francisco Sales Tax",
            rate_pct=8.5,
            valid_period=f"[{now.isoformat()},)",
            recorded_at=now,
        )
        db_session.add(version)
        db_session.commit()

        # Retrieve and verify timezone awareness
        retrieved = db_session.exec(
            select(TaxRateVersion).where(TaxRateVersion.id == version.id)
        ).first()
        assert retrieved is not None
        assert retrieved.recorded_at.tzinfo is not None
        assert retrieved.recorded_at.tzinfo == UTC

    def test_tenant_markup_version_recorded_at_timezone(
        self, db_session: Session, test_tenant
    ):
        """Test TenantMarkupVersion.recorded_at is timezone-aware."""
        # Create minimal job_expense_category for testing
        from app.models.fulfillment import JobExpenseCategory

        category = JobExpenseCategory(
            code="material",
            name="Material",
        )
        db_session.add(category)
        db_session.commit()

        now = datetime.now(UTC)
        version = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            job_expense_category_code=category.code,
            markup_pct=25.0,
            valid_period=f"[{now.isoformat()},)",
            recorded_at=now,
        )
        db_session.add(version)
        db_session.commit()

        # Retrieve and verify timezone awareness
        retrieved = db_session.exec(
            select(TenantMarkupVersion).where(TenantMarkupVersion.id == version.id)
        ).first()
        assert retrieved is not None
        assert retrieved.recorded_at.tzinfo is not None
        assert retrieved.recorded_at.tzinfo == UTC
