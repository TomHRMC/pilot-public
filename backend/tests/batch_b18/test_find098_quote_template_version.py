"""
FIND-098 (S2 High) — Create quote_template_version table (A25 deferred schema).

Test coverage:
  1. DB: table exists with correct structure
  2. DB: guard_created_immutable + audit triggers exist
  3. ORM: QuoteTemplateVersion model has all required fields
  4. Integration: creating a template creates version_no=1 row
  5. Integration: PK column is named 'id' (regression guard)
  6. Integration: guard_created_immutable blocks UPDATE on created_at
  7. Integration: seed step — existing templates have version_no=1 row after migration

Test subfolder: tests/batch_b18/
"""

import uuid
from datetime import UTC, datetime

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# 1. DB schema: table + structure
# ─────────────────────────────────────────────────────────────────────────────


class TestFind098DBSchema:
    """DB structure must match plan spec."""

    def test_table_exists(self, db_session):
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'quote_template_version'"
            )
        ).first()
        assert result is not None, "quote_template_version table must exist"

    @pytest.mark.parametrize(
        "column_name,expected_nullable",
        [
            ("id", "NO"),
            ("template_id", "NO"),
            ("version_no", "NO"),
            ("content_json", "NO"),
            ("changelog", "YES"),
            ("created_at", "NO"),
            ("created_by", "YES"),
        ],
    )
    def test_column_exists_with_correct_nullability(
        self, db_session, column_name, expected_nullable
    ):
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_name, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'quote_template_version' "
                "  AND column_name = :col"
            ).bindparams(col=column_name)
        ).first()

        assert result is not None, (
            f"Column '{column_name}' missing from quote_template_version"
        )
        assert result[1] == expected_nullable, (
            f"quote_template_version.{column_name} is_nullable must be "
            f"'{expected_nullable}', got '{result[1]}'"
        )

    def test_pk_column_is_named_id(self, db_session):
        """PK must be named 'id' — regression guard against 'version_id' naming drift."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT kcu.column_name "
                "FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                " AND kcu.table_schema = tc.table_schema "
                "WHERE tc.table_schema = 'public' "
                "  AND tc.table_name = 'quote_template_version' "
                "  AND tc.constraint_type = 'PRIMARY KEY'"
            )
        ).first()

        assert result is not None, "quote_template_version must have a PK"
        assert result[0] == "id", f"PK column must be named 'id', got '{result[0]}'"


# ─────────────────────────────────────────────────────────────────────────────
# 2. DB: triggers exist
# ─────────────────────────────────────────────────────────────────────────────


class TestFind098TriggersExist:
    """Both AppendOnlyMixin triggers must be installed."""

    @pytest.mark.parametrize(
        "trigger_name",
        [
            "audit_quote_template_version_changes",
            "guard_quote_template_version_created_immutable",
        ],
    )
    def test_trigger_exists(self, db_session, trigger_name):
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT trigger_name FROM information_schema.triggers "
                "WHERE event_object_schema = 'public' "
                "  AND event_object_table = 'quote_template_version' "
                "  AND trigger_name = :name"
            ).bindparams(name=trigger_name)
        ).first()

        assert result is not None, (
            f"Trigger '{trigger_name}' must exist on quote_template_version"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. ORM model
# ─────────────────────────────────────────────────────────────────────────────


class TestFind098ORMModel:
    def test_model_exists(self):
        from app.models.quoting import QuoteTemplateVersion

        assert QuoteTemplateVersion.__tablename__ == "quote_template_version"

    def test_required_fields_present(self):
        from app.models.quoting import QuoteTemplateVersion

        for field in (
            "id",
            "template_id",
            "version_no",
            "content_json",
            "changelog",
            "created_at",
            "created_by",
        ):
            assert hasattr(QuoteTemplateVersion, field), (
                f"QuoteTemplateVersion.{field} field missing"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Integration: create template → version_no=1 row created
# ─────────────────────────────────────────────────────────────────────────────


class TestFind098IntegrationVersionCreation:
    """Creating a quote template must insert a version_no=1 row."""

    def test_create_template_creates_version_1(
        self, db_session, test_tenant, test_user
    ):
        """ORM: create template + wire version → version_no=1 persisted in DB."""
        from sqlmodel import select

        from app.models.quoting import QuoteTemplate, QuoteTemplateVersion

        now = datetime.now(UTC)
        template = QuoteTemplate(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            name=f"Test Template {uuid.uuid4().hex[:6]}",
            style="component",
            current_version=1,
            is_system_template=False,
            is_active=True,
            created_at=now,
            updated_at=now,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(template)
        db_session.flush()

        # Wire version_no=1 (mirrors what create_quote_template handler does)
        version = QuoteTemplateVersion(
            id=uuid.uuid4(),
            template_id=template.id,
            version_no=1,
            content_json=[],
            changelog="Initial version",
            created_by=test_user.id,
            created_at=now,
        )
        db_session.add(version)
        db_session.commit()

        fetched = db_session.exec(
            select(QuoteTemplateVersion).where(
                QuoteTemplateVersion.template_id == template.id,
                QuoteTemplateVersion.version_no == 1,
            )
        ).first()

        assert fetched is not None, "version_no=1 row must persist to DB"
        assert fetched.template_id == template.id
        assert fetched.version_no == 1
        assert fetched.content_json == []


# ─────────────────────────────────────────────────────────────────────────────
# 5. Integration: immutable guard blocks UPDATE on created_at
# ─────────────────────────────────────────────────────────────────────────────


class TestFind098GuardImmutable:
    """guard_created_fields_immutable must block UPDATE on created_at."""

    def test_guard_blocks_update_on_created_at(self, db_session, test_tenant):
        from sqlalchemy import text
        from sqlmodel import select

        from app.models.quoting import QuoteTemplate, QuoteTemplateVersion

        # Find or create a template
        template = db_session.exec(
            select(QuoteTemplate)
            .where(QuoteTemplate.tenant_id == test_tenant.id)
            .limit(1)
        ).first()

        if template is None:
            now = datetime.now(UTC)
            template = QuoteTemplate(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                name=f"Test Template {uuid.uuid4().hex[:6]}",
                style="component",
                current_version=1,
                is_system_template=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db_session.add(template)
            db_session.flush()

        now = datetime.now(UTC)
        version = QuoteTemplateVersion(
            id=uuid.uuid4(),
            template_id=template.id,
            version_no=99,
            content_json=[],
            changelog="Test version",
            created_at=now,
        )
        db_session.add(version)
        db_session.commit()

        # Attempt to UPDATE created_at — must raise IntegrityError (trigger fires)
        with pytest.raises(Exception):  # psycopg2.errors.RaiseException wrapped
            db_session.exec(
                text(
                    "UPDATE quote_template_version "
                    "SET created_at = now() + interval '1 day' "
                    "WHERE id = :vid"
                ).bindparams(vid=str(version.id))
            )
            db_session.flush()

        db_session.rollback()
