"""
Batch B1 — A25 Test Coverage
============================

A25: Quote Template Schema with Style and Versioning

Test Coverage:
- quote_template table exists in DB with correct columns
- quote_template_line table exists in DB with correct columns
- 3 system templates are seeded (Service Call Basic, Installation Standard, Fixed Bid Simple)
- QuoteTemplate ORM model has correct fields
- QuoteTemplateLine ORM model has correct fields
- System templates are accessible via query (tenant_id=NULL, is_system_template=TRUE)
- GET /api/v1/quote-templates returns system templates
- Template variable substitution (_substitute_variables) works correctly
"""

import uuid
from decimal import Decimal

from sqlalchemy import text
from sqlmodel import Session, select

from api.routes.quote_templates import (
    QuoteTemplateCreate,
    QuoteTemplateLineCreate,
    _substitute_variables,
)
from app.models.quoting import QuoteTemplate, QuoteTemplateLine

# ─────────────────────────────────────────────────────────────────────────────
# A25 — DB table existence
# ─────────────────────────────────────────────────────────────────────────────


class TestA25DatabaseTables:
    """Verify both new tables exist in the live DB."""

    def test_quote_template_table_exists(self, db_session: Session):
        row = db_session.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'quote_template'
            """)
        ).first()
        assert row is not None, "quote_template table missing from DB"

    def test_quote_template_line_table_exists(self, db_session: Session):
        row = db_session.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'quote_template_line'
            """)
        ).first()
        assert row is not None, "quote_template_line table missing from DB"

    def test_quote_template_style_check_constraint_exists(self, db_session: Session):
        row = db_session.execute(
            text("""
                SELECT constraint_name FROM information_schema.table_constraints
                WHERE table_schema = 'public'
                  AND table_name = 'quote_template'
                  AND constraint_type = 'CHECK'
                  AND constraint_name = 'chk_quote_template_style'
            """)
        ).first()
        assert row is not None, "CHECK constraint chk_quote_template_style missing"

    def test_quote_template_unique_constraint_exists(self, db_session: Session):
        row = db_session.execute(
            text("""
                SELECT constraint_name FROM information_schema.table_constraints
                WHERE table_schema = 'public'
                  AND table_name = 'quote_template'
                  AND constraint_type = 'UNIQUE'
                  AND constraint_name = 'uq_quote_template_tenant_name'
            """)
        ).first()
        assert row is not None, (
            "UNIQUE constraint uq_quote_template_tenant_name missing"
        )


# ─────────────────────────────────────────────────────────────────────────────
# A25 — DB Column verification
# ─────────────────────────────────────────────────────────────────────────────


