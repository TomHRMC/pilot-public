"""
FIND-074 (S3 Medium) — Add 2 composite indexes on invoice table.

Indexes added:
  - idx_invoice_tenant_status (tenant_id, status_id)
  - idx_invoice_tenant_created_at (tenant_id, created_at DESC)

Test coverage:
  1. DB: both composite indexes exist after migration
  2. ORM: Invoice.__table_args__ contains both Index entries

Test subfolder: tests/batch_b18/
"""

import pytest


class TestFind074CompositeIndexesExist:
    """Both composite indexes must exist on the invoice table after migration."""

    @pytest.mark.parametrize(
        "index_name",
        [
            "idx_invoice_tenant_status",
            "idx_invoice_tenant_created_at",
        ],
    )
    def test_composite_index_exists(self, db_session, index_name):
        """Composite index must exist on invoice table."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'invoice' "
                "  AND indexname = :idx"
            ).bindparams(idx=index_name)
        ).first()

        assert result is not None, (
            f"Index '{index_name}' must exist on invoice table (FIND-074 migration)"
        )


class TestFind074ORMModel:
    """Invoice.__table_args__ must contain both new composite index entries."""

    def test_invoice_table_args_has_tenant_status_index(self):
        from sqlalchemy import Index

        from app.models.billing import Invoice

        names = [
            getattr(a, "name", None)
            for a in Invoice.__table_args__
            if isinstance(a, Index)
        ]
        assert "idx_invoice_tenant_status" in names, (
            "idx_invoice_tenant_status missing from Invoice.__table_args__"
        )

    def test_invoice_table_args_has_tenant_created_at_index(self):
        from sqlalchemy import Index

        from app.models.billing import Invoice

        names = [
            getattr(a, "name", None)
            for a in Invoice.__table_args__
            if isinstance(a, Index)
        ]
        assert "idx_invoice_tenant_created_at" in names, (
            "idx_invoice_tenant_created_at missing from Invoice.__table_args__"
        )
