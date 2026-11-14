"""phase_fe_1_batch_b2_voice_feedback_table

Revision ID: dc5b82049f97
Revises: c3192a4c4a31
Create Date: 2026-05-01 13:08:46.638909+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dc5b82049f97"
down_revision: str | None = "c3192a4c4a31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create voice_feedback table for AI training data capture
    op.create_table(
        "voice_feedback",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("voice_command_log_id", sa.BigInteger(), nullable=True),
        sa.Column("original_transcription", sa.Text(), nullable=False),
        sa.Column("corrected_text", sa.Text(), nullable=True),
        sa.Column(
            "intent_misparsed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("corrected_intent", sa.Text(), nullable=True),
        sa.Column("feedback_notes", sa.Text(), nullable=True),
        sa.Column("s3_export_key", sa.Text(), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.dialects.postgresql.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_voice_feedback_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name="fk_voice_feedback_user", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["voice_command_log_id"],
            ["voice_command_log.id"],
            name="fk_voice_feedback_voice_log",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_voice_feedback_created_by",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_voice_feedback"),
    )

    # Create indexes
    op.create_index("ix_voice_feedback_tenant_id", "voice_feedback", ["tenant_id"])
    op.create_index("ix_voice_feedback_user_id", "voice_feedback", ["user_id"])
    op.create_index(
        "ix_voice_feedback_unexported",
        "voice_feedback",
        ["exported_at"],
        postgresql_where=sa.text("exported_at IS NULL"),
    )

    # Create audit trigger
    op.execute("""
        CREATE TRIGGER audit_voice_feedback_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.voice_feedback
        FOR EACH ROW
        EXECUTE FUNCTION audit.log_changes()
    """)

    # Create immutable guard trigger (prevent updates to created fields)
    op.execute("""
        CREATE TRIGGER trg_voice_feedback_guard_created_immutable
        BEFORE UPDATE ON public.voice_feedback
        FOR EACH ROW
        EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)


def downgrade() -> None:
    # Drop triggers first
    op.execute(
        "DROP TRIGGER IF EXISTS audit_voice_feedback_changes ON public.voice_feedback"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_voice_feedback_guard_created_immutable ON public.voice_feedback"
    )

    # Drop indexes
    op.drop_index("ix_voice_feedback_unexported", table_name="voice_feedback")
    op.drop_index("ix_voice_feedback_user_id", table_name="voice_feedback")
    op.drop_index("ix_voice_feedback_tenant_id", table_name="voice_feedback")

    # Drop table
    op.drop_table("voice_feedback")
