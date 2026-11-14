"""
FIND-070 (S2 High) — B18 schema: Add qb_item_name_hint to qco_line_type + seed 3 system rows.

PRD-§3.6-F7: QB line item mapping at QB connect time.

Column added:
  qco_line_type.qb_item_name_hint VARCHAR NULL
  — used at QB connect time to search tenant's QB Items catalog by name
  — seeded for system rows: labor='Services', material='Materials', misc='Miscellaneous'

Test coverage:
  1. DB schema: column exists and is nullable
  2. ORM model: QcoLineType has qb_item_name_hint field
  3. Seed data: system rows have correct hints after migration
  4. Integrity: NULL hint is valid (tenant-custom rows, 'discount' system row)
  5. ORM insert: hint persists correctly for new rows

Test subfolder: tests/batch_b18/
"""

import uuid
from datetime import UTC, datetime

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# 1. DB schema
# ─────────────────────────────────────────────────────────────────────────────


class TestFind070DBSchema:
    """Verify qb_item_name_hint column was created by migration."""

    def test_column_exists_and_is_nullable(self, db_session):
        """qb_item_name_hint must exist on qco_line_type and be nullable."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_name, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'qco_line_type' "
                "  AND column_name = 'qb_item_name_hint'"
            )
        ).first()

        assert result is not None, "qb_item_name_hint column missing from qco_line_type"
        assert result[1] == "YES", (
            f"qb_item_name_hint must be nullable, got is_nullable='{result[1]}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. ORM model
# ─────────────────────────────────────────────────────────────────────────────


class TestFind070ORMModel:
    """QcoLineType must expose qb_item_name_hint field."""

    def test_qco_line_type_has_qb_item_name_hint(self):
        from app.models.quoting import QcoLineType

        assert hasattr(QcoLineType, "qb_item_name_hint"), (
            "QcoLineType.qb_item_name_hint field missing"
        )

    def test_qb_item_name_hint_is_optional(self):
        """qb_item_name_hint must be Optional (nullable column)."""
        import typing

        from app.models.quoting import QcoLineType

        hints = typing.get_type_hints(QcoLineType)
        field_type = hints.get("qb_item_name_hint")
        assert field_type is not None, "qb_item_name_hint not found in type hints"
        # Should be Optional[str] (Union[str, None])
        origin = getattr(field_type, "__origin__", None)
        assert origin is typing.Union, (
            f"qb_item_name_hint must be Optional[str], got {field_type}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Seed data
# ─────────────────────────────────────────────────────────────────────────────


class TestFind070SeedData:
    """System rows must have correct qb_item_name_hint values after migration."""

    @pytest.mark.parametrize(
        "code,expected_hint",
        [
            ("labor", "Services"),
            ("material", "Materials"),
            ("misc", "Miscellaneous"),
        ],
    )
    def test_system_row_has_correct_hint(self, db_session, code, expected_hint):
        """System qco_line_type row must have the correct qb_item_name_hint."""
        from sqlmodel import select

        from app.models.quoting import QcoLineType

        row = db_session.exec(
            select(QcoLineType).where(
                QcoLineType.code == code,
                QcoLineType.tenant_id == None,
            )
        ).first()

        assert row is not None, f"System qco_line_type row code='{code}' not found"
        assert row.qb_item_name_hint == expected_hint, (
            f"qco_line_type code='{code}' must have qb_item_name_hint='{expected_hint}', "
            f"got '{row.qb_item_name_hint}'"
        )

    def test_discount_system_row_hint_is_null(self, db_session):
        """'discount' system row must have NULL hint — discounts handled separately in QB."""
        from sqlmodel import select

        from app.models.quoting import QcoLineType

        row = db_session.exec(
            select(QcoLineType).where(
                QcoLineType.code == "discount",
                QcoLineType.tenant_id == None,
            )
        ).first()

        if row is None:
            pytest.skip("'discount' system row not seeded — skipping")

        assert row.qb_item_name_hint is None, (
            f"'discount' system row must have NULL qb_item_name_hint, "
            f"got '{row.qb_item_name_hint}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4 & 5. ORM insert: NULL and non-null hints persist correctly
# ─────────────────────────────────────────────────────────────────────────────


class TestFind070ORMInsertBehavior:
    """Verify new column works correctly via ORM inserts."""

    def test_new_row_with_null_hint_persists(self, db_session, test_tenant):
        """A tenant-custom qco_line_type with no hint (NULL) must persist."""
        from sqlmodel import select

        from app.models.quoting import QcoLineType

        now = datetime.now(UTC)
        code = f"custom_{uuid.uuid4().hex[:8]}"
        row = QcoLineType(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            code=code,
            name="Custom Line Type",
            qb_item_name_hint=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(row)
        db_session.commit()

        fetched = db_session.exec(
            select(QcoLineType).where(QcoLineType.id == row.id)
        ).first()
        assert fetched is not None
        assert fetched.qb_item_name_hint is None

    def test_new_row_with_hint_persists(self, db_session, test_tenant):
        """A tenant-custom qco_line_type with a hint must persist the hint value."""
        from sqlmodel import select

        from app.models.quoting import QcoLineType

        now = datetime.now(UTC)
        code = f"custom_{uuid.uuid4().hex[:8]}"
        row = QcoLineType(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            code=code,
            name="Custom Labor Type",
            qb_item_name_hint="Custom Services",
            created_at=now,
            updated_at=now,
        )
        db_session.add(row)
        db_session.commit()

        fetched = db_session.exec(
            select(QcoLineType).where(QcoLineType.id == row.id)
        ).first()
        assert fetched is not None
        assert fetched.qb_item_name_hint == "Custom Services"
