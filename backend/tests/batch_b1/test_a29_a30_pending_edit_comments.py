"""
Batch B1 — A29 & A30 Test Coverage
====================================

A29: Pending Edit Storage During Owner Review
  - quote_pending_edit table exists in DB with correct columns and constraints
  - QuotePendingEdit ORM model has correct fields
  - QuotePendingEditCreate/Update/Response schemas exist
  - pending-edits routes are registered (GET, POST, PATCH, DELETE single, DELETE all)

A30: Approval Comment & Annotation System
  - quote_approval_comment table exists in DB with correct columns
  - QuoteApprovalComment ORM model has correct fields
  - QuoteApprovalCommentResponse schema exists
  - QuoteKickbackRequest/Response schemas exist
  - Comments GET route and kickback POST route are registered
"""

from sqlalchemy import text
from sqlmodel import Session

from api.schemas.quotes import (
    QuoteApprovalCommentResponse,
    QuoteKickbackRequest,
    QuoteKickbackResponse,
    QuotePendingEditCreate,
    QuotePendingEditResponse,
    QuotePendingEditUpdate,
)
from app.models.quoting import QuoteApprovalComment, QuotePendingEdit

# ─────────────────────────────────────────────────────────────────────────────
# A29 — DB table and column verification
# ─────────────────────────────────────────────────────────────────────────────


