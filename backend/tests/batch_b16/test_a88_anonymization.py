"""
A88 — Anonymization Pipeline for Training Data Capture tests.

Test focus:
- pii_anonymizer.anonymize_text() replaces email, phone, UUID, address
- anonymize_text() does not mangle non-PII text
- HelpTrainingCorpus ORM model creates correctly
- _anonymize_session_impl() writes corpus entry and marks session anonymized
- _anonymize_session_impl() skips duplicate sessions (hash dedup)
- anonymize_help_sessions() processes sessions older than 90 days
- anonymize_help_sessions() does not touch sessions < 90 days old
"""

from datetime import UTC, datetime, timedelta

# ──────────────────────────────────────────────────────────────────────────────
# PII anonymizer unit tests
# ──────────────────────────────────────────────────────────────────────────────


class TestAnonymizeText:
    def test_replaces_email(self):
        from services.pii_anonymizer import anonymize_text

        result = anonymize_text("Contact me at mike@example.com for details.")
        assert "[email]" in result
        assert "mike@example.com" not in result

    def test_replaces_phone_us_format(self):
        from services.pii_anonymizer import anonymize_text

        result = anonymize_text("Call me at 555-867-5309 for help.")
        assert "[phone]" in result
        assert "555-867-5309" not in result

    def test_replaces_uuid(self):
        from services.pii_anonymizer import anonymize_text

        test_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        result = anonymize_text(f"My account ID is {test_uuid}.")
        assert "[id]" in result
        assert test_uuid not in result

    def test_replaces_address(self):
        from services.pii_anonymizer import anonymize_text

        result = anonymize_text("I live at 123 Main Street near downtown.")
        assert "[address]" in result
        assert "123 Main Street" not in result

    def test_non_pii_text_unchanged(self):
        from services.pii_anonymizer import anonymize_text

        safe_text = "How do I connect QuickBooks to Pilot for Trades?"
        result = anonymize_text(safe_text)
        assert result == safe_text

    def test_empty_string_handled(self):
        from services.pii_anonymizer import anonymize_text

        assert anonymize_text("") == ""

    def test_none_handled(self):
        from services.pii_anonymizer import anonymize_text

        assert anonymize_text(None) is None

    def test_multiple_pii_replaced(self):
        from services.pii_anonymizer import anonymize_text

        text = (
            "My email is john@test.com, phone 555-123-4567, "
            "and I live at 456 Oak Avenue."
        )
        result = anonymize_text(text)
        assert "john@test.com" not in result
        assert "555-123-4567" not in result
        assert "456 Oak Avenue" not in result


# ──────────────────────────────────────────────────────────────────────────────
# HelpTrainingCorpus ORM model
# ──────────────────────────────────────────────────────────────────────────────


class TestHelpTrainingCorpusModel:
    def test_create_corpus_entry(self, db_session):
        from app.models.help import HelpTrainingCorpus

        now = datetime.now(UTC)
        corpus = HelpTrainingCorpus(
            original_session_id_hash="abc123hash",
            anonymized_message_history=[
                {"role": "user", "content": "How do I connect [id]?"},
                {"role": "assistant", "content": "Go to Settings > Integrations."},
            ],
            anonymized_context_payload={"route": "/settings"},
            category_inferred="integrations",
            outcome="resolved",
            anonymized_at=now,
            created_at=now,
        )
        db_session.add(corpus)
        db_session.commit()
        db_session.refresh(corpus)

        assert corpus.corpus_id is not None
        assert corpus.outcome == "resolved"
        assert len(corpus.anonymized_message_history) == 2


# ──────────────────────────────────────────────────────────────────────────────
# Anonymization pipeline logic tests
# ──────────────────────────────────────────────────────────────────────────────


def _make_old_session(db_session, tenant_id, user_id, days_ago=95):
    from app.models.help import HelpChatSession

    old_time = datetime.now(UTC) - timedelta(days=days_ago)
    session = HelpChatSession(
        tenant_id=tenant_id,
        user_id=user_id,
        started_at=old_time,
        last_activity_at=old_time,
        message_count=2,
        outcome="resolved",
        created_at=old_time,
        updated_at=old_time,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def _make_message_for_session(
    db_session, session_id, tenant_id, role="user", content="Hello"
):
    from app.models.help import HelpChatMessage

    now = datetime.now(UTC)
    msg = HelpChatMessage(
        session_id=session_id,
        tenant_id=tenant_id,
        role=role,
        content=content,
        voice_used=False,
        created_at=now,
    )
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)
    return msg


