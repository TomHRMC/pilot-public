"""
Test Suite: Phase 4.6 Task 10 - Quote Acceptance VARCHAR Alignment
Tests removal of arbitrary VARCHAR limits on quote_acceptance table
"""

from sqlalchemy import text
from sqlmodel import Session, select

from app.models.quoting import QuoteAcceptance


class TestQuoteAcceptanceColumnTypes:
    """Test quote_acceptance column types match JSON schema"""

    def test_accepted_by_email_is_citext(self, db_session: Session):
        """Verify accepted_by_email uses citext (case-insensitive)"""
        result = db_session.execute(
            text("""
            SELECT udt_name
            FROM information_schema.columns
            WHERE table_name = 'quote_acceptance'
              AND column_name = 'accepted_by_email'
        """)
        )
        assert result.scalar() == "citext"

    def test_accepted_by_name_is_text(self, db_session: Session):
        """Verify accepted_by_name uses unlimited text"""
        result = db_session.execute(
            text("""
            SELECT data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'quote_acceptance'
              AND column_name = 'accepted_by_name'
        """)
        )
        row = result.fetchone()
        assert row[0] == "text"
        assert row[1] is None  # No length limit

    def test_acceptance_notes_is_text(self, db_session: Session):
        """Verify acceptance_notes uses unlimited text"""
        result = db_session.execute(
            text("""
            SELECT data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'quote_acceptance'
              AND column_name = 'acceptance_notes'
        """)
        )
        row = result.fetchone()
        assert row[0] == "text"
        assert row[1] is None  # No length limit


class TestQuoteAcceptanceVarcharLimitsRemoved:
    """Test that VARCHAR limits have been removed"""

    def test_long_email_accepted(
        self, db_session: Session, test_tenant, test_quote_version
    ):
        """Email longer than 255 characters should be accepted"""
        long_email = "a" * 250 + "@example.com"  # 262 chars
        acceptance = QuoteAcceptance(
            tenant_id=test_tenant.id,
            quote_version_id=test_quote_version.id,
            accepted_by_email=long_email,
            accepted_by_name="Test User",
        )
        db_session.add(acceptance)
        db_session.commit()

        result = db_session.exec(
            select(QuoteAcceptance).where(QuoteAcceptance.id == acceptance.id)
        ).first()
        assert result.accepted_by_email == long_email.lower()  # citext stores lowercase
        assert len(result.accepted_by_email) > 255

    def test_long_name_accepted(
        self, db_session: Session, test_tenant, test_quote_version
    ):
        """Name longer than 255 characters should be accepted"""
        long_name = "A" * 300  # 300 chars
        acceptance = QuoteAcceptance(
            tenant_id=test_tenant.id,
            quote_version_id=test_quote_version.id,
            accepted_by_email="test@example.com",
            accepted_by_name=long_name,
        )
        db_session.add(acceptance)
        db_session.commit()

        result = db_session.exec(
            select(QuoteAcceptance).where(QuoteAcceptance.id == acceptance.id)
        ).first()
        assert result.accepted_by_name == long_name
        assert len(result.accepted_by_name) > 255

    def test_long_notes_accepted(
        self, db_session: Session, test_tenant, test_quote_version
    ):
        """Notes longer than 1000 characters should be accepted"""
        long_notes = "N" * 1500  # 1500 chars
        acceptance = QuoteAcceptance(
            tenant_id=test_tenant.id,
            quote_version_id=test_quote_version.id,
            accepted_by_email="test@example.com",
            accepted_by_name="Test User",
            acceptance_notes=long_notes,
        )
        db_session.add(acceptance)
        db_session.commit()

        result = db_session.exec(
            select(QuoteAcceptance).where(QuoteAcceptance.id == acceptance.id)
        ).first()
        assert result.acceptance_notes == long_notes
        assert len(result.acceptance_notes) > 1000