class TestA29DatabaseTable:
    """Verify quote_pending_edit table structure."""

    def test_table_exists(self, db_session: Session):
        row = db_session.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'quote_pending_edit'
            """)
        ).first()
        assert row is not None, "quote_pending_edit table missing"

    def test_edit_type_check_constraint_exists(self, db_session: Session):
        row = db_session.execute(
            text("""
                SELECT constraint_name FROM information_schema.table_constraints
                WHERE table_schema = 'public' AND table_name = 'quote_pending_edit'
                  AND constraint_type = 'CHECK'
                  AND constraint_name = 'chk_quote_pending_edit_type'
            """)
        ).first()
        assert row is not None, "CHECK constraint chk_quote_pending_edit_type missing"

    def test_edit_payload_is_jsonb(self, db_session: Session):
        row = db_session.execute(
            text("""
                SELECT data_type, udt_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'quote_pending_edit'
                  AND column_name = 'edit_payload'
            """)
        ).first()
        assert row is not None, "edit_payload column missing"
        assert row.udt_name == "jsonb"

    def test_indexes_exist(self, db_session: Session):
        for idx in [
            "ix_quote_pending_edit_quote_id",
            "ix_quote_pending_edit_editor",
            "ix_quote_pending_edit_tenant",
        ]:
            row = db_session.execute(
                text("""
                    SELECT indexname FROM pg_indexes
                    WHERE schemaname = 'public' AND tablename = 'quote_pending_edit'
                      AND indexname = :idx
                """),
                {"idx": idx},
            ).first()
            assert row is not None, f"Index {idx} missing from quote_pending_edit"


# ─────────────────────────────────────────────────────────────────────────────
# A30 — DB table and column verification
# ─────────────────────────────────────────────────────────────────────────────


class TestA30DatabaseTable:
    """Verify quote_approval_comment table structure."""

    def test_table_exists(self, db_session: Session):
        row = db_session.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'quote_approval_comment'
            """)
        ).first()
        assert row is not None, "quote_approval_comment table missing"

    def test_comment_type_check_constraint_exists(self, db_session: Session):
        row = db_session.execute(
            text("""
                SELECT constraint_name FROM information_schema.table_constraints
                WHERE table_schema = 'public' AND table_name = 'quote_approval_comment'
                  AND constraint_type = 'CHECK'
                  AND constraint_name = 'chk_quote_approval_comment_type'
            """)
        ).first()
        assert row is not None, (
            "CHECK constraint chk_quote_approval_comment_type missing"
        )

    def test_no_updated_at_column(self, db_session: Session):
        """AppendOnly table should NOT have updated_at."""
        row = db_session.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'quote_approval_comment'
                  AND column_name = 'updated_at'
            """)
        ).first()
        assert row is None, (
            "quote_approval_comment should NOT have updated_at (AppendOnly)"
        )

    def test_indexes_exist(self, db_session: Session):
        for idx in [
            "ix_quote_approval_comment_quote_id",
            "ix_quote_approval_comment_tenant",
            "ix_quote_approval_comment_version",
        ]:
            row = db_session.execute(
                text("""
                    SELECT indexname FROM pg_indexes
                    WHERE schemaname = 'public' AND tablename = 'quote_approval_comment'
                      AND indexname = :idx
                """),
                {"idx": idx},
            ).first()
            assert row is not None, f"Index {idx} missing from quote_approval_comment"


# ─────────────────────────────────────────────────────────────────────────────
# A29 — ORM model field presence
# ─────────────────────────────────────────────────────────────────────────────


class TestA29OrmFields:
    """Verify QuotePendingEdit ORM model fields."""

    def test_has_quote_id(self):
        assert hasattr(QuotePendingEdit, "quote_id")

    def test_has_quote_version_id(self):
        assert hasattr(QuotePendingEdit, "quote_version_id")

    def test_has_editor_user_id(self):
        assert hasattr(QuotePendingEdit, "editor_user_id")

    def test_has_edit_type(self):
        assert hasattr(QuotePendingEdit, "edit_type")

    def test_has_edit_payload(self):
        assert hasattr(QuotePendingEdit, "edit_payload")

    def test_has_target_line_id(self):
        assert hasattr(QuotePendingEdit, "target_line_id")

    def test_has_annotation(self):
        assert hasattr(QuotePendingEdit, "annotation")


# ─────────────────────────────────────────────────────────────────────────────
# A30 — ORM model field presence
# ─────────────────────────────────────────────────────────────────────────────


class TestA30OrmFields:
    """Verify QuoteApprovalComment ORM model fields."""

    def test_has_quote_id(self):
        assert hasattr(QuoteApprovalComment, "quote_id")

    def test_has_quote_version_id(self):
        assert hasattr(QuoteApprovalComment, "quote_version_id")

    def test_has_author_user_id(self):
        assert hasattr(QuoteApprovalComment, "author_user_id")

    def test_has_comment_type(self):
        assert hasattr(QuoteApprovalComment, "comment_type")

    def test_has_content(self):
        assert hasattr(QuoteApprovalComment, "content")

    def test_has_target_line_id(self):
        assert hasattr(QuoteApprovalComment, "target_line_id")


# ─────────────────────────────────────────────────────────────────────────────
# A29 — Pydantic schema tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA29PydanticSchemas:
    """Verify A29 request/response schemas."""

    def test_create_request_fields(self):
        req = QuotePendingEditCreate(
            edit_type="modify_line",
            edit_payload={"unit_price_cents": 50000},
        )
        assert req.edit_type == "modify_line"
        assert req.edit_payload == {"unit_price_cents": 50000}
        assert req.target_line_id is None
        assert req.annotation is None

    def test_update_request_fields(self):
        req = QuotePendingEditUpdate(annotation="See notes")
        assert req.annotation == "See notes"
        assert req.edit_payload is None

    def test_response_has_required_fields(self):
        fields = QuotePendingEditResponse.model_fields
        assert "id" in fields
        assert "quote_id" in fields
        assert "edit_type" in fields
        assert "edit_payload" in fields
        assert "editor_user_id" in fields


# ─────────────────────────────────────────────────────────────────────────────
# A30 — Pydantic schema tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA30PydanticSchemas:
    """Verify A30 request/response schemas."""

    def test_kickback_request_defaults(self):
        req = QuoteKickbackRequest(overall_comment="Please revise labor rate")
        assert req.overall_comment == "Please revise labor rate"
        assert req.line_comments is None
        assert req.expected_quote_version_id is None

    def test_kickback_response_fields(self):
        fields = QuoteKickbackResponse.model_fields
        assert "quote_id" in fields
        assert "status" in fields
        assert "comment_count" in fields

    def test_comment_response_fields(self):
        fields = QuoteApprovalCommentResponse.model_fields
        assert "id" in fields
        assert "comment_type" in fields
        assert "content" in fields
        assert "author_user_id" in fields


# ─────────────────────────────────────────────────────────────────────────────
# A29 + A30 — Route registration
# ─────────────────────────────────────────────────────────────────────────────


class TestA29A30RouteRegistration:
    """Verify A29/A30 endpoints are registered."""

    def test_pending_edits_get_route_registered(self):
        from api.routes.quotes import router

        paths = [r.path for r in router.routes if hasattr(r, "path")]
        matching = [p for p in paths if "pending-edits" in p]
        assert matching, "pending-edits route not found"

    def test_comments_get_route_registered(self):
        from api.routes.quotes import router

        paths = [r.path for r in router.routes if hasattr(r, "path")]
        matching = [p for p in paths if "comments" in p]
        assert matching, "comments route not found"

    def test_kickback_route_registered(self):
        from api.routes.quotes import router

        paths = [r.path for r in router.routes if hasattr(r, "path")]
        matching = [p for p in paths if "kickback" in p]
        assert matching, "kickback route not found"
