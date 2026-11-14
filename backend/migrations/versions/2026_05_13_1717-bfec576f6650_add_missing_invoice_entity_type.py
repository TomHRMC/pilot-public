"""add_missing_invoice_entity_type

Revision ID: bfec576f6650
Revises: fe7a54e40735
Create Date: 2026-05-13 17:17:57.914447+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bfec576f6650"
down_revision: str | None = "fe7a54e40735"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add missing "invoice" entity_type required by notification events
    op.execute("""
        INSERT INTO entity_type (code, name, is_active, is_default, created_at, updated_at)
        VALUES (
            'invoice',
            'Invoice',
            TRUE,
            FALSE,
            NOW(),
            NOW()
        )
        ON CONFLICT (code) DO NOTHING
    """)

    # Add missing "dunning_reminder" notification_type
    op.execute("""
        INSERT INTO notification_type (code, audience, name, description, is_active, created_at, updated_at)
        VALUES (
            'dunning_reminder',
            'tenant',
            'Dunning Reminder',
            'Overdue invoice reminder notification',
            TRUE,
            NOW(),
            NOW()
        )
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    # Remove the dunning_reminder notification_type
    op.execute("""
        DELETE FROM notification_type WHERE code = 'dunning_reminder'
    """)

    # Remove the invoice entity_type
    op.execute("""
        DELETE FROM entity_type WHERE code = 'invoice'
    """)
