"""FIND-101: Seed metered product_feature rows for voice AI, QB sync, data exports

Revision ID: b19find101seed
Revises: 8d160dad91a1
Create Date: 2026-05-13 00:00:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b19find101seed"
down_revision: str | None = "8d160dad91a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Seed three metered product_feature rows required for SaaS metered billing aggregation (FIND-101)
    # These are referenced in:
    # - backend/api/routes/voice.py: UsageLedger write for voice_ai_minutes
    # - backend/services/quickbooks_sync.py: UsageLedger write for qb_sync_operations
    # - backend/tasks/data_export_pipeline.py: UsageLedger write for data_exports

    # Insert into product_feature table (code is primary key)
    op.execute(
        """
        INSERT INTO product_feature (code, name, unit, description, is_active, created_at, updated_at, created_by, updated_by)
        VALUES
            ('voice_ai_minutes', 'Voice AI minutes', 'minutes', 'Minutes spent processing voice commands via Whisper/Ollama', true, now(), now(), NULL, NULL),
            ('qb_sync_operations', 'QB sync operations', 'operations', 'Number of QuickBooks Online sync operations (journal entries, items, etc)', true, now(), now(), NULL, NULL),
            ('data_exports', 'Data exports', 'count', 'Number of data export requests completed', true, now(), now(), NULL, NULL)
        ON CONFLICT (code) DO NOTHING;
        """
    )


def downgrade() -> None:
    # Remove the three seeded product_feature rows
    op.execute(
        """
        DELETE FROM product_feature
        WHERE code IN ('voice_ai_minutes', 'qb_sync_operations', 'data_exports');
        """
    )
