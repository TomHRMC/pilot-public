"""phase_fe_1_batch_b15_public_link_short_code_table

Revision ID: 27e787ad52bd
Revises: 867c45788e39
Create Date: 2026-05-03 14:07:15.000000

B15/A80: Create public_link_short_code table.
Short codes are base62, 5-8 chars. link_id is polymorphic (no DB FK).
Mixin: MachineLogMixin (created_at only).

NOTE: No audit trigger — audit.log_changes() requires NEW.id (UUID) but
public_link_short_code PK is short_code (TEXT). MachineLogMixin tables with
non-UUID PKs skip the audit trigger per project convention (same as
email_template). Click tracking via click_count/last_clicked_at provides
the operational trail needed without formal audit.event rows.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "27e787ad52bd"
down_revision = "867c45788e39"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_link_short_code",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("short_code", sa.Text(), nullable=False),
        sa.Column("link_type", sa.Text(), nullable=False),
        sa.Column("link_id", sa.UUID(), nullable=False),
        sa.Column(
            "click_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("last_clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "link_type IN ('quote', 'invoice')",
            name="public_link_short_code_link_type_chk",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_public_link_short_code_created_by",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("short_code", name="pk_public_link_short_code"),
    )

    op.create_index(
        "ix_public_link_short_code_link_id", "public_link_short_code", ["link_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_public_link_short_code_link_id", table_name="public_link_short_code"
    )
    op.drop_table("public_link_short_code")
