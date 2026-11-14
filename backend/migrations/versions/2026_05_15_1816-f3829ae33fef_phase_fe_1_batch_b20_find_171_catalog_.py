"""phase_fe_1_batch_b20_find_171_catalog_manage_permission

FIND-171 (S2 High): Pricebook Item CRUD + Temporal Price Management

Seed `catalog.manage` RBAC permission to tenant_user_role for accountant role.
This permission guards all 6 new pricebook management endpoints:
  - GET  /api/v1/catalog/pricebook
  - POST /api/v1/catalog/pricebook
  - GET  /api/v1/catalog/pricebook/{item_id}
  - PATCH /api/v1/catalog/pricebook/{item_id}
  - POST /api/v1/catalog/pricebook/{item_id}/price
  - GET  /api/v1/catalog/pricebook/{item_id}/price-history

Notes:
  - owner role already has "*" wildcard covering all permissions — no row update needed.
  - accountant role needs explicit catalog.manage for pricebook financial reconciliation.
  - Uses idempotent JSONB array append pattern (no double-add if run twice).

Revision ID: f3829ae33fef
Revises: ac4a225c0f7c
Create Date: 2026-05-15 18:16:01
"""

from alembic import op

# revision identifiers
revision = "f3829ae33fef"
down_revision = "ac4a225c0f7c"
branch_labels = None
depends_on = None

# Permission to add
_PERMISSION = "catalog.manage"
_ROLE = "accountant"


def upgrade() -> None:
    """Add catalog.manage to accountant role in tenant_user_role (idempotent)."""
    op.execute(f"""
        UPDATE tenant_user_role
        SET permissions = permissions || '"{_PERMISSION}"'::jsonb
        WHERE code = '{_ROLE}'
          AND is_active = true
          AND NOT (
              SELECT bool_or(elem.value = '"{_PERMISSION}"')
              FROM jsonb_array_elements(permissions) AS elem(value)
          );
    """)


def downgrade() -> None:
    """Remove catalog.manage from accountant role in tenant_user_role."""
    op.execute(f"""
        UPDATE tenant_user_role
        SET permissions = (
            SELECT COALESCE(jsonb_agg(elem ORDER BY elem), '[]'::jsonb)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text != '"{_PERMISSION}"'
        )
        WHERE code = '{_ROLE}'
          AND is_active = true
          AND permissions @> '"{_PERMISSION}"'::jsonb;
    """)
