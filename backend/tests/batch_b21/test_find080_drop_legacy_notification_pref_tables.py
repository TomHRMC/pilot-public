"""
Batch B21 — FIND-080: Drop legacy notification preference tables
=================================================================

FIND-080 (S3 Medium): Drop legacy `tenant_notification_default`,
`tenant_user_notification_pref`, and `contact_notification_pref` tables.
These tables were superseded by the `NotificationPreference` model and had:
  - 0 rows each (MCP-verified 2026-05-18)
  - Zero active consumers in api/, services/, tasks/

Migration: phase_fe_1_batch_b21_drop_legacy_notification_pref_tables
"""

from sqlalchemy import text


class TestFind080DroppedTables:
    """FIND-080: Verify legacy notification preference tables have been dropped."""

    def test_tenant_notification_default_does_not_exist(self, db_session):
        """tenant_notification_default table must not exist after migration."""
        result = db_session.execute(
            text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'tenant_notification_default'
            """)
        )
        assert result.scalar() == 0, (
            "tenant_notification_default table must be dropped by "
            "phase_fe_1_batch_b21_drop_legacy_notification_pref_tables"
        )

    def test_tenant_user_notification_pref_does_not_exist(self, db_session):
        """tenant_user_notification_pref table must not exist after migration."""
        result = db_session.execute(
            text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'tenant_user_notification_pref'
            """)
        )
        assert result.scalar() == 0, (
            "tenant_user_notification_pref table must be dropped by "
            "phase_fe_1_batch_b21_drop_legacy_notification_pref_tables"
        )

    def test_contact_notification_pref_does_not_exist(self, db_session):
        """contact_notification_pref table must not exist after migration."""
        result = db_session.execute(
            text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'contact_notification_pref'
            """)
        )
        assert result.scalar() == 0, (
            "contact_notification_pref table must be dropped by "
            "phase_fe_1_batch_b21_drop_legacy_notification_pref_tables"
        )

    def test_all_three_tables_dropped(self, db_session):
        """Combined check: none of the three legacy tables must exist."""
        result = db_session.execute(
            text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                    'tenant_notification_default',
                    'tenant_user_notification_pref',
                    'contact_notification_pref'
                  )
            """)
        )
        count = result.scalar()
        assert count == 0, (
            f"Expected 0 legacy notification pref tables to exist, found {count}. "
            "Migration phase_fe_1_batch_b21_drop_legacy_notification_pref_tables "
            "must drop all three."
        )

    def test_orm_classes_removed_from_models_init(self):
        """ContactNotificationPref, TenantUserNotificationPref, TenantNotificationDefault
        must not be importable from app.models after B21 removal."""
        import app.models as models_module

        assert not hasattr(models_module, "ContactNotificationPref"), (
            "ContactNotificationPref must be removed from app.models — "
            "legacy table dropped in FIND-080/B21"
        )
        assert not hasattr(models_module, "TenantUserNotificationPref"), (
            "TenantUserNotificationPref must be removed from app.models — "
            "legacy table dropped in FIND-080/B21"
        )
        assert not hasattr(models_module, "TenantNotificationDefault"), (
            "TenantNotificationDefault must be removed from app.models — "
            "legacy table dropped in FIND-080/B21"
        )

    def test_idx_tenant_user_notif_pref_does_not_exist(self, db_session):
        """idx_tenant_user_notif_pref index must be dropped with its table."""
        result = db_session.execute(
            text("""
                SELECT COUNT(*) FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_tenant_user_notif_pref'
            """)
        )
        assert result.scalar() == 0, (
            "idx_tenant_user_notif_pref index must be dropped with "
            "tenant_user_notification_pref table (CASCADE)"
        )
