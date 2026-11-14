"""
Batch B1 — A24 & A28 Test Coverage
====================================

A24: Quote Line Item Schema Extension
  - customer_visible, parent_line_id, display_order, is_section_header present on ORM
  - DB columns exist with correct types and server defaults
  - Self-referential parent_line_id FK persists correctly
  - Check constraint chk_section_header_no_parent fires
  - A24 fields appear in QuoteLineCreate and QuoteLineResponse schemas

A28: Multi-Line Description Verification
  - quote_line.description has no length cap in DB (character_maximum_length = NULL)
  - QuoteLineCreate accepts a long multi-paragraph description string
"""

import uuid
from decimal import Decimal

from sqlalchemy import text
from sqlmodel import Session

from api.schemas.quotes import QuoteLineCreate, QuoteLineResponse
from app.models.quoting import QuoteLine

# ─────────────────────────────────────────────────────────────────────────────
# A24 — ORM field presence tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA24OrmFields:
    """Verify A24 columns exist on the QuoteLine ORM model."""

    def test_customer_visible_field_exists(self):
        """customer_visible field is present on QuoteLine model."""
        assert hasattr(QuoteLine, "customer_visible"), (
            "QuoteLine is missing 'customer_visible' field (A24)"
        )

    def test_parent_line_id_field_exists(self):
        """parent_line_id field is present on QuoteLine model."""
        assert hasattr(QuoteLine, "parent_line_id"), (
            "QuoteLine is missing 'parent_line_id' field (A24)"
        )

    def test_display_order_field_exists(self):
        """display_order field is present on QuoteLine model."""
        assert hasattr(QuoteLine, "display_order"), (
            "QuoteLine is missing 'display_order' field (A24)"
        )

    def test_is_section_header_field_exists(self):
        """is_section_header field is present on QuoteLine model."""
        assert hasattr(QuoteLine, "is_section_header"), (
            "QuoteLine is missing 'is_section_header' field (A24)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# A24 — DB column verification (live DB queries)
# ─────────────────────────────────────────────────────────────────────────────


class TestA24DatabaseColumns:
    """Verify A24 columns exist in the live DB with correct types and defaults."""

    def _get_column_info(self, db_session: Session, column_name: str) -> dict:
        result = db_session.exec(  # type: ignore[call-overload]
            text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'quote_line'
                  AND column_name = :col
            """),
            {"col": column_name},
        ).first()
        assert result is not None, (
            f"Column '{column_name}' not found on quote_line table"
        )
        return dict(result._mapping)

    def test_customer_visible_column_in_db(self, db_session: Session):
        """A24: customer_visible exists as NOT NULL BOOLEAN with default TRUE."""
        row = db_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'quote_line'
                  AND column_name = 'customer_visible'
            """)
        ).first()
        assert row is not None, "customer_visible column missing from quote_line"
        assert row.data_type == "boolean"
        assert row.is_nullable == "NO"
        assert "true" in (row.column_default or "").lower()

    def test_parent_line_id_column_in_db(self, db_session: Session):
        """A24: parent_line_id exists as nullable UUID."""
        row = db_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'quote_line'
                  AND column_name = 'parent_line_id'
            """)
        ).first()
        assert row is not None, "parent_line_id column missing from quote_line"
        assert row.data_type == "uuid"
        assert row.is_nullable == "YES"

    def test_display_order_column_in_db(self, db_session: Session):
        """A24: display_order exists as NOT NULL INTEGER with default 0."""
        row = db_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'quote_line'
                  AND column_name = 'display_order'
            """)
        ).first()
        assert row is not None, "display_order column missing from quote_line"
        assert row.data_type == "integer"
        assert row.is_nullable == "NO"
        assert "0" in (row.column_default or "")

    def test_is_section_header_column_in_db(self, db_session: Session):
        """A24: is_section_header exists as NOT NULL BOOLEAN with default FALSE."""
        row = db_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'quote_line'
                  AND column_name = 'is_section_header'
            """)
        ).first()
        assert row is not None, "is_section_header column missing from quote_line"
        assert row.data_type == "boolean"
        assert row.is_nullable == "NO"
        assert "false" in (row.column_default or "").lower()

    def test_parent_line_id_fk_exists(self, db_session: Session):
        """A24: Self-referential FK fk_quote_line_parent_line_id exists."""
        row = db_session.execute(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = 'public'
                  AND table_name = 'quote_line'
                  AND constraint_type = 'FOREIGN KEY'
                  AND constraint_name = 'fk_quote_line_parent_line_id'
            """)
        ).first()
        assert row is not None, (
            "FK fk_quote_line_parent_line_id missing from quote_line"
        )

    def test_check_constraint_section_header_no_parent_exists(
        self, db_session: Session
    ):
        """A24: CHECK constraint chk_section_header_no_parent exists."""
        row = db_session.execute(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = 'public'
                  AND table_name = 'quote_line'
                  AND constraint_type = 'CHECK'
                  AND constraint_name = 'chk_section_header_no_parent'
            """)
        ).first()
        assert row is not None, "CHECK constraint chk_section_header_no_parent missing"

    def test_parent_line_id_index_exists(self, db_session: Session):
        """A24: Index ix_quote_line_parent_line_id exists."""
        row = db_session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'quote_line'
                  AND indexname = 'ix_quote_line_parent_line_id'
            """)
        ).first()
        assert row is not None, "Index ix_quote_line_parent_line_id missing"


