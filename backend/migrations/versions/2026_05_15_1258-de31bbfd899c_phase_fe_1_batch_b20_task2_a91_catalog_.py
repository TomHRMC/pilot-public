"""phase_fe_1_batch_b20_task2_a91_catalog_manage_permission

A91 (FIND-056): Labor Rate Version Management Endpoints

Seed `catalog.manage` RBAC permission to platform_role (owner, accountant).
This permission controls access to:
  - GET /api/v1/settings/labor-rates (read active rates)
  - POST /api/v1/settings/labor-rates (create/supersede rates)
  - GET /api/v1/settings/labor-rates/{skill_level_code}/history (read audit trail)

Uses JSONB array append pattern (idempotent).
Paired with A90 (FIND-055) which uses the same permission.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "de31bbfd899c"
down_revision = "5026cc474168"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Seed catalog.manage permission to owner and accountant roles."""
    # Owner: add catalog.manage (idempotent via ON CONFLICT logic in JSONB)
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["catalog.manage"]'::jsonb
        WHERE code = 'owner'
          AND NOT (permissions @> '["catalog.manage"]'::jsonb)
    """)

    # Accountant: add catalog.manage (idempotent)
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["catalog.manage"]'::jsonb
        WHERE code = 'accountant'
          AND NOT (permissions @> '["catalog.manage"]'::jsonb)
    """)


def downgrade() -> None:
    """Remove catalog.manage permission from platform_role."""
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(elem ORDER BY elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text != '"catalog.manage"'
        )
        WHERE code IN ('owner', 'accountant')
          AND (permissions @> '["catalog.manage"]'::jsonb)
    """)
