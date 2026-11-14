"""phase_fe_1_batch_b1_quote_approval_state_machine

Revision ID: 0711fb10275a
Revises: cc08b2d99a0c
Create Date: 2026-05-01 10:57:34

A2 — Quote Approval Workflow State Machine
- Seeds 2 new quote_status rows: 'pending_approval', 'approved'
- Adds 4 nullable columns to quote: submitted_by_user_id, submitted_at,
  approved_by_user_id, approved_at
- Adds 1 NOT NULL column to tenant_settings: require_approval_for_tech_quotes
  (3-part pattern: nullable → backfill → NOT NULL)

Note: Does NOT rename/touch existing 'pending' status (code=pending is
retained as-is per F&Q Q1 in batch-b1-design.md).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0711fb10275a"
down_revision = "cc08b2d99a0c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Seed two new quote_status system rows                            #
    # ------------------------------------------------------------------ #
    op.execute("""
        INSERT INTO quote_status (id, tenant_id, code, name, is_terminal, is_default, is_active,
                                  created_at, updated_at)
        VALUES
          (gen_random_uuid(), NULL, 'pending_approval', 'Pending Approval',
           FALSE, FALSE, TRUE, now(), now()),
          (gen_random_uuid(), NULL, 'approved', 'Approved',
           FALSE, FALSE, TRUE, now(), now())
        ON CONFLICT DO NOTHING
    """)

    # ------------------------------------------------------------------ #
    # 2. Add 4 nullable columns to quote                                  #
    # ------------------------------------------------------------------ #
    op.add_column("quote", sa.Column("submitted_by_user_id", sa.UUID(), nullable=True))
    op.add_column(
        "quote", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("quote", sa.Column("approved_by_user_id", sa.UUID(), nullable=True))
    op.add_column(
        "quote", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)
    )

    # FK constraints for the new user references
    op.create_foreign_key(
        "fk_quote_submitted_by_user_id",
        "quote",
        "user",
        ["submitted_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_quote_approved_by_user_id",
        "quote",
        "user",
        ["approved_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # 3. Add require_approval_for_tech_quotes to tenant_settings          #
    #    3-part pattern: nullable → backfill → NOT NULL + default         #
    # ------------------------------------------------------------------ #
    # Part 1: Add nullable
    op.add_column(
        "tenant_settings",
        sa.Column("require_approval_for_tech_quotes", sa.Boolean(), nullable=True),
    )

    # Part 2: Backfill existing rows — safe default = TRUE (require approval)
    op.execute("""
        UPDATE tenant_settings
        SET require_approval_for_tech_quotes = TRUE
        WHERE require_approval_for_tech_quotes IS NULL
    """)

    # Part 3: Lock NOT NULL + set server default
    op.alter_column(
        "tenant_settings",
        "require_approval_for_tech_quotes",
        nullable=False,
        server_default=sa.text("true"),
    )


def downgrade() -> None:
    # Remove tenant_settings column
    op.drop_column("tenant_settings", "require_approval_for_tech_quotes")

    # Remove quote FK constraints and columns
    op.drop_constraint("fk_quote_approved_by_user_id", "quote", type_="foreignkey")
    op.drop_constraint("fk_quote_submitted_by_user_id", "quote", type_="foreignkey")
    op.drop_column("quote", "approved_at")
    op.drop_column("quote", "approved_by_user_id")
    op.drop_column("quote", "submitted_at")
    op.drop_column("quote", "submitted_by_user_id")

    # Remove seeded status rows (system rows have tenant_id = NULL)
    op.execute("""
        DELETE FROM quote_status
        WHERE code IN ('pending_approval', 'approved')
          AND tenant_id IS NULL
    """)
