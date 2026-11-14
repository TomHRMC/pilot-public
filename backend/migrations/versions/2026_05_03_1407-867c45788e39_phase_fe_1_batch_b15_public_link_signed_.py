"""phase_fe_1_batch_b15_public_link_signed_token

Revision ID: 867c45788e39
Revises: 6db8e8c0e9ac
Create Date: 2026-05-03 14:07:15.000000

B15/A80: Add signed_token, revoked_at, created_by_user_id to quote_public_link
and invoice_public_link. Tighten expires_at to NOT NULL on both tables.

3-part migration pattern for NOT NULL columns:
  Step 1: Add as NULLABLE
  Step 2: Backfill existing rows
  Step 3: ALTER to NOT NULL

For expires_at: backfill NULL rows with NOW() + INTERVAL '90 days', then NOT NULL.
For created_by_user_id: backfill from created_by (same user); rows with NULL created_by
  get a fallback NULL (left nullable in DB; only new rows will have NOT NULL enforced
  application-side — see design doc §F2).
For signed_token: generate a placeholder token for legacy rows so NOT NULL can be applied
  (legacy code still uses token_hash; signed_token is for new public-link endpoints only).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "867c45788e39"
down_revision = "6db8e8c0e9ac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── quote_public_link ─────────────────────────────────────────────────────
    # Step 1: Add new columns as NULLABLE
    op.add_column(
        "quote_public_link", sa.Column("signed_token", sa.Text(), nullable=True)
    )
    op.add_column(
        "quote_public_link",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "quote_public_link", sa.Column("created_by_user_id", sa.UUID(), nullable=True)
    )

    # Step 2a: Backfill expires_at NULLs
    op.execute("""
        UPDATE quote_public_link
        SET expires_at = NOW() + INTERVAL '90 days'
        WHERE expires_at IS NULL
    """)

    # Step 2b: Backfill signed_token with a placeholder (token_hash prefixed) for legacy rows
    op.execute("""
        UPDATE quote_public_link
        SET signed_token = 'legacy.' || token_hash
        WHERE signed_token IS NULL
    """)

    # Step 2c: Backfill created_by_user_id from created_by
    op.execute("""
        UPDATE quote_public_link
        SET created_by_user_id = created_by
        WHERE created_by_user_id IS NULL AND created_by IS NOT NULL
    """)

    # Step 3: Tighten NOT NULL where specified by design doc
    op.alter_column("quote_public_link", "expires_at", nullable=False)
    op.alter_column("quote_public_link", "signed_token", nullable=False)
    # created_by_user_id: design doc §F2 allows remaining NULL for legacy rows with no created_by

    # Add FK for created_by_user_id
    op.create_foreign_key(
        "fk_quote_public_link_created_by_user_id",
        "quote_public_link",
        "user",
        ["created_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ─── invoice_public_link ───────────────────────────────────────────────────
    # Step 1: Add new columns as NULLABLE
    op.add_column(
        "invoice_public_link", sa.Column("signed_token", sa.Text(), nullable=True)
    )
    op.add_column(
        "invoice_public_link",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "invoice_public_link", sa.Column("created_by_user_id", sa.UUID(), nullable=True)
    )

    # Step 2a: Backfill expires_at NULLs
    op.execute("""
        UPDATE invoice_public_link
        SET expires_at = NOW() + INTERVAL '90 days'
        WHERE expires_at IS NULL
    """)

    # Step 2b: Backfill signed_token with a placeholder
    op.execute("""
        UPDATE invoice_public_link
        SET signed_token = 'legacy.' || token_hash
        WHERE signed_token IS NULL
    """)

    # Step 2c: Backfill created_by_user_id from created_by
    op.execute("""
        UPDATE invoice_public_link
        SET created_by_user_id = created_by
        WHERE created_by_user_id IS NULL AND created_by IS NOT NULL
    """)

    # Step 3: Tighten NOT NULL
    op.alter_column("invoice_public_link", "expires_at", nullable=False)
    op.alter_column("invoice_public_link", "signed_token", nullable=False)

    # Add FK for created_by_user_id
    op.create_foreign_key(
        "fk_invoice_public_link_created_by_user_id",
        "invoice_public_link",
        "user",
        ["created_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # invoice_public_link
    op.drop_constraint(
        "fk_invoice_public_link_created_by_user_id",
        "invoice_public_link",
        type_="foreignkey",
    )
    op.drop_column("invoice_public_link", "created_by_user_id")
    op.drop_column("invoice_public_link", "revoked_at")
    op.drop_column("invoice_public_link", "signed_token")
    op.alter_column("invoice_public_link", "expires_at", nullable=True)

    # quote_public_link
    op.drop_constraint(
        "fk_quote_public_link_created_by_user_id",
        "quote_public_link",
        type_="foreignkey",
    )
    op.drop_column("quote_public_link", "created_by_user_id")
    op.drop_column("quote_public_link", "revoked_at")
    op.drop_column("quote_public_link", "signed_token")
    op.alter_column("quote_public_link", "expires_at", nullable=True)
