"""phase_7_0_batch_5_tenant_stamping_communications_webhooks

Revision ID: 760e6045deb0
Revises:
Create Date: 2026-04-15 17:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "760e6045deb0"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ==============================================================
    # TABLE: conversation_message
    # Parent: conversation_session via session_id (1-hop)
    # conversation_session.tenant_id is NON-NULLABLE — safe to join.
    # ==============================================================
    op.add_column(
        "conversation_message", sa.Column("tenant_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_conversation_message_tenant_id",
        "conversation_message",
        "tenant",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(
        "ix_conversation_message_tenant_id", "conversation_message", ["tenant_id"]
    )
    op.execute("""
        UPDATE conversation_message
        SET tenant_id = conversation_session.tenant_id
        FROM conversation_session
        WHERE conversation_message.session_id = conversation_session.id
    """)
    op.alter_column("conversation_message", "tenant_id", nullable=False)

    # ==============================================================
    # TABLE: webhook_delivery_attempt
    # Parent: webhook_endpoint via webhook_endpoint_id (1-hop)
    # webhook_endpoint.tenant_id is NON-NULLABLE — safe to join.
    # ⚠️ DO NOT use webhook_event as the join source — its tenant_id is NULLABLE.
    # ⚠️ id is a serial INTEGER — do NOT alter or reference id as UUID.
    # ==============================================================
    op.add_column(
        "webhook_delivery_attempt", sa.Column("tenant_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_webhook_delivery_attempt_tenant_id",
        "webhook_delivery_attempt",
        "tenant",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(
        "ix_webhook_delivery_attempt_tenant_id",
        "webhook_delivery_attempt",
        ["tenant_id"],
    )
    op.execute("""
        UPDATE webhook_delivery_attempt
        SET tenant_id = webhook_endpoint.tenant_id
        FROM webhook_endpoint
        WHERE webhook_delivery_attempt.webhook_endpoint_id = webhook_endpoint.id
    """)
    op.alter_column("webhook_delivery_attempt", "tenant_id", nullable=False)


def downgrade() -> None:
    op.drop_index(
        "ix_webhook_delivery_attempt_tenant_id", table_name="webhook_delivery_attempt"
    )
    op.drop_constraint(
        "fk_webhook_delivery_attempt_tenant_id",
        "webhook_delivery_attempt",
        type_="foreignkey",
    )
    op.drop_column("webhook_delivery_attempt", "tenant_id")

    op.drop_index(
        "ix_conversation_message_tenant_id", table_name="conversation_message"
    )
    op.drop_constraint(
        "fk_conversation_message_tenant_id", "conversation_message", type_="foreignkey"
    )
    op.drop_column("conversation_message", "tenant_id")
