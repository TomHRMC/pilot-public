"""add_quickbooks_webhook_fields

Task: Phase 3, Task #19 - QuickBooks Webhook Handler
Gap: #27 - Webhook Delivery Worker

Adds QuickBooks-specific fields to webhook_event table for Cloud Events support.

Revision ID: 0de405f02fa7
Revises: 40a492ca69ce
Create Date: 2026-03-22 20:20:00.101185+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0de405f02fa7"
down_revision: str | None = "40a492ca69ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add QuickBooks webhook fields to webhook_event table
    op.add_column(
        "webhook_event",
        sa.Column("source_app", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "webhook_event",
        sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "webhook_event",
        sa.Column("event_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "webhook_event",
        sa.Column(
            "signature_valid", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "webhook_event",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "webhook_event",
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )

    # Make legacy fields nullable for backward compatibility
    op.alter_column(
        "webhook_event", "tenant_id", existing_type=sa.UUID(), nullable=True
    )
    op.alter_column(
        "webhook_event", "event_type_code", existing_type=sa.VARCHAR(), nullable=True
    )
    op.alter_column(
        "webhook_event", "entity_type_code", existing_type=sa.VARCHAR(), nullable=True
    )
    op.alter_column(
        "webhook_event", "entity_id", existing_type=sa.UUID(), nullable=True
    )

    # Create indexes for efficient queries
    op.create_index(
        op.f("ix_webhook_event_event_id"), "webhook_event", ["event_id"], unique=False
    )
    op.create_index(
        op.f("ix_webhook_event_source_app"),
        "webhook_event",
        ["source_app"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_webhook_event_source_app"), table_name="webhook_event")
    op.drop_index(op.f("ix_webhook_event_event_id"), table_name="webhook_event")

    # Restore legacy field constraints
    op.alter_column(
        "webhook_event", "entity_id", existing_type=sa.UUID(), nullable=False
    )
    op.alter_column(
        "webhook_event", "entity_type_code", existing_type=sa.VARCHAR(), nullable=False
    )
    op.alter_column(
        "webhook_event", "event_type_code", existing_type=sa.VARCHAR(), nullable=False
    )
    op.alter_column(
        "webhook_event", "tenant_id", existing_type=sa.UUID(), nullable=False
    )

    # Drop QuickBooks webhook fields
    op.drop_column("webhook_event", "error_message")
    op.drop_column("webhook_event", "processed_at")
    op.drop_column("webhook_event", "signature_valid")
    op.drop_column("webhook_event", "event_id")
    op.drop_column("webhook_event", "event_type")
    op.drop_column("webhook_event", "source_app")
