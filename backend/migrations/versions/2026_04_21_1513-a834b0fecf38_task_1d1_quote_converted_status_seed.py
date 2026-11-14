"""task_1d1_quote_converted_status_seed

Revision ID: a834b0fecf38
Revises: 3b9a777d2de9
Create Date: 2026-04-21 15:13:35.000000

Purpose:
    Seed a system-wide `converted` QuoteStatus row (tenant_id IS NULL).
    This status is applied to quotes when they are auto-converted to a Job
    via the POST /api/v1/quotes/{id}/convert endpoint (Task 1-D-1).

    No schema changes — data-only migration.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a834b0fecf38"
down_revision = "3b9a777d2de9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use WHERE NOT EXISTS because ON CONFLICT fails to catch duplicates
    # when the unique constraint contains a NULL value in PostgreSQL.
    # created_at / updated_at have no server default — must supply NOW() explicitly.
    op.execute("""
        INSERT INTO quote_status (id, tenant_id, code, name, is_terminal, is_default, is_active, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            NULL,
            'converted',
            'Converted to Job',
            true,
            false,
            true,
            NOW(),
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM quote_status
            WHERE code = 'converted' AND tenant_id IS NULL
        );
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM quote_status
        WHERE code = 'converted'
          AND tenant_id IS NULL;
    """)
