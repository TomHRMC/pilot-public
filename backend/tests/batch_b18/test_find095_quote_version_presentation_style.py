"""
FIND-095 (S2 High) — quote_version.presentation_style column + API surface.

Deliverables:
  1. Migration: presentation_style TEXT NOT NULL DEFAULT 'clean'
     CHECK (presentation_style IN ('clean','line_itemed','hybrid'))
  2. QuoteVersionCreate: accepts presentation_style (default='clean')
  3. _create_quote_version_impl: passes presentation_style to QuoteVersion()
  4. QuoteVersionResponse: exposes presentation_style

Test coverage:
  1. DB schema: column exists, NOT NULL, correct default
  2. DB schema: CHECK constraint exists
  3. ORM model: field present with nullable=False
  4. Schema: QuoteVersionCreate validator rejects invalid values
  5. Schema: QuoteVersionResponse includes presentation_style
  6. Endpoint: POST /versions/test with presentation_style='line_itemed' → persisted
  7. Endpoint: POST /versions/test without presentation_style → defaults to 'clean'
  8. Endpoint: POST /versions/test with invalid value → 422

Test subfolder: tests/batch_b18/
"""

import uuid
from datetime import UTC, datetime

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_quote_fixture(db_session, test_tenant, test_user):
    """Create minimal Quote row for FK requirements."""
    from sqlmodel import select

    from app.models.crm import Customer, Site
    from app.models.quoting import Quote, QuoteStatus

    now = datetime.now(UTC)
    status = db_session.exec(select(QuoteStatus).limit(1)).first()
    assert status is not None, "No QuoteStatus seeded"

    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        type="person",
        display_name=f"Test Customer {uuid.uuid4().hex[:6]}",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)

    site = Site(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=customer.id,
        display_name="Test Site",
        created_at=now,
        updated_at=now,
    )
    db_session.add(site)

    quote = Quote(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=customer.id,
        site_id=site.id,
        status_id=status.id,
        currency="USD",
        subtotal_cents=0,
        tax_cents=0,
        total_cents=0,
        created_at=now,
        updated_at=now,
    )
    db_session.add(quote)
    db_session.flush()
    return quote


# ─────────────────────────────────────────────────────────────────────────────
# 1. DB schema
# ─────────────────────────────────────────────────────────────────────────────


class TestFind095DBSchema:
    def test_column_exists_and_is_not_nullable(self, db_session):
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_name, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'quote_version' "
                "  AND column_name = 'presentation_style'"
            )
        ).first()

        assert result is not None, "presentation_style missing from quote_version"
        assert result[1] == "NO", (
            f"presentation_style must be NOT NULL, got '{result[1]}'"
        )
        assert result[2] is not None, "presentation_style must have a server default"
        assert "clean" in str(result[2])

    def test_check_constraint_exists(self, db_session):
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT constraint_name "
                "FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'quote_version' "
                "  AND constraint_type = 'CHECK' "
                "  AND constraint_name = 'quote_version_presentation_style_chk'"
            )
        ).first()

        assert result is not None, (
            "quote_version_presentation_style_chk CHECK must exist"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. ORM model
# ─────────────────────────────────────────────────────────────────────────────


class TestFind095ORMModel:
    def test_presentation_style_field_exists(self):
        from app.models.quoting import QuoteVersion

        assert hasattr(QuoteVersion, "presentation_style")

    def test_presentation_style_is_not_nullable(self):
        from app.models.quoting import QuoteVersion

        col = QuoteVersion.__table__.c["presentation_style"]
        assert col.nullable is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. Schema validation
# ─────────────────────────────────────────────────────────────────────────────


class TestFind095SchemaValidation:
    def test_invalid_presentation_style_raises_validation_error(self):
        from pydantic import ValidationError

        from api.schemas.quotes import QuoteVersionCreate

        with pytest.raises(ValidationError):
            QuoteVersionCreate(presentation_style="full_page")

    def test_valid_values_accepted(self):
        from api.schemas.quotes import QuoteVersionCreate

        for style in ("clean", "line_itemed", "hybrid"):
            obj = QuoteVersionCreate(presentation_style=style)
            assert obj.presentation_style == style

    def test_default_is_clean(self):
        from api.schemas.quotes import QuoteVersionCreate

        obj = QuoteVersionCreate()
        assert obj.presentation_style == "clean"

    def test_quote_version_response_has_presentation_style(self):
        """QuoteVersionResponse must expose presentation_style for frontend codegen."""
        import typing

        from api.schemas.quotes import QuoteVersionResponse

        hints = typing.get_type_hints(QuoteVersionResponse)
        assert "presentation_style" in hints, (
            "QuoteVersionResponse must include presentation_style field"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Endpoint integration
# ─────────────────────────────────────────────────────────────────────────────


class TestFind095EndpointIntegration:
    def test_post_with_presentation_style_persists_value(
        self, client, db_session, test_tenant
    ):
        """POST /quotes/{id}/versions/test with presentation_style='line_itemed' → persisted."""
        from sqlmodel import select

        from app.models.quoting import QuoteVersion

        quote = _make_quote_fixture(db_session, test_tenant, None)
        db_session.commit()

        resp = client.post(
            f"/api/v1/quotes/{quote.id}/versions/test",
            json={"presentation_style": "line_itemed"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["presentation_style"] == "line_itemed"

        # Integration: verify DB column
        fetched = db_session.exec(
            select(QuoteVersion).where(QuoteVersion.id == data["id"])
        ).first()
        assert fetched is not None
        assert fetched.presentation_style == "line_itemed"

    def test_post_without_presentation_style_defaults_to_clean(
        self, client, db_session, test_tenant
    ):
        """POST without body → defaults to 'clean'."""
        quote = _make_quote_fixture(db_session, test_tenant, None)
        db_session.commit()

        resp = client.post(f"/api/v1/quotes/{quote.id}/versions/test")
        assert resp.status_code == 201, resp.text
        assert resp.json()["presentation_style"] == "clean"

    def test_post_with_invalid_presentation_style_returns_422(
        self, client, db_session, test_tenant
    ):
        """POST with invalid presentation_style → 422 Validation Error."""
        quote = _make_quote_fixture(db_session, test_tenant, None)
        db_session.commit()

        resp = client.post(
            f"/api/v1/quotes/{quote.id}/versions/test",
            json={"presentation_style": "full_page"},
        )
        assert resp.status_code == 422, (
            f"Invalid presentation_style must return 422, got {resp.status_code}"
        )
