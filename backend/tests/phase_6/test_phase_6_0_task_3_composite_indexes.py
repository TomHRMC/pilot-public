"""
Test Suite: Phase 6.0 Task 3 - Composite Indexes Verification
Validates composite and sorting indexes for common query patterns.

Reference: phase-6.0-db-schema-sync-10-plan.md - Task 3
"""

from sqlalchemy import text


class TestDescendingCreatedAtIndexes:
    """Test descending created_at indexes"""

    def test_change_order_created_at_index_exists(self, db_session):
        """Verify idx_change_order_created_at index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'change_order'
                AND indexname = 'idx_change_order_created_at'
        """)
        )
        assert result.scalar() == "idx_change_order_created_at"

    def test_qpl_action_created_at_index_exists(self, db_session):
        """Verify idx_qpl_action_created_at index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'quote_public_link_contact_action'
                AND indexname = 'idx_qpl_action_created_at'
        """)
        )
        assert result.scalar() == "idx_qpl_action_created_at"

    def test_quote_version_created_at_index_exists(self, db_session):
        """Verify idx_quote_version_created_at index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'quote_version'
                AND indexname = 'idx_quote_version_created_at'
        """)
        )
        assert result.scalar() == "idx_quote_version_created_at"

    def test_payment_created_at_index_exists(self, db_session):
        """Verify idx_payment_created_at index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'payment'
                AND indexname = 'idx_payment_created_at'
        """)
        )
        assert result.scalar() == "idx_payment_created_at"


class TestCompositeIndexes:
    """Test composite indexes for query performance"""

    def test_connector_run_supplier_started_index_exists(self, db_session):
        """Verify idx_connector_run_supplier_started index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'connector_run_log'
                AND indexname = 'idx_connector_run_supplier_started'
        """)
        )
        assert result.scalar() == "idx_connector_run_supplier_started"

    def test_connector_run_supplier_status_index_exists(self, db_session):
        """Verify idx_connector_run_supplier_status index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'connector_run_log'
                AND indexname = 'idx_connector_run_supplier_status'
        """)
        )
        assert result.scalar() == "idx_connector_run_supplier_status"

    def test_invoice_line_source_index_exists(self, db_session):
        """Verify idx_invoice_line_source index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'invoice_line'
                AND indexname = 'idx_invoice_line_source'
        """)
        )
        assert result.scalar() == "idx_invoice_line_source"

    def test_quote_message_tenant_quote_time_index_exists(self, db_session):
        """Verify idx_quote_message_tenant_quote_time index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'quote_message'
                AND indexname = 'idx_quote_message_tenant_quote_time'
        """)
        )
        assert result.scalar() == "idx_quote_message_tenant_quote_time"

    def test_site_tenant_customer_index_exists(self, db_session):
        """Verify idx_site_tenant_customer index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'site'
                AND indexname = 'idx_site_tenant_customer'
        """)
        )
        assert result.scalar() == "idx_site_tenant_customer"

    def test_tenant_markup_category_index_exists(self, db_session):
        """Verify idx_tenant_markup_category index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'tenant_markup_version'
                AND indexname = 'idx_tenant_markup_category'
        """)
        )
        assert result.scalar() == "idx_tenant_markup_category"

    def test_tenant_user_notif_pref_index_dropped(self, db_session):
        """FIND-080/B21: idx_tenant_user_notif_pref must NOT exist (table was dropped)."""
        result = db_session.execute(
            text("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE schemaname = 'public'
                AND indexname = 'idx_tenant_user_notif_pref'
        """)
        )
        assert result.scalar() == 0, (
            "idx_tenant_user_notif_pref must be dropped with its table — "
            "phase_fe_1_batch_b21_drop_legacy_notification_pref_tables"
        )

    def test_user_sso_provider_id_index_exists(self, db_session):
        """Verify idx_user_sso_provider_id index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'user_sso_identity'
                AND indexname = 'idx_user_sso_provider_id'
        """)
        )
        assert result.scalar() == "idx_user_sso_provider_id"

    def test_usage_ledger_tenant_feature_index_exists(self, db_session):
        """Verify idx_usage_ledger_tenant_feature index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'usage_ledger'
                AND indexname = 'idx_usage_ledger_tenant_feature'
        """)
        )
        assert result.scalar() == "idx_usage_ledger_tenant_feature"


class TestIndexCount:
    """Test total index count for Task 3"""

    def test_all_task_3_indexes_created(self, db_session):
        """Verify all 13 Task 3 indexes exist.

        Note: idx_tenant_user_notif_pref removed from count — table
        tenant_user_notification_pref dropped in FIND-080/B21 (2026-05-18).
        """
        result = db_session.execute(
            text("""
            SELECT COUNT(*) as total_indexes
            FROM pg_indexes
            WHERE schemaname = 'public'
                AND indexname IN (
                    'idx_change_order_created_at',
                    'idx_payment_created_at',
                    'idx_qpl_action_created_at',
                    'idx_quote_version_created_at',
                    'idx_connector_run_supplier_started',
                    'idx_connector_run_supplier_status',
                    'idx_invoice_line_source',
                    'idx_quote_message_tenant_quote_time',
                    'idx_site_tenant_customer',
                    'idx_tenant_markup_category',
                    'idx_user_sso_provider_id',
                    'idx_usage_ledger_tenant_feature'
                )
        """)
        )
        assert result.scalar() == 12


class TestDescendingIndexDefinitions:
    """Verify DESC ordering in index definitions"""

    def test_desc_indexes_contain_desc_keyword(self, db_session):
        """Verify all DESC indexes contain DESC in definition"""
        result = db_session.execute(
            text("""
            SELECT COUNT(*) as desc_count
            FROM pg_indexes
            WHERE schemaname = 'public'
                AND indexname IN (
                    'idx_change_order_created_at',
                    'idx_payment_created_at',
                    'idx_qpl_action_created_at',
                    'idx_quote_version_created_at'
                )
                AND indexdef LIKE '%DESC%'
        """)
        )
        # All 4 simple DESC indexes should contain DESC
        assert result.scalar() == 4

    def test_composite_desc_indexes_contain_desc_keyword(self, db_session):
        """Verify composite indexes with DESC contain DESC in definition"""
        result = db_session.execute(
            text("""
            SELECT COUNT(*) as desc_count
            FROM pg_indexes
            WHERE schemaname = 'public'
                AND indexname IN (
                    'idx_connector_run_supplier_started',
                    'idx_connector_run_supplier_status',
                    'idx_quote_message_tenant_quote_time'
                )
                AND indexdef LIKE '%DESC%'
        """)
        )
        # All 3 composite DESC indexes should contain DESC
        assert result.scalar() == 3
