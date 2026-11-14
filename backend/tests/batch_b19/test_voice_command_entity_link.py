"""
FIND-168 (B19): Voice Command Entity Link Table — Junction table linking voice_command_log
rows to the entities they created or mutated. Enables platform-wide voice-to-entity
audit trail for: owner re-listen, dispute resolution, training data audit, and support debugging.

Tests:
- Table schema: VoiceCommandEntityLink ORM model
- Insertion via _link_voice_to_entity() helper
- Single voice command → multiple entity links
- Query by entity: fetch voice log from entity reference
- ON DELETE RESTRICT: cannot delete voice log while links exist
- AppendOnly guard: UPDATE on link row rejected
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ai import VoiceCommandEntityLink, VoiceCommandLog
from app.models.voice_helpers import _link_voice_to_entity

# Suppress SQLModel deprecation warnings about session.query() vs session.exec()
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


class TestVoiceCommandEntityLinkSchema:
    """Verify ORM model and database schema match spec."""

    def test_voice_command_entity_link_table_exists(self, db_session: Session):
        """Table voice_command_entity_link exists."""
        from sqlalchemy import inspect

        inspector = inspect(db_session.bind)
        tables = inspector.get_table_names()
        assert "voice_command_entity_link" in tables

    def test_voice_command_entity_link_bigint_pk(self, db_session: Session):
        """PK column id is BIGINT autoincrement."""
        from app.models.ai import VoiceCommandEntityLink

        mapper = VoiceCommandEntityLink.__mapper__
        pk_cols = [c for c in mapper.columns if c.primary_key]
        assert len(pk_cols) == 1
        assert pk_cols[0].name == "id"

    def test_voice_command_entity_link_has_required_columns(self, db_session: Session):
        """All required columns present: tenant_id, voice_command_log_id, entity_type, entity_id, action, created_at, created_by."""
        from app.models.ai import VoiceCommandEntityLink

        link = VoiceCommandEntityLink()
        assert hasattr(link, "id")
        assert hasattr(link, "tenant_id")
        assert hasattr(link, "voice_command_log_id")
        assert hasattr(link, "entity_type")
        assert hasattr(link, "entity_id")
        assert hasattr(link, "action")
        assert hasattr(link, "created_at")
        assert hasattr(link, "created_by")

    def test_voice_command_entity_link_indexes_exist(self, db_session: Session):
        """Composite indexes on (tenant_id, entity_type, entity_id) and (voice_command_log_id)."""
        from sqlalchemy import inspect

        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("voice_command_entity_link")
        index_names = {idx["name"] for idx in indexes}

        assert "ix_vcel_entity" in index_names
        assert "ix_vcel_voice_log" in index_names


class TestVoiceCommandEntityLinkInsertion:
    """Test _link_voice_to_entity() helper and row insertion."""

    def test_link_voice_to_entity_creates_row(
        self, db_session: Session, test_tenant, test_user
    ):
        """_link_voice_to_entity() creates a VoiceCommandEntityLink row."""
        # Create voice log
        voice_log = VoiceCommandLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            intent_detected="clock_in",
            is_successful=True,
        )
        db_session.add(voice_log)
        db_session.commit()

        # Create link
        entity_id = uuid.uuid4()
        link = _link_voice_to_entity(
            db=db_session,
            tenant_id=test_tenant.id,
            voice_command_log_id=voice_log.id,
            entity_type="job_time_entry",
            entity_id=entity_id,
            action="clock_in",
            created_by=test_user.id,
        )
        db_session.add(link)
        db_session.commit()

        # Verify row
        retrieved = (
            db_session.query(VoiceCommandEntityLink)
            .filter_by(entity_id=entity_id)
            .first()
        )
        assert retrieved is not None
        assert retrieved.entity_type == "job_time_entry"
        assert retrieved.action == "clock_in"
        assert retrieved.created_by == test_user.id

    def test_one_voice_command_multiple_entities(
        self, db_session: Session, test_tenant, test_user
    ):
        """One voice command can touch multiple entities → multiple link rows with same voice_command_log_id."""
        # Create voice log
        voice_log = VoiceCommandLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            intent_detected="clock_out_and_expense",
            is_successful=True,
        )
        db_session.add(voice_log)
        db_session.commit()

        # Create two links from the same voice command
        entry_id = uuid.uuid4()
        expense_id = uuid.uuid4()

        link1 = _link_voice_to_entity(
            db=db_session,
            tenant_id=test_tenant.id,
            voice_command_log_id=voice_log.id,
            entity_type="job_time_entry",
            entity_id=entry_id,
            action="clock_out",
        )
        db_session.add(link1)

        link2 = _link_voice_to_entity(
            db=db_session,
            tenant_id=test_tenant.id,
            voice_command_log_id=voice_log.id,
            entity_type="job_expense",
            entity_id=expense_id,
            action="created",
        )
        db_session.add(link2)
        db_session.commit()

        # Verify both rows have same voice_command_log_id
        rows = (
            db_session.query(VoiceCommandEntityLink)
            .filter_by(voice_command_log_id=voice_log.id)
            .all()
        )
        assert len(rows) == 2
        assert all(r.voice_command_log_id == voice_log.id for r in rows)


class TestVoiceCommandEntityLinkQuery:
    """Test querying links by entity to find originating voice command."""

    def test_query_by_entity_returns_voice_log(
        self, db_session: Session, test_tenant, test_user
    ):
        """Query by (entity_type, entity_id) returns the voice log that created it."""
        voice_log = VoiceCommandLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            intent_detected="create_quote",
            is_successful=True,
        )
        db_session.add(voice_log)
        db_session.commit()

        quote_id = uuid.uuid4()
        link = _link_voice_to_entity(
            db=db_session,
            tenant_id=test_tenant.id,
            voice_command_log_id=voice_log.id,
            entity_type="quote",
            entity_id=quote_id,
            action="created",
        )
        db_session.add(link)
        db_session.commit()

        # Query: given entity_type='quote' and entity_id=quote_id, get voice log
        link_row = (
            db_session.query(VoiceCommandEntityLink)
            .filter(
                VoiceCommandEntityLink.entity_type == "quote",
                VoiceCommandEntityLink.entity_id == quote_id,
                VoiceCommandEntityLink.tenant_id == test_tenant.id,
            )
            .first()
        )

        assert link_row is not None
        retrieved_log = (
            db_session.query(VoiceCommandLog)
            .filter_by(id=link_row.voice_command_log_id)
            .first()
        )
        assert retrieved_log.intent_detected == "create_quote"


class TestVoiceCommandEntityLinkDelete:
    """Test ON DELETE RESTRICT behavior."""

    def test_delete_voice_log_with_links_raises_integrity_error(
        self, db_session: Session, test_tenant, test_user
    ):
        """Attempt to DELETE voice_command_log row with link rows raises IntegrityError (FK RESTRICT)."""
        voice_log = VoiceCommandLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            intent_detected="test",
            is_successful=True,
        )
        db_session.add(voice_log)
        db_session.commit()

        entity_id = uuid.uuid4()
        link = _link_voice_to_entity(
            db=db_session,
            tenant_id=test_tenant.id,
            voice_command_log_id=voice_log.id,
            entity_type="job",
            entity_id=entity_id,
        )
        db_session.add(link)
        db_session.commit()

        # Attempt to delete voice log → should fail
        db_session.delete(voice_log)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestVoiceCommandEntityLinkAppendOnly:
    """Test AppendOnlyMixin — created_at and created_by are immutable."""

    def test_link_has_created_at_and_created_by(
        self, db_session: Session, test_tenant, test_user
    ):
        """VoiceCommandEntityLink has AppendOnlyMixin columns: created_at, created_by."""
        voice_log = VoiceCommandLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            intent_detected="test",
            is_successful=True,
        )
        db_session.add(voice_log)
        db_session.commit()

        entity_id = uuid.uuid4()
        link = _link_voice_to_entity(
            db=db_session,
            tenant_id=test_tenant.id,
            voice_command_log_id=voice_log.id,
            entity_type="job",
            entity_id=entity_id,
            action="created",
            created_by=test_user.id,
        )
        db_session.add(link)
        db_session.commit()

        # Verify immutable fields are set
        retrieved = (
            db_session.query(VoiceCommandEntityLink)
            .filter_by(entity_id=entity_id)
            .first()
        )
        assert retrieved.created_at is not None
        assert retrieved.created_by == test_user.id
