"""phase_fe_1_batch_b13_auth_refresh_token_session_id

Revision ID: aa299c94248a
Revises: 97ffd00c829c
Create Date: 2026-05-02 19:47:58

A70: Add session_id FK column to auth_refresh_token.
NULL for pre-B13 tokens (they expire naturally; not revocable via session revocation path).
3-part pattern: add nullable → stays nullable (no backfill needed).
"""

from alembic import op

revision = "aa299c94248a"
down_revision = "97ffd00c829c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Add nullable column (stays nullable — pre-B13 tokens legitimately NULL)
    op.execute("""
        ALTER TABLE auth_refresh_token
            ADD COLUMN session_id UUID REFERENCES user_session_metadata(session_id)
    """)
    op.execute("""
        CREATE INDEX ix_auth_refresh_token_session_id
            ON auth_refresh_token(session_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_auth_refresh_token_session_id")
    op.execute("""
        ALTER TABLE auth_refresh_token
            DROP COLUMN IF EXISTS session_id
    """)
