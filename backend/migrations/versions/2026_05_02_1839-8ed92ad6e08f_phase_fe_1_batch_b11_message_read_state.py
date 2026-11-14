"""phase_fe_1_batch_b11_message_read_state

Revision ID: 8ed92ad6e08f
Revises: 7b1ac8c0eecb
Create Date: 2026-05-02 18:39:01

B11/A66 — Create customer_communication_message_read_state table.
Per-user read receipt for individual SMS messages.
Composite PK (message_id, user_id). CASCADE on delete.
Depends on Migration 3 (customer_communication_message must exist).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "8ed92ad6e08f"
down_revision = "7b1ac8c0eecb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE customer_communication_message_read_state (
            message_id  UUID        NOT NULL REFERENCES customer_communication_message(id) ON DELETE CASCADE,
            user_id     UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            read_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (message_id, user_id)
        );
    """)

    op.execute("""
        CREATE INDEX idx_msg_read_state_user
            ON customer_communication_message_read_state(user_id, message_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS customer_communication_message_read_state;")