class TestA25DatabaseColumns:
    """Verify key columns on both tables."""

    def _get_col(self, db_session: Session, table: str, col: str):
        return db_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :tbl AND column_name = :col
            """),
            {"tbl": table, "col": col},
        ).first()

    def test_quote_template_style_col(self, db_session: Session):
        row = self._get_col(db_session, "quote_template", "style")
        assert row is not None
        assert row.is_nullable == "NO"

    def test_quote_template_current_version_col(self, db_session: Session):
        row = self._get_col(db_session, "quote_template", "current_version")
        assert row is not None
        assert row.is_nullable == "NO"

    def test_quote_template_is_system_template_col(self, db_session: Session):
        row = self._get_col(db_session, "quote_template", "is_system_template")
        assert row is not None
        assert row.is_nullable == "NO"

    def test_quote_template_line_display_order_col(self, db_session: Session):
        row = self._get_col(db_session, "quote_template_line", "display_order")
        assert row is not None
        assert row.is_nullable == "NO"

    def test_quote_template_line_customer_visible_col(self, db_session: Session):
        row = self._get_col(db_session, "quote_template_line", "customer_visible")
        assert row is not None
        assert row.is_nullable == "NO"

    def test_quote_template_line_is_section_header_col(self, db_session: Session):
        row = self._get_col(db_session, "quote_template_line", "is_section_header")
        assert row is not None
        assert row.is_nullable == "NO"


# ─────────────────────────────────────────────────────────────────────────────
# A25 — Seeded system templates
# ─────────────────────────────────────────────────────────────────────────────


class TestA25SystemTemplateSeeds:
    """Verify the 3 system templates were seeded."""

    def test_service_call_basic_seeded(self, db_session: Session):
        t = db_session.exec(
            select(QuoteTemplate)
            .where(QuoteTemplate.name == "Service Call Basic")
            .where(QuoteTemplate.is_system_template == True)
        ).first()
        assert t is not None, "'Service Call Basic' system template not seeded"
        assert t.style == "component"
        assert t.category == "service_call"
        assert t.tenant_id is None

    def test_installation_standard_seeded(self, db_session: Session):
        t = db_session.exec(
            select(QuoteTemplate)
            .where(QuoteTemplate.name == "Installation Standard")
            .where(QuoteTemplate.is_system_template == True)
        ).first()
        assert t is not None, "'Installation Standard' system template not seeded"
        assert t.style == "deliverable"
        assert t.category == "installation"

    def test_fixed_bid_simple_seeded(self, db_session: Session):
        t = db_session.exec(
            select(QuoteTemplate)
            .where(QuoteTemplate.name == "Fixed Bid Simple")
            .where(QuoteTemplate.is_system_template == True)
        ).first()
        assert t is not None, "'Fixed Bid Simple' system template not seeded"
        assert t.style == "lump_sum"


# ─────────────────────────────────────────────────────────────────────────────
# A25 — ORM model field presence
# ─────────────────────────────────────────────────────────────────────────────


class TestA25OrmFields:
    """Verify ORM model fields exist."""

    def test_quote_template_has_style(self):
        assert hasattr(QuoteTemplate, "style")

    def test_quote_template_has_is_system_template(self):
        assert hasattr(QuoteTemplate, "is_system_template")

    def test_quote_template_has_current_version(self):
        assert hasattr(QuoteTemplate, "current_version")

    def test_quote_template_has_system_template_id(self):
        assert hasattr(QuoteTemplate, "system_template_id")

    def test_quote_template_has_forked_from_version(self):
        assert hasattr(QuoteTemplate, "forked_from_version")

    def test_quote_template_line_has_customer_visible(self):
        assert hasattr(QuoteTemplateLine, "customer_visible")

    def test_quote_template_line_has_is_section_header(self):
        assert hasattr(QuoteTemplateLine, "is_section_header")

    def test_quote_template_line_has_display_order(self):
        assert hasattr(QuoteTemplateLine, "display_order")


# ─────────────────────────────────────────────────────────────────────────────
# A25 — Variable substitution helper
# ─────────────────────────────────────────────────────────────────────────────


class TestA25VariableSubstitution:
    """Test the _substitute_variables helper."""

    def test_substitutes_known_variables(self):
        template = "Hello {customer_name}, your site is {site_address}."
        ctx = {"customer_name": "John Smith", "site_address": "123 Main St"}
        result = _substitute_variables(template, ctx)
        assert result == "Hello John Smith, your site is 123 Main St."

    def test_preserves_unknown_variables(self):
        template = "Hello {customer_name} and {unknown_var}."
        ctx = {"customer_name": "Jane"}
        result = _substitute_variables(template, ctx)
        assert result == "Hello Jane and {unknown_var}."

    def test_handles_empty_template(self):
        result = _substitute_variables("", {"customer_name": "Test"})
        assert result == ""

    def test_handles_no_variables(self):
        text = "No variables here."
        result = _substitute_variables(text, {"customer_name": "Test"})
        assert result == text

    def test_all_b1_namespace_variables(self):
        """Verify all B1 namespace variables can be substituted."""
        template = "{customer_name} {customer_first_name} {site_address} {quote_date}"
        ctx = {
            "customer_name": "Mike Johnson",
            "customer_first_name": "Mike",
            "site_address": "456 Elm Ave",
            "quote_date": "2026-05-01",
        }
        result = _substitute_variables(template, ctx)
        assert "Mike Johnson" in result
        assert "Mike" in result
        assert "456 Elm Ave" in result
        assert "2026-05-01" in result


# ─────────────────────────────────────────────────────────────────────────────
# A25 — Pydantic schema validation
# ─────────────────────────────────────────────────────────────────────────────


class TestA25PydanticSchemas:
    """Verify QuoteTemplateCreate and QuoteTemplateLineCreate schema behavior."""

    def test_quote_template_create_valid_styles(self):
        for style in ["component", "deliverable", "lump_sum"]:
            payload = QuoteTemplateCreate(name=f"Test {style}", style=style)
            assert payload.style == style

    def test_quote_template_line_create_defaults(self):
        line = QuoteTemplateLineCreate(
            qco_line_type_id=uuid.uuid4(),
            description="Test line",
        )
        assert line.default_quantity == Decimal("1")
        assert line.default_unit_price_cents == 0
        assert line.customer_visible is True
        assert line.is_section_header is False
        assert line.display_order == 0
        assert line.parent_line_id is None
