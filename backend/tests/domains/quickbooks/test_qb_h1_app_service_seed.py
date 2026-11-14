"""
QB-H1 Task 1 — app_service* Registry Restoration: Seed Verification Tests

Verifies that the QuickBooks app_service trio (category, provider, global row)
and the qb_connection_expired notification type + templates are present after
the QB-H1 migration + seed_core.py / seed_platform.py ownership change.

These tests assert against the **shared dev database** (which has the migration
applied and seeds run). They are ID-scoped — never assert on total row counts.

Batch: QB-H1
Design: dev-docs/architecture-design/batch-designs/batch-qb-h1-design.md §B, §C.1
"""

import uuid

import pytest
from sqlmodel import select

from app.models.system import (
    AppService,
    NotificationTemplate,
    NotificationType,
)

pytestmark = [
    pytest.mark.domain_quickbooks,
    pytest.mark.unit,
]

# Deterministic UUID for the global app_service row (design §B.4).
GLOBAL_APP_SERVICE_ID = uuid.UUID("00000000-0000-0000-0000-000000000aa5")


class TestAppServiceTrioSeed:
    """Verify the app_service trio rows are present and correctly shaped."""

    def test_category_accounting_exists(self, db_session):
        """app_service_category 'accounting' row is present and active."""
        from app.models.system import AppServiceCategory

        cat = db_session.exec(
            select(AppServiceCategory).where(AppServiceCategory.code == "accounting")
        ).first()
        assert cat is not None, "app_service_category 'accounting' must exist"
        assert cat.is_active is True
        assert "Accounting" in cat.description

    def test_provider_quickbooks_exists(self, db_session):
        """app_service_provider 'quickbooks' row is present and active."""
        from app.models.system import AppServiceProvider

        prov = db_session.exec(
            select(AppServiceProvider).where(AppServiceProvider.code == "quickbooks")
        ).first()
        assert prov is not None, "app_service_provider 'quickbooks' must exist"
        assert prov.is_active is True
        assert "QuickBooks" in prov.description

    def test_provider_intuit_retired(self, db_session):
        """The orphan 'intuit' provider row must NOT exist (design §G Q1)."""
        from app.models.system import AppServiceProvider

        prov = db_session.exec(
            select(AppServiceProvider).where(AppServiceProvider.code == "intuit")
        ).first()
        assert prov is None, (
            "app_service_provider 'intuit' must be retired — canonical code is 'quickbooks'"
        )

    def test_global_app_service_row_exists(self, db_session):
        """The global app_service row exists at the deterministic UUID."""
        svc = db_session.exec(
            select(AppService).where(AppService.id == GLOBAL_APP_SERVICE_ID)
        ).first()
        assert svc is not None, (
            f"Global app_service row at {GLOBAL_APP_SERVICE_ID} must exist"
        )
        assert svc.tenant_id is None, "Global row must have tenant_id IS NULL"
        assert svc.provider_code == "quickbooks"
        assert svc.category_code == "accounting"
        assert svc.is_active is True
        assert svc.name == "QuickBooks Online"


class TestQbConnectionExpiredNotification:
    """Verify the qb_connection_expired notification type + 3 templates."""

    def test_notification_type_exists(self, db_session):
        """qb_connection_expired notification_type row is present."""
        nt = db_session.exec(
            select(NotificationType).where(
                NotificationType.code == "qb_connection_expired"
            )
        ).first()
        assert nt is not None, "notification_type 'qb_connection_expired' must exist"
        assert nt.is_active is True
        assert nt.audience == "tenant"

    def test_email_template_exists(self, db_session):
        """qb_connection_expired email template (tenant_id IS NULL) is present."""
        tmpl = db_session.exec(
            select(NotificationTemplate).where(
                NotificationTemplate.notification_type_code == "qb_connection_expired",
                NotificationTemplate.channel == "email",
                NotificationTemplate.tenant_id == None,
            )
        ).first()
        assert tmpl is not None, "qb_connection_expired email template must exist"
        assert tmpl.is_active is True
        assert tmpl.locale == "en"
        assert "Connection expired" in tmpl.subject

    def test_in_app_template_exists(self, db_session):
        """qb_connection_expired in_app template (tenant_id IS NULL) is present."""
        tmpl = db_session.exec(
            select(NotificationTemplate).where(
                NotificationTemplate.notification_type_code == "qb_connection_expired",
                NotificationTemplate.channel == "in_app",
                NotificationTemplate.tenant_id == None,
            )
        ).first()
        assert tmpl is not None, "qb_connection_expired in_app template must exist"
        assert tmpl.is_active is True
        assert tmpl.locale == "en"

    def test_push_template_exists(self, db_session):
        """qb_connection_expired push template (tenant_id IS NULL) is present."""
        tmpl = db_session.exec(
            select(NotificationTemplate).where(
                NotificationTemplate.notification_type_code == "qb_connection_expired",
                NotificationTemplate.channel == "push",
                NotificationTemplate.tenant_id == None,
            )
        ).first()
        assert tmpl is not None, "qb_connection_expired push template must exist"
        assert tmpl.is_active is True
        assert tmpl.locale == "en"

    def test_exactly_three_templates(self, db_session):
        """Exactly 3 qb_connection_expired templates (email/in_app/push) exist."""
        templates = db_session.exec(
            select(NotificationTemplate).where(
                NotificationTemplate.notification_type_code == "qb_connection_expired",
                NotificationTemplate.tenant_id == None,
            )
        ).all()
        channels = {t.channel for t in templates}
        assert channels == {"email", "in_app", "push"}, (
            f"Expected email/in_app/push, got {channels}"
        )
