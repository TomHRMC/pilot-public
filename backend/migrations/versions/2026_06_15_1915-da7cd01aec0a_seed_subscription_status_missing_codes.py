"""seed subscription_status missing codes (trialing, unpaid, paused)

Revision ID: da7cd01aec0a
Revises: 50e2ffd2a388
Create Date: 2026-06-15

Context: Migration dd4ed7ed5f3b already seeds trial/active/past_due/canceled.
This migration adds the 3 Stripe-standard codes never previously migrated.
seed_platform.py handles all 6 codes for dev-env restore workflows.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "da7cd01aec0a"
down_revision: str | None = "50e2ffd2a388"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # subscription_status has UUID `id` PK — audit.log_changes() works fine on INSERT.
    # BEFORE UPDATE triggers don't fire on INSERT. No session_replication_role needed.
    op.execute("""
        INSERT INTO public.subscription_status
            (id, tenant_id, code, name, is_billing_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'trialing', 'Trialing', true,  now(), now()),
            (gen_random_uuid(), NULL, 'unpaid',   'Unpaid',   false, now(), now()),
            (gen_random_uuid(), NULL, 'paused',   'Paused',   false, now(), now())
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM public.subscription_status
        WHERE code IN ('trialing', 'unpaid', 'paused')
          AND tenant_id IS NULL;
    """)