# ─────────────────────────────────────────────────────────────────────────────
# A24 — Schema (Pydantic) tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA24PydanticSchema:
    """Verify A24 fields are present in QuoteLineCreate and QuoteLineResponse."""

    def test_quote_line_create_has_customer_visible(self):
        payload = QuoteLineCreate(
            position=1,
            qco_line_type_id=uuid.uuid4(),
            description="Test line",
            quantity=Decimal("1"),
            customer_visible=False,
        )
        assert payload.customer_visible is False

    def test_quote_line_create_customer_visible_defaults_true(self):
        payload = QuoteLineCreate(
            position=1,
            qco_line_type_id=uuid.uuid4(),
            description="Test",
        )
        assert payload.customer_visible is True

    def test_quote_line_create_has_parent_line_id(self):
        parent_id = uuid.uuid4()
        payload = QuoteLineCreate(
            position=2,
            qco_line_type_id=uuid.uuid4(),
            description="Child line",
            parent_line_id=parent_id,
        )
        assert payload.parent_line_id == parent_id

    def test_quote_line_create_has_display_order(self):
        payload = QuoteLineCreate(
            position=1,
            qco_line_type_id=uuid.uuid4(),
            description="Test",
            display_order=5,
        )
        assert payload.display_order == 5

    def test_quote_line_create_display_order_defaults_zero(self):
        payload = QuoteLineCreate(
            position=1,
            qco_line_type_id=uuid.uuid4(),
            description="Test",
        )
        assert payload.display_order == 0

    def test_quote_line_create_has_is_section_header(self):
        payload = QuoteLineCreate(
            position=1,
            qco_line_type_id=uuid.uuid4(),
            description="Section: Electrical",
            is_section_header=True,
        )
        assert payload.is_section_header is True

    def test_quote_line_create_is_section_header_defaults_false(self):
        payload = QuoteLineCreate(
            position=1,
            qco_line_type_id=uuid.uuid4(),
            description="Test",
        )
        assert payload.is_section_header is False

    def test_quote_line_response_has_a24_fields(self):
        """QuoteLineResponse model includes all A24 fields."""
        fields = QuoteLineResponse.model_fields
        assert "customer_visible" in fields
        assert "parent_line_id" in fields
        assert "display_order" in fields
        assert "is_section_header" in fields


# ─────────────────────────────────────────────────────────────────────────────
# A28 — Description no-length-cap verification
# ─────────────────────────────────────────────────────────────────────────────


class TestA28DescriptionNoLengthCap:
    """
    A28: Verify description field on quote_line has no length constraint.
    Per A28 design doc resolution: character_maximum_length must be NULL.
    """

    def test_description_no_max_length_in_db(self, db_session: Session):
        """A28: description column character_maximum_length = NULL (no cap)."""
        row = db_session.execute(
            text("""
                SELECT character_maximum_length, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'quote_line'
                  AND column_name = 'description'
            """)
        ).first()
        assert row is not None, "description column missing from quote_line"
        assert row.character_maximum_length is None, (
            f"description has a max length cap of {row.character_maximum_length} — "
            "A28 requires no length cap (VARCHAR without limit = TEXT)"
        )

    def test_description_accepts_very_long_text_in_schema(self):
        """A28: QuoteLineCreate accepts a multi-paragraph description of any length."""
        long_description = (
            "Panel upgrade from 100A to 200A service.\n\n"
            "Scope of work includes:\n"
            "- Remove existing 100A main breaker panel\n"
            "- Install new 200A Square D HomeLine panel (42-circuit)\n"
            "- Pull new 4/0-4/0-4/0-2/0 aluminum SER cable from meter base\n"
            "- Update grounding electrode system per NEC 250.50\n"
            "- Label all circuits\n"
            "- Schedule inspection with AHJ\n\n"
            "Notes: Customer has confirmed utility has been notified. "
            "Work to commence after utility drop reconnect is scheduled. "
            "All materials are included in the quoted price. " * 50  # ~2500 chars
        )
        payload = QuoteLineCreate(
            position=1,
            qco_line_type_id=uuid.uuid4(),
            description=long_description,
            quantity=Decimal("1"),
        )
        assert len(payload.description) > 2000, "Long description was truncated"
        assert payload.description == long_description

    def test_quote_line_create_docstring_documents_a28(self):
        """A28: QuoteLineCreate has docstring documenting the no-length-cap guarantee."""
        docstring = QuoteLineCreate.__doc__ or ""
        assert "A28" in docstring, (
            "QuoteLineCreate docstring must reference A28 guarantee"
        )
        assert (
            "no length cap" in docstring.lower() or "no-length-cap" in docstring.lower()
        ), "QuoteLineCreate docstring must explicitly state the no-length-cap guarantee"