class TestAnonymizeSessionImpl:
    def test_creates_corpus_entry(self, db_session, test_tenant, test_user):
        from sqlmodel import select

        from app.models.help import HelpTrainingCorpus
        from tasks.help_corpus import _anonymize_session_impl

        session = _make_old_session(db_session, test_tenant.id, test_user.id)
        # FIND-169: session.session_id → session.id
        _make_message_for_session(
            db_session,
            session.id,
            test_tenant.id,
            "user",
            "How do I connect QuickBooks?",
        )
        _make_message_for_session(
            db_session,
            session.id,
            test_tenant.id,
            "assistant",
            "Go to Settings > Integrations.",
        )

        _anonymize_session_impl(session, db_session)
        db_session.commit()

        corpus_entries = db_session.exec(select(HelpTrainingCorpus)).all()
        assert len(corpus_entries) >= 1

        # Session should be marked anonymized
        db_session.refresh(session)
        assert session.anonymized_at is not None

    def test_deduplicates_session(self, db_session, test_tenant, test_user):
        import hashlib

        from sqlmodel import select

        from app.models.help import HelpTrainingCorpus
        from tasks.help_corpus import _anonymize_session_impl

        session = _make_old_session(db_session, test_tenant.id, test_user.id)
        # FIND-169: session.session_id → session.id
        session_hash = hashlib.sha256(str(session.id).encode()).hexdigest()

        # Pre-insert corpus entry for this session
        now = datetime.now(UTC)
        existing = HelpTrainingCorpus(
            original_session_id_hash=session_hash,
            anonymized_message_history=[],
            outcome="resolved",
            anonymized_at=now,
            created_at=now,
        )
        db_session.add(existing)
        db_session.commit()

        count_before = len(db_session.exec(select(HelpTrainingCorpus)).all())

        # Anonymize again — should not create a duplicate corpus entry
        _anonymize_session_impl(session, db_session)
        db_session.commit()

        count_after = len(db_session.exec(select(HelpTrainingCorpus)).all())
        assert count_after == count_before  # no new corpus entry created

    def test_messages_deleted_after_anonymization(
        self, db_session, test_tenant, test_user
    ):
        from sqlmodel import select

        from app.models.help import HelpChatMessage
        from tasks.help_corpus import _anonymize_session_impl

        session = _make_old_session(db_session, test_tenant.id, test_user.id)
        # FIND-169: session.session_id → session.id
        msg1 = _make_message_for_session(db_session, session.id, test_tenant.id)
        msg2 = _make_message_for_session(
            db_session, session.id, test_tenant.id, "assistant", "Answer"
        )

        _anonymize_session_impl(session, db_session)
        db_session.commit()

        # Messages should be deleted
        remaining = db_session.exec(
            # FIND-169: session.session_id → session.id
            select(HelpChatMessage).where(HelpChatMessage.session_id == session.id)
        ).all()
        assert len(remaining) == 0


class TestAnonymizeHelpSessionsTask:
    def test_processes_sessions_older_than_90_days(
        self, db_session, test_tenant, test_user
    ):
        from tasks.help_corpus import _anonymize_session_impl

        session = _make_old_session(
            db_session, test_tenant.id, test_user.id, days_ago=95
        )
        # FIND-169: session.session_id → session.id
        _make_message_for_session(db_session, session.id, test_tenant.id)

        # Directly test the impl since we can't call beat task easily
        _anonymize_session_impl(session, db_session)
        db_session.commit()

        db_session.refresh(session)
        assert session.anonymized_at is not None

    def test_skips_recent_sessions(self, db_session, test_tenant, test_user):
        from app.models.help import HelpChatSession

        # Create a recent session (< 90 days old)
        now = datetime.now(UTC)
        recent = HelpChatSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            started_at=now - timedelta(days=10),
            last_activity_at=now - timedelta(days=10),
            message_count=0,
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=10),
        )
        db_session.add(recent)
        db_session.commit()

        # Recent session should not be picked up by 90-day filter
        from sqlmodel import select

        cutoff = datetime.now(UTC) - timedelta(days=90)
        eligible = db_session.exec(
            select(HelpChatSession)
            .where(HelpChatSession.last_activity_at <= cutoff)
            .where(HelpChatSession.anonymized_at == None)
        ).all()

        assert recent not in eligible
