"""
FIND-067 (S4 Low) — Drop 2 duplicate partial unique indexes on user_endpoint.

Duplicates dropped:
  - idx_user_endpoint_primary_email → exact duplicate of ux_user_email_primary
  - idx_user_endpoint_email_value_lower → exact duplicate of ux_global_primary_email

Canonical indexes retained:
  - ux_user_email_primary
  - ux_global_primary_email

Note: the duplicate indexes were never in the JSON design doc (DB-only artifacts
from a prior migration phase) — no schema_manager.py update required.

Test coverage:
  1. DB: duplicate indexes are absent after migration
  2. DB: canonical indexes are still present (not accidentally dropped)
  3. ORM: UserEndpoint.__table_args__ no longer references the dropped indexes

Test subfolder: tests/batch_b18/
"""

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# 1. Duplicate indexes are absent
# ─────────────────────────────────────────────────────────────────────────────


class TestFind067DuplicateIndexesDropped:
    """Verify the duplicate indexes were removed by migration."""

    @pytest.mark.parametrize(
        "index_name",
        [
            "idx_user_endpoint_primary_email",
            "idx_user_endpoint_email_value_lower",
        ],
    )
    def test_duplicate_index_is_absent(self, db_session, index_name):
        """Duplicate index must not exist after FIND-067 migration."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'user_endpoint' "
                "  AND indexname = :idx"
            ).bindparams(idx=index_name)
        ).first()

        assert result is None, (
            f"Index '{index_name}' must be dropped by FIND-067 migration — "
            f"it is a duplicate of a canonical unique index"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Canonical indexes are still present
# ─────────────────────────────────────────────────────────────────────────────


class TestFind067CanonicalIndexesRetained:
    """Verify the canonical replacement indexes were NOT accidentally dropped."""

    @pytest.mark.parametrize(
        "index_name",
        [
            "ux_user_email_primary",
            "ux_global_primary_email",
        ],
    )
    def test_canonical_index_still_exists(self, db_session, index_name):
        """Canonical index must still exist on user_endpoint after migration."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'user_endpoint' "
                "  AND indexname = :idx"
            ).bindparams(idx=index_name)
        ).first()

        assert result is not None, (
            f"Canonical index '{index_name}' must NOT have been dropped — "
            f"FIND-067 only removes the duplicate indexes"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. ORM model: no longer references the dropped indexes
# ─────────────────────────────────────────────────────────────────────────────


class TestFind067ORMModel:
    """UserEndpoint.__table_args__ must not reference the dropped index names."""

    def test_user_endpoint_table_args_no_primary_email_index(self):
        """idx_user_endpoint_primary_email must not be in UserEndpoint.__table_args__."""
        from sqlalchemy import Index

        from app.models.core import UserEndpoint

        index_names = [
            getattr(arg, "name", None)
            for arg in UserEndpoint.__table_args__
            if isinstance(arg, Index)
        ]
        assert "idx_user_endpoint_primary_email" not in index_names, (
            "idx_user_endpoint_primary_email must be removed from UserEndpoint.__table_args__"
        )

    def test_user_endpoint_table_args_no_email_value_lower_index(self):
        """idx_user_endpoint_email_value_lower must not be in UserEndpoint.__table_args__."""
        from sqlalchemy import Index

        from app.models.core import UserEndpoint

        index_names = [
            getattr(arg, "name", None)
            for arg in UserEndpoint.__table_args__
            if isinstance(arg, Index)
        ]
        assert "idx_user_endpoint_email_value_lower" not in index_names, (
            "idx_user_endpoint_email_value_lower must be removed from UserEndpoint.__table_args__"
        )

    def test_user_endpoint_table_args_only_check_constraints(self):
        """UserEndpoint.__table_args__ should contain only CheckConstraints after FIND-067."""
        from sqlalchemy import CheckConstraint, Index

        from app.models.core import UserEndpoint

        args = UserEndpoint.__table_args__
        index_args = [a for a in args if isinstance(a, Index)]
        check_args = [a for a in args if isinstance(a, CheckConstraint)]

        assert len(index_args) == 0, (
            f"UserEndpoint.__table_args__ must have 0 Index entries after FIND-067, "
            f"found: {[a.name for a in index_args]}"
        )
        assert len(check_args) == 4, (
            f"UserEndpoint.__table_args__ must have 4 CheckConstraints, found {len(check_args)}"
        )
