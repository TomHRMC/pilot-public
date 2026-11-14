"""phase_fe_1_batch_b17_quote_link_status_seed_revoked_expired_exhausted

FIND-146 (S2 High): Seed the 3 missing quote_link_status rows needed for the
full quote public link lifecycle:
  - revoked   / Revoked            — manually revoked by owner
  - expired   / Expired            — past expires_at timestamp
  - exhausted / Max Uses Reached   — used_count >= max_uses consumed

The 'active' row already exists (seeded in a prior migration).

These rows are required by the FIND-146 lifecycle enforcement in the acceptance
handler, _create_public_link_impl (server-resolves 'active'), and revoke handler.

Revision ID: bf1e91a9e960
Revises: f80aca00dc97
Create Date: 2026-05-11 19:56:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "bf1e91a9e960"
down_revision = "f80aca00dc97"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # BEFORE UPDATE triggers don't fire on INSERT; audit fallback handles non-UUID PKs.
    # No session_replication_role bypass needed on RDS.
    op.execute("""
        INSERT INTO quote_link_status (id, tenant_id, code, name, is_default, is_active,
                                       created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'revoked',   'Revoked',          false, true, now(), now()),
            (gen_random_uuid(), NULL, 'expired',   'Expired',          false, true, now(), now()),
            (gen_random_uuid(), NULL, 'exhausted', 'Max Uses Reached', false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM quote_link_status
        WHERE tenant_id IS NULL
          AND code IN ('revoked', 'expired', 'exhausted');
    """)
