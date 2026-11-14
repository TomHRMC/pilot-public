"""phase_fe_1_batch_b19_voice_command_entity_link

Revision ID: 8d160dad91a1
Revises: 2369fb1773a6
Create Date: 2026-05-12 21:21:00.380788+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d160dad91a1"
down_revision: str | None = "2369fb1773a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create voice_command_entity_link table
    op.create_table(
        "voice_command_entity_link",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column(
            "tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("voice_command_log_id", sa.BigInteger(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column(
            "entity_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["voice_command_log_id"], ["voice_command_log.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        "ix_vcel_entity",
        "voice_command_entity_link",
        ["tenant_id", "entity_type", "entity_id"],
    )
    op.create_index(
        "ix_vcel_voice_log", "voice_command_entity_link", ["voice_command_log_id"]
    )

    # Create AppendOnlyMixin guard trigger (prevents updates to created_at/created_by)
    op.execute(
        """
        CREATE TRIGGER trg_voice_command_entity_link_guard_created_immutable
        BEFORE UPDATE ON public.voice_command_entity_link
        FOR EACH ROW
        EXECUTE FUNCTION public.guard_created_fields_immutable()
        """
    )

    # Create audit trigger (logs all DML to audit.event)
    op.execute(
        """
        CREATE TRIGGER audit_voice_command_entity_link_changes
        AFTER INSERT OR UPDATE OR DELETE ON public.voice_command_entity_link
        FOR EACH ROW
        EXECUTE FUNCTION audit.log_changes();
        """
    )


def downgrade() -> None:
    # Drop triggers first
    op.execute(
        "DROP TRIGGER IF EXISTS audit_voice_command_entity_link_changes ON public.voice_command_entity_link;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_voice_command_entity_link_guard_created_immutable ON public.voice_command_entity_link;"
    )

    # Drop indexes
    op.drop_index("ix_vcel_voice_log", table_name="voice_command_entity_link")
    op.drop_index("ix_vcel_entity", table_name="voice_command_entity_link")

    # Drop table
    op.drop_table("voice_command_entity_link")
