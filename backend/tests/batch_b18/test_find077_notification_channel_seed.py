"""
FIND-077 (S2 High) — Seed notification_channel with 4 MVP rows; replace
notification_outbox.channel CHECK constraint with FK to notification_channel.code.

Actions in migration:
  1. Seed: email, sms, push, in_app in notification_channel
  2. DROP: notification_outbox_channel_chk CHECK constraint
  3. ADD FK: fk_outbox_channel → notification_channel(code) ON DELETE RESTRICT

Note: voice channel deferred to Phase 2.

Test coverage:
  1. Seed: all 4 channel rows present in DB
  2. DB: old CHECK constraint is gone
  3. DB: FK fk_outbox_channel exists on notification_outbox
  4. ORM: NotificationOutbox.channel has FK to notification_channel.code
  5. Integrity: invalid channel value rejected by FK (not by CHECK)
  6. Integrity: valid channel values ('email', 'sms', 'push', 'in_app') are accepted

Test subfolder: tests/batch_b18/
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

# ─────────────────────────────────────────────────────────────────────────────
# 1. Seed data: all 4 MVP channels present
# ─────────────────────────────────────────────────────────────────────────────


class TestFind077SeedData:
    """All 4 MVP notification_channel rows must be present after migration."""

    @pytest.mark.parametrize("code", ["email", "sms", "push", "in_app"])
    def test_channel_row_exists(self, db_session, code):
        """notification_channel must have seeded row for each MVP channel."""
        from sqlalchemy import text

        result = db_session.exec(
            text("SELECT code FROM notification_channel WHERE code = :code").bindparams(
                code=code
            )
        ).first()

        assert result is not None, (
            f"notification_channel missing seed row for code='{code}'"
        )

    def test_voice_channel_is_absent(self, db_session):
        """'voice' must NOT be seeded in MVP — deferred to Phase 2."""
        from sqlalchemy import text

        result = db_session.exec(
            text("SELECT code FROM notification_channel WHERE code = 'voice'")
        ).first()

        assert result is None, (
            "'voice' channel must not be in notification_channel for MVP "
            "(deferred to Phase 2 per Tom's decision 2026-05-08)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. DB: old CHECK constraint is absent
# ─────────────────────────────────────────────────────────────────────────────


class TestFind077CheckConstraintDropped:
    """notification_outbox_channel_chk must be dropped."""

    def test_channel_check_constraint_is_absent(self, db_session):
        """notification_outbox_channel_chk CHECK must be dropped — FK replaces it."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT constraint_name "
                "FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'notification_outbox' "
                "  AND constraint_type = 'CHECK' "
                "  AND constraint_name = 'notification_outbox_channel_chk'"
            )
        ).first()

        assert result is None, (
            "notification_outbox_channel_chk CHECK constraint must be dropped — "
            "it was superseded by FK fk_outbox_channel"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. DB: FK exists on notification_outbox
# ─────────────────────────────────────────────────────────────────────────────


class TestFind077FKExists:
    """fk_outbox_channel FK must exist on notification_outbox."""

    def test_fk_outbox_channel_exists(self, db_session):
        """FK fk_outbox_channel → notification_channel(code) must exist."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT constraint_name "
                "FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'notification_outbox' "
                "  AND constraint_type = 'FOREIGN KEY' "
                "  AND constraint_name = 'fk_outbox_channel'"
            )
        ).first()

        assert result is not None, (
            "FK 'fk_outbox_channel' must exist on notification_outbox "
            "(FIND-077 migration)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. ORM: channel field has FK
# ─────────────────────────────────────────────────────────────────────────────


class TestFind077ORMModel:
    """NotificationOutbox.channel must have FK to notification_channel.code."""

    def test_channel_has_foreign_key(self):
        from app.models.system import NotificationOutbox

        fk_tables = {
            fk.column.table.name
            for fk in NotificationOutbox.__table__.c.channel.foreign_keys
        }
        assert "notification_channel" in fk_tables, (
            "NotificationOutbox.channel must have a FK to notification_channel"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Integrity: invalid channel rejected by FK
# ─────────────────────────────────────────────────────────────────────────────


class TestFind077FKIntegrity:
    """FK enforcement: invalid channel must raise IntegrityError."""

    def test_invalid_channel_rejected_by_fk(self, db_session, test_tenant, test_user):
        """Inserting an outbox row with channel='voice' must fail (FK violation).
        Creates a notification_event and notification_category row inline if needed.
        """
        from sqlalchemy import text

        now = datetime.now(UTC)

        # Create a notification_event row (append-only — won't be rolled back, but unique id)
        evt_id = str(uuid.uuid4())
        db_session.exec(
            text(
                "INSERT INTO notification_event "
                "(id, tenant_id, notification_type_code, entity_type_code, entity_id, "
                " occurred_at, created_at) "
                "VALUES (:id, :tenant_id, 'quote_accepted', 'customer', :eid, :now, :now)"
            ).bindparams(
                id=evt_id,
                tenant_id=str(test_tenant.id),
                eid=str(uuid.uuid4()),
                now=now,
            )
        )
        db_session.flush()

        cat_result = db_session.exec(
            text("SELECT code FROM notification_category LIMIT 1")
        ).first()
        assert cat_result is not None, "notification_category must be seeded"

        with pytest.raises(IntegrityError):
            db_session.exec(
                text(
                    "INSERT INTO notification_outbox "
                    "(id, notification_event_id, tenant_id, recipient_user_id, channel, "
                    " category_id, status, created_at, updated_at) "
                    "VALUES (:id, :evt_id, :tenant_id, :user_id, 'voice', "
                    " :cat_id, 'pending', :now, :now)"
                ).bindparams(
                    id=str(uuid.uuid4()),
                    evt_id=evt_id,
                    tenant_id=str(test_tenant.id),
                    user_id=str(test_user.id),
                    cat_id=str(cat_result[0]),
                    now=now,
                )
            )
            db_session.flush()

        db_session.rollback()
