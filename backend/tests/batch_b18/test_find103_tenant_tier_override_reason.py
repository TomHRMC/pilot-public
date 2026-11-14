"""
FIND-103 (S2 High) — tenant_tier_override.override_reason NOT NULL constraint.

Test coverage:
  1. DB: column is NOT NULL after migration
  2. DB: no existing rows with NULL override_reason (backfill verification)
  3. ORM: override_reason field is non-Optional str with nullable=False
  4. Integrity: raw SQL INSERT with override_reason=NULL raises IntegrityError
  5. Integrity: INSERT with valid override_reason succeeds

Test subfolder: tests/batch_b18/
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

# ─────────────────────────────────────────────────────────────────────────────
# 1. DB schema: NOT NULL
# ─────────────────────────────────────────────────────────────────────────────


class TestFind103DBSchema:
    def test_override_reason_column_is_not_nullable(self, db_session):
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_name, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'tenant_tier_override' "
                "  AND column_name = 'override_reason'"
            )
        ).first()

        assert result is not None, (
            "override_reason column missing from tenant_tier_override"
        )
        assert result[1] == "NO", (
            f"override_reason must be NOT NULL, got is_nullable='{result[1]}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Backfill: no NULL rows remain
# ─────────────────────────────────────────────────────────────────────────────


class TestFind103Backfill:
    def test_no_null_override_reason_rows(self, db_session):
        """After backfill migration, zero rows with override_reason=NULL."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT COUNT(*) FROM tenant_tier_override "
                "WHERE override_reason IS NULL"
            )
        ).first()

        assert result is not None
        assert result[0] == 0, (
            f"Expected 0 rows with NULL override_reason after backfill, found {result[0]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. ORM model: non-Optional str
# ─────────────────────────────────────────────────────────────────────────────


class TestFind103ORMModel:
    def test_override_reason_is_not_optional(self):
        import typing

        from app.models.subscription import TenantTierOverride

        hints = typing.get_type_hints(TenantTierOverride)
        field_type = hints.get("override_reason")
        assert field_type is not None, "override_reason not found in type hints"
        origin = getattr(field_type, "__origin__", None)
        assert origin is not typing.Union, (
            f"override_reason must be str (not Optional[str]), got {field_type}"
        )

    def test_override_reason_sa_column_nullable_false(self):
        from app.models.subscription import TenantTierOverride

        col = TenantTierOverride.__table__.c["override_reason"]
        assert col.nullable is False, (
            f"override_reason SA column nullable must be False, got {col.nullable}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4-5. Integrity constraints
# ─────────────────────────────────────────────────────────────────────────────


class TestFind103IntegrityConstraints:
    def _get_operator_user(self, db_session):
        """Find a seeded user for set_by_operator_user_id FK."""
        from sqlalchemy import text

        result = db_session.exec(text('SELECT id FROM "user" LIMIT 1')).first()
        return str(result[0]) if result else None

    def _get_tier_id(self, db_session):
        """Find a seeded subscription tier for override_tier_id FK."""
        from sqlalchemy import text

        result = db_session.exec(
            text("SELECT tier_id FROM subscription_tier LIMIT 1")
        ).first()
        return str(result[0]) if result else None

    def test_null_override_reason_rejected(self, db_session, test_tenant):
        """Raw SQL INSERT with override_reason=NULL must raise IntegrityError."""
        from sqlalchemy import text

        operator_id = self._get_operator_user(db_session)
        if operator_id is None:
            pytest.skip("No user seeded — skipping FK test")

        now = datetime.now(UTC)
        with pytest.raises(IntegrityError):
            db_session.exec(
                text(
                    "INSERT INTO tenant_tier_override "
                    "(tenant_id, override_reason, set_by_operator_user_id, set_at, "
                    " created_at, updated_at) "
                    "VALUES (:tid, NULL, :uid, :now, :now, :now)"
                ).bindparams(
                    tid=str(test_tenant.id),
                    uid=operator_id,
                    now=now,
                )
            )
            db_session.flush()

        db_session.rollback()

    def test_valid_override_reason_accepted(self, db_session, test_tenant):
        """INSERT with valid override_reason must succeed."""
        from sqlalchemy import text
        from sqlmodel import select

        from app.models.subscription import TenantTierOverride

        operator_id = self._get_operator_user(db_session)
        if operator_id is None:
            pytest.skip("No user seeded — skipping insert test")

        # Check if row already exists for this tenant (PK = tenant_id)
        existing = db_session.exec(
            select(TenantTierOverride).where(
                TenantTierOverride.tenant_id == test_tenant.id
            )
        ).first()
        if existing:
            pytest.skip("tenant_tier_override row already exists for test tenant")

        now = datetime.now(UTC)
        db_session.exec(
            text(
                "INSERT INTO tenant_tier_override "
                "(tenant_id, override_reason, set_by_operator_user_id, set_at, "
                " created_at, updated_at) "
                "VALUES (:tid, :reason, :uid, :now, :now, :now)"
            ).bindparams(
                tid=str(test_tenant.id),
                reason="Extended trial per Charter approval",
                uid=operator_id,
                now=now,
            )
        )
        db_session.flush()

        # Verify persisted
        row = db_session.exec(
            select(TenantTierOverride).where(
                TenantTierOverride.tenant_id == test_tenant.id
            )
        ).first()
        assert row is not None
        assert row.override_reason == "Extended trial per Charter approval"

        db_session.rollback()
